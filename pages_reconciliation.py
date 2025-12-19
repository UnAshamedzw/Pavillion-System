"""
pages_reconciliation.py - Daily Reconciliation Module
Pavillion Coaches Bus Management System

Features:
- Daily cash shortfall entry
- Fuel overuse tracking
- Damage recording
- Red ticket management
- Inspector performance tracking
- Automatic payroll deduction integration
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from database import get_connection, get_engine, USE_POSTGRES, get_placeholder
from audit_logger import AuditLogger
from auth import has_permission


# =============================================================================
# RED TICKETS FUNCTIONS
# =============================================================================

def get_conductors():
    """Get active conductors"""
    conn = get_connection()
    ph = get_placeholder()
    try:
        query = f"""
            SELECT id, employee_id, full_name, job_title 
            FROM employees 
            WHERE status = 'Active' 
              AND (job_title LIKE {ph} OR job_title LIKE {ph})
            ORDER BY full_name
        """
        df = pd.read_sql_query(query, get_engine(), params=('%Conductor%', '%conductor%'))
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def get_inspectors():
    """Get active inspectors (Risk Management)"""
    conn = get_connection()
    ph = get_placeholder()
    try:
        query = f"""
            SELECT id, employee_id, full_name, job_title, department 
            FROM employees 
            WHERE status = 'Active' 
              AND (department LIKE {ph} OR job_title LIKE {ph} OR job_title LIKE {ph})
            ORDER BY full_name
        """
        df = pd.read_sql_query(query, get_engine(), params=('%Risk%', '%Inspector%', '%inspector%'))
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def get_drivers():
    """Get active drivers"""
    conn = get_connection()
    ph = get_placeholder()
    try:
        query = f"""
            SELECT id, employee_id, full_name, job_title 
            FROM employees 
            WHERE status = 'Active' 
              AND (job_title LIKE {ph} OR job_title LIKE {ph})
            ORDER BY full_name
        """
        df = pd.read_sql_query(query, get_engine(), params=('%Driver%', '%driver%'))
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def get_buses():
    """Get active buses"""
    conn = get_connection()
    try:
        query = "SELECT id, registration_number, bus_name FROM buses WHERE status = 'Active' ORDER BY registration_number"
        df = pd.read_sql_query(query, get_engine())
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def get_routes():
    """Get active routes"""
    conn = get_connection()
    try:
        query = "SELECT id, route_name, start_point, end_point FROM routes WHERE status = 'Active' ORDER BY route_name"
        df = pd.read_sql_query(query, get_engine())
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def add_red_ticket(ticket_date, conductor_id, conductor_name, inspector_id, inspector_name,
                   bus_number, route, amount, passenger_count, description, created_by):
    """Add a red ticket record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO red_tickets 
                (ticket_date, conductor_id, conductor_name, inspector_id, inspector_name,
                 bus_number, route, amount, passenger_count, description, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s)
                RETURNING id
            ''', (ticket_date, conductor_id, conductor_name, inspector_id, inspector_name,
                  bus_number, route, amount, passenger_count, description, created_by))
            result = cursor.fetchone()
            ticket_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO red_tickets 
                (ticket_date, conductor_id, conductor_name, inspector_id, inspector_name,
                 bus_number, route, amount, passenger_count, description, status, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            ''', (str(ticket_date), conductor_id, conductor_name, inspector_id, inspector_name,
                  bus_number, route, amount, passenger_count, description, created_by))
            ticket_id = cursor.lastrowid
        
        conn.commit()
        return ticket_id
    except Exception as e:
        conn.rollback()
        print(f"Error adding red ticket: {e}")
        return None
    finally:
        conn.close()


