"""
pages_driver_performance.py - Driver Performance Scoring Module
Pavillion Coaches Bus Management System
Automated performance metrics and scoring for drivers
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES
from audit_logger import AuditLogger
from auth import has_permission


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_all_drivers():
    """Get all drivers from employees table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, employee_id, full_name, phone, status, date_joined
        FROM employees 
        WHERE position LIKE '%Driver%'
        ORDER BY full_name
    """)
    
    drivers = cursor.fetchall()
    conn.close()
    return drivers


def get_driver_trips(driver_name=None, start_date=None, end_date=None):
    """
    Get trips for a driver or all drivers.
    Queries from income table for maximum compatibility with Excel imports.
    """
    conn = get_connection()
    
    # Query from income table which is the primary trip data source
    query = """
        SELECT 
            driver_name,
            date as trip_date,
            bus_number,
            route as route_name,
            departure_time,
            arrival_time,
            CASE 
                WHEN departure_time IS NOT NULL AND arrival_time IS NOT NULL 
                THEN EXTRACT(EPOCH FROM (arrival_time::time - departure_time::time))/60
                ELSE 0
            END as duration_minutes,
            COALESCE(passengers, 0) as passengers,
            COALESCE(amount, 0) as revenue,
            CASE WHEN passengers > 0 THEN amount / passengers ELSE 0 END as revenue_per_passenger,
            COALESCE(trip_type, 'Regular') as trip_type
        FROM income
        WHERE driver_name IS NOT NULL AND driver_name != ''
    """
    
    # Simpler version for SQLite
    if not USE_POSTGRES:
        query = """
            SELECT 
                driver_name,
                date as trip_date,
                bus_number,
                route as route_name,
                departure_time,
                arrival_time,
                0 as duration_minutes,
                COALESCE(passengers, 0) as passengers,
                COALESCE(amount, 0) as revenue,
                CASE WHEN passengers > 0 THEN amount / passengers ELSE 0 END as revenue_per_passenger,
                COALESCE(trip_type, 'Regular') as trip_type
            FROM income
            WHERE driver_name IS NOT NULL AND driver_name != ''
        """
    
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if driver_name:
        query += f" AND driver_name = {ph}"
        params.append(driver_name)
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(str(end_date))
    
    query += " ORDER BY date DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
        # Ensure numeric columns
        df['passengers'] = pd.to_numeric(df['passengers'], errors='coerce').fillna(0)
        df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0)
    except Exception as e:
        print(f"Error getting driver trips: {e}")
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_driver_incidents(driver_name=None, start_date=None, end_date=None):
    """Get disciplinary records/incidents for drivers"""
    conn = get_connection()
    
    query = """
        SELECT 
            e.full_name as driver_name,
            d.incident_date,
            d.incident_type,
            d.severity,
            d.description,
            d.action_taken
        FROM disciplinary_records d
        JOIN employees e ON d.employee_id = e.id
        WHERE e.position LIKE '%Driver%'
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if driver_name:
        query += f" AND e.full_name = {ph}"
        params.append(driver_name)
    
    if start_date:
        query += f" AND d.incident_date >= {ph}"
        params.append(start_date)
    
    if end_date:
        query += f" AND d.incident_date <= {ph}"
        params.append(end_date)
    
    query += " ORDER BY d.incident_date DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    except Exception as e:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_driver_leave_records(driver_name=None, start_date=None, end_date=None):
    """Get leave records for drivers"""
    conn = get_connection()
    
    query = """
        SELECT 
            e.full_name as driver_name,
            l.leave_type,
            l.start_date,
            l.end_date,
            l.days_requested,
            l.status
        FROM leave_records l
        JOIN employees e ON l.employee_id = e.id
        WHERE e.position LIKE '%Driver%'
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if driver_name:
        query += f" AND e.full_name = {ph}"
        params.append(driver_name)
    
    if start_date:
        query += f" AND l.start_date >= {ph}"
        params.append(start_date)
    
    if end_date:
        query += f" AND l.end_date <= {ph}"
        params.append(end_date)
    
    query += " ORDER BY l.start_date DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    except Exception as e:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_maintenance_issues_by_driver(start_date=None, end_date=None):
    """
    Get maintenance issues that could be attributed to drivers
    (e.g., accidents, driver-caused damage)
    """
    conn = get_connection()
    
    query = """
        SELECT 
            bus_number,
            date,
            maintenance_type,
            description,
            cost
        FROM maintenance
        WHERE LOWER(maintenance_type) LIKE '%accident%'
           OR LOWER(description) LIKE '%driver%'
           OR LOWER(description) LIKE '%accident%'
           OR LOWER(description) LIKE '%collision%'
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(start_date)
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(end_date)
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    except Exception as e:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_fuel_efficiency_by_driver(start_date=None, end_date=None):
    """
    Get fuel efficiency metrics per driver based on trips and fuel records.
    This is an approximation based on bus usage patterns.
    """
    conn = get_connection()
    
    # Get trips per driver per bus
    trip_query = """
        SELECT 
            driver_name,
            bus_number,
            COUNT(*) as trip_count,
            SUM(passengers) as total_passengers,
            SUM(revenue) as total_revenue
        FROM trips
        WHERE driver_name IS NOT NULL
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        trip_query += f" AND trip_date >= {ph}"
        params.append(start_date)
    
    if end_date:
        trip_query += f" AND trip_date <= {ph}"
        params.append(end_date)
    
    trip_query += " GROUP BY driver_name, bus_number"
    
    try:
        trip_df = pd.read_sql_query(trip_query, get_engine(), params=params)
    except Exception as e:
        trip_df = pd.DataFrame()
    
    # Get fuel efficiency per bus
    fuel_query = """
        SELECT 
            bus_number,
            AVG(fuel_efficiency) as avg_efficiency
        FROM fuel_records
        WHERE fuel_efficiency IS NOT NULL AND fuel_efficiency > 0
    """
    
    fuel_params = []
    if start_date:
        fuel_query += f" AND date >= {ph}"
        fuel_params.append(start_date)
    
    if end_date:
        fuel_query += f" AND date <= {ph}"
        fuel_params.append(end_date)
    
    fuel_query += " GROUP BY bus_number"
    
    try:
        fuel_df = pd.read_sql_query(fuel_query, get_engine(), params=fuel_params)
    except Exception as e:
        fuel_df = pd.DataFrame()
    
    conn.close()
    
    if trip_df.empty or fuel_df.empty:
        return pd.DataFrame()
    
    # Merge and calculate weighted efficiency per driver
    merged = trip_df.merge(fuel_df, on='bus_number', how='left')
    
    if merged.empty:
        return pd.DataFrame()
    
    # Weight efficiency by trip count
    merged['weighted_efficiency'] = merged['avg_efficiency'] * merged['trip_count']
    
    driver_eff = merged.groupby('driver_name').agg({
        'trip_count': 'sum',
        'weighted_efficiency': 'sum'
    }).reset_index()
    
    driver_eff['avg_efficiency'] = driver_eff['weighted_efficiency'] / driver_eff['trip_count']
    
    return driver_eff[['driver_name', 'avg_efficiency']]


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def calculate_driver_scores(start_date, end_date):
    """
    Calculate comprehensive driver performance scores.
    
    Scoring components (total 100 points):
    - Trip Volume (20 points): Number of trips completed
    - Revenue Generation (25 points): Total revenue generated
    - Passenger Load (15 points): Average passengers per trip
    - Punctuality (15 points): Based on trip completion rate
    - Safety Record (15 points): Based on incidents/accidents
    - Attendance (10 points): Based on leave patterns
    """
    
    # Get all data
    trips_df = get_driver_trips(start_date=start_date, end_date=end_date)
    incidents_df = get_driver_incidents(start_date=start_date, end_date=end_date)
    leave_df = get_driver_leave_records(start_date=start_date, end_date=end_date)
    
    if trips_df.empty:
        return pd.DataFrame()
    
    # Aggregate trip metrics per driver
    driver_metrics = trips_df.groupby('driver_name').agg({
        'trip_date': 'count',  # trip count
        'passengers': ['sum', 'mean'],
        'revenue': ['sum', 'mean'],
        'duration_minutes': 'mean'
    }).reset_index()
    
    driver_metrics.columns = ['driver_name', 'trip_count', 'total_passengers', 
                              'avg_passengers', 'total_revenue', 'avg_revenue', 
                              'avg_duration']
    
    # Calculate days worked
    days_worked = trips_df.groupby('driver_name')['trip_date'].nunique().reset_index()
    days_worked.columns = ['driver_name', 'days_worked']
    driver_metrics = driver_metrics.merge(days_worked, on='driver_name', how='left')
    
    # Calculate trips per day
    driver_metrics['trips_per_day'] = driver_metrics['trip_count'] / driver_metrics['days_worked']
    
    # Get incident counts
    if not incidents_df.empty:
        incident_counts = incidents_df.groupby('driver_name').size().reset_index(name='incident_count')
        
        # Weight by severity
        severity_weights = {'Minor': 1, 'Moderate': 2, 'Major': 3, 'Severe': 5}
        incidents_df['severity_weight'] = incidents_df['severity'].map(severity_weights).fillna(1)
        severity_score = incidents_df.groupby('driver_name')['severity_weight'].sum().reset_index(name='incident_severity')
        
        driver_metrics = driver_metrics.merge(incident_counts, on='driver_name', how='left')
        driver_metrics = driver_metrics.merge(severity_score, on='driver_name', how='left')
    else:
        driver_metrics['incident_count'] = 0
        driver_metrics['incident_severity'] = 0
    
    # Get leave days
    if not leave_df.empty:
        approved_leave = leave_df[leave_df['status'] == 'Approved']
        if not approved_leave.empty:
            leave_days = approved_leave.groupby('driver_name')['days_requested'].sum().reset_index(name='leave_days')
            driver_metrics = driver_metrics.merge(leave_days, on='driver_name', how='left')
        else:
            driver_metrics['leave_days'] = 0
    else:
        driver_metrics['leave_days'] = 0
    
    # Fill NaN values
    driver_metrics = driver_metrics.fillna(0)
    
    # Calculate scores
    
    # 1. Trip Volume Score (20 points)
    max_trips = driver_metrics['trip_count'].max()
    if max_trips > 0:
        driver_metrics['trip_score'] = (driver_metrics['trip_count'] / max_trips * 20).clip(0, 20)
    else:
        driver_metrics['trip_score'] = 0
    
    # 2. Revenue Score (25 points)
    max_revenue = driver_metrics['total_revenue'].max()
    if max_revenue > 0:
        driver_metrics['revenue_score'] = (driver_metrics['total_revenue'] / max_revenue * 25).clip(0, 25)
    else:
        driver_metrics['revenue_score'] = 0
    
    # 3. Passenger Load Score (15 points)
    max_avg_passengers = driver_metrics['avg_passengers'].max()
    if max_avg_passengers > 0:
        driver_metrics['passenger_score'] = (driver_metrics['avg_passengers'] / max_avg_passengers * 15).clip(0, 15)
    else:
        driver_metrics['passenger_score'] = 0
    
    # 4. Productivity Score (15 points) - based on trips per day
    max_trips_per_day = driver_metrics['trips_per_day'].max()
    if max_trips_per_day > 0:
        driver_metrics['productivity_score'] = (driver_metrics['trips_per_day'] / max_trips_per_day * 15).clip(0, 15)
    else:
        driver_metrics['productivity_score'] = 0
    
    # 5. Safety Score (15 points) - deduct for incidents
    # Start at 15, deduct based on incident severity
    driver_metrics['safety_score'] = (15 - driver_metrics['incident_severity']).clip(0, 15)
    
    # 6. Attendance Score (10 points)
    # Based on days worked vs expected (estimate 22 working days per month)
    period_days = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days
    expected_work_days = (period_days / 30) * 22  # Approximate work days
    
    if expected_work_days > 0:
        attendance_ratio = driver_metrics['days_worked'] / expected_work_days
        driver_metrics['attendance_score'] = (attendance_ratio * 10).clip(0, 10)
    else:
        driver_metrics['attendance_score'] = 10
    
    # Calculate total score
    driver_metrics['total_score'] = (
        driver_metrics['trip_score'] +
        driver_metrics['revenue_score'] +
        driver_metrics['passenger_score'] +
        driver_metrics['productivity_score'] +
        driver_metrics['safety_score'] +
        driver_metrics['attendance_score']
    ).round(1)
    
    # Assign grade
    def get_grade(score):
        if score >= 90:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 80:
            return 'A-'
        elif score >= 75:
            return 'B+'
        elif score >= 70:
            return 'B'
        elif score >= 65:
            return 'B-'
        elif score >= 60:
            return 'C+'
        elif score >= 55:
            return 'C'
        elif score >= 50:
            return 'C-'
        elif score >= 45:
            return 'D'
        else:
            return 'F'
    
    driver_metrics['grade'] = driver_metrics['total_score'].apply(get_grade)
    
    # Rank drivers
    driver_metrics['rank'] = driver_metrics['total_score'].rank(ascending=False, method='min').astype(int)
    
    return driver_metrics.sort_values('total_score', ascending=False)


def get_driver_trend(driver_name, months=6):
    """Get monthly performance trend for a driver"""
    today = datetime.now().date()
    results = []
    
    for i in range(months):
        if i == 0:
            month_end = today
            month_start = today.replace(day=1)
        else:
            month_end = (today.replace(day=1) - timedelta(days=1))
            for _ in range(i - 1):
                month_end = (month_end.replace(day=1) - timedelta(days=1))
            month_start = month_end.replace(day=1)
        
        # Get trips for this month
        trips = get_driver_trips(driver_name, str(month_start), str(month_end))
        
        if not trips.empty:
            results.append({
                'month': month_start.strftime('%B %Y'),
                'month_start': month_start,
                'trips': len(trips),
                'passengers': trips['passengers'].sum(),
                'revenue': trips['revenue'].sum(),
                'avg_passengers': trips['passengers'].mean()
            })
        else:
            results.append({
                'month': month_start.strftime('%B %Y'),
                'month_start': month_start,
                'trips': 0,
                'passengers': 0,
                'revenue': 0,
                'avg_passengers': 0
            })
    
    return pd.DataFrame(results)


# =============================================================================
# PAGE FUNCTION
# =============================================================================

def driver_scoring_page():
    """Driver performance scoring and analysis page"""
    
    st.header("🏆 Driver Performance Scoring")
    st.markdown("Automated performance metrics and rankings for drivers")
    st.markdown("---")
    
    # Period selector
    st.subheader("📅 Select Evaluation Period")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        period_options = {
            "Last 7 Days": 7,
            "Last 14 Days": 14,
            "Last 30 Days": 30,
            "Last 3 Months": 90,
            "This Month": "this_month",
            "Last Month": "last_month",
            "This Quarter": "this_quarter",
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
    elif period_options[selected_period] == "this_quarter":
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=quarter_month, day=1)
        end_date = today
    elif period_options[selected_period] == "custom":
        with col2:
            start_date = st.date_input("From", value=today - timedelta(days=30), key="score_start")
        with col3:
            end_date = st.date_input("To", value=today, key="score_end")
    else:
        days = period_options[selected_period]
        start_date = today - timedelta(days=days)
        end_date = today
    
    st.info(f"📅 Evaluating performance from **{start_date}** to **{end_date}**")
    st.markdown("---")
    
    # Calculate scores
    scores_df = calculate_driver_scores(str(start_date), str(end_date))
    
    if scores_df.empty:
        st.warning("No driver trip data available for the selected period.")
        st.info("💡 Make sure to record trips with driver names in Trip Entry.")
        return
    
    # Summary metrics
    st.subheader("📊 Fleet Performance Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("👥 Total Drivers", len(scores_df))
    with col2:
        st.metric("🚌 Total Trips", f"{int(scores_df['trip_count'].sum()):,}")
    with col3:
        st.metric("💰 Total Revenue", f"${scores_df['total_revenue'].sum():,.2f}")
    with col4:
        st.metric("📊 Avg Score", f"{scores_df['total_score'].mean():.1f}")
    with col5:
        top_performers = len(scores_df[scores_df['total_score'] >= 75])
        st.metric("⭐ Top Performers", f"{top_performers}")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏆 Rankings", 
        "📊 Score Breakdown", 
        "👤 Individual Analysis",
        "📈 Trends",
        "⚙️ Scoring Criteria"
    ])
    
    with tab1:
        st.subheader("🏆 Driver Rankings")
        
        # Top 3 podium
        if len(scores_df) >= 3:
            st.markdown("### 🥇🥈🥉 Top Performers")
            
            col1, col2, col3 = st.columns(3)
            
            top3 = scores_df.head(3)
            
            with col2:  # Gold in center
                driver = top3.iloc[0]
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #FFD700, #FFA500); border-radius: 10px; margin-bottom: 10px;">
                    <h2 style="color: white; margin: 0;">🥇</h2>
                    <h3 style="color: white; margin: 5px 0;">{driver['driver_name']}</h3>
                    <h2 style="color: white; margin: 5px 0;">{driver['total_score']:.1f}</h2>
                    <p style="color: white; margin: 0;">Grade: {driver['grade']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col1:  # Silver
                driver = top3.iloc[1]
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #C0C0C0, #A8A8A8); border-radius: 10px; margin-top: 30px;">
                    <h2 style="color: white; margin: 0;">🥈</h2>
                    <h3 style="color: white; margin: 5px 0;">{driver['driver_name']}</h3>
                    <h2 style="color: white; margin: 5px 0;">{driver['total_score']:.1f}</h2>
                    <p style="color: white; margin: 0;">Grade: {driver['grade']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:  # Bronze
                driver = top3.iloc[2]
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #CD7F32, #8B4513); border-radius: 10px; margin-top: 30px;">
                    <h2 style="color: white; margin: 0;">🥉</h2>
                    <h3 style="color: white; margin: 5px 0;">{driver['driver_name']}</h3>
                    <h2 style="color: white; margin: 5px 0;">{driver['total_score']:.1f}</h2>
                    <p style="color: white; margin: 0;">Grade: {driver['grade']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
        
        # Full ranking table
        st.markdown("### Full Rankings")
        
        display_cols = ['rank', 'driver_name', 'total_score', 'grade', 'trip_count', 
                       'total_revenue', 'avg_passengers', 'days_worked']
        display_df = scores_df[display_cols].copy()
        display_df.columns = ['Rank', 'Driver', 'Score', 'Grade', 'Trips', 
                             'Revenue ($)', 'Avg Pass/Trip', 'Days Worked']
        
        # Round values
        display_df['Revenue ($)'] = display_df['Revenue ($)'].round(2)
        display_df['Avg Pass/Trip'] = display_df['Avg Pass/Trip'].round(1)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Grade distribution
        st.markdown("### Grade Distribution")
        grade_counts = scores_df['grade'].value_counts().sort_index()
        
        fig = px.bar(
            x=grade_counts.index,
            y=grade_counts.values,
            title='Driver Grade Distribution',
            labels={'x': 'Grade', 'y': 'Number of Drivers'},
            color=grade_counts.values,
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("📊 Score Component Breakdown")
        
        # Score components chart
        score_cols = ['trip_score', 'revenue_score', 'passenger_score', 
                     'productivity_score', 'safety_score', 'attendance_score']
        score_labels = ['Trip Volume (20)', 'Revenue (25)', 'Passengers (15)', 
                       'Productivity (15)', 'Safety (15)', 'Attendance (10)']
        
        # Radar chart for top 5 drivers
        st.markdown("### Top 5 Drivers - Score Radar")
        
        top5 = scores_df.head(5)
        
        fig = go.Figure()
        
        for _, driver in top5.iterrows():
            fig.add_trace(go.Scatterpolar(
                r=[driver[col] for col in score_cols],
                theta=score_labels,
                fill='toself',
                name=driver['driver_name']
            ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 25])),
            showlegend=True,
            title='Score Components Comparison'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Stacked bar chart
        st.markdown("### All Drivers - Score Components")
        
        fig2 = go.Figure()
        
        colors = ['#3498db', '#2ecc71', '#f1c40f', '#e74c3c', '#9b59b6', '#1abc9c']
        
        for i, (col, label) in enumerate(zip(score_cols, score_labels)):
            fig2.add_trace(go.Bar(
                x=scores_df['driver_name'],
                y=scores_df[col],
                name=label,
                marker_color=colors[i]
            ))
        
        fig2.update_layout(
            barmode='stack',
            title='Score Breakdown by Driver',
            xaxis_title='Driver',
            yaxis_title='Score Points'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # Detailed breakdown table
        st.markdown("### Detailed Score Table")
        
        breakdown_df = scores_df[['driver_name'] + score_cols + ['total_score', 'grade']].copy()
        breakdown_df.columns = ['Driver', 'Trip (20)', 'Revenue (25)', 'Passenger (15)', 
                               'Productivity (15)', 'Safety (15)', 'Attendance (10)', 
                               'Total', 'Grade']
        
        for col in breakdown_df.columns[1:-1]:
            breakdown_df[col] = breakdown_df[col].round(1)
        
        st.dataframe(breakdown_df, use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("👤 Individual Driver Analysis")
        
        # Driver selector
        driver_options = scores_df['driver_name'].tolist()
        selected_driver = st.selectbox("Select Driver", driver_options)
        
        if selected_driver:
            driver_data = scores_df[scores_df['driver_name'] == selected_driver].iloc[0]
            
            # Header with grade
            grade_colors = {
                'A+': '#00C853', 'A': '#00E676', 'A-': '#69F0AE',
                'B+': '#FFD600', 'B': '#FFEA00', 'B-': '#FFF176',
                'C+': '#FF9100', 'C': '#FF6D00', 'C-': '#FFAB40',
                'D': '#FF5252', 'F': '#D50000'
            }
            
            grade_color = grade_colors.get(driver_data['grade'], '#757575')
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"## {selected_driver}")
                st.markdown(f"**Rank:** #{int(driver_data['rank'])} of {len(scores_df)} drivers")
            
            with col2:
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: {grade_color}; border-radius: 10px;">
                    <h1 style="color: white; margin: 0;">{driver_data['grade']}</h1>
                    <h3 style="color: white; margin: 0;">{driver_data['total_score']:.1f}/100</h3>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("🚌 Trips", int(driver_data['trip_count']))
            with col2:
                st.metric("💰 Revenue", f"${driver_data['total_revenue']:,.2f}")
            with col3:
                st.metric("👥 Total Passengers", int(driver_data['total_passengers']))
            with col4:
                st.metric("📅 Days Worked", int(driver_data['days_worked']))
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Avg Passengers/Trip", f"{driver_data['avg_passengers']:.1f}")
            with col2:
                st.metric("💵 Avg Revenue/Trip", f"${driver_data['avg_revenue']:.2f}")
            with col3:
                st.metric("🔄 Trips/Day", f"{driver_data['trips_per_day']:.1f}")
            with col4:
                st.metric("⚠️ Incidents", int(driver_data['incident_count']))
            
            st.markdown("---")
            
            # Score breakdown
            st.markdown("### Score Breakdown")
            
            score_items = [
                ('Trip Volume', driver_data['trip_score'], 20, '🚌'),
                ('Revenue Generation', driver_data['revenue_score'], 25, '💰'),
                ('Passenger Load', driver_data['passenger_score'], 15, '👥'),
                ('Productivity', driver_data['productivity_score'], 15, '📈'),
                ('Safety Record', driver_data['safety_score'], 15, '🛡️'),
                ('Attendance', driver_data['attendance_score'], 10, '📅')
            ]
            
            for name, score, max_score, icon in score_items:
                pct = (score / max_score * 100) if max_score > 0 else 0
                col1, col2, col3 = st.columns([2, 3, 1])
                
                with col1:
                    st.write(f"{icon} **{name}**")
                with col2:
                    st.progress(pct / 100)
                with col3:
                    st.write(f"{score:.1f}/{max_score}")
            
            st.markdown("---")
            
            # Recent trips
            st.markdown("### Recent Trips")
            
            recent_trips = get_driver_trips(selected_driver, str(start_date), str(end_date))
            
            if not recent_trips.empty:
                display_trips = recent_trips.head(10)[['trip_date', 'bus_number', 'route_name', 
                                                       'passengers', 'revenue']].copy()
                display_trips.columns = ['Date', 'Bus', 'Route', 'Passengers', 'Revenue ($)']
                st.dataframe(display_trips, use_container_width=True, hide_index=True)
            else:
                st.info("No recent trips")
            
            # Incidents
            incidents = get_driver_incidents(selected_driver, str(start_date), str(end_date))
            
            if not incidents.empty:
                st.markdown("### ⚠️ Incidents")
                st.dataframe(incidents[['incident_date', 'incident_type', 'severity', 'description']], 
                           use_container_width=True, hide_index=True)
    
    with tab4:
        st.subheader("📈 Performance Trends")
        
        # Select driver for trends
        trend_driver = st.selectbox("Select Driver for Trend Analysis", 
                                   scores_df['driver_name'].tolist(), key="trend_driver")
        
        if trend_driver:
            trend_df = get_driver_trend(trend_driver, months=6)
            
            if not trend_df.empty and trend_df['trips'].sum() > 0:
                # Reverse for chronological order
                trend_df = trend_df.iloc[::-1].reset_index(drop=True)
                
                # Revenue trend
                fig = px.line(
                    trend_df,
                    x='month',
                    y='revenue',
                    title=f'Monthly Revenue: {trend_driver}',
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
                    title=f'Monthly Trips & Passengers: {trend_driver}',
                    yaxis=dict(title='Trips'),
                    yaxis2=dict(title='Passengers', overlaying='y', side='right')
                )
                
                st.plotly_chart(fig2, use_container_width=True)
                
                # Summary table
                st.markdown("### Monthly Summary")
                display_trend = trend_df[['month', 'trips', 'passengers', 'revenue', 'avg_passengers']].copy()
                display_trend.columns = ['Month', 'Trips', 'Passengers', 'Revenue ($)', 'Avg Pass/Trip']
                display_trend['Avg Pass/Trip'] = display_trend['Avg Pass/Trip'].round(1)
                st.dataframe(display_trend, use_container_width=True, hide_index=True)
            else:
                st.info(f"No historical data available for {trend_driver}")
        
        st.markdown("---")
        
        # Fleet-wide trends
        st.markdown("### Fleet-Wide Performance")
        
        # Score distribution histogram
        fig = px.histogram(
            scores_df,
            x='total_score',
            nbins=10,
            title='Score Distribution Across All Drivers',
            labels={'total_score': 'Performance Score'}
        )
        fig.add_vline(x=scores_df['total_score'].mean(), line_dash="dash", 
                     annotation_text=f"Average: {scores_df['total_score'].mean():.1f}")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab5:
        st.subheader("⚙️ Scoring Criteria Explanation")
        
        st.markdown("""
        ### How Driver Scores Are Calculated
        
        Each driver is evaluated on **6 key performance areas** with a maximum total of **100 points**:
        
        ---
        
        #### 🚌 Trip Volume (20 points)
        - Measures the number of trips completed
        - Higher trip counts indicate greater productivity
        - Score = (Driver's Trips / Highest Trip Count) × 20
        
        ---
        
        #### 💰 Revenue Generation (25 points)
        - Measures total revenue generated from trips
        - Recognizes drivers who contribute most to company income
        - Score = (Driver's Revenue / Highest Revenue) × 25
        
        ---
        
        #### 👥 Passenger Load (15 points)
        - Measures average passengers per trip
        - Higher loads indicate better route/schedule optimization
        - Score = (Driver's Avg Passengers / Highest Avg) × 15
        
        ---
        
        #### 📈 Productivity (15 points)
        - Measures trips per day worked
        - Rewards efficient use of working time
        - Score = (Driver's Trips/Day / Highest Trips/Day) × 15
        
        ---
        
        #### 🛡️ Safety Record (15 points)
        - Starts at 15 points, deducted for incidents
        - Minor incident: -1 point
        - Moderate incident: -2 points
        - Major incident: -3 points
        - Severe incident: -5 points
        
        ---
        
        #### 📅 Attendance (10 points)
        - Based on days worked vs expected work days
        - Full attendance = 10 points
        - Score adjusted for leave taken
        
        ---
        
        ### Grade Scale
        
        | Score | Grade |
        |-------|-------|
        | 90-100 | A+ |
        | 85-89 | A |
        | 80-84 | A- |
        | 75-79 | B+ |
        | 70-74 | B |
        | 65-69 | B- |
        | 60-64 | C+ |
        | 55-59 | C |
        | 50-54 | C- |
        | 45-49 | D |
        | 0-44 | F |
        """)
    
    # Export
    st.markdown("---")
    st.subheader("📥 Export Report")
    
    csv = scores_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Performance Report (CSV)",
        data=csv,
        file_name=f"driver_performance_{start_date}_{end_date}.csv",
        mime="text/csv"
    )