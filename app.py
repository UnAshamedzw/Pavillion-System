"""
app.py - Main Application Entry Point
Pavillion Coaches Bus Management System
WITH ROLE-BASED PERMISSIONS - Menu items filtered by user permissions
"""

import streamlit as st
from database import init_database, migrate_database
from auth import (
    create_users_table, create_sessions_table, create_permissions_tables,
    initialize_predefined_roles, login_page, logout, restore_session,
    has_permission, can_access_page, get_accessible_menu_items, get_user_role
)
from pages_operations import (
    income_entry_page, 
    maintenance_entry_page, 
    revenue_history_page,
    import_data_page,
    dashboard_page,
    routes_assignments_page
)
from pages_hr import (
    employee_management_page,
    employee_performance_page,
    payroll_management_page,
    leave_management_page,
    disciplinary_records_page,
    get_expiring_documents, 
    display_document_expiry_alerts
)
from pages_users import user_management_page, my_profile_page, role_management_page
from pages_audit import activity_log_page, user_activity_dashboard
from pages_bus_analysis import bus_analysis_page
from pages_performance_metrics import performance_metrics_page
from fleet_management_page import fleet_management_page, show_expiry_alerts
from pages_fuel import fuel_entry_page, fuel_analysis_page
from pages_backup import backup_export_page
from pages_trips import trip_analysis_page
from pages_route_profitability import route_profitability_page
from pages_driver_performance import driver_scoring_page
from pages_documents import document_management_page
from pages_customers import customer_management_page
from pages_inventory import inventory_management_page
from pages_alerts import alerts_dashboard_page, get_dashboard_alerts_widget
from pages_expenses import general_expenses_page
from pages_profit_loss import profit_loss_page
from pages_contracts import contract_generator_page
from pages_notifications import notification_settings_page
from pages_landing import show_landing_page, can_see_full_dashboard, FULL_DASHBOARD_ROLES
from pages_payroll import payroll_processing_page
from pages_reconciliation import daily_reconciliation_page
from pages_employee_portal import employee_portal_page
from pages_approvals import approvals_center_page
from pages_cash_left import cash_left_page
from mobile_styles import apply_mobile_styles
import base64
from pathlib import Path


def get_base64_image(image_path):
    """Convert image to base64 for display"""
    try:
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return None


