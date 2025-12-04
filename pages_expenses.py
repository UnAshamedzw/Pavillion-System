"""
pages_expenses.py - General Expenses Module
Pavillion Coaches Bus Management System
Track non-bus related operational expenses like utilities, office supplies, etc.
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

def create_linked_expense(expense_date, category, subcategory, description, vendor,
                          amount, source_type, source_id, payment_status='Paid',
                          payment_method='Bank Transfer', created_by=None):
    """
    Create an expense record linked from another module.
    Used by: Fleet Management (insurance), Documents, etc.
    
    source_type: 'insurance', 'maintenance', 'document', etc.
    source_id: ID or reference from source table
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Add source reference to notes
    notes = f"Auto-linked from {source_type} (Ref: {source_id})"
    
    try:
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO general_expenses (
                    expense_date, category, subcategory, description, vendor,
                    amount, payment_method, payment_status, receipt_number,
                    recurring, recurring_frequency, notes, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (expense_date, category, subcategory, description, vendor,
                  amount, payment_method, payment_status, source_id,
                  False, None, notes, created_by))
            result = cursor.fetchone()
            expense_id = result['id'] if hasattr(result, 'keys') else result[0]
        else:
            cursor.execute("""
                INSERT INTO general_expenses (
                    expense_date, category, subcategory, description, vendor,
                    amount, payment_method, payment_status, receipt_number,
                    recurring, recurring_frequency, notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (expense_date, category, subcategory, description, vendor,
                  amount, payment_method, payment_status, source_id,
                  False, None, notes, created_by))
            expense_id = cursor.lastrowid
        
        conn.commit()
        return expense_id
    except Exception as e:
        print(f"Error creating linked expense: {e}")
        return None
    finally:
        conn.close()


def check_linked_expense_exists(source_type, source_id):
    """Check if an expense already exists for this source"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT id FROM general_expenses 
        WHERE receipt_number = {ph} AND notes LIKE {ph}
    """, (source_id, f"%{source_type}%"))
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def get_expenses(category=None, start_date=None, end_date=None, payment_status=None):
    """Get expenses with optional filters"""
    conn = get_connection()
    
    query = """
        SELECT id, expense_date, category, subcategory, description, vendor,
               amount, payment_method, payment_status, receipt_number,
               recurring, recurring_frequency, notes, created_by, created_at
        FROM general_expenses
        WHERE 1=1
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if category:
        query += f" AND category = {ph}"
        params.append(category)
    
    if start_date:
        query += f" AND expense_date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND expense_date <= {ph}"
        params.append(str(end_date))
    
    if payment_status:
        query += f" AND payment_status = {ph}"
        params.append(payment_status)
    
    query += " ORDER BY expense_date DESC, created_at DESC"
    
    df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    conn.close()
    return df


def add_expense(expense_date, category, subcategory, description, vendor,
                amount, payment_method, payment_status, receipt_number=None,
                recurring=False, recurring_frequency=None, notes=None, created_by=None):
    """Add a new expense record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO general_expenses (
                    expense_date, category, subcategory, description, vendor,
                    amount, payment_method, payment_status, receipt_number,
                    recurring, recurring_frequency, notes, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (expense_date, category, subcategory, description, vendor,
                  amount, payment_method, payment_status, receipt_number,
                  recurring, recurring_frequency, notes, created_by))
            result = cursor.fetchone()
            expense_id = result['id'] if hasattr(result, 'keys') else result[0]
        else:
            cursor.execute("""
                INSERT INTO general_expenses (
                    expense_date, category, subcategory, description, vendor,
                    amount, payment_method, payment_status, receipt_number,
                    recurring, recurring_frequency, notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (expense_date, category, subcategory, description, vendor,
                  amount, payment_method, payment_status, receipt_number,
                  recurring, recurring_frequency, notes, created_by))
            expense_id = cursor.lastrowid
        
        conn.commit()
        return expense_id
    except Exception as e:
        print(f"Error adding expense: {e}")
        return None
    finally:
        conn.close()


def update_expense(expense_id, **kwargs):
    """Update an expense record"""
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
    params.append(expense_id)
    
    query = f"UPDATE general_expenses SET {', '.join(set_clauses)} WHERE id = {ph}"
    
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating expense: {e}")
        return False
    finally:
        conn.close()


def delete_expense(expense_id):
    """Delete an expense record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    ph = '%s' if USE_POSTGRES else '?'
    
    try:
        cursor.execute(f"DELETE FROM general_expenses WHERE id = {ph}", (expense_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting expense: {e}")
        return False
    finally:
        conn.close()


def get_expense_summary(start_date=None, end_date=None):
    """Get expense summary statistics"""
    conn = get_connection()
    
    ph = '%s' if USE_POSTGRES else '?'
    
    where_clause = "WHERE 1=1"
    params = []
    
    if start_date:
        where_clause += f" AND expense_date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        where_clause += f" AND expense_date <= {ph}"
        params.append(str(end_date))
    
    # Total expenses
    total_query = f"SELECT COALESCE(SUM(amount), 0) as total FROM general_expenses {where_clause}"
    total_df = pd.read_sql_query(total_query, get_engine(), params=tuple(params) if params else None)
    total = float(total_df['total'].values[0]) if not total_df.empty else 0
    
    # Count
    count_query = f"SELECT COUNT(*) as count FROM general_expenses {where_clause}"
    count_df = pd.read_sql_query(count_query, get_engine(), params=tuple(params) if params else None)
    count = int(count_df['count'].values[0]) if not count_df.empty else 0
    
    # Unpaid
    unpaid_params = params.copy()
    unpaid_params.append('Unpaid')
    unpaid_query = f"SELECT COALESCE(SUM(amount), 0) as unpaid FROM general_expenses {where_clause} AND payment_status = {ph}"
    unpaid_df = pd.read_sql_query(unpaid_query, get_engine(), params=tuple(unpaid_params) if unpaid_params else None)
    unpaid = float(unpaid_df['unpaid'].values[0]) if not unpaid_df.empty else 0
    
    conn.close()
    
    return {
        'total': total,
        'count': count,
        'unpaid': unpaid,
        'average': total / count if count > 0 else 0
    }


def get_expenses_by_category(start_date=None, end_date=None):
    """Get expenses grouped by category"""
    conn = get_connection()
    
    ph = '%s' if USE_POSTGRES else '?'
    
    where_clause = "WHERE 1=1"
    params = []
    
    if start_date:
        where_clause += f" AND expense_date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        where_clause += f" AND expense_date <= {ph}"
        params.append(str(end_date))
    
    query = f"""
        SELECT category, COUNT(*) as count, SUM(amount) as total
        FROM general_expenses
        {where_clause}
        GROUP BY category
        ORDER BY total DESC
    """
    
    df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    conn.close()
    return df


def get_monthly_expenses(year=None):
    """Get monthly expense totals"""
    conn = get_connection()
    
    if year is None:
        year = datetime.now().year
    
    ph = '%s' if USE_POSTGRES else '?'
    
    if USE_POSTGRES:
        query = f"""
            SELECT 
                EXTRACT(MONTH FROM expense_date::date) as month,
                SUM(amount) as total
            FROM general_expenses
            WHERE EXTRACT(YEAR FROM expense_date::date) = {ph}
            GROUP BY EXTRACT(MONTH FROM expense_date::date)
            ORDER BY month
        """
    else:
        query = f"""
            SELECT 
                CAST(strftime('%m', expense_date) AS INTEGER) as month,
                SUM(amount) as total
            FROM general_expenses
            WHERE strftime('%Y', expense_date) = {ph}
            GROUP BY strftime('%m', expense_date)
            ORDER BY month
        """
    
    df = pd.read_sql_query(query, get_engine(), params=(str(year),))
    conn.close()
    return df


# =============================================================================
# CONSTANTS
# =============================================================================

EXPENSE_CATEGORIES = {
    "Utilities": ["Electricity", "Water", "Internet/WiFi", "Phone", "Gas", "Other Utilities"],
    "Office": ["Rent", "Office Supplies", "Furniture", "Equipment", "Cleaning", "Security", "Other Office"],
    "Staff Welfare": ["Food/Meals", "Tea/Coffee", "Staff Events", "Uniforms", "Training", "Medical", "Other Welfare"],
    "Administrative": ["Licenses & Permits", "Insurance", "Legal Fees", "Accounting", "Bank Charges", "Subscriptions", "Other Admin"],
    "Marketing": ["Advertising", "Signage", "Promotions", "Website", "Social Media", "Other Marketing"],
    "Transport": ["Staff Transport", "Courier/Delivery", "Parking", "Tolls", "Other Transport"],
    "Repairs & Maintenance": ["Building Repairs", "Equipment Repairs", "Plumbing", "Electrical", "HVAC", "Other Repairs"],
    "Technology": ["Software", "Hardware", "IT Services", "Cloud Services", "Other Tech"],
    "Miscellaneous": ["Donations", "Gifts", "Entertainment", "Contingency", "Other"]
}

PAYMENT_METHODS = [
    "Cash", "Bank Transfer", "EcoCash", "OneMoney", "InnBucks", 
    "Credit Card", "Debit Card", "Cheque", "Petty Cash", "Other"
]

PAYMENT_STATUS = ["Paid", "Unpaid", "Partial", "Pending Approval"]

RECURRING_FREQUENCIES = ["Weekly", "Monthly", "Quarterly", "Annually"]


# =============================================================================
# PAGE FUNCTION
# =============================================================================

def general_expenses_page():
    """General expenses management page"""
    
    st.header("💸 General Expenses")
    st.markdown("Track non-bus related operational expenses")
    st.markdown("---")
    
    can_add = has_permission('add_income') or has_permission('add_maintenance')
    can_delete = has_permission('delete_income') or has_permission('delete_maintenance')
    
    # Date range for summary
    col_date1, col_date2, col_date3 = st.columns([2, 2, 2])
    
    with col_date1:
        summary_start = st.date_input(
            "From", 
            value=datetime.now().date().replace(day=1),
            key="summary_start"
        )
    
    with col_date2:
        summary_end = st.date_input(
            "To", 
            value=datetime.now().date(),
            key="summary_end"
        )
    
    with col_date3:
        st.write("")
        st.write("")
        if st.button("📊 This Month"):
            summary_start = datetime.now().date().replace(day=1)
            summary_end = datetime.now().date()
    
    # Summary metrics
    summary = get_expense_summary(summary_start, summary_end)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Total Expenses", f"${summary['total']:,.2f}")
    with col2:
        st.metric("📝 Total Records", summary['count'])
    with col3:
        st.metric("📊 Average", f"${summary['average']:,.2f}")
    with col4:
        st.metric("⚠️ Unpaid", f"${summary['unpaid']:,.2f}",
                 delta_color="inverse" if summary['unpaid'] > 0 else "off")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "➕ Add Expense",
        "📋 Expense List",
        "📊 Reports",
        "🔄 Recurring Expenses"
    ])
    
    with tab1:
        st.subheader("➕ Add New Expense")
        
        if not can_add:
            st.warning("You don't have permission to add expenses")
        else:
            with st.form("add_expense_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    expense_date = st.date_input("📅 Date*", value=datetime.now().date())
                    
                    category = st.selectbox("📁 Category*", list(EXPENSE_CATEGORIES.keys()))
                    
                    # Dynamic subcategory based on category
                    subcategories = EXPENSE_CATEGORIES.get(category, ["Other"])
                    subcategory = st.selectbox("📂 Subcategory*", subcategories)
                    
                    description = st.text_input("📝 Description*", placeholder="e.g., December electricity bill")
                    
                    vendor = st.text_input("🏪 Vendor/Supplier", placeholder="e.g., ZESA, Econet")
                
                with col2:
                    amount = st.number_input("💰 Amount ($)*", min_value=0.0, step=0.01, format="%.2f")
                    
                    payment_method = st.selectbox("💳 Payment Method", PAYMENT_METHODS)
                    
                    payment_status = st.selectbox("📊 Payment Status", PAYMENT_STATUS)
                    
                    receipt_number = st.text_input("🧾 Receipt/Invoice Number", placeholder="e.g., INV-2024-001")
                    
                    col_rec1, col_rec2 = st.columns(2)
                    with col_rec1:
                        is_recurring = st.checkbox("🔄 Recurring Expense")
                    with col_rec2:
                        if is_recurring:
                            recurring_freq = st.selectbox("Frequency", RECURRING_FREQUENCIES)
                        else:
                            recurring_freq = None
                
                notes = st.text_area("📝 Notes", placeholder="Additional details...")
                
                if st.form_submit_button("➕ Add Expense", type="primary", use_container_width=True):
                    if not all([category, subcategory, description, amount > 0]):
                        st.error("Please fill in all required fields")
                    else:
                        expense_id = add_expense(
                            expense_date=str(expense_date),
                            category=category,
                            subcategory=subcategory,
                            description=description,
                            vendor=vendor,
                            amount=amount,
                            payment_method=payment_method,
                            payment_status=payment_status,
                            receipt_number=receipt_number,
                            recurring=is_recurring,
                            recurring_frequency=recurring_freq,
                            notes=notes,
                            created_by=st.session_state.get('user', {}).get('username', 'system')
                        )
                        
                        if expense_id:
                            AuditLogger.log_action(
                                "Create", "Expenses",
                                f"Added expense: {category}/{subcategory} - ${amount:.2f}"
                            )
                            st.success(f"✅ Expense added successfully! (ID: {expense_id})")
                            st.rerun()
                        else:
                            st.error("Error adding expense")
    
    with tab2:
        st.subheader("📋 Expense List")
        
        # Filters
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            filter_category = st.selectbox(
                "Category", 
                ["All Categories"] + list(EXPENSE_CATEGORIES.keys()),
                key="filter_cat"
            )
        
        with col_f2:
            filter_status = st.selectbox(
                "Payment Status",
                ["All Status"] + PAYMENT_STATUS,
                key="filter_status"
            )
        
        with col_f3:
            filter_start = st.date_input(
                "From",
                value=datetime.now().date() - timedelta(days=30),
                key="filter_start"
            )
        
        with col_f4:
            filter_end = st.date_input(
                "To",
                value=datetime.now().date(),
                key="filter_end"
            )
        
        # Get filtered expenses
        cat_filter = filter_category if filter_category != "All Categories" else None
        status_filter = filter_status if filter_status != "All Status" else None
        
        expenses_df = get_expenses(
            category=cat_filter,
            start_date=filter_start,
            end_date=filter_end,
            payment_status=status_filter
        )
        
        if expenses_df.empty:
            st.info("No expenses found for the selected filters")
        else:
            # Summary for filtered results
            filtered_total = expenses_df['amount'].sum()
            st.info(f"**{len(expenses_df)} expenses** totaling **${filtered_total:,.2f}**")
            
            # Display table
            display_df = expenses_df[[
                'expense_date', 'category', 'subcategory', 'description',
                'vendor', 'amount', 'payment_method', 'payment_status'
            ]].copy()
            
            display_df.columns = ['Date', 'Category', 'Subcategory', 'Description',
                                 'Vendor', 'Amount ($)', 'Payment', 'Status']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Export
            csv = expenses_df.to_csv(index=False)
            st.download_button(
                label="📥 Export to CSV",
                data=csv,
                file_name=f"expenses_{filter_start}_{filter_end}.csv",
                mime="text/csv"
            )
            
            st.markdown("---")
            
            # Update/Delete section
            st.subheader("✏️ Update Expense")
            
            expense_options = {
                f"ID:{row['id']} - {row['expense_date']} - {row['description'][:30]} (${row['amount']:.2f})": row['id']
                for _, row in expenses_df.iterrows()
            }
            
            selected_expense = st.selectbox("Select Expense", list(expense_options.keys()))
            
            if selected_expense:
                expense_id = expense_options[selected_expense]
                expense_row = expenses_df[expenses_df['id'] == expense_id].iloc[0]
                
                col_u1, col_u2, col_u3 = st.columns(3)
                
                with col_u1:
                    new_status = st.selectbox(
                        "Update Status",
                        PAYMENT_STATUS,
                        index=PAYMENT_STATUS.index(expense_row['payment_status']) if expense_row['payment_status'] in PAYMENT_STATUS else 0
                    )
                
                with col_u2:
                    if st.button("💾 Update Status", use_container_width=True):
                        if update_expense(expense_id, payment_status=new_status):
                            AuditLogger.log_action("Update", "Expenses", f"Updated expense ID:{expense_id} status to {new_status}")
                            st.success("Status updated!")
                            st.rerun()
                
                with col_u3:
                    if can_delete:
                        if st.button("🗑️ Delete", use_container_width=True):
                            if st.session_state.get(f'confirm_del_exp_{expense_id}', False):
                                if delete_expense(expense_id):
                                    AuditLogger.log_action("Delete", "Expenses", f"Deleted expense ID:{expense_id}")
                                    st.success("Deleted!")
                                    st.rerun()
                            else:
                                st.session_state[f'confirm_del_exp_{expense_id}'] = True
                                st.warning("Click again to confirm")
    
    with tab3:
        st.subheader("📊 Expense Reports")
        
        # Category breakdown
        st.markdown("### Expenses by Category")
        
        cat_df = get_expenses_by_category(summary_start, summary_end)
        
        if cat_df.empty:
            st.info("No expense data for reports")
        else:
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                fig_pie = px.pie(
                    cat_df,
                    values='total',
                    names='category',
                    title='Expense Distribution by Category'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_chart2:
                fig_bar = px.bar(
                    cat_df,
                    x='category',
                    y='total',
                    title='Expense Amounts by Category',
                    labels={'category': 'Category', 'total': 'Amount ($)'},
                    color='total',
                    color_continuous_scale='Reds'
                )
                fig_bar.update_xaxes(tickangle=45)
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Category table
            cat_display = cat_df.copy()
            cat_display.columns = ['Category', 'Count', 'Total ($)']
            cat_display['Avg ($)'] = cat_display['Total ($)'] / cat_display['Count']
            st.dataframe(cat_display, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Monthly trend
        st.markdown("### Monthly Expense Trend")
        
        year = st.selectbox("Select Year", range(datetime.now().year, datetime.now().year - 5, -1))
        
        monthly_df = get_monthly_expenses(year)
        
        if monthly_df.empty:
            st.info(f"No expense data for {year}")
        else:
            # Fill missing months
            all_months = pd.DataFrame({'month': range(1, 13)})
            monthly_df = all_months.merge(monthly_df, on='month', how='left').fillna(0)
            
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            monthly_df['month_name'] = monthly_df['month'].apply(lambda x: month_names[int(x)-1])
            
            fig_line = px.line(
                monthly_df,
                x='month_name',
                y='total',
                title=f'Monthly Expenses - {year}',
                labels={'month_name': 'Month', 'total': 'Amount ($)'},
                markers=True
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
            # Monthly summary table
            monthly_display = monthly_df[['month_name', 'total']].copy()
            monthly_display.columns = ['Month', 'Total ($)']
            
            col_m1, col_m2 = st.columns([2, 1])
            with col_m1:
                st.dataframe(monthly_display, use_container_width=True, hide_index=True)
            with col_m2:
                yearly_total = monthly_df['total'].sum()
                st.metric(f"Total {year}", f"${yearly_total:,.2f}")
                st.metric("Monthly Average", f"${yearly_total/12:,.2f}")
    
    with tab4:
        st.subheader("🔄 Recurring Expenses")
        
        # Get recurring expenses
        all_expenses = get_expenses()
        recurring_df = all_expenses[all_expenses['recurring'] == True] if not all_expenses.empty else pd.DataFrame()
        
        if recurring_df.empty:
            st.info("No recurring expenses set up")
        else:
            st.success(f"📋 {len(recurring_df)} recurring expense(s) configured")
            
            for _, row in recurring_df.iterrows():
                with st.expander(f"🔄 {row['description']} - ${row['amount']:.2f} ({row['recurring_frequency']})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Category:** {row['category']} / {row['subcategory']}")
                        st.write(f"**Vendor:** {row['vendor'] or 'N/A'}")
                        st.write(f"**Amount:** ${row['amount']:.2f}")
                    with col2:
                        st.write(f"**Frequency:** {row['recurring_frequency']}")
                        st.write(f"**Payment Method:** {row['payment_method']}")
                        st.write(f"**Last Recorded:** {row['expense_date']}")
        
        st.markdown("---")
        
        # Quick add recurring
        st.markdown("### ➕ Quick Add from Recurring")
        
        if not recurring_df.empty:
            recurring_options = {
                f"{row['description']} - ${row['amount']:.2f} ({row['recurring_frequency']})": row
                for _, row in recurring_df.iterrows()
            }
            
            selected_recurring = st.selectbox("Select Recurring Expense", list(recurring_options.keys()))
            
            if selected_recurring:
                rec_row = recurring_options[selected_recurring]
                
                col1, col2 = st.columns(2)
                with col1:
                    new_date = st.date_input("Date for New Entry", value=datetime.now().date())
                with col2:
                    new_amount = st.number_input("Amount", value=float(rec_row['amount']), step=0.01)
                
                if st.button("➕ Add This Month's Entry", type="primary"):
                    expense_id = add_expense(
                        expense_date=str(new_date),
                        category=rec_row['category'],
                        subcategory=rec_row['subcategory'],
                        description=f"{rec_row['description']} - {new_date.strftime('%B %Y')}",
                        vendor=rec_row['vendor'],
                        amount=new_amount,
                        payment_method=rec_row['payment_method'],
                        payment_status="Unpaid",
                        receipt_number=None,
                        recurring=False,
                        recurring_frequency=None,
                        notes=f"From recurring: {rec_row['description']}",
                        created_by=st.session_state.get('user', {}).get('username', 'system')
                    )
                    
                    if expense_id:
                        st.success(f"✅ Added! (ID: {expense_id})")
                        st.rerun()