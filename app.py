"""
app.py - Main Application Entry Point
Bus Income and Maintenance Management System with HR Module, Authentication, and Audit Trail
NOW WITH BUSES AND ROUTES MANAGEMENT
"""

import streamlit as st
from database import init_database
from auth import create_users_table, login_page, logout
from pages_operations import (
    income_entry_page, 
    maintenance_entry_page, 
    revenue_history_page,
    import_data_page,
    dashboard_page,
    buses_routes_management_page
)
from pages_hr import (
    employee_management_page,
    employee_performance_page,
    payroll_management_page,
    leave_management_page,
    disciplinary_records_page
)
from pages_users import user_management_page, my_profile_page
from pages_audit import activity_log_page, user_activity_dashboard
from pages_bus_analysis import bus_analysis_page
from pages_performance_metrics import performance_metrics_page
from fleet_management_page import fleet_management_page, show_expiry_alerts

def main():
    """Main application entry point"""
    
    # Page configuration
    st.set_page_config(
        page_title="Bus Management System",
        page_icon="🚌",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize database only once per session
    if 'initialized' not in st.session_state:
        init_database() 
        create_users_table()  # Initialize user authentication tables
        st.session_state.initialized = True
    
    # Check authentication
    if not st.session_state.get('authenticated', False):
        login_page()
        return
    
    # Custom CSS
    st.markdown("""
        <style>
        .main {
            padding: 0rem 1rem;
        }
        h1 {
            color: #2c3e50;
            padding-bottom: 1rem;
        }
        h2 {
            color: #34495e;
        }
        .stMetric {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #3498db;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Get current user info
    user = st.session_state['user']
    
    # Sidebar
    st.sidebar.title("🚌 Bus Management System")
    st.sidebar.markdown(f"**👤 {user['full_name']}** ({user['role']})")
    st.sidebar.markdown("---")
    
    # Main menu selection
    menu_section = st.sidebar.radio(
        "Main Menu:",
        ["🚌 Operations", "👥 HR Management", "📊 Analytics", "⚙️ System"]
    )
    
    st.sidebar.markdown("---")
    
    # Sub-menu based on main menu
    if menu_section == "🚌 Operations":
        page = st.sidebar.radio(
            "Operations:",
            [
                "📊 Income Entry",
                "🔧 Maintenance Entry",
                "📥 Import from Excel",
                "💰 Revenue History",
                "📈 Dashboard",
                "🚌 Fleet Management",
                "🚗 Buses & Routes"
            ]
        )
    elif menu_section == "👥 HR Management":
        page = st.sidebar.radio(
            "HR Management:",
            [
                "👥 Employee Management",
                "📊 Employee Performance",
                "💰 Payroll & Payslips",
                "📅 Leave Management",
                "⚠️ Disciplinary Records"
            ]
        )
    elif menu_section == "📊 Analytics":
        page = st.sidebar.radio(
            "Analytics:",
            [
                "🚌 Bus-by-Bus Analysis",
                "📈 Performance Metrics"
            ]
        )
    else:  # System
        pages_list = ["👤 My Profile", "📊 My Activity"]
        # Only show User Management and Activity Log for Admins
        if user['role'] == 'Admin':
            pages_list.extend(["👥 User Management", "📜 Activity Log"])
        
        page = st.sidebar.radio("System:", pages_list)
    
    st.sidebar.markdown("---")
    
    # Info boxes
    if menu_section == "🚌 Operations":
        st.sidebar.info("""
        **Operations Features:**
        - 📊 Track daily revenue
        - 🔧 Record maintenance
        - 📥 Bulk import from Excel
        - 💰 Revenue history
        - 📈 Analytics dashboard
        - 🚌 Fleet management
        - 🚗 Buses & routes setup
        - ⚠️ Document tracking
        - ✅ Full audit trail
        """)
    elif menu_section == "👥 HR Management":
        st.sidebar.info("""
        **HR Features:**
        - 👥 Employee database
        - 📊 Performance metrics
        - 💰 Payroll & payslips
        - 📅 Leave management
        - ⚠️ Disciplinary records
        - 💵 Commission tracking
        """)
    elif menu_section == "📊 Analytics":
        st.sidebar.info("""
        **Analytics Features:**
        - 🚌 Bus-by-bus analysis
        - 💰 Revenue vs expenses
        - 📊 Profit/loss tracking
        - 📈 Performance trends
        - 📥 Export to Excel/PDF
        """)
    else:
        st.sidebar.info(f"""
        **User Info:**
        - **Name:** {user['full_name']}
        - **Role:** {user['role']}
        - **Username:** {user['username']}
        
        **System Features:**
        - 🔐 Secure authentication
        - 📜 Complete audit trail
        - 👥 User management
        """)
    
    # Logout button
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()
    
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2025 Bus Management System v3.2")
    st.sidebar.caption("🔒 Secure | 📊 Audited | 🚀 Efficient")
    
    # Main content area
    st.title("🚌 Bus Management System")
    st.caption("Complete Operations & HR Management Solution with Full Audit Trail")
    
    # Show document expiry alerts on Dashboard page
    if page == "📈 Dashboard":
        try:
            show_expiry_alerts()
            st.markdown("---")
        except Exception as e:
            # Silently fail if fleet management is not set up yet
            pass
    
    # Route to appropriate page
    if page == "📊 Income Entry":
        income_entry_page()
    elif page == "🔧 Maintenance Entry":
        maintenance_entry_page()
    elif page == "📥 Import from Excel":
        import_data_page()
    elif page == "💰 Revenue History":
        revenue_history_page()
    elif page == "📈 Dashboard":
        dashboard_page()
    elif page == "🚌 Fleet Management":
        fleet_management_page()
    elif page == "🚗 Buses & Routes":
        buses_routes_management_page()
    elif page == "👥 Employee Management":
        employee_management_page()
    elif page == "📊 Employee Performance":
        employee_performance_page()
    elif page == "💰 Payroll & Payslips":
        payroll_management_page()
    elif page == "📅 Leave Management":
        leave_management_page()
    elif page == "⚠️ Disciplinary Records":
        disciplinary_records_page()
    elif page == "🚌 Bus-by-Bus Analysis":
        bus_analysis_page()
    elif page == "📈 Performance Metrics":
        performance_metrics_page()
    elif page == "👤 My Profile":
        my_profile_page()
    elif page == "📊 My Activity":
        user_activity_dashboard()
    elif page == "👥 User Management":
        user_management_page()
    elif page == "📜 Activity Log":
        activity_log_page()

if __name__ == "__main__":
    main()