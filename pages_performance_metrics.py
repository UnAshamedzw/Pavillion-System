"""
pages_performance_metrics.py - Advanced Performance Metrics Dashboard
Comprehensive KPIs, trends, and benchmarking for fleet operations
FIXED: Handles missing tables gracefully
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sqlite3
import numpy as np
from audit_logger import AuditLogger

def table_exists(conn, table_name):
    """Check if a table exists in the database"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

def get_performance_data(start_date, end_date):
    """Fetch all performance-related data with error handling for missing tables"""
    conn = sqlite3.connect('bus_management.db')
    
    try:
        # Income data
        income_query = """
            SELECT * FROM income 
            WHERE date >= ? AND date <= ?
        """
        income_df = pd.read_sql_query(income_query, conn, params=[start_date, end_date])
    except Exception as e:
        st.error(f"Error loading income data: {e}")
        income_df = pd.DataFrame()
    
    try:
        # Maintenance data
        maint_query = """
            SELECT * FROM maintenance 
            WHERE date >= ? AND date <= ?
        """
        maintenance_df = pd.read_sql_query(maint_query, conn, params=[start_date, end_date])
    except Exception as e:
        st.warning(f"Maintenance table not found or empty: {e}")
        maintenance_df = pd.DataFrame()
    
    # Bus fleet data - handle if table doesn't exist
    try:
        if table_exists(conn, 'buses'):
            buses_df = pd.read_sql_query("SELECT * FROM buses", conn)
        else:
            # Create buses_df from income data
            if not income_df.empty and 'bus_number' in income_df.columns:
                unique_buses = income_df['bus_number'].unique()
                buses_df = pd.DataFrame({'bus_number': unique_buses})
                st.info("Note: Using bus numbers from income records. Create a 'buses' table for complete fleet data.")
            else:
                buses_df = pd.DataFrame()
    except Exception as e:
        st.warning(f"Could not load buses data: {e}")
        if not income_df.empty and 'bus_number' in income_df.columns:
            unique_buses = income_df['bus_number'].unique()
            buses_df = pd.DataFrame({'bus_number': unique_buses})
        else:
            buses_df = pd.DataFrame()
    
    # Driver data - handle if table doesn't exist
    try:
        if table_exists(conn, 'drivers'):
            drivers_df = pd.read_sql_query("SELECT * FROM drivers", conn)
        else:
            # Create drivers_df from income data
            if not income_df.empty and 'driver_name' in income_df.columns:
                unique_drivers = income_df['driver_name'].unique()
                drivers_df = pd.DataFrame({'name': unique_drivers})
            else:
                drivers_df = pd.DataFrame()
    except Exception as e:
        if not income_df.empty and 'driver_name' in income_df.columns:
            unique_drivers = income_df['driver_name'].unique()
            drivers_df = pd.DataFrame({'name': unique_drivers})
        else:
            drivers_df = pd.DataFrame()
    
    # Conductor data - handle if table doesn't exist
    try:
        if table_exists(conn, 'conductors'):
            conductors_df = pd.read_sql_query("SELECT * FROM conductors", conn)
        else:
            # Create conductors_df from income data
            if not income_df.empty and 'conductor_name' in income_df.columns:
                unique_conductors = income_df['conductor_name'].unique()
                conductors_df = pd.DataFrame({'name': unique_conductors})
            else:
                conductors_df = pd.DataFrame()
    except Exception as e:
        if not income_df.empty and 'conductor_name' in income_df.columns:
            unique_conductors = income_df['conductor_name'].unique()
            conductors_df = pd.DataFrame({'name': unique_conductors})
        else:
            conductors_df = pd.DataFrame()
    
    conn.close()
    
    return income_df, maintenance_df, buses_df, drivers_df, conductors_df


