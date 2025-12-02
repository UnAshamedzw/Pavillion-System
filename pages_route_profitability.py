"""
pages_route_profitability.py - Route Profitability Analysis Module
Pavillion Coaches Bus Management System
Analyze route profitability by comparing revenue against allocated costs
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES
from auth import has_permission


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_routes():
    """Get all routes"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, distance, description FROM routes ORDER BY name")
    routes = cursor.fetchall()
    conn.close()
    return routes


def get_route_income(start_date=None, end_date=None):
    """Get income grouped by route"""
    conn = get_connection()
    
    query = """
        SELECT 
            route,
            COUNT(*) as income_entries,
            SUM(amount) as total_income,
            AVG(amount) as avg_income_per_entry
        FROM income
        WHERE route IS NOT NULL AND route != ''
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(start_date)
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(end_date)
    
    query += " GROUP BY route ORDER BY total_income DESC"
    
    df = pd.read_sql_query(query, get_engine(), params=params)
    conn.close()
    return df


def get_trip_revenue_by_route(start_date=None, end_date=None):
    """Get trip revenue grouped by route"""
    conn = get_connection()
    
    query = """
        SELECT 
            route_name as route,
            COUNT(*) as trip_count,
            SUM(passengers) as total_passengers,
            SUM(revenue) as total_revenue,
            AVG(passengers) as avg_passengers,
            AVG(revenue) as avg_revenue_per_trip,
            AVG(revenue_per_passenger) as avg_revenue_per_passenger
        FROM trips
        WHERE route_name IS NOT NULL
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        query += f" AND trip_date >= {ph}"
        params.append(start_date)
    
    if end_date:
        query += f" AND trip_date <= {ph}"
        params.append(end_date)
    
    query += " GROUP BY route_name ORDER BY total_revenue DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=params)
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_maintenance_by_route(start_date=None, end_date=None):
    """
    Get maintenance costs - allocated proportionally based on route usage.
    Since maintenance is per bus, we allocate costs based on trips per route.
    """
    conn = get_connection()
    
    # First get total maintenance costs per bus
    maint_query = """
        SELECT 
            bus_number,
            SUM(cost) as total_maintenance
        FROM maintenance
        WHERE 1=1
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        maint_query += f" AND date >= {ph}"
        params.append(start_date)
    
    if end_date:
        maint_query += f" AND date <= {ph}"
        params.append(end_date)
    
    maint_query += " GROUP BY bus_number"
    
    try:
        maint_df = pd.read_sql_query(maint_query, get_engine(), params=params)
    except:
        maint_df = pd.DataFrame()
    
    # Get trip distribution per bus per route
    trip_query = """
        SELECT 
            bus_number,
            route_name,
            COUNT(*) as trip_count
        FROM trips
        WHERE route_name IS NOT NULL
    """
    
    trip_params = []
    if start_date:
        trip_query += f" AND trip_date >= {ph}"
        trip_params.append(start_date)
    
    if end_date:
        trip_query += f" AND trip_date <= {ph}"
        trip_params.append(end_date)
    
    trip_query += " GROUP BY bus_number, route_name"
    
    try:
        trip_dist_df = pd.read_sql_query(trip_query, get_engine(), params=trip_params)
    except:
        trip_dist_df = pd.DataFrame()
    
    conn.close()
    
    if maint_df.empty or trip_dist_df.empty:
        return pd.DataFrame(columns=['route', 'allocated_maintenance'])
    
    # Calculate allocation
    # For each bus, allocate maintenance proportionally to routes based on trips
    results = []
    
    for bus in maint_df['bus_number'].unique():
        bus_maint = maint_df[maint_df['bus_number'] == bus]['total_maintenance'].values[0]
        bus_trips = trip_dist_df[trip_dist_df['bus_number'] == bus]
        
        if bus_trips.empty:
            continue
        
        total_trips = bus_trips['trip_count'].sum()
        
        for _, row in bus_trips.iterrows():
            allocation = (row['trip_count'] / total_trips) * bus_maint
            results.append({
                'route': row['route_name'],
                'allocated_maintenance': allocation
            })
    
    if results:
        result_df = pd.DataFrame(results)
        result_df = result_df.groupby('route')['allocated_maintenance'].sum().reset_index()
        return result_df
    
    return pd.DataFrame(columns=['route', 'allocated_maintenance'])


def get_fuel_by_route(start_date=None, end_date=None):
    """
    Get fuel costs - allocated proportionally based on route usage.
    Similar to maintenance allocation.
    """
    conn = get_connection()
    
    # Get total fuel costs per bus
    fuel_query = """
        SELECT 
            bus_number,
            SUM(total_cost) as total_fuel
        FROM fuel_records
        WHERE 1=1
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        fuel_query += f" AND date >= {ph}"
        params.append(start_date)
    
    if end_date:
        fuel_query += f" AND date <= {ph}"
        params.append(end_date)
    
    fuel_query += " GROUP BY bus_number"
    
    try:
        fuel_df = pd.read_sql_query(fuel_query, get_engine(), params=params)
    except:
        fuel_df = pd.DataFrame()
    
    # Get trip distribution
    trip_query = """
        SELECT 
            bus_number,
            route_name,
            COUNT(*) as trip_count
        FROM trips
        WHERE route_name IS NOT NULL
    """
    
    trip_params = []
    if start_date:
        trip_query += f" AND trip_date >= {ph}"
        trip_params.append(start_date)
    
    if end_date:
        trip_query += f" AND trip_date <= {ph}"
        trip_params.append(end_date)
    
    trip_query += " GROUP BY bus_number, route_name"
    
    try:
        trip_dist_df = pd.read_sql_query(trip_query, get_engine(), params=trip_params)
    except:
        trip_dist_df = pd.DataFrame()
    
    conn.close()
    
    if fuel_df.empty or trip_dist_df.empty:
        return pd.DataFrame(columns=['route', 'allocated_fuel'])
    
    # Calculate allocation
    results = []
    
    for bus in fuel_df['bus_number'].unique():
        bus_fuel = fuel_df[fuel_df['bus_number'] == bus]['total_fuel'].values[0]
        bus_trips = trip_dist_df[trip_dist_df['bus_number'] == bus]
        
        if bus_trips.empty:
            continue
        
        total_trips = bus_trips['trip_count'].sum()
        
        for _, row in bus_trips.iterrows():
            allocation = (row['trip_count'] / total_trips) * bus_fuel
            results.append({
                'route': row['route_name'],
                'allocated_fuel': allocation
            })
    
    if results:
        result_df = pd.DataFrame(results)
        result_df = result_df.groupby('route')['allocated_fuel'].sum().reset_index()
        return result_df
    
    return pd.DataFrame(columns=['route', 'allocated_fuel'])


