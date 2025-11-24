"""
pages_fleet_management.py - Complete Fleet Management System
Buses, Drivers, Conductors with Insurance & Document Expiry Tracking
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from audit_logger import AuditLogger

def get_expiring_documents(days_threshold=30):
    """Get all documents expiring within the threshold"""
    conn = sqlite3.connect('bus_management.db')
    
    expiring_items = []
    today = datetime.now().date()
    threshold_date = today + timedelta(days=days_threshold)
    
    # Check buses
    try:
        buses_query = """
            SELECT bus_number, registration_number,
                   zinara_licence_expiry, vehicle_insurance_expiry,
                   passenger_insurance_expiry, fitness_expiry, route_permit_expiry
            FROM buses
            WHERE status = 'Active'
        """
        buses_df = pd.read_sql_query(buses_query, conn)
        
        for _, bus in buses_df.iterrows():
            documents = {
                'ZINARA Licence': bus.get('zinara_licence_expiry'),
                'Vehicle Insurance': bus.get('vehicle_insurance_expiry'),
                'Passenger Insurance': bus.get('passenger_insurance_expiry'),
                'Bus Fitness': bus.get('fitness_expiry'),
                'Route Authority Permit': bus.get('route_permit_expiry')
            }
            
            for doc_name, expiry_date in documents.items():
                if expiry_date and expiry_date != '':
                    try:
                        expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
                        days_remaining = (expiry - today).days
                        
                        if days_remaining <= days_threshold:
                            status = 'EXPIRED' if days_remaining < 0 else 'EXPIRING SOON' if days_remaining <= 7 else 'WARNING'
                            expiring_items.append({
                                'type': 'Bus Document',
                                'item': f"Bus {bus['bus_number']}",
                                'document': doc_name,
                                'expiry_date': expiry,
                                'days_remaining': days_remaining,
                                'status': status
                            })
                    except:
                        pass
    except Exception as e:
        pass
    
    # Check driver licenses
    try:
        drivers_query = """
            SELECT name, license_number, license_expiry
            FROM drivers
            WHERE status = 'Active' AND license_expiry IS NOT NULL
        """
        drivers_df = pd.read_sql_query(drivers_query, conn)
        
        for _, driver in drivers_df.iterrows():
            try:
                expiry = datetime.strptime(driver['license_expiry'], '%Y-%m-%d').date()
                days_remaining = (expiry - today).days
                
                if days_remaining <= days_threshold:
                    status = 'EXPIRED' if days_remaining < 0 else 'EXPIRING SOON' if days_remaining <= 7 else 'WARNING'
                    expiring_items.append({
                        'type': 'Driver License',
                        'item': driver['name'],
                        'document': 'Driving License',
                        'expiry_date': expiry,
                        'days_remaining': days_remaining,
                        'status': status
                    })
            except:
                pass
    except Exception as e:
        pass
    
    conn.close()
    return expiring_items


def show_expiry_alerts():
    """Show expiry alerts on dashboard/home page"""
    expiring = get_expiring_documents(30)
    
    if not expiring:
        return
    
    # Separate by urgency
    expired = [x for x in expiring if x['days_remaining'] < 0]
    critical = [x for x in expiring if 0 <= x['days_remaining'] <= 7]
    warning = [x for x in expiring if 7 < x['days_remaining'] <= 30]
    
    if expired:
        st.error(f"🚨 **URGENT: {len(expired)} EXPIRED DOCUMENTS!**")
        with st.expander("⚠️ View Expired Documents", expanded=True):
            for item in expired:
                st.error(f"❌ **{item['item']}** - {item['document']} expired {abs(item['days_remaining'])} days ago (Expired: {item['expiry_date']})")
    
    if critical:
        st.warning(f"⚠️ **CRITICAL: {len(critical)} Documents Expiring Within 7 Days!**")
        with st.expander("📋 View Critical Documents", expanded=True):
            for item in critical:
                st.warning(f"⏰ **{item['item']}** - {item['document']} expires in {item['days_remaining']} days (Expiry: {item['expiry_date']})")
    
    if warning:
        st.info(f"📢 **NOTICE: {len(warning)} Documents Expiring Within 30 Days**")
        with st.expander("📅 View Upcoming Expirations"):
            for item in warning:
                st.info(f"📅 **{item['item']}** - {item['document']} expires in {item['days_remaining']} days (Expiry: {item['expiry_date']})")


def fleet_management_page():
    """Main Fleet Management Page"""
    
    st.header("🚌 Fleet Management System")
    st.markdown("Complete management of buses, drivers, and conductors with document tracking")
    st.markdown("---")
    
    # Show expiry alerts at the top
    show_expiry_alerts()
    st.markdown("---")
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚌 Bus Fleet",
        "👨‍✈️ Drivers",
        "👨‍💼 Conductors",
        "📊 Assignments"
    ])
    
    with tab1:
        manage_buses()
    
    with tab2:
        manage_drivers()
    
    with tab3:
        manage_conductors()
    
    with tab4:
        manage_assignments()


def manage_buses():
    """Bus fleet management with insurance tracking"""
    
    st.subheader("🚌 Bus Fleet Management")
    
    # Action selector
    action = st.radio("Select Action:", ["View All Buses", "Add New Bus", "Edit Bus", "View Documents Status"], horizontal=True)
    
    conn = sqlite3.connect('bus_management.db')
    
    if action == "View All Buses":
        try:
            buses_df = pd.read_sql_query("SELECT * FROM buses ORDER BY bus_number", conn)
            
            if buses_df.empty:
                st.info("No buses found. Add your first bus!")
            else:
                st.dataframe(buses_df, use_container_width=True, height=400)
                
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Buses", len(buses_df))
                with col2:
                    active = len(buses_df[buses_df['status'] == 'Active'])
                    st.metric("Active Buses", active)
                with col3:
                    inactive = len(buses_df[buses_df['status'] != 'Active'])
                    st.metric("Inactive Buses", inactive)
                with col4:
                    expiring = len(get_expiring_documents(30))
                    st.metric("⚠️ Expiring Docs", expiring)
        except Exception as e:
            st.error(f"Error loading buses: {e}")
    
    elif action == "Add New Bus":
        st.markdown("### Add New Bus")
        
        with st.form("add_bus_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                bus_number = st.text_input("Bus Number *", placeholder="e.g., BUS001")
                registration = st.text_input("Registration Number", placeholder="e.g., ABC-1234")
                make = st.text_input("Make", placeholder="e.g., Mercedes")
                model = st.text_input("Model", placeholder="e.g., Sprinter")
                year = st.number_input("Year", min_value=1990, max_value=datetime.now().year + 1, value=2020)
                capacity = st.number_input("Passenger Capacity", min_value=1, max_value=100, value=50)
                status = st.selectbox("Status", ["Active", "Maintenance", "Inactive"])
            
            with col2:
                st.markdown("**📋 Document Expiry Dates**")
                zinara_expiry = st.date_input("ZINARA Licence Expiry")
                vehicle_insurance = st.date_input("Vehicle Insurance Expiry")
                passenger_insurance = st.date_input("Passenger Insurance Expiry")
                fitness_expiry = st.date_input("Bus Fitness Expiry")
                route_permit = st.date_input("Route Authority Permit Expiry")
                
                purchase_date = st.date_input("Purchase Date", value=datetime.now())
                purchase_cost = st.number_input("Purchase Cost ($)", min_value=0.0, value=0.0, step=1000.0)
            
            submitted = st.form_submit_button("➕ Add Bus", use_container_width=True)
            
            if submitted:
                if not bus_number:
                    st.error("Bus number is required!")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO buses (
                                bus_number, registration_number, make, model, year, capacity,
                                status, purchase_date, purchase_cost,
                                zinara_licence_expiry, vehicle_insurance_expiry,
                                passenger_insurance_expiry, fitness_expiry, route_permit_expiry
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            bus_number, registration, make, model, year, capacity,
                            status, purchase_date, purchase_cost,
                            zinara_expiry, vehicle_insurance, passenger_insurance,
                            fitness_expiry, route_permit
                        ))
                        conn.commit()
                        st.success(f"✅ Bus {bus_number} added successfully!")
                        
                        AuditLogger.log_action("Create", "Fleet Management", f"Added new bus: {bus_number}")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"Bus number {bus_number} already exists!")
                    except Exception as e:
                        st.error(f"Error adding bus: {e}")
    
    elif action == "Edit Bus":
        try:
            buses_df = pd.read_sql_query("SELECT bus_number FROM buses ORDER BY bus_number", conn)
            
            if buses_df.empty:
                st.info("No buses to edit. Add a bus first!")
            else:
                selected_bus = st.selectbox("Select Bus to Edit", buses_df['bus_number'].tolist())
                
                if selected_bus:
                    bus_data = pd.read_sql_query(f"SELECT * FROM buses WHERE bus_number = ?", conn, params=[selected_bus])
                    bus = bus_data.iloc[0]
                    
                    with st.form("edit_bus_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_bus_number = st.text_input("Bus Number", value=bus['bus_number'])
                            registration = st.text_input("Registration Number", value=bus.get('registration_number', ''))
                            make = st.text_input("Make", value=bus.get('make', ''))
                            model = st.text_input("Model", value=bus.get('model', ''))
                            year = st.number_input("Year", min_value=1990, max_value=datetime.now().year + 1, value=int(bus.get('year', 2020)))
                            capacity = st.number_input("Passenger Capacity", min_value=1, max_value=100, value=int(bus.get('capacity', 50)))
                            status = st.selectbox("Status", ["Active", "Maintenance", "Inactive"], index=["Active", "Maintenance", "Inactive"].index(bus.get('status', 'Active')))
                        
                        with col2:
                            st.markdown("**📋 Document Expiry Dates**")
                            
                            def parse_date(date_str):
                                if date_str and date_str != '':
                                    try:
                                        return datetime.strptime(str(date_str), '%Y-%m-%d').date()
                                    except:
                                        pass
                                return datetime.now().date()
                            
                            zinara_expiry = st.date_input("ZINARA Licence Expiry", value=parse_date(bus.get('zinara_licence_expiry')))
                            vehicle_insurance = st.date_input("Vehicle Insurance Expiry", value=parse_date(bus.get('vehicle_insurance_expiry')))
                            passenger_insurance = st.date_input("Passenger Insurance Expiry", value=parse_date(bus.get('passenger_insurance_expiry')))
                            fitness_expiry = st.date_input("Bus Fitness Expiry", value=parse_date(bus.get('fitness_expiry')))
                            route_permit = st.date_input("Route Authority Permit Expiry", value=parse_date(bus.get('route_permit_expiry')))
                        
                        submitted = st.form_submit_button("💾 Update Bus", use_container_width=True)
                        
                        if submitted:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE buses SET
                                        bus_number = ?, registration_number = ?, make = ?, model = ?,
                                        year = ?, capacity = ?, status = ?,
                                        zinara_licence_expiry = ?, vehicle_insurance_expiry = ?,
                                        passenger_insurance_expiry = ?, fitness_expiry = ?, route_permit_expiry = ?,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE bus_number = ?
                                """, (
                                    new_bus_number, registration, make, model, year, capacity, status,
                                    zinara_expiry, vehicle_insurance, passenger_insurance,
                                    fitness_expiry, route_permit, selected_bus
                                ))
                                conn.commit()
                                st.success(f"✅ Bus {selected_bus} updated successfully!")
                                
                                AuditLogger.log_action("Update", "Fleet Management", f"Updated bus: {selected_bus}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating bus: {e}")
        except Exception as e:
            st.error(f"Error: {e}")
    
    elif action == "View Documents Status":
        st.subheader("📋 Document Expiry Status")
        
        expiring = get_expiring_documents(90)  # Show 90 days
        
        if not expiring:
            st.success("✅ All documents are up to date!")
        else:
            # Create DataFrame
            df = pd.DataFrame(expiring)
            df = df.sort_values('days_remaining')
            
            # Color coding
            def status_color(row):
                if row['days_remaining'] < 0:
                    return '🔴 EXPIRED'
                elif row['days_remaining'] <= 7:
                    return '🟠 CRITICAL'
                elif row['days_remaining'] <= 30:
                    return '🟡 WARNING'
                else:
                    return '🟢 OK'
            
            df['Status'] = df.apply(status_color, axis=1)
            
            st.dataframe(df[['Status', 'item', 'document', 'expiry_date', 'days_remaining']], use_container_width=True, height=400)
            
            # Statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                expired = len([x for x in expiring if x['days_remaining'] < 0])
                st.metric("🔴 Expired", expired)
            with col2:
                critical = len([x for x in expiring if 0 <= x['days_remaining'] <= 7])
                st.metric("🟠 Critical (7 days)", critical)
            with col3:
                warning = len([x for x in expiring if 7 < x['days_remaining'] <= 30])
                st.metric("🟡 Warning (30 days)", warning)
            with col4:
                ok = len([x for x in expiring if x['days_remaining'] > 30])
                st.metric("🟢 OK (90 days)", ok)
    
    conn.close()


