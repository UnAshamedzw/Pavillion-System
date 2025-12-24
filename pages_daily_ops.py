"""
pages_daily_ops.py - Consolidated Daily Operations Page
Combines Trip Entry, Cash Left, and Reconciliation into one streamlined interface
"""

import streamlit as st
from datetime import datetime, timedelta

# Import existing page functions
from pages_operations import income_entry_page
from pages_cash_left import cash_left_page, get_pending_cash_left, get_cash_left_summary
from pages_reconciliation import daily_reconciliation_page


def daily_operations_page():
    """
    Consolidated Daily Operations page with tabs for:
    - Trip & Income Entry
    - Cash Left at Rank
    - Daily Reconciliation
    """
    
    st.title("Daily Operations")
    
    # Show alerts/summary at top
    show_daily_summary()
    
    st.markdown("---")
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs([
        "Trip Entry",
        "Cash Left",
        "Reconciliation"
    ])
    
    with tab1:
        income_entry_section()
    
    with tab2:
        cash_left_section()
    
    with tab3:
        reconciliation_section()


def show_daily_summary():
    """Show quick summary of today's operations"""
    from database import get_connection, get_engine
    
    today = datetime.now().date()
    
    try:
        conn = get_connection()
        
        # Today's trips and revenue
        import pandas as pd
        revenue_df = pd.read_sql_query(f"""
            SELECT COUNT(*) as trips, COALESCE(SUM(amount), 0) as revenue
            FROM income WHERE date = '{today}'
        """, get_engine())
        
        trips = int(revenue_df['trips'].iloc[0]) if not revenue_df.empty else 0
        revenue = float(revenue_df['revenue'].iloc[0]) if not revenue_df.empty else 0
        
        conn.close()
    except Exception as e:
        trips = 0
        revenue = 0
    
    # Get pending cash left
    cash_summary = get_cash_left_summary()
    
    # Display summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Today's Trips", trips)
    
    with col2:
        st.metric("Today's Revenue", f"${revenue:,.2f}")
    
    with col3:
        st.metric("Pending Cash Left", cash_summary['count'])
    
    with col4:
        st.metric("Cash Left Amount", f"${cash_summary['amount']:,.2f}")


def income_entry_section():
    """Simplified income entry section"""
    st.subheader("Record Trip Income")
    
    # Call the existing income entry page but we can simplify later
    income_entry_page()


def cash_left_section():
    """Simplified cash left section"""
    st.subheader("Cash Left at Rank")
    
    # Call the existing cash left page
    cash_left_page()


def reconciliation_section():
    """Simplified reconciliation section"""
    st.subheader("Daily Reconciliation")
    
    # Call the existing reconciliation page
    daily_reconciliation_page()
