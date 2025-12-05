"""
fleet_management_page.py - Fleet Management System (BUSES ONLY)
Drivers and Conductors are managed in HR > Employee Management
"""

import streamlit as st
import pandas as pd
from database import get_connection, get_engine, USE_POSTGRES
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
        buses_df = pd.read_sql_query(buses_query, get_engine())
        
        for _, bus in buses_df.iterrows():
            documents = {
                'ZINARA Licence': bus.get('zinara_licence_expiry'),
                'Vehicle Insurance': bus.get('vehicle_insurance_expiry'),
                'Passenger Insurance': bus.get('passenger_insurance_expiry'),
                'Bus Fitness': bus.get('fitness_expiry'),
                'Route Authority Permit': bus.get('route_permit_expiry')
            }
            
            # Use registration_number as primary identifier
            display_name = bus.get('registration_number') or bus['bus_number']
            
            for doc_name, expiry_date in documents.items():
                if expiry_date and expiry_date != '':
                    try:
                        expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
                        days_remaining = (expiry - today).days
                        
                        if days_remaining <= days_threshold:
                            status = 'EXPIRED' if days_remaining < 0 else 'EXPIRING SOON' if days_remaining <= 7 else 'WARNING'
                            expiring_items.append({
                                'type': 'Bus Document',
                                'item': display_name,  # Registration number shown
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
    """Show expiry alerts on dashboard/home page - collapsed by default"""
    expiring = get_expiring_documents(90)  # Get 90 days for full overview
    
    if not expiring:
        return
    
    # Separate by urgency
    expired = [x for x in expiring if x['days_remaining'] < 0]
    critical = [x for x in expiring if 0 <= x['days_remaining'] <= 7]
    warning = [x for x in expiring if 7 < x['days_remaining'] <= 30]
    upcoming = [x for x in expiring if 30 < x['days_remaining'] <= 90]
    
    # Calculate totals for summary
    total_issues = len(expired) + len(critical) + len(warning)
    
    # Create a single collapsible section with summary
    if total_issues > 0:
        # Determine header color based on severity
        if expired:
            header_icon = "🚨"
            header_text = f"Document Alerts: {len(expired)} Expired, {len(critical)} Critical, {len(warning)} Warning"
        elif critical:
            header_icon = "⚠️"
            header_text = f"Document Alerts: {len(critical)} Critical, {len(warning)} Warning"
        else:
            header_icon = "📋"
            header_text = f"Document Alerts: {len(warning)} Expiring Soon"
        
        # Single collapsed expander with all alerts
        with st.expander(f"{header_icon} {header_text}", expanded=False):
            if expired:
                st.markdown("### 🔴 Expired Documents")
                for item in expired:
                    st.error(f"❌ **{item['item']}** - {item['document']} expired {abs(item['days_remaining'])} days ago")
                st.markdown("---")
            
            if critical:
                st.markdown("### 🟠 Critical (Within 7 Days)")
                for item in critical:
                    st.warning(f"⏰ **{item['item']}** - {item['document']} expires in {item['days_remaining']} days")
                st.markdown("---")
            
            if warning:
                st.markdown("### 🟡 Warning (Within 30 Days)")
                for item in warning:
                    st.info(f"📅 **{item['item']}** - {item['document']} expires in {item['days_remaining']} days")
            
            if upcoming:
                st.markdown("---")
                st.markdown("### 🟢 Upcoming (30-90 Days)")
                for item in upcoming:
                    st.write(f"📆 **{item['item']}** - {item['document']} expires in {item['days_remaining']} days")
    else:
        # Just show upcoming if no urgent issues
        if upcoming:
            with st.expander(f"📋 Document Status: {len(upcoming)} upcoming renewals", expanded=False):
                for item in upcoming:
                    st.write(f"📆 **{item['item']}** - {item['document']} expires in {item['days_remaining']} days")


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
    action = st.radio("Select Action:", ["View All Buses", "Add New Bus", "Edit Bus", "Delete Bus", "View Documents Status", "💰 Insurance & Renewals"], horizontal=True)
    
    conn = get_connection()
    
    if action == "View All Buses":
        try:
            buses_df = pd.read_sql_query("SELECT * FROM buses ORDER BY bus_number", get_engine())
            
            if buses_df.empty:
                st.info("No buses found. Add your first bus!")
            else:
                st.dataframe(buses_df, width="stretch", height=400)
                
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
        
        # Auto-generate bus number
        cursor = conn.cursor()
        if USE_POSTGRES:
            cursor.execute("SELECT bus_number FROM buses WHERE bus_number LIKE 'BUS%' ORDER BY bus_number DESC LIMIT 1")
        else:
            cursor.execute("SELECT bus_number FROM buses WHERE bus_number LIKE 'BUS%' ORDER BY bus_number DESC LIMIT 1")
        
        result = cursor.fetchone()
        if result:
            last_num = result['bus_number'] if hasattr(result, 'keys') else result[0]
            try:
                # Extract number from BUS001, BUS002, etc.
                num = int(last_num.replace('BUS', ''))
                next_bus_number = f"BUS{num + 1:03d}"
            except:
                next_bus_number = "BUS001"
        else:
            next_bus_number = "BUS001"
        
        st.info(f"🔢 Next Bus Number: **{next_bus_number}** (auto-generated)")
        
        with st.form("add_bus_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Show auto-generated bus number (read-only display)
                st.text_input("Bus Number (Auto-generated)", value=next_bus_number, disabled=True)
                registration = st.text_input("Registration Number *", placeholder="e.g., ABC-1234")
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
            
            submitted = st.form_submit_button("➕ Add Bus", width="stretch")
            
            if submitted:
                if not registration:
                    st.error("Registration number is required!")
                else:
                    try:
                        cursor = conn.cursor()
                        if USE_POSTGRES:
                            cursor.execute("""
                                INSERT INTO buses (
                                    bus_number, registration_number, make, model, year, capacity,
                                    status, purchase_date, purchase_cost,
                                    zinara_licence_expiry, vehicle_insurance_expiry,
                                    passenger_insurance_expiry, fitness_expiry, route_permit_expiry
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                next_bus_number, registration, make, model, year, capacity,
                                status, purchase_date, purchase_cost,
                                zinara_expiry, vehicle_insurance, passenger_insurance,
                                fitness_expiry, route_permit
                            ))
                        else:
                            cursor.execute("""
                                INSERT INTO buses (
                                    bus_number, registration_number, make, model, year, capacity,
                                    status, purchase_date, purchase_cost,
                                    zinara_licence_expiry, vehicle_insurance_expiry,
                                    passenger_insurance_expiry, fitness_expiry, route_permit_expiry
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                next_bus_number, registration, make, model, year, capacity,
                                status, purchase_date, purchase_cost,
                                zinara_expiry, vehicle_insurance, passenger_insurance,
                                fitness_expiry, route_permit
                            ))
                        conn.commit()
                        st.success(f"✅ Bus {next_bus_number} added successfully!")
                        
                        AuditLogger.log_action("Create", "Fleet Management", f"Added new bus: {next_bus_number}")
                        st.rerun()
                    except Exception as e:
                        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                            st.error(f"Bus number {next_bus_number} already exists!")
                        else:
                            st.error(f"Error adding bus: {e}")
    
    elif action == "Edit Bus":
        try:
            buses_df = pd.read_sql_query("SELECT bus_number FROM buses ORDER BY bus_number", get_engine())
            
            if buses_df.empty:
                st.info("No buses to edit. Add a bus first!")
            else:
                selected_bus = st.selectbox("Select Bus to Edit", buses_df['bus_number'].tolist())
                
                if selected_bus:
                    ph = '%s' if USE_POSTGRES else '?'
                    bus_data = pd.read_sql_query(f"SELECT * FROM buses WHERE bus_number = {ph}", get_engine(), params=(selected_bus,))
                    bus = bus_data.iloc[0]
                    
                    with st.form("edit_bus_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_bus_number = st.text_input("Bus Number", value=bus['bus_number'])
                            registration = st.text_input("Registration Number", value=bus.get('registration_number', '') or '')
                            make = st.text_input("Make", value=bus.get('make', '') or '')
                            model = st.text_input("Model", value=bus.get('model', '') or '')
                            year = st.number_input("Year", min_value=1990, max_value=datetime.now().year + 1, value=int(bus.get('year', 2020) or 2020))
                            capacity = st.number_input("Passenger Capacity", min_value=1, max_value=100, value=int(bus.get('capacity', 50) or 50))
                            status = st.selectbox("Status", ["Active", "Maintenance", "Inactive"], index=["Active", "Maintenance", "Inactive"].index(bus.get('status', 'Active') or 'Active'))
                        
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
                        
                        submitted = st.form_submit_button("💾 Update Bus", width="stretch")
                        
                        if submitted:
                            try:
                                cursor = conn.cursor()
                                if USE_POSTGRES:
                                    cursor.execute("""
                                        UPDATE buses SET
                                            bus_number = %s, registration_number = %s, make = %s, model = %s,
                                            year = %s, capacity = %s, status = %s,
                                            zinara_licence_expiry = %s, vehicle_insurance_expiry = %s,
                                            passenger_insurance_expiry = %s, fitness_expiry = %s, route_permit_expiry = %s,
                                            updated_at = CURRENT_TIMESTAMP
                                        WHERE bus_number = %s
                                    """, (
                                        new_bus_number, registration, make, model, year, capacity, status,
                                        zinara_expiry, vehicle_insurance, passenger_insurance,
                                        fitness_expiry, route_permit, selected_bus
                                    ))
                                else:
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
    
    elif action == "Delete Bus":
        st.subheader("🗑️ Delete Bus")
        st.warning("⚠️ **Warning:** Deleting a bus will remove the bus record. Income and maintenance records associated with this bus will NOT be deleted but will no longer be linked to an active bus.")
        
        try:
            buses_df = pd.read_sql_query("""
                SELECT bus_number, registration_number, make, model, status 
                FROM buses 
                ORDER BY bus_number
            """, get_engine())
            
            if buses_df.empty:
                st.info("No buses to delete.")
            else:
                # Show bus list with details
                st.markdown("### Select Bus to Delete")
                
                # Create display options
                bus_options = []
                for _, bus in buses_df.iterrows():
                    reg = bus['registration_number'] or 'No Reg'
                    model = bus['model'] or 'Unknown'
                    status = bus['status'] or 'Unknown'
                    bus_options.append(f"{reg} - {bus['bus_number']} ({model}) - {status}")
                
                selected_option = st.selectbox("Select Bus", bus_options)
                
                if selected_option:
                    # Extract bus_number from selection
                    selected_bus = buses_df.iloc[bus_options.index(selected_option)]['bus_number']
                    selected_reg = buses_df.iloc[bus_options.index(selected_option)]['registration_number']
                    
                    # Show bus details
                    st.markdown("---")
                    st.markdown(f"**Selected Bus:** {selected_reg or selected_bus}")
                    
                    # Check for related records
                    ph = '%s' if USE_POSTGRES else '?'
                    
                    # Count income records (using registration number which is stored in bus_number field in income table)
                    income_count_df = pd.read_sql_query(
                        f"SELECT COUNT(*) as count FROM income WHERE bus_number = {ph}", 
                        get_engine(), 
                        params=(selected_reg or selected_bus,)
                    )
                    income_count = income_count_df['count'].iloc[0]
                    
                    # Count maintenance records
                    maint_count_df = pd.read_sql_query(
                        f"SELECT COUNT(*) as count FROM maintenance WHERE bus_number = {ph}", 
                        get_engine(), 
                        params=(selected_reg or selected_bus,)
                    )
                    maint_count = maint_count_df['count'].iloc[0]
                    
                    # Count assignments
                    assign_count_df = pd.read_sql_query(
                        f"SELECT COUNT(*) as count FROM bus_assignments WHERE bus_number = {ph}", 
                        get_engine(), 
                        params=(selected_reg or selected_bus,)
                    )
                    assign_count = assign_count_df['count'].iloc[0]
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📊 Income Records", income_count)
                    with col2:
                        st.metric("🔧 Maintenance Records", maint_count)
                    with col3:
                        st.metric("📋 Assignments", assign_count)
                    
                    st.markdown("---")
                    
                    # Delete options
                    delete_related = st.checkbox(
                        "🗑️ Also delete ALL related records (income, maintenance, assignments)", 
                        value=False,
                        help="If checked, all income, maintenance, and assignment records for this bus will be permanently deleted."
                    )
                    
                    if delete_related:
                        st.error("⚠️ **DANGER:** This will permanently delete ALL income, maintenance, and assignment records for this bus!")
                    
                    # Confirmation
                    confirm_text = st.text_input(
                        f"Type '{selected_reg or selected_bus}' to confirm deletion",
                        placeholder=f"Type: {selected_reg or selected_bus}"
                    )
                    
                    if st.button("🗑️ Delete Bus", type="primary", width="stretch"):
                        if confirm_text == (selected_reg or selected_bus):
                            try:
                                cursor = conn.cursor()
                                
                                if delete_related:
                                    # Delete related records first
                                    if USE_POSTGRES:
                                        cursor.execute("DELETE FROM income WHERE bus_number = %s", (selected_reg or selected_bus,))
                                        cursor.execute("DELETE FROM maintenance WHERE bus_number = %s", (selected_reg or selected_bus,))
                                        cursor.execute("DELETE FROM bus_assignments WHERE bus_number = %s", (selected_reg or selected_bus,))
                                    else:
                                        cursor.execute("DELETE FROM income WHERE bus_number = ?", (selected_reg or selected_bus,))
                                        cursor.execute("DELETE FROM maintenance WHERE bus_number = ?", (selected_reg or selected_bus,))
                                        cursor.execute("DELETE FROM bus_assignments WHERE bus_number = ?", (selected_reg or selected_bus,))
                                    
                                    AuditLogger.log_action(
                                        "Delete", 
                                        "Fleet Management", 
                                        f"Deleted bus {selected_bus} ({selected_reg}) with {income_count} income, {maint_count} maintenance, {assign_count} assignment records"
                                    )
                                else:
                                    AuditLogger.log_action(
                                        "Delete", 
                                        "Fleet Management", 
                                        f"Deleted bus {selected_bus} ({selected_reg}) - related records preserved"
                                    )
                                
                                # Delete the bus
                                if USE_POSTGRES:
                                    cursor.execute("DELETE FROM buses WHERE bus_number = %s", (selected_bus,))
                                else:
                                    cursor.execute("DELETE FROM buses WHERE bus_number = ?", (selected_bus,))
                                
                                conn.commit()
                                st.success(f"✅ Bus {selected_reg or selected_bus} deleted successfully!")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error deleting bus: {e}")
                        else:
                            st.error(f"❌ Please type '{selected_reg or selected_bus}' exactly to confirm deletion")
                            
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
            
            st.dataframe(df[['Status', 'item', 'document', 'expiry_date', 'days_remaining']], width="stretch", height=400)
            
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
    
    elif action == "💰 Insurance & Renewals":
        st.subheader("💰 Insurance & Renewals with Expense Tracking")
        st.markdown("Record insurance renewals and link costs to General Expenses")
        
        st.info("""
        💡 **How it works:** When you record an insurance renewal with a cost, 
        it automatically creates an expense entry in General Expenses for accurate P&L tracking.
        """)
        
        # Get buses
        buses_df = pd.read_sql_query("SELECT * FROM buses WHERE status = 'Active' ORDER BY registration_number", get_engine())
        
        if buses_df.empty:
            st.warning("No active buses found")
        else:
            st.markdown("### 📝 Record Insurance/License Renewal")
            
            with st.form("renewal_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Bus selection
                    bus_options = {
                        f"{row['registration_number']} ({row['make']} {row['model']})": row['bus_number']
                        for _, row in buses_df.iterrows()
                    }
                    selected_bus_display = st.selectbox("Select Bus*", list(bus_options.keys()))
                    selected_bus_number = bus_options[selected_bus_display]
                    
                    # Document type
                    doc_type = st.selectbox("Document Type*", [
                        "ZINARA License",
                        "Vehicle Insurance",
                        "Passenger Insurance",
                        "Fitness Certificate",
                        "Route Authority Permit"
                    ])
                    
                    # Vendor/Provider
                    vendor = st.text_input("Insurance Provider/Vendor", placeholder="e.g., Old Mutual, ZINARA")
                
                with col2:
                    # New expiry date
                    new_expiry = st.date_input("New Expiry Date*", value=datetime.now() + timedelta(days=365))
                    
                    # Cost
                    cost = st.number_input("Cost ($)*", min_value=0.0, step=10.0, format="%.2f")
                    
                    # Payment method
                    payment_method = st.selectbox("Payment Method", [
                        "Bank Transfer", "Cash", "EcoCash", "Cheque", "Other"
                    ])
                
                # Reference/Policy number
                reference = st.text_input("Policy/Reference Number", placeholder="e.g., POL-2024-12345")
                
                # Link to expenses checkbox
                link_to_expenses = st.checkbox("✅ Link to General Expenses (Recommended)", value=True)
                
                notes = st.text_area("Notes", placeholder="Additional details...")
                
                if st.form_submit_button("💾 Save Renewal", type="primary", use_container_width=True):
                    if cost <= 0:
                        st.error("Please enter a valid cost")
                    else:
                        try:
                            cursor = conn.cursor()
                            
                            # Map document type to database column
                            doc_column_map = {
                                "ZINARA License": "zinara_licence_expiry",
                                "Vehicle Insurance": "vehicle_insurance_expiry",
                                "Passenger Insurance": "passenger_insurance_expiry",
                                "Fitness Certificate": "fitness_expiry",
                                "Route Authority Permit": "route_permit_expiry"
                            }
                            
                            column = doc_column_map.get(doc_type)
                            
                            # Update bus document expiry
                            if USE_POSTGRES:
                                cursor.execute(f"""
                                    UPDATE buses SET {column} = %s, updated_at = CURRENT_TIMESTAMP
                                    WHERE bus_number = %s
                                """, (new_expiry, selected_bus_number))
                            else:
                                cursor.execute(f"""
                                    UPDATE buses SET {column} = ?, updated_at = CURRENT_TIMESTAMP
                                    WHERE bus_number = ?
                                """, (str(new_expiry), selected_bus_number))
                            
                            conn.commit()
                            
                            # Link to expenses if checked
                            if link_to_expenses and cost > 0:
                                try:
                                    from pages_expenses import create_linked_expense
                                    
                                    expense_id = create_linked_expense(
                                        expense_date=str(datetime.now().date()),
                                        category="Administrative",
                                        subcategory="Insurance",
                                        description=f"{doc_type} renewal for {selected_bus_display}",
                                        vendor=vendor or "Insurance Provider",
                                        amount=cost,
                                        source_type="bus_insurance",
                                        source_id=f"{selected_bus_number}-{doc_type}-{new_expiry}",
                                        payment_status="Paid",
                                        payment_method=payment_method,
                                        created_by=st.session_state.get('user', {}).get('username', 'system')
                                    )
                                    
                                    if expense_id:
                                        st.success(f"✅ Expense linked! (Expense ID: {expense_id})")
                                except Exception as exp_err:
                                    st.warning(f"Renewal saved but expense linking failed: {exp_err}")
                            
                            AuditLogger.log_action(
                                "Update", "Fleet Management",
                                f"Renewed {doc_type} for {selected_bus_display}, Cost: ${cost:.2f}"
                            )
                            
                            st.success(f"✅ {doc_type} renewed successfully! New expiry: {new_expiry}")
                            st.balloons()
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error saving renewal: {e}")
            
            st.markdown("---")
            
            # Recent renewals from expenses
            st.markdown("### 📋 Recent Insurance Expenses")
            
            try:
                insurance_expenses = pd.read_sql_query("""
                    SELECT expense_date, description, vendor, amount, payment_method, payment_status
                    FROM general_expenses
                    WHERE subcategory = 'Insurance' OR notes LIKE '%bus_insurance%'
                    ORDER BY expense_date DESC
                    LIMIT 20
                """, get_engine())
                
                if insurance_expenses.empty:
                    st.info("No insurance expenses recorded yet")
                else:
                    insurance_expenses.columns = ['Date', 'Description', 'Vendor', 'Amount ($)', 'Payment', 'Status']
                    st.dataframe(insurance_expenses, use_container_width=True, hide_index=True)
                    
                    total_insurance = insurance_expenses['Amount ($)'].sum()
                    st.metric("Total Insurance Expenses", f"${total_insurance:,.2f}")
            except Exception as e:
                st.info("No insurance expense data available")
    
    conn.close()