def manage_drivers():
    """Driver management"""
    
    st.subheader("👨‍✈️ Driver Management")
    
    action = st.radio("Select Action:", ["View All Drivers", "Add New Driver", "Edit Driver"], horizontal=True)
    
    conn = sqlite3.connect('bus_management.db')
    
    if action == "View All Drivers":
        try:
            drivers_df = pd.read_sql_query("SELECT * FROM drivers ORDER BY name", conn)
            
            if drivers_df.empty:
                st.info("No drivers found. Add your first driver!")
            else:
                st.dataframe(drivers_df, use_container_width=True, height=400)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Drivers", len(drivers_df))
                with col2:
                    active = len(drivers_df[drivers_df['status'] == 'Active'])
                    st.metric("Active Drivers", active)
        except Exception as e:
            st.error(f"Error loading drivers: {e}")
    
    elif action == "Add New Driver":
        st.markdown("### Add New Driver")
        
        with st.form("add_driver_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name *", placeholder="e.g., John Doe")
                employee_id = st.text_input("Employee ID", placeholder="e.g., DRV001")
                license_number = st.text_input("License Number *", placeholder="e.g., 123456")
                license_expiry = st.date_input("License Expiry Date")
                phone = st.text_input("Phone Number", placeholder="e.g., +263771234567")
            
            with col2:
                email = st.text_input("Email", placeholder="driver@example.com")
                address = st.text_area("Address", placeholder="Enter address")
                dob = st.date_input("Date of Birth", value=datetime(1990, 1, 1))
                hire_date = st.date_input("Hire Date", value=datetime.now())
                salary = st.number_input("Monthly Salary ($)", min_value=0.0, value=0.0, step=50.0)
                commission = st.number_input("Commission Rate (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                status = st.selectbox("Status", ["Active", "On Leave", "Inactive"])
            
            submitted = st.form_submit_button("➕ Add Driver", use_container_width=True)
            
            if submitted:
                if not name:
                    st.error("Driver name is required!")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO drivers (
                                employee_id, name, license_number, license_expiry,
                                phone, email, address, date_of_birth, hire_date,
                                salary, commission_rate, status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            employee_id, name, license_number, license_expiry,
                            phone, email, address, dob, hire_date,
                            salary, commission, status
                        ))
                        conn.commit()
                        st.success(f"✅ Driver {name} added successfully!")
                        
                        AuditLogger.log_action("Create", "Fleet Management", f"Added new driver: {name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding driver: {e}")
    
    elif action == "Edit Driver":
        try:
            drivers_df = pd.read_sql_query("SELECT id, name FROM drivers ORDER BY name", conn)
            
            if drivers_df.empty:
                st.info("No drivers to edit. Add a driver first!")
            else:
                driver_options = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in drivers_df.iterrows()}
                selected_driver = st.selectbox("Select Driver to Edit", list(driver_options.keys()))
                
                if selected_driver:
                    driver_id = driver_options[selected_driver]
                    driver_data = pd.read_sql_query(f"SELECT * FROM drivers WHERE id = ?", conn, params=[driver_id])
                    driver = driver_data.iloc[0]
                    
                    with st.form("edit_driver_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            name = st.text_input("Full Name", value=driver['name'])
                            employee_id = st.text_input("Employee ID", value=driver.get('employee_id', ''))
                            license_number = st.text_input("License Number", value=driver.get('license_number', ''))
                            
                            def parse_date(date_str):
                                if date_str and date_str != '':
                                    try:
                                        return datetime.strptime(str(date_str), '%Y-%m-%d').date()
                                    except:
                                        pass
                                return datetime.now().date()
                            
                            license_expiry = st.date_input("License Expiry", value=parse_date(driver.get('license_expiry')))
                            phone = st.text_input("Phone", value=driver.get('phone', ''))
                        
                        with col2:
                            email = st.text_input("Email", value=driver.get('email', ''))
                            address = st.text_area("Address", value=driver.get('address', ''))
                            
                            # Safe float conversion
                            salary_value = driver.get('salary', 0)
                            salary = st.number_input("Monthly Salary ($)", value=float(salary_value) if salary_value else 0.0)
                            
                            commission_value = driver.get('commission_rate', 0)
                            commission = st.number_input("Commission Rate (%)", value=float(commission_value) if commission_value else 0.0)
                            
                            status = st.selectbox("Status", ["Active", "On Leave", "Inactive"], 
                                                index=["Active", "On Leave", "Inactive"].index(driver.get('status', 'Active')) if driver.get('status') in ["Active", "On Leave", "Inactive"] else 0)
                        
                        submitted = st.form_submit_button("💾 Update Driver", use_container_width=True)
                        
                        if submitted:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE drivers SET
                                        name = ?, employee_id = ?, license_number = ?, license_expiry = ?,
                                        phone = ?, email = ?, address = ?, salary = ?,
                                        commission_rate = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                """, (name, employee_id, license_number, license_expiry,
                                     phone, email, address, salary, commission, status, driver_id))
                                conn.commit()
                                st.success(f"✅ Driver {name} updated successfully!")
                                
                                AuditLogger.log_action("Update", "Fleet Management", f"Updated driver: {name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating driver: {e}")
        except Exception as e:
            st.error(f"Error: {e}")
    
    conn.close()


def manage_conductors():
    """Conductor management (similar to drivers)"""
    
    st.subheader("👨‍💼 Conductor Management")
    
    action = st.radio("Select Action:", ["View All Conductors", "Add New Conductor", "Edit Conductor"], horizontal=True, key="conductor_action")
    
    conn = sqlite3.connect('bus_management.db')
    
    if action == "View All Conductors":
        try:
            conductors_df = pd.read_sql_query("SELECT * FROM conductors ORDER BY name", conn)
            
            if conductors_df.empty:
                st.info("No conductors found. Add your first conductor!")
            else:
                st.dataframe(conductors_df, use_container_width=True, height=400)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Conductors", len(conductors_df))
                with col2:
                    active = len(conductors_df[conductors_df['status'] == 'Active'])
                    st.metric("Active Conductors", active)
        except Exception as e:
            st.error(f"Error loading conductors: {e}")
    
    elif action == "Add New Conductor":
        st.markdown("### Add New Conductor")
        
        with st.form("add_conductor_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name *", placeholder="e.g., Jane Doe")
                employee_id = st.text_input("Employee ID", placeholder="e.g., CND001")
                phone = st.text_input("Phone Number", placeholder="e.g., +263771234567")
                email = st.text_input("Email", placeholder="conductor@example.com")
            
            with col2:
                address = st.text_area("Address", placeholder="Enter address")
                dob = st.date_input("Date of Birth", value=datetime(1990, 1, 1))
                hire_date = st.date_input("Hire Date", value=datetime.now())
                salary = st.number_input("Monthly Salary ($)", min_value=0.0, value=0.0, step=50.0)
                commission = st.number_input("Commission Rate (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                status = st.selectbox("Status", ["Active", "On Leave", "Inactive"], key="add_cond_status")
            
            submitted = st.form_submit_button("➕ Add Conductor", use_container_width=True)
            
            if submitted:
                if not name:
                    st.error("Conductor name is required!")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO conductors (
                                employee_id, name, phone, email, address,
                                date_of_birth, hire_date, salary, commission_rate, status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            employee_id, name, phone, email, address,
                            dob, hire_date, salary, commission, status
                        ))
                        conn.commit()
                        st.success(f"✅ Conductor {name} added successfully!")
                        
                        AuditLogger.log_action("Create", "Fleet Management", f"Added new conductor: {name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding conductor: {e}")
    
    elif action == "Edit Conductor":
        try:
            conductors_df = pd.read_sql_query("SELECT id, name FROM conductors ORDER BY name", conn)
            
            if conductors_df.empty:
                st.info("No conductors to edit. Add a conductor first!")
            else:
                conductor_options = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in conductors_df.iterrows()}
                selected_conductor = st.selectbox("Select Conductor to Edit", list(conductor_options.keys()))
                
                if selected_conductor:
                    conductor_id = conductor_options[selected_conductor]
                    conductor_data = pd.read_sql_query(f"SELECT * FROM conductors WHERE id = ?", conn, params=[conductor_id])
                    conductor = conductor_data.iloc[0]
                    
                    with st.form("edit_conductor_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            name = st.text_input("Full Name", value=conductor['name'])
                            employee_id = st.text_input("Employee ID", value=conductor.get('employee_id', ''))
                            phone = st.text_input("Phone", value=conductor.get('phone', ''))
                            email = st.text_input("Email", value=conductor.get('email', ''))
                        
                        with col2:
                            address = st.text_area("Address", value=conductor.get('address', ''))
                            
                            # Safe float conversion
                            salary_value = conductor.get('salary', 0)
                            salary = st.number_input("Monthly Salary ($)", value=float(salary_value) if salary_value else 0.0)
                            
                            commission_value = conductor.get('commission_rate', 0)
                            commission = st.number_input("Commission Rate (%)", value=float(commission_value) if commission_value else 0.0)
                            
                            status = st.selectbox("Status", ["Active", "On Leave", "Inactive"], 
                                                index=["Active", "On Leave", "Inactive"].index(conductor.get('status', 'Active')) if conductor.get('status') in ["Active", "On Leave", "Inactive"] else 0,
                                                key="edit_cond_status")
                        
                        submitted = st.form_submit_button("💾 Update Conductor", use_container_width=True)
                        
                        if submitted:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE conductors SET
                                        name = ?, employee_id = ?, phone = ?, email = ?,
                                        address = ?, salary = ?, commission_rate = ?,
                                        status = ?, updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                """, (name, employee_id, phone, email, address,
                                     salary, commission, status, conductor_id))
                                conn.commit()
                                st.success(f"✅ Conductor {name} updated successfully!")
                                
                                AuditLogger.log_action("Update", "Fleet Management", f"Updated conductor: {name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating conductor: {e}")
        except Exception as e:
            st.error(f"Error: {e}")
    
    conn.close()


