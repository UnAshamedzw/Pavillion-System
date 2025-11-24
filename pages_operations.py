"""
pages_operations.py - Complete Operations Module with Buses and Routes Management
NOW WITH DROPDOWN SELECTIONS and HIRE SUPPORT
"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from audit_logger import AuditLogger
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import io
from database import (
    get_all_buses, get_active_buses, add_bus, update_bus, delete_bus,
    get_all_routes, add_route, update_route, delete_route
)

# ============================================================================
# BUSES AND ROUTES MANAGEMENT PAGE
# ============================================================================

def buses_routes_management_page():
    """Manage buses and routes"""
    
    st.header("🚌 Buses & Routes Management")
    st.markdown("Manage your fleet and route information")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["🚌 Buses", "🛣️ Routes"])
    
    # ========== BUSES TAB ==========
    with tab1:
        st.subheader("🚌 Fleet Management")
        
        # Add Bus Form
        with st.expander("➕ Add New Bus", expanded=False):
            with st.form("add_bus_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    bus_number = st.text_input("Bus Number*", placeholder="e.g., Bus 1, Bus 2")
                    registration_number = st.text_input("Registration Number", placeholder="e.g., ABC-1234")
                    model = st.text_input("Model*", placeholder="e.g., Mercedes Sprinter")
                    capacity = st.number_input("Capacity (seats)*", min_value=1, step=1, value=50)
                
                with col2:
                    year = st.number_input("Year", min_value=1900, max_value=2030, value=2020, step=1)
                    status = st.selectbox("Status", ["Active", "Maintenance", "Inactive"])
                
                notes = st.text_area("Notes", placeholder="Additional information...")
                
                submit_bus = st.form_submit_button("➕ Add Bus", use_container_width=True, type="primary")
                
                if submit_bus:
                    if not all([bus_number, model, capacity]):
                        st.error("⚠️ Please fill in all required fields")
                    else:
                        bus_id = add_bus(
                            bus_number=bus_number,
                            model=model,
                            capacity=capacity,
                            year=year,
                            status=status,
                            notes=notes,
                            created_by=st.session_state['user']['username'],
                            registration_number=registration_number
                        )
                        
                        if bus_id:
                            st.success(f"✅ Bus {bus_number} added successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Bus with this number already exists")
        
        st.markdown("---")
        
        # Display Buses
        buses = get_all_buses()
        
        if buses:
            st.subheader(f"📋 Fleet List ({len(buses)} buses)")
            
            for bus in buses:
                # Display both bus_number and registration_number if available
                display_title = f"🚌 {bus['bus_number']}"
                if 'registration_number' in bus.keys() and bus['registration_number']:
                    display_title += f" ({bus['registration_number']})"
                display_title += f" - {bus['model']} ({bus['status']})"
                
                with st.expander(display_title):
                    col_info, col_actions = st.columns([3, 1])
                    
                    with col_info:
                        st.write(f"**Bus Number:** {bus['bus_number']}")
                        if 'registration_number' in bus.keys() and bus['registration_number']:
                            st.write(f"**Registration Number:** {bus['registration_number']}")
                        st.write(f"**Model:** {bus['model']}")
                        st.write(f"**Capacity:** {bus['capacity']} seats")
                        st.write(f"**Year:** {bus['year'] or 'N/A'}")
                        st.write(f"**Status:** {bus['status']}")
                        if bus['notes']:
                            st.write(f"**Notes:** {bus['notes']}")
                        st.caption(f"Added: {bus['created_at']} by {bus['created_by']}")
                    
                    with col_actions:
                        if st.button("✏️ Edit", key=f"edit_bus_{bus['id']}"):
                            st.session_state[f'edit_bus_{bus["id"]}'] = True
                            st.rerun()
                        
                        if st.button("🗑️ Delete", key=f"delete_bus_{bus['id']}"):
                            if st.session_state.get(f'confirm_delete_bus_{bus["id"]}', False):
                                delete_bus(bus['id'])
                                st.success(f"Bus {bus['bus_number']} deleted")
                                st.rerun()
                            else:
                                st.session_state[f'confirm_delete_bus_{bus["id"]}'] = True
                                st.warning("Click again to confirm")
                    
                    # Edit Form
                    if st.session_state.get(f'edit_bus_{bus["id"]}', False):
                        st.markdown("---")
                        with st.form(f"edit_bus_form_{bus['id']}"):
                            edit_col1, edit_col2 = st.columns(2)
                            
                            with edit_col1:
                                edit_bus_number = st.text_input("Bus Number", value=bus['bus_number'])
                                edit_registration = st.text_input("Registration Number", 
                                    value=bus['registration_number'] if 'registration_number' in bus.keys() and bus['registration_number'] else '')
                                edit_model = st.text_input("Model", value=bus['model'])
                                edit_capacity = st.number_input("Capacity", value=bus['capacity'], min_value=1)
                            
                            with edit_col2:
                                edit_year = st.number_input("Year", value=bus['year'] or 2020, min_value=1900, max_value=2030)
                                edit_status = st.selectbox("Status", ["Active", "Maintenance", "Inactive"], 
                                                          index=["Active", "Maintenance", "Inactive"].index(bus['status']))
                            
                            edit_notes = st.text_area("Notes", value=bus['notes'] or "")
                            
                            col_save, col_cancel = st.columns(2)
                            
                            with col_save:
                                save_btn = st.form_submit_button("💾 Save", use_container_width=True)
                            with col_cancel:
                                cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
                            
                            if save_btn:
                                update_bus(bus['id'], edit_bus_number, edit_model, edit_capacity, 
                                         edit_year, edit_status, edit_notes, registration_number=edit_registration)
                                st.success("✅ Bus updated successfully!")
                                st.session_state[f'edit_bus_{bus["id"]}'] = False
                                st.rerun()
                            
                            if cancel_btn:
                                st.session_state[f'edit_bus_{bus["id"]}'] = False
                                st.rerun()
        else:
            st.info("🔭 No buses added yet. Add your first bus above!")
    
    # ========== ROUTES TAB ==========
    with tab2:
        st.subheader("🛣️ Routes Management")
        
        # Add Route Form
        with st.expander("➕ Add New Route", expanded=False):
            with st.form("add_route_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    route_name = st.text_input("Route Name*", placeholder="e.g., Harare - Mutare")
                
                with col2:
                    distance = st.number_input("Distance (km)", min_value=0.0, step=1.0, value=0.0)
                
                description = st.text_area("Description", placeholder="Additional route information...")
                
                submit_route = st.form_submit_button("➕ Add Route", use_container_width=True, type="primary")
                
                if submit_route:
                    if not route_name:
                        st.error("⚠️ Please enter a route name")
                    else:
                        route_id = add_route(
                            name=route_name,
                            distance=distance if distance > 0 else None,
                            description=description,
                            created_by=st.session_state['user']['username']
                        )
                        
                        if route_id:
                            st.success(f"✅ Route '{route_name}' added successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Route with this name already exists")
        
        st.markdown("---")
        
        # Display Routes
        routes = get_all_routes()
        
        if routes:
            st.subheader(f"📋 Routes List ({len(routes)} routes)")
            
            # Note about Hire route
            st.info("💡 **Note:** The 'Hire' route is automatically available for hire jobs. You don't need to add it here.")
            
            for route in routes:
                with st.expander(f"🛣️ {route['name']}"):
                    col_info, col_actions = st.columns([3, 1])
                    
                    with col_info:
                        st.write(f"**Route:** {route['name']}")
                        st.write(f"**Distance:** {route['distance']} km" if route['distance'] else "**Distance:** Not specified")
                        if route['description']:
                            st.write(f"**Description:** {route['description']}")
                        st.caption(f"Added: {route['created_at']} by {route['created_by']}")
                    
                    with col_actions:
                        if st.button("✏️ Edit", key=f"edit_route_{route['id']}"):
                            st.session_state[f'edit_route_{route["id"]}'] = True
                            st.rerun()
                        
                        if st.button("🗑️ Delete", key=f"delete_route_{route['id']}"):
                            if st.session_state.get(f'confirm_delete_route_{route["id"]}', False):
                                delete_route(route['id'])
                                st.success(f"Route '{route['name']}' deleted")
                                st.rerun()
                            else:
                                st.session_state[f'confirm_delete_route_{route["id"]}'] = True
                                st.warning("Click again to confirm")
                    
                    # Edit Form
                    if st.session_state.get(f'edit_route_{route["id"]}', False):
                        st.markdown("---")
                        with st.form(f"edit_route_form_{route['id']}"):
                            edit_name = st.text_input("Route Name", value=route['name'])
                            edit_distance = st.number_input("Distance (km)", value=route['distance'] or 0.0, min_value=0.0, step=1.0)
                            edit_desc = st.text_area("Description", value=route['description'] or "")
                            
                            col_save, col_cancel = st.columns(2)
                            
                            with col_save:
                                save_btn = st.form_submit_button("💾 Save", use_container_width=True)
                            with col_cancel:
                                cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
                            
                            if save_btn:
                                update_route(route['id'], edit_name, edit_distance if edit_distance > 0 else None, edit_desc)
                                st.success("✅ Route updated successfully!")
                                st.session_state[f'edit_route_{route["id"]}'] = False
                                st.rerun()
                            
                            if cancel_btn:
                                st.session_state[f'edit_route_{route["id"]}'] = False
                                st.rerun()
        else:
            st.info("🔭 No routes added yet. Add your first route above!")


# ============================================================================
# PDF GENERATION HELPER
# ============================================================================

def generate_income_pdf(records_df, filters, username):
    """Generate PDF report for income records"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           leftMargin=0.5*inch, rightMargin=0.5*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#34495e'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    elements.append(Paragraph("🚌 Bus Management System", title_style))
    elements.append(Paragraph("Income Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    report_date = datetime.now().strftime("%B %d, %Y at %H:%M")
    metadata = f"Generated: {report_date} | By: {username}"
    elements.append(Paragraph(metadata, subtitle_style))
    elements.append(Spacer(1, 0.3*inch))
    
    if filters:
        filter_text = "Filters: " + ", ".join([f"{k}: {v}" for k, v in filters.items()])
        elements.append(Paragraph(filter_text, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
    
    if not records_df.empty:
        table_data = [['Date', 'Bus', 'Driver', 'Conductor', 'Route', 'Amount', 'Notes']]
        
        for _, row in records_df.iterrows():
            route_display = row.get('route', '')
            if route_display == 'Hire' and row.get('hire_destination'):
                route_display = f"Hire: {row.get('hire_destination', '')[:15]}"
            
            table_data.append([
                str(row.get('date', '')),
                str(row.get('bus_number', '')),
                str(row.get('driver_name', 'N/A')),
                str(row.get('conductor_name', 'N/A')),
                str(route_display),
                f"${row.get('amount', 0):.2f}",
                str(row.get('notes', ''))[:20]
            ])
        
        total_amount = records_df['amount'].sum()
        table_data.append(['TOTAL', '', '', '', '', f"${total_amount:.2f}", ''])
        
        table = Table(table_data, colWidths=[1.0*inch, 0.9*inch, 1.1*inch, 1.1*inch, 1.1*inch, 0.9*inch, 1.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No records found.", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ============================================================================
# INCOME ENTRY PAGE - WITH DROPDOWN SELECTIONS
# ============================================================================

def income_entry_page():
    """Income entry page with dropdown selections for buses and routes"""
    
    st.header("📊 Income Entry")
    st.markdown("Record daily bus revenue with dropdown selections")
    st.markdown("---")
    
    # Get active buses
    buses = get_active_buses()
    if not buses:
        st.warning("⚠️ No active buses found. Please add buses in Fleet Management first.")
        st.info("💡 **How to add buses:** Use the sidebar menu: Operations → 🚌 Fleet Management")
        st.info("📝 **Note:** You can also use 'Buses & Routes' for basic bus setup, but Fleet Management has more features including document tracking.")
        return
    
    # Get routes
    routes = get_all_routes()
    
    # Get drivers and conductors from employees table
    conn = sqlite3.connect('bus_management.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT employee_id, full_name FROM employees WHERE position LIKE '%Driver%' AND status = 'Active'")
    drivers = cursor.fetchall()
    
    cursor.execute("SELECT employee_id, full_name FROM employees WHERE position LIKE '%Conductor%' AND status = 'Active'")
    conductors = cursor.fetchall()
    
    conn.close()
    
    if not drivers:
        st.warning("⚠️ No active drivers found. Please add drivers in Employee Management first.")
        return
    
    if not conductors:
        st.warning("⚠️ No active conductors found. Please add conductors in Employee Management first.")
        return
    
    # Add Income Form
    with st.form("income_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Bus dropdown - UPDATED: Show registration_number first, then bus_number
            bus_options = []
            for bus in buses:
                reg_num = bus['registration_number'] if 'registration_number' in bus.keys() and bus['registration_number'] else 'No Reg'
                bus_options.append(f"{reg_num} - {bus['bus_number']} ({bus['model']})")
            
            selected_bus = st.selectbox("🚌 Select Bus*", bus_options)
            # Extract bus_number from selection (it's between " - " and " (")
            bus_number = selected_bus.split(" - ")[1].split(" (")[0]
            
            # Route dropdown (including Hire option)
            route_options = ["Hire"] + [route['name'] for route in routes]
            selected_route = st.selectbox("🛣️ Route*", route_options)
            
            # Show hire destination field if Hire is selected
            hire_destination = ""
            if selected_route == "Hire":
                hire_destination = st.text_input(
                    "📍 Hire Destination/Description*",
                    placeholder="e.g., Wedding at Lake Chivero, Corporate trip to Nyanga"
                )
            
            # Driver selection
            driver_options = [f"{d[0]} - {d[1]}" for d in drivers]
            selected_driver = st.selectbox("👨‍✈️ Driver*", driver_options)
            driver_name = selected_driver.split(" - ")[1]
        
        with col2:
            date = st.date_input("📅 Date*", datetime.now())
            amount = st.number_input("💰 Amount*", min_value=0.0, step=0.01, format="%.2f")
            
            # Conductor selection
            conductor_options = [f"{c[0]} - {c[1]}" for c in conductors]
            selected_conductor = st.selectbox("👨‍💼 Conductor*", conductor_options)
            conductor_name = selected_conductor.split(" - ")[1]
        
        notes = st.text_area("📝 Notes", placeholder="Optional notes...")
        
        submitted = st.form_submit_button("➕ Add Income Record", use_container_width=True, type="primary")
        
        if submitted:
            # Validation
            if not all([bus_number, selected_route, amount > 0, driver_name, conductor_name]):
                st.error("⚠️ Please fill in all required fields")
            elif selected_route == "Hire" and not hire_destination.strip():
                st.error("⚠️ Please describe the hire destination")
            else:
                # Insert into database
                conn = sqlite3.connect('bus_management.db')
                cursor = conn.cursor()
                
                try:
                    cursor.execute('''
                        INSERT INTO income (bus_number, route, hire_destination, driver_name, conductor_name, 
                                          date, amount, notes, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        bus_number,
                        selected_route,
                        hire_destination if selected_route == "Hire" else None,
                        driver_name,
                        conductor_name,
                        date.strftime("%Y-%m-%d"),
                        amount,
                        notes,
                        st.session_state['user']['username']
                    ))
                    
                    record_id = cursor.lastrowid
                    conn.commit()
                    
                    # ✅ AUTOMATIC AUDIT LOGGING
                    AuditLogger.log_income_add(
                        bus_number=bus_number,
                        route=selected_route,
                        amount=amount,
                        date=date.strftime("%Y-%m-%d")
                    )
                    
                    st.success(f"✅ Income record added successfully! (ID: {record_id})")
                    st.balloons()
                    
                except sqlite3.Error as e:
                    st.error(f"❌ Database error: {e}")
                finally:
                    conn.close()
    
    st.markdown("---")
    
    # Recent Income Records with Edit/Delete
    st.subheader("📋 Recent Income Records")
    
    # Filter options
    col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)
    
    with col_filter1:
        filter_bus = st.text_input("🔍 Filter by Bus", placeholder="Leave empty for all")
    
    with col_filter2:
        filter_route = st.text_input("🔍 Filter by Route", placeholder="Leave empty for all")
    
    with col_filter3:
        filter_driver = st.text_input("🔍 Filter by Driver", placeholder="Leave empty for all")
    
    with col_filter4:
        days_back = st.selectbox("📅 Show last", [7, 30, 90, 365], index=1)
    
    conn = sqlite3.connect('bus_management.db')
    cursor = conn.cursor()
    
    # Build query with filters
    query = '''
        SELECT id, bus_number, route, hire_destination, driver_name, conductor_name, 
               date, amount, notes, created_by
        FROM income
        WHERE date >= date('now', '-' || ? || ' days')
    '''
    params = [days_back]
    
    if filter_bus:
        query += " AND bus_number LIKE ?"
        params.append(f"%{filter_bus}%")
    
    if filter_route:
        query += " AND route LIKE ?"
        params.append(f"%{filter_route}%")
    
    if filter_driver:
        query += " AND driver_name LIKE ?"
        params.append(f"%{filter_driver}%")
    
    query += " ORDER BY date DESC, id DESC LIMIT 50"
    
    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()
    
    if records:
        # Summary stats
        total_revenue = sum(record[7] for record in records)
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("📊 Total Records", len(records))
        with col_stat2:
            st.metric("💰 Total Revenue", f"${total_revenue:,.2f}")
        with col_stat3:
            avg_revenue = total_revenue / len(records) if records else 0
            st.metric("📈 Average Revenue", f"${avg_revenue:,.2f}")
        
        st.markdown("---")
        
        # Export buttons
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        
        with col_exp1:
            if st.button("📄 Download PDF Report", use_container_width=True):
                records_df = pd.DataFrame(records, columns=['id', 'bus_number', 'route', 'hire_destination', 
                                                           'driver_name', 'conductor_name', 'date', 'amount', 
                                                           'notes', 'created_by'])
                filters_dict = {}
                if filter_bus:
                    filters_dict['Bus'] = filter_bus
                if filter_route:
                    filters_dict['Route'] = filter_route
                if filter_driver:
                    filters_dict['Driver'] = filter_driver
                
                pdf_buffer = generate_income_pdf(records_df, filters_dict, st.session_state['user']['full_name'])
                st.download_button(
                    label="📥 Download",
                    data=pdf_buffer,
                    file_name=f"income_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        
        with col_exp2:
            records_df = pd.DataFrame(records, columns=['id', 'bus_number', 'route', 'hire_destination',
                                                       'driver_name', 'conductor_name', 'date', 'amount', 
                                                       'notes', 'created_by'])
            excel_buffer = io.BytesIO()
            records_df.to_excel(excel_buffer, sheet_name='Income', index=False)
            excel_buffer.seek(0)
            st.download_button(
                label="📊 Download Excel Report",
                data=excel_buffer,
                file_name=f"income_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col_exp3:
            st.write("")
        
        st.markdown("---")
        
        # Display records
        for record in records:
            record_id, bus_num, route_name, hire_dest, driver, conductor, date_str, amt, notes_text, created_by = record
            
            # Format route display
            route_display = route_name
            if route_name == "Hire" and hire_dest:
                route_display = f"Hire: {hire_dest}"
            
            with st.expander(f"🚌 {bus_num} - {route_display} | ${amt:,.2f} | {date_str}"):
                col_a, col_b = st.columns([3, 1])
                
                with col_a:
                    st.write(f"**Bus:** {bus_num}")
                    st.write(f"**Route:** {route_display}")
                    st.write(f"**Driver:** {driver or 'N/A'}")
                    st.write(f"**Conductor:** {conductor or 'N/A'}")
                    st.write(f"**Amount:** ${amt:,.2f}")
                    st.write(f"**Date:** {date_str}")
                    if notes_text:
                        st.write(f"**Notes:** {notes_text}")
                    st.caption(f"Created by: {created_by}")
                
                with col_b:
                    # Edit button
                    if st.button("✏️ Edit", key=f"edit_{record_id}"):
                        st.session_state[f'edit_mode_{record_id}'] = True
                        st.rerun()
                    
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_{record_id}"):
                        if st.session_state.get(f'confirm_delete_{record_id}', False):
                            conn = sqlite3.connect('bus_management.db')
                            cursor = conn.cursor()
                            cursor.execute('DELETE FROM income WHERE id = ?', (record_id,))
                            conn.commit()
                            conn.close()
                            
                            # ✅ AUTOMATIC AUDIT LOGGING
                            AuditLogger.log_income_delete(
                                record_id=record_id,
                                bus_number=bus_num,
                                date=date_str
                            )
                            
                            st.success("Record deleted")
                            st.rerun()
                        else:
                            st.session_state[f'confirm_delete_{record_id}'] = True
                            st.warning("Click again to confirm")
                
                # Edit mode
                if st.session_state.get(f'edit_mode_{record_id}', False):
                    st.markdown("---")
                    st.markdown("**Edit Record:**")
                    
                    with st.form(f"edit_form_{record_id}"):
                        edit_col1, edit_col2 = st.columns(2)
                        
                        with edit_col1:
                            # Bus dropdown for editing - UPDATED: Show registration_number first
                            edit_buses = get_active_buses()
                            edit_bus_options = []
                            for bus in edit_buses:
                                reg_num = bus['registration_number'] if 'registration_number' in bus.keys() and bus['registration_number'] else 'No Reg'
                                edit_bus_options.append(f"{reg_num} - {bus['bus_number']} ({bus['model']})")
                            
                            current_bus_idx = next((i for i, opt in enumerate(edit_bus_options) if bus_num in opt), 0)
                            edit_selected_bus = st.selectbox("Select Bus", edit_bus_options, index=current_bus_idx)
                            # Extract bus_number from selection
                            new_bus = edit_selected_bus.split(" - ")[1].split(" (")[0]
                            
                            # Route dropdown for editing
                            edit_routes = get_all_routes()
                            edit_route_options = ["Hire"] + [r['name'] for r in edit_routes]
                            current_route_idx = edit_route_options.index(route_name) if route_name in edit_route_options else 0
                            edit_selected_route = st.selectbox("Route", edit_route_options, index=current_route_idx)
                            
                            # Hire destination if Hire is selected
                            new_hire_dest = ""
                            if edit_selected_route == "Hire":
                                new_hire_dest = st.text_input("Hire Destination", value=hire_dest or "")
                            
                            new_driver = st.text_input("Driver", value=driver or "")
                        
                        with edit_col2:
                            new_conductor = st.text_input("Conductor", value=conductor or "")
                            new_amount = st.number_input("Amount", value=float(amt))
                            new_date = st.date_input("Date", value=pd.to_datetime(date_str))
                        
                        new_notes = st.text_area("Notes", value=notes_text or "")
                        
                        col_save, col_cancel = st.columns(2)
                        
                        with col_save:
                            save_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)
                        
                        with col_cancel:
                            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
                        
                        if save_btn:
                            # Validate hire destination
                            if edit_selected_route == "Hire" and not new_hire_dest.strip():
                                st.error("⚠️ Please describe the hire destination")
                            else:
                                old_values = {
                                    'bus_number': bus_num,
                                    'route': route_name,
                                    'hire_destination': hire_dest,
                                    'driver_name': driver,
                                    'conductor_name': conductor,
                                    'amount': amt,
                                    'date': date_str,
                                    'notes': notes_text
                                }
                                
                                new_values = {
                                    'bus_number': new_bus,
                                    'route': edit_selected_route,
                                    'hire_destination': new_hire_dest if edit_selected_route == "Hire" else None,
                                    'driver_name': new_driver,
                                    'conductor_name': new_conductor,
                                    'amount': new_amount,
                                    'date': new_date.strftime("%Y-%m-%d"),
                                    'notes': new_notes
                                }
                                
                                conn = sqlite3.connect('bus_management.db')
                                cursor = conn.cursor()
                                
                                cursor.execute('''
                                    UPDATE income
                                    SET bus_number = ?, route = ?, hire_destination = ?, driver_name = ?, 
                                        conductor_name = ?, amount = ?, date = ?, notes = ?
                                    WHERE id = ?
                                ''', (new_bus, edit_selected_route, new_values['hire_destination'], 
                                      new_driver, new_conductor, new_amount,
                                      new_date.strftime("%Y-%m-%d"), new_notes, record_id))
                                
                                conn.commit()
                                conn.close()
                                
                                # ✅ AUTOMATIC AUDIT LOGGING
                                AuditLogger.log_income_edit(
                                    record_id=record_id,
                                    bus_number=new_bus,
                                    old_data=old_values,
                                    new_data=new_values
                                )
                                
                                st.success("✅ Record updated successfully!")
                                st.session_state[f'edit_mode_{record_id}'] = False
                                st.rerun()
                        
                        if cancel_btn:
                            st.session_state[f'edit_mode_{record_id}'] = False
                            st.rerun()
    else:
        st.info("No income records found. Add your first record above!")


# ============================================================================
# MAINTENANCE ENTRY PAGE
# ============================================================================

def maintenance_entry_page():
    """Maintenance entry page with automatic audit logging"""
    
    st.header("🔧 Maintenance Entry")
    st.markdown("Record bus maintenance and repairs")
    st.markdown("---")
    
    # Get active buses for dropdown
    buses = get_active_buses()
    
    # Add Maintenance Form
    with st.form("maintenance_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            if buses:
                # Bus dropdown - UPDATED: Show registration_number first
                bus_options = []
                for bus in buses:
                    reg_num = bus['registration_number'] if 'registration_number' in bus.keys() and bus['registration_number'] else 'No Reg'
                    bus_options.append(f"{reg_num} - {bus['bus_number']} ({bus['model']})")
                
                selected_bus = st.selectbox("🚌 Select Bus*", bus_options)
                # Extract bus_number from selection
                bus_number = selected_bus.split(" - ")[1].split(" (")[0]
            else:
                bus_number = st.text_input("🚌 Bus Number*", placeholder="e.g., Bus 1")
            
            maintenance_type = st.selectbox(
                "🔧 Maintenance Type*",
                ["Oil Change", "Tire Replacement", "Brake Service", 
                 "Engine Repair", "Body Work", "Electrical", "Transmission", "Other"]
            )
            mechanic_name = st.text_input("👨‍🔧 Mechanic Name", placeholder="e.g., Mike Smith")
        
        with col2:
            date = st.date_input("📅 Date*", datetime.now())
            cost = st.number_input("💰 Cost*", min_value=0.0, step=0.01, format="%.2f")
            status = st.selectbox("📊 Status", ["Completed", "In Progress", "Scheduled"])
        
        description = st.text_area("📝 Description", placeholder="Details of maintenance work...")
        parts_used = st.text_area("📦 Parts Used", placeholder="List of parts and quantities...")
        
        submitted = st.form_submit_button("➕ Add Maintenance Record", use_container_width=True, type="primary")
        
        if submitted:
            if not all([bus_number, maintenance_type, cost >= 0]):
                st.error("⚠️ Please fill in all required fields")
            else:
                conn = sqlite3.connect('bus_management.db')
                cursor = conn.cursor()
                
                try:
                    cursor.execute('''
                        INSERT INTO maintenance 
                        (bus_number, maintenance_type, mechanic_name, date, cost, 
                         status, description, parts_used, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        bus_number,
                        maintenance_type,
                        mechanic_name,
                        date.strftime("%Y-%m-%d"),
                        cost,
                        status,
                        description,
                        parts_used,
                        st.session_state['user']['username']
                    ))
                    
                    record_id = cursor.lastrowid
                    conn.commit()
                    
                    # ✅ AUTOMATIC AUDIT LOGGING
                    AuditLogger.log_maintenance_add(
                        bus_number=bus_number,
                        maintenance_type=maintenance_type,
                        cost=cost,
                        date=date.strftime("%Y-%m-%d")
                    )
                    
                    st.success(f"✅ Maintenance record added successfully! (ID: {record_id})")
                    st.balloons()
                    
                except sqlite3.Error as e:
                    st.error(f"❌ Database error: {e}")
                finally:
                    conn.close()
    
    st.markdown("---")
    
    # Recent Maintenance Records
    st.subheader("📋 Recent Maintenance Records")
    
    # Filter options
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        filter_bus = st.text_input("🔍 Filter by Bus", placeholder="Leave empty for all", key="maint_filter_bus")
    
    with col_filter2:
        filter_type = st.selectbox("🔧 Maintenance Type", 
                                   ["All"] + ["Oil Change", "Tire Replacement", "Brake Service", 
                                              "Engine Repair", "Body Work", "Electrical", "Transmission", "Other"])
    
    with col_filter3:
        days_back = st.selectbox("📅 Show last", [7, 30, 90, 365], index=1, key="maint_days_back")
    
    conn = sqlite3.connect('bus_management.db')
    cursor = conn.cursor()
    
    # Build query with filters
    query = '''
        SELECT id, bus_number, maintenance_type, mechanic_name, date, cost, 
               status, description, parts_used, created_by
        FROM maintenance
        WHERE date >= date('now', '-' || ? || ' days')
    '''
    params = [days_back]
    
    if filter_bus:
        query += " AND bus_number LIKE ?"
        params.append(f"%{filter_bus}%")
    
    if filter_type != "All":
        query += " AND maintenance_type = ?"
        params.append(filter_type)
    
    query += " ORDER BY date DESC, id DESC LIMIT 50"
    
    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()
    
    if records:
        # Summary stats
        total_cost = sum(record[5] for record in records)
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("📊 Total Records", len(records))
        with col_stat2:
            st.metric("💰 Total Cost", f"${total_cost:,.2f}")
        with col_stat3:
            avg_cost = total_cost / len(records) if records else 0
            st.metric("📈 Average Cost", f"${avg_cost:,.2f}")
        
        st.markdown("---")
        
        # Display records
        for record in records:
            record_id, bus_num, maint_type, mechanic, date_str, cost_amt, status_val, desc, parts, created_by = record
            
            status_icon = "✅" if status_val == "Completed" else "⏳" if status_val == "In Progress" else "📅"
            
            with st.expander(f"{status_icon} {bus_num} - {maint_type} | ${cost_amt:,.2f} | {date_str}"):
                col_a, col_b = st.columns([3, 1])
                
                with col_a:
                    st.write(f"**Bus:** {bus_num}")
                    st.write(f"**Type:** {maint_type}")
                    st.write(f"**Mechanic:** {mechanic or 'N/A'}")
                    st.write(f"**Cost:** ${cost_amt:,.2f}")
                    st.write(f"**Date:** {date_str}")
                    st.write(f"**Status:** {status_val}")
                    if desc:
                        st.write(f"**Description:** {desc}")
                    if parts:
                        st.write(f"**Parts Used:** {parts}")
                    st.caption(f"Created by: {created_by}")
                
                with col_b:
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_maint_{record_id}"):
                        if st.session_state.get(f'confirm_delete_maint_{record_id}', False):
                            conn = sqlite3.connect('bus_management.db')
                            cursor = conn.cursor()
                            cursor.execute('DELETE FROM maintenance WHERE id = ?', (record_id,))
                            conn.commit()
                            conn.close()
                            
                            # ✅ AUTOMATIC AUDIT LOGGING
                            AuditLogger.log_maintenance_delete(
                                record_id=record_id,
                                bus_number=bus_num,
                                date=date_str
                            )
                            
                            st.success("Record deleted")
                            st.rerun()
                        else:
                            st.session_state[f'confirm_delete_maint_{record_id}'] = True
                            st.warning("Click again to confirm")
    else:
        st.info("No maintenance records found. Add your first record above!")

def auto_create_driver_conductor(name, position, conn):
    """
    Auto-create driver or conductor if they don't exist
    Returns: employee_id (int) or None
    """
    cursor = conn.cursor()
    
    # Check if employee exists
    cursor.execute("""
        SELECT employee_id FROM employees 
        WHERE full_name = ? AND position LIKE ?
    """, (name, f"%{position}%"))
    
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Create new employee
    try:
        # Generate employee ID
        cursor.execute("""
            SELECT MAX(CAST(SUBSTR(employee_id, 4) AS INTEGER)) 
            FROM employees 
            WHERE employee_id LIKE ?
        """, (f"{position[:3].upper()}%",))
        
        max_num = cursor.fetchone()[0]
        new_num = (max_num or 0) + 1
        employee_id = f"{position[:3].upper()}{new_num:03d}"
        
        cursor.execute("""
            INSERT INTO employees 
            (employee_id, full_name, position, department, hire_date, salary, status, created_by)
            VALUES (?, ?, ?, 'Operations', date('now'), 0.0, 'Active', 'AUTO_IMPORT')
        """, (employee_id, name, position))
        
        conn.commit()
        return employee_id
    except:
        return None


def auto_create_assignment(bus_number, driver_name, conductor_name, date_str, route, conn):
    """
    Auto-create bus assignment from income entry
    Returns: True if successful, False otherwise
    """
    cursor = conn.cursor()
    
    try:
        # Get or create driver
        driver_id = auto_create_driver_conductor(driver_name, "Driver", conn)
        if not driver_id:
            return False
        
        # Get or create conductor
        conductor_id = auto_create_driver_conductor(conductor_name, "Conductor", conn)
        if not conductor_id:
            return False
        
        # Check if assignment already exists for this date and bus
        cursor.execute("""
            SELECT id FROM bus_assignments 
            WHERE bus_number = ? AND assignment_date = ?
        """, (bus_number, date_str))
        
        if cursor.fetchone():
            # Update existing assignment
            cursor.execute("""
                UPDATE bus_assignments 
                SET driver_id = (SELECT id FROM drivers WHERE name = ?),
                    conductor_id = (SELECT id FROM conductors WHERE name = ?),
                    route = ?
                WHERE bus_number = ? AND assignment_date = ?
            """, (driver_name, conductor_name, route, bus_number, date_str))
        else:
            # Get driver and conductor IDs from drivers/conductors tables
            cursor.execute("SELECT id FROM drivers WHERE name = ?", (driver_name,))
            driver_table_id = cursor.fetchone()
            
            cursor.execute("SELECT id FROM conductors WHERE name = ?", (conductor_name,))
            conductor_table_id = cursor.fetchone()
            
            # Create new assignment
            cursor.execute("""
                INSERT INTO bus_assignments 
                (bus_number, driver_id, conductor_id, assignment_date, shift, route, notes, created_at)
                VALUES (?, ?, ?, ?, 'Full Day', ?, 'Auto-created from income import', CURRENT_TIMESTAMP)
            """, (bus_number, 
                 driver_table_id[0] if driver_table_id else None,
                 conductor_table_id[0] if conductor_table_id else None,
                 date_str, route))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating assignment: {e}")
        return False


"""
REPLACE the import_data_page() function with this enhanced version
that includes auto-assignment creation
"""

def import_data_page():
    """Import data from Excel files with AUTO-ASSIGNMENT feature"""
    
    st.header("📥 Import from Excel")
    st.markdown("Bulk import income and maintenance records")
    st.markdown("---")
    
    # 🆕 Feature highlight
    st.info("✨ **NEW:** When importing income data, assignments are automatically created for drivers and conductors!")
    
    # Instructions
    with st.expander("📖 Instructions", expanded=True):
        st.markdown("""
        ### How to Import Data:
        
        1. **Download the template** below for the type of data you want to import
        2. **Fill in your data** in the Excel file
        3. **Upload the file** using the upload button
        4. **Review the preview** and click Import
        
        ### 🆕 Auto-Assignment Feature (Income Import):
        - Automatically creates bus assignments from income entries
        - Creates missing drivers/conductors if needed
        - Links bus + driver + conductor + date
        - Shows summary of auto-created assignments
        
        ### Required Columns:
        
        **Income Data:**
        - bus_number, route, driver_name, conductor_name, date, amount
        - Optional: hire_destination (required if route = "Hire"), notes
        
        **Maintenance Data:**
        - bus_number, maintenance_type, mechanic_name, date, cost, status, description, parts_used
        
        **Date Format:** YYYY-MM-DD (e.g., 2025-10-15)
        """)
    
    # Download templates
    st.subheader("📄 Download Templates")
    
    col_temp1, col_temp2 = st.columns(2)
    
    with col_temp1:
        income_template = pd.DataFrame({
            'bus_number': ['PAV-07', 'PAV-08', 'PAV-09'],
            'route': ['Harare-Mutare', 'Hire', 'Harare-Bulawayo'],
            'hire_destination': ['', 'Wedding at Lake Chivero', ''],
            'driver_name': ['John Doe', 'Jane Smith', 'Bob Wilson'],
            'conductor_name': ['Mike Johnson', 'Sarah Williams', 'Tom Brown'],
            'date': ['2025-10-15', '2025-10-15', '2025-10-15'],
            'amount': [500.00, 1200.00, 450.00],
            'notes': ['Regular run', 'Private hire', 'Express service']
        })
        
        csv_income = income_template.to_csv(index=False)
        st.download_button(
            label="📊 Download Income Template",
            data=csv_income,
            file_name="income_template.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_temp2:
        maint_template = pd.DataFrame({
            'bus_number': ['PAV-07', 'PAV-08'],
            'maintenance_type': ['Oil Change', 'Tire Replacement'],
            'mechanic_name': ['Mike Smith', 'Tom Brown'],
            'date': ['2025-10-15', '2025-10-15'],
            'cost': [50.00, 200.00],
            'status': ['Completed', 'Completed'],
            'description': ['Regular oil change', 'Replaced front tires'],
            'parts_used': ['Oil filter, 5L oil', '2x Front tires']
        })
        
        csv_maint = maint_template.to_csv(index=False)
        st.download_button(
            label="🔧 Download Maintenance Template",
            data=csv_maint,
            file_name="maintenance_template.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # Import section
    st.subheader("📤 Upload and Import")
    
    import_type = st.radio("Select import type:", ["💰 Income Data", "🔧 Maintenance Data"], horizontal=True)
    
    # 🆕 Auto-assignment toggle for income imports
    auto_assign = False
    if import_type == "💰 Income Data":
        auto_assign = st.checkbox("🤖 Auto-create bus assignments", value=True,
                                  help="Automatically create assignments for drivers and conductors from income data")
    
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="Upload your data file (CSV or Excel format)"
    )
    
    if uploaded_file is not None:
        try:
            # Read file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ File loaded successfully! Found {len(df)} records.")
            
            # Preview data
            st.subheader("👀 Data Preview")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Validation
            st.subheader("✓ Validation")
            
            if import_type == "💰 Income Data":
                required_cols = ['bus_number', 'route', 'driver_name', 'conductor_name', 'date', 'amount']
                optional_cols = ['hire_destination', 'notes']
            else:  # Maintenance
                required_cols = ['bus_number', 'maintenance_type', 'date', 'cost']
                optional_cols = ['mechanic_name', 'status', 'description', 'parts_used']
            
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
            else:
                st.success(f"✅ All required columns present")
                
                # Fill optional columns with defaults
                for col in optional_cols:
                    if col not in df.columns:
                        if col == 'status':
                            df[col] = 'Completed'
                        else:
                            df[col] = ''
                
                # Import button
                if st.button("🚀 Import Data", type="primary", use_container_width=True):
                    conn = sqlite3.connect('bus_management.db')
                    cursor = conn.cursor()
                    
                    success_count = 0
                    error_count = 0
                    errors = []
                    
                    # 🆕 Assignment tracking
                    assignments_created = 0
                    drivers_created = 0
                    conductors_created = 0
                    
                    with st.spinner("Importing data..."):
                        for idx, row in df.iterrows():
                            try:
                                if import_type == "💰 Income Data":
                                    # Validate hire destination for Hire routes
                                    if row['route'] == 'Hire' and not str(row.get('hire_destination', '')).strip():
                                        raise ValueError("Hire destination required for Hire routes")
                                    
                                    cursor.execute('''
                                        INSERT INTO income 
                                        (bus_number, route, hire_destination, driver_name, conductor_name, 
                                         date, amount, notes, created_by)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        row['bus_number'],
                                        row['route'],
                                        row.get('hire_destination', ''),
                                        row['driver_name'],
                                        row['conductor_name'],
                                        row['date'],
                                        row['amount'],
                                        row.get('notes', ''),
                                        st.session_state['user']['username']
                                    ))
                                    
                                    # 🆕 AUTO-CREATE ASSIGNMENT
                                    if auto_assign:
                                        # Check if driver/conductor were newly created
                                        cursor.execute("""
                                            SELECT COUNT(*) FROM employees 
                                            WHERE full_name = ? AND created_by = 'AUTO_IMPORT'
                                        """, (row['driver_name'],))
                                        if cursor.fetchone()[0] > 0:
                                            drivers_created += 1
                                        
                                        cursor.execute("""
                                            SELECT COUNT(*) FROM employees 
                                            WHERE full_name = ? AND created_by = 'AUTO_IMPORT'
                                        """, (row['conductor_name'],))
                                        if cursor.fetchone()[0] > 0:
                                            conductors_created += 1
                                        
                                        # Create assignment
                                        if auto_create_assignment(
                                            row['bus_number'],
                                            row['driver_name'],
                                            row['conductor_name'],
                                            row['date'],
                                            row['route'],
                                            conn
                                        ):
                                            assignments_created += 1
                                
                                else:  # Maintenance
                                    cursor.execute('''
                                        INSERT INTO maintenance
                                        (bus_number, maintenance_type, mechanic_name, date, cost, 
                                         status, description, parts_used, created_by)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        row['bus_number'],
                                        row['maintenance_type'],
                                        row.get('mechanic_name', ''),
                                        row['date'],
                                        row['cost'],
                                        row.get('status', 'Completed'),
                                        row.get('description', ''),
                                        row.get('parts_used', ''),
                                        st.session_state['user']['username']
                                    ))
                                
                                success_count += 1
                                
                            except Exception as e:
                                error_count += 1
                                errors.append(f"Row {idx + 1}: {str(e)}")
                        
                        conn.commit()
                        conn.close()
                    
                    # Audit logging
                    module = "Income" if import_type == "💰 Income Data" else "Maintenance"
                    AuditLogger.log_data_import(
                        module=module,
                        record_count=success_count,
                        file_name=uploaded_file.name
                    )
                    
                    # Results
                    st.markdown("---")
                    st.subheader("📊 Import Results")
                    
                    col_res1, col_res2, col_res3 = st.columns(3)
                    with col_res1:
                        st.metric("✅ Successful", success_count)
                    with col_res2:
                        st.metric("❌ Errors", error_count)
                    with col_res3:
                        st.metric("📊 Total", len(df))
                    
                    # 🆕 Auto-assignment results
                    if import_type == "💰 Income Data" and auto_assign:
                        st.markdown("---")
                        st.subheader("🤖 Auto-Assignment Results")
                        
                        col_auto1, col_auto2, col_auto3 = st.columns(3)
                        with col_auto1:
                            st.metric("📅 Assignments Created", assignments_created)
                        with col_auto2:
                            st.metric("👨‍✈️ New Drivers Added", drivers_created)
                        with col_auto3:
                            st.metric("👨‍💼 New Conductors Added", conductors_created)
                        
                        if assignments_created > 0:
                            st.success(f"🎉 Automatically created {assignments_created} bus assignments!")
                        
                        if drivers_created > 0 or conductors_created > 0:
                            st.info(f"💡 Created {drivers_created} drivers and {conductors_created} conductors. Update their details in Employee Management.")
                    
                    if success_count > 0:
                        st.success(f"🎉 Successfully imported {success_count} records!")
                        st.balloons()
                    
                    if errors:
                        with st.expander("⚠️ View Errors"):
                            for error in errors[:10]:
                                st.error(error)
                            if len(errors) > 10:
                                st.warning(f"... and {len(errors) - 10} more errors")
        
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
            st.info("Please make sure your file is in the correct format (CSV or Excel)")


# ============================================================================
# IMPORT DATA PAGE - WITH HIRE SUPPORT
# ============================================================================

def import_data_page():
    """Import data from Excel files with hire support"""
    
    st.header("📥 Import from Excel")
    st.markdown("Bulk import income and maintenance records")
    st.markdown("---")
    
    # Instructions
    with st.expander("📖 Instructions", expanded=True):
        st.markdown("""
        ### How to Import Data:
        
        1. **Download the template** below for the type of data you want to import
        2. **Fill in your data** in the Excel file
        3. **Upload the file** using the upload button
        4. **Review the preview** and click Import
        
        ### Required Columns:
        
        **Income Data:**
        - bus_number, route, driver_name, conductor_name, date, amount
        - Optional: hire_destination (required if route = "Hire"), notes
        
        **Maintenance Data:**
        - bus_number, maintenance_type, mechanic_name, date, cost, status, description, parts_used
        
        **Date Format:** YYYY-MM-DD (e.g., 2025-10-15)
        """)
    
    # Download templates
    st.subheader("📄 Download Templates")
    
    col_temp1, col_temp2 = st.columns(2)
    
    with col_temp1:
        # Income template with hire support
        income_template = pd.DataFrame({
            'bus_number': ['PAV-07', 'PAV-08', 'PAV-09'],
            'route': ['Harare-Mutare', 'Hire', 'Harare-Bulawayo'],
            'hire_destination': ['', 'Wedding at Lake Chivero', ''],
            'driver_name': ['John Doe', 'Jane Smith', 'Bob Wilson'],
            'conductor_name': ['Mike Johnson', 'Sarah Williams', 'Tom Brown'],
            'date': ['2025-10-15', '2025-10-15', '2025-10-15'],
            'amount': [500.00, 1200.00, 450.00],
            'notes': ['Regular run', 'Private hire', 'Express service']
        })
        
        csv_income = income_template.to_csv(index=False)
        st.download_button(
            label="📊 Download Income Template",
            data=csv_income,
            file_name="income_template.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_temp2:
        # Maintenance template
        maint_template = pd.DataFrame({
            'bus_number': ['PAV-07', 'PAV-08'],
            'maintenance_type': ['Oil Change', 'Tire Replacement'],
            'mechanic_name': ['Mike Smith', 'Tom Brown'],
            'date': ['2025-10-15', '2025-10-15'],
            'cost': [50.00, 200.00],
            'status': ['Completed', 'Completed'],
            'description': ['Regular oil change', 'Replaced front tires'],
            'parts_used': ['Oil filter, 5L oil', '2x Front tires']
        })
        
        csv_maint = maint_template.to_csv(index=False)
        st.download_button(
            label="🔧 Download Maintenance Template",
            data=csv_maint,
            file_name="maintenance_template.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # Import section
    st.subheader("📤 Upload and Import")
    
    import_type = st.radio("Select import type:", ["💰 Income Data", "🔧 Maintenance Data"], horizontal=True)
    
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=['csv', 'xlsx', 'xls'],
        help="Upload your data file (CSV or Excel format)"
    )
    
    if uploaded_file is not None:
        try:
            # Read file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ File loaded successfully! Found {len(df)} records.")
            
            # Preview data
            st.subheader("👀 Data Preview")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Validation
            st.subheader("✓ Validation")
            
            if import_type == "💰 Income Data":
                required_cols = ['bus_number', 'route', 'driver_name', 'conductor_name', 'date', 'amount']
                optional_cols = ['hire_destination', 'notes']
            else:  # Maintenance
                required_cols = ['bus_number', 'maintenance_type', 'date', 'cost']
                optional_cols = ['mechanic_name', 'status', 'description', 'parts_used']
            
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
            else:
                st.success(f"✅ All required columns present")
                
                # Fill optional columns with defaults
                for col in optional_cols:
                    if col not in df.columns:
                        if col == 'status':
                            df[col] = 'Completed'
                        else:
                            df[col] = ''
                
                # Import button
                if st.button("🚀 Import Data", type="primary", use_container_width=True):
                    conn = sqlite3.connect('bus_management.db')
                    cursor = conn.cursor()
                    
                    success_count = 0
                    error_count = 0
                    errors = []
                    
                    with st.spinner("Importing data..."):
                        for idx, row in df.iterrows():
                            try:
                                if import_type == "💰 Income Data":
                                    # Validate hire destination for Hire routes
                                    if row['route'] == 'Hire' and not str(row.get('hire_destination', '')).strip():
                                        raise ValueError("Hire destination required for Hire routes")
                                    
                                    cursor.execute('''
                                        INSERT INTO income 
                                        (bus_number, route, hire_destination, driver_name, conductor_name, 
                                         date, amount, notes, created_by)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        row['bus_number'],
                                        row['route'],
                                        row.get('hire_destination', ''),
                                        row['driver_name'],
                                        row['conductor_name'],
                                        row['date'],
                                        row['amount'],
                                        row.get('notes', ''),
                                        st.session_state['user']['username']
                                    ))
                                else:  # Maintenance
                                    cursor.execute('''
                                        INSERT INTO maintenance
                                        (bus_number, maintenance_type, mechanic_name, date, cost, 
                                         status, description, parts_used, created_by)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ''', (
                                        row['bus_number'],
                                        row['maintenance_type'],
                                        row.get('mechanic_name', ''),
                                        row['date'],
                                        row['cost'],
                                        row.get('status', 'Completed'),
                                        row.get('description', ''),
                                        row.get('parts_used', ''),
                                        st.session_state['user']['username']
                                    ))
                                
                                success_count += 1
                                
                            except Exception as e:
                                error_count += 1
                                errors.append(f"Row {idx + 1}: {str(e)}")
                        
                        conn.commit()
                        conn.close()
                    
                    # ✅ AUTOMATIC AUDIT LOGGING
                    module = "Income" if import_type == "💰 Income Data" else "Maintenance"
                    AuditLogger.log_data_import(
                        module=module,
                        record_count=success_count,
                        file_name=uploaded_file.name
                    )
                    
                    # Results
                    st.markdown("---")
                    st.subheader("📊 Import Results")
                    
                    col_res1, col_res2, col_res3 = st.columns(3)
                    with col_res1:
                        st.metric("✅ Successful", success_count)
                    with col_res2:
                        st.metric("❌ Errors", error_count)
                    with col_res3:
                        st.metric("📊 Total", len(df))
                    
                    if success_count > 0:
                        st.success(f"🎉 Successfully imported {success_count} records!")
                        st.balloons()
                    
                    if errors:
                        with st.expander("⚠️ View Errors"):
                            for error in errors[:10]:  # Show first 10 errors
                                st.error(error)
                            if len(errors) > 10:
                                st.warning(f"... and {len(errors) - 10} more errors")
        
        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
            st.info("Please make sure your file is in the correct format (CSV or Excel)")


# ============================================================================
# REVENUE HISTORY PAGE - WITH HIRE ROUTE GROUPING
# ============================================================================

def revenue_history_page():
    """View and analyze revenue history with hire support"""
    
    st.header("💰 Revenue History")
    st.markdown("View and analyze income and maintenance records")
    st.markdown("---")
    
    # Date range selector
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", datetime.now())
    with col3:
        view_type = st.selectbox("View", ["📊 Income", "🔧 Maintenance", "📈 Combined"])
    
    # Additional filters for income
    if view_type in ["📊 Income", "📈 Combined"]:
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            filter_bus = st.text_input("🔍 Filter by Bus", placeholder="Leave empty for all")
        with col_f2:
            filter_driver = st.text_input("🔍 Filter by Driver", placeholder="Leave empty for all")
        with col_f3:
            filter_conductor = st.text_input("🔍 Filter by Conductor", placeholder="Leave empty for all")
    
    # Fetch data
    conn = sqlite3.connect('bus_management.db')
    
    if view_type in ["📊 Income", "📈 Combined"]:
        query = "SELECT * FROM income WHERE date BETWEEN ? AND ?"
        params = [start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]
        
        if filter_bus:
            query += " AND bus_number LIKE ?"
            params.append(f"%{filter_bus}%")
        if filter_driver:
            query += " AND driver_name LIKE ?"
            params.append(f"%{filter_driver}%")
        if filter_conductor:
            query += " AND conductor_name LIKE ?"
            params.append(f"%{filter_conductor}%")
        
        query += " ORDER BY date DESC"
        
        income_df = pd.read_sql_query(query, conn, params=params)
    else:
        income_df = pd.DataFrame()
    
    if view_type in ["🔧 Maintenance", "📈 Combined"]:
        maint_df = pd.read_sql_query(
            "SELECT * FROM maintenance WHERE date BETWEEN ? AND ? ORDER BY date DESC",
            conn,
            params=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        )
    else:
        maint_df = pd.DataFrame()
    
    conn.close()
    
    # Display based on view type
    if view_type == "📊 Income":
        if not income_df.empty:
            total = income_df['amount'].sum()
            count = len(income_df)
            avg = income_df['amount'].mean()
            
            col_met1, col_met2, col_met3 = st.columns(3)
            with col_met1:
                st.metric("💰 Total Revenue", f"${total:,.2f}")
            with col_met2:
                st.metric("📊 Number of Records", count)
            with col_met3:
                st.metric("📈 Average per Record", f"${avg:,.2f}")
            
            st.markdown("---")
            
            # Export buttons
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                filters_dict = {}
                if filter_bus:
                    filters_dict['Bus'] = filter_bus
                if filter_driver:
                    filters_dict['Driver'] = filter_driver
                if filter_conductor:
                    filters_dict['Conductor'] = filter_conductor
                
                pdf_buffer = generate_income_pdf(income_df, filters_dict, st.session_state['user']['full_name'])
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_buffer,
                    file_name=f"income_history_{start_date}_{end_date}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col_exp2:
                excel_buffer = io.BytesIO()
                income_df.to_excel(excel_buffer, sheet_name='Income', index=False)
                excel_buffer.seek(0)
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_buffer,
                    file_name=f"income_history_{start_date}_{end_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            with col_exp3:
                csv = income_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"income_history_{start_date}_{end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            st.markdown("---")
            st.dataframe(income_df, use_container_width=True)
        else:
            st.info("No income records found for this period")
    
    elif view_type == "🔧 Maintenance":
        if not maint_df.empty:
            total = maint_df['cost'].sum()
            count = len(maint_df)
            avg = maint_df['cost'].mean()
            
            col_met1, col_met2, col_met3 = st.columns(3)
            with col_met1:
                st.metric("💰 Total Cost", f"${total:,.2f}")
            with col_met2:
                st.metric("🔧 Maintenance Events", count)
            with col_met3:
                st.metric("📈 Average Cost", f"${avg:,.2f}")
            
            st.markdown("---")
            st.dataframe(maint_df, use_container_width=True)
            
            # Export button
            csv = maint_df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                f"maintenance_history_{start_date}_{end_date}.csv",
                "text/csv"
            )
        else:
            st.info("No maintenance records found for this period")
    
    else:  # Combined view
        total_income = income_df['amount'].sum() if not income_df.empty else 0
        total_maint = maint_df['cost'].sum() if not maint_df.empty else 0
        net_profit = total_income - total_maint
        
        col_met1, col_met2, col_met3, col_met4 = st.columns(4)
        with col_met1:
            st.metric("💰 Revenue", f"${total_income:,.2f}")
        with col_met2:
            st.metric("🔧 Expenses", f"${total_maint:,.2f}")
        with col_met3:
            profit_delta = f"{(net_profit/total_income*100):.1f}%" if total_income > 0 else "0%"
            st.metric("💵 Profit", f"${net_profit:,.2f}", delta=profit_delta)
        with col_met4:
            margin = (net_profit / total_income * 100) if total_income > 0 else 0
            st.metric("📊 Margin", f"{margin:.1f}%")
        
        st.markdown("---")
        
        # Tabs for income and maintenance
        tab1, tab2 = st.tabs(["💰 Income Records", "🔧 Maintenance Records"])
        
        with tab1:
            if not income_df.empty:
                st.dataframe(income_df, use_container_width=True)
            else:
                st.info("No income records")
        
        with tab2:
            if not maint_df.empty:
                st.dataframe(maint_df, use_container_width=True)
            else:
                st.info("No maintenance records")


# ============================================================================
# DASHBOARD PAGE - WITH HIRE ROUTE ANALYSIS
# ============================================================================

def dashboard_page():
    """Main operations dashboard with charts and KPIs"""
    
    st.header("📈 Operations Dashboard")
    st.markdown("Real-time business intelligence and analytics")
    st.markdown("---")
    
    # Date range
    col1, col2 = st.columns(2)
    with col1:
        days_back = st.selectbox("Time Period", [7, 30, 90, 365], index=1)
    with col2:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        st.info(f"📅 {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Fetch data
    conn = sqlite3.connect('bus_management.db')
    
    income_df = pd.read_sql_query(
        "SELECT * FROM income WHERE date >= date('now', '-' || ? || ' days')",
        conn, params=(days_back,)
    )
    
    maint_df = pd.read_sql_query(
        "SELECT * FROM maintenance WHERE date >= date('now', '-' || ? || ' days')",
        conn, params=(days_back,)
    )
    
    conn.close()
    
    # KPIs
    total_revenue = income_df['amount'].sum() if not income_df.empty else 0
    total_expenses = maint_df['cost'].sum() if not maint_df.empty else 0
    net_profit = total_revenue - total_expenses
    num_records = len(income_df)
    num_buses = income_df['bus_number'].nunique() if not income_df.empty else 0
    
    col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
    
    with col_kpi1:
        st.metric("💰 Revenue", f"${total_revenue:,.2f}")
    with col_kpi2:
        st.metric("🔧 Expenses", f"${total_expenses:,.2f}")
    with col_kpi3:
        st.metric("💵 Profit", f"${net_profit:,.2f}")
    with col_kpi4:
        st.metric("🚌 Records", num_records)
    with col_kpi5:
        st.metric("🚗 Active Buses", num_buses)
    
    st.markdown("---")
    
    # Charts
    if not income_df.empty or not maint_df.empty:
        
        # Revenue vs Expenses Chart
        st.subheader("📊 Revenue vs Expenses Trend")
        
        if not income_df.empty:
            income_daily = income_df.groupby('date')['amount'].sum().reset_index()
            income_daily.columns = ['date', 'revenue']
        else:
            income_daily = pd.DataFrame(columns=['date', 'revenue'])
        
        if not maint_df.empty:
            maint_daily = maint_df.groupby('date')['cost'].sum().reset_index()
            maint_daily.columns = ['date', 'expenses']
        else:
            maint_daily = pd.DataFrame(columns=['date', 'expenses'])
        
        if not income_daily.empty or not maint_daily.empty:
            combined = pd.merge(income_daily, maint_daily, on='date', how='outer').fillna(0)
            combined['profit'] = combined['revenue'] - combined['expenses']
            combined = combined.sort_values('date')
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=combined['date'],
                y=combined['revenue'],
                mode='lines+markers',
                name='Revenue',
                line=dict(color='green', width=3)
            ))
            
            fig.add_trace(go.Scatter(
                x=combined['date'],
                y=combined['expenses'],
                mode='lines+markers',
                name='Expenses',
                line=dict(color='red', width=3)
            ))
            
            fig.update_layout(
                xaxis_title='Date',
                yaxis_title='Amount ($)',
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Two columns for additional charts
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            # Top buses by revenue
            if not income_df.empty:
                st.subheader("🏆 Top Buses by Revenue")
                top_buses = income_df.groupby('bus_number')['amount'].sum().sort_values(ascending=False).head(10)
                
                fig_buses = px.bar(
                    x=top_buses.values,
                    y=top_buses.index,
                    orientation='h',
                    labels={'x': 'Revenue ($)', 'y': 'Bus Number'}
                )
                fig_buses.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_buses, use_container_width=True)
        
        with col_chart2:
            # Maintenance by type
            if not maint_df.empty:
                st.subheader("🔧 Maintenance by Type")
                maint_types = maint_df.groupby('maintenance_type')['cost'].sum().sort_values(ascending=False)
                
                fig_maint = px.pie(
                    values=maint_types.values,
                    names=maint_types.index,
                    hole=0.4
                )
                fig_maint.update_layout(height=400)
                st.plotly_chart(fig_maint, use_container_width=True)
        
        st.markdown("---")
        
        # Driver and Conductor performance
        if not income_df.empty:
            col_perf1, col_perf2 = st.columns(2)
            
            with col_perf1:
                if 'driver_name' in income_df.columns:
                    st.subheader("👨‍✈️ Top Drivers by Revenue")
                    driver_perf = income_df.groupby('driver_name')['amount'].sum().sort_values(ascending=False).head(5)
                    st.dataframe(driver_perf, use_container_width=True)
            
            with col_perf2:
                if 'conductor_name' in income_df.columns:
                    st.subheader("👨‍💼 Top Conductors by Revenue")
                    conductor_perf = income_df.groupby('conductor_name')['amount'].sum().sort_values(ascending=False).head(5)
                    st.dataframe(conductor_perf, use_container_width=True)
        
        st.markdown("---")
        
        # Route analysis - WITH HIRE GROUPING
        if not income_df.empty and 'route' in income_df.columns:
            st.subheader("🛣️ Route Performance")
            
            # Group all hire entries under "Hire"
            route_analysis = income_df.groupby('route').agg({
                'amount': ['sum', 'count', 'mean']
            }).round(2)
            
            route_analysis.columns = ['Total Revenue', 'Number of Trips', 'Avg per Trip']
            route_analysis = route_analysis.sort_values('Total Revenue', ascending=False)
            
            st.dataframe(route_analysis, use_container_width=True)
            
            # Show hire destinations breakdown if there are hire records
            hire_records = income_df[income_df['route'] == 'Hire']
            if not hire_records.empty:
                with st.expander("🚐 View Hire Destinations Details"):
                    st.markdown("**Individual Hire Jobs:**")
                    hire_details = hire_records[['date', 'bus_number', 'hire_destination', 'amount']].sort_values('date', ascending=False)
                    st.dataframe(hire_details, use_container_width=True)
    
    else:
        st.info("🔭 No data available for the selected period. Start adding records to see your dashboard!")
    
    # Log dashboard view
    AuditLogger.log_action(
        action_type="View",
        module="Dashboard",
        description=f"Viewed operations dashboard for last {days_back} days"
    )