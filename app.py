"""
app.py - Main Application Entry Point
Pavillion Coaches Bus Management System
WITH ROLE-BASED PERMISSIONS - Menu items filtered by user permissions
SIMPLIFIED MENU - Consolidated pages for easier navigation
"""

import streamlit as st
from database import init_database, migrate_database
from auth import (
    create_users_table, create_sessions_table, create_permissions_tables,
    initialize_predefined_roles, login_page, logout, restore_session,
    has_permission, can_access_page, get_accessible_menu_items, get_user_role
)

# Original page imports (still needed for some direct access)
from pages_operations import dashboard_page
from pages_hr import get_expiring_documents, display_document_expiry_alerts
from pages_users import my_profile_page
from pages_backup import backup_export_page
from pages_customers import customer_management_page
from pages_contracts import contract_generator_page
from pages_landing import show_landing_page, can_see_full_dashboard, FULL_DASHBOARD_ROLES
from pages_employee_portal import employee_portal_page
from pages_approvals import approvals_center_page
from pages_alerts import alerts_dashboard_page

# NEW: Consolidated page imports
from pages_daily_ops import daily_operations_page
from pages_fleet_maintenance import fleet_maintenance_page
from pages_expenses_inventory import expenses_inventory_page
from pages_docs_import import documents_import_page
from pages_employees_consolidated import employees_consolidated_page
from pages_payroll_consolidated import payroll_consolidated_page
from pages_reports import reports_analytics_page
from pages_admin import user_management_consolidated_page, system_settings_page

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
    
    # Apply global table and metric styles
    from table_styles import apply_global_styles
    apply_global_styles()
    
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
    
    # ==========================================================================
    # SIMPLIFIED MENU STRUCTURE
    # Consolidated from 30+ items to ~15 logical groupings
    # ==========================================================================
    
    operations_items = []
    if user_role in FULL_DASHBOARD_ROLES:
        operations_items.append("Dashboard")
    
    operations_items.extend([
        "Daily Operations",      # Combines: Trip Entry, Cash Left, Reconciliation
        "Fleet & Maintenance",   # Combines: Fleet Management, Maintenance, Fuel
        "Expenses & Inventory",  # Combines: Expenses, Inventory
        "Customers & Bookings",
        "Documents & Import",    # Combines: Documents, Import from Excel
    ])
    
    hr_items = [
        "Approvals",             # Approvals Center
        "Employees",             # Combines: Employee Management, Performance, Disciplinary
        "Payroll",               # Combines: Payroll, Leave Management
        "Contracts",
    ]
    
    analytics_items = [
        "Reports & Analytics",   # Combines: All analytics into one page with tabs
    ]
    
    system_items = ["My Profile"]
    
    # Add admin-only items if user has permissions
    if has_permission('export_income') or has_permission('generate_reports'):
        system_items.append("Backup & Export")
    if has_permission('view_users') or has_permission('manage_roles'):
        system_items.append("User Management")  # Combines: Users, Roles, Activity Log
    if has_permission('manage_roles'):
        system_items.append("System Settings")  # Combines: Notifications, Settings
    
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
    # ==========================================================================
    # SIMPLIFIED ROUTING - Consolidated Pages
    # ==========================================================================
    
    if page == "Dashboard":
        if get_user_role() in FULL_DASHBOARD_ROLES:
            dashboard_page()
        else:
            show_access_denied(page)
    
    elif page == "Daily Operations":
        daily_operations_page()
    
    elif page == "Fleet & Maintenance":
        fleet_maintenance_page()
    
    elif page == "Expenses & Inventory":
        expenses_inventory_page()
    
    elif page == "Customers & Bookings":
        customer_management_page()
    
    elif page == "Documents & Import":
        documents_import_page()
    
    elif page == "Approvals":
        approvals_center_page()
    
    elif page == "Employees":
        employees_consolidated_page()
    
    elif page == "Payroll":
        payroll_consolidated_page()
    
    elif page == "Contracts":
        contract_generator_page()
    
    elif page == "Reports & Analytics":
        reports_analytics_page()
    
    elif page == "My Profile":
        my_profile_page()
    
    elif page == "Backup & Export":
        if has_permission('export_income') or has_permission('generate_reports'):
            backup_export_page()
        else:
            show_access_denied(page)
    
    elif page == "User Management":
        if has_permission('view_users') or has_permission('manage_roles'):
            user_management_consolidated_page()
        else:
            show_access_denied(page)
    
    elif page == "System Settings":
        if has_permission('manage_roles'):
            system_settings_page()
        else:
            show_access_denied(page)
    
    else:
        st.info("Select a page from the menu")


def show_access_denied(page_name: str):
    """Display access denied message"""
    st.error("Access Denied")
    st.markdown(f"""
        You don't have permission to access **{page_name}**.
        
        Please contact your administrator if you need access to this feature.
    """)


if __name__ == "__main__":
    main()