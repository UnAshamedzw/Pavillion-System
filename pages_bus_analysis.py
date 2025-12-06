"""
pages_bus_analysis.py - Comprehensive Bus-by-Bus Analysis Dashboard
WITH CONDUCTOR SUPPORT and Enhanced Filtering
Detailed financial and operational analysis for individual buses
NOTE: Uses registration_number as bus identifier throughout
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES
from io import BytesIO
from audit_logger import AuditLogger

def get_bus_data(registration_number=None, start_date=None, end_date=None, route=None, driver=None, conductor=None):
    """
    Fetch income and maintenance data for bus analysis WITH CONDUCTOR FILTER
    Uses registration_number as the bus identifier (stored in bus_number field)
    
    Returns: tuple of (income_df, maintenance_df)
    """
    conn = get_connection()
    
    # Use correct placeholder for database type
    ph = '%s' if USE_POSTGRES else '?'
    
    # Build income query
    income_query = "SELECT * FROM income WHERE 1=1"
    income_params = []
    
    if registration_number and registration_number != "All Buses":
        income_query += f" AND bus_number = {ph}"
        income_params.append(registration_number)
    
    if start_date:
        income_query += f" AND date >= {ph}"
        income_params.append(start_date)
    
    if end_date:
        income_query += f" AND date <= {ph}"
        income_params.append(end_date)
    
    if route and route != "All Routes":
        income_query += f" AND route = {ph}"
        income_params.append(route)
    
    if driver and driver != "All Drivers":
        income_query += f" AND driver_name = {ph}"
        income_params.append(driver)
    
    # NEW: Conductor filter
    if conductor and conductor != "All Conductors":
        income_query += f" AND conductor_name = {ph}"
        income_params.append(conductor)
    
    income_df = pd.read_sql_query(income_query, get_engine(), params=tuple(income_params) if income_params else None)
    
    # Convert amount to numeric if needed
    if 'amount' in income_df.columns:
        income_df['amount'] = pd.to_numeric(income_df['amount'], errors='coerce')
    
    # Build maintenance query
    maint_query = "SELECT * FROM maintenance WHERE 1=1"
    maint_params = []
    
    if registration_number and registration_number != "All Buses":
        maint_query += f" AND bus_number = {ph}"
        maint_params.append(registration_number)
    
    if start_date:
        maint_query += f" AND date >= {ph}"
        maint_params.append(start_date)
    
    if end_date:
        maint_query += f" AND date <= {ph}"
        maint_params.append(end_date)
    
    maintenance_df = pd.read_sql_query(maint_query, get_engine(), params=tuple(maint_params) if maint_params else None)
    
    # Convert cost to numeric if needed
    if 'cost' in maintenance_df.columns:
        maintenance_df['cost'] = pd.to_numeric(maintenance_df['cost'], errors='coerce')
    
    conn.close()
    
    return income_df, maintenance_df


def get_available_filters():
    """Get all available buses, routes, drivers, and conductors for filtering"""
    conn = get_connection()
    
    # Get buses
    buses_df = pd.read_sql_query("SELECT DISTINCT bus_number FROM income ORDER BY bus_number", get_engine())
    buses = ["All Buses"] + buses_df['bus_number'].tolist()
    
    # Get routes
    routes_df = pd.read_sql_query("SELECT DISTINCT route FROM income ORDER BY route", get_engine())
    routes = ["All Routes"] + routes_df['route'].tolist()
    
    # Get drivers
    drivers_df = pd.read_sql_query("SELECT DISTINCT driver_name FROM income WHERE driver_name IS NOT NULL ORDER BY driver_name", get_engine())
    drivers = ["All Drivers"] + drivers_df['driver_name'].tolist()
    
    # NEW: Get conductors
    conductors_df = pd.read_sql_query("SELECT DISTINCT conductor_name FROM income WHERE conductor_name IS NOT NULL ORDER BY conductor_name", get_engine())
    conductors = ["All Conductors"] + conductors_df['conductor_name'].tolist()
    
    conn.close()
    
    return buses, routes, drivers, conductors


def create_revenue_vs_expenses_chart(income_df, maintenance_df):
    """Create a line chart showing daily revenue vs expenses"""
    
    if income_df.empty and maintenance_df.empty:
        return None
    
    # Aggregate income by date
    if not income_df.empty:
        income_by_date = income_df.groupby('date')['amount'].sum().reset_index()
        income_by_date.columns = ['date', 'revenue']
    else:
        income_by_date = pd.DataFrame(columns=['date', 'revenue'])
    
    # Aggregate maintenance by date
    if not maintenance_df.empty:
        maint_by_date = maintenance_df.groupby('date')['cost'].sum().reset_index()
        maint_by_date.columns = ['date', 'expenses']
    else:
        maint_by_date = pd.DataFrame(columns=['date', 'expenses'])
    
    # Merge data
    combined = pd.merge(income_by_date, maint_by_date, on='date', how='outer').fillna(0)
    combined = combined.sort_values('date')
    
    # Create the chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=combined['date'],
        y=combined['revenue'],
        mode='lines+markers',
        name='Revenue',
        line=dict(color='green', width=3),
        marker=dict(size=8)
    ))
    
    fig.add_trace(go.Scatter(
        x=combined['date'],
        y=combined['expenses'],
        mode='lines+markers',
        name='Expenses',
        line=dict(color='red', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title='Daily Revenue vs Expenses',
        xaxis_title='Date',
        yaxis_title='Amount ($)',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig


def create_profit_chart(income_df, maintenance_df):
    """Create a bar chart showing daily profit/loss"""
    
    if income_df.empty and maintenance_df.empty:
        return None
    
    # Aggregate data
    if not income_df.empty:
        income_by_date = income_df.groupby('date')['amount'].sum().reset_index()
        income_by_date.columns = ['date', 'revenue']
    else:
        income_by_date = pd.DataFrame(columns=['date', 'revenue'])
    
    if not maintenance_df.empty:
        maint_by_date = maintenance_df.groupby('date')['cost'].sum().reset_index()
        maint_by_date.columns = ['date', 'expenses']
    else:
        maint_by_date = pd.DataFrame(columns=['date', 'expenses'])
    
    # Merge and calculate profit
    combined = pd.merge(income_by_date, maint_by_date, on='date', how='outer').fillna(0)
    combined['profit'] = combined['revenue'] - combined['expenses']
    combined = combined.sort_values('date')
    
    # Color based on profit/loss
    colors = ['green' if x >= 0 else 'red' for x in combined['profit']]
    
    fig = go.Figure(data=[
        go.Bar(
            x=combined['date'],
            y=combined['profit'],
            marker_color=colors,
            name='Profit/Loss'
        )
    ])
    
    fig.update_layout(
        title='Daily Profit/Loss',
        xaxis_title='Date',
        yaxis_title='Profit/Loss ($)',
        template='plotly_white',
        height=400
    )
    
    return fig


def export_to_excel(income_df, maintenance_df, summary_stats):
    """Export analysis data to Excel file with multiple sheets"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        summary_df = pd.DataFrame([summary_stats])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Income sheet
        if not income_df.empty:
            income_df.to_excel(writer, sheet_name='Income Records', index=False)
        
        # Maintenance sheet
        if not maintenance_df.empty:
            maintenance_df.to_excel(writer, sheet_name='Maintenance Records', index=False)
        
        # Daily summary sheet
        if not income_df.empty or not maintenance_df.empty:
            # Create daily summary
            if not income_df.empty:
                daily_income = income_df.groupby('date')['amount'].sum().reset_index()
                daily_income.columns = ['date', 'revenue']
            else:
                daily_income = pd.DataFrame(columns=['date', 'revenue'])
            
            if not maintenance_df.empty:
                daily_maint = maintenance_df.groupby('date')['cost'].sum().reset_index()
                daily_maint.columns = ['date', 'expenses']
            else:
                daily_maint = pd.DataFrame(columns=['date', 'expenses'])
            
            daily_summary = pd.merge(daily_income, daily_maint, on='date', how='outer').fillna(0)
            daily_summary['profit'] = daily_summary['revenue'] - daily_summary['expenses']
            daily_summary.to_excel(writer, sheet_name='Daily Summary', index=False)
        
        # NEW: Driver performance sheet
        if not income_df.empty and 'driver_name' in income_df.columns:
            driver_summary = income_df.groupby('driver_name').agg({
                'amount': ['sum', 'count', 'mean']
            }).reset_index()
            driver_summary.columns = ['Driver', 'Total Revenue', 'Trips', 'Avg per Trip']
            driver_summary.to_excel(writer, sheet_name='Driver Performance', index=False)
        
        # NEW: Conductor performance sheet
        if not income_df.empty and 'conductor_name' in income_df.columns:
            conductor_summary = income_df.groupby('conductor_name').agg({
                'amount': ['sum', 'count', 'mean']
            }).reset_index()
            conductor_summary.columns = ['Conductor', 'Total Revenue', 'Trips', 'Avg per Trip']
            conductor_summary.to_excel(writer, sheet_name='Conductor Performance', index=False)
    
    output.seek(0)
    return output


