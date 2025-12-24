"""
pages_daily_ops.py - Consolidated Daily Operations Page
Combines Trip Entry, Cash Left, Fuel, and Reconciliation into one streamlined interface
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Import existing page functions
from pages_operations import income_entry_page
from pages_cash_left import cash_left_page, get_pending_cash_left, get_cash_left_summary
from pages_reconciliation import daily_reconciliation_page
from pages_fuel import fuel_entry_page


def daily_operations_page():
    """
    Consolidated Daily Operations page with tabs for:
    - Trip & Income Entry
    - Cash Left at Rank
    - Fuel Entry
    - Daily Reconciliation
    """
    
    st.title("Daily Operations")
    
    # Show alerts/summary at top
    show_daily_summary()
    
    st.markdown("---")
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Trip Entry",
        "Cash Left",
        "Fuel",
        "Reconciliation"
    ])
    
    with tab1:
        income_entry_section()
    
    with tab2:
        cash_left_section()
    
    with tab3:
        fuel_section()
    
    with tab4:
        reconciliation_section()


def show_daily_summary():
    """Show quick summary of today's operations with styled metrics"""
    from database import get_connection, get_engine
    from table_styles import format_currency
    
    today = datetime.now().date()
    
    try:
        conn = get_connection()
        
        # Today's trips and revenue
        revenue_df = pd.read_sql_query(f"""
            SELECT COUNT(*) as trips, COALESCE(SUM(amount), 0) as revenue
            FROM income WHERE date = '{today}'
        """, get_engine())
        
        trips = int(revenue_df['trips'].iloc[0]) if not revenue_df.empty else 0
        revenue = float(revenue_df['revenue'].iloc[0]) if not revenue_df.empty else 0
        
        # Today's fuel
        fuel_df = pd.read_sql_query(f"""
            SELECT COUNT(*) as fills, COALESCE(SUM(total_cost), 0) as fuel_cost
            FROM fuel_records WHERE date = '{today}'
        """, get_engine())
        
        fuel_fills = int(fuel_df['fills'].iloc[0]) if not fuel_df.empty else 0
        fuel_cost = float(fuel_df['fuel_cost'].iloc[0]) if not fuel_df.empty else 0
        
        conn.close()
    except Exception as e:
        trips = revenue = fuel_fills = fuel_cost = 0
    
    # Get pending cash left
    cash_summary = get_cash_left_summary()
    
    # Display styled summary
    st.markdown("""
        <style>
        .summary-container {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }
        .summary-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 20px;
            flex: 1;
            min-width: 150px;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .summary-card.green {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }
        .summary-card.orange {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        .summary-card.blue {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        .summary-card h3 {
            margin: 0;
            font-size: 28px;
            font-weight: bold;
        }
        .summary-card p {
            margin: 5px 0 0 0;
            opacity: 0.9;
            font-size: 14px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="summary-card green">
                <h3>{format_currency(revenue)}</h3>
                <p>Today's Revenue ({trips} trips)</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="summary-card orange">
                <h3>{format_currency(fuel_cost)}</h3>
                <p>Fuel Cost ({fuel_fills} fills)</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="summary-card blue">
                <h3>{cash_summary['count']}</h3>
                <p>Pending Cash Left</p>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        net_today = revenue - fuel_cost
        st.markdown(f"""
            <div class="summary-card">
                <h3>{format_currency(net_today)}</h3>
                <p>Net (Revenue - Fuel)</p>
            </div>
        """, unsafe_allow_html=True)


def income_entry_section():
    """Simplified income entry section"""
    income_entry_page()


def cash_left_section():
    """Cash left section"""
    cash_left_page()


def fuel_section():
    """Fuel entry section"""
    fuel_entry_page()


def reconciliation_section():
    """Reconciliation section"""
    daily_reconciliation_page()