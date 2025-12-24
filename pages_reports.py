"""
pages_reports.py - Consolidated Reports & Analytics Page
Combines all analytics into one streamlined interface
"""

import streamlit as st


def reports_analytics_page():
    """
    Consolidated Reports & Analytics page with tabs for:
    - Overview / Dashboard
    - Revenue Reports
    - Fleet Analysis
    - Driver Performance
    - Financial Reports
    """
    
    st.title("Reports & Analytics")
    
    # Main tabs - organized by what users typically need
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Overview",
        "Revenue",
        "Fleet",
        "Staff",
        "Financial"
    ])
    
    with tab1:
        overview_section()
    
    with tab2:
        revenue_section()
    
    with tab3:
        fleet_section()
    
    with tab4:
        staff_section()
    
    with tab5:
        financial_section()


def overview_section():
    """Quick overview with key metrics"""
    st.subheader("Performance Overview")
    
    from pages_performance_metrics import performance_metrics_page
    performance_metrics_page()


def revenue_section():
    """Revenue and trip analysis"""
    st.subheader("Revenue Analysis")
    
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Trip Analysis", "Route Profitability", "Revenue History"])
    
    with sub_tab1:
        from pages_trips import trip_analysis_page
        trip_analysis_page()
    
    with sub_tab2:
        from pages_route_profitability import route_profitability_page
        route_profitability_page()
    
    with sub_tab3:
        from pages_operations import revenue_history_page
        revenue_history_page()


def fleet_section():
    """Fleet and fuel analysis"""
    st.subheader("Fleet Analysis")
    
    sub_tab1, sub_tab2 = st.tabs(["Bus Analysis", "Fuel Analysis"])
    
    with sub_tab1:
        from pages_bus_analysis import bus_analysis_page
        bus_analysis_page()
    
    with sub_tab2:
        from pages_fuel import fuel_analysis_page
        fuel_analysis_page()


def staff_section():
    """Staff performance analysis"""
    st.subheader("Staff Performance")
    
    from pages_driver_performance import driver_scoring_page
    driver_scoring_page()


def financial_section():
    """Financial reports"""
    st.subheader("Financial Reports")
    
    from pages_profit_loss import profit_loss_page
    profit_loss_page()
