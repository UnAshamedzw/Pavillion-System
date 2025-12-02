"""
pages_alerts.py - Notifications & Alerts Module
Pavillion Coaches Bus Management System
Centralized alert system for expiring documents, low stock, upcoming bookings, etc.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES
from auth import has_permission


# =============================================================================
# ALERT FUNCTIONS
# =============================================================================

def get_expiring_documents_alerts(days=30):
    """Get documents expiring within specified days"""
    conn = get_connection()
    
    today = datetime.now().date()
    cutoff = today + timedelta(days=days)
    
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT id, document_type, document_name, entity_type, entity_name,
               expiry_date, days_to_expiry, status
        FROM documents
        WHERE expiry_date IS NOT NULL 
        AND expiry_date <= {ph}
        AND status = 'Active'
        ORDER BY expiry_date ASC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=[str(cutoff)])
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_expired_licenses_alerts():
    """Get buses with expired licenses/insurance"""
    conn = get_connection()
    
    today = str(datetime.now().date())
    
    query = """
        SELECT bus_number, registration_number, make, model,
               zinara_licence_expiry, vehicle_insurance_expiry,
               passenger_insurance_expiry, fitness_certificate_expiry
        FROM buses
        WHERE status = 'Active'
    """
    
    try:
        df = pd.read_sql_query(query, get_engine())
    except:
        df = pd.DataFrame()
    
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
    
    # Check each expiry column
    alerts = []
    
    for _, row in df.iterrows():
        expiry_cols = {
            'ZINARA License': 'zinara_licence_expiry',
            'Vehicle Insurance': 'vehicle_insurance_expiry',
            'Passenger Insurance': 'passenger_insurance_expiry',
            'Fitness Certificate': 'fitness_certificate_expiry'
        }
        
        for doc_type, col in expiry_cols.items():
            if pd.notna(row[col]) and row[col]:
                try:
                    exp_date = datetime.strptime(str(row[col])[:10], '%Y-%m-%d').date()
                    days_left = (exp_date - datetime.now().date()).days
                    
                    if days_left <= 30:
                        alerts.append({
                            'bus_number': row['bus_number'],
                            'registration': row['registration_number'],
                            'document_type': doc_type,
                            'expiry_date': row[col],
                            'days_left': days_left,
                            'status': 'Expired' if days_left < 0 else 'Expiring Soon'
                        })
                except:
                    pass
    
    return pd.DataFrame(alerts)


def get_low_stock_alerts():
    """Get inventory items below reorder level"""
    conn = get_connection()
    
    query = """
        SELECT id, part_number, part_name, category, quantity, 
               reorder_level, unit, supplier
        FROM inventory
        WHERE quantity <= reorder_level AND status = 'Active'
        ORDER BY (reorder_level - quantity) DESC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine())
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_upcoming_bookings_alerts(days=7):
    """Get bookings in the next X days"""
    conn = get_connection()
    
    today = str(datetime.now().date())
    cutoff = str(datetime.now().date() + timedelta(days=days))
    
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT b.*, c.customer_name, c.phone as customer_phone
        FROM bookings b
        LEFT JOIN customers c ON b.customer_id = c.id
        WHERE b.trip_date >= {ph} AND b.trip_date <= {ph}
        AND b.status IN ('Pending', 'Confirmed')
        ORDER BY b.trip_date ASC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=[today, cutoff])
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_pending_bookings_alerts():
    """Get bookings that are still pending confirmation"""
    conn = get_connection()
    
    query = """
        SELECT b.*, c.customer_name, c.phone as customer_phone
        FROM bookings b
        LEFT JOIN customers c ON b.customer_id = c.id
        WHERE b.status = 'Pending'
        ORDER BY b.trip_date ASC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine())
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_unpaid_bookings_alerts():
    """Get bookings with outstanding payments"""
    conn = get_connection()
    
    query = """
        SELECT b.*, c.customer_name, c.phone as customer_phone
        FROM bookings b
        LEFT JOIN customers c ON b.customer_id = c.id
        WHERE b.payment_status IN ('Unpaid', 'Deposit Paid')
        AND b.status != 'Cancelled'
        ORDER BY b.trip_date ASC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine())
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_maintenance_due_alerts():
    """Get buses that may be due for maintenance based on last service"""
    conn = get_connection()
    
    # Get last maintenance date per bus
    query = """
        SELECT bus_number, MAX(date) as last_maintenance
        FROM maintenance
        GROUP BY bus_number
    """
    
    try:
        df = pd.read_sql_query(query, get_engine())
    except:
        df = pd.DataFrame()
    
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
    
    # Check if last maintenance was more than 30 days ago
    alerts = []
    today = datetime.now().date()
    
    for _, row in df.iterrows():
        if pd.notna(row['last_maintenance']):
            try:
                last_date = datetime.strptime(str(row['last_maintenance'])[:10], '%Y-%m-%d').date()
                days_since = (today - last_date).days
                
                if days_since >= 30:
                    alerts.append({
                        'bus_number': row['bus_number'],
                        'last_maintenance': row['last_maintenance'],
                        'days_since': days_since
                    })
            except:
                pass
    
    return pd.DataFrame(alerts)


