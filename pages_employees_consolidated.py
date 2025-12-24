"""
pages_employees_consolidated.py - Consolidated Employee Management Page
Combines Employee Management, Performance, and Disciplinary into one interface
"""

import streamlit as st


def employees_consolidated_page():
    """
    Consolidated Employee page with tabs for:
    - Employee List
    - Performance
    - Disciplinary Records
    """
    
    st.title("Employee Management")
    
    # Import existing page functions
    from pages_hr import employee_management_page, employee_performance_page, disciplinary_records_page
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs([
        "Employees",
        "Performance",
        "Disciplinary"
    ])
    
    with tab1:
        employee_management_page()
    
    with tab2:
        employee_performance_page()
    
    with tab3:
        disciplinary_records_page()
