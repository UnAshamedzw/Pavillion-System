"""
pages_landing.py - Role-Based Landing Pages
Pavillion Coaches Bus Management System
Each role gets a customized, secure landing page with relevant information only
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES
from auth import has_permission, get_user_role


# =============================================================================
# ROLE-TO-LANDING PAGE MAPPING
# =============================================================================

# Define which landing page each role should see
ROLE_LANDING_PAGES = {
    'System Admin': 'admin_dashboard',
    'Director': 'executive_dashboard',
    'HR Manager': 'hr_dashboard',
    'Operations Manager': 'operations_dashboard',
    'Finance Manager': 'finance_dashboard',
    'Route Supervisor': 'supervisor_dashboard',
    'Workshop Supervisor': 'workshop_dashboard',
    'Stores Supervisor': 'stores_dashboard',
    'Payroll Officer': 'payroll_dashboard',
    'Data Entry Clerk': 'clerk_dashboard',
    'Viewer': 'viewer_dashboard',
}

# Define which roles can see company-wide financial data
FINANCIAL_DATA_ROLES = ['System Admin', 'Director', 'Finance Manager']

# Define which roles can see the full operations dashboard
FULL_DASHBOARD_ROLES = ['System Admin', 'Director', 'Operations Manager', 'Finance Manager']


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_landing_page_for_role(role):
    """Get the appropriate landing page function for a role"""
    return ROLE_LANDING_PAGES.get(role, 'viewer_dashboard')


def can_see_financial_data():
    """Check if current user can see company-wide financial data"""
    role = get_user_role()
    return role in FINANCIAL_DATA_ROLES


def can_see_full_dashboard():
    """Check if current user can see the full operations dashboard"""
    role = get_user_role()
    return role in FULL_DASHBOARD_ROLES


def get_greeting():
    """Get time-appropriate greeting"""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"


def get_user_stats(employee_id=None):
    """Get quick stats for the current user"""
    conn = get_connection()
    stats = {}
    
    try:
        # If employee_id provided, get their specific stats
        if employee_id:
            # Get trips/income entered by this user today
            today = datetime.now().strftime('%Y-%m-%d')
            df = pd.read_sql_query(f"""
                SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
                FROM income WHERE date = '{today}'
            """, get_engine())
            stats['today_entries'] = int(df['count'].iloc[0]) if not df.empty else 0
            stats['today_total'] = float(df['total'].iloc[0]) if not df.empty else 0
    except:
        pass
    finally:
        conn.close()
    
    return stats


# =============================================================================
# LANDING PAGE: EXECUTIVE DASHBOARD (Director)
# =============================================================================

def executive_dashboard():
    """Landing page for Directors - High-level KPIs and summaries"""
    
    user = st.session_state.get('user', {})
    st.title(f"👔 {get_greeting()}, {user.get('full_name', 'Director')}")
    st.markdown("### Executive Overview")
    
    conn = get_connection()
    
    try:
        # Date ranges
        today = datetime.now().date()
        month_start = today.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        
        # This month's revenue
        revenue_df = pd.read_sql_query(f"""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM income WHERE date >= '{month_start}'
        """, get_engine())
        month_revenue = float(revenue_df['total'].iloc[0]) if not revenue_df.empty else 0
        
        # This month's expenses (maintenance + general)
        maint_df = pd.read_sql_query(f"""
            SELECT COALESCE(SUM(cost), 0) as total
            FROM maintenance WHERE date >= '{month_start}'
        """, get_engine())
        month_maintenance = float(maint_df['total'].iloc[0]) if not maint_df.empty else 0
        
        try:
            expense_df = pd.read_sql_query(f"""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM general_expenses WHERE expense_date >= '{month_start}'
            """, get_engine())
            month_expenses = float(expense_df['total'].iloc[0]) if not expense_df.empty else 0
        except:
            month_expenses = 0
        
        total_expenses = month_maintenance + month_expenses
        month_profit = month_revenue - total_expenses
        
        # Fleet status
        fleet_df = pd.read_sql_query("""
            SELECT status, COUNT(*) as count FROM buses GROUP BY status
        """, get_engine())
        active_buses = int(fleet_df[fleet_df['status'] == 'Active']['count'].sum()) if not fleet_df.empty else 0
        
        # Employee count
        emp_df = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM employees WHERE status = 'Active'
        """, get_engine())
        active_employees = int(emp_df['count'].iloc[0]) if not emp_df.empty else 0
        
    except Exception as e:
        month_revenue = month_profit = total_expenses = 0
        active_buses = active_employees = 0
    finally:
        conn.close()
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📈 Month Revenue",
            f"${month_revenue:,.0f}",
            help="Total revenue this month"
        )
    
    with col2:
        st.metric(
            "💰 Month Profit",
            f"${month_profit:,.0f}",
            delta=f"${month_profit:,.0f}" if month_profit > 0 else None,
            delta_color="normal" if month_profit > 0 else "inverse"
        )
    
    with col3:
        st.metric(
            "🚌 Active Fleet",
            f"{active_buses} buses"
        )
    
    with col4:
        st.metric(
            "👥 Employees",
            f"{active_employees}"
        )
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Full Dashboard", use_container_width=True):
            st.session_state['navigate_to'] = '📈 Operations Dashboard'
            st.rerun()
    
    with col2:
        if st.button("💰 Profit & Loss", use_container_width=True):
            st.session_state['navigate_to'] = '💰 Profit & Loss'
            st.rerun()
    
    with col3:
        if st.button("👥 HR Overview", use_container_width=True):
            st.session_state['navigate_to'] = '👤 Employee Management'
            st.rerun()
    
    with col4:
        if st.button("🚨 View Alerts", use_container_width=True):
            st.session_state['navigate_to'] = '🚨 Alerts Dashboard'
            st.rerun()
    
    # Critical Alerts Summary
    st.markdown("---")
    st.subheader("🚨 Items Requiring Attention")
    show_critical_alerts_summary()