def main():
    """Main application entry point"""
    
    # Page configuration
    st.set_page_config(
        page_title="Pavillion Coaches - Bus Management System",
        page_icon="🚌",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Apply mobile-responsive styles
    apply_mobile_styles()
    
    # Initialize database only once per session
    if 'initialized' not in st.session_state:
        init_database()
        migrate_database()
        create_users_table()
        create_sessions_table()
        create_permissions_tables()
        initialize_predefined_roles()
        st.session_state.initialized = True
    
    # Try to restore session from query params (persistent login)
    restore_session()
    
    # Check if employee portal mode is requested
    if st.session_state.get('show_employee_portal', False):
        employee_portal_page()
        
        # Add back button to return to main login
        st.markdown("---")
        if st.button("← Back to Main Login"):
            st.session_state['show_employee_portal'] = False
            if 'portal_employee' in st.session_state:
                del st.session_state['portal_employee']
            st.rerun()
        return
    
    # Check authentication
    if not st.session_state.get('authenticated', False):
        login_page()
        return
    
    # Custom CSS with Pavillion Coaches branding colors
    st.markdown("""
        <style>
        /* Pavillion Coaches Brand Colors */
        :root {
            --pavillion-gold: #E6A918;
            --pavillion-green: #1B4D3E;
            --pavillion-dark: #2c3e50;
            --pavillion-light: #f8f9fa;
        }
        
        .main {
            padding: 0rem 1rem;
        }
        
        h1 {
            color: var(--pavillion-green);
            padding-bottom: 1rem;
        }
        
        h2 {
            color: var(--pavillion-dark);
        }
        
        /* Branded metrics */
        .stMetric {
            background-color: var(--pavillion-light);
            border-radius: 8px;
            padding: 0.5rem;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background-color: var(--pavillion-light);
        }
        
        /* Header styling */
        .brand-header {
            text-align: center;
            padding: 1rem 0;
            border-bottom: 3px solid var(--pavillion-gold);
            margin-bottom: 1rem;
        }
        
        .brand-header h1 {
            color: var(--pavillion-green);
            margin: 0;
        }
        
        .brand-header p {
            color: var(--pavillion-gold);
            font-style: italic;
            margin: 0.5rem 0 0 0;
        }
        
        /* Permission denied styling */
        .access-denied {
            text-align: center;
            padding: 2rem;
            background-color: #fee;
            border-radius: 8px;
            margin: 1rem 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Get current user
    user = st.session_state['user']
    
    # Sidebar with logo
    logo_path = Path("pavillion_logo.png")
    if logo_path.exists():
        logo_b64 = get_base64_image(str(logo_path))
        if logo_b64:
            st.sidebar.markdown(
                f"""
                <div style="text-align: center; padding: 1rem 0;">
                    <img src="data:image/png;base64,{logo_b64}" style="max-width: 180px;">
                    <p style="color: #E6A918; margin: 0.5rem 0 0 0; font-style: italic;">smart travel</p>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.sidebar.markdown("""
            <div style="text-align: center; padding: 1rem 0;">
                <h2 style="color: #1B4D3E; margin: 0;">Pavillion Coaches</h2>
                <p style="color: #E6A918; margin: 0.5rem 0 0 0; font-style: italic;">smart travel</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**👤 {user['full_name']}**")
    st.sidebar.markdown(f"*{user['role']}*")
    st.sidebar.markdown("---")
    
    # Initialize default page in session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 Home"
    
    # Check for navigation requests from landing pages
    if 'navigate_to' in st.session_state:
        st.session_state.current_page = st.session_state.navigate_to
        del st.session_state.navigate_to
        st.rerun()
    
    # Home button at top of sidebar
    if st.sidebar.button("🏠 Home", use_container_width=True):
        st.session_state.current_page = "🏠 Home"
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Main menu selection
    menu_section = st.sidebar.radio(
        "Main Menu:",
        ["🚌 Operations", "👥 HR Management", "📊 Analytics", "⚙️ System"]
    )
    
    st.sidebar.markdown("---")
    
    # Define all menu items with permission requirements
    # Only show full dashboard to authorized roles
    user_role = get_user_role()
    
    operations_items = []
    if user_role in FULL_DASHBOARD_ROLES:
        operations_items.append("📈 Operations Dashboard")
    
    operations_items.extend([
        "🔔 Alerts",
        "🚌 Trip & Income Entry",
        "💵 Cash Left at Rank",
        "📋 Daily Reconciliation",
        "👥 Customers & Bookings",
        "🔧 Maintenance Entry",
        "⛽ Fuel Entry",
        "💸 General Expenses",
        "📦 Inventory",
        "📄 Documents",
        "📥 Import from Excel",
        "💰 Revenue History",
        "🚌 Fleet Management",
        "🛣️ Routes & Assignments"
    ])
    
    hr_items = [
        "✅ Approvals Center",
        "👥 Employee Management",
        "📝 Contract Generator",
        "📊 Employee Performance",
        "💰 Payroll & Payslips",
        "📅 Leave Management",
        "⚠️ Disciplinary Records"
    ]
    
    analytics_items = [
        "🚌 Bus-by-Bus Analysis",
        "📈 Performance Metrics",
        "⛽ Fuel Analysis",
        "🚌 Trip Analysis",
        "💰 Route Profitability",
        "🏆 Driver Scoring",
        "📊 Profit & Loss"
    ]
    
    system_items = ["👤 My Profile", "📊 My Activity"]
    
    # Add admin-only items if user has permissions
    if has_permission('export_income') or has_permission('generate_reports'):
        system_items.append("💾 Backup & Export")
    if has_permission('view_users'):
        system_items.append("👥 User Management")
    if has_permission('manage_roles'):
        system_items.append("🔐 Role Management")
    if has_permission('view_audit_logs'):
        system_items.append("📜 Activity Log")
    if has_permission('manage_roles'):  # Admin only
        system_items.append("🔔 Notification Settings")
    
    # Filter menu items based on permissions
    if menu_section == "🚌 Operations":
        available_items = get_accessible_menu_items(operations_items)
        if available_items:
            page = st.sidebar.radio("Operations:", available_items)
        else:
            page = None
            st.sidebar.warning("No accessible pages in this section")
            
    elif menu_section == "👥 HR Management":
        available_items = get_accessible_menu_items(hr_items)
        if available_items:
            page = st.sidebar.radio("HR Management:", available_items)
        else:
            page = None
            st.sidebar.warning("No accessible pages in this section")
            
    elif menu_section == "📊 Analytics":
        available_items = get_accessible_menu_items(analytics_items)
        if available_items:
            page = st.sidebar.radio("Analytics:", available_items)
        else:
            page = None
            st.sidebar.warning("No accessible pages in this section")
            
    else:  # System
        page = st.sidebar.radio("System:", system_items)
    
    st.sidebar.markdown("---")
    
    # Info boxes with branded colors
    if menu_section == "🚌 Operations":
        st.sidebar.info("""
        **Operations Features:**
        - 📈 Analytics dashboard
        - 📊 Track daily revenue
        - 🔧 Record maintenance
        - 📥 Bulk import from Excel
        - 💰 Revenue history
        - 🚌 Fleet management
        - 🛣️ Routes & assignments
        """)
    elif menu_section == "👥 HR Management":
        st.sidebar.info("""
        **HR Features:**
        - 👥 Employee database
        - 📊 Performance metrics
        - 💰 Payroll & payslips
        - 📅 Leave management
        - ⚠️ Disciplinary records
        """)
    elif menu_section == "📊 Analytics":
        st.sidebar.info("""
        **Analytics Features:**
        - 🚌 Bus-by-bus analysis
        - 💰 Revenue vs expenses
        - 📊 Profit/loss tracking
        - 📈 Performance trends
        """)
    else:
        st.sidebar.info(f"""
        **User Info:**
        - **Name:** {user['full_name']}
        - **Role:** {user['role']}
        - **Username:** {user['username']}
        """)
    
    # Logout button
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", width="stretch"):
        logout()
    
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2025 Pavillion Coaches")
    st.sidebar.caption("🔒 Secure | 📊 Audited | 🚀 Efficient")
    st.sidebar.caption("*smart travel*")
    
    # Main content area with branded header
    st.markdown("""
        <div class="brand-header">
            <h1>Pavillion Coaches</h1>
            <p>Bus Management System</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Handle Home page - show role-based landing page
    if page == "🏠 Home" or page is None:
        show_landing_page()
        return
    
    # Show document expiry alerts on Operations Dashboard page
    if page == "📈 Operations Dashboard":
        try:
            show_expiry_alerts()
        except Exception:
            pass
        
        try:
            display_document_expiry_alerts()
        except Exception:
            pass
        
        st.markdown("---")
    
    # Route to appropriate page with permission check
    if page == "🚌 Trip & Income Entry":
        if can_access_page(page):
            income_entry_page()
        else:
            show_access_denied(page)
    elif page == "💵 Cash Left at Rank":
        if can_access_page(page):
            cash_left_page()
        else:
            show_access_denied(page)
    elif page == "📋 Daily Reconciliation":
        if can_access_page(page):
            daily_reconciliation_page()
        else:
            show_access_denied(page)
    elif page == "🔧 Maintenance Entry":
        if can_access_page(page):
            maintenance_entry_page()
        else:
            show_access_denied(page)
    elif page == "📥 Import from Excel":
        if can_access_page(page):
            import_data_page()
        else:
            show_access_denied(page)
    elif page == "💰 Revenue History":
        if can_access_page(page):
            revenue_history_page()
        else:
            show_access_denied(page)
    elif page == "📈 Operations Dashboard":
        # Only authorized roles can see full dashboard
        if get_user_role() in FULL_DASHBOARD_ROLES and can_access_page(page):
            dashboard_page()
        else:
            show_access_denied(page)
    elif page == "🔔 Alerts":
        if can_access_page(page):
            alerts_dashboard_page()
        else:
            show_access_denied(page)
    elif page == "🚌 Fleet Management":
        if can_access_page(page):
            fleet_management_page()
        else:
            show_access_denied(page)
    elif page == "🛣️ Routes & Assignments":
        if can_access_page(page):
            routes_assignments_page()
        else:
            show_access_denied(page)
    elif page == "👥 Employee Management":
        if can_access_page(page):
            employee_management_page()
        else:
            show_access_denied(page)
    elif page == "✅ Approvals Center":
        if can_access_page(page):
            approvals_center_page()
        else:
            show_access_denied(page)
    elif page == "📝 Contract Generator":
        if can_access_page(page):
            contract_generator_page()
        else:
            show_access_denied(page)
    elif page == "📊 Employee Performance":
        if can_access_page(page):
            employee_performance_page()
        else:
            show_access_denied(page)
    elif page == "💰 Payroll & Payslips":
        if can_access_page(page):
            payroll_processing_page()
        else:
            show_access_denied(page)
    elif page == "📅 Leave Management":
        if can_access_page(page):
            leave_management_page()
        else:
            show_access_denied(page)
    elif page == "⚠️ Disciplinary Records":
        if can_access_page(page):
            disciplinary_records_page()
        else:
            show_access_denied(page)
    elif page == "🚌 Bus-by-Bus Analysis":
        if can_access_page(page):
            bus_analysis_page()
        else:
            show_access_denied(page)
    elif page == "📈 Performance Metrics":
        if can_access_page(page):
            performance_metrics_page()
        else:
            show_access_denied(page)
    elif page == "⛽ Fuel Entry":
        if can_access_page(page):
            fuel_entry_page()
        else:
            show_access_denied(page)
    elif page == "⛽ Fuel Analysis":
        if can_access_page(page):
            fuel_analysis_page()
        else:
            show_access_denied(page)
    elif page == "💸 General Expenses":
        if can_access_page(page):
            general_expenses_page()
        else:
            show_access_denied(page)
    elif page == "📄 Documents":
        if can_access_page(page):
            document_management_page()
        else:
            show_access_denied(page)
    elif page == "📦 Inventory":
        if can_access_page(page):
            inventory_management_page()
        else:
            show_access_denied(page)
    elif page == "👥 Customers & Bookings":
        if can_access_page(page):
            customer_management_page()
        else:
            show_access_denied(page)
    elif page == "🚌 Trip Analysis":
        if can_access_page(page):
            trip_analysis_page()
        else:
            show_access_denied(page)
    elif page == "💰 Route Profitability":
        if can_access_page(page):
            route_profitability_page()
        else:
            show_access_denied(page)
    elif page == "🏆 Driver Scoring":
        if can_access_page(page):
            driver_scoring_page()
        else:
            show_access_denied(page)
    elif page == "📊 Profit & Loss":
        if can_access_page(page):
            profit_loss_page()
        else:
            show_access_denied(page)
    elif page == "👤 My Profile":
        my_profile_page()
    elif page == "📊 My Activity":
        user_activity_dashboard()
    elif page == "💾 Backup & Export":
        if has_permission('export_income') or has_permission('generate_reports'):
            backup_export_page()
        else:
            show_access_denied(page)
    elif page == "👥 User Management":
        if has_permission('view_users'):
            user_management_page()
        else:
            show_access_denied(page)
    elif page == "🔐 Role Management":
        if has_permission('manage_roles'):
            role_management_page()
        else:
            show_access_denied(page)
    elif page == "📜 Activity Log":
        if has_permission('view_audit_logs'):
            activity_log_page()
        else:
            show_access_denied(page)
    elif page == "🔔 Notification Settings":
        if has_permission('manage_roles'):
            notification_settings_page()
        else:
            show_access_denied(page)


def show_access_denied(page_name: str):
    """Display access denied message"""
    st.error("🚫 Access Denied")
    st.markdown(f"""
        <div class="access-denied">
            <h3>You don't have permission to access this page</h3>
            <p><strong>Page:</strong> {page_name}</p>
            <p>Please contact your administrator if you need access to this feature.</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()