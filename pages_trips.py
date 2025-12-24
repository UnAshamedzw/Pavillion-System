"""
pages_trips.py - Trip/Journey Tracking Module
Pavillion Coaches Bus Management System
Track individual trips, passengers, and revenue per journey
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

def get_active_buses():
    """Get list of active buses"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT bus_number, registration_number, make, model, capacity
        FROM buses 
        WHERE status = 'Active' 
        ORDER BY registration_number
    """)
    
    buses = cursor.fetchall()
    conn.close()
    return buses


def get_routes():
    """Get list of routes"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, distance FROM routes ORDER BY name")
    routes = cursor.fetchall()
    conn.close()
    return routes


def get_drivers():
    """Get list of active drivers"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, employee_id, full_name 
        FROM employees 
        WHERE position LIKE '%Driver%' AND status = 'Active'
        ORDER BY full_name
    """)
    
    drivers = cursor.fetchall()
    conn.close()
    return drivers


def get_conductors():
    """Get list of active conductors"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, employee_id, full_name 
        FROM employees 
        WHERE position LIKE '%Conductor%' AND status = 'Active'
        ORDER BY full_name
    """)
    
    conductors = cursor.fetchall()
    conn.close()
    return conductors


def add_trip(bus_number, route_id, route_name, driver_id, driver_name, 
             conductor_id, conductor_name, trip_date, departure_time,
             arrival_time, passengers, revenue, trip_type='Scheduled',
             notes=None, created_by=None):
    """Add a new trip record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Calculate trip duration if both times provided
    duration_minutes = None
    if departure_time and arrival_time:
        try:
            dep = datetime.strptime(departure_time, '%H:%M')
            arr = datetime.strptime(arrival_time, '%H:%M')
            duration = arr - dep
            duration_minutes = int(duration.total_seconds() / 60)
            if duration_minutes < 0:  # Handle overnight trips
                duration_minutes += 24 * 60
        except Exception as e:
            pass
    
    # Calculate revenue per passenger
    revenue_per_passenger = revenue / passengers if passengers > 0 else 0
    
    try:
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO trips (
                    bus_number, route_id, route_name, driver_id, driver_name,
                    conductor_id, conductor_name, trip_date, departure_time,
                    arrival_time, duration_minutes, passengers, revenue,
                    revenue_per_passenger, trip_type, notes, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (bus_number, route_id, route_name, driver_id, driver_name,
                  conductor_id, conductor_name, trip_date, departure_time,
                  arrival_time, duration_minutes, passengers, revenue,
                  revenue_per_passenger, trip_type, notes, created_by))
            result = cursor.fetchone()
            trip_id = result['id'] if hasattr(result, 'keys') else result[0]
        else:
            cursor.execute("""
                INSERT INTO trips (
                    bus_number, route_id, route_name, driver_id, driver_name,
                    conductor_id, conductor_name, trip_date, departure_time,
                    arrival_time, duration_minutes, passengers, revenue,
                    revenue_per_passenger, trip_type, notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (bus_number, route_id, route_name, driver_id, driver_name,
                  conductor_id, conductor_name, trip_date, departure_time,
                  arrival_time, duration_minutes, passengers, revenue,
                  revenue_per_passenger, trip_type, notes, created_by))
            trip_id = cursor.lastrowid
        
        conn.commit()
        return trip_id
    except Exception as e:
        print(f"Error adding trip: {e}")
        return None
    finally:
        conn.close()


