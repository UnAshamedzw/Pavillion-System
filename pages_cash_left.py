"""
pages_cash_left.py - Cash Left at Rank Tracking Module
Pavillion Coaches Bus Management System

Track cash left by drivers/conductors at the rank before departing on trips.
This cash is collected later when they return with additional revenue.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES, get_placeholder
from audit_logger import AuditLogger
from auth import has_permission


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_pending_cash_left():
    """Get all pending (uncollected) cash left records"""
    conn = get_connection()
    try:
        query = """
            SELECT * FROM cash_left 
            WHERE status = 'pending'
            ORDER BY date_left DESC, created_at DESC
        """
        df = pd.read_sql_query(query, get_engine())
    except Exception as e:
        print(f"Error getting pending cash left: {e}")
        df = pd.DataFrame()
    conn.close()
    return df


def get_cash_left_summary():
    """Get summary of pending cash left for dashboard"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                COALESCE(SUM(amount), 0) as total_amount
            FROM cash_left 
            WHERE status = 'pending'
        """)
        result = cursor.fetchone()
        
        if result:
            if hasattr(result, 'keys'):
                return {
                    'count': result['total_records'] or 0,
                    'amount': result['total_amount'] or 0
                }
            else:
                return {
                    'count': result[0] or 0,
                    'amount': result[1] or 0
                }
    except Exception as e:
        print(f"Error getting cash left summary: {e}")
    finally:
        conn.close()
    
    return {'count': 0, 'amount': 0}


def get_cash_left_by_bus(bus_number):
    """Get pending cash left for a specific bus"""
    conn = get_connection()
    ph = get_placeholder()
    
    try:
        query = f"""
            SELECT * FROM cash_left 
            WHERE bus_number = {ph} AND status = 'pending'
            ORDER BY date_left DESC
        """
        df = pd.read_sql_query(query, get_engine(), params=(bus_number,))
    except Exception as e:
        print(f"Error getting cash left for bus: {e}")
        df = pd.DataFrame()
    conn.close()
    return df


def get_all_cash_left(start_date=None, end_date=None, status=None):
    """Get all cash left records with optional filters"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = "SELECT * FROM cash_left WHERE 1=1"
    params = []
    
    if start_date:
        query += f" AND date_left >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND date_left <= {ph}"
        params.append(str(end_date))
    
    if status:
        query += f" AND status = {ph}"
        params.append(status)
    
    query += " ORDER BY date_left DESC, created_at DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    except Exception as e:
        print(f"Error getting cash left records: {e}")
        df = pd.DataFrame()
    conn.close()
    return df


