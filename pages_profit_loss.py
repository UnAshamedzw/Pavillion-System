"""
pages_profit_loss.py - Profit & Loss Dashboard
Pavillion Coaches Bus Management System
Comprehensive financial overview combining all income and expenses
NOTE: Fuel costs are EXCLUDED as they are deducted before income entry
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES
from auth import has_permission


# =============================================================================
# DATA RETRIEVAL FUNCTIONS
# =============================================================================

def get_total_income(start_date, end_date):
    """Get total income for period (fare income + hire income)"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT 
            COALESCE(SUM(total_income), 0) as total_income,
            COUNT(*) as trip_count
        FROM income
        WHERE date >= {ph} AND date <= {ph}
    """
    
    df = pd.read_sql_query(query, get_engine(), params=(str(start_date), str(end_date)))
    conn.close()
    
    return {
        'total': float(df['total_income'].values[0]) if not df.empty else 0,
        'count': int(df['trip_count'].values[0]) if not df.empty else 0
    }


def get_booking_income(start_date, end_date):
    """Get income from bookings/private hires"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT 
            COALESCE(SUM(total_amount), 0) as total,
            COUNT(*) as count
        FROM bookings
        WHERE trip_date >= {ph} AND trip_date <= {ph}
        AND status IN ('Completed', 'Confirmed')
        AND payment_status IN ('Paid', 'Deposit Paid')
    """
    
    df = pd.read_sql_query(query, get_engine(), params=(str(start_date), str(end_date)))
    conn.close()
    
    return {
        'total': float(df['total'].values[0]) if not df.empty else 0,
        'count': int(df['count'].values[0]) if not df.empty else 0
    }


def get_maintenance_costs(start_date, end_date):
    """Get total maintenance costs for period"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT 
            COALESCE(SUM(cost), 0) as total,
            COUNT(*) as count
        FROM maintenance
        WHERE date >= {ph} AND date <= {ph}
    """
    
    df = pd.read_sql_query(query, get_engine(), params=(str(start_date), str(end_date)))
    conn.close()
    
    return {
        'total': float(df['total'].values[0]) if not df.empty else 0,
        'count': int(df['count'].values[0]) if not df.empty else 0
    }


def get_general_expenses(start_date, end_date):
    """Get total general expenses for period"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT 
            COALESCE(SUM(amount), 0) as total,
            COUNT(*) as count
        FROM general_expenses
        WHERE expense_date >= {ph} AND expense_date <= {ph}
    """
    
    df = pd.read_sql_query(query, get_engine(), params=(str(start_date), str(end_date)))
    conn.close()
    
    return {
        'total': float(df['total'].values[0]) if not df.empty else 0,
        'count': int(df['count'].values[0]) if not df.empty else 0
    }


def get_expenses_by_category(start_date, end_date):
    """Get general expenses grouped by category"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT 
            category,
            COALESCE(SUM(amount), 0) as total,
            COUNT(*) as count
        FROM general_expenses
        WHERE expense_date >= {ph} AND expense_date <= {ph}
        GROUP BY category
        ORDER BY total DESC
    """
    
    df = pd.read_sql_query(query, get_engine(), params=(str(start_date), str(end_date)))
    conn.close()
    return df


def get_maintenance_by_type(start_date, end_date):
    """Get maintenance costs grouped by type"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT 
            maintenance_type,
            COALESCE(SUM(cost), 0) as total,
            COUNT(*) as count
        FROM maintenance
        WHERE date >= {ph} AND date <= {ph}
        GROUP BY maintenance_type
        ORDER BY total DESC
    """
    
    df = pd.read_sql_query(query, get_engine(), params=(str(start_date), str(end_date)))
    conn.close()
    return df


def get_income_by_route(start_date, end_date):
    """Get income grouped by route"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT 
            route,
            COALESCE(SUM(total_income), 0) as total,
            COUNT(*) as trips
        FROM income
        WHERE date >= {ph} AND date <= {ph}
        GROUP BY route
        ORDER BY total DESC
    """
    
    df = pd.read_sql_query(query, get_engine(), params=(str(start_date), str(end_date)))
    conn.close()
    return df


def get_monthly_pnl(year):
    """Get monthly profit/loss data for the year"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    results = []
    
    for month in range(1, 13):
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year}-12-31"
        else:
            end_date = f"{year}-{month+1:02d}-01"
        
        # Income
        income_data = get_total_income(start_date, end_date)
        booking_data = get_booking_income(start_date, end_date)
        total_income = income_data['total'] + booking_data['total']
        
        # Expenses (excluding fuel)
        maintenance = get_maintenance_costs(start_date, end_date)
        general = get_general_expenses(start_date, end_date)
        total_expenses = maintenance['total'] + general['total']
        
        profit = total_income - total_expenses
        
        results.append({
            'month': month,
            'month_name': datetime(year, month, 1).strftime('%b'),
            'income': total_income,
            'expenses': total_expenses,
            'profit': profit
        })
    
    conn.close()
    return pd.DataFrame(results)