# =============================================================================
# LANDING PAGE: OPERATIONS DASHBOARD (Operations Manager)
# =============================================================================

def operations_dashboard():
    """Landing page for Operations Managers - Fleet and route focus"""
    
    user = st.session_state.get('user', {})
    st.title(f"🚌 {get_greeting()}, {user.get('full_name', 'Manager')}")
    st.markdown("### Operations Overview")
    
    conn = get_connection()
    
    try:
        today = datetime.now().date()
        
        # Today's revenue
        revenue_df = pd.read_sql_query(f"""
            SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as trips
            FROM income WHERE date = '{today}'
        """, get_engine())
        today_revenue = float(revenue_df['total'].iloc[0]) if not revenue_df.empty else 0
        today_trips = int(revenue_df['trips'].iloc[0]) if not revenue_df.empty else 0
        
        # Active buses
        fleet_df = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM buses WHERE status = 'Active'
        """, get_engine())
        active_buses = int(fleet_df['count'].iloc[0]) if not fleet_df.empty else 0
        
        # Pending maintenance
        maint_df = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM maintenance WHERE status = 'Scheduled'
        """, get_engine())
        pending_maint = int(maint_df['count'].iloc[0]) if not maint_df.empty else 0
        
    except:
        today_revenue = today_trips = active_buses = pending_maint = 0
    finally:
        conn.close()
    
    # KPI Cards - Operations focused (no company-wide financials)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📈 Today's Revenue", f"${today_revenue:,.0f}")
    
    with col2:
        st.metric("🚌 Active Buses", f"{active_buses}")
    
    with col3:
        st.metric("🚗 Today's Trips", f"{today_trips}")
    
    with col4:
        st.metric("🔧 Pending Maintenance", f"{pending_maint}")
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("➕ Add Income", use_container_width=True):
            st.session_state['navigate_to'] = '📊 Income Entry'
            st.rerun()
    
    with col2:
        if st.button("🔧 Add Maintenance", use_container_width=True):
            st.session_state['navigate_to'] = '🔧 Maintenance Entry'
            st.rerun()
    
    with col3:
        if st.button("⛽ Add Fuel", use_container_width=True):
            st.session_state['navigate_to'] = '⛽ Fuel Entry'
            st.rerun()
    
    with col4:
        if st.button("🚌 Fleet Status", use_container_width=True):
            st.session_state['navigate_to'] = '🚌 Fleet Management'
            st.rerun()
    
    # Alerts
    st.markdown("---")
    st.subheader("🚨 Operations Alerts")
    show_operations_alerts()


