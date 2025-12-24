"""
pages_admin.py - Consolidated User & System Management Page
Combines User Management, Role Management, and Activity Logs
"""

import streamlit as st


def user_management_consolidated_page():
    """
    Consolidated User Management page with tabs for:
    - Users
    - Roles & Permissions
    - Activity Log
    """
    
    st.title("User Management")
    
    # Import existing page functions
    from pages_users import user_management_page, role_management_page
    from pages_audit import activity_log_page
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs([
        "Users",
        "Roles",
        "Activity Log"
    ])
    
    with tab1:
        user_management_page()
    
    with tab2:
        role_management_page()
    
    with tab3:
        activity_log_page()


def system_settings_page():
    """
    System Settings page with tabs for:
    - Notifications
    - System Configuration
    """
    
    st.title("System Settings")
    
    from pages_notifications import notification_settings_page
    
    tab1, tab2 = st.tabs([
        "Notifications",
        "Configuration"
    ])
    
    with tab1:
        notification_settings_page()
    
    with tab2:
        st.subheader("System Configuration")
        st.info("System configuration options coming soon.")
        
        # Placeholder for future settings
        st.markdown("""
        **Available Settings:**
        - Company Information
        - Tax Rates (PAYE, NSSA)
        - Default Commission Rates
        - Currency Settings
        - Backup Schedule
        """)
