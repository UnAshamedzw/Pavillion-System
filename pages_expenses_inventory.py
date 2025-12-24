"""
pages_expenses_inventory.py - Consolidated Expenses & Inventory Page
Combines General Expenses and Inventory into one interface
"""

import streamlit as st


def expenses_inventory_page():
    """
    Consolidated Expenses & Inventory page with tabs for:
    - General Expenses
    - Inventory Management
    """
    
    st.title("Expenses & Inventory")
    
    # Import existing page functions
    from pages_expenses import general_expenses_page
    from pages_inventory import inventory_management_page
    
    # Main tabs
    tab1, tab2 = st.tabs([
        "Expenses",
        "Inventory"
    ])
    
    with tab1:
        st.subheader("General Expenses")
        general_expenses_page()
    
    with tab2:
        st.subheader("Inventory Management")
        inventory_management_page()