# =============================================================================
# LANDING PAGE: HR DASHBOARD (HR Manager)
# =============================================================================

def hr_dashboard():
    """Landing page for HR Managers - Employee focus"""
    
    user = st.session_state.get('user', {})
    st.title(f"👥 {get_greeting()}, {user.get('full_name', 'HR Manager')}")
    st.markdown("### Human Resources Overview")
    
    conn = get_connection()
    
    try:
        # Employee stats
        emp_df = pd.read_sql_query("""
            SELECT status, COUNT(*) as count FROM employees GROUP BY status
        """, get_engine())
        active_employees = int(emp_df[emp_df['status'] == 'Active']['count'].sum()) if not emp_df.empty else 0
        
        # Leave requests pending
        try:
            leave_df = pd.read_sql_query("""
                SELECT COUNT(*) as count FROM leave_requests WHERE status = 'Pending'
            """, get_engine())
            pending_leave = int(leave_df['count'].iloc[0]) if not leave_df.empty else 0
        except:
            pending_leave = 0
        
        # Expiring documents
        today = datetime.now().date()
        threshold = today + timedelta(days=30)
        doc_df = pd.read_sql_query(f"""
            SELECT COUNT(*) as count FROM employees 
            WHERE status = 'Active' AND (
                license_expiry <= '{threshold}' OR
                medical_cert_expiry <= '{threshold}' OR
                defensive_driving_expiry <= '{threshold}'
            )
        """, get_engine())
        expiring_docs = int(doc_df['count'].iloc[0]) if not doc_df.empty else 0
        
    except:
        active_employees = pending_leave = expiring_docs = 0
    finally:
        conn.close()
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Active Employees", f"{active_employees}")
    
    with col2:
        st.metric("📅 Pending Leave", f"{pending_leave}")
    
    with col3:
        st.metric("📄 Expiring Docs", f"{expiring_docs}")
    
    with col4:
        st.metric("📊 This Month", "View Reports")
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("➕ Add Employee", use_container_width=True):
            st.session_state['navigate_to'] = '👤 Employee Management'
            st.rerun()
    
    with col2:
        if st.button("📅 Leave Requests", use_container_width=True):
            st.session_state['navigate_to'] = '📅 Leave Management'
            st.rerun()
    
    with col3:
        if st.button("📝 Contracts", use_container_width=True):
            st.session_state['navigate_to'] = '📝 Contract Generator'
            st.rerun()
    
    with col4:
        if st.button("💰 Payroll", use_container_width=True):
            st.session_state['navigate_to'] = '💰 Payroll Management'
            st.rerun()
    
    # Alerts
    st.markdown("---")
    st.subheader("🚨 HR Alerts")
    show_hr_alerts()


# =============================================================================
# LANDING PAGE: FINANCE DASHBOARD (Finance Manager)
# =============================================================================