def get_leave_requests_pending():
    """Get pending leave requests"""
    conn = get_connection()
    
    query = """
        SELECT l.*, e.full_name, e.position
        FROM leave_records l
        JOIN employees e ON l.employee_id = e.id
        WHERE l.status = 'Pending'
        ORDER BY l.created_at DESC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine())
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_employee_documents_expiring(days=30):
    """Get employee documents expiring soon"""
    conn = get_connection()
    
    today = datetime.now().date()
    cutoff = today + timedelta(days=days)
    
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT id, document_type, document_name, entity_name,
               expiry_date, days_to_expiry
        FROM documents
        WHERE entity_type = 'Employee'
        AND expiry_date IS NOT NULL 
        AND expiry_date <= {ph}
        AND status = 'Active'
        ORDER BY expiry_date ASC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=[str(cutoff)])
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_all_alerts_summary():
    """Get summary count of all alert types"""
    
    # Documents expiring
    docs_expiring = get_expiring_documents_alerts(30)
    docs_expired = docs_expiring[docs_expiring['days_to_expiry'] < 0] if not docs_expiring.empty else pd.DataFrame()
    
    # Bus licenses
    bus_licenses = get_expired_licenses_alerts()
    
    # Low stock
    low_stock = get_low_stock_alerts()
    out_of_stock = low_stock[low_stock['quantity'] == 0] if not low_stock.empty else pd.DataFrame()
    
    # Bookings
    upcoming_bookings = get_upcoming_bookings_alerts(7)
    pending_bookings = get_pending_bookings_alerts()
    unpaid_bookings = get_unpaid_bookings_alerts()
    
    # Maintenance
    maintenance_due = get_maintenance_due_alerts()
    
    # Leave requests
    pending_leave = get_leave_requests_pending()
    
    return {
        'docs_expiring': len(docs_expiring),
        'docs_expired': len(docs_expired),
        'bus_licenses': len(bus_licenses),
        'low_stock': len(low_stock),
        'out_of_stock': len(out_of_stock),
        'upcoming_bookings': len(upcoming_bookings),
        'pending_bookings': len(pending_bookings),
        'unpaid_bookings': len(unpaid_bookings),
        'maintenance_due': len(maintenance_due),
        'pending_leave': len(pending_leave)
    }


# =============================================================================
# PAGE FUNCTION
# =============================================================================

def alerts_dashboard_page():
    """Centralized alerts and notifications dashboard"""
    
    st.header("🔔 Alerts & Notifications")
    st.markdown("Centralized view of all system alerts requiring attention")
    st.markdown("---")
    
    # Get all alerts summary
    summary = get_all_alerts_summary()
    
    # Calculate total critical alerts
    critical_count = (
        summary['docs_expired'] + 
        summary['out_of_stock'] + 
        summary['bus_licenses']
    )
    
    warning_count = (
        summary['docs_expiring'] - summary['docs_expired'] +
        summary['low_stock'] - summary['out_of_stock'] +
        summary['pending_bookings'] +
        summary['unpaid_bookings'] +
        summary['maintenance_due'] +
        summary['pending_leave']
    )
    
    # Summary cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if critical_count > 0:
            st.error(f"🔴 **{critical_count}** Critical Alerts")
        else:
            st.success("🟢 No Critical Alerts")
    
    with col2:
        if warning_count > 0:
            st.warning(f"🟡 **{warning_count}** Warnings")
        else:
            st.success("🟢 No Warnings")
    
    with col3:
        st.info(f"📅 **{summary['upcoming_bookings']}** Upcoming Trips (7 days)")
    
    with col4:
        total = critical_count + warning_count
        st.metric("Total Alerts", total)
    
    st.markdown("---")
    
    # Alert Categories
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        f"📄 Documents ({summary['docs_expiring']})",
        f"🚌 Fleet ({summary['bus_licenses']})",
        f"📦 Inventory ({summary['low_stock']})",
        f"📅 Bookings ({summary['pending_bookings'] + summary['unpaid_bookings']})",
        f"🔧 Maintenance ({summary['maintenance_due']})",
        f"👥 HR ({summary['pending_leave']})"
    ])
    
    with tab1:
        st.subheader("📄 Document Alerts")
        
        docs_df = get_expiring_documents_alerts(30)
        
        if docs_df.empty:
            st.success("✅ No document alerts")
        else:
            # Expired documents
            expired = docs_df[docs_df['days_to_expiry'] < 0]
            
            if not expired.empty:
                st.error(f"🔴 **{len(expired)} Expired Documents**")
                
                for _, doc in expired.iterrows():
                    days_ago = abs(int(doc['days_to_expiry']))
                    st.markdown(f"""
                    <div style="background-color: #ffebee; padding: 10px; border-radius: 5px; margin: 5px 0;">
                        <strong>🔴 {doc['document_type']}</strong> - {doc['entity_type']}: {doc['entity_name']}<br>
                        <small>Expired {days_ago} days ago ({doc['expiry_date']})</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
            
            # Expiring within 7 days
            expiring_7 = docs_df[(docs_df['days_to_expiry'] >= 0) & (docs_df['days_to_expiry'] <= 7)]
            
            if not expiring_7.empty:
                st.warning(f"🟠 **{len(expiring_7)} Expiring Within 7 Days**")
                
                for _, doc in expiring_7.iterrows():
                    days_left = int(doc['days_to_expiry'])
                    st.markdown(f"""
                    <div style="background-color: #fff3e0; padding: 10px; border-radius: 5px; margin: 5px 0;">
                        <strong>🟠 {doc['document_type']}</strong> - {doc['entity_type']}: {doc['entity_name']}<br>
                        <small>Expires in {days_left} days ({doc['expiry_date']})</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
            
            # Expiring within 30 days
            expiring_30 = docs_df[(docs_df['days_to_expiry'] > 7) & (docs_df['days_to_expiry'] <= 30)]
            
            if not expiring_30.empty:
                st.info(f"🟡 **{len(expiring_30)} Expiring Within 30 Days**")
                
                display_df = expiring_30[['document_type', 'entity_type', 'entity_name', 
                                          'expiry_date', 'days_to_expiry']].copy()
                display_df.columns = ['Document', 'Type', 'Entity', 'Expiry Date', 'Days Left']
                st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("🚌 Fleet Alerts")
        
        bus_df = get_expired_licenses_alerts()
        
        if bus_df.empty:
            st.success("✅ All bus documents are valid")
        else:
            # Expired
            expired = bus_df[bus_df['status'] == 'Expired']
            
            if not expired.empty:
                st.error(f"🔴 **{len(expired)} Expired Bus Documents**")
                
                for _, row in expired.iterrows():
                    st.markdown(f"""
                    <div style="background-color: #ffebee; padding: 10px; border-radius: 5px; margin: 5px 0;">
                        <strong>🔴 {row['registration']}</strong> - {row['document_type']}<br>
                        <small>Expired {abs(row['days_left'])} days ago ({row['expiry_date']})</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
            
            # Expiring soon
            expiring = bus_df[bus_df['status'] == 'Expiring Soon']
            
            if not expiring.empty:
                st.warning(f"🟡 **{len(expiring)} Expiring Soon**")
                
                display_df = expiring[['registration', 'document_type', 'expiry_date', 'days_left']].copy()
                display_df.columns = ['Bus', 'Document', 'Expiry Date', 'Days Left']
                st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("📦 Inventory Alerts")
        
        stock_df = get_low_stock_alerts()
        
        if stock_df.empty:
            st.success("✅ All inventory items adequately stocked")
        else:
            # Out of stock
            out_of_stock = stock_df[stock_df['quantity'] == 0]
            
            if not out_of_stock.empty:
                st.error(f"🔴 **{len(out_of_stock)} Out of Stock**")
                
                for _, row in out_of_stock.iterrows():
                    st.markdown(f"""
                    <div style="background-color: #ffebee; padding: 10px; border-radius: 5px; margin: 5px 0;">
                        <strong>🔴 {row['part_name']}</strong> ({row['part_number']})<br>
                        <small>Category: {row['category']} | Reorder Level: {row['reorder_level']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
            
            # Low stock
            low_stock = stock_df[stock_df['quantity'] > 0]
            
            if not low_stock.empty:
                st.warning(f"🟡 **{len(low_stock)} Low Stock Items**")
                
                display_df = low_stock[['part_number', 'part_name', 'category', 
                                        'quantity', 'reorder_level', 'supplier']].copy()
                display_df.columns = ['Part #', 'Name', 'Category', 'Qty', 'Reorder Level', 'Supplier']
                st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    with tab4:
        st.subheader("📅 Booking Alerts")
        
        # Pending bookings
        pending_df = get_pending_bookings_alerts()
        
        if not pending_df.empty:
            st.warning(f"⏳ **{len(pending_df)} Pending Confirmation**")
            
            display_pending = pending_df[['booking_ref', 'customer_name', 'trip_date', 
                                          'pickup_location', 'total_amount']].copy()
            display_pending.columns = ['Ref', 'Customer', 'Trip Date', 'Pickup', 'Amount ($)']
            st.dataframe(display_pending, use_container_width=True, hide_index=True)
            
            st.markdown("---")
        
        # Unpaid bookings
        unpaid_df = get_unpaid_bookings_alerts()
        
        if not unpaid_df.empty:
            st.warning(f"💰 **{len(unpaid_df)} Outstanding Payments**")
            
            for _, row in unpaid_df.iterrows():
                balance = float(row['total_amount']) - float(row['deposit_amount'] or 0)
                status_icon = "🟡" if row['payment_status'] == 'Deposit Paid' else "🔴"
                
                st.markdown(f"""
                <div style="background-color: #fff3e0; padding: 10px; border-radius: 5px; margin: 5px 0;">
                    <strong>{status_icon} {row['booking_ref']}</strong> - {row['customer_name']}<br>
                    <small>Trip: {row['trip_date']} | Balance Due: ${balance:,.2f} ({row['payment_status']})</small>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Upcoming bookings
        upcoming_df = get_upcoming_bookings_alerts(7)
        
        if not upcoming_df.empty:
            st.info(f"📅 **{len(upcoming_df)} Upcoming Trips (Next 7 Days)**")
            
            display_upcoming = upcoming_df[['booking_ref', 'customer_name', 'trip_date',
                                            'pickup_time', 'pickup_location', 'status']].copy()
            display_upcoming.columns = ['Ref', 'Customer', 'Date', 'Time', 'Pickup', 'Status']
            st.dataframe(display_upcoming, use_container_width=True, hide_index=True)
        
        if pending_df.empty and unpaid_df.empty and upcoming_df.empty:
            st.success("✅ No booking alerts")
    
    with tab5:
        st.subheader("🔧 Maintenance Alerts")
        
        maint_df = get_maintenance_due_alerts()
        
        if maint_df.empty:
            st.success("✅ All buses recently serviced")
        else:
            st.warning(f"🔧 **{len(maint_df)} Buses May Need Service**")
            st.caption("Buses with no maintenance recorded in 30+ days")
            
            for _, row in maint_df.iterrows():
                color = "#ffebee" if row['days_since'] > 60 else "#fff3e0"
                icon = "🔴" if row['days_since'] > 60 else "🟡"
                
                st.markdown(f"""
                <div style="background-color: {color}; padding: 10px; border-radius: 5px; margin: 5px 0;">
                    <strong>{icon} Bus {row['bus_number']}</strong><br>
                    <small>Last service: {row['last_maintenance']} ({row['days_since']} days ago)</small>
                </div>
                """, unsafe_allow_html=True)
    
    with tab6:
        st.subheader("👥 HR Alerts")
        
        # Pending leave requests
        leave_df = get_leave_requests_pending()
        
        if not leave_df.empty:
            st.warning(f"📋 **{len(leave_df)} Pending Leave Requests**")
            
            for _, row in leave_df.iterrows():
                st.markdown(f"""
                <div style="background-color: #e3f2fd; padding: 10px; border-radius: 5px; margin: 5px 0;">
                    <strong>📋 {row['full_name']}</strong> ({row['position']})<br>
                    <small>{row['leave_type']}: {row['start_date']} to {row['end_date']} ({row['days_requested']} days)</small>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Employee documents expiring
        emp_docs_df = get_employee_documents_expiring(30)
        
        if not emp_docs_df.empty:
            st.warning(f"📄 **{len(emp_docs_df)} Employee Documents Expiring**")
            
            display_df = emp_docs_df[['entity_name', 'document_type', 'expiry_date', 'days_to_expiry']].copy()
            display_df.columns = ['Employee', 'Document', 'Expiry Date', 'Days Left']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        if leave_df.empty and emp_docs_df.empty:
            st.success("✅ No HR alerts")
    
    # Quick Actions
    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📄 Go to Documents", use_container_width=True):
            st.info("Navigate to: Operations → 📄 Documents")
    
    with col2:
        if st.button("📦 Go to Inventory", use_container_width=True):
            st.info("Navigate to: Operations → 📦 Inventory")
    
    with col3:
        if st.button("📅 Go to Bookings", use_container_width=True):
            st.info("Navigate to: Operations → 👥 Customers & Bookings")
    
    with col4:
        if st.button("🚌 Go to Fleet", use_container_width=True):
            st.info("Navigate to: Operations → 🚌 Fleet Management")


def get_dashboard_alerts_widget():
    """
    Returns alert counts for display on the main dashboard.
    Call this from the dashboard page to show alerts.
    """
    summary = get_all_alerts_summary()
    
    critical = (
        summary['docs_expired'] + 
        summary['out_of_stock'] + 
        summary['bus_licenses']
    )
    
    warnings = (
        summary['docs_expiring'] - summary['docs_expired'] +
        summary['low_stock'] - summary['out_of_stock'] +
        summary['pending_bookings'] +
        summary['maintenance_due']
    )
    
    return {
        'critical': critical,
        'warnings': warnings,
        'upcoming_trips': summary['upcoming_bookings'],
        'pending_payments': summary['unpaid_bookings'],
        'details': summary
    }


def display_alerts_sidebar():
    """Display alerts in the sidebar (optional integration)"""
    summary = get_all_alerts_summary()
    
    critical = (
        summary['docs_expired'] + 
        summary['out_of_stock'] + 
        summary['bus_licenses']
    )
    
    if critical > 0:
        st.sidebar.error(f"🔴 {critical} Critical Alerts")
    
    warnings = summary['docs_expiring'] + summary['low_stock'] + summary['pending_bookings']
    
    if warnings > 0:
        st.sidebar.warning(f"🟡 {warnings} Warnings")