def get_driver_costs_by_route(start_date=None, end_date=None):
    """
    Estimate driver/conductor costs per route based on trips and average wages.
    This is a simplified allocation based on trip count.
    """
    conn = get_connection()
    
    # Get average daily wage from payroll (simplified)
    try:
        payroll_query = "SELECT AVG(net_salary) as avg_salary FROM payroll"
        payroll_df = pd.read_sql_query(payroll_query, get_engine())
        avg_monthly_salary = payroll_df['avg_salary'].values[0] if not payroll_df.empty else 500
        if pd.isna(avg_monthly_salary):
            avg_monthly_salary = 500  # Default estimate
    except:
        avg_monthly_salary = 500
    
    # Estimate daily wage (assuming 26 working days)
    daily_wage = avg_monthly_salary / 26
    
    # Get trip counts per route
    trip_query = """
        SELECT 
            route_name as route,
            COUNT(*) as trip_count
        FROM trips
        WHERE route_name IS NOT NULL
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        trip_query += f" AND trip_date >= {ph}"
        params.append(start_date)
    
    if end_date:
        trip_query += f" AND trip_date <= {ph}"
        params.append(end_date)
    
    trip_query += " GROUP BY route_name"
    
    try:
        trip_df = pd.read_sql_query(trip_query, get_engine(), params=params)
    except:
        trip_df = pd.DataFrame()
    
    conn.close()
    
    if trip_df.empty:
        return pd.DataFrame(columns=['route', 'allocated_wages'])
    
    # Allocate wages based on trips (assuming 2 crew per trip: driver + conductor)
    # Estimate cost per trip based on daily wage / average trips per day
    avg_trips_per_day = 4  # Estimate
    cost_per_trip = (daily_wage * 2) / avg_trips_per_day  # 2 for driver + conductor
    
    trip_df['allocated_wages'] = trip_df['trip_count'] * cost_per_trip
    
    return trip_df[['route', 'allocated_wages']]


def calculate_route_profitability(start_date, end_date):
    """Calculate comprehensive route profitability"""
    
    # Get all revenue data
    income_df = get_route_income(start_date, end_date)
    trip_revenue_df = get_trip_revenue_by_route(start_date, end_date)
    
    # Get all cost data
    maintenance_df = get_maintenance_by_route(start_date, end_date)
    fuel_df = get_fuel_by_route(start_date, end_date)
    wages_df = get_driver_costs_by_route(start_date, end_date)
    
    # Combine revenue sources
    if not trip_revenue_df.empty:
        revenue_df = trip_revenue_df[['route', 'total_revenue', 'trip_count', 'total_passengers']].copy()
        revenue_df.columns = ['route', 'revenue', 'trips', 'passengers']
    elif not income_df.empty:
        revenue_df = income_df[['route', 'total_income', 'income_entries']].copy()
        revenue_df.columns = ['route', 'revenue', 'trips']
        revenue_df['passengers'] = 0
    else:
        return pd.DataFrame()
    
    # Merge all cost data
    result = revenue_df.copy()
    
    if not maintenance_df.empty:
        result = result.merge(maintenance_df, on='route', how='left')
    else:
        result['allocated_maintenance'] = 0
    
    if not fuel_df.empty:
        result = result.merge(fuel_df, on='route', how='left')
    else:
        result['allocated_fuel'] = 0
    
    if not wages_df.empty:
        result = result.merge(wages_df, on='route', how='left')
    else:
        result['allocated_wages'] = 0
    
    # Fill NaN with 0
    result = result.fillna(0)
    
    # Calculate totals
    result['total_costs'] = (
        result['allocated_maintenance'] + 
        result['allocated_fuel'] + 
        result['allocated_wages']
    )
    
    result['profit'] = result['revenue'] - result['total_costs']
    result['profit_margin'] = (result['profit'] / result['revenue'] * 100).round(2)
    result['profit_margin'] = result['profit_margin'].replace([float('inf'), float('-inf')], 0)
    
    # Revenue per trip
    result['revenue_per_trip'] = (result['revenue'] / result['trips']).round(2)
    result['cost_per_trip'] = (result['total_costs'] / result['trips']).round(2)
    result['profit_per_trip'] = (result['profit'] / result['trips']).round(2)
    
    # Handle division by zero
    result = result.replace([float('inf'), float('-inf')], 0)
    
    return result.sort_values('profit', ascending=False)


def get_monthly_route_trends(route_name, months=6):
    """Get monthly trends for a specific route"""
    conn = get_connection()
    
    today = datetime.now().date()
    results = []
    
    for i in range(months):
        # Calculate month start and end
        if i == 0:
            month_end = today
            month_start = today.replace(day=1)
        else:
            # Go back i months
            month_end = (today.replace(day=1) - timedelta(days=1))
            for _ in range(i - 1):
                month_end = (month_end.replace(day=1) - timedelta(days=1))
            month_start = month_end.replace(day=1)
        
        # Get trip revenue for this month
        ph = '%s' if USE_POSTGRES else '?'
        
        try:
            query = f"""
                SELECT 
                    SUM(revenue) as revenue,
                    SUM(passengers) as passengers,
                    COUNT(*) as trips
                FROM trips
                WHERE route_name = {ph}
                AND trip_date >= {ph}
                AND trip_date <= {ph}
            """
            
            cursor = conn.cursor()
            cursor.execute(query, (route_name, str(month_start), str(month_end)))
            row = cursor.fetchone()
            
            if row:
                if hasattr(row, 'keys'):
                    revenue = row['revenue'] or 0
                    passengers = row['passengers'] or 0
                    trips = row['trips'] or 0
                else:
                    revenue = row[0] or 0
                    passengers = row[1] or 0
                    trips = row[2] or 0
            else:
                revenue = passengers = trips = 0
            
            results.append({
                'month': month_start.strftime('%B %Y'),
                'month_start': month_start,
                'revenue': revenue,
                'passengers': passengers,
                'trips': trips
            })
        except Exception as e:
            print(f"Error getting monthly trends: {e}")
    
    conn.close()
    
    return pd.DataFrame(results)


# =============================================================================
# PAGE FUNCTION
# =============================================================================

def route_profitability_page():
    """Route profitability analysis page"""
    
    st.header("📊 Route Profitability Analysis")
    st.markdown("Analyze revenue, costs, and profit margins by route")
    st.markdown("---")
    
    # Period selector
    st.subheader("📅 Select Analysis Period")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        period_options = {
            "Last 7 Days": 7,
            "Last 14 Days": 14,
            "Last 30 Days": 30,
            "Last 3 Months": 90,
            "Last 6 Months": 180,
            "This Month": "this_month",
            "Last Month": "last_month",
            "This Year": "this_year",
            "Custom Range": "custom"
        }
        selected_period = st.selectbox("Select Period", list(period_options.keys()))
    
    today = datetime.now().date()
    
    if period_options[selected_period] == "this_month":
        start_date = today.replace(day=1)
        end_date = today
    elif period_options[selected_period] == "last_month":
        first_of_month = today.replace(day=1)
        end_date = first_of_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    elif period_options[selected_period] == "this_year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif period_options[selected_period] == "custom":
        with col2:
            start_date = st.date_input("From", value=today - timedelta(days=30), key="prof_start")
        with col3:
            end_date = st.date_input("To", value=today, key="prof_end")
    else:
        days = period_options[selected_period]
        start_date = today - timedelta(days=days)
        end_date = today
    
    st.info(f"📅 Analyzing data from **{start_date}** to **{end_date}**")
    st.markdown("---")
    
    # Calculate profitability
    profit_df = calculate_route_profitability(str(start_date), str(end_date))
    
    if profit_df.empty:
        st.warning("No data available for the selected period. Make sure you have trips or income records.")
        st.info("💡 Tip: Use Trip Entry to record individual trips, or Income Entry for daily revenue.")
        return
    
    # Overall summary
    st.subheader("📈 Overall Summary")
    
    total_revenue = profit_df['revenue'].sum()
    total_costs = profit_df['total_costs'].sum()
    total_profit = profit_df['profit'].sum()
    overall_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    total_trips = profit_df['trips'].sum()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💰 Total Revenue", f"${total_revenue:,.2f}")
    with col2:
        st.metric("💸 Total Costs", f"${total_costs:,.2f}")
    with col3:
        delta_color = "normal" if total_profit >= 0 else "inverse"
        st.metric("📊 Net Profit", f"${total_profit:,.2f}", 
                 delta=f"{overall_margin:.1f}% margin",
                 delta_color=delta_color)
    with col4:
        st.metric("🚌 Total Trips", f"{int(total_trips):,}")
    with col5:
        profit_per_trip = total_profit / total_trips if total_trips > 0 else 0
        st.metric("💵 Profit/Trip", f"${profit_per_trip:.2f}")
    
    st.markdown("---")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Profitability Overview", 
        "📈 Charts", 
        "🔍 Route Details",
        "📉 Cost Breakdown",
        "📅 Trends"
    ])
    
    with tab1:
        st.subheader("Route Profitability Summary")
        
        # Color code by profitability
        def highlight_profit(val):
            if val > 0:
                return 'background-color: #d4edda'  # Green
            elif val < 0:
                return 'background-color: #f8d7da'  # Red
            return ''
        
        # Prepare display dataframe
        display_df = profit_df[[
            'route', 'trips', 'revenue', 'total_costs', 'profit', 'profit_margin',
            'revenue_per_trip', 'cost_per_trip', 'profit_per_trip'
        ]].copy()
        
        display_df.columns = [
            'Route', 'Trips', 'Revenue ($)', 'Total Costs ($)', 'Profit ($)', 
            'Margin (%)', 'Rev/Trip ($)', 'Cost/Trip ($)', 'Profit/Trip ($)'
        ]
        
        # Round values
        for col in display_df.columns:
            if col not in ['Route', 'Trips']:
                display_df[col] = display_df[col].round(2)
        
        st.dataframe(
            display_df.style.applymap(highlight_profit, subset=['Profit ($)']),
            use_container_width=True,
            hide_index=True
        )
        
        # Profitable vs unprofitable routes
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ✅ Most Profitable Routes")
            profitable = profit_df[profit_df['profit'] > 0].head(5)
            for _, row in profitable.iterrows():
                st.write(f"🟢 **{row['route']}**: ${row['profit']:,.2f} ({row['profit_margin']:.1f}% margin)")
        
        with col2:
            st.markdown("### ⚠️ Underperforming Routes")
            unprofitable = profit_df[profit_df['profit'] <= 0].head(5)
            if not unprofitable.empty:
                for _, row in unprofitable.iterrows():
                    st.write(f"🔴 **{row['route']}**: ${row['profit']:,.2f} ({row['profit_margin']:.1f}% margin)")
            else:
                st.success("All routes are profitable! 🎉")
    
    with tab2:
        st.subheader("Profitability Charts")
        
        # Profit by route bar chart
        fig = go.Figure()
        
        colors = ['green' if p >= 0 else 'red' for p in profit_df['profit']]
        
        fig.add_trace(go.Bar(
            x=profit_df['route'],
            y=profit_df['profit'],
            marker_color=colors,
            name='Profit'
        ))
        
        fig.update_layout(
            title='Profit by Route',
            xaxis_title='Route',
            yaxis_title='Profit ($)',
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Revenue vs Costs comparison
        fig2 = go.Figure()
        
        fig2.add_trace(go.Bar(
            x=profit_df['route'],
            y=profit_df['revenue'],
            name='Revenue',
            marker_color='blue'
        ))
        
        fig2.add_trace(go.Bar(
            x=profit_df['route'],
            y=profit_df['total_costs'],
            name='Costs',
            marker_color='red'
        ))
        
        fig2.update_layout(
            title='Revenue vs Costs by Route',
            xaxis_title='Route',
            yaxis_title='Amount ($)',
            barmode='group'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # Profit margin pie chart
        fig3 = px.pie(
            profit_df[profit_df['profit'] > 0].head(10),
            values='profit',
            names='route',
            title='Profit Distribution (Top 10 Profitable Routes)'
        )
        st.plotly_chart(fig3, use_container_width=True)
        
        # Margin comparison
        fig4 = px.bar(
            profit_df,
            x='route',
            y='profit_margin',
            title='Profit Margin by Route (%)',
            color='profit_margin',
            color_continuous_scale=['red', 'yellow', 'green'],
            labels={'profit_margin': 'Margin (%)'}
        )
        fig4.add_hline(y=0, line_dash="dash", line_color="black")
        st.plotly_chart(fig4, use_container_width=True)
    
    with tab3:
        st.subheader("🔍 Detailed Route Analysis")
        
        # Route selector
        route_options = profit_df['route'].tolist()
        selected_route = st.selectbox("Select Route for Detailed Analysis", route_options)
        
        if selected_route:
            route_data = profit_df[profit_df['route'] == selected_route].iloc[0]
            
            st.markdown(f"### Route: {selected_route}")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Revenue", f"${route_data['revenue']:,.2f}")
            with col2:
                st.metric("Total Costs", f"${route_data['total_costs']:,.2f}")
            with col3:
                profit_color = "normal" if route_data['profit'] >= 0 else "inverse"
                st.metric("Profit", f"${route_data['profit']:,.2f}", 
                         delta=f"{route_data['profit_margin']:.1f}%",
                         delta_color=profit_color)
            with col4:
                st.metric("Trips", int(route_data['trips']))
            
            st.markdown("---")
            
            # Cost breakdown
            st.markdown("#### Cost Breakdown")
            
            cost_data = {
                'Category': ['Fuel', 'Maintenance', 'Wages'],
                'Amount': [
                    route_data['allocated_fuel'],
                    route_data['allocated_maintenance'],
                    route_data['allocated_wages']
                ]
            }
            
            cost_df = pd.DataFrame(cost_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(
                    cost_df,
                    values='Amount',
                    names='Category',
                    title='Cost Distribution'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Cost Details:**")
                st.write(f"- ⛽ Fuel: ${route_data['allocated_fuel']:,.2f}")
                st.write(f"- 🔧 Maintenance: ${route_data['allocated_maintenance']:,.2f}")
                st.write(f"- 👥 Wages: ${route_data['allocated_wages']:,.2f}")
                st.write(f"- **Total: ${route_data['total_costs']:,.2f}**")
            
            st.markdown("---")
            
            # Per-trip metrics
            st.markdown("#### Per-Trip Metrics")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Revenue/Trip", f"${route_data['revenue_per_trip']:.2f}")
            with col2:
                st.metric("Cost/Trip", f"${route_data['cost_per_trip']:.2f}")
            with col3:
                st.metric("Profit/Trip", f"${route_data['profit_per_trip']:.2f}")
            
            # Passengers if available
            if 'passengers' in route_data and route_data['passengers'] > 0:
                st.markdown("---")
                st.markdown("#### Passenger Metrics")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Passengers", f"{int(route_data['passengers']):,}")
                with col2:
                    avg_pass = route_data['passengers'] / route_data['trips'] if route_data['trips'] > 0 else 0
                    st.metric("Avg Passengers/Trip", f"{avg_pass:.1f}")
                with col3:
                    rev_per_pass = route_data['revenue'] / route_data['passengers'] if route_data['passengers'] > 0 else 0
                    st.metric("Revenue/Passenger", f"${rev_per_pass:.2f}")
    
    with tab4:
        st.subheader("📉 Cost Analysis")
        
        # Aggregate costs
        total_fuel = profit_df['allocated_fuel'].sum()
        total_maint = profit_df['allocated_maintenance'].sum()
        total_wages = profit_df['allocated_wages'].sum()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("⛽ Total Fuel Costs", f"${total_fuel:,.2f}")
        with col2:
            st.metric("🔧 Total Maintenance", f"${total_maint:,.2f}")
        with col3:
            st.metric("👥 Total Wages", f"${total_wages:,.2f}")
        
        st.markdown("---")
        
        # Cost breakdown chart
        cost_breakdown = pd.DataFrame({
            'Category': ['Fuel', 'Maintenance', 'Wages'],
            'Amount': [total_fuel, total_maint, total_wages]
        })
        
        fig = px.pie(
            cost_breakdown,
            values='Amount',
            names='Category',
            title='Overall Cost Distribution'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Cost per route stacked bar
        fig2 = go.Figure()
        
        fig2.add_trace(go.Bar(
            x=profit_df['route'],
            y=profit_df['allocated_fuel'],
            name='Fuel',
            marker_color='orange'
        ))
        
        fig2.add_trace(go.Bar(
            x=profit_df['route'],
            y=profit_df['allocated_maintenance'],
            name='Maintenance',
            marker_color='blue'
        ))
        
        fig2.add_trace(go.Bar(
            x=profit_df['route'],
            y=profit_df['allocated_wages'],
            name='Wages',
            marker_color='green'
        ))
        
        fig2.update_layout(
            title='Cost Breakdown by Route',
            xaxis_title='Route',
            yaxis_title='Cost ($)',
            barmode='stack'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # Cost efficiency ranking
        st.markdown("### Cost Efficiency Ranking")
        st.caption("Routes ranked by cost-to-revenue ratio (lower is better)")
        
        profit_df['cost_ratio'] = (profit_df['total_costs'] / profit_df['revenue'] * 100).round(2)
        profit_df['cost_ratio'] = profit_df['cost_ratio'].replace([float('inf'), float('-inf')], 0)
        
        efficiency_df = profit_df[['route', 'revenue', 'total_costs', 'cost_ratio']].sort_values('cost_ratio')
        efficiency_df.columns = ['Route', 'Revenue ($)', 'Costs ($)', 'Cost Ratio (%)']
        
        st.dataframe(efficiency_df, use_container_width=True, hide_index=True)
    
    with tab5:
        st.subheader("📅 Monthly Trends")
        
        # Select route for trend analysis
        trend_route = st.selectbox("Select Route for Trend Analysis", profit_df['route'].tolist(), key="trend_route")
        
        if trend_route:
            trend_df = get_monthly_route_trends(trend_route, months=6)
            
            if not trend_df.empty and trend_df['revenue'].sum() > 0:
                # Reverse for chronological order
                trend_df = trend_df.iloc[::-1].reset_index(drop=True)
                
                # Revenue trend
                fig = px.line(
                    trend_df,
                    x='month',
                    y='revenue',
                    title=f'Monthly Revenue Trend: {trend_route}',
                    markers=True
                )
                fig.update_traces(fill='tozeroy')
                st.plotly_chart(fig, use_container_width=True)
                
                # Trips and passengers
                fig2 = go.Figure()
                
                fig2.add_trace(go.Bar(
                    x=trend_df['month'],
                    y=trend_df['trips'],
                    name='Trips',
                    marker_color='blue'
                ))
                
                fig2.add_trace(go.Scatter(
                    x=trend_df['month'],
                    y=trend_df['passengers'],
                    name='Passengers',
                    yaxis='y2',
                    line=dict(color='green', width=2),
                    mode='lines+markers'
                ))
                
                fig2.update_layout(
                    title=f'Monthly Trips & Passengers: {trend_route}',
                    yaxis=dict(title='Trips'),
                    yaxis2=dict(title='Passengers', overlaying='y', side='right')
                )
                
                st.plotly_chart(fig2, use_container_width=True)
                
                # Monthly table
                st.markdown("### Monthly Summary")
                display_trend = trend_df[['month', 'trips', 'passengers', 'revenue']].copy()
                display_trend.columns = ['Month', 'Trips', 'Passengers', 'Revenue ($)']
                st.dataframe(display_trend, use_container_width=True, hide_index=True)
            else:
                st.info(f"No historical data available for {trend_route}")
        
        st.markdown("---")
        
        # Seasonal insights
        st.markdown("### 📊 Seasonal Insights")
        st.info("""
        **Recommendations based on profitability analysis:**
        
        1. **High-profit routes** - Consider increasing frequency or capacity
        2. **Low-margin routes** - Review pricing or reduce costs
        3. **Negative-profit routes** - Evaluate whether to discontinue or restructure
        4. **High fuel cost routes** - Consider more fuel-efficient buses
        5. **High maintenance routes** - May indicate road conditions or vehicle issues
        """)
    
    # Export section
    st.markdown("---")
    st.subheader("📥 Export Report")
    
    csv = profit_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Profitability Report (CSV)",
        data=csv,
        file_name=f"route_profitability_{start_date}_{end_date}.csv",
        mime="text/csv"
    )