def finance_dashboard():
    """Landing page for Finance Managers - Financial focus with full data access"""
    
    user = st.session_state.get('user', {})
    st.title(f"💰 {get_greeting()}, {user.get('full_name', 'Finance Manager')}")
    st.markdown("### Financial Overview")
    
    conn = get_connection()
    
    try:
        today = datetime.now().date()
        month_start = today.replace(day=1)
        
        # This month's revenue
        revenue_df = pd.read_sql_query(f"""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM income WHERE date >= '{month_start}'
        """, get_engine())
        month_revenue = float(revenue_df['total'].iloc[0]) if not revenue_df.empty else 0
        
        # This month's expenses
        maint_df = pd.read_sql_query(f"""
            SELECT COALESCE(SUM(cost), 0) as total
            FROM maintenance WHERE date >= '{month_start}'
        """, get_engine())
        month_maintenance = float(maint_df['total'].iloc[0]) if not maint_df.empty else 0
        
        try:
            expense_df = pd.read_sql_query(f"""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM general_expenses WHERE expense_date >= '{month_start}'
            """, get_engine())
            month_expenses = float(expense_df['total'].iloc[0]) if not expense_df.empty else 0
        except:
            month_expenses = 0
        
        # Unpaid expenses
        try:
            unpaid_df = pd.read_sql_query("""
                SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
                FROM general_expenses WHERE payment_status IN ('Unpaid', 'Pending Approval')
            """, get_engine())
            unpaid_count = int(unpaid_df['count'].iloc[0]) if not unpaid_df.empty else 0
            unpaid_total = float(unpaid_df['total'].iloc[0]) if not unpaid_df.empty else 0
        except:
            unpaid_count = unpaid_total = 0
        
        total_expenses = month_maintenance + month_expenses
        month_profit = month_revenue - total_expenses
        
    except:
        month_revenue = month_maintenance = month_expenses = month_profit = 0
        unpaid_count = unpaid_total = 0
    finally:
        conn.close()
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📈 Month Revenue", f"${month_revenue:,.0f}")
    
    with col2:
        st.metric("📉 Month Expenses", f"${total_expenses:,.0f}")
    
    with col3:
        st.metric(
            "💰 Month Profit",
            f"${month_profit:,.0f}",
            delta_color="normal" if month_profit > 0 else "inverse"
        )
    
    with col4:
        st.metric("⚠️ Unpaid Expenses", f"{unpaid_count} (${unpaid_total:,.0f})")
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💰 Profit & Loss", use_container_width=True):
            st.session_state['navigate_to'] = '💰 Profit & Loss'
            st.rerun()
    
    with col2:
        if st.button("💸 Expenses", use_container_width=True):
            st.session_state['navigate_to'] = '💸 General Expenses'
            st.rerun()
    
    with col3:
        if st.button("💰 Payroll", use_container_width=True):
            st.session_state['navigate_to'] = '💰 Payroll Management'
            st.rerun()
    
    with col4:
        if st.button("📊 Revenue History", use_container_width=True):
            st.session_state['navigate_to'] = '💰 Revenue History'
            st.rerun()


# =============================================================================
# LANDING PAGE: SUPERVISOR DASHBOARD (Route/Workshop Supervisors)
# =============================================================================

def supervisor_dashboard():
    """Landing page for Route Supervisors - Daily operations focus"""
    
    user = st.session_state.get('user', {})
    st.title(f"🚌 {get_greeting()}, {user.get('full_name', 'Supervisor')}")
    st.markdown("### Daily Operations")
    
    conn = get_connection()
    
    try:
        today = datetime.now().date()
        
        # Today's stats
        revenue_df = pd.read_sql_query(f"""
            SELECT COUNT(*) as trips, COALESCE(SUM(amount), 0) as total
            FROM income WHERE date = '{today}'
        """, get_engine())
        today_trips = int(revenue_df['trips'].iloc[0]) if not revenue_df.empty else 0
        today_revenue = float(revenue_df['total'].iloc[0]) if not revenue_df.empty else 0
        
        # Active assignments
        assign_df = pd.read_sql_query(f"""
            SELECT COUNT(*) as count FROM bus_assignments 
            WHERE assignment_date = '{today}'
        """, get_engine())
        today_assignments = int(assign_df['count'].iloc[0]) if not assign_df.empty else 0
        
    except:
        today_trips = today_revenue = today_assignments = 0
    finally:
        conn.close()
    
    # KPI Cards - Limited view (no company-wide financials)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🚗 Today's Trips", f"{today_trips}")
    
    with col2:
        st.metric("📈 Today's Collection", f"${today_revenue:,.0f}")
    
    with col3:
        st.metric("📋 Assignments", f"{today_assignments}")
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Record Income", use_container_width=True, type="primary"):
            st.session_state['navigate_to'] = '📊 Income Entry'
            st.rerun()
    
    with col2:
        if st.button("📋 Assignments", use_container_width=True):
            st.session_state['navigate_to'] = '🛣️ Routes & Assignments'
            st.rerun()
    
    with col3:
        if st.button("⛽ Fuel Entry", use_container_width=True):
            st.session_state['navigate_to'] = '⛽ Fuel Entry'
            st.rerun()


