"""
pages_payroll_consolidated.py - Consolidated Payroll Page
Combines Payroll Processing and Leave Management into one interface
"""

import streamlit as st


def payroll_consolidated_page():
    """
    Consolidated Payroll page with tabs for:
    - Payroll Processing
    - Leave Management
    """
    
    st.title("Payroll & Leave")
    
    # Import existing page functions
    from pages_payroll import payroll_processing_page
    from pages_hr import leave_management_page
    
    # Main tabs
    tab1, tab2 = st.tabs([
        "Payroll",
        "Leave"
    ])
    
    with tab1:
        st.subheader("Payroll Processing")
        payroll_processing_page()
    
    with tab2:
        st.subheader("Leave Management")
        leave_management_page()