def get_fuel_insights(start_date, end_date):
    """
    Get fuel data for INSIGHTS ONLY - not included in P&L
    This is because fuel is deducted before income entry
    """
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    query = f"""
        SELECT 
            COALESCE(SUM(total_cost), 0) as total_cost,
            COALESCE(SUM(litres), 0) as total_litres,
            COUNT(*) as count
        FROM fuel_records
        WHERE date >= {ph} AND date <= {ph}
    """
    
    df = pd.read_sql_query(query, get_engine(), params=(str(start_date), str(end_date)))
    conn.close()
    
    return {
        'total_cost': float(df['total_cost'].values[0]) if not df.empty else 0,
        'total_litres': float(df['total_litres'].values[0]) if not df.empty else 0,
        'count': int(df['count'].values[0]) if not df.empty else 0
    }


def get_bus_expenses(start_date, end_date, bus_number=None):
    """Get expenses breakdown per bus"""
    conn = get_connection()
    ph = '%s' if USE_POSTGRES else '?'
    
    # Maintenance per bus
    maint_query = f"""
        SELECT 
            bus_number,
            COALESCE(SUM(cost), 0) as maintenance_cost
        FROM maintenance
        WHERE date >= {ph} AND date <= {ph}
    """
    params = [str(start_date), str(end_date)]
    
    if bus_number:
        maint_query += f" AND bus_number = {ph}"
        params.append(bus_number)
    
    maint_query += " GROUP BY bus_number"
    
    maint_df = pd.read_sql_query(maint_query, get_engine(), params=tuple(params))
    
    # Income per bus
    income_query = f"""
        SELECT 
            bus_number,
            COALESCE(SUM(total_income), 0) as total_income
        FROM income
        WHERE date >= {ph} AND date <= {ph}
    """
    income_params = [str(start_date), str(end_date)]
    
    if bus_number:
        income_query += f" AND bus_number = {ph}"
        income_params.append(bus_number)
    
    income_query += " GROUP BY bus_number"
    
    income_df = pd.read_sql_query(income_query, get_engine(), params=tuple(income_params))
    
    conn.close()
    
    # Merge
    if not maint_df.empty and not income_df.empty:
        merged = pd.merge(income_df, maint_df, on='bus_number', how='outer').fillna(0)
        merged['profit'] = merged['total_income'] - merged['maintenance_cost']
        return merged
    elif not income_df.empty:
        income_df['maintenance_cost'] = 0
        income_df['profit'] = income_df['total_income']
        return income_df
    elif not maint_df.empty:
        maint_df['total_income'] = 0
        maint_df['profit'] = -maint_df['maintenance_cost']
        return maint_df
    
    return pd.DataFrame()


# =============================================================================
# PAGE FUNCTION
# =============================================================================