def workshop_dashboard():
    """Landing page for Workshop Supervisors - Maintenance focus"""
    
    user = st.session_state.get('user', {})
    st.title(f"🔧 {get_greeting()}, {user.get('full_name', 'Supervisor')}")
    st.markdown("### Workshop Overview")
    
    conn = get_connection()
    
    try:
        # Pending maintenance
        maint_df = pd.read_sql_query("""
            SELECT status, COUNT(*) as count FROM maintenance GROUP BY status
        """, get_engine())
        scheduled = int(maint_df[maint_df['status'] == 'Scheduled']['count'].sum()) if not maint_df.empty else 0
        in_progress = int(maint_df[maint_df['status'] == 'In Progress']['count'].sum()) if not maint_df.empty else 0
        
        # Low inventory
        try:
            inv_df = pd.read_sql_query("""
                SELECT COUNT(*) as count FROM inventory WHERE quantity <= minimum_stock
            """, get_engine())
            low_stock = int(inv_df['count'].iloc[0]) if not inv_df.empty else 0
        except:
            low_stock = 0
        
    except:
        scheduled = in_progress = low_stock = 0
    finally:
        conn.close()
    
    # KPI Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📋 Scheduled", f"{scheduled}")
    
    with col2:
        st.metric("🔧 In Progress", f"{in_progress}")
    
    with col3:
        st.metric("📦 Low Stock Items", f"{low_stock}")
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Add Maintenance", use_container_width=True, type="primary"):
            st.session_state['navigate_to'] = '🔧 Maintenance Entry'
            st.rerun()
    
    with col2:
        if st.button("📦 Inventory", use_container_width=True):
            st.session_state['navigate_to'] = '📦 Inventory'
            st.rerun()
    
    with col3:
        if st.button("🚌 Fleet Status", use_container_width=True):
            st.session_state['navigate_to'] = '🚌 Fleet Management'
            st.rerun()


# =============================================================================
# LANDING PAGE: STORES SUPERVISOR (Inventory focus)
# =============================================================================

def stores_dashboard():
    """Landing page for Stores Supervisors - Inventory and stock focus"""
    
    user = st.session_state.get('user', {})
    st.title(f"📦 {get_greeting()}, {user.get('full_name', 'Stores Supervisor')}")
    st.markdown("### Stores & Inventory Overview")
    
    conn = get_connection()
    
    try:
        # Total inventory items
        try:
            total_df = pd.read_sql_query("""
                SELECT COUNT(*) as count FROM inventory
            """, get_engine())
            total_items = int(total_df['count'].iloc[0]) if not total_df.empty else 0
        except:
            total_items = 0
        
        # Low stock items
        try:
            low_df = pd.read_sql_query("""
                SELECT COUNT(*) as count FROM inventory WHERE quantity <= minimum_stock AND quantity > 0
            """, get_engine())
            low_stock = int(low_df['count'].iloc[0]) if not low_df.empty else 0
        except:
            low_stock = 0
        
        # Out of stock items
        try:
            out_df = pd.read_sql_query("""
                SELECT COUNT(*) as count FROM inventory WHERE quantity = 0
            """, get_engine())
            out_of_stock = int(out_df['count'].iloc[0]) if not out_df.empty else 0
        except:
            out_of_stock = 0
        
        # Total stock value
        try:
            value_df = pd.read_sql_query("""
                SELECT COALESCE(SUM(quantity * unit_cost), 0) as total FROM inventory
            """, get_engine())
            stock_value = float(value_df['total'].iloc[0]) if not value_df.empty else 0
        except:
            stock_value = 0
        
    except:
        total_items = low_stock = out_of_stock = 0
        stock_value = 0
    finally:
        conn.close()
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📦 Total Items", f"{total_items}")
    
    with col2:
        st.metric("⚠️ Low Stock", f"{low_stock}")
    
    with col3:
        st.metric("🚫 Out of Stock", f"{out_of_stock}")
    
    with col4:
        st.metric("💰 Stock Value", f"${stock_value:,.0f}")
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📦 Manage Inventory", use_container_width=True, type="primary"):
            st.session_state['navigate_to'] = '📦 Inventory'
            st.rerun()
    
    with col2:
        if st.button("➕ Add Stock", use_container_width=True):
            st.session_state['navigate_to'] = '📦 Inventory'
            st.rerun()
    
    with col3:
        if st.button("📄 View Documents", use_container_width=True):
            st.session_state['navigate_to'] = '📄 Documents'
            st.rerun()
    
    # Alerts
    st.markdown("---")
    st.subheader("🚨 Inventory Alerts")
    show_inventory_alerts()


