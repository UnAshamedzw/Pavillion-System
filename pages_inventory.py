"""
pages_inventory.py - Inventory/Parts Management Module
Pavillion Coaches Bus Management System
Track spare parts, stock levels, and workshop inventory
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES
from audit_logger import AuditLogger
from auth import has_permission


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_inventory_items(category=None, search=None, low_stock_only=False):
    """Get inventory items with optional filters"""
    conn = get_connection()
    
    query = """
        SELECT * FROM inventory
        WHERE 1=1
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if category:
        query += f" AND category = {ph}"
        params.append(category)
    
    if search:
        query += f" AND (part_name LIKE {ph} OR part_number LIKE {ph} OR description LIKE {ph})"
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])
    
    if low_stock_only:
        query += " AND quantity <= reorder_level"
    
    query += " ORDER BY category, part_name"
    
    df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    conn.close()
    return df


def add_inventory_item(part_number, part_name, category, description, quantity,
                       unit, unit_cost, reorder_level, supplier, location,
                       notes=None, created_by=None):
    """Add a new inventory item"""
    conn = get_connection()
    cursor = conn.cursor()
    
    total_value = quantity * unit_cost
    
    try:
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO inventory (
                    part_number, part_name, category, description, quantity,
                    unit, unit_cost, total_value, reorder_level, supplier,
                    location, notes, status, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (part_number, part_name, category, description, quantity,
                  unit, unit_cost, total_value, reorder_level, supplier,
                  location, notes, 'Active', created_by))
            result = cursor.fetchone()
            item_id = result['id'] if hasattr(result, 'keys') else result[0]
        else:
            cursor.execute("""
                INSERT INTO inventory (
                    part_number, part_name, category, description, quantity,
                    unit, unit_cost, total_value, reorder_level, supplier,
                    location, notes, status, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (part_number, part_name, category, description, quantity,
                  unit, unit_cost, total_value, reorder_level, supplier,
                  location, notes, 'Active', created_by))
            item_id = cursor.lastrowid
        
        conn.commit()
        return item_id
    except Exception as e:
        print(f"Error adding inventory item: {e}")
        return None
    finally:
        conn.close()


def update_inventory_item(item_id, **kwargs):
    """Update an inventory item"""
    conn = get_connection()
    cursor = conn.cursor()
    
    set_clauses = []
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = {ph}")
        params.append(value)
    
    if not set_clauses:
        return False
    
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    params.append(item_id)
    
    query = f"UPDATE inventory SET {', '.join(set_clauses)} WHERE id = {ph}"
    
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating inventory item: {e}")
        return False
    finally:
        conn.close()


def adjust_stock(item_id, quantity_change, transaction_type, reference=None, 
                notes=None, created_by=None):
    """Adjust stock quantity and log transaction"""
    conn = get_connection()
    cursor = conn.cursor()
    
    ph = '%s' if USE_POSTGRES else '?'
    
    try:
        # Get current quantity
        cursor.execute(f"SELECT quantity, unit_cost, part_name FROM inventory WHERE id = {ph}", (item_id,))
        result = cursor.fetchone()
        
        if not result:
            return False
        
        if hasattr(result, 'keys'):
            current_qty = result['quantity']
            unit_cost = result['unit_cost']
            part_name = result['part_name']
        else:
            current_qty = result[0]
            unit_cost = result[1]
            part_name = result[2]
        
        new_qty = current_qty + quantity_change
        
        if new_qty < 0:
            return False  # Can't go negative
        
        new_total_value = new_qty * unit_cost
        
        # Update inventory
        cursor.execute(f"""
            UPDATE inventory 
            SET quantity = {ph}, total_value = {ph}, updated_at = CURRENT_TIMESTAMP
            WHERE id = {ph}
        """, (new_qty, new_total_value, item_id))
        
        # Log transaction
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO inventory_transactions (
                    inventory_id, part_name, transaction_type, quantity_change,
                    quantity_before, quantity_after, unit_cost, total_value,
                    reference, notes, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (item_id, part_name, transaction_type, quantity_change,
                  current_qty, new_qty, unit_cost, abs(quantity_change) * unit_cost,
                  reference, notes, created_by))
        else:
            cursor.execute("""
                INSERT INTO inventory_transactions (
                    inventory_id, part_name, transaction_type, quantity_change,
                    quantity_before, quantity_after, unit_cost, total_value,
                    reference, notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (item_id, part_name, transaction_type, quantity_change,
                  current_qty, new_qty, unit_cost, abs(quantity_change) * unit_cost,
                  reference, notes, created_by))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adjusting stock: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_inventory_transactions(item_id=None, transaction_type=None, 
                               start_date=None, end_date=None):
    """Get inventory transactions"""
    conn = get_connection()
    
    query = """
        SELECT * FROM inventory_transactions
        WHERE 1=1
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if item_id:
        query += f" AND inventory_id = {ph}"
        params.append(item_id)
    
    if transaction_type:
        query += f" AND transaction_type = {ph}"
        params.append(transaction_type)
    
    if start_date:
        query += f" AND DATE(created_at) >= {ph}"
        params.append(start_date)
    
    if end_date:
        query += f" AND DATE(created_at) <= {ph}"
        params.append(end_date)
    
    query += " ORDER BY created_at DESC"
    
    df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    conn.close()
    return df


def get_low_stock_items():
    """Get items below reorder level"""
    conn = get_connection()
    
    query = """
        SELECT * FROM inventory
        WHERE quantity <= reorder_level AND status = 'Active'
        ORDER BY (reorder_level - quantity) DESC
    """
    
    df = pd.read_sql_query(query, get_engine())
    conn.close()
    return df


def get_inventory_summary():
    """Get inventory summary statistics"""
    conn = get_connection()
    
    # Total items and value
    query = """
        SELECT 
            COUNT(*) as total_items,
            SUM(quantity) as total_quantity,
            SUM(total_value) as total_value
        FROM inventory
        WHERE status = 'Active'
    """
    summary_df = pd.read_sql_query(query, get_engine())
    
    # Low stock count
    low_stock_query = """
        SELECT COUNT(*) as low_stock
        FROM inventory
        WHERE quantity <= reorder_level AND status = 'Active'
    """
    low_stock_df = pd.read_sql_query(low_stock_query, get_engine())
    
    # Out of stock
    out_of_stock_query = """
        SELECT COUNT(*) as out_of_stock
        FROM inventory
        WHERE quantity = 0 AND status = 'Active'
    """
    out_of_stock_df = pd.read_sql_query(out_of_stock_query, get_engine())
    
    # Categories count
    cat_query = """
        SELECT COUNT(DISTINCT category) as categories
        FROM inventory
        WHERE status = 'Active'
    """
    cat_df = pd.read_sql_query(cat_query, get_engine())
    
    conn.close()
    
    return {
        'total_items': summary_df['total_items'].values[0] if not summary_df.empty else 0,
        'total_quantity': summary_df['total_quantity'].values[0] if not summary_df.empty else 0,
        'total_value': summary_df['total_value'].values[0] if not summary_df.empty else 0,
        'low_stock': low_stock_df['low_stock'].values[0] if not low_stock_df.empty else 0,
        'out_of_stock': out_of_stock_df['out_of_stock'].values[0] if not out_of_stock_df.empty else 0,
        'categories': cat_df['categories'].values[0] if not cat_df.empty else 0
    }


def get_inventory_by_category():
    """Get inventory grouped by category"""
    conn = get_connection()
    
    query = """
        SELECT 
            category,
            COUNT(*) as item_count,
            SUM(quantity) as total_quantity,
            SUM(total_value) as total_value
        FROM inventory
        WHERE status = 'Active'
        GROUP BY category
        ORDER BY total_value DESC
    """
    
    df = pd.read_sql_query(query, get_engine())
    conn.close()
    return df


def delete_inventory_item(item_id):
    """Delete/deactivate an inventory item"""
    conn = get_connection()
    cursor = conn.cursor()
    
    ph = '%s' if USE_POSTGRES else '?'
    
    try:
        cursor.execute(f"UPDATE inventory SET status = 'Inactive' WHERE id = {ph}", (item_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting inventory item: {e}")
        return False
    finally:
        conn.close()


# =============================================================================
# CONSTANTS
# =============================================================================

INVENTORY_CATEGORIES = [
    "Engine Parts",
    "Brake System",
    "Suspension",
    "Electrical",
    "Body Parts",
    "Interior",
    "Tyres & Wheels",
    "Filters",
    "Fluids & Lubricants",
    "Belts & Hoses",
    "Cooling System",
    "Fuel System",
    "Transmission",
    "Exhaust System",
    "Safety Equipment",
    "Tools",
    "Consumables",
    "Other"
]

UNIT_TYPES = [
    "Piece", "Pair", "Set", "Litre", "Gallon", "Kg", "Metre", "Box", "Pack", "Roll"
]

TRANSACTION_TYPES = [
    "Stock In",
    "Stock Out",
    "Adjustment",
    "Return",
    "Damage/Loss",
    "Transfer"
]


# =============================================================================
# PAGE FUNCTION
# =============================================================================

def inventory_management_page():
    """Inventory and parts management page"""
    
    st.header("🔧 Inventory & Parts Management")
    st.markdown("Track spare parts, stock levels, and workshop inventory")
    st.markdown("---")
    
    can_add = has_permission('add_maintenance')
    can_edit = has_permission('edit_maintenance')
    can_delete = has_permission('delete_maintenance')
    
    # Summary metrics
    summary = get_inventory_summary()
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("📦 Total Items", summary['total_items'])
    with col2:
        st.metric("🔢 Total Quantity", f"{int(summary['total_quantity'] or 0):,}")
    with col3:
        st.metric("💰 Total Value", f"${float(summary['total_value'] or 0):,.2f}")
    with col4:
        st.metric("📂 Categories", summary['categories'])
    with col5:
        st.metric("⚠️ Low Stock", summary['low_stock'], 
                 delta_color="inverse" if summary['low_stock'] > 0 else "off")
    with col6:
        st.metric("❌ Out of Stock", summary['out_of_stock'],
                 delta_color="inverse" if summary['out_of_stock'] > 0 else "off")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📦 Inventory List",
        "➕ Add Item",
        "📊 Stock Movement",
        "⚠️ Low Stock Alerts",
        "📈 Reports"
    ])
    
    with tab1:
        st.subheader("📦 Inventory List")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search = st.text_input("🔍 Search", placeholder="Part name or number...")
        
        with col2:
            category_filter = st.selectbox("Category", ["All Categories"] + INVENTORY_CATEGORIES)
        
        with col3:
            stock_filter = st.checkbox("Show only low stock items")
        
        # Get items
        cat_val = category_filter if category_filter != "All Categories" else None
        items_df = get_inventory_items(
            category=cat_val,
            search=search if search else None,
            low_stock_only=stock_filter
        )
        
        if items_df.empty:
            st.info("No inventory items found")
        else:
            # Add stock status indicator
            def get_stock_status(row):
                if row['quantity'] == 0:
                    return "🔴 Out of Stock"
                elif row['quantity'] <= row['reorder_level']:
                    return "🟡 Low Stock"
                else:
                    return "🟢 In Stock"
            
            items_df['Stock Status'] = items_df.apply(get_stock_status, axis=1)
            
            display_df = items_df[[
                'Stock Status', 'part_number', 'part_name', 'category',
                'quantity', 'unit', 'unit_cost', 'total_value', 'location'
            ]].copy()
            
            display_df.columns = ['Status', 'Part #', 'Name', 'Category',
                                 'Qty', 'Unit', 'Unit Cost ($)', 'Total Value ($)', 'Location']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Export
            csv = items_df.to_csv(index=False)
            st.download_button(
                label="📥 Export Inventory",
                data=csv,
                file_name=f"inventory_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with tab2:
        st.subheader("➕ Add New Inventory Item")
        
        if not can_add:
            st.warning("You don't have permission to add inventory items")
        else:
            with st.form("add_inventory_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    part_number = st.text_input("Part Number*", placeholder="e.g., BRK-001")
                    part_name = st.text_input("Part Name*", placeholder="e.g., Brake Pads - Front")
                    category = st.selectbox("Category*", INVENTORY_CATEGORIES)
                    description = st.text_area("Description", height=100)
                
                with col2:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        quantity = st.number_input("Initial Quantity*", min_value=0, value=0)
                    with col_b:
                        unit = st.selectbox("Unit", UNIT_TYPES)
                    
                    col_c, col_d = st.columns(2)
                    with col_c:
                        unit_cost = st.number_input("Unit Cost ($)*", min_value=0.0, value=0.0, step=0.01)
                    with col_d:
                        reorder_level = st.number_input("Reorder Level", min_value=0, value=5)
                    
                    supplier = st.text_input("Supplier", placeholder="Supplier name")
                    location = st.text_input("Storage Location", placeholder="e.g., Shelf A-3")
                
                notes = st.text_area("Notes", height=68)
                
                # Show calculated total
                total_value = quantity * unit_cost
                st.info(f"💰 Total Value: ${total_value:,.2f}")
                
                if st.form_submit_button("➕ Add Item", type="primary", use_container_width=True):
                    if not part_number or not part_name:
                        st.error("Part number and name are required")
                    else:
                        item_id = add_inventory_item(
                            part_number=part_number,
                            part_name=part_name,
                            category=category,
                            description=description,
                            quantity=quantity,
                            unit=unit,
                            unit_cost=unit_cost,
                            reorder_level=reorder_level,
                            supplier=supplier,
                            location=location,
                            notes=notes,
                            created_by=st.session_state['user']['username']
                        )
                        
                        if item_id:
                            AuditLogger.log_action("Create", "Inventory",
                                                  f"Added item: {part_name} ({part_number})")
                            st.success(f"✅ Item added! (ID: {item_id})")
                            st.rerun()
                        else:
                            st.error("Error adding item")
    
    with tab3:
        st.subheader("📊 Stock Movement")
        
        items_df = get_inventory_items()
        
        if items_df.empty:
            st.info("No inventory items. Add items first.")
        else:
            # Stock adjustment form
            st.markdown("### Adjust Stock")
            
            with st.form("stock_adjustment_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    item_options = {
                        f"{row['part_number']} - {row['part_name']} (Qty: {row['quantity']})": row['id']
                        for _, row in items_df.iterrows()
                    }
                    
                    selected_item = st.selectbox("Select Item*", list(item_options.keys()))
                    
                    transaction_type = st.selectbox("Transaction Type*", TRANSACTION_TYPES)
                
                with col2:
                    quantity_change = st.number_input("Quantity", value=1, step=1)
                    
                    # Auto-adjust sign based on transaction type
                    if transaction_type in ["Stock Out", "Damage/Loss"]:
                        quantity_change = -abs(quantity_change)
                        st.caption("⚠️ Stock will be reduced")
                    else:
                        quantity_change = abs(quantity_change)
                        st.caption("✅ Stock will be increased")
                    
                    reference = st.text_input("Reference", placeholder="e.g., Maintenance Job #123")
                
                adj_notes = st.text_area("Notes", height=68, key="adj_notes")
                
                if st.form_submit_button("📊 Record Movement", type="primary"):
                    item_id = item_options[selected_item]
                    
                    if adjust_stock(
                        item_id=item_id,
                        quantity_change=quantity_change,
                        transaction_type=transaction_type,
                        reference=reference,
                        notes=adj_notes,
                        created_by=st.session_state['user']['username']
                    ):
                        AuditLogger.log_action("Update", "Inventory",
                                              f"Stock {transaction_type}: {quantity_change} units")
                        st.success("✅ Stock updated!")
                        st.rerun()
                    else:
                        st.error("Error updating stock. Quantity cannot go below zero.")
            
            st.markdown("---")
            
            # Transaction history
            st.markdown("### Recent Transactions")
            
            col1, col2 = st.columns(2)
            with col1:
                trans_start = st.date_input("From", value=datetime.now().date() - timedelta(days=30), key="trans_start")
            with col2:
                trans_end = st.date_input("To", value=datetime.now().date(), key="trans_end")
            
            transactions_df = get_inventory_transactions(
                start_date=str(trans_start),
                end_date=str(trans_end)
            )
            
            if transactions_df.empty:
                st.info("No transactions found for this period")
            else:
                display_trans = transactions_df[[
                    'created_at', 'part_name', 'transaction_type', 'quantity_change',
                    'quantity_before', 'quantity_after', 'reference', 'created_by'
                ]].copy()
                
                display_trans.columns = ['Date', 'Part', 'Type', 'Change',
                                         'Before', 'After', 'Reference', 'By']
                
                st.dataframe(display_trans.head(50), use_container_width=True, hide_index=True)
    
    with tab4:
        st.subheader("⚠️ Low Stock Alerts")
        
        low_stock_df = get_low_stock_items()
        
        if low_stock_df.empty:
            st.success("✅ All items are adequately stocked!")
        else:
            st.warning(f"⚠️ {len(low_stock_df)} item(s) need attention!")
            
            # Critical items (out of stock)
            out_of_stock = low_stock_df[low_stock_df['quantity'] == 0]
            
            if not out_of_stock.empty:
                st.markdown("### 🔴 Out of Stock")
                st.error(f"{len(out_of_stock)} item(s) are completely out of stock!")
                
                for _, row in out_of_stock.iterrows():
                    st.markdown(f"""
                    - **{row['part_name']}** ({row['part_number']})
                      - Category: {row['category']}
                      - Reorder Level: {row['reorder_level']}
                      - Supplier: {row['supplier'] or 'N/A'}
                    """)
            
            # Low stock items
            low_not_zero = low_stock_df[low_stock_df['quantity'] > 0]
            
            if not low_not_zero.empty:
                st.markdown("### 🟡 Low Stock")
                st.warning(f"{len(low_not_zero)} item(s) are below reorder level")
                
                display_low = low_not_zero[[
                    'part_number', 'part_name', 'category', 'quantity',
                    'reorder_level', 'unit', 'supplier'
                ]].copy()
                
                display_low.columns = ['Part #', 'Name', 'Category', 'Current Qty',
                                       'Reorder Level', 'Unit', 'Supplier']
                
                display_low['Shortage'] = display_low['Reorder Level'] - display_low['Current Qty']
                
                st.dataframe(display_low, use_container_width=True, hide_index=True)
            
            # Generate reorder list
            st.markdown("---")
            st.markdown("### 📋 Suggested Reorder List")
            
            reorder_list = low_stock_df[['part_number', 'part_name', 'quantity', 
                                         'reorder_level', 'unit', 'supplier', 'unit_cost']].copy()
            reorder_list['Suggested Order'] = reorder_list['reorder_level'] * 2 - reorder_list['quantity']
            reorder_list['Est. Cost'] = reorder_list['Suggested Order'] * reorder_list['unit_cost']
            
            st.dataframe(reorder_list, use_container_width=True, hide_index=True)
            
            total_reorder_cost = reorder_list['Est. Cost'].sum()
            st.info(f"💰 Estimated total reorder cost: **${total_reorder_cost:,.2f}**")
            
            # Export reorder list
            csv = reorder_list.to_csv(index=False)
            st.download_button(
                label="📥 Export Reorder List",
                data=csv,
                file_name=f"reorder_list_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with tab5:
        st.subheader("📈 Inventory Reports")
        
        # Value by category
        cat_df = get_inventory_by_category()
        
        if cat_df.empty:
            st.info("No inventory data for reports")
        else:
            st.markdown("### Inventory Value by Category")
            
            fig = px.pie(
                cat_df,
                values='total_value',
                names='category',
                title='Inventory Value Distribution'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Bar chart
            fig2 = px.bar(
                cat_df,
                x='category',
                y='total_value',
                title='Value by Category',
                labels={'category': 'Category', 'total_value': 'Value ($)'},
                color='total_value',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Category summary table
            st.markdown("### Category Summary")
            
            display_cat = cat_df.copy()
            display_cat.columns = ['Category', 'Items', 'Total Qty', 'Total Value ($)']
            st.dataframe(display_cat, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # Stock movement trends
            st.markdown("### Stock Movement Trends (Last 30 Days)")
            
            transactions_df = get_inventory_transactions(
                start_date=str(datetime.now().date() - timedelta(days=30)),
                end_date=str(datetime.now().date())
            )
            
            if not transactions_df.empty:
                # Group by date and type
                transactions_df['date'] = pd.to_datetime(transactions_df['created_at']).dt.date
                
                daily_movements = transactions_df.groupby(['date', 'transaction_type']).agg({
                    'quantity_change': 'sum',
                    'total_value': 'sum'
                }).reset_index()
                
                fig3 = px.bar(
                    daily_movements,
                    x='date',
                    y='quantity_change',
                    color='transaction_type',
                    title='Daily Stock Movements',
                    labels={'date': 'Date', 'quantity_change': 'Quantity Change'}
                )
                st.plotly_chart(fig3, use_container_width=True)
                
                # Summary by transaction type
                st.markdown("### Movement Summary by Type")
                
                type_summary = transactions_df.groupby('transaction_type').agg({
                    'quantity_change': 'sum',
                    'total_value': 'sum'
                }).reset_index()
                type_summary.columns = ['Transaction Type', 'Total Qty Change', 'Total Value ($)']
                
                st.dataframe(type_summary, use_container_width=True, hide_index=True)
            else:
                st.info("No transactions in the last 30 days")
            
            st.markdown("---")
            
            # Top items by value
            st.markdown("### Top 10 Items by Value")
            
            items_df = get_inventory_items()
            
            if not items_df.empty:
                top_items = items_df.nlargest(10, 'total_value')[
                    ['part_number', 'part_name', 'quantity', 'unit_cost', 'total_value']
                ]
                top_items.columns = ['Part #', 'Name', 'Qty', 'Unit Cost ($)', 'Total Value ($)']
                
                st.dataframe(top_items, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # Maintenance Parts Usage
            st.markdown("### 🔧 Parts Used in Maintenance")
            
            maint_usage = transactions_df[transactions_df['reference'].str.contains('MAINT', case=False, na=False)] if not transactions_df.empty else pd.DataFrame()
            
            if maint_usage.empty:
                st.info("No parts used in maintenance records yet")
            else:
                maint_usage_display = maint_usage[[
                    'created_at', 'part_name', 'quantity_change', 'total_value', 'reference'
                ]].copy()
                maint_usage_display.columns = ['Date', 'Part', 'Qty Used', 'Value ($)', 'Maintenance Ref']
                maint_usage_display['Qty Used'] = maint_usage_display['Qty Used'].abs()
                
                st.dataframe(maint_usage_display, use_container_width=True, hide_index=True)
                
                total_maint_value = maint_usage_display['Value ($)'].sum()
                st.metric("Total Parts Value Used in Maintenance", f"${total_maint_value:,.2f}")