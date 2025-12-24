"""
pages_fleet_maintenance.py - Consolidated Fleet & Maintenance Page
Combines Fleet Management, Maintenance, Fuel, and Routes into one interface
"""

import streamlit as st


def fleet_maintenance_page():
    """
    Consolidated Fleet & Maintenance page with tabs for:
    - Fleet Overview (buses)
    - Maintenance
    - Fuel
    - Routes & Assignments
    """
    
    st.title("Fleet & Maintenance")
    
    # Import existing page functions
    from fleet_management_page import fleet_management_page
    from pages_operations import maintenance_entry_page, routes_assignments_page
    from pages_fuel import fuel_entry_page
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Fleet",
        "Maintenance", 
        "Fuel",
        "Routes"
    ])
    
    with tab1:
        st.subheader("Fleet Management")
        fleet_management_page()
    
    with tab2:
        st.subheader("Maintenance Records")
        maintenance_entry_page()
    
    with tab3:
        st.subheader("Fuel Records")
        fuel_entry_page()
    
    with tab4:
        st.subheader("Routes & Assignments")
        routes_assignments_page()
