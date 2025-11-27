"""
fleet_management_page.py - Fleet Management System (BUSES ONLY)
Drivers and Conductors are managed in HR > Employee Management
"""

import streamlit as st
import pandas as pd
from database import get_connection, USE_POSTGRES
from datetime import datetime, timedelta
from audit_logger import AuditLogger

def get_bus_display_name(bus_number, conn=None):
    """Get formatted bus display name with registration number"""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    
    try:
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute("""
                SELECT registration_number, model 
                FROM buses 
                WHERE bus_number = %s
            """, (bus_number,))
        else:
            cursor.execute("""
                SELECT registration_number, model 
                FROM buses 
                WHERE bus_number = ?
            """, (bus_number,))
        result = cursor.fetchone()
        
        if result and result[0]:
            return f"{result[0]} - {bus_number} ({result[1]})"
        elif result:
            return f"{bus_number} ({result[1]})"
        else:
            return bus_number
    finally:
        if should_close:
            conn.close()


def get_expiring_documents(days_threshold=30):
    """Get all bus documents expiring within the threshold"""
    conn = get_connection()
    
    expiring_items = []
    today = datetime.now().date()
    threshold_date = today + timedelta(days=days_threshold)
    
    # Check buses only
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
    """Main Fleet Management Page - BUSES ONLY"""
    
    st.header("🚌 Fleet Management System")
    st.markdown("Complete management of bus fleet with document tracking")
    st.info("💡 **Note:** Drivers and Conductors are managed in **HR > Employee Management**")
    st.markdown("---")
    
    # Show expiry alerts at the top
    show_expiry_alerts()
    st.markdown("---")
    
    # Only Bus Fleet Management
    manage_buses()


def manage_buses():
    """Bus fleet management with insurance tracking"""
    
    st.subheader("🚌 Bus Fleet Management")
    
    # Action selector
    action = st.radio("Select Action:", ["View All Buses", "Add New Bus", "Edit Bus", "View Documents Status"], horizontal=True)
    
    conn = get_connection()
    
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
                    except Exception as e:
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