def profit_loss_page():
    """Comprehensive Profit & Loss Dashboard"""
    
    st.header("📊 Profit & Loss Statement")
    st.markdown("Comprehensive financial overview of all income and expenses")
    
    st.info("""
    💡 **Note:** Fuel costs are shown for **insights only** and are NOT included in expense calculations.
    This is because fuel is already deducted before income entry to avoid double-counting.
    """)
    
    st.markdown("---")
    
    # Date range selection
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    
    with col1:
        start_date = st.date_input(
            "From",
            value=datetime.now().date().replace(day=1),
            key="pnl_start"
        )
    
    with col2:
        end_date = st.date_input(
            "To",
            value=datetime.now().date(),
            key="pnl_end"
        )
    
    with col3:
        if st.button("📅 This Month", use_container_width=True):
            start_date = datetime.now().date().replace(day=1)
            end_date = datetime.now().date()
    
    with col4:
        if st.button("📆 This Year", use_container_width=True):
            start_date = datetime.now().date().replace(month=1, day=1)
            end_date = datetime.now().date()
    
    st.markdown("---")
    
    # ==========================================================================
    # INCOME SECTION
    # ==========================================================================
    
    st.subheader("💰 INCOME")
    
    fare_income = get_total_income(start_date, end_date)
    booking_income = get_booking_income(start_date, end_date)
    
    total_income = fare_income['total'] + booking_income['total']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "🚌 Route/Fare Income",
            f"${fare_income['total']:,.2f}",
            f"{fare_income['count']} trips"
        )
    
    with col2:
        st.metric(
            "📋 Booking/Hire Income",
            f"${booking_income['total']:,.2f}",
            f"{booking_income['count']} bookings"
        )
    
    with col3:
        st.metric(
            "💵 TOTAL INCOME",
            f"${total_income:,.2f}",
            delta=None
        )
    
    st.markdown("---")
    
    # ==========================================================================
    # EXPENSES SECTION
    # ==========================================================================
    
    st.subheader("💸 EXPENSES")
    
    maintenance = get_maintenance_costs(start_date, end_date)
    general_exp = get_general_expenses(start_date, end_date)
    
    total_expenses = maintenance['total'] + general_exp['total']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "🔧 Bus Maintenance",
            f"${maintenance['total']:,.2f}",
            f"{maintenance['count']} records"
        )
    
    with col2:
        st.metric(
            "🏢 General Expenses",
            f"${general_exp['total']:,.2f}",
            f"{general_exp['count']} records"
        )
    
    with col3:
        st.metric(
            "💳 TOTAL EXPENSES",
            f"${total_expenses:,.2f}",
            delta=None
        )
    
    st.markdown("---")
    
    # ==========================================================================
    # PROFIT/LOSS SECTION
    # ==========================================================================
    
    st.subheader("📈 PROFIT / LOSS")
    
    profit = total_income - total_expenses
    profit_margin = (profit / total_income * 100) if total_income > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "💵 Total Income",
            f"${total_income:,.2f}"
        )
    
    with col2:
        st.metric(
            "💳 Total Expenses",
            f"${total_expenses:,.2f}"
        )
    
    with col3:
        delta_color = "normal" if profit >= 0 else "inverse"
        profit_label = "NET PROFIT" if profit >= 0 else "NET LOSS"
        st.metric(
            f"{'✅' if profit >= 0 else '❌'} {profit_label}",
            f"${abs(profit):,.2f}",
            f"{profit_margin:.1f}% margin" if profit >= 0 else f"-{abs(profit_margin):.1f}%",
            delta_color=delta_color
        )
    
    # Visual indicator
    if profit >= 0:
        st.success(f"✅ **PROFITABLE** - Net profit of ${profit:,.2f} ({profit_margin:.1f}% margin)")
    else:
        st.error(f"❌ **LOSS** - Net loss of ${abs(profit):,.2f}")
    
    st.markdown("---")
    
    # ==========================================================================
    # FUEL INSIGHTS (NOT INCLUDED IN P&L)
    # ==========================================================================
    
    st.subheader("⛽ Fuel Insights (Reference Only)")
    
    st.warning("""
    ⚠️ **Fuel costs below are for REFERENCE ONLY** and are NOT included in the P&L calculation above.
    Fuel is deducted from revenue before income entry, so including it here would be double-counting.
    """)
    
    fuel = get_fuel_insights(start_date, end_date)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("⛽ Total Fuel Cost", f"${fuel['total_cost']:,.2f}")
    
    with col2:
        st.metric("🛢️ Total Litres", f"{fuel['total_litres']:,.0f} L")
    
    with col3:
        avg_price = fuel['total_cost'] / fuel['total_litres'] if fuel['total_litres'] > 0 else 0
        st.metric("💲 Avg Price/Litre", f"${avg_price:.2f}")
    
    with col4:
        st.metric("📝 Fuel Records", fuel['count'])
    
    st.markdown("---")
    
    # ==========================================================================
    # DETAILED BREAKDOWN TABS
    # ==========================================================================
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Visual Charts",
        "📋 Expense Breakdown",
        "🚌 Per-Bus Analysis",
        "📈 Monthly Trend"
    ])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Income vs Expenses pie
            fig_overview = go.Figure(data=[
                go.Pie(
                    labels=['Income', 'Expenses'],
                    values=[total_income, total_expenses],
                    hole=0.4,
                    marker_colors=['#28a745', '#dc3545']
                )
            ])
            fig_overview.update_layout(title='Income vs Expenses')
            st.plotly_chart(fig_overview, use_container_width=True)
        
        with col2:
            # Expense breakdown pie
            exp_cat = get_expenses_by_category(start_date, end_date)
            maint_data = get_maintenance_by_type(start_date, end_date)
            
            # Combine maintenance as a category
            all_expenses = []
            
            if not exp_cat.empty:
                for _, row in exp_cat.iterrows():
                    all_expenses.append({
                        'category': row['category'],
                        'total': row['total']
                    })
            
            if not maint_data.empty:
                maint_total = maint_data['total'].sum()
                all_expenses.append({
                    'category': 'Bus Maintenance',
                    'total': maint_total
                })
            
            if all_expenses:
                exp_df = pd.DataFrame(all_expenses)
                fig_exp = px.pie(
                    exp_df,
                    values='total',
                    names='category',
                    title='Expense Distribution'
                )
                st.plotly_chart(fig_exp, use_container_width=True)
            else:
                st.info("No expense data for charts")
        
        # Income by route
        st.markdown("### 💰 Income by Route")
        route_df = get_income_by_route(start_date, end_date)
        
        if not route_df.empty:
            fig_route = px.bar(
                route_df,
                x='route',
                y='total',
                title='Revenue by Route',
                labels={'route': 'Route', 'total': 'Revenue ($)'},
                color='total',
                color_continuous_scale='Greens'
            )
            st.plotly_chart(fig_route, use_container_width=True)
        else:
            st.info("No route income data")
    
    with tab2:
        st.markdown("### 💳 Expense Breakdown")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏢 General Expenses by Category")
            exp_cat = get_expenses_by_category(start_date, end_date)
            
            if not exp_cat.empty:
                exp_cat.columns = ['Category', 'Total ($)', 'Count']
                st.dataframe(exp_cat, use_container_width=True, hide_index=True)
            else:
                st.info("No general expenses")
        
        with col2:
            st.markdown("#### 🔧 Maintenance by Type")
            maint_type = get_maintenance_by_type(start_date, end_date)
            
            if not maint_type.empty:
                maint_type.columns = ['Type', 'Total ($)', 'Count']
                st.dataframe(maint_type, use_container_width=True, hide_index=True)
            else:
                st.info("No maintenance records")
        
        # Summary table
        st.markdown("---")
        st.markdown("### 📊 Summary Table")
        
        summary_data = [
            {"Category": "Route/Fare Income", "Amount": fare_income['total'], "Type": "Income"},
            {"Category": "Booking/Hire Income", "Amount": booking_income['total'], "Type": "Income"},
            {"Category": "Bus Maintenance", "Amount": -maintenance['total'], "Type": "Expense"},
            {"Category": "General Expenses", "Amount": -general_exp['total'], "Type": "Expense"},
        ]
        
        summary_df = pd.DataFrame(summary_data)
        summary_df['Amount ($)'] = summary_df['Amount'].apply(
            lambda x: f"${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}"
        )
        
        st.dataframe(
            summary_df[['Category', 'Type', 'Amount ($)']],
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown(f"**Net Result: {'Profit' if profit >= 0 else 'Loss'} of ${abs(profit):,.2f}**")
    
    with tab3:
        st.markdown("### 🚌 Per-Bus Profit Analysis")
        
        bus_data = get_bus_expenses(start_date, end_date)
        
        if bus_data.empty:
            st.info("No bus-level data available")
        else:
            bus_data = bus_data.sort_values('profit', ascending=False)
            
            # Chart
            fig_bus = go.Figure()
            
            fig_bus.add_trace(go.Bar(
                name='Income',
                x=bus_data['bus_number'],
                y=bus_data['total_income'],
                marker_color='green'
            ))
            
            fig_bus.add_trace(go.Bar(
                name='Maintenance',
                x=bus_data['bus_number'],
                y=bus_data['maintenance_cost'],
                marker_color='red'
            ))
            
            fig_bus.update_layout(
                title='Income vs Maintenance by Bus',
                barmode='group',
                xaxis_title='Bus',
                yaxis_title='Amount ($)'
            )
            
            st.plotly_chart(fig_bus, use_container_width=True)
            
            # Table
            display_bus = bus_data.copy()
            display_bus.columns = ['Bus', 'Income ($)', 'Maintenance ($)', 'Profit ($)']
            display_bus['Status'] = display_bus['Profit ($)'].apply(
                lambda x: '✅ Profitable' if x > 0 else '❌ Loss' if x < 0 else '⚪ Break-even'
            )
            
            st.dataframe(display_bus, use_container_width=True, hide_index=True)
    
    with tab4:
        st.markdown("### 📈 Monthly Profit/Loss Trend")
        
        year = st.selectbox(
            "Select Year",
            range(datetime.now().year, datetime.now().year - 5, -1),
            key="pnl_year"
        )
        
        monthly_data = get_monthly_pnl(year)
        
        if not monthly_data.empty:
            # Line chart
            fig_monthly = go.Figure()
            
            fig_monthly.add_trace(go.Scatter(
                x=monthly_data['month_name'],
                y=monthly_data['income'],
                name='Income',
                mode='lines+markers',
                line=dict(color='green', width=2)
            ))
            
            fig_monthly.add_trace(go.Scatter(
                x=monthly_data['month_name'],
                y=monthly_data['expenses'],
                name='Expenses',
                mode='lines+markers',
                line=dict(color='red', width=2)
            ))
            
            fig_monthly.add_trace(go.Scatter(
                x=monthly_data['month_name'],
                y=monthly_data['profit'],
                name='Profit/Loss',
                mode='lines+markers',
                line=dict(color='blue', width=3)
            ))
            
            fig_monthly.update_layout(
                title=f'Monthly Financial Performance - {year}',
                xaxis_title='Month',
                yaxis_title='Amount ($)',
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_monthly, use_container_width=True)
            
            # Monthly table
            monthly_display = monthly_data[['month_name', 'income', 'expenses', 'profit']].copy()
            monthly_display.columns = ['Month', 'Income ($)', 'Expenses ($)', 'Profit ($)']
            monthly_display['Status'] = monthly_display['Profit ($)'].apply(
                lambda x: '✅' if x > 0 else '❌' if x < 0 else '⚪'
            )
            
            st.dataframe(monthly_display, use_container_width=True, hide_index=True)
            
            # Year totals
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(f"Total Income {year}", f"${monthly_data['income'].sum():,.2f}")
            with col2:
                st.metric(f"Total Expenses {year}", f"${monthly_data['expenses'].sum():,.2f}")
            with col3:
                year_profit = monthly_data['profit'].sum()
                st.metric(
                    f"Net {'Profit' if year_profit >= 0 else 'Loss'} {year}",
                    f"${abs(year_profit):,.2f}",
                    delta_color="normal" if year_profit >= 0 else "inverse"
                )
        else:
            st.info(f"No data available for {year}")