def bus_analysis_page():
    """
    Main Bus Analysis Dashboard WITH CONDUCTOR SUPPORT
    Comprehensive financial and operational performance analysis
    """
    
    st.header("🚌 Bus-by-Bus Analysis Dashboard")
    st.markdown("Detailed financial and operational performance analysis with driver and conductor tracking")
    st.markdown("---")
    
    # Get available filter options
    buses, routes, drivers, conductors = get_available_filters()
    
    # Filter Section
    with st.expander("🔍 Analysis Filters", expanded=True):
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            selected_bus = st.selectbox("🚌 Registration", buses, key="bus_filter")
        
        with col2:
            selected_route = st.selectbox("🛣️ Route", routes, key="route_filter")
        
        with col3:
            selected_driver = st.selectbox("👨‍✈️ Driver", drivers, key="driver_filter")
        
        with col4:
            # NEW: Conductor filter
            selected_conductor = st.selectbox("👨‍💼 Conductor", conductors, key="conductor_filter")
        
        with col5:
            date_preset = st.selectbox(
                "📅 Period",
                ["Last 7 Days", "Last 30 Days", "Last 90 Days", "This Year", "Custom"]
            )
        
        # Date range inputs
        if date_preset == "Custom":
            col_a, col_b = st.columns(2)
            with col_a:
                start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
            with col_b:
                end_date = st.date_input("End Date", datetime.now())
        else:
            end_date = datetime.now().date()
            if date_preset == "Last 7 Days":
                start_date = end_date - timedelta(days=7)
            elif date_preset == "Last 30 Days":
                start_date = end_date - timedelta(days=30)
            elif date_preset == "Last 90 Days":
                start_date = end_date - timedelta(days=90)
            else:  # This Year
                start_date = datetime(datetime.now().year, 1, 1).date()
        
        if st.button("📊 Generate Analysis", width="stretch", type="primary"):
            st.session_state['run_analysis'] = True
    
    st.markdown("---")
    
    # Run analysis if button clicked or already run
    if st.session_state.get('run_analysis', False):
        
        # Fetch data WITH CONDUCTOR FILTER
        with st.spinner("Fetching data..."):
            income_df, maintenance_df = get_bus_data(
                registration_number=selected_bus if selected_bus != "All Buses" else None,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                route=selected_route if selected_route != "All Routes" else None,
                driver=selected_driver if selected_driver != "All Drivers" else None,
                conductor=selected_conductor if selected_conductor != "All Conductors" else None
            )
        
        # Calculate summary statistics
        total_revenue = income_df['amount'].sum() if not income_df.empty else 0
        total_expenses = maintenance_df['cost'].sum() if not maintenance_df.empty else 0
        total_profit = total_revenue - total_expenses
        num_records = len(income_df) if not income_df.empty else 0
        num_maintenance = len(maintenance_df) if not maintenance_df.empty else 0
        
        # Average per record
        avg_revenue_per_record = total_revenue / num_records if num_records > 0 else 0
        
        # Display Key Metrics
        st.subheader("📊 Performance Summary")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "💰 Total Revenue",
                f"${total_revenue:,.2f}",
                delta=None
            )
        
        with col2:
            st.metric(
                "🔧 Total Expenses",
                f"${total_expenses:,.2f}",
                delta=None
            )
        
        with col3:
            profit_color = "normal" if total_profit >= 0 else "inverse"
            st.metric(
                "💵 Net Profit/Loss",
                f"${total_profit:,.2f}",
                delta=f"{(total_profit/total_revenue*100):.1f}%" if total_revenue > 0 else "0%"
            )
        
        with col4:
            st.metric(
                "🚌 Income Records",
                f"{num_records:,}",
                delta=None
            )
        
        with col5:
            st.metric(
                "🔧 Maintenance Events",
                f"{num_maintenance:,}",
                delta=None
            )
        
        # Additional metrics
        col6, col7, col8 = st.columns(3)
        
        with col6:
            st.metric(
                "📈 Avg Revenue/Record",
                f"${avg_revenue_per_record:,.2f}"
            )
        
        with col7:
            profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            st.metric(
                "📊 Profit Margin",
                f"{profit_margin:.1f}%"
            )
        
        with col8:
            avg_expense = total_expenses / num_maintenance if num_maintenance > 0 else 0
            st.metric(
                "🔧 Avg Maintenance Cost",
                f"${avg_expense:,.2f}"
            )
        
        st.markdown("---")
        
        # Charts Section
        st.subheader("📈 Visual Analysis")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Revenue vs Expenses",
            "💵 Profit/Loss",
            "📋 Income Details",
            "🔧 Maintenance Details",
            "👥 Staff Performance"
        ])
        
        with tab1:
            fig_revenue = create_revenue_vs_expenses_chart(income_df, maintenance_df)
            if fig_revenue:
                st.plotly_chart(fig_revenue, use_container_width=True)
            else:
                st.info("No data available for chart")
        
        with tab2:
            fig_profit = create_profit_chart(income_df, maintenance_df)
            if fig_profit:
                st.plotly_chart(fig_profit, use_container_width=True)
            else:
                st.info("No data available for chart")
        
        with tab3:
            if not income_df.empty:
                st.dataframe(
                    income_df.sort_values('date', ascending=False),
                    width="stretch",
                    height=400
                )
                
                # Route breakdown
                st.subheader("📍 Revenue by Route")
                route_summary = income_df.groupby('route')['amount'].agg(['sum', 'count', 'mean']).reset_index()
                route_summary.columns = ['Route', 'Total Revenue', 'Number of Records', 'Avg per Record']
                route_summary = route_summary.sort_values('Total Revenue', ascending=False)
                st.dataframe(route_summary, width="stretch")
            else:
                st.info("No income records found for the selected filters")
        
        with tab4:
            if not maintenance_df.empty:
                st.dataframe(
                    maintenance_df.sort_values('date', ascending=False),
                    width="stretch",
                    height=400
                )
                
                # Maintenance type breakdown
                if 'maintenance_type' in maintenance_df.columns:
                    st.subheader("🔧 Expenses by Maintenance Type")
                    maint_summary = maintenance_df.groupby('maintenance_type')['cost'].agg(['sum', 'count', 'mean']).reset_index()
                    maint_summary.columns = ['Maintenance Type', 'Total Cost', 'Number of Events', 'Avg Cost']
                    maint_summary = maint_summary.sort_values('Total Cost', ascending=False)
                    st.dataframe(maint_summary, width="stretch")
                    
                    # Pie chart of maintenance costs
                    fig_maint_pie = px.pie(
                        maint_summary,
                        values='Total Cost',
                        names='Maintenance Type',
                        title='Maintenance Cost Distribution'
                    )
                    st.plotly_chart(fig_maint_pie, use_container_width=True)
            else:
                st.info("No maintenance records found for the selected filters")
        
        with tab5:
            # NEW: Staff Performance Tab
            if not income_df.empty:
                col_staff1, col_staff2 = st.columns(2)
                
                with col_staff1:
                    # Driver breakdown
                    if 'driver_name' in income_df.columns:
                        st.subheader("👨‍✈️ Driver Performance")
                        driver_summary = income_df.groupby('driver_name')['amount'].agg(['sum', 'count', 'mean']).reset_index()
                        driver_summary.columns = ['Driver', 'Total Revenue', 'Records', 'Avg per Record']
                        driver_summary = driver_summary.sort_values('Total Revenue', ascending=False)
                        st.dataframe(driver_summary, width="stretch")
                        
                        # Driver chart
                        top_drivers = driver_summary.head(10)
                        fig_drivers = px.bar(
                            top_drivers,
                            x='Total Revenue',
                            y='Driver',
                            orientation='h',
                            title='Top 10 Drivers by Revenue'
                        )
                        st.plotly_chart(fig_drivers, use_container_width=True)
                
                with col_staff2:
                    # NEW: Conductor breakdown
                    if 'conductor_name' in income_df.columns:
                        st.subheader("👨‍💼 Conductor Performance")
                        conductor_summary = income_df.groupby('conductor_name')['amount'].agg(['sum', 'count', 'mean']).reset_index()
                        conductor_summary.columns = ['Conductor', 'Total Revenue', 'Records', 'Avg per Record']
                        conductor_summary = conductor_summary.sort_values('Total Revenue', ascending=False)
                        st.dataframe(conductor_summary, width="stretch")
                        
                        # Conductor chart
                        top_conductors = conductor_summary.head(10)
                        fig_conductors = px.bar(
                            top_conductors,
                            x='Total Revenue',
                            y='Conductor',
                            orientation='h',
                            title='Top 10 Conductors by Revenue'
                        )
                        st.plotly_chart(fig_conductors, use_container_width=True)
                
                # NEW: Driver-Conductor Team Analysis
                st.markdown("---")
                st.subheader("👥 Driver-Conductor Team Performance")
                
                if 'driver_name' in income_df.columns and 'conductor_name' in income_df.columns:
                    team_summary = income_df.groupby(['driver_name', 'conductor_name'])['amount'].agg(['sum', 'count', 'mean']).reset_index()
                    team_summary.columns = ['Driver', 'Conductor', 'Total Revenue', 'Records', 'Avg per Record']
                    team_summary = team_summary.sort_values('Total Revenue', ascending=False).head(20)
                    st.dataframe(team_summary, width="stretch")
            else:
                st.info("No income data available for staff performance analysis")
        
        st.markdown("---")
        
        # Export Section
        st.subheader("📥 Export Analysis")
        
        col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)
        
        with col_exp1:
            # Prepare summary stats for export
            summary_stats = {
                'Analysis Period': f"{start_date} to {end_date}",
                'Registration': selected_bus,
                'Route': selected_route,
                'Driver': selected_driver,
                'Conductor': selected_conductor,  # NEW
                'Total Revenue': total_revenue,
                'Total Expenses': total_expenses,
                'Net Profit': total_profit,
                'Income Records': num_records,
                'Maintenance Events': num_maintenance,
                'Avg Revenue per Record': avg_revenue_per_record,
                'Profit Margin %': profit_margin
            }
            
            # Export to Excel
            excel_data = export_to_excel(income_df, maintenance_df, summary_stats)
            
            st.download_button(
                label="📊 Download Excel Report",
                data=excel_data,
                file_name=f"bus_analysis_{selected_bus}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"
            )
        
        with col_exp2:
            # Export to CSV
            if not income_df.empty:
                csv_data = income_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download Income CSV",
                    data=csv_data,
                    file_name=f"income_{selected_bus}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    width="stretch"
                )
        
        with col_exp3:
            # Export maintenance to CSV
            if not maintenance_df.empty:
                csv_maint = maintenance_df.to_csv(index=False)
                st.download_button(
                    label="🔧 Download Maintenance CSV",
                    data=csv_maint,
                    file_name=f"maintenance_{selected_bus}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    width="stretch"
                )
        
        with col_exp4:
            # NEW: Export staff performance
            if not income_df.empty and 'driver_name' in income_df.columns and 'conductor_name' in income_df.columns:
                staff_data = income_df[['date', 'bus_number', 'driver_name', 'conductor_name', 'route', 'amount']].to_csv(index=False)
                st.download_button(
                    label="👥 Download Staff Report",
                    data=staff_data,
                    file_name=f"staff_performance_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    width="stretch"
                )
        
        # Log this analysis view
        AuditLogger.log_action(
            action_type="View",
            module="Bus Analysis",
            description=f"Generated analysis for {selected_bus}, Driver: {selected_driver}, Conductor: {selected_conductor} from {start_date} to {end_date}"
        )
    
    else:
        st.info("👆 Select your filters above and click 'Generate Analysis' to view the dashboard")