def get_trips(bus_number=None, route_name=None, driver_name=None, 
              start_date=None, end_date=None, trip_type=None):
    """
    Get trips with optional filters.
    Queries from INCOME table for compatibility with Excel imports.
    """
    conn = get_connection()
    
    # Query from INCOME table (where Excel data is imported)
    query = """
        SELECT 
            id,
            date as trip_date,
            bus_number,
            route as route_name,
            driver_name,
            conductor_name,
            COALESCE(passengers, 0) as passengers,
            COALESCE(amount, 0) as revenue,
            CASE WHEN passengers > 0 THEN amount / passengers ELSE 0 END as revenue_per_passenger,
            COALESCE(trip_type, 'Regular') as trip_type,
            notes,
            departure_time,
            arrival_time,
            created_by
        FROM income 
        WHERE 1=1
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if bus_number:
        query += f" AND bus_number = {ph}"
        params.append(bus_number)
    
    if route_name:
        query += f" AND route = {ph}"
        params.append(route_name)
    
    if driver_name:
        query += f" AND (driver_name = {ph} OR driver_name LIKE {ph})"
        params.append(driver_name)
        params.append(f"%{driver_name}%")
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(str(end_date))
    
    if trip_type:
        query += f" AND trip_type = {ph}"
        params.append(trip_type)
    
    query += " ORDER BY date DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
        # Ensure numeric columns
        df['passengers'] = pd.to_numeric(df['passengers'], errors='coerce').fillna(0)
        df['revenue'] = pd.to_numeric(df['revenue'], errors='coerce').fillna(0)
    except Exception as e:
        print(f"Error getting trips: {e}")
        df = pd.DataFrame()
    
    conn.close()
    return df


def update_trip(trip_id, **kwargs):
    """Update a trip record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    set_clauses = []
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    for key, value in kwargs.items():
        if value is not None:
            set_clauses.append(f"{key} = {ph}")
            params.append(value)
    
    if not set_clauses:
        return False
    
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    params.append(trip_id)
    
    query = f"UPDATE trips SET {', '.join(set_clauses)} WHERE id = {ph}"
    
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating trip: {e}")
        return False
    finally:
        conn.close()