def manage_assignments():
    """Manage driver and conductor assignments to buses"""
    
    st.subheader("📊 Driver & Conductor Assignments")
    st.markdown("*Note: Assignments are flexible - drivers and conductors can be assigned to different buses at any time*")
    
    conn = sqlite3.connect('bus_management.db')
    
    # Create assignments table if it doesn't exist
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bus_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT NOT NULL,
            driver_id INTEGER,
            conductor_id INTEGER,
            assignment_date DATE NOT NULL,
            shift TEXT,
            route TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (driver_id) REFERENCES drivers(id),
            FOREIGN KEY (conductor_id) REFERENCES conductors(id)
        )
    """)
    conn.commit()
    
    action = st.radio("Select Action:", ["View Current Assignments", "Create New Assignment", "Assignment History"], horizontal=True, key="assign_action")
    
    if action == "View Current Assignments":
        st.markdown("### 📋 Current Day Assignments")
        
        today = datetime.now().date()
        
        try:
            query = """
                SELECT 
                    ba.id,
                    ba.bus_number,
                    d.name as driver_name,
                    c.name as conductor_name,
                    ba.assignment_date,
                    ba.shift,
                    ba.route,
                    ba.notes
                FROM bus_assignments ba
                LEFT JOIN drivers d ON ba.driver_id = d.id
                LEFT JOIN conductors c ON ba.conductor_id = c.id
                WHERE ba.assignment_date = ?
                ORDER BY ba.bus_number
            """
            
            assignments_df = pd.read_sql_query(query, conn, params=[today])
            
            if assignments_df.empty:
                st.info("No assignments for today. Create new assignments below.")
            else:
                st.dataframe(assignments_df, use_container_width=True, height=400)
                
                # Summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Buses Assigned", assignments_df['bus_number'].nunique())
                with col2:
                    st.metric("Drivers on Duty", assignments_df['driver_name'].nunique())
                with col3:
                    st.metric("Conductors on Duty", assignments_df['conductor_name'].nunique())
                
                # Delete assignment option
                st.markdown("---")
                assignment_to_delete = st.selectbox(
                    "Remove Assignment:",
                    ["Select to remove..."] + [f"Bus {row['bus_number']} - {row['driver_name']} & {row['conductor_name']}" 
                                                for _, row in assignments_df.iterrows()]
                )
                
                if assignment_to_delete != "Select to remove...":
                    if st.button("🗑️ Remove Selected Assignment", type="secondary"):
                        try:
                            assignment_id = assignments_df.iloc[assignments_df.index[assignment_to_delete.split(" - ")[0].replace("Bus ", "") == assignments_df['bus_number']][0]]['id']
                            cursor.execute("DELETE FROM bus_assignments WHERE id = ?", (assignment_id,))
                            conn.commit()
                            st.success("✅ Assignment removed!")
                            AuditLogger.log_action("Delete", "Fleet Management", f"Removed assignment: {assignment_to_delete}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error removing assignment: {e}")
        
        except Exception as e:
            st.error(f"Error loading assignments: {e}")
    
    elif action == "Create New Assignment":
        st.markdown("### ➕ Create New Assignment")
        
        try:
            # Get available buses, drivers, conductors
            buses_df = pd.read_sql_query("SELECT bus_number FROM buses WHERE status = 'Active' ORDER BY bus_number", conn)
            drivers_df = pd.read_sql_query("SELECT id, name FROM drivers WHERE status = 'Active' ORDER BY name", conn)
            conductors_df = pd.read_sql_query("SELECT id, name FROM conductors WHERE status = 'Active' ORDER BY name", conn)
            
            if buses_df.empty:
                st.warning("No active buses available. Add buses first.")
            elif drivers_df.empty:
                st.warning("No active drivers available. Add drivers first.")
            elif conductors_df.empty:
                st.warning("No active conductors available. Add conductors first.")
            else:
                with st.form("assignment_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        bus_number = st.selectbox("🚌 Select Bus", buses_df['bus_number'].tolist())
                        driver_dict = {row['name']: row['id'] for _, row in drivers_df.iterrows()}
                        selected_driver = st.selectbox("👨‍✈️ Select Driver", list(driver_dict.keys()))
                        conductor_dict = {row['name']: row['id'] for _, row in conductors_df.iterrows()}
                        selected_conductor = st.selectbox("👨‍💼 Select Conductor", list(conductor_dict.keys()))
                    
                    with col2:
                        assignment_date = st.date_input("📅 Assignment Date", value=datetime.now())
                        shift = st.selectbox("⏰ Shift", ["Morning", "Afternoon", "Evening", "Night", "Full Day"])
                        route = st.text_input("🛣️ Route", placeholder="e.g., City Center - Airport")
                        notes = st.text_area("📝 Notes", placeholder="Any special instructions or notes")
                    
                    submitted = st.form_submit_button("✅ Create Assignment", use_container_width=True)
                    
                    if submitted:
                        try:
                            driver_id = driver_dict[selected_driver]
                            conductor_id = conductor_dict[selected_conductor]
                            
                            cursor.execute("""
                                INSERT INTO bus_assignments (
                                    bus_number, driver_id, conductor_id,
                                    assignment_date, shift, route, notes
                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (bus_number, driver_id, conductor_id, assignment_date, shift, route, notes))
                            
                            conn.commit()
                            st.success(f"✅ Assignment created: Bus {bus_number} → {selected_driver} & {selected_conductor}")
                            
                            AuditLogger.log_action("Create", "Fleet Management", 
                                                 f"Created assignment: Bus {bus_number} - {selected_driver} & {selected_conductor} on {assignment_date}")
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"Error creating assignment: {e}")
        
        except Exception as e:
            st.error(f"Error: {e}")
    
    elif action == "Assignment History":
        st.markdown("### 📜 Assignment History")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From Date", value=datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("To Date", value=datetime.now())
        
        try:
            query = """
                SELECT 
                    ba.bus_number,
                    d.name as driver_name,
                    c.name as conductor_name,
                    ba.assignment_date,
                    ba.shift,
                    ba.route,
                    ba.notes
                FROM bus_assignments ba
                LEFT JOIN drivers d ON ba.driver_id = d.id
                LEFT JOIN conductors c ON ba.conductor_id = c.id
                WHERE ba.assignment_date BETWEEN ? AND ?
                ORDER BY ba.assignment_date DESC, ba.bus_number
            """
            
            history_df = pd.read_sql_query(query, conn, params=[start_date, end_date])
            
            if history_df.empty:
                st.info("No assignment history found for the selected period.")
            else:
                st.dataframe(history_df, use_container_width=True, height=400)
                
                # Statistics
                st.markdown("---")
                st.subheader("📊 Assignment Statistics")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Assignments", len(history_df))
                with col2:
                    st.metric("Unique Buses", history_df['bus_number'].nunique())
                with col3:
                    st.metric("Unique Drivers", history_df['driver_name'].nunique())
                with col4:
                    st.metric("Unique Conductors", history_df['conductor_name'].nunique())
                
                # Most active
                st.markdown("---")
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.markdown("**🚌 Most Active Buses**")
                    bus_counts = history_df['bus_number'].value_counts().head(5)
                    st.dataframe(bus_counts.reset_index(), use_container_width=True)
                
                with col_b:
                    st.markdown("**👨‍✈️ Most Active Drivers**")
                    driver_counts = history_df['driver_name'].value_counts().head(5)
                    st.dataframe(driver_counts.reset_index(), use_container_width=True)
                
                with col_c:
                    st.markdown("**👨‍💼 Most Active Conductors**")
                    conductor_counts = history_df['conductor_name'].value_counts().head(5)
                    st.dataframe(conductor_counts.reset_index(), use_container_width=True)
                
                # Export option
                st.markdown("---")
                csv_data = history_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Assignment History (CSV)",
                    data=csv_data,
                    file_name=f"assignment_history_{start_date}_to_{end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        except Exception as e:
            st.error(f"Error loading history: {e}")
    
    conn.close()