"""
pages_fuel.py - Fuel Tracking Module
Pavillion Coaches Bus Management System
Track fuel consumption, costs, and efficiency per bus
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
        SELECT bus_number, registration_number, make, model 
        FROM buses 
        WHERE status = 'Active' 
        ORDER BY registration_number
    """)
    
    buses = cursor.fetchall()
    conn.close()
    return buses


def get_last_odometer(bus_number):
    """Get the last recorded odometer reading for a bus"""
    conn = get_connection()
    cursor = conn.cursor()
    
    ph = '%s' if USE_POSTGRES else '?'
    cursor.execute(f"""
        SELECT odometer_reading 
        FROM fuel_records 
        WHERE bus_number = {ph} AND odometer_reading IS NOT NULL
        ORDER BY date DESC, id DESC
        LIMIT 1
    """, (bus_number,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result['odometer_reading'] if hasattr(result, 'keys') else result[0]
    return None


def add_fuel_record(bus_number, date, liters, cost_per_liter, total_cost, 
                    odometer_reading=None, fuel_station=None, payment_method='Cash',
                    receipt_number=None, filled_by=None, notes=None, created_by=None):
    """Add a new fuel record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Calculate km traveled and fuel efficiency if odometer provided
    previous_odometer = None
    km_traveled = None
    fuel_efficiency = None
    
    if odometer_reading:
        previous_odometer = get_last_odometer(bus_number)
        if previous_odometer and odometer_reading > previous_odometer:
            km_traveled = odometer_reading - previous_odometer
            fuel_efficiency = km_traveled / liters if liters > 0 else None
    
    try:
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO fuel_records (
                    bus_number, date, liters, cost_per_liter, total_cost,
                    odometer_reading, previous_odometer, km_traveled, fuel_efficiency,
                    fuel_station, payment_method, receipt_number, filled_by, notes, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (bus_number, date, liters, cost_per_liter, total_cost,
                  odometer_reading, previous_odometer, km_traveled, fuel_efficiency,
                  fuel_station, payment_method, receipt_number, filled_by, notes, created_by))
            result = cursor.fetchone()
            record_id = result['id'] if hasattr(result, 'keys') else result[0]
        else:
            cursor.execute("""
                INSERT INTO fuel_records (
                    bus_number, date, liters, cost_per_liter, total_cost,
                    odometer_reading, previous_odometer, km_traveled, fuel_efficiency,
                    fuel_station, payment_method, receipt_number, filled_by, notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (bus_number, date, liters, cost_per_liter, total_cost,
                  odometer_reading, previous_odometer, km_traveled, fuel_efficiency,
                  fuel_station, payment_method, receipt_number, filled_by, notes, created_by))
            record_id = cursor.lastrowid
        
        conn.commit()
        return record_id
    except Exception as e:
        print(f"Error adding fuel record: {e}")
        return None
    finally:
        conn.close()


def get_fuel_records(bus_number=None, start_date=None, end_date=None):
    """Get fuel records with optional filters"""
    conn = get_connection()
    
    query = "SELECT * FROM fuel_records WHERE 1=1"
    params = []
    
    ph = '%s' if USE_POSTGRES else '?'
    
    if bus_number:
        query += f" AND bus_number = {ph}"
        params.append(bus_number)
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(start_date)
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(end_date)
    
    query += " ORDER BY date DESC, id DESC"
    
    df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    conn.close()
    return df


def update_fuel_record(record_id, **kwargs):
    """Update a fuel record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Build update query dynamically
    set_clauses = []
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    for key, value in kwargs.items():
        if value is not None:
            set_clauses.append(f"{key} = {ph}")
            params.append(value)
    
    if not set_clauses:
        return False
    
    set_clauses.append(f"updated_at = CURRENT_TIMESTAMP")
    params.append(record_id)
    
    query = f"UPDATE fuel_records SET {', '.join(set_clauses)} WHERE id = {ph}"
    
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating fuel record: {e}")
        return False
    finally:
        conn.close()


def delete_fuel_record(record_id):
    """Delete a fuel record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    ph = '%s' if USE_POSTGRES else '?'
    
    try:
        cursor.execute(f"DELETE FROM fuel_records WHERE id = {ph}", (record_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting fuel record: {e}")
        return False
    finally:
        conn.close()


def get_fuel_summary_by_bus(start_date=None, end_date=None):
    """Get fuel summary statistics by bus"""
    conn = get_connection()
    
    query = """
        SELECT 
            bus_number,
            COUNT(*) as fill_count,
            SUM(liters) as total_liters,
            SUM(total_cost) as total_cost,
            AVG(cost_per_liter) as avg_cost_per_liter,
            AVG(fuel_efficiency) as avg_efficiency,
            SUM(km_traveled) as total_km
        FROM fuel_records
        WHERE 1=1
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(start_date)
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(end_date)
    
    query += " GROUP BY bus_number ORDER BY total_cost DESC"
    
    df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    conn.close()
    return df


def get_fuel_trends(bus_number=None, days=90):
    """Get daily fuel cost trends"""
    conn = get_connection()
    
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    query = """
        SELECT 
            date,
            SUM(total_cost) as daily_cost,
            SUM(liters) as daily_liters,
            AVG(fuel_efficiency) as avg_efficiency
        FROM fuel_records
        WHERE date >= %s
    """ if USE_POSTGRES else """
        SELECT 
            date,
            SUM(total_cost) as daily_cost,
            SUM(liters) as daily_liters,
            AVG(fuel_efficiency) as avg_efficiency
        FROM fuel_records
        WHERE date >= ?
    """
    
    params = [start_date]
    
    if bus_number:
        ph = '%s' if USE_POSTGRES else '?'
        query += f" AND bus_number = {ph}"
        params.append(bus_number)
    
    query += " GROUP BY date ORDER BY date"
    
    df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    conn.close()
    return df


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_bus_display_option(bus):
    """Format bus for dropdown display"""
    if hasattr(bus, 'keys'):
        reg = bus.get('registration_number') or 'No Reg'
        model = bus.get('model', '')
    else:
        reg = bus[1] or 'No Reg'
        model = bus[3] if len(bus) > 3 else ''
    
    return f"{reg} ({model})" if model else reg


def extract_bus_from_option(option, buses):
    """Extract bus_number from display option"""
    for bus in buses:
        if get_bus_display_option(bus) == option:
            if hasattr(bus, 'keys'):
                return bus.get('registration_number') or bus.get('bus_number')
            else:
                return bus[1] or bus[0]  # registration_number or bus_number
    return None


# =============================================================================
# PAGE FUNCTIONS
# =============================================================================

def fuel_entry_page():
    """Fuel entry page for recording fuel purchases"""
    
    st.header("⛽ Fuel Entry")
    st.markdown("Record fuel purchases for buses")
    st.markdown("---")
    
    # Check permissions
    can_add = has_permission('add_income')  # Using income permission for now
    can_edit = has_permission('edit_income')
    can_delete = has_permission('delete_income')
    
    tab1, tab2, tab3 = st.tabs(["➕ Add Fuel Record", "📋 Fuel History", "✏️ Edit/Delete"])
    
    with tab1:
        if not can_add:
            st.warning("You don't have permission to add fuel records")
        else:
            st.subheader("➕ Record Fuel Purchase")
            
            buses = get_active_buses()
            
            if not buses:
                st.warning("No active buses found. Please add buses first.")
            else:
                # Create bus options
                bus_options = [get_bus_display_option(bus) for bus in buses]
                
                with st.form("fuel_entry_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        selected_bus_option = st.selectbox("Select Bus (Registration)*", bus_options)
                        fuel_date = st.date_input("Date*", value=datetime.now().date())
                        liters = st.number_input("Liters*", min_value=0.0, step=1.0, format="%.2f")
                        cost_per_liter = st.number_input("Cost per Liter ($)*", min_value=0.0, step=0.01, format="%.2f")
                        
                        # Auto-calculate total
                        total_cost = liters * cost_per_liter
                        st.metric("Total Cost", f"${total_cost:.2f}")
                    
                    with col2:
                        # Get last odometer for selected bus
                        selected_bus = extract_bus_from_option(selected_bus_option, buses)
                        last_odometer = get_last_odometer(selected_bus) if selected_bus else None
                        
                        if last_odometer:
                            st.info(f"📊 Last odometer reading: **{last_odometer:,.0f} km**")
                        else:
                            st.info("📊 No previous odometer reading recorded")
                        
                        odometer_reading = st.number_input(
                            "Odometer Reading (km)", 
                            min_value=0.0, 
                            step=1.0, 
                            format="%.0f",
                            help="Optional - Leave as 0 if odometer is malfunctioning"
                        )
                        
                        fuel_station = st.text_input("Fuel Station", placeholder="e.g., Zuva, Puma, Total")
                        payment_method = st.selectbox("Payment Method", ["Cash", "Fuel Card", "EcoCash", "Bank Transfer", "Credit"])
                        receipt_number = st.text_input("Receipt Number", placeholder="Optional")
                    
                    filled_by = st.text_input("Filled By", placeholder="Person who filled the tank")
                    notes = st.text_area("Notes", placeholder="Any additional notes...")
                    
                    submitted = st.form_submit_button("⛽ Save Fuel Record", type="primary", use_container_width=True)
                    
                    if submitted:
                        if not selected_bus or liters <= 0 or cost_per_liter <= 0:
                            st.error("Please fill in all required fields (Bus, Liters, Cost per Liter)")
                        else:
                            # Set odometer to None if 0
                            odo = odometer_reading if odometer_reading > 0 else None
                            
                            record_id = add_fuel_record(
                                bus_number=selected_bus,
                                date=str(fuel_date),
                                liters=liters,
                                cost_per_liter=cost_per_liter,
                                total_cost=total_cost,
                                odometer_reading=odo,
                                fuel_station=fuel_station,
                                payment_method=payment_method,
                                receipt_number=receipt_number,
                                filled_by=filled_by,
                                notes=notes,
                                created_by=st.session_state['user']['username']
                            )
                            
                            if record_id:
                                AuditLogger.log_action(
                                    "Create", "Fuel",
                                    f"Added fuel record: {selected_bus} - {liters}L @ ${cost_per_liter}/L = ${total_cost:.2f}"
                                )
                                st.success(f"✅ Fuel record saved! (ID: {record_id})")
                                
                                # Show efficiency if calculated
                                if odo and get_last_odometer(selected_bus):
                                    last_odo = get_last_odometer(selected_bus)
                                    # Note: last_odo is now the new reading, so we need to recalculate
                                    # This is handled in the add_fuel_record function
                                    st.info("📊 Fuel efficiency calculated and saved")
                                
                                st.rerun()
                            else:
                                st.error("Error saving fuel record")
    
    with tab2:
        st.subheader("📋 Fuel History")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            buses = get_active_buses()
            bus_options = ["All Buses"] + [get_bus_display_option(bus) for bus in buses]
            filter_bus = st.selectbox("Filter by Bus", bus_options, key="history_bus")
        
        with col2:
            filter_start = st.date_input("From Date", value=datetime.now().date() - timedelta(days=30), key="history_start")
        
        with col3:
            filter_end = st.date_input("To Date", value=datetime.now().date(), key="history_end")
        
        # Get bus number for filter
        filter_bus_number = None
        if filter_bus != "All Buses":
            filter_bus_number = extract_bus_from_option(filter_bus, buses)
        
        # Get records
        records_df = get_fuel_records(
            bus_number=filter_bus_number,
            start_date=str(filter_start),
            end_date=str(filter_end)
        )
        
        if records_df.empty:
            st.info("No fuel records found for the selected filters")
        else:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Records", len(records_df))
            with col2:
                st.metric("Total Liters", f"{records_df['liters'].sum():,.0f} L")
            with col3:
                st.metric("Total Cost", f"${records_df['total_cost'].sum():,.2f}")
            with col4:
                avg_eff = records_df['fuel_efficiency'].dropna().mean()
                if pd.notna(avg_eff):
                    st.metric("Avg Efficiency", f"{avg_eff:.1f} km/L")
                else:
                    st.metric("Avg Efficiency", "N/A")
            
            st.markdown("---")
            
            # Display records
            display_df = records_df[[
                'id', 'date', 'bus_number', 'liters', 'cost_per_liter', 
                'total_cost', 'odometer_reading', 'fuel_efficiency', 'fuel_station'
            ]].copy()
            
            display_df.columns = ['ID', 'Date', 'Registration', 'Liters', '$/L', 
                                  'Total $', 'Odometer', 'Efficiency (km/L)', 'Station']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Export button
            csv = records_df.to_csv(index=False)
            st.download_button(
                label="📥 Export to CSV",
                data=csv,
                file_name=f"fuel_records_{filter_start}_{filter_end}.csv",
                mime="text/csv"
            )
    
    with tab3:
        st.subheader("✏️ Edit/Delete Fuel Records")
        
        if not can_edit and not can_delete:
            st.warning("You don't have permission to edit or delete fuel records")
        else:
            # Add filter options like History tab
            col1, col2, col3 = st.columns(3)
            
            with col1:
                buses = get_active_buses()
                bus_options = ["All Buses"] + [get_bus_display_option(bus) for bus in buses]
                edit_filter_bus = st.selectbox("Filter by Bus", bus_options, key="edit_bus")
            
            with col2:
                edit_filter_start = st.date_input("From Date", value=datetime.now().date() - timedelta(days=90), key="edit_start")
            
            with col3:
                edit_filter_end = st.date_input("To Date", value=datetime.now().date(), key="edit_end")
            
            # Get bus number for filter
            edit_bus_number = None
            if edit_filter_bus != "All Buses":
                edit_bus_number = extract_bus_from_option(edit_filter_bus, buses)
            
            # Get recent records with filters
            recent_records = get_fuel_records(
                bus_number=edit_bus_number,
                start_date=str(edit_filter_start),
                end_date=str(edit_filter_end)
            )
            
            if recent_records.empty:
                st.info("No fuel records found for the selected filters")
            else:
                # Create selection options
                record_options = {}
                for _, row in recent_records.iterrows():
                    label = f"ID:{row['id']} | {row['date']} | {row['bus_number']} | {row['liters']}L | ${row['total_cost']:.2f}"
                    record_options[label] = row['id']
                
                selected_record = st.selectbox("Select Record to Edit/Delete", list(record_options.keys()))
                
                if selected_record:
                    record_id = record_options[selected_record]
                    record = recent_records[recent_records['id'] == record_id].iloc[0]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Current Values:**")
                        st.write(f"- **Bus:** {record['bus_number']}")
                        st.write(f"- **Date:** {record['date']}")
                        st.write(f"- **Liters:** {record['liters']}")
                        st.write(f"- **Cost/L:** ${record['cost_per_liter']:.2f}")
                        st.write(f"- **Total:** ${record['total_cost']:.2f}")
                        st.write(f"- **Odometer:** {record['odometer_reading'] or 'N/A'}")
                        st.write(f"- **Station:** {record['fuel_station'] or 'N/A'}")
                    
                    with col2:
                        if can_edit:
                            with st.form("edit_fuel_form"):
                                st.markdown("**Edit Values:**")
                                new_liters = st.number_input("Liters", value=float(record['liters']), min_value=0.0, step=1.0)
                                new_cost = st.number_input("Cost per Liter", value=float(record['cost_per_liter']), min_value=0.0, step=0.01)
                                new_station = st.text_input("Station", value=record['fuel_station'] or "")
                                new_notes = st.text_area("Notes", value=record['notes'] or "")
                                
                                if st.form_submit_button("💾 Update Record", type="primary"):
                                    new_total = new_liters * new_cost
                                    if update_fuel_record(
                                        record_id,
                                        liters=new_liters,
                                        cost_per_liter=new_cost,
                                        total_cost=new_total,
                                        fuel_station=new_station,
                                        notes=new_notes
                                    ):
                                        AuditLogger.log_action(
                                            "Update", "Fuel",
                                            f"Updated fuel record ID:{record_id}"
                                        )
                                        st.success("✅ Record updated!")
                                        st.rerun()
                                    else:
                                        st.error("Error updating record")
                        
                        if can_delete:
                            st.markdown("---")
                            st.markdown("**Delete Record:**")
                            if st.button("🗑️ Delete This Record", type="secondary"):
                                st.session_state[f'confirm_delete_fuel_{record_id}'] = True
                            
                            if st.session_state.get(f'confirm_delete_fuel_{record_id}', False):
                                st.warning("⚠️ Are you sure you want to delete this record?")
                                col_yes, col_no = st.columns(2)
                                with col_yes:
                                    if st.button("✅ Yes, Delete"):
                                        if delete_fuel_record(record_id):
                                            AuditLogger.log_action(
                                                "Delete", "Fuel",
                                                f"Deleted fuel record ID:{record_id}"
                                            )
                                            st.success("Record deleted!")
                                            del st.session_state[f'confirm_delete_fuel_{record_id}']
                                            st.rerun()
                                with col_no:
                                    if st.button("❌ Cancel"):
                                        del st.session_state[f'confirm_delete_fuel_{record_id}']
                                        st.rerun()


def fuel_analysis_page():
    """Fuel analysis and reporting page"""
    
    st.header("📊 Fuel Analysis")
    st.markdown("Analyze fuel consumption, costs, and efficiency")
    st.markdown("---")
    
    # Quick period selectors
    st.subheader("📅 Select Period")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        period_options = {
            "Last 7 Days": 7,
            "Last 14 Days": 14,
            "Last 30 Days": 30,
            "Last 3 Months": 90,
            "Last 6 Months": 180,
            "Last Year": 365,
            "This Month": "this_month",
            "Last Month": "last_month",
            "This Year": "this_year",
            "Custom Range": "custom"
        }
        selected_period = st.selectbox("Quick Select Period", list(period_options.keys()))
    
    # Calculate dates based on selection
    today = datetime.now().date()
    
    if period_options[selected_period] == "this_month":
        start_date = today.replace(day=1)
        end_date = today
    elif period_options[selected_period] == "last_month":
        first_of_this_month = today.replace(day=1)
        end_date = first_of_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    elif period_options[selected_period] == "this_year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif period_options[selected_period] == "custom":
        with col2:
            start_date = st.date_input("From", value=today - timedelta(days=30), key="custom_start")
        with col3:
            end_date = st.date_input("To", value=today, key="custom_end")
    else:
        days = period_options[selected_period]
        start_date = today - timedelta(days=days)
        end_date = today
    
    # Display selected period
    st.info(f"📅 Showing data from **{start_date}** to **{end_date}** ({(end_date - start_date).days + 1} days)")
    
    st.markdown("---")
    
    # Get summary data
    summary_df = get_fuel_summary_by_bus(str(start_date), str(end_date))
    
    if summary_df.empty:
        st.warning("No fuel data available for the selected period")
        return
    
    # Overall metrics
    st.subheader("📈 Period Summary")
    
    total_cost = summary_df['total_cost'].sum()
    total_liters = summary_df['total_liters'].sum()
    total_km = summary_df['total_km'].sum()
    avg_efficiency = summary_df['avg_efficiency'].dropna().mean()
    avg_cost_per_liter = summary_df['avg_cost_per_liter'].mean()
    num_buses = len(summary_df)
    total_fills = summary_df['fill_count'].sum()
    
    # Calculate daily averages
    days_in_period = (end_date - start_date).days + 1
    daily_avg_cost = total_cost / days_in_period if days_in_period > 0 else 0
    daily_avg_liters = total_liters / days_in_period if days_in_period > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Total Fuel Cost", f"${total_cost:,.2f}")
        st.caption(f"${daily_avg_cost:,.2f}/day avg")
    with col2:
        st.metric("⛽ Total Liters", f"{total_liters:,.0f} L")
        st.caption(f"{daily_avg_liters:,.0f} L/day avg")
    with col3:
        st.metric("🚗 Total KM Traveled", f"{total_km:,.0f} km")
    with col4:
        st.metric("⚡ Avg Efficiency", f"{avg_efficiency:.1f} km/L" if pd.notna(avg_efficiency) else "N/A")
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("💵 Avg Cost/Liter", f"${avg_cost_per_liter:.2f}")
    with col6:
        st.metric("🚌 Buses Fueled", num_buses)
    with col7:
        st.metric("🔄 Total Fill-ups", int(total_fills))
    with col8:
        cost_per_km = total_cost / total_km if total_km > 0 else 0
        st.metric("💲 Cost per KM", f"${cost_per_km:.2f}")
    
    st.markdown("---")
    
    # Charts
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 By Bus", "📈 Trends", "⚡ Efficiency", "📋 Period Comparison", "🚨 Alerts"])
    
    with tab1:
        st.subheader("Fuel Cost by Bus")
        
        if not summary_df.empty:
            # Bar chart - Cost by bus
            fig_cost = px.bar(
                summary_df.head(15),
                x='bus_number',
                y='total_cost',
                title=f'Total Fuel Cost by Bus ({selected_period})',
                labels={'bus_number': 'Registration', 'total_cost': 'Total Cost ($)'},
                color='total_cost',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_cost, use_container_width=True)
            
            # Pie chart - Cost distribution
            fig_pie = px.pie(
                summary_df.head(10),
                values='total_cost',
                names='bus_number',
                title='Fuel Cost Distribution (Top 10 Buses)'
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Table
            st.markdown("### Detailed Summary")
            display_summary = summary_df.copy()
            display_summary.columns = ['Registration', 'Fill Count', 'Total Liters', 'Total Cost ($)', 
                                       'Avg $/L', 'Avg Efficiency (km/L)', 'Total KM']
            st.dataframe(display_summary, use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("Fuel Cost Trends")
        
        trends_df = get_fuel_trends(days=90)
        
        if not trends_df.empty:
            # Daily cost trend
            fig_trend = px.line(
                trends_df,
                x='date',
                y='daily_cost',
                title='Daily Fuel Spending',
                labels={'date': 'Date', 'daily_cost': 'Cost ($)'}
            )
            fig_trend.update_traces(fill='tozeroy')
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # Weekly aggregation
            trends_df['date'] = pd.to_datetime(trends_df['date'])
            weekly = trends_df.resample('W', on='date').agg({
                'daily_cost': 'sum',
                'daily_liters': 'sum'
            }).reset_index()
            
            fig_weekly = px.bar(
                weekly,
                x='date',
                y='daily_cost',
                title='Weekly Fuel Spending',
                labels={'date': 'Week', 'daily_cost': 'Cost ($)'}
            )
            st.plotly_chart(fig_weekly, use_container_width=True)
    
    with tab3:
        st.subheader("⚡ Fuel Efficiency Analysis")
        
        # Get efficiency data
        eff_df = summary_df[summary_df['avg_efficiency'].notna()].copy()
        
        if eff_df.empty:
            st.warning("No efficiency data available. Make sure to record odometer readings!")
        else:
            # Sort by efficiency
            eff_df = eff_df.sort_values('avg_efficiency', ascending=False)
            
            # Efficiency bar chart
            fig_eff = px.bar(
                eff_df,
                x='bus_number',
                y='avg_efficiency',
                title='Fuel Efficiency by Bus (km/L)',
                labels={'bus_number': 'Registration', 'avg_efficiency': 'Efficiency (km/L)'},
                color='avg_efficiency',
                color_continuous_scale='Greens'
            )
            
            # Add average line
            avg_eff = eff_df['avg_efficiency'].mean()
            annotation_label = "Fleet Avg: " + str(round(avg_eff, 1)) + " km/L"
            fig_eff.add_hline(y=avg_eff, line_dash="dash", line_color="red", 
                            annotation_text=annotation_label)
            
            st.plotly_chart(fig_eff, use_container_width=True)
            
            # Best and worst performers
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🏆 Most Efficient Buses")
                best = eff_df.head(5)[['bus_number', 'avg_efficiency', 'total_km']]
                best.columns = ['Registration', 'Efficiency (km/L)', 'Total KM']
                st.dataframe(best, hide_index=True)
            
            with col2:
                st.markdown("### ⚠️ Least Efficient Buses")
                worst = eff_df.tail(5)[['bus_number', 'avg_efficiency', 'total_km']]
                worst.columns = ['Registration', 'Efficiency (km/L)', 'Total KM']
                st.dataframe(worst, hide_index=True)
    
    with tab4:
        st.subheader("📋 Period Comparison")
        st.markdown("Compare fuel consumption across different time periods")
        
        # Get data for different periods
        today = datetime.now().date()
        
        periods = {
            "Last 7 Days": (today - timedelta(days=7), today),
            "Previous 7 Days": (today - timedelta(days=14), today - timedelta(days=7)),
            "Last 14 Days": (today - timedelta(days=14), today),
            "Previous 14 Days": (today - timedelta(days=28), today - timedelta(days=14)),
            "Last 30 Days": (today - timedelta(days=30), today),
            "Previous 30 Days": (today - timedelta(days=60), today - timedelta(days=30)),
            "This Month": (today.replace(day=1), today),
            "Last Month": ((today.replace(day=1) - timedelta(days=1)).replace(day=1), today.replace(day=1) - timedelta(days=1)),
        }
        
        # Comparison selection
        col1, col2 = st.columns(2)
        with col1:
            period1 = st.selectbox("Compare Period 1", ["Last 7 Days", "Last 14 Days", "Last 30 Days", "This Month"], key="period1")
        with col2:
            period2 = st.selectbox("With Period 2", ["Previous 7 Days", "Previous 14 Days", "Previous 30 Days", "Last Month"], key="period2")
        
        # Get data for both periods
        p1_start, p1_end = periods[period1]
        p2_start, p2_end = periods[period2]
        
        p1_data = get_fuel_summary_by_bus(str(p1_start), str(p1_end))
        p2_data = get_fuel_summary_by_bus(str(p2_start), str(p2_end))
        
        # Calculate totals
        p1_cost = p1_data['total_cost'].sum() if not p1_data.empty else 0
        p2_cost = p2_data['total_cost'].sum() if not p2_data.empty else 0
        p1_liters = p1_data['total_liters'].sum() if not p1_data.empty else 0
        p2_liters = p2_data['total_liters'].sum() if not p2_data.empty else 0
        p1_km = p1_data['total_km'].sum() if not p1_data.empty else 0
        p2_km = p2_data['total_km'].sum() if not p2_data.empty else 0
        
        # Calculate changes
        cost_change = ((p1_cost - p2_cost) / p2_cost * 100) if p2_cost > 0 else 0
        liters_change = ((p1_liters - p2_liters) / p2_liters * 100) if p2_liters > 0 else 0
        km_change = ((p1_km - p2_km) / p2_km * 100) if p2_km > 0 else 0
        
        st.markdown("---")
        
        # Display comparison
        st.markdown(f"### {period1} vs {period2}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            delta_color = "inverse" if cost_change > 0 else "normal"  # Higher cost is bad
            st.metric(
                f"💰 Total Cost",
                f"${p1_cost:,.2f}",
                f"{cost_change:+.1f}% vs {period2}",
                delta_color=delta_color
            )
            st.caption(f"{period2}: ${p2_cost:,.2f}")
        
        with col2:
            delta_color = "inverse" if liters_change > 0 else "normal"
            st.metric(
                f"⛽ Total Liters",
                f"{p1_liters:,.0f} L",
                f"{liters_change:+.1f}%",
                delta_color=delta_color
            )
            st.caption(f"{period2}: {p2_liters:,.0f} L")
        
        with col3:
            delta_color = "normal" if km_change > 0 else "inverse"  # More km is good
            st.metric(
                f"🚗 Total KM",
                f"{p1_km:,.0f} km",
                f"{km_change:+.1f}%",
                delta_color=delta_color
            )
            st.caption(f"{period2}: {p2_km:,.0f} km")
        
        st.markdown("---")
        
        # Per-bus comparison
        st.markdown("### Per-Bus Comparison")
        
        if not p1_data.empty and not p2_data.empty:
            # Merge data
            comparison = p1_data[['bus_number', 'total_cost', 'total_liters']].merge(
                p2_data[['bus_number', 'total_cost', 'total_liters']],
                on='bus_number',
                how='outer',
                suffixes=('_current', '_previous')
            ).fillna(0)
            
            comparison['cost_change'] = comparison['total_cost_current'] - comparison['total_cost_previous']
            comparison['cost_change_pct'] = ((comparison['total_cost_current'] - comparison['total_cost_previous']) / 
                                              comparison['total_cost_previous'].replace(0, 1) * 100)
            
            # Sort by cost change
            comparison = comparison.sort_values('cost_change', ascending=False)
            
            # Show buses with biggest cost increases
            st.markdown("#### 🔺 Biggest Cost Increases")
            increases = comparison[comparison['cost_change'] > 0].head(5)
            if not increases.empty:
                for _, row in increases.iterrows():
                    st.write(f"- **{row['bus_number']}**: +${row['cost_change']:,.2f} ({row['cost_change_pct']:+.1f}%)")
            else:
                st.success("No buses with increased fuel costs!")
            
            st.markdown("#### 🔻 Biggest Cost Decreases")
            decreases = comparison[comparison['cost_change'] < 0].tail(5)
            if not decreases.empty:
                for _, row in decreases.iterrows():
                    st.write(f"- **{row['bus_number']}**: ${row['cost_change']:,.2f} ({row['cost_change_pct']:+.1f}%)")
            else:
                st.info("No buses with decreased fuel costs")
        
        # Monthly summary table
        st.markdown("---")
        st.markdown("### 📊 Monthly Summary (Last 6 Months)")
        
        monthly_data = []
        for i in range(6):
            month_end = (today.replace(day=1) - timedelta(days=1)) if i == 0 else (today.replace(day=1) - timedelta(days=30*i))
            month_start = month_end.replace(day=1)
            
            if i > 0:
                # Adjust for previous months
                for _ in range(i):
                    month_end = (month_start - timedelta(days=1))
                    month_start = month_end.replace(day=1)
            else:
                month_start = today.replace(day=1)
                month_end = today
            
            month_summary = get_fuel_summary_by_bus(str(month_start), str(month_end))
            
            monthly_data.append({
                'Month': month_start.strftime('%B %Y'),
                'Total Cost ($)': month_summary['total_cost'].sum() if not month_summary.empty else 0,
                'Total Liters': month_summary['total_liters'].sum() if not month_summary.empty else 0,
                'Buses Fueled': len(month_summary) if not month_summary.empty else 0,
                'Fill-ups': month_summary['fill_count'].sum() if not month_summary.empty else 0
            })
        
        monthly_df = pd.DataFrame(monthly_data)
        st.dataframe(monthly_df, use_container_width=True, hide_index=True)
    
    with tab5:
        st.subheader("🚨 Fuel Alerts & Anomalies")
        
        if summary_df.empty:
            st.info("No data for alerts")
        else:
            # Buses without odometer readings
            st.markdown("### 📝 Missing Odometer Data")
            no_odo = summary_df[summary_df['avg_efficiency'].isna()]
            if not no_odo.empty:
                st.warning(f"⚠️ {len(no_odo)} buses have no efficiency data (missing odometer readings)")
                st.dataframe(no_odo[['bus_number', 'fill_count', 'total_cost']], hide_index=True)
            else:
                st.success("✅ All buses have odometer data")
            
            st.markdown("---")
            
            # High fuel consumption buses
            st.markdown("### 🔴 High Fuel Cost Buses")
            avg_cost = summary_df['total_cost'].mean()
            high_cost = summary_df[summary_df['total_cost'] > avg_cost * 1.5]
            
            if not high_cost.empty:
                st.warning(f"⚠️ {len(high_cost)} buses have fuel costs 50% above average")
                for _, row in high_cost.iterrows():
                    st.write(f"- **{row['bus_number']}**: ${row['total_cost']:,.2f} (Avg: ${avg_cost:,.2f})")
            else:
                st.success("✅ No buses with abnormally high fuel costs")
            
            # Low efficiency buses
            eff_df = summary_df[summary_df['avg_efficiency'].notna()].copy()
            if not eff_df.empty:
                st.markdown("---")
                st.markdown("### ⚠️ Low Efficiency Buses")
                avg_eff = eff_df['avg_efficiency'].mean()
                low_eff = eff_df[eff_df['avg_efficiency'] < avg_eff * 0.7]
                
                if not low_eff.empty:
                    st.warning(f"⚠️ {len(low_eff)} buses have efficiency 30% below average")
                    for _, row in low_eff.iterrows():
                        st.write(f"- **{row['bus_number']}**: {row['avg_efficiency']:.1f} km/L (Avg: {avg_eff:.1f} km/L)")
                    st.info("💡 Consider checking these buses for engine issues, tire pressure, or driving habits")
                else:
                    st.success("✅ No buses with abnormally low efficiency")