# =============================================================================
# LANDING PAGE: CLERK DASHBOARD (Data Entry Clerk)
# =============================================================================

def clerk_dashboard():
    """Landing page for Data Entry Clerks - Simple, task-focused"""
    
    user = st.session_state.get('user', {})
    st.title(f"📝 {get_greeting()}, {user.get('full_name', 'User')}")
    st.markdown("### Your Tasks")
    
    # Simple, focused interface
    st.info("Select a task below to get started")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Data Entry")
        if st.button("➕ Add Income Record", use_container_width=True, type="primary"):
            st.session_state['navigate_to'] = '📊 Income Entry'
            st.rerun()
        
        if st.button("🔧 Add Maintenance", use_container_width=True):
            st.session_state['navigate_to'] = '🔧 Maintenance Entry'
            st.rerun()
        
        if st.button("⛽ Add Fuel Record", use_container_width=True):
            st.session_state['navigate_to'] = '⛽ Fuel Entry'
            st.rerun()
    
    with col2:
        st.subheader("📋 View Records")
        if st.button("💰 View Revenue History", use_container_width=True):
            st.session_state['navigate_to'] = '💰 Revenue History'
            st.rerun()
        
        if st.button("🚌 View Fleet", use_container_width=True):
            st.session_state['navigate_to'] = '🚌 Fleet Management'
            st.rerun()


# =============================================================================
# LANDING PAGE: PAYROLL OFFICER
# =============================================================================