def calculate_kpis(income_df, maintenance_df, buses_df):
    """Calculate key performance indicators"""
    
    kpis = {}
    
    # Revenue KPIs
    kpis['total_revenue'] = income_df['amount'].sum() if not income_df.empty else 0
    kpis['avg_daily_revenue'] = income_df.groupby('date')['amount'].sum().mean() if not income_df.empty else 0
    kpis['total_trips'] = len(income_df) if not income_df.empty else 0
    kpis['avg_revenue_per_trip'] = kpis['total_revenue'] / kpis['total_trips'] if kpis['total_trips'] > 0 else 0
    
    # Cost KPIs
    kpis['total_maintenance_cost'] = maintenance_df['cost'].sum() if not maintenance_df.empty else 0
    kpis['avg_maintenance_cost'] = maintenance_df['cost'].mean() if not maintenance_df.empty else 0
    kpis['maintenance_events'] = len(maintenance_df) if not maintenance_df.empty else 0
    
    # Profitability KPIs
    kpis['net_profit'] = kpis['total_revenue'] - kpis['total_maintenance_cost']
    kpis['profit_margin'] = (kpis['net_profit'] / kpis['total_revenue'] * 100) if kpis['total_revenue'] > 0 else 0
    kpis['roi'] = (kpis['net_profit'] / kpis['total_maintenance_cost'] * 100) if kpis['total_maintenance_cost'] > 0 else 0
    
    # Fleet utilization
    kpis['active_buses'] = income_df['bus_number'].nunique() if not income_df.empty else 0
    kpis['total_buses'] = len(buses_df) if not buses_df.empty else kpis['active_buses']
    kpis['fleet_utilization'] = (kpis['active_buses'] / kpis['total_buses'] * 100) if kpis['total_buses'] > 0 else 0
    
    # Operational efficiency
    if not income_df.empty and 'bus_number' in income_df.columns:
        trips_per_bus = income_df.groupby('bus_number').size()
        kpis['avg_trips_per_bus'] = trips_per_bus.mean()
        kpis['max_trips_per_bus'] = trips_per_bus.max()
        kpis['min_trips_per_bus'] = trips_per_bus.min()
    else:
        kpis['avg_trips_per_bus'] = 0
        kpis['max_trips_per_bus'] = 0
        kpis['min_trips_per_bus'] = 0
    
    return kpis