def get_red_tickets(start_date=None, end_date=None, conductor_id=None, inspector_id=None, status=None):
    """Get red tickets with filters"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = "SELECT * FROM red_tickets WHERE 1=1"
    params = []
    
    if start_date:
        query += f" AND ticket_date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND ticket_date <= {ph}"
        params.append(str(end_date))
    
    if conductor_id:
        query += f" AND conductor_id = {ph}"
        params.append(conductor_id)
    
    if inspector_id:
        query += f" AND inspector_id = {ph}"
        params.append(inspector_id)
    
    if status:
        query += f" AND status = {ph}"
        params.append(status)
    
    query += " ORDER BY ticket_date DESC, created_at DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def update_red_ticket_status(ticket_id, status, payroll_id=None):
    """Update red ticket status"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        if payroll_id:
            query = f"UPDATE red_tickets SET status = {ph}, applied_to_payroll_id = {ph} WHERE id = {ph}"
            cursor.execute(query, (status, payroll_id, ticket_id))
        else:
            query = f"UPDATE red_tickets SET status = {ph} WHERE id = {ph}"
            cursor.execute(query, (status, ticket_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating red ticket: {e}")
        return False
    finally:
        conn.close()


def delete_red_ticket(ticket_id):
    """Delete a red ticket"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        cursor.execute(f"DELETE FROM red_tickets WHERE id = {ph}", (ticket_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error deleting red ticket: {e}")
        return False
    finally:
        conn.close()


# =============================================================================
# DAILY RECONCILIATION FUNCTIONS
# =============================================================================

def add_reconciliation(recon_date, employee_id, employee_name, employee_role, bus_number, route,
                       expected_amount, actual_amount, fuel_expected, fuel_actual,
                       damage_amount, damage_description, other_deductions, other_description,
                       notes, reconciled_by):
    """Add a daily reconciliation record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Calculate shortages/overages
    shortage = max(0, expected_amount - actual_amount) if expected_amount > 0 else 0
    overage = max(0, actual_amount - expected_amount) if actual_amount > expected_amount else 0
    
    fuel_overuse = max(0, fuel_actual - fuel_expected) if fuel_actual > fuel_expected else 0
    # Assume fuel cost of $1.50/L for now - this could be configurable
    fuel_cost_per_liter = 1.50
    fuel_overuse_cost = fuel_overuse * fuel_cost_per_liter
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO daily_reconciliation 
                (reconciliation_date, employee_id, employee_name, employee_role, bus_number, route,
                 expected_amount, actual_amount, shortage_amount, overage_amount,
                 fuel_expected, fuel_actual, fuel_overuse, fuel_overuse_cost,
                 damage_amount, damage_description, other_deductions, other_deductions_description,
                 notes, status, reconciled_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s)
                RETURNING id
            ''', (recon_date, employee_id, employee_name, employee_role, bus_number, route,
                  expected_amount, actual_amount, shortage, overage,
                  fuel_expected, fuel_actual, fuel_overuse, fuel_overuse_cost,
                  damage_amount, damage_description, other_deductions, other_description,
                  notes, reconciled_by))
            result = cursor.fetchone()
            recon_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO daily_reconciliation 
                (reconciliation_date, employee_id, employee_name, employee_role, bus_number, route,
                 expected_amount, actual_amount, shortage_amount, overage_amount,
                 fuel_expected, fuel_actual, fuel_overuse, fuel_overuse_cost,
                 damage_amount, damage_description, other_deductions, other_deductions_description,
                 notes, status, reconciled_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            ''', (str(recon_date), employee_id, employee_name, employee_role, bus_number, route,
                  expected_amount, actual_amount, shortage, overage,
                  fuel_expected, fuel_actual, fuel_overuse, fuel_overuse_cost,
                  damage_amount, damage_description, other_deductions, other_description,
                  notes, reconciled_by))
            recon_id = cursor.lastrowid
        
        conn.commit()
        return recon_id
    except Exception as e:
        conn.rollback()
        print(f"Error adding reconciliation: {e}")
        return None
    finally:
        conn.close()


def get_reconciliations(start_date=None, end_date=None, employee_id=None, status=None):
    """Get reconciliation records with filters"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = "SELECT * FROM daily_reconciliation WHERE 1=1"
    params = []
    
    if start_date:
        query += f" AND reconciliation_date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND reconciliation_date <= {ph}"
        params.append(str(end_date))
    
    if employee_id:
        query += f" AND employee_id = {ph}"
        params.append(employee_id)
    
    if status:
        query += f" AND status = {ph}"
        params.append(status)
    
    query += " ORDER BY reconciliation_date DESC, created_at DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def add_employee_deduction(employee_id, deduction_type, description, amount, date_incurred, created_by):
    """Add an employee deduction/penalty"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO employee_deductions 
                (employee_id, deduction_type, description, amount, date_incurred, status, created_by)
                VALUES (%s, %s, %s, %s, %s, 'pending', %s)
                RETURNING id
            ''', (employee_id, deduction_type, description, amount, date_incurred, created_by))
            result = cursor.fetchone()
            ded_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO employee_deductions 
                (employee_id, deduction_type, description, amount, date_incurred, status, created_by)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            ''', (employee_id, deduction_type, description, amount, str(date_incurred), created_by))
            ded_id = cursor.lastrowid
        
        conn.commit()
        return ded_id
    except Exception as e:
        conn.rollback()
        print(f"Error adding deduction: {e}")
        return None
    finally:
        conn.close()