def delete_trip(trip_id):
    """Delete a trip record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    ph = '%s' if USE_POSTGRES else '?'
    
    try:
        cursor.execute(f"DELETE FROM trips WHERE id = {ph}", (trip_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting trip: {e}")
        return False
    finally:
        conn.close()


def get_trip_summary_by_bus(start_date=None, end_date=None):
    """Get trip summary by bus from INCOME table"""
    conn = get_connection()
    
    query = """
        SELECT 
            bus_number,
            COUNT(*) as trip_count,
            COALESCE(SUM(passengers), 0) as total_passengers,
            COALESCE(SUM(amount), 0) as total_revenue,
            COALESCE(AVG(passengers), 0) as avg_passengers,
            COALESCE(AVG(amount), 0) as avg_revenue_per_trip,
            CASE WHEN SUM(passengers) > 0 THEN SUM(amount) / SUM(passengers) ELSE 0 END as avg_revenue_per_passenger
        FROM income
        WHERE bus_number IS NOT NULL AND bus_number != ''
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(str(end_date))
    
    query += " GROUP BY bus_number ORDER BY total_revenue DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
        # Ensure numeric columns
        for col in ['trip_count', 'total_passengers', 'total_revenue', 'avg_passengers', 'avg_revenue_per_trip']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    except Exception as e:
        print(f"Error in bus summary: {e}")
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_trip_summary_by_route(start_date=None, end_date=None):
    """Get trip summary by route from INCOME table"""
    conn = get_connection()
    
    query = """
        SELECT 
            route as route_name,
            COUNT(*) as trip_count,
            COALESCE(SUM(passengers), 0) as total_passengers,
            COALESCE(SUM(amount), 0) as total_revenue,
            COALESCE(AVG(passengers), 0) as avg_passengers,
            COALESCE(AVG(amount), 0) as avg_revenue_per_trip,
            0 as avg_duration
        FROM income
        WHERE route IS NOT NULL AND route != ''
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(str(end_date))
    
    query += " GROUP BY route ORDER BY total_revenue DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
        for col in ['trip_count', 'total_passengers', 'total_revenue', 'avg_passengers', 'avg_revenue_per_trip']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    except Exception as e:
        print(f"Error in route summary: {e}")
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_trip_summary_by_driver(start_date=None, end_date=None):
    """Get trip summary by driver from INCOME table"""
    conn = get_connection()
    
    query = """
        SELECT 
            driver_name,
            COUNT(*) as trip_count,
            COALESCE(SUM(passengers), 0) as total_passengers,
            COALESCE(SUM(amount), 0) as total_revenue,
            COALESCE(AVG(passengers), 0) as avg_passengers,
            COALESCE(AVG(amount), 0) as avg_revenue_per_trip
        FROM income
        WHERE driver_name IS NOT NULL AND driver_name != ''
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(str(end_date))
    
    query += " GROUP BY driver_name ORDER BY total_revenue DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
        for col in ['trip_count', 'total_passengers', 'total_revenue', 'avg_passengers', 'avg_revenue_per_trip']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    except Exception as e:
        print(f"Error in driver summary: {e}")
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_daily_trip_summary(start_date=None, end_date=None):
    """Get daily trip summary from INCOME table"""
    conn = get_connection()
    
    query = """
        SELECT 
            date as trip_date,
            COUNT(*) as trip_count,
            COALESCE(SUM(passengers), 0) as total_passengers,
            COALESCE(SUM(amount), 0) as total_revenue
        FROM income
        WHERE 1=1
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(str(end_date))
    
    query += " GROUP BY date ORDER BY date"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
        for col in ['trip_count', 'total_passengers', 'total_revenue']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    except Exception as e:
        print(f"Error in daily summary: {e}")
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_hourly_distribution(start_date=None, end_date=None):
    """Get trip distribution by hour of day from INCOME table"""
    conn = get_connection()
    
    if USE_POSTGRES:
        query = """
            SELECT 
                EXTRACT(HOUR FROM departure_time::time) as hour,
                COUNT(*) as trip_count,
                COALESCE(SUM(passengers), 0) as total_passengers,
                COALESCE(SUM(amount), 0) as total_revenue
            FROM income
            WHERE departure_time IS NOT NULL
        """
    else:
        query = """
            SELECT 
                CAST(SUBSTR(departure_time, 1, 2) AS INTEGER) as hour,
                COUNT(*) as trip_count,
                COALESCE(SUM(passengers), 0) as total_passengers,
                COALESCE(SUM(amount), 0) as total_revenue
            FROM income
            WHERE departure_time IS NOT NULL
        """
    
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(str(end_date))
    
    query += " GROUP BY hour ORDER BY hour"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
        for col in ['trip_count', 'total_passengers', 'total_revenue']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    except Exception as e:
        print(f"Error in hourly distribution: {e}")
        df = pd.DataFrame()
    
    conn.close()
    return df


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_bus_display(bus):
    """Format bus for dropdown"""
    if hasattr(bus, 'keys'):
        reg = bus.get('registration_number') or bus.get('bus_number', 'Unknown')
        model = bus.get('model', '')
        capacity = bus.get('capacity', '')
    else:
        reg = bus[1] or bus[0] if len(bus) > 1 else 'Unknown'
        model = bus[3] if len(bus) > 3 else ''
        capacity = bus[4] if len(bus) > 4 else ''
    
    if capacity:
        return f"{reg} ({model}) - {capacity} seats"
    return f"{reg} ({model})" if model else reg


def get_bus_number_from_display(display, buses):
    """Extract bus_number from display string"""
    for bus in buses:
        if get_bus_display(bus) == display:
            if hasattr(bus, 'keys'):
                return bus.get('registration_number') or bus.get('bus_number')
            else:
                return bus[1] or bus[0]
    return None


def get_employee_display(emp):
    """Format employee for dropdown"""
    if hasattr(emp, 'keys'):
        return f"{emp.get('full_name', 'Unknown')} ({emp.get('employee_id', '')})"
    else:
        return f"{emp[2]} ({emp[1]})" if len(emp) > 2 else str(emp[0])


def get_employee_info(display, employees):
    """Extract employee info from display string"""
    for emp in employees:
        if get_employee_display(emp) == display:
            if hasattr(emp, 'keys'):
                return emp.get('id'), emp.get('full_name')
            else:
                return emp[0], emp[2] if len(emp) > 2 else None
    return None, None


def get_route_display(route):
    """Format route for dropdown"""
    if hasattr(route, 'keys'):
        name = route.get('name', 'Unknown')
        distance = route.get('distance')
    else:
        name = route[1] if len(route) > 1 else str(route[0])
        distance = route[2] if len(route) > 2 else None
    
    if distance:
        return f"{name} ({distance} km)"
    return name


def get_route_info(display, routes):
    """Extract route info from display string"""
    for route in routes:
        if get_route_display(route) == display:
            if hasattr(route, 'keys'):
                return route.get('id'), route.get('name')
            else:
                return route[0], route[1] if len(route) > 1 else None
    return None, None


# =============================================================================
# PAGE FUNCTIONS
# =============================================================================

def trip_entry_page():
    """Trip entry page for recording individual journeys"""
    
    st.header("🚌 Trip Entry")
    st.markdown("Record individual bus trips and journeys")
    st.markdown("---")
    
    # Check permissions
    can_add = has_permission('add_income')
    can_edit = has_permission('edit_income')
    can_delete = has_permission('delete_income')
    
    tab1, tab2, tab3 = st.tabs(["➕ Add Trip", "📋 Trip History", "✏️ Edit/Delete"])
    
    with tab1:
        if not can_add:
            st.warning("You don't have permission to add trips")
        else:
            st.subheader("➕ Record New Trip")
            
            # Get data for dropdowns
            buses = get_active_buses()
            routes = get_routes()
            drivers = get_drivers()
            conductors = get_conductors()
            
            if not buses:
                st.warning("No active buses found. Please add buses first.")
                return
            
            with st.form("trip_entry_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Bus selection
                    bus_options = [get_bus_display(bus) for bus in buses]
                    selected_bus = st.selectbox("Select Bus*", bus_options)
                    
                    # Route selection
                    if routes:
                        route_options = ["-- Select Route --"] + [get_route_display(r) for r in routes]
                        selected_route = st.selectbox("Route*", route_options)
                    else:
                        selected_route = None
                        st.text_input("Route Name*", key="manual_route")
                    
                    # Trip type
                    trip_type = st.selectbox("Trip Type", ["Scheduled", "Charter", "Private Hire", "Express", "Other"])
                    
                    # Date
                    trip_date = st.date_input("Trip Date*", value=datetime.now().date())
                
                with col2:
                    # Driver selection
                    if drivers:
                        driver_options = ["-- Select Driver --"] + [get_employee_display(d) for d in drivers]
                        selected_driver = st.selectbox("Driver", driver_options)
                    else:
                        selected_driver = None
                        st.text_input("Driver Name", key="manual_driver")
                    
                    # Conductor selection
                    if conductors:
                        conductor_options = ["-- No Conductor --"] + [get_employee_display(c) for c in conductors]
                        selected_conductor = st.selectbox("Conductor", conductor_options)
                    else:
                        selected_conductor = None
                        st.text_input("Conductor Name", key="manual_conductor")
                    
                    # Times
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        departure_time = st.time_input("Departure Time", value=None)
                    with col_t2:
                        arrival_time = st.time_input("Arrival Time", value=None)
                
                st.markdown("---")
                
                # Revenue and passengers
                col3, col4, col5 = st.columns(3)
                
                with col3:
                    passengers = st.number_input("Passengers*", min_value=0, step=1, value=0)
                
                with col4:
                    revenue = st.number_input("Revenue ($)*", min_value=0.0, step=10.0, format="%.2f")
                
                with col5:
                    if passengers > 0:
                        rev_per_pass = revenue / passengers
                        st.metric("Revenue/Passenger", f"${rev_per_pass:.2f}")
                    else:
                        st.metric("Revenue/Passenger", "N/A")
                
                notes = st.text_area("Notes", placeholder="Any additional notes about this trip...")
                
                submitted = st.form_submit_button("🚌 Save Trip", type="primary", use_container_width=True)
                
                if submitted:
                    # Get bus number
                    bus_number = get_bus_number_from_display(selected_bus, buses)
                    
                    # Get route info
                    if routes and selected_route and selected_route != "-- Select Route --":
                        route_id, route_name = get_route_info(selected_route, routes)
                    else:
                        route_id = None
                        route_name = st.session_state.get('manual_route', 'Unknown')
                    
                    # Get driver info
                    if drivers and selected_driver and selected_driver != "-- Select Driver --":
                        driver_id, driver_name = get_employee_info(selected_driver, drivers)
                    else:
                        driver_id = None
                        driver_name = st.session_state.get('manual_driver', None)
                    
                    # Get conductor info
                    if conductors and selected_conductor and selected_conductor != "-- No Conductor --":
                        conductor_id, conductor_name = get_employee_info(selected_conductor, conductors)
                    else:
                        conductor_id = None
                        conductor_name = st.session_state.get('manual_conductor', None)
                    
                    # Format times
                    dep_time = departure_time.strftime('%H:%M') if departure_time else None
                    arr_time = arrival_time.strftime('%H:%M') if arrival_time else None
                    
                    # Validation
                    if not bus_number or not route_name or passengers <= 0 or revenue <= 0:
                        st.error("Please fill in all required fields (Bus, Route, Passengers, Revenue)")
                    else:
                        trip_id = add_trip(
                            bus_number=bus_number,
                            route_id=route_id,
                            route_name=route_name,
                            driver_id=driver_id,
                            driver_name=driver_name,
                            conductor_id=conductor_id,
                            conductor_name=conductor_name,
                            trip_date=str(trip_date),
                            departure_time=dep_time,
                            arrival_time=arr_time,
                            passengers=passengers,
                            revenue=revenue,
                            trip_type=trip_type,
                            notes=notes,
                            created_by=st.session_state['user']['username']
                        )
                        
                        if trip_id:
                            AuditLogger.log_action(
                                "Create", "Trips",
                                f"Added trip: {bus_number} on {route_name} - {passengers} passengers, ${revenue:.2f}"
                            )
                            st.success(f"✅ Trip saved successfully! (ID: {trip_id})")
                            st.rerun()
                        else:
                            st.error("Error saving trip")
    
    with tab2:
        st.subheader("📋 Trip History")
        
        # Filters
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            buses = get_active_buses()
            bus_filter_options = ["All Buses"] + [get_bus_display(b) for b in buses]
            filter_bus = st.selectbox("Filter by Bus", bus_filter_options, key="hist_bus")
        
        with col2:
            routes = get_routes()
            route_filter_options = ["All Routes"] + [r['name'] if hasattr(r, 'keys') else r[1] for r in routes]
            filter_route = st.selectbox("Filter by Route", route_filter_options, key="hist_route")
        
        with col3:
            filter_start = st.date_input("From", value=datetime.now().date() - timedelta(days=30), key="hist_start")
        
        with col4:
            filter_end = st.date_input("To", value=datetime.now().date(), key="hist_end")
        
        # Get filter values
        bus_filter = get_bus_number_from_display(filter_bus, buses) if filter_bus != "All Buses" else None
        route_filter = filter_route if filter_route != "All Routes" else None
        
        # Get trips
        trips_df = get_trips(
            bus_number=bus_filter,
            route_name=route_filter,
            start_date=str(filter_start),
            end_date=str(filter_end)
        )
        
        if trips_df.empty:
            st.info("No trips found for the selected filters")
        else:
            # Summary metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Trips", len(trips_df))
            with col2:
                st.metric("Total Passengers", f"{trips_df['passengers'].sum():,}")
            with col3:
                st.metric("Total Revenue", f"${trips_df['revenue'].sum():,.2f}")
            with col4:
                st.metric("Avg Passengers", f"{trips_df['passengers'].mean():.1f}")
            with col5:
                st.metric("Avg Revenue/Trip", f"${trips_df['revenue'].mean():.2f}")
            
            st.markdown("---")
            
            # Display trips
            display_cols = ['id', 'trip_date', 'bus_number', 'route_name', 'driver_name', 
                           'departure_time', 'passengers', 'revenue', 'trip_type']
            display_df = trips_df[display_cols].copy()
            display_df.columns = ['ID', 'Date', 'Bus', 'Route', 'Driver', 'Departure', 
                                 'Passengers', 'Revenue', 'Type']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Export
            csv = trips_df.to_csv(index=False)
            st.download_button(
                label="📥 Export to CSV",
                data=csv,
                file_name=f"trips_{filter_start}_{filter_end}.csv",
                mime="text/csv"
            )
    
    with tab3:
        st.subheader("✏️ Edit/Delete Trips")
        
        if not can_edit and not can_delete:
            st.warning("You don't have permission to edit or delete trips")
        else:
            # Get recent trips
            recent_trips = get_trips(start_date=str(datetime.now().date() - timedelta(days=7)))
            
            if recent_trips.empty:
                st.info("No recent trips to edit")
            else:
                # Selection
                trip_options = {}
                for _, row in recent_trips.iterrows():
                    label = f"ID:{row['id']} | {row['trip_date']} | {row['bus_number']} | {row['route_name']} | ${row['revenue']:.2f}"
                    trip_options[label] = row['id']
                
                selected_trip = st.selectbox("Select Trip", list(trip_options.keys()))
                
                if selected_trip:
                    trip_id = trip_options[selected_trip]
                    trip = recent_trips[recent_trips['id'] == trip_id].iloc[0]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Current Values:**")
                        st.write(f"- **Date:** {trip['trip_date']}")
                        st.write(f"- **Bus:** {trip['bus_number']}")
                        st.write(f"- **Route:** {trip['route_name']}")
                        st.write(f"- **Driver:** {trip['driver_name'] or 'N/A'}")
                        st.write(f"- **Passengers:** {trip['passengers']}")
                        st.write(f"- **Revenue:** ${trip['revenue']:.2f}")
                        st.write(f"- **Type:** {trip['trip_type']}")
                    
                    with col2:
                        if can_edit:
                            with st.form("edit_trip_form"):
                                st.markdown("**Edit Values:**")
                                new_passengers = st.number_input("Passengers", value=int(trip['passengers']), min_value=0)
                                new_revenue = st.number_input("Revenue ($)", value=float(trip['revenue']), min_value=0.0)
                                new_notes = st.text_area("Notes", value=trip['notes'] or "")
                                
                                if st.form_submit_button("💾 Update Trip", type="primary"):
                                    rev_per_pass = new_revenue / new_passengers if new_passengers > 0 else 0
                                    if update_trip(
                                        trip_id,
                                        passengers=new_passengers,
                                        revenue=new_revenue,
                                        revenue_per_passenger=rev_per_pass,
                                        notes=new_notes
                                    ):
                                        AuditLogger.log_action("Update", "Trips", f"Updated trip ID:{trip_id}")
                                        st.success("✅ Trip updated!")
                                        st.rerun()
                                    else:
                                        st.error("Error updating trip")
                        
                        if can_delete:
                            st.markdown("---")
                            if st.button("🗑️ Delete This Trip"):
                                st.session_state[f'confirm_delete_trip_{trip_id}'] = True
                            
                            if st.session_state.get(f'confirm_delete_trip_{trip_id}', False):
                                st.warning("⚠️ Are you sure?")
                                col_y, col_n = st.columns(2)
                                with col_y:
                                    if st.button("✅ Yes, Delete"):
                                        if delete_trip(trip_id):
                                            AuditLogger.log_action("Delete", "Trips", f"Deleted trip ID:{trip_id}")
                                            st.success("Deleted!")
                                            del st.session_state[f'confirm_delete_trip_{trip_id}']
                                            st.rerun()
                                with col_n:
                                    if st.button("❌ Cancel"):
                                        del st.session_state[f'confirm_delete_trip_{trip_id}']
                                        st.rerun()


def trip_analysis_page():
    """Trip analysis and reporting page"""
    
    st.header("📊 Trip Analysis")
    st.markdown("Analyze trips, passengers, and revenue patterns")
    st.markdown("---")
    
    # Period selector
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        period_options = {
            "Last 7 Days": 7,
            "Last 14 Days": 14,
            "Last 30 Days": 30,
            "Last 3 Months": 90,
            "This Month": "this_month",
            "Last Month": "last_month",
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
    elif period_options[selected_period] == "custom":
        with col2:
            start_date = st.date_input("From", value=today - timedelta(days=30), key="analysis_start")
        with col3:
            end_date = st.date_input("To", value=today, key="analysis_end")
    else:
        days = period_options[selected_period]
        start_date = today - timedelta(days=days)
        end_date = today
    
    st.info(f"📅 Showing data from **{start_date}** to **{end_date}**")
    st.markdown("---")
    
    # Get summary data
    trips_df = get_trips(start_date=str(start_date), end_date=str(end_date))
    
    if trips_df.empty:
        st.warning("No trip data available for the selected period")
        return
    
    # Overall metrics
    st.subheader("📈 Period Summary")
    
    total_trips = len(trips_df)
    total_passengers = trips_df['passengers'].sum()
    total_revenue = trips_df['revenue'].sum()
    avg_passengers = trips_df['passengers'].mean()
    avg_revenue = trips_df['revenue'].mean()
    days_in_period = (end_date - start_date).days + 1
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("🚌 Total Trips", f"{total_trips:,}")
        st.caption(f"{total_trips/days_in_period:.1f}/day avg")
    with col2:
        st.metric("👥 Total Passengers", f"{total_passengers:,}")
        st.caption(f"{total_passengers/days_in_period:.0f}/day avg")
    with col3:
        st.metric("💰 Total Revenue", f"${total_revenue:,.2f}")
        st.caption(f"${total_revenue/days_in_period:.2f}/day avg")
    with col4:
        st.metric("👥 Avg Passengers/Trip", f"{avg_passengers:.1f}")
    with col5:
        st.metric("💰 Avg Revenue/Trip", f"${avg_revenue:.2f}")
    
    st.markdown("---")
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 By Bus", "🛣️ By Route", "👤 By Driver", "📈 Trends", "⏰ Time Analysis"])
    
    with tab1:
        st.subheader("Trips by Bus")
        
        bus_summary = get_trip_summary_by_bus(str(start_date), str(end_date))
        
        if not bus_summary.empty:
            # Bar chart
            fig = px.bar(
                bus_summary.head(15),
                x='bus_number',
                y='total_revenue',
                title='Revenue by Bus',
                labels={'bus_number': 'Bus', 'total_revenue': 'Revenue ($)'},
                color='total_revenue',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Passengers chart
            fig2 = px.bar(
                bus_summary.head(15),
                x='bus_number',
                y='total_passengers',
                title='Passengers by Bus',
                labels={'bus_number': 'Bus', 'total_passengers': 'Passengers'},
                color='total_passengers',
                color_continuous_scale='Greens'
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Table
            st.markdown("### Detailed Summary")
            display_df = bus_summary.copy()
            display_df.columns = ['Bus', 'Trips', 'Passengers', 'Revenue ($)', 
                                 'Avg Pass/Trip', 'Avg Rev/Trip', 'Avg Rev/Pass']
            st.dataframe(display_df.round(2), use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("Trips by Route")
        
        route_summary = get_trip_summary_by_route(str(start_date), str(end_date))
        
        if not route_summary.empty:
            # Revenue by route
            fig = px.pie(
                route_summary.head(10),
                values='total_revenue',
                names='route_name',
                title='Revenue Distribution by Route'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Bar chart
            fig2 = px.bar(
                route_summary,
                x='route_name',
                y=['total_revenue', 'total_passengers'],
                title='Revenue vs Passengers by Route',
                barmode='group',
                labels={'value': 'Count/Amount', 'route_name': 'Route'}
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Table
            st.markdown("### Route Summary")
            display_df = route_summary.copy()
            display_df.columns = ['Route', 'Trips', 'Passengers', 'Revenue ($)', 
                                 'Avg Pass/Trip', 'Avg Rev/Trip', 'Avg Duration (min)']
            st.dataframe(display_df.round(2), use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("Trips by Driver")
        
        driver_summary = get_trip_summary_by_driver(str(start_date), str(end_date))
        
        if not driver_summary.empty:
            # Revenue by driver
            fig = px.bar(
                driver_summary.head(15),
                x='driver_name',
                y='total_revenue',
                title='Revenue by Driver',
                labels={'driver_name': 'Driver', 'total_revenue': 'Revenue ($)'},
                color='total_revenue',
                color_continuous_scale='Oranges'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Table
            st.markdown("### Driver Performance")
            display_df = driver_summary.copy()
            display_df.columns = ['Driver', 'Trips', 'Passengers', 'Revenue ($)', 
                                 'Avg Pass/Trip', 'Avg Rev/Trip']
            st.dataframe(display_df.round(2), use_container_width=True, hide_index=True)
            
            # Best performers
            st.markdown("### 🏆 Top Performers")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**By Revenue:**")
                for i, (_, row) in enumerate(driver_summary.head(5).iterrows(), 1):
                    st.write(f"{i}. **{row['driver_name']}**: ${row['total_revenue']:,.2f}")
            
            with col2:
                st.markdown("**By Trips:**")
                by_trips = driver_summary.sort_values('trip_count', ascending=False).head(5)
                for i, (_, row) in enumerate(by_trips.iterrows(), 1):
                    st.write(f"{i}. **{row['driver_name']}**: {int(row['trip_count'])} trips")
        else:
            st.info("No driver data available")
    
    with tab4:
        st.subheader("Daily Trends")
        
        daily_summary = get_daily_trip_summary(str(start_date), str(end_date))
        
        if not daily_summary.empty:
            daily_summary['trip_date'] = pd.to_datetime(daily_summary['trip_date'])
            
            # Revenue trend
            fig = px.line(
                daily_summary,
                x='trip_date',
                y='total_revenue',
                title='Daily Revenue Trend',
                labels={'trip_date': 'Date', 'total_revenue': 'Revenue ($)'}
            )
            fig.update_traces(fill='tozeroy')
            st.plotly_chart(fig, use_container_width=True)
            
            # Trips and passengers trend
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=daily_summary['trip_date'],
                y=daily_summary['trip_count'],
                name='Trips',
                marker_color='blue'
            ))
            fig2.add_trace(go.Scatter(
                x=daily_summary['trip_date'],
                y=daily_summary['total_passengers'],
                name='Passengers',
                yaxis='y2',
                line=dict(color='green', width=2)
            ))
            fig2.update_layout(
                title='Daily Trips and Passengers',
                yaxis=dict(title='Trips'),
                yaxis2=dict(title='Passengers', overlaying='y', side='right')
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    with tab5:
        st.subheader("Time Analysis")
        
        hourly_data = get_hourly_distribution(str(start_date), str(end_date))
        
        if not hourly_data.empty:
            # Hourly distribution
            fig = px.bar(
                hourly_data,
                x='hour',
                y='trip_count',
                title='Trips by Hour of Day',
                labels={'hour': 'Hour', 'trip_count': 'Number of Trips'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Revenue by hour
            fig2 = px.bar(
                hourly_data,
                x='hour',
                y='total_revenue',
                title='Revenue by Hour of Day',
                labels={'hour': 'Hour', 'total_revenue': 'Revenue ($)'},
                color='total_revenue',
                color_continuous_scale='Greens'
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # Peak hours
            st.markdown("### ⏰ Peak Hours")
            peak_hours = hourly_data.nlargest(5, 'trip_count')
            for _, row in peak_hours.iterrows():
                hour = int(row['hour'])
                st.write(f"- **{hour:02d}:00 - {hour+1:02d}:00**: {int(row['trip_count'])} trips, ${row['total_revenue']:,.2f}")
        else:
            st.info("No hourly data available. Make sure to record departure times.")
        
        # Trip type distribution
        st.markdown("---")
        st.markdown("### 🚌 Trip Type Distribution")
        
        type_counts = trips_df['trip_type'].value_counts()
        fig = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title='Trips by Type'
        )
        st.plotly_chart(fig, use_container_width=True)