def add_cash_left(date_left, bus_number, driver_name, driver_employee_id,
                  conductor_name, conductor_employee_id, amount, supervisor_name,
                  route=None, reason=None, notes=None, created_by=None):
    """Add a new cash left record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO cash_left 
                (date_left, bus_number, driver_name, driver_employee_id,
                 conductor_name, conductor_employee_id, amount, supervisor_name,
                 route, reason, notes, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s)
                RETURNING id
            ''', (str(date_left), bus_number, driver_name, driver_employee_id,
                  conductor_name, conductor_employee_id, amount, supervisor_name,
                  route, reason, notes, created_by))
            result = cursor.fetchone()
            record_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO cash_left 
                (date_left, bus_number, driver_name, driver_employee_id,
                 conductor_name, conductor_employee_id, amount, supervisor_name,
                 route, reason, notes, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            ''', (str(date_left), bus_number, driver_name, driver_employee_id,
                  conductor_name, conductor_employee_id, amount, supervisor_name,
                  route, reason, notes, created_by))
            record_id = cursor.lastrowid
        
        conn.commit()
        return record_id
    except Exception as e:
        conn.rollback()
        print(f"Error adding cash left: {e}")
        return None
    finally:
        conn.close()


def collect_cash_left(record_id, collected_by, collection_notes=None, linked_income_id=None):
    """Mark cash left as collected"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        if USE_POSTGRES:
            cursor.execute(f'''
                UPDATE cash_left 
                SET status = 'collected',
                    date_collected = %s,
                    collected_by = %s,
                    collection_notes = %s,
                    linked_income_id = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (str(datetime.now().date()), collected_by, collection_notes, 
                  linked_income_id, record_id))
        else:
            cursor.execute(f'''
                UPDATE cash_left 
                SET status = 'collected',
                    date_collected = ?,
                    collected_by = ?,
                    collection_notes = ?,
                    linked_income_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (str(datetime.now().date()), collected_by, collection_notes,
                  linked_income_id, record_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error collecting cash left: {e}")
        return False
    finally:
        conn.close()


def cancel_cash_left(record_id, cancelled_by, reason):
    """Cancel a cash left record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                UPDATE cash_left 
                SET status = 'cancelled',
                    collection_notes = %s,
                    collected_by = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            ''', (f"Cancelled: {reason}", cancelled_by, record_id))
        else:
            cursor.execute('''
                UPDATE cash_left 
                SET status = 'cancelled',
                    collection_notes = ?,
                    collected_by = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (f"Cancelled: {reason}", cancelled_by, record_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error cancelling cash left: {e}")
        return False
    finally:
        conn.close()


def get_active_buses():
    """Get list of active buses"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT bus_number, registration_number, make, model 
        FROM buses 
        WHERE status = 'Active' 
        ORDER BY registration_number
    """)
    
    buses = cursor.fetchall()
    conn.close()
    return buses


def get_active_drivers():
    """Get active drivers"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT employee_id, full_name 
        FROM employees 
        WHERE status = 'Active' AND position LIKE '%Driver%'
        ORDER BY full_name
    """)
    
    drivers = cursor.fetchall()
    conn.close()
    return drivers


def get_active_conductors():
    """Get active conductors"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT employee_id, full_name 
        FROM employees 
        WHERE status = 'Active' AND position LIKE '%Conductor%'
        ORDER BY full_name
    """)
    
    conductors = cursor.fetchall()
    conn.close()
    return conductors


def get_routes():
    """Get active routes"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT route_name FROM routes 
            WHERE status = 'Active'
            ORDER BY route_name
        """)
        routes = cursor.fetchall()
    except Exception as e:
        routes = []
    conn.close()
    return routes


# =============================================================================
# UI COMPONENTS
# =============================================================================

def cash_left_dashboard_widget():
    """Widget to show pending cash left on dashboard"""
    summary = get_cash_left_summary()
    
    if summary['count'] > 0:
        st.markdown("### Cash Left at Rank")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Pending Records", summary['count'])
        with col2:
            st.metric("Total Amount", f"${summary['amount']:,.2f}")
        
        # Show details
        pending = get_pending_cash_left()
        if not pending.empty:
            st.markdown("**Pending Cash:**")
            for _, row in pending.iterrows():
                bus = row.get('bus_number', 'N/A')
                amount = row.get('amount', 0)
                driver = row.get('driver_name', 'Unknown')
                date_left = row.get('date_left', 'N/A')
                supervisor = row.get('supervisor_name', 'N/A')
                
                st.markdown(f"- **{bus}**: ${amount:,.2f} - {driver} ({date_left}) - Supervisor: {supervisor}")
        
        st.markdown("---")


def cash_left_page():
    """Main Cash Left Management Page"""
    st.title("Cash Left at Rank")
    st.markdown("Track cash left by drivers/conductors at the rank before trips")
    
    tab1, tab2, tab3 = st.tabs(["Record Cash Left", "Pending Collections", "History"])
    
    with tab1:
        record_cash_left_section()
    
    with tab2:
        pending_collections_section()
    
    with tab3:
        cash_left_history_section()


def record_cash_left_section():
    """Section to record new cash left"""
    st.subheader("Record Cash Left")
    
    # Get buses, drivers, conductors
    buses = get_active_buses()
    drivers = get_active_drivers()
    conductors = get_active_conductors()
    routes = get_routes()
    
    if not buses:
        st.warning("No active buses found. Please add buses first.")
        return
    
    with st.form("cash_left_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Date
            date_left = st.date_input("Date", value=datetime.now().date())
            
            # Bus selection
            bus_options = ["-- Select Bus --"]
            for bus in buses:
                if hasattr(bus, 'keys'):
                    bus_options.append(f"{bus['registration_number']} ({bus['make']} {bus['model']})")
                else:
                    bus_options.append(f"{bus[1]} ({bus[2]} {bus[3]})")
            
            selected_bus = st.selectbox("Bus*", bus_options)
            
            # Driver selection
            driver_options = ["-- Select Driver --"]
            for driver in drivers:
                if hasattr(driver, 'keys'):
                    driver_options.append(f"{driver['full_name']} ({driver['employee_id']})")
                else:
                    driver_options.append(f"{driver[1]} ({driver[0]})")
            
            selected_driver = st.selectbox("Driver", driver_options)
            
            # Conductor selection
            conductor_options = ["-- Select Conductor --"]
            for conductor in conductors:
                if hasattr(conductor, 'keys'):
                    conductor_options.append(f"{conductor['full_name']} ({conductor['employee_id']})")
                else:
                    conductor_options.append(f"{conductor[1]} ({conductor[0]})")
            
            selected_conductor = st.selectbox("Conductor", conductor_options)
        
        with col2:
            # Amount
            amount = st.number_input("Amount Left ($)*", min_value=0.0, step=10.0, format="%.2f")
            
            # Supervisor
            supervisor_name = st.text_input("Supervisor Name*", placeholder="Name of person receiving cash")
            
            # Route
            route_options = ["-- Select Route --"] + [r[0] if isinstance(r, tuple) else r.get('route_name', r) for r in routes]
            route_options.append("Charter/Hire")
            selected_route = st.selectbox("Route (Optional)", route_options)
            
            # Reason
            reason = st.selectbox("Reason", [
                "Safety/Security",
                "Change Float",
                "Partial Handover",
                "End of Shift",
                "Other"
            ])
        
        # Notes
        notes = st.text_area("Notes", placeholder="Additional notes...")
        
        submitted = st.form_submit_button("Record Cash Left", type="primary", use_container_width=True)
        
        if submitted:
            # Validation
            if selected_bus == "-- Select Bus --":
                st.error("Please select a bus")
            elif amount <= 0:
                st.error("Please enter a valid amount")
            elif not supervisor_name.strip():
                st.error("Please enter supervisor name")
            else:
                # Extract bus number
                bus_number = selected_bus.split(" (")[0] if selected_bus != "-- Select Bus --" else None
                
                # Extract driver info
                driver_name = None
                driver_employee_id = None
                if selected_driver != "-- Select Driver --":
                    parts = selected_driver.rsplit(" (", 1)
                    driver_name = parts[0]
                    driver_employee_id = parts[1].rstrip(")") if len(parts) > 1 else None
                
                # Extract conductor info
                conductor_name = None
                conductor_employee_id = None
                if selected_conductor != "-- Select Conductor --":
                    parts = selected_conductor.rsplit(" (", 1)
                    conductor_name = parts[0]
                    conductor_employee_id = parts[1].rstrip(")") if len(parts) > 1 else None
                
                # Route
                route = selected_route if selected_route != "-- Select Route --" else None
                
                # Save record
                record_id = add_cash_left(
                    date_left=date_left,
                    bus_number=bus_number,
                    driver_name=driver_name,
                    driver_employee_id=driver_employee_id,
                    conductor_name=conductor_name,
                    conductor_employee_id=conductor_employee_id,
                    amount=amount,
                    supervisor_name=supervisor_name.strip(),
                    route=route,
                    reason=reason,
                    notes=notes,
                    created_by=st.session_state.get('user', {}).get('username', 'system')
                )
                
                if record_id:
                    AuditLogger.log_action(
                        "Create", "Cash Left",
                        f"Recorded cash left: {bus_number} - ${amount:.2f} to {supervisor_name}"
                    )
                    st.success(f"Cash left recorded successfully! (ID: {record_id})")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Error recording cash left")


def pending_collections_section():
    """Section to view and collect pending cash left"""
    st.subheader("Pending Collections")
    
    pending = get_pending_cash_left()
    
    if pending.empty:
        st.success("No pending cash to collect!")
        return
    
    # Summary
    total_pending = pending['amount'].sum()
    st.metric("Total Pending", f"${total_pending:,.2f}", delta=f"{len(pending)} records")
    
    st.markdown("---")
    
    # List pending records
    for idx, row in pending.iterrows():
        record_id = row.get('id')
        bus_number = row.get('bus_number', 'N/A')
        amount = row.get('amount', 0)
        driver = row.get('driver_name', 'Unknown')
        conductor = row.get('conductor_name', '')
        date_left = row.get('date_left', 'N/A')
        supervisor = row.get('supervisor_name', 'N/A')
        route = row.get('route', 'N/A')
        reason = row.get('reason', '')
        notes = row.get('notes', '')
        
        crew = driver
        if conductor:
            crew += f" & {conductor}"
        
        with st.expander(f"**{bus_number}** - ${amount:,.2f} - {crew} ({date_left})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Bus:** {bus_number}")
                st.write(f"**Amount:** ${amount:,.2f}")
                st.write(f"**Date Left:** {date_left}")
                st.write(f"**Route:** {route or 'N/A'}")
            
            with col2:
                st.write(f"**Driver:** {driver or 'N/A'}")
                st.write(f"**Conductor:** {conductor or 'N/A'}")
                st.write(f"**Supervisor:** {supervisor}")
                st.write(f"**Reason:** {reason or 'N/A'}")
            
            if notes:
                st.info(f"**Notes:** {notes}")
            
            st.markdown("---")
            
            # Collection form
            col_a, col_b = st.columns(2)
            
            with col_a:
                collection_notes = st.text_input(
                    "Collection Notes", 
                    placeholder="Any notes about collection...",
                    key=f"notes_{record_id}"
                )
            
            with col_b:
                st.write("")  # Spacing
                st.write("")
                
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("Collect Cash", key=f"collect_{record_id}", type="primary", use_container_width=True):
                    collected_by = st.session_state.get('user', {}).get('username', 'system')
                    if collect_cash_left(record_id, collected_by, collection_notes):
                        AuditLogger.log_action(
                            "Update", "Cash Left",
                            f"Collected cash: {bus_number} - ${amount:.2f}"
                        )
                        st.success("Cash collected successfully!")
                        st.rerun()
                    else:
                        st.error("Error collecting cash")
            
            with col_btn2:
                if st.button("Cancel Record", key=f"cancel_{record_id}", use_container_width=True):
                    cancelled_by = st.session_state.get('user', {}).get('username', 'system')
                    if cancel_cash_left(record_id, cancelled_by, collection_notes or "Cancelled by user"):
                        AuditLogger.log_action(
                            "Delete", "Cash Left",
                            f"Cancelled cash left: {bus_number} - ${amount:.2f}"
                        )
                        st.warning("Record cancelled")
                        st.rerun()


def cash_left_history_section():
    """Section to view cash left history"""
    st.subheader("Cash Left History")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_date = st.date_input(
            "From Date", 
            value=datetime.now().date() - timedelta(days=30),
            key="history_start"
        )
    
    with col2:
        end_date = st.date_input(
            "To Date",
            value=datetime.now().date(),
            key="history_end"
        )
    
    with col3:
        status_filter = st.selectbox(
            "Status",
            ["All", "pending", "collected", "cancelled"],
            key="history_status"
        )
    
    # Get data
    status = status_filter if status_filter != "All" else None
    history = get_all_cash_left(start_date, end_date, status)
    
    if history.empty:
        st.info("No records found for the selected filters")
        return
    
    # Summary
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    
    with col_s1:
        st.metric("Total Records", len(history))
    
    with col_s2:
        total_amount = history['amount'].sum()
        st.metric("Total Amount", f"${total_amount:,.2f}")
    
    with col_s3:
        collected = len(history[history['status'] == 'collected'])
        st.metric("Collected", collected)
    
    with col_s4:
        pending = len(history[history['status'] == 'pending'])
        st.metric("Pending", pending)
    
    st.markdown("---")
    
    # Display table
    display_cols = ['date_left', 'bus_number', 'driver_name', 'amount', 'supervisor_name', 'status', 'date_collected']
    available_cols = [c for c in display_cols if c in history.columns]
    
    display_df = history[available_cols].copy()
    display_df.columns = [c.replace('_', ' ').title() for c in available_cols]
    
    # Format amount
    if 'Amount' in display_df.columns:
        display_df['Amount'] = display_df['Amount'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Export option
    if st.button("Export to CSV"):
        csv = history.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            file_name=f"cash_left_history_{start_date}_{end_date}.csv",
            mime="text/csv"
        )