def payroll_dashboard():
    """Landing page for Payroll Officers"""
    
    user = st.session_state.get('user', {})
    st.title(f"💰 {get_greeting()}, {user.get('full_name', 'User')}")
    st.markdown("### Payroll Overview")
    
    conn = get_connection()
    
    try:
        # Employee count
        emp_df = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM employees WHERE status = 'Active'
        """, get_engine())
        active_employees = int(emp_df['count'].iloc[0]) if not emp_df.empty else 0
    except:
        active_employees = 0
    finally:
        conn.close()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("👥 Active Employees", f"{active_employees}")
    
    with col2:
        st.metric("📅 Current Period", datetime.now().strftime("%B %Y"))
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💰 Process Payroll", use_container_width=True, type="primary"):
            st.session_state['navigate_to'] = '💰 Payroll Management'
            st.rerun()
    
    with col2:
        if st.button("👥 View Employees", use_container_width=True):
            st.session_state['navigate_to'] = '👤 Employee Management'
            st.rerun()


# =============================================================================
# LANDING PAGE: VIEWER (Read-only users)
# =============================================================================

def viewer_dashboard():
    """Landing page for Viewers - Read-only access"""
    
    user = st.session_state.get('user', {})
    st.title(f"👁️ {get_greeting()}, {user.get('full_name', 'User')}")
    st.markdown("### View Mode")
    
    st.info("You have read-only access to the system. Select a section from the menu to view data.")
    
    st.markdown("---")
    st.subheader("📋 Available Sections")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚌 View Fleet", use_container_width=True):
            st.session_state['navigate_to'] = '🚌 Fleet Management'
            st.rerun()
    
    with col2:
        if st.button("👥 View Employees", use_container_width=True):
            st.session_state['navigate_to'] = '👤 Employee Management'
            st.rerun()


# =============================================================================
# LANDING PAGE: ADMIN DASHBOARD
# =============================================================================

def admin_dashboard():
    """Landing page for System Admins - Full system overview"""
    
    user = st.session_state.get('user', {})
    st.title(f"⚙️ {get_greeting()}, {user.get('full_name', 'Admin')}")
    st.markdown("### System Administration")
    
    conn = get_connection()
    
    try:
        # System stats
        users_df = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM users WHERE is_active = TRUE
        """, get_engine())
        active_users = int(users_df['count'].iloc[0]) if not users_df.empty else 0
        
        emp_df = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM employees WHERE status = 'Active'
        """, get_engine())
        active_employees = int(emp_df['count'].iloc[0]) if not emp_df.empty else 0
        
        buses_df = pd.read_sql_query("""
            SELECT COUNT(*) as count FROM buses WHERE status = 'Active'
        """, get_engine())
        active_buses = int(buses_df['count'].iloc[0]) if not buses_df.empty else 0
        
    except:
        active_users = active_employees = active_buses = 0
    finally:
        conn.close()
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👤 Active Users", f"{active_users}")
    
    with col2:
        st.metric("👥 Employees", f"{active_employees}")
    
    with col3:
        st.metric("🚌 Buses", f"{active_buses}")
    
    with col4:
        st.metric("⚙️ System", "Online")
    
    st.markdown("---")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📈 Full Dashboard", use_container_width=True):
            st.session_state['navigate_to'] = '📈 Operations Dashboard'
            st.rerun()
    
    with col2:
        if st.button("👥 User Management", use_container_width=True):
            st.session_state['navigate_to'] = '👥 User Management'
            st.rerun()
    
    with col3:
        if st.button("🔐 Roles", use_container_width=True):
            st.session_state['navigate_to'] = '🔐 Role Management'
            st.rerun()
    
    with col4:
        if st.button("📜 Audit Logs", use_container_width=True):
            st.session_state['navigate_to'] = '📜 Activity Log'
            st.rerun()
    
    # System Alerts
    st.markdown("---")
    st.subheader("🚨 System Alerts")
    show_critical_alerts_summary()


# =============================================================================
# ALERT SUMMARY FUNCTIONS
# =============================================================================

def show_critical_alerts_summary():
    """Show a summary of critical alerts"""
    conn = get_connection()
    
    try:
        today = datetime.now().date()
        threshold = today + timedelta(days=7)
        
        # Expiring bus documents
        bus_docs = pd.read_sql_query(f"""
            SELECT COUNT(*) as count FROM buses 
            WHERE status = 'Active' AND (
                zinara_licence_expiry <= '{threshold}' OR
                vehicle_insurance_expiry <= '{threshold}' OR
                fitness_expiry <= '{threshold}'
            )
        """, get_engine())
        bus_alerts = int(bus_docs['count'].iloc[0]) if not bus_docs.empty else 0
        
        # Expiring employee documents
        emp_docs = pd.read_sql_query(f"""
            SELECT COUNT(*) as count FROM employees 
            WHERE status = 'Active' AND (
                license_expiry <= '{threshold}' OR
                medical_cert_expiry <= '{threshold}'
            )
        """, get_engine())
        emp_alerts = int(emp_docs['count'].iloc[0]) if not emp_docs.empty else 0
        
        # Low inventory
        try:
            inv = pd.read_sql_query("""
                SELECT COUNT(*) as count FROM inventory WHERE quantity <= minimum_stock
            """, get_engine())
            inv_alerts = int(inv['count'].iloc[0]) if not inv.empty else 0
        except:
            inv_alerts = 0
        
    except:
        bus_alerts = emp_alerts = inv_alerts = 0
    finally:
        conn.close()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if bus_alerts > 0:
            st.error(f"🚗 {bus_alerts} bus document(s) expiring soon")
        else:
            st.success("🚗 Bus documents OK")
    
    with col2:
        if emp_alerts > 0:
            st.warning(f"👤 {emp_alerts} employee document(s) expiring soon")
        else:
            st.success("👤 Employee documents OK")
    
    with col3:
        if inv_alerts > 0:
            st.warning(f"📦 {inv_alerts} item(s) low in stock")
        else:
            st.success("📦 Inventory OK")


def show_operations_alerts():
    """Show operations-specific alerts"""
    show_critical_alerts_summary()


def show_hr_alerts():
    """Show HR-specific alerts"""
    conn = get_connection()
    
    try:
        today = datetime.now().date()
        threshold = today + timedelta(days=30)
        
        # Expiring documents
        emp_docs = pd.read_sql_query(f"""
            SELECT full_name, 
                   license_expiry, medical_cert_expiry, defensive_driving_expiry
            FROM employees 
            WHERE status = 'Active' AND (
                license_expiry <= '{threshold}' OR
                medical_cert_expiry <= '{threshold}' OR
                defensive_driving_expiry <= '{threshold}'
            )
            LIMIT 5
        """, get_engine())
        
        if not emp_docs.empty:
            st.warning(f"⚠️ {len(emp_docs)} employee(s) have documents expiring within 30 days")
            with st.expander("View Details"):
                st.dataframe(emp_docs, use_container_width=True)
        else:
            st.success("✅ No employee documents expiring in the next 30 days")
        
    except Exception as e:
        st.info("No alerts to display")
    finally:
        conn.close()


def show_inventory_alerts():
    """Show inventory-specific alerts"""
    conn = get_connection()
    
    try:
        # Out of stock items
        out_df = pd.read_sql_query("""
            SELECT part_name, part_number, category
            FROM inventory WHERE quantity = 0
            LIMIT 10
        """, get_engine())
        
        if not out_df.empty:
            st.error(f"🚫 {len(out_df)} item(s) are OUT OF STOCK")
            with st.expander("View Out of Stock Items"):
                st.dataframe(out_df, use_container_width=True)
        
        # Low stock items
        low_df = pd.read_sql_query("""
            SELECT part_name, part_number, quantity, minimum_stock, category
            FROM inventory WHERE quantity <= minimum_stock AND quantity > 0
            LIMIT 10
        """, get_engine())
        
        if not low_df.empty:
            st.warning(f"⚠️ {len(low_df)} item(s) are LOW IN STOCK")
            with st.expander("View Low Stock Items"):
                st.dataframe(low_df, use_container_width=True)
        
        if out_df.empty and low_df.empty:
            st.success("✅ All inventory levels are healthy")
        
    except Exception as e:
        st.info("No inventory alerts to display")
    finally:
        conn.close()


# =============================================================================
# MAIN LANDING PAGE ROUTER
# =============================================================================

def show_landing_page():
    """Show the appropriate landing page based on user role"""
    
    role = get_user_role()
    landing_page = get_landing_page_for_role(role)
    
    # Route to appropriate landing page
    if landing_page == 'admin_dashboard':
        admin_dashboard()
    elif landing_page == 'executive_dashboard':
        executive_dashboard()
    elif landing_page == 'hr_dashboard':
        hr_dashboard()
    elif landing_page == 'operations_dashboard':
        operations_dashboard()
    elif landing_page == 'finance_dashboard':
        finance_dashboard()
    elif landing_page == 'supervisor_dashboard':
        supervisor_dashboard()
    elif landing_page == 'workshop_dashboard':
        workshop_dashboard()
    elif landing_page == 'stores_dashboard':
        stores_dashboard()
    elif landing_page == 'payroll_dashboard':
        payroll_dashboard()
    elif landing_page == 'clerk_dashboard':
        clerk_dashboard()
    else:
        viewer_dashboard()