def get_employee_deductions(employee_id=None, status=None, start_date=None, end_date=None):
    """Get employee deductions with filters"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = "SELECT * FROM employee_deductions WHERE 1=1"
    params = []
    
    if employee_id:
        query += f" AND employee_id = {ph}"
        params.append(employee_id)
    
    if status:
        query += f" AND status = {ph}"
        params.append(status)
    
    if start_date:
        query += f" AND date_incurred >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND date_incurred <= {ph}"
        params.append(str(end_date))
    
    query += " ORDER BY date_incurred DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    except:
        df = pd.DataFrame()
    conn.close()
    return df


# =============================================================================
# MAIN PAGE
# =============================================================================

def daily_reconciliation_page():
    """Daily reconciliation and red tickets page"""
    
    st.header("📋 Daily Reconciliation")
    st.markdown("Record daily cash shortfalls, fuel issues, red tickets, and penalties")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💵 Cash Reconciliation",
        "🎫 Red Tickets",
        "⚠️ Penalties & Deductions",
        "📊 Summary",
        "👮 Inspector Performance"
    ])
    
    with tab1:
        cash_reconciliation_tab()
    
    with tab2:
        red_tickets_tab()
    
    with tab3:
        penalties_tab()
    
    with tab4:
        summary_tab()
    
    with tab5:
        inspector_performance_tab()


def cash_reconciliation_tab():
    """Cash reconciliation entry tab"""
    
    st.subheader("💵 Daily Cash Reconciliation")
    st.markdown("Record cash shortfalls, fuel overuse, and damage for conductors/drivers")
    
    # Get employees and buses
    conductors = get_conductors()
    drivers = get_drivers()
    buses = get_buses()
    routes = get_routes()
    
    # Combine drivers and conductors
    all_employees = pd.concat([
        conductors.assign(type='Conductor'),
        drivers.assign(type='Driver')
    ], ignore_index=True) if not conductors.empty or not drivers.empty else pd.DataFrame()
    
    if all_employees.empty:
        st.warning("No employees found. Add employees first.")
        return
    
    st.markdown("### ➕ Add Reconciliation Entry")
    
    col1, col2 = st.columns(2)
    
    with col1:
        recon_date = st.date_input("📅 Date", value=datetime.now().date())
        
        # Employee selection
        emp_options = {f"{row['full_name']} ({row['type']})": (row['id'], row['full_name'], row['type']) 
                      for _, row in all_employees.iterrows()}
        selected_emp = st.selectbox("👤 Employee*", list(emp_options.keys()))
        
        if selected_emp:
            emp_id, emp_name, emp_role = emp_options[selected_emp]
    
    with col2:
        # Bus selection
        bus_options = [""] + [row['registration_number'] for _, row in buses.iterrows()] if not buses.empty else [""]
        selected_bus = st.selectbox("🚌 Bus", bus_options)
        
        # Route selection
        route_options = [""] + [row['route_name'] for _, row in routes.iterrows()] if not routes.empty else [""]
        selected_route = st.selectbox("🛣️ Route", route_options)
    
    st.markdown("---")
    st.markdown("### 💰 Cash Reconciliation")
    
    cash_col1, cash_col2, cash_col3 = st.columns(3)
    
    with cash_col1:
        expected_amount = st.number_input("Expected Amount ($)", min_value=0.0, step=10.0, 
                                          help="Expected revenue from ticketing system")
    
    with cash_col2:
        actual_amount = st.number_input("Actual Amount ($)", min_value=0.0, step=10.0,
                                        help="Actual cash handed in")
    
    with cash_col3:
        if expected_amount > 0:
            shortage = max(0, expected_amount - actual_amount)
            overage = max(0, actual_amount - expected_amount)
            if shortage > 0:
                st.metric("🔴 Shortage", f"${shortage:,.2f}", delta=f"-${shortage:,.2f}", delta_color="inverse")
            elif overage > 0:
                st.metric("🟢 Overage", f"${overage:,.2f}", delta=f"+${overage:,.2f}")
            else:
                st.metric("✅ Balanced", "$0.00")
        else:
            st.metric("Balance", "N/A")
    
    st.markdown("---")
    st.markdown("### ⛽ Fuel Reconciliation (Drivers)")
    
    fuel_col1, fuel_col2, fuel_col3 = st.columns(3)
    
    with fuel_col1:
        fuel_expected = st.number_input("Expected Fuel (L)", min_value=0.0, step=5.0,
                                        help="Expected fuel consumption for route/distance")
    
    with fuel_col2:
        fuel_actual = st.number_input("Actual Fuel Used (L)", min_value=0.0, step=5.0,
                                      help="Actual fuel recorded")
    
    with fuel_col3:
        if fuel_expected > 0 and fuel_actual > 0:
            fuel_diff = fuel_actual - fuel_expected
            if fuel_diff > 0:
                fuel_cost = fuel_diff * 1.50  # Assume $1.50/L
                st.metric("🔴 Fuel Overuse", f"{fuel_diff:.1f}L", delta=f"${fuel_cost:.2f} penalty")
            else:
                st.metric("✅ Fuel OK", f"{abs(fuel_diff):.1f}L saved")
        else:
            st.metric("Fuel Diff", "N/A")
    
    st.markdown("---")
    st.markdown("### 🔧 Damage (If Applicable)")
    
    damage_col1, damage_col2 = st.columns(2)
    
    with damage_col1:
        damage_amount = st.number_input("Damage Penalty ($)", min_value=0.0, step=10.0,
                                        help="Penalty amount for bus damage (if driver responsible)")
    
    with damage_col2:
        damage_description = st.text_input("Damage Description", placeholder="e.g., Side mirror broken")
    
    st.markdown("---")
    st.markdown("### ➕ Other Deductions")
    
    other_col1, other_col2 = st.columns(2)
    
    with other_col1:
        other_deductions = st.number_input("Other Deductions ($)", min_value=0.0, step=5.0)
    
    with other_col2:
        other_description = st.text_input("Description", placeholder="e.g., Uniform replacement")
    
    notes = st.text_area("📝 Notes", placeholder="Additional notes about this reconciliation...")
    
    # Calculate total deductions
    shortage_amount = max(0, expected_amount - actual_amount) if expected_amount > 0 else 0
    fuel_overuse_cost = max(0, (fuel_actual - fuel_expected) * 1.50) if fuel_actual > fuel_expected else 0
    total_deductions = shortage_amount + fuel_overuse_cost + damage_amount + other_deductions
    
    st.markdown("---")
    st.markdown("### 📊 Summary")
    
    sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
    
    with sum_col1:
        st.metric("Cash Shortage", f"${shortage_amount:,.2f}")
    with sum_col2:
        st.metric("Fuel Overuse", f"${fuel_overuse_cost:,.2f}")
    with sum_col3:
        st.metric("Damage", f"${damage_amount:,.2f}")
    with sum_col4:
        st.metric("Total Deductions", f"${total_deductions:,.2f}")
    
    if st.button("💾 Save Reconciliation", type="primary", use_container_width=True):
        if not selected_emp:
            st.error("Please select an employee")
            return
        
        recon_id = add_reconciliation(
            recon_date=recon_date,
            employee_id=emp_id,
            employee_name=emp_name,
            employee_role=emp_role,
            bus_number=selected_bus,
            route=selected_route,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            fuel_expected=fuel_expected,
            fuel_actual=fuel_actual,
            damage_amount=damage_amount,
            damage_description=damage_description,
            other_deductions=other_deductions,
            other_description=other_description,
            notes=notes,
            reconciled_by=st.session_state['user']['username']
        )
        
        if recon_id:
            AuditLogger.log_action("Create", "Reconciliation", 
                                  f"Reconciliation for {emp_name} - Total deductions: ${total_deductions:.2f}")
            st.success(f"✅ Reconciliation saved! (ID: {recon_id})")
            
            if total_deductions > 0:
                st.info(f"💰 ${total_deductions:.2f} will be deducted from {emp_name}'s next payroll")
        else:
            st.error("❌ Error saving reconciliation")
    
    # Show recent reconciliations
    st.markdown("---")
    st.markdown("### 📋 Recent Reconciliations")
    
    recent = get_reconciliations(
        start_date=datetime.now().date() - timedelta(days=30)
    )
    
    if not recent.empty:
        display_df = recent[['reconciliation_date', 'employee_name', 'employee_role', 
                            'shortage_amount', 'fuel_overuse_cost', 'damage_amount', 'status']].copy()
        display_df.columns = ['Date', 'Employee', 'Role', 'Shortage', 'Fuel', 'Damage', 'Status']
        display_df['Total'] = display_df['Shortage'] + display_df['Fuel'] + display_df['Damage']
        
        for col in ['Shortage', 'Fuel', 'Damage', 'Total']:
            display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent reconciliations found")


def red_tickets_tab():
    """Red tickets entry and management"""
    
    st.subheader("🎫 Red Tickets")
    st.markdown("Record red tickets issued by inspectors for unpaid passengers/luggage")
    
    # Get required data
    conductors = get_conductors()
    inspectors = get_inspectors()
    buses = get_buses()
    routes = get_routes()
    
    if inspectors.empty:
        st.warning("⚠️ No inspectors found. Add employees with 'Inspector' job title or 'Risk Management' department.")
        st.info("To add inspectors: Go to Employee Management and add employees with job title containing 'Inspector' or department 'Risk Management'")
    
    if conductors.empty:
        st.warning("⚠️ No conductors found.")
        return
    
    # Entry form
    st.markdown("### ➕ Issue Red Ticket")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ticket_date = st.date_input("📅 Date", value=datetime.now().date(), key="rt_date")
        
        # Conductor selection
        conductor_options = {row['full_name']: (row['id'], row['full_name']) 
                           for _, row in conductors.iterrows()}
        selected_conductor = st.selectbox("👤 Conductor*", list(conductor_options.keys()))
        
        if selected_conductor:
            conductor_id, conductor_name = conductor_options[selected_conductor]
        
        # Amount
        ticket_amount = st.number_input("💵 Ticket Amount ($)*", min_value=0.0, step=1.0,
                                        help="Monetary value of the red ticket")
    
    with col2:
        # Inspector selection
        if not inspectors.empty:
            inspector_options = {row['full_name']: (row['id'], row['full_name']) 
                               for _, row in inspectors.iterrows()}
            selected_inspector = st.selectbox("👮 Inspector*", list(inspector_options.keys()))
            
            if selected_inspector:
                inspector_id, inspector_name = inspector_options[selected_inspector]
        else:
            inspector_id, inspector_name = None, "N/A"
            st.text_input("👮 Inspector", value="No inspectors available", disabled=True)
        
        # Passenger count
        passenger_count = st.number_input("👥 Unpaid Passengers", min_value=1, value=1, step=1)
        
        # Bus
        bus_options = [""] + [row['registration_number'] for _, row in buses.iterrows()] if not buses.empty else [""]
        selected_bus = st.selectbox("🚌 Bus", bus_options, key="rt_bus")
    
    # Route
    route_options = [""] + [row['route_name'] for _, row in routes.iterrows()] if not routes.empty else [""]
    selected_route = st.selectbox("🛣️ Route", route_options, key="rt_route")
    
    description = st.text_area("📝 Description", placeholder="e.g., Passenger boarded at Mbare without ticket")
    
    if st.button("🎫 Issue Red Ticket", type="primary", use_container_width=True):
        if not selected_conductor:
            st.error("Please select a conductor")
        elif ticket_amount <= 0:
            st.error("Please enter a valid amount")
        elif not inspectors.empty and not selected_inspector:
            st.error("Please select an inspector")
        else:
            ticket_id = add_red_ticket(
                ticket_date=ticket_date,
                conductor_id=conductor_id,
                conductor_name=conductor_name,
                inspector_id=inspector_id if not inspectors.empty else 0,
                inspector_name=inspector_name,
                bus_number=selected_bus,
                route=selected_route,
                amount=ticket_amount,
                passenger_count=passenger_count,
                description=description,
                created_by=st.session_state['user']['username']
            )
            
            if ticket_id:
                AuditLogger.log_action("Create", "Red Ticket", 
                                      f"Red ticket #{ticket_id} issued to {conductor_name} - ${ticket_amount}")
                st.success(f"✅ Red Ticket #{ticket_id} issued!")
                st.info(f"💰 ${ticket_amount:.2f} will be deducted from {conductor_name}'s payroll")
            else:
                st.error("❌ Error issuing red ticket")
    
    # View/Edit section
    st.markdown("---")
    st.markdown("### 📋 Red Ticket History")
    
    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        filter_start = st.date_input("From", value=datetime.now().date() - timedelta(days=30), key="rt_filter_start")
    
    with filter_col2:
        filter_end = st.date_input("To", value=datetime.now().date(), key="rt_filter_end")
    
    with filter_col3:
        status_filter = st.selectbox("Status", ["All", "Pending", "Applied", "Cancelled"], key="rt_status")
    
    tickets = get_red_tickets(
        start_date=filter_start,
        end_date=filter_end,
        status=status_filter.lower() if status_filter != "All" else None
    )
    
    if not tickets.empty:
        # Summary metrics
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        
        with metric_col1:
            st.metric("Total Tickets", len(tickets))
        with metric_col2:
            st.metric("Total Amount", f"${tickets['amount'].sum():,.2f}")
        with metric_col3:
            pending = len(tickets[tickets['status'] == 'pending'])
            st.metric("Pending", pending)
        
        # Display table
        display_df = tickets[['ticket_date', 'conductor_name', 'inspector_name', 
                             'amount', 'passenger_count', 'bus_number', 'route', 'status']].copy()
        display_df.columns = ['Date', 'Conductor', 'Inspector', 'Amount', 'Passengers', 'Bus', 'Route', 'Status']
        display_df['Amount'] = display_df['Amount'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Delete option
        if has_permission('delete_red_ticket'):
            st.markdown("---")
            st.markdown("### ❌ Delete Red Ticket")
            
            delete_options = {f"#{row['id']} - {row['conductor_name']} (${row['amount']:.2f})": row['id'] 
                            for _, row in tickets.iterrows() if row['status'] == 'pending'}
            
            if delete_options:
                selected_delete = st.selectbox("Select ticket to delete", list(delete_options.keys()))
                
                if st.button("🗑️ Delete Selected Ticket", type="secondary"):
                    if delete_red_ticket(delete_options[selected_delete]):
                        st.success("Ticket deleted!")
                        st.rerun()
                    else:
                        st.error("Error deleting ticket")
            else:
                st.info("No pending tickets to delete")
    else:
        st.info("No red tickets found for the selected period")


def penalties_tab():
    """General penalties and deductions"""
    
    st.subheader("⚠️ Penalties & Deductions")
    st.markdown("Record ad-hoc penalties for employees")
    
    # Get all employees
    conn = get_connection()
    try:
        employees = pd.read_sql_query(
            "SELECT id, employee_id, full_name, job_title FROM employees WHERE status = 'Active' ORDER BY full_name",
            get_engine()
        )
    except:
        employees = pd.DataFrame()
    conn.close()
    
    if employees.empty:
        st.warning("No employees found")
        return
    
    st.markdown("### ➕ Add Penalty/Deduction")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Employee selection
        emp_options = {f"{row['full_name']} ({row['job_title']})": row['id'] 
                      for _, row in employees.iterrows()}
        selected_emp = st.selectbox("👤 Employee*", list(emp_options.keys()), key="pen_emp")
        
        penalty_date = st.date_input("📅 Date", value=datetime.now().date(), key="pen_date")
    
    with col2:
        # Deduction type - free form but with suggestions
        deduction_types = [
            "Misconduct",
            "Late Arrival",
            "Uniform Violation",
            "Customer Complaint",
            "Traffic Fine",
            "Property Damage",
            "Safety Violation",
            "Insubordination",
            "Unauthorized Absence",
            "Other"
        ]
        deduction_type = st.selectbox("📋 Penalty Type", deduction_types)
        
        penalty_amount = st.number_input("💵 Amount ($)*", min_value=0.0, step=5.0, key="pen_amount")
    
    penalty_description = st.text_area("📝 Description*", 
                                       placeholder="Describe the reason for this penalty...",
                                       key="pen_desc")
    
    if st.button("💾 Add Penalty", type="primary", use_container_width=True):
        if not selected_emp:
            st.error("Please select an employee")
        elif penalty_amount <= 0:
            st.error("Please enter a valid amount")
        elif not penalty_description:
            st.error("Please enter a description")
        else:
            emp_id = emp_options[selected_emp]
            
            ded_id = add_employee_deduction(
                employee_id=emp_id,
                deduction_type=deduction_type,
                description=penalty_description,
                amount=penalty_amount,
                date_incurred=penalty_date,
                created_by=st.session_state['user']['username']
            )
            
            if ded_id:
                emp_name = selected_emp.split(" (")[0]
                AuditLogger.log_action("Create", "Penalty", 
                                      f"Penalty for {emp_name}: ${penalty_amount} - {deduction_type}")
                st.success(f"✅ Penalty recorded!")
                st.info(f"💰 ${penalty_amount:.2f} will be deducted from next payroll")
            else:
                st.error("❌ Error recording penalty")
    
    # View existing penalties
    st.markdown("---")
    st.markdown("### 📋 Recent Penalties")
    
    penalties = get_employee_deductions(
        start_date=datetime.now().date() - timedelta(days=90)
    )
    
    if not penalties.empty:
        # Join with employee names
        penalties_display = penalties.merge(
            employees[['id', 'full_name']], 
            left_on='employee_id', 
            right_on='id', 
            how='left'
        )
        
        display_df = penalties_display[['date_incurred', 'full_name', 'deduction_type', 
                                        'amount', 'description', 'status']].copy()
        display_df.columns = ['Date', 'Employee', 'Type', 'Amount', 'Description', 'Status']
        display_df['Amount'] = display_df['Amount'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Summary
        st.metric("Total Pending Deductions", 
                 f"${penalties[penalties['status'] == 'pending']['amount'].sum():,.2f}")
    else:
        st.info("No recent penalties found")


def summary_tab():
    """Summary of all pending deductions"""
    
    st.subheader("📊 Deductions Summary")
    st.markdown("Overview of all pending deductions by employee")
    
    # Date range filter
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("From", value=datetime.now().date().replace(day=1), key="sum_start")
    
    with col2:
        end_date = st.date_input("To", value=datetime.now().date(), key="sum_end")
    
    # Get all deduction sources
    reconciliations = get_reconciliations(start_date=start_date, end_date=end_date, status='pending')
    red_tickets = get_red_tickets(start_date=start_date, end_date=end_date, status='pending')
    penalties = get_employee_deductions(start_date=start_date, end_date=end_date, status='pending')
    
    # Aggregate by employee
    employee_totals = {}
    
    # From reconciliations
    if not reconciliations.empty:
        for _, row in reconciliations.iterrows():
            emp_id = row['employee_id']
            emp_name = row['employee_name']
            total = (row.get('shortage_amount', 0) or 0) + \
                   (row.get('fuel_overuse_cost', 0) or 0) + \
                   (row.get('damage_amount', 0) or 0) + \
                   (row.get('other_deductions', 0) or 0)
            
            if emp_id not in employee_totals:
                employee_totals[emp_id] = {'name': emp_name, 'shortage': 0, 'fuel': 0, 
                                           'damage': 0, 'red_tickets': 0, 'penalties': 0}
            
            employee_totals[emp_id]['shortage'] += row.get('shortage_amount', 0) or 0
            employee_totals[emp_id]['fuel'] += row.get('fuel_overuse_cost', 0) or 0
            employee_totals[emp_id]['damage'] += row.get('damage_amount', 0) or 0
    
    # From red tickets
    if not red_tickets.empty:
        for _, row in red_tickets.iterrows():
            emp_id = row['conductor_id']
            emp_name = row['conductor_name']
            
            if emp_id not in employee_totals:
                employee_totals[emp_id] = {'name': emp_name, 'shortage': 0, 'fuel': 0, 
                                           'damage': 0, 'red_tickets': 0, 'penalties': 0}
            
            employee_totals[emp_id]['red_tickets'] += row['amount']
    
    # From general penalties
    if not penalties.empty:
        conn = get_connection()
        employees = pd.read_sql_query("SELECT id, full_name FROM employees", get_engine())
        conn.close()
        emp_names = dict(zip(employees['id'], employees['full_name']))
        
        for _, row in penalties.iterrows():
            emp_id = row['employee_id']
            emp_name = emp_names.get(emp_id, 'Unknown')
            
            if emp_id not in employee_totals:
                employee_totals[emp_id] = {'name': emp_name, 'shortage': 0, 'fuel': 0, 
                                           'damage': 0, 'red_tickets': 0, 'penalties': 0}
            
            employee_totals[emp_id]['penalties'] += row['amount']
    
    if employee_totals:
        # Create summary dataframe
        summary_data = []
        for emp_id, data in employee_totals.items():
            total = data['shortage'] + data['fuel'] + data['damage'] + data['red_tickets'] + data['penalties']
            if total > 0:
                summary_data.append({
                    'Employee': data['name'],
                    'Cash Shortage': data['shortage'],
                    'Fuel Overuse': data['fuel'],
                    'Damage': data['damage'],
                    'Red Tickets': data['red_tickets'],
                    'Penalties': data['penalties'],
                    'Total': total
                })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df = summary_df.sort_values('Total', ascending=False)
            
            # Overall metrics
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            
            with metric_col1:
                st.metric("Employees with Deductions", len(summary_df))
            with metric_col2:
                st.metric("Total Pending", f"${summary_df['Total'].sum():,.2f}")
            with metric_col3:
                st.metric("Largest Individual", f"${summary_df['Total'].max():,.2f}")
            
            # Format currency columns
            for col in ['Cash Shortage', 'Fuel Overuse', 'Damage', 'Red Tickets', 'Penalties', 'Total']:
                summary_df[col] = summary_df[col].apply(lambda x: f"${x:,.2f}")
            
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No pending deductions for any employee!")
    else:
        st.success("✅ No pending deductions found for the selected period")


def inspector_performance_tab():
    """Inspector performance tracking"""
    
    st.subheader("👮 Inspector Performance")
    st.markdown("Track inspector red ticket issuance and trends")
    
    inspectors = get_inspectors()
    
    if inspectors.empty:
        st.warning("No inspectors found. Add employees with 'Inspector' job title or 'Risk Management' department.")
        return
    
    # Date range
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("From", value=datetime.now().date() - timedelta(days=30), key="insp_start")
    
    with col2:
        end_date = st.date_input("To", value=datetime.now().date(), key="insp_end")
    
    # Get all red tickets for the period
    tickets = get_red_tickets(start_date=start_date, end_date=end_date)
    
    if tickets.empty:
        st.info("No red tickets found for this period")
        return
    
    # Aggregate by inspector
    inspector_stats = tickets.groupby(['inspector_id', 'inspector_name']).agg({
        'id': 'count',
        'amount': 'sum',
        'passenger_count': 'sum'
    }).reset_index()
    inspector_stats.columns = ['Inspector ID', 'Inspector', 'Tickets Issued', 'Total Amount', 'Passengers Caught']
    
    # Calculate metrics
    total_tickets = len(tickets)
    total_amount = tickets['amount'].sum()
    
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    
    with metric_col1:
        st.metric("Total Tickets", total_tickets)
    with metric_col2:
        st.metric("Total Value", f"${total_amount:,.2f}")
    with metric_col3:
        st.metric("Active Inspectors", len(inspector_stats))
    with metric_col4:
        avg_per_inspector = total_tickets / len(inspector_stats) if len(inspector_stats) > 0 else 0
        st.metric("Avg per Inspector", f"{avg_per_inspector:.1f}")
    
    st.markdown("---")
    st.markdown("### 📊 Inspector Ranking")
    
    # Sort by tickets issued
    inspector_stats = inspector_stats.sort_values('Tickets Issued', ascending=False)
    inspector_stats['Avg per Ticket'] = inspector_stats['Total Amount'] / inspector_stats['Tickets Issued']
    
    # Format currency
    inspector_stats['Total Amount'] = inspector_stats['Total Amount'].apply(lambda x: f"${x:,.2f}")
    inspector_stats['Avg per Ticket'] = inspector_stats['Avg per Ticket'].apply(lambda x: f"${x:,.2f}")
    
    display_df = inspector_stats[['Inspector', 'Tickets Issued', 'Passengers Caught', 'Total Amount', 'Avg per Ticket']]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Tickets by day trend
    st.markdown("---")
    st.markdown("### 📈 Daily Trend")
    
    daily = tickets.groupby('ticket_date').agg({'id': 'count', 'amount': 'sum'}).reset_index()
    daily.columns = ['Date', 'Tickets', 'Amount']
    
    st.line_chart(daily.set_index('Date')['Tickets'])
    
    # Top conductors receiving tickets
    st.markdown("---")
    st.markdown("### 🔴 Conductors with Most Red Tickets")
    
    conductor_stats = tickets.groupby(['conductor_id', 'conductor_name']).agg({
        'id': 'count',
        'amount': 'sum'
    }).reset_index()
    conductor_stats.columns = ['ID', 'Conductor', 'Tickets Received', 'Total Amount']
    conductor_stats = conductor_stats.sort_values('Tickets Received', ascending=False).head(10)
    conductor_stats['Total Amount'] = conductor_stats['Total Amount'].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(conductor_stats[['Conductor', 'Tickets Received', 'Total Amount']], 
                use_container_width=True, hide_index=True)