def create_revenue_trend_chart(income_df):
    """Create daily revenue trend with moving average"""
    if income_df.empty:
        return None
    
    daily_revenue = income_df.groupby('date')['amount'].sum().reset_index()
    daily_revenue = daily_revenue.sort_values('date')
    
    # Calculate 7-day moving average
    daily_revenue['ma_7'] = daily_revenue['amount'].rolling(window=7, min_periods=1).mean()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_revenue['date'],
        y=daily_revenue['amount'],
        mode='lines+markers',
        name='Daily Revenue',
        line=dict(color='lightblue', width=2),
        marker=dict(size=6)
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_revenue['date'],
        y=daily_revenue['ma_7'],
        mode='lines',
        name='7-Day Moving Average',
        line=dict(color='blue', width=3, dash='dash')
    ))
    
    fig.update_layout(
        title='Revenue Trend Analysis',
        xaxis_title='Date',
        yaxis_title='Revenue ($)',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig


def create_bus_performance_chart(income_df):
    """Create top performing buses chart"""
    if income_df.empty:
        return None
    
    bus_performance = income_df.groupby('bus_number')['amount'].agg(['sum', 'count']).reset_index()
    bus_performance.columns = ['bus_number', 'total_revenue', 'trips']
    bus_performance['avg_revenue'] = bus_performance['total_revenue'] / bus_performance['trips']
    bus_performance = bus_performance.sort_values('total_revenue', ascending=True).tail(15)
    
    fig = go.Figure(data=[
        go.Bar(
            x=bus_performance['total_revenue'],
            y=bus_performance['bus_number'],
            orientation='h',
            marker=dict(
                color=bus_performance['total_revenue'],
                colorscale='Viridis',
                showscale=True
            ),
            text=bus_performance['total_revenue'].round(2),
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title='Top 15 Buses by Revenue',
        xaxis_title='Total Revenue ($)',
        yaxis_title='Bus Number',
        template='plotly_white',
        height=500
    )
    
    return fig


def create_route_performance_chart(income_df):
    """Create route performance comparison"""
    if income_df.empty or 'route' not in income_df.columns:
        return None
    
    route_perf = income_df.groupby('route').agg({
        'amount': ['sum', 'count', 'mean']
    }).reset_index()
    route_perf.columns = ['route', 'total_revenue', 'trips', 'avg_revenue']
    route_perf = route_perf.sort_values('total_revenue', ascending=False)
    
    fig = go.Figure(data=[
        go.Bar(
            name='Total Revenue',
            x=route_perf['route'],
            y=route_perf['total_revenue'],
            yaxis='y',
            offsetgroup=1,
            marker=dict(color='green')
        ),
        go.Bar(
            name='Number of Trips',
            x=route_perf['route'],
            y=route_perf['trips'],
            yaxis='y2',
            offsetgroup=2,
            marker=dict(color='orange')
        )
    ])
    
    fig.update_layout(
        title='Route Performance Overview',
        xaxis=dict(title='Route'),
        yaxis=dict(title='Total Revenue ($)', side='left'),
        yaxis2=dict(title='Number of Trips', side='right', overlaying='y'),
        template='plotly_white',
        barmode='group',
        height=400
    )
    
    return fig


def create_maintenance_analysis_chart(maintenance_df):
    """Create maintenance cost analysis"""
    if maintenance_df.empty:
        return None
    
    if 'maintenance_type' in maintenance_df.columns:
        maint_by_type = maintenance_df.groupby('maintenance_type')['cost'].sum().reset_index()
        maint_by_type = maint_by_type.sort_values('cost', ascending=False)
        
        fig = px.pie(
            maint_by_type,
            values='cost',
            names='maintenance_type',
            title='Maintenance Cost Distribution by Type',
            hole=0.4
        )
    else:
        maint_by_bus = maintenance_df.groupby('bus_number')['cost'].sum().reset_index()
        maint_by_bus = maint_by_bus.sort_values('cost', ascending=False).head(10)
        
        fig = px.bar(
            maint_by_bus,
            x='bus_number',
            y='cost',
            title='Top 10 Buses by Maintenance Cost'
        )
    
    fig.update_layout(
        template='plotly_white',
        height=400
    )
    
    return fig


def create_staff_performance_comparison(income_df):
    """Create driver vs conductor performance comparison"""
    if income_df.empty:
        return None, None
    
    driver_fig = None
    conductor_fig = None
    
    # Driver performance
    if 'driver_name' in income_df.columns:
        driver_perf = income_df.groupby('driver_name')['amount'].agg(['sum', 'count', 'mean']).reset_index()
        driver_perf.columns = ['driver', 'total_revenue', 'trips', 'avg_revenue']
        driver_perf = driver_perf.sort_values('total_revenue', ascending=True).tail(10)
        
        driver_fig = go.Figure(data=[
            go.Bar(
                x=driver_perf['total_revenue'],
                y=driver_perf['driver'],
                orientation='h',
                marker=dict(color='steelblue'),
                text=driver_perf['total_revenue'].round(2),
                textposition='auto'
            )
        ])
        
        driver_fig.update_layout(
            title='Top 10 Drivers by Revenue',
            xaxis_title='Total Revenue ($)',
            yaxis_title='Driver',
            template='plotly_white',
            height=400
        )
    
    # Conductor performance
    if 'conductor_name' in income_df.columns:
        conductor_perf = income_df.groupby('conductor_name')['amount'].agg(['sum', 'count', 'mean']).reset_index()
        conductor_perf.columns = ['conductor', 'total_revenue', 'trips', 'avg_revenue']
        conductor_perf = conductor_perf.sort_values('total_revenue', ascending=True).tail(10)
        
        conductor_fig = go.Figure(data=[
            go.Bar(
                x=conductor_perf['total_revenue'],
                y=conductor_perf['conductor'],
                orientation='h',
                marker=dict(color='darkorange'),
                text=conductor_perf['total_revenue'].round(2),
                textposition='auto'
            )
        ])
        
        conductor_fig.update_layout(
            title='Top 10 Conductors by Revenue',
            xaxis_title='Total Revenue ($)',
            yaxis_title='Conductor',
            template='plotly_white',
            height=400
        )
    
    return driver_fig, conductor_fig


def create_efficiency_metrics_chart(income_df, maintenance_df):
    """Create efficiency ratio analysis"""
    if income_df.empty:
        return None
    
    # Calculate efficiency by bus
    bus_revenue = income_df.groupby('bus_number')['amount'].sum()
    bus_maintenance = maintenance_df.groupby('bus_number')['cost'].sum() if not maintenance_df.empty else pd.Series()
    
    efficiency_df = pd.DataFrame({
        'revenue': bus_revenue,
        'maintenance': bus_maintenance
    }).fillna(0)
    
    efficiency_df['efficiency_ratio'] = (efficiency_df['revenue'] / efficiency_df['maintenance']).replace([np.inf, -np.inf], 0)
    efficiency_df = efficiency_df.sort_values('efficiency_ratio', ascending=False).head(15)
    efficiency_df = efficiency_df.reset_index()
    
    fig = go.Figure(data=[
        go.Scatter(
            x=efficiency_df['maintenance'],
            y=efficiency_df['revenue'],
            mode='markers+text',
            marker=dict(
                size=15,
                color=efficiency_df['efficiency_ratio'],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Efficiency Ratio")
            ),
            text=efficiency_df['bus_number'],
            textposition='top center'
        )
    ])
    
    fig.update_layout(
        title='Bus Efficiency: Revenue vs Maintenance Cost',
        xaxis_title='Maintenance Cost ($)',
        yaxis_title='Revenue ($)',
        template='plotly_white',
        height=500
    )
    
    return fig


def performance_metrics_page():
    """Main Performance Metrics Dashboard"""
    
    st.header("📊 Performance Metrics Dashboard")
    st.markdown("Comprehensive KPIs and performance analytics for fleet operations")
    st.markdown("---")
    
    # Date range selector
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        date_range = st.selectbox(
            "📅 Analysis Period",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "This Year", "Custom Range"],
            key="perf_date_range"
        )
    
    if date_range == "Custom Range":
        with col2:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
        with col3:
            end_date = st.date_input("End Date", datetime.now())
    else:
        end_date = datetime.now().date()
        if date_range == "Last 7 Days":
            start_date = end_date - timedelta(days=7)
        elif date_range == "Last 30 Days":
            start_date = end_date - timedelta(days=30)
        elif date_range == "Last 90 Days":
            start_date = end_date - timedelta(days=90)
        else:  # This Year
            start_date = datetime(datetime.now().year, 1, 1).date()
    
    # Refresh button
    if st.button("🔄 Refresh Metrics", type="primary", use_container_width=True):
        st.rerun()
    
    st.markdown("---")
    
    # Fetch data
    with st.spinner("Loading performance data..."):
        try:
            income_df, maintenance_df, buses_df, drivers_df, conductors_df = get_performance_data(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
        except Exception as e:
            st.error(f"Error loading data: {e}")
            st.info("Make sure you have income and maintenance data in your database.")
            return
    
    # Check if we have any data
    if income_df.empty:
        st.warning("⚠️ No income data found for the selected period. Please add some income records first.")
        return
    
    # Calculate KPIs
    kpis = calculate_kpis(income_df, maintenance_df, buses_df)
    
    # Display KPI Dashboard
    st.subheader("🎯 Key Performance Indicators")
    
    # Row 1: Revenue Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Total Revenue",
            f"${kpis['total_revenue']:,.2f}",
            help="Total revenue generated in the period"
        )
    
    with col2:
        st.metric(
            "📈 Avg Daily Revenue",
            f"${kpis['avg_daily_revenue']:,.2f}",
            help="Average revenue per day"
        )
    
    with col3:
        st.metric(
            "🎫 Total Trips",
            f"{kpis['total_trips']:,}",
            help="Total number of trips completed"
        )
    
    with col4:
        st.metric(
            "💵 Avg Revenue/Trip",
            f"${kpis['avg_revenue_per_trip']:,.2f}",
            help="Average revenue per trip"
        )
    
    # Row 2: Cost & Profitability
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric(
            "🔧 Maintenance Cost",
            f"${kpis['total_maintenance_cost']:,.2f}",
            help="Total maintenance expenses"
        )
    
    with col6:
        profit_delta = f"+${kpis['net_profit']:,.2f}" if kpis['net_profit'] >= 0 else f"-${abs(kpis['net_profit']):,.2f}"
        st.metric(
            "💎 Net Profit",
            f"${kpis['net_profit']:,.2f}",
            delta=profit_delta,
            help="Total profit after maintenance costs"
        )
    
    with col7:
        st.metric(
            "📊 Profit Margin",
            f"{kpis['profit_margin']:.1f}%",
            help="Profit as percentage of revenue"
        )
    
    with col8:
        st.metric(
            "📈 ROI",
            f"{kpis['roi']:.1f}%",
            help="Return on investment"
        )
    
    # Row 3: Fleet & Operational Metrics
    col9, col10, col11, col12 = st.columns(4)
    
    with col9:
        st.metric(
            "🚌 Active Buses",
            f"{kpis['active_buses']}/{kpis['total_buses']}",
            help="Number of buses in operation"
        )
    
    with col10:
        st.metric(
            "⚡ Fleet Utilization",
            f"{kpis['fleet_utilization']:.1f}%",
            help="Percentage of fleet in active use"
        )
    
    with col11:
        st.metric(
            "🎯 Avg Trips/Bus",
            f"{kpis['avg_trips_per_bus']:.1f}",
            help="Average trips per bus"
        )
    
    with col12:
        st.metric(
            "🛠️ Maintenance Events",
            f"{kpis['maintenance_events']}",
            help="Total maintenance events"
        )
    
    st.markdown("---")
    
    # Visualizations
    st.subheader("📈 Performance Trends & Analysis")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Revenue Trends",
        "🚌 Bus Performance",
        "🛣️ Route Analysis",
        "👥 Staff Performance",
        "🔧 Maintenance & Efficiency"
    ])
    
    with tab1:
        # Revenue trend
        fig_revenue_trend = create_revenue_trend_chart(income_df)
        if fig_revenue_trend:
            st.plotly_chart(fig_revenue_trend, use_container_width=True)
        else:
            st.info("No revenue data available for trend analysis")
        
        # Revenue statistics
        if not income_df.empty:
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            
            daily_revenue = income_df.groupby('date')['amount'].sum()
            
            with col_stat1:
                st.metric("📊 Highest Daily Revenue", f"${daily_revenue.max():,.2f}")
            
            with col_stat2:
                st.metric("📉 Lowest Daily Revenue", f"${daily_revenue.min():,.2f}")
            
            with col_stat3:
                st.metric("📈 Revenue Std Dev", f"${daily_revenue.std():,.2f}")
    
    with tab2:
        # Bus performance
        fig_bus_perf = create_bus_performance_chart(income_df)
        if fig_bus_perf:
            st.plotly_chart(fig_bus_perf, use_container_width=True)
        
        # Detailed bus metrics table
        if not income_df.empty:
            st.subheader("📋 Detailed Bus Performance Metrics")
            
            bus_metrics = income_df.groupby('bus_number').agg({
                'amount': ['sum', 'count', 'mean', 'std']
            }).reset_index()
            bus_metrics.columns = ['Bus Number', 'Total Revenue', 'Trips', 'Avg Revenue', 'Std Dev']
            
            # Add maintenance data
            if not maintenance_df.empty:
                bus_maint = maintenance_df.groupby('bus_number')['cost'].sum().reset_index()
                bus_maint.columns = ['Bus Number', 'Maintenance Cost']
                bus_metrics = bus_metrics.merge(bus_maint, on='Bus Number', how='left').fillna(0)
                bus_metrics['Net Profit'] = bus_metrics['Total Revenue'] - bus_metrics['Maintenance Cost']
                bus_metrics['Efficiency Ratio'] = (bus_metrics['Total Revenue'] / bus_metrics['Maintenance Cost']).replace([np.inf, -np.inf], 0)
            
            bus_metrics = bus_metrics.sort_values('Total Revenue', ascending=False)
            st.dataframe(bus_metrics, use_container_width=True, height=400)
    
    with tab3:
        # Route performance
        fig_route = create_route_performance_chart(income_df)
        if fig_route:
            st.plotly_chart(fig_route, use_container_width=True)
        else:
            st.info("Route data not available")
        
        # Route details table
        if not income_df.empty and 'route' in income_df.columns:
            st.subheader("🛣️ Route Performance Details")
            
            route_details = income_df.groupby('route').agg({
                'amount': ['sum', 'count', 'mean'],
                'bus_number': 'nunique'
            }).reset_index()
            route_details.columns = ['Route', 'Total Revenue', 'Trips', 'Avg Revenue/Trip', 'Buses Used']
            route_details = route_details.sort_values('Total Revenue', ascending=False)
            
            st.dataframe(route_details, use_container_width=True)
    
    with tab4:
        # Staff performance
        col_staff1, col_staff2 = st.columns(2)
        
        driver_fig, conductor_fig = create_staff_performance_comparison(income_df)
        
        with col_staff1:
            if driver_fig:
                st.plotly_chart(driver_fig, use_container_width=True)
            else:
                st.info("No driver data available")
        
        with col_staff2:
            if conductor_fig:
                st.plotly_chart(conductor_fig, use_container_width=True)
            else:
                st.info("No conductor data available")
        
        # Team performance
        if not income_df.empty and 'driver_name' in income_df.columns and 'conductor_name' in income_df.columns:
            st.subheader("👥 Top Performing Teams")
            
            team_perf = income_df.groupby(['driver_name', 'conductor_name'])['amount'].agg(['sum', 'count', 'mean']).reset_index()
            team_perf.columns = ['Driver', 'Conductor', 'Total Revenue', 'Trips', 'Avg Revenue']
            team_perf = team_perf.sort_values('Total Revenue', ascending=False).head(20)
            
            st.dataframe(team_perf, use_container_width=True)
    
    with tab5:
        # Maintenance analysis
        fig_maint = create_maintenance_analysis_chart(maintenance_df)
        if fig_maint:
            st.plotly_chart(fig_maint, use_container_width=True)
        else:
            st.info("No maintenance data available")
        
        # Efficiency scatter plot
        fig_efficiency = create_efficiency_metrics_chart(income_df, maintenance_df)
        if fig_efficiency:
            st.plotly_chart(fig_efficiency, use_container_width=True)
        
        # Efficiency metrics table
        if not income_df.empty and not maintenance_df.empty:
            st.subheader("⚡ Bus Efficiency Rankings")
            
            bus_revenue = income_df.groupby('bus_number')['amount'].sum()
            bus_maint = maintenance_df.groupby('bus_number')['cost'].sum()
            
            efficiency_table = pd.DataFrame({
                'Bus Number': bus_revenue.index,
                'Revenue': bus_revenue.values,
                'Maintenance Cost': [bus_maint.get(bus, 0) for bus in bus_revenue.index],
            })
            
            efficiency_table['Net Profit'] = efficiency_table['Revenue'] - efficiency_table['Maintenance Cost']
            efficiency_table['Efficiency Ratio'] = (efficiency_table['Revenue'] / efficiency_table['Maintenance Cost']).replace([np.inf, -np.inf], 0)
            efficiency_table['Profit Margin %'] = (efficiency_table['Net Profit'] / efficiency_table['Revenue'] * 100)
            
            efficiency_table = efficiency_table.sort_values('Efficiency Ratio', ascending=False)
            
            st.dataframe(efficiency_table, use_container_width=True, height=400)
    
    st.markdown("---")
    
    # Insights and Recommendations
    st.subheader("💡 Automated Insights")
    
    col_ins1, col_ins2, col_ins3 = st.columns(3)
    
    with col_ins1:
        st.info("**💰 Revenue Performance**")
        if kpis['profit_margin'] > 20:
            st.success(f"Excellent profit margin of {kpis['profit_margin']:.1f}%!")
        elif kpis['profit_margin'] > 10:
            st.warning(f"Moderate profit margin of {kpis['profit_margin']:.1f}%. Consider cost optimization.")
        else:
            st.error(f"Low profit margin of {kpis['profit_margin']:.1f}%. Review pricing and costs.")
    
    with col_ins2:
        st.info("**⚡ Fleet Utilization**")
        if kpis['fleet_utilization'] > 80:
            st.success(f"High utilization at {kpis['fleet_utilization']:.1f}%!")
        elif kpis['fleet_utilization'] > 60:
            st.warning(f"Moderate utilization at {kpis['fleet_utilization']:.1f}%. Potential for growth.")
        else:
            st.error(f"Low utilization at {kpis['fleet_utilization']:.1f}%. Many buses underutilized.")
    
    with col_ins3:
        st.info("**🔧 Maintenance Efficiency**")
        avg_maint_per_bus = kpis['total_maintenance_cost'] / kpis['active_buses'] if kpis['active_buses'] > 0 else 0
        st.metric("Avg Maintenance/Bus", f"${avg_maint_per_bus:,.2f}")
    
    # Log the view
    try:
        AuditLogger.log_action(
            action_type="View",
            module="Performance Metrics",
            description=f"Viewed performance metrics from {start_date} to {end_date}"
        )
    except Exception as e:
        pass  # Silently fail if audit logging is not available