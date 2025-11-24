"""
pages_hr.py - Complete HR Management Module with Audit Logging and PDF/EXCEL EXPORT
Includes: Employee Management, Performance, Payroll, Leave, Disciplinary
"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from audit_logger import AuditLogger
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import io

# ============================================================================
# PDF GENERATION HELPER FOR HR REPORTS
# ============================================================================

def generate_hr_pdf(data_df, report_title, filters, username):
    """Generate PDF report for HR data"""
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
    elements.append(Paragraph(report_title, title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    report_date = datetime.now().strftime("%B %d, %Y at %H:%M")
    metadata = f"Generated: {report_date} | By: {username}"
    elements.append(Paragraph(metadata, subtitle_style))
    elements.append(Spacer(1, 0.3*inch))
    
    if filters:
        filter_text = "Filters: " + ", ".join([f"{k}: {v}" for k, v in filters.items()])
        elements.append(Paragraph(filter_text, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
    
    if not data_df.empty:
        # Prepare table data based on report type
        if 'Employee' in report_title or 'employee_id' in data_df.columns:
            table_data = [['ID', 'Name', 'Position', 'Department', 'Status', 'Salary']]
            for _, row in data_df.iterrows():
                table_data.append([
                    str(row.get('employee_id', '')),
                    str(row.get('full_name', ''))[:20],
                    str(row.get('position', ''))[:15],
                    str(row.get('department', ''))[:12],
                    str(row.get('status', '')),
                    f"${row.get('salary', 0):,.0f}"
                ])
        elif 'Payroll' in report_title or 'pay_period' in data_df.columns:
            table_data = [['Employee', 'Period', 'Basic', 'Allow.', 'Deduc.', 'Net']]
            for _, row in data_df.iterrows():
                table_data.append([
                    str(row.get('full_name', ''))[:18],
                    str(row.get('pay_period', ''))[:10],
                    f"${row.get('basic_salary', 0):,.0f}",
                    f"${row.get('allowances', 0):,.0f}",
                    f"${row.get('deductions', 0):,.0f}",
                    f"${row.get('net_salary', 0):,.0f}"
                ])
        elif 'Leave' in report_title or 'leave_type' in data_df.columns:
            table_data = [['Employee', 'Type', 'Start', 'End', 'Status']]
            for _, row in data_df.iterrows():
                table_data.append([
                    str(row.get('full_name', ''))[:18],
                    str(row.get('leave_type', ''))[:12],
                    str(row.get('start_date', ''))[:10],
                    str(row.get('end_date', ''))[:10],
                    str(row.get('status', ''))
                ])
        elif 'Disciplinary' in report_title or 'action_type' in data_df.columns:
            table_data = [['Employee', 'Action', 'Date', 'Status']]
            for _, row in data_df.iterrows():
                table_data.append([
                    str(row.get('full_name', ''))[:20],
                    str(row.get('action_type', ''))[:15],
                    str(row.get('record_date', ''))[:10],
                    str(row.get('status', ''))
                ])
        else:  # Performance
            table_data = [['Employee', 'Period', 'Rating', 'Evaluator']]
            for _, row in data_df.iterrows():
                table_data.append([
                    str(row.get('full_name', ''))[:20],
                    str(row.get('evaluation_period', ''))[:12],
                    str(row.get('rating', '')),
                    str(row.get('evaluator', ''))[:15]
                ])
        
        table = Table(table_data, colWidths=[1.2*inch] * len(table_data[0]))
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        summary_text = f"Total Records: {len(data_df)}"
        elements.append(Paragraph(summary_text, styles['Normal']))
    else:
        elements.append(Paragraph("No records found.", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ============================================================================
# EMPLOYEE MANAGEMENT PAGE - WITH PDF/EXCEL EXPORT
# ============================================================================

def employee_management_page():
    """Employee management with full CRUD, audit logging, and export"""
    
    st.header("👥 Employee Management")
    st.markdown("Manage employee records and information")
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["👥 All Employees", "➕ Add New Employee", "📊 Export Reports"])
    
    with tab1:
        st.subheader("Employee Directory")
        
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            filter_dept = st.selectbox("Department", ["All", "Operations", "Maintenance", "Administration", "HR"])
        with col_f2:
            filter_status = st.selectbox("Status", ["All", "Active", "On Leave", "Terminated"])
        with col_f3:
            search_name = st.text_input("🔍 Search by name", placeholder="Employee name")
        
        # Fetch employees
        conn = sqlite3.connect('bus_management.db')
        cursor = conn.cursor()
        
        query = """
            SELECT id, employee_id, full_name, position, department, hire_date, 
                   salary, phone, email, address, status, created_by, created_at 
            FROM employees WHERE 1=1
        """
        params = []
        
        if filter_dept != "All":
            query += " AND department = ?"
            params.append(filter_dept)
        
        if filter_status != "All":
            query += " AND status = ?"
            params.append(filter_status)
        
        if search_name:
            query += " AND full_name LIKE ?"
            params.append(f"%{search_name}%")
        
        query += " ORDER BY full_name"
        
        cursor.execute(query, params)
        employees = cursor.fetchall()
        conn.close()
        
        if employees:
            # Summary stats
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("👥 Total Employees", len(employees))
            with col_stat2:
                active_count = sum(1 for emp in employees if emp[10] == 'Active')
                st.metric("✅ Active", active_count)
            with col_stat3:
                total_salary = sum(emp[6] for emp in employees)
                st.metric("💰 Total Salary", f"${total_salary:,.2f}")
            
            st.markdown("---")
            
            # Display employees
            for emp in employees:
                (emp_id, employee_id, full_name, position, department, hire_date, 
                 salary, phone, email, address, status, created_by, created_at) = emp
                
                status_icon = "✅" if status == "Active" else "⏸️" if status == "On Leave" else "❌"
                
                with st.expander(f"{status_icon} {full_name} - {position} ({employee_id})"):
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.write(f"**Employee ID:** {employee_id}")
                        st.write(f"**Position:** {position}")
                        st.write(f"**Department:** {department}")
                        st.write(f"**Salary:** ${salary:,.2f}")
                        st.write(f"**Status:** {status}")
                    
                    with col_info2:
                        st.write(f"**Hire Date:** {hire_date}")
                        st.write(f"**Phone:** {phone or 'N/A'}")
                        st.write(f"**Email:** {email or 'N/A'}")
                        st.write(f"**Address:** {address or 'N/A'}")
                    
                    st.markdown("---")
                    
                    # Action buttons
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        if st.button("✏️ Edit", key=f"edit_emp_{emp_id}"):
                            st.session_state[f'edit_emp_mode_{emp_id}'] = True
                            st.rerun()
                    
                    with col_btn2:
                        if status == "Active":
                            if st.button("⏸️ Deactivate", key=f"deact_emp_{emp_id}"):
                                conn = sqlite3.connect('bus_management.db')
                                cursor = conn.cursor()
                                cursor.execute("UPDATE employees SET status = 'Terminated' WHERE id = ?", (emp_id,))
                                conn.commit()
                                conn.close()
                                
                                AuditLogger.log_action(
                                    action_type="Edit",
                                    module="Employee",
                                    description=f"Employee status changed to Terminated: {full_name}",
                                    affected_table="employees",
                                    affected_record_id=emp_id
                                )
                                
                                st.success("Employee deactivated")
                                st.rerun()
                    
                    with col_btn3:
                        if st.button("🗑️ Delete", key=f"del_emp_{emp_id}"):
                            if st.session_state.get(f'confirm_del_emp_{emp_id}', False):
                                conn = sqlite3.connect('bus_management.db')
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
                                conn.commit()
                                conn.close()
                                
                                AuditLogger.log_action(
                                    action_type="Delete",
                                    module="Employee",
                                    description=f"Employee record deleted: {full_name} (ID: {employee_id})",
                                    affected_table="employees",
                                    affected_record_id=emp_id
                                )
                                
                                st.success("Employee deleted")
                                st.rerun()
                            else:
                                st.session_state[f'confirm_del_emp_{emp_id}'] = True
                                st.warning("Click again to confirm")
                    
                    # Edit mode
                    if st.session_state.get(f'edit_emp_mode_{emp_id}', False):
                        st.markdown("---")
                        st.markdown("**Edit Employee:**")
                        
                        with st.form(f"edit_emp_form_{emp_id}"):
                            col_edit1, col_edit2 = st.columns(2)
                            
                            with col_edit1:
                                new_full_name = st.text_input("Full Name", value=full_name)
                                new_position = st.text_input("Position", value=position)
                                new_department = st.selectbox(
                                    "Department",
                                    ["Operations", "Maintenance", "Administration", "HR"],
                                    index=["Operations", "Maintenance", "Administration", "HR"].index(department) if department in ["Operations", "Maintenance", "Administration", "HR"] else 0
                                )
                                new_salary = st.number_input("Salary", value=float(salary))
                            
                            with col_edit2:
                                new_phone = st.text_input("Phone", value=phone or "")
                                new_email = st.text_input("Email", value=email or "")
                                new_address = st.text_area("Address", value=address or "")
                                new_status = st.selectbox(
                                    "Status",
                                    ["Active", "On Leave", "Terminated"],
                                    index=["Active", "On Leave", "Terminated"].index(status) if status in ["Active", "On Leave", "Terminated"] else 0
                                )
                            
                            col_save, col_cancel = st.columns(2)
                            
                            with col_save:
                                if st.form_submit_button("💾 Save", use_container_width=True):
                                    old_data = {
                                        'full_name': full_name,
                                        'position': position,
                                        'department': department,
                                        'salary': salary,
                                        'phone': phone,
                                        'email': email,
                                        'address': address,
                                        'status': status
                                    }
                                    
                                    new_data = {
                                        'full_name': new_full_name,
                                        'position': new_position,
                                        'department': new_department,
                                        'salary': new_salary,
                                        'phone': new_phone,
                                        'email': new_email,
                                        'address': new_address,
                                        'status': new_status
                                    }
                                    
                                    conn = sqlite3.connect('bus_management.db')
                                    cursor = conn.cursor()
                                    cursor.execute('''
                                        UPDATE employees
                                        SET full_name = ?, position = ?, department = ?, salary = ?,
                                            phone = ?, email = ?, address = ?, status = ?
                                        WHERE id = ?
                                    ''', (new_full_name, new_position, new_department, new_salary,
                                          new_phone, new_email, new_address, new_status, emp_id))
                                    conn.commit()
                                    conn.close()
                                    
                                    AuditLogger.log_action(
                                        action_type="Edit",
                                        module="Employee",
                                        description=f"Updated employee: {new_full_name} (ID: {employee_id})",
                                        affected_table="employees",
                                        affected_record_id=emp_id,
                                        old_values=old_data,
                                        new_values=new_data
                                    )
                                    
                                    st.success("Employee updated!")
                                    st.session_state[f'edit_emp_mode_{emp_id}'] = False
                                    st.rerun()
                            
                            with col_cancel:
                                if st.form_submit_button("❌ Cancel", use_container_width=True):
                                    st.session_state[f'edit_emp_mode_{emp_id}'] = False
                                    st.rerun()
        else:
            st.info("No employees found. Add your first employee in the 'Add New Employee' tab.")
    
    with tab2:
        st.subheader("Add New Employee")
        
        with st.form("new_employee_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                employee_id = st.text_input("Employee ID*", placeholder="e.g., EMP001")
                full_name = st.text_input("Full Name*", placeholder="e.g., John Doe")
                position = st.text_input("Position*", placeholder="e.g., Bus Driver")
                department = st.selectbox("Department*", ["Operations", "Maintenance", "Administration", "HR"])
            
            with col2:
                hire_date = st.date_input("Hire Date*", datetime.now())
                salary = st.number_input("Salary*", min_value=0.0, step=100.0, format="%.2f")
                phone = st.text_input("Phone", placeholder="+263 xxx xxx xxx")
                email = st.text_input("Email", placeholder="employee@example.com")
            
            address = st.text_area("Address", placeholder="Full address...")
            
            submitted = st.form_submit_button("➕ Add Employee", use_container_width=True, type="primary")
            
            if submitted:
                if not all([employee_id, full_name, position, department, salary > 0]):
                    st.error("⚠️ Please fill in all required fields")
                else:
                    conn = sqlite3.connect('bus_management.db')
                    cursor = conn.cursor()
                    
                    try:
                        cursor.execute('''
                            INSERT INTO employees 
                            (employee_id, full_name, position, department, hire_date, salary, 
                             phone, email, address, status, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
                        ''', (employee_id, full_name, position, department, hire_date.strftime("%Y-%m-%d"),
                              salary, phone, email, address, st.session_state['user']['username']))
                        
                        conn.commit()
                        
                        AuditLogger.log_action(
                            action_type="Add",
                            module="Employee",
                            description=f"New employee added: {full_name}, {position}, {department}, Salary: ${salary:,.2f}",
                            affected_table="employees"
                        )
                        
                        st.success(f"✅ Employee {full_name} added successfully!")
                        st.balloons()
                        
                    except sqlite3.IntegrityError:
                        st.error(f"❌ Employee ID '{employee_id}' already exists!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                    finally:
                        conn.close()
    
    with tab3:
        st.subheader("📊 Export Employee Reports")
        st.write("Generate and download employee reports in PDF or Excel format")
        
        # Report type selection
        report_type = st.selectbox(
            "Select Report Type",
            ["Employee Directory", "Active Employees", "Department Summary", "Salary Report"]
        )
        
        # Filters for export
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            exp_dept = st.selectbox("Department Filter", ["All", "Operations", "Maintenance", "Administration", "HR"], key="exp_dept")
        
        with col_exp2:
            exp_status = st.selectbox("Status Filter", ["All", "Active", "On Leave", "Terminated"], key="exp_status")
        
        st.markdown("---")
        
        # Fetch data for export
        conn = sqlite3.connect('bus_management.db')
        
        query = "SELECT * FROM employees WHERE 1=1"
        params = []
        
        if exp_dept != "All":
            query += " AND department = ?"
            params.append(exp_dept)
        
        if exp_status != "All":
            query += " AND status = ?"
            params.append(exp_status)
        
        export_df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if not export_df.empty:
            col_prev, col_pdf, col_excel = st.columns(3)
            
            with col_prev:
                st.metric("📊 Records to Export", len(export_df))
            
            with col_pdf:
                filters_dict = {}
                if exp_dept != "All":
                    filters_dict['Department'] = exp_dept
                if exp_status != "All":
                    filters_dict['Status'] = exp_status
                
                pdf_buffer = generate_hr_pdf(
                    export_df,
                    f"{report_type}",
                    filters_dict,
                    st.session_state['user']['full_name']
                )
                
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_buffer,
                    file_name=f"employee_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col_excel:
                excel_buffer = io.BytesIO()
                export_df.to_excel(excel_buffer, sheet_name='Employees', index=False)
                excel_buffer.seek(0)
                
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_buffer,
                    file_name=f"employee_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            st.markdown("---")
            st.write("### Preview of Export Data")
            st.dataframe(export_df, use_container_width=True, height=300)
        else:
            st.warning("No employees match the selected filters.")


# ============================================================================
# EMPLOYEE PERFORMANCE PAGE - WITH EXPORT
# ============================================================================

def employee_performance_page():
    """Employee performance tracking and evaluation with export"""
    
    st.header("📊 Employee Performance")
    st.markdown("Track and evaluate employee performance")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📊 Performance Records", "➕ Add Evaluation", "📥 Export Reports"])
    
    with tab1:
        st.subheader("Performance Evaluations")
        
        conn = sqlite3.connect('bus_management.db')
        
        # Get all performance records with employee info
        try:
            perf_df = pd.read_sql_query('''
                SELECT p.*, e.full_name, e.position
                FROM performance_records p
                JOIN employees e ON p.employee_id = e.employee_id
                ORDER BY p.evaluation_date DESC
            ''', conn)
        except:
            perf_df = pd.DataFrame()
        
        conn.close()
        
        if not perf_df.empty:
            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Evaluations", len(perf_df))
            with col2:
                avg_rating = perf_df['rating'].mean()
                st.metric("⭐ Average Rating", f"{avg_rating:.1f}/5")
            with col3:
                recent = perf_df[perf_df['evaluation_date'] >= (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")]
                st.metric("📅 This Month", len(recent))
            
            st.markdown("---")
            
            # Display records
            for idx, row in perf_df.iterrows():
                rating_stars = "⭐" * int(row['rating'])
                
                with st.expander(f"{rating_stars} {row['full_name']} - {row['evaluation_period']} ({row['evaluation_date']})"):
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.write(f"**Employee:** {row['full_name']}")
                        st.write(f"**Position:** {row['position']}")
                        st.write(f"**Period:** {row['evaluation_period']}")
                        st.write(f"**Rating:** {row['rating']}/5")
                    
                    with col_b:
                        st.write(f"**Evaluator:** {row['evaluator']}")
                        st.write(f"**Date:** {row['evaluation_date']}")
                    
                    if row['strengths']:
                        st.success(f"**Strengths:** {row['strengths']}")
                    if row['weaknesses']:
                        st.warning(f"**Areas for Improvement:** {row['weaknesses']}")
                    if row['goals']:
                        st.info(f"**Goals:** {row['goals']}")
                    if row['notes']:
                        st.write(f"**Notes:** {row['notes']}")
        else:
            st.info("No performance records found. Add evaluations in the next tab.")
    
    with tab2:
        st.subheader("Add Performance Evaluation")
        
        conn = sqlite3.connect('bus_management.db')
        try:
            employees_df = pd.read_sql_query("SELECT employee_id, full_name, position FROM employees WHERE status = 'Active'", conn)
        except:
            employees_df = pd.DataFrame()
        conn.close()
        
        if not employees_df.empty:
            with st.form("performance_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    employee_options = [f"{row['employee_id']} - {row['full_name']}" for idx, row in employees_df.iterrows()]
                    selected_emp = st.selectbox("Employee*", employee_options)
                    employee_id = selected_emp.split(" - ")[0]
                    
                    evaluation_period = st.text_input("Evaluation Period*", placeholder="e.g., Q4 2025")
                    rating = st.slider("Performance Rating*", 1, 5, 3)
                
                with col2:
                    evaluation_date = st.date_input("Evaluation Date*", datetime.now())
                    evaluator = st.text_input("Evaluator*", value=st.session_state['user']['full_name'])
                
                strengths = st.text_area("Strengths", placeholder="What does this employee do well?")
                weaknesses = st.text_area("Areas for Improvement", placeholder="What can be improved?")
                goals = st.text_area("Goals", placeholder="Goals for next period...")
                notes = st.text_area("Additional Notes")
                
                submitted = st.form_submit_button("➕ Submit Evaluation", use_container_width=True, type="primary")
                
                if submitted:
                    if not all([employee_id, evaluation_period, rating, evaluator]):
                        st.error("⚠️ Please fill in all required fields")
                    else:
                        conn = sqlite3.connect('bus_management.db')
                        cursor = conn.cursor()
                        
                        cursor.execute('''
                            INSERT INTO performance_records
                            (employee_id, evaluation_period, rating, strengths, weaknesses, 
                             goals, evaluator, evaluation_date, notes, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (employee_id, evaluation_period, rating, strengths, weaknesses,
                              goals, evaluator, evaluation_date.strftime("%Y-%m-%d"), notes,
                              st.session_state['user']['username']))
                        
                        conn.commit()
                        conn.close()
                        
                        emp_name = selected_emp.split(" - ")[1]
                        AuditLogger.log_action(
                            action_type="Add",
                            module="Performance",
                            description=f"Performance evaluation added for {emp_name}: Rating {rating}/5, Period: {evaluation_period}",
                            affected_table="performance_records"
                        )
                        
                        st.success("✅ Performance evaluation submitted!")
                        st.balloons()
        else:
            st.warning("No active employees found. Please add employees first.")
    
    with tab3:
        st.subheader("📥 Export Performance Reports")
        
        conn = sqlite3.connect('bus_management.db')
        try:
            perf_export_df = pd.read_sql_query('''
                SELECT p.*, e.full_name, e.position, e.department
                FROM performance_records p
                JOIN employees e ON p.employee_id = e.employee_id
                ORDER BY p.evaluation_date DESC
            ''', conn)
        except:
            perf_export_df = pd.DataFrame()
        conn.close()
        
        if not perf_export_df.empty:
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                st.metric("📊 Records", len(perf_export_df))
            
            with col_exp2:
                pdf_buffer = generate_hr_pdf(
                    perf_export_df,
                    "Performance Evaluation Report",
                    {},
                    st.session_state['user']['full_name']
                )
                
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_buffer,
                    file_name=f"performance_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col_exp3:
                excel_buffer = io.BytesIO()
                perf_export_df.to_excel(excel_buffer, sheet_name='Performance', index=False)
                excel_buffer.seek(0)
                
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_buffer,
                    file_name=f"performance_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            st.markdown("---")
            st.dataframe(perf_export_df, use_container_width=True, height=300)
        else:
            st.warning("No performance records found.")


# ============================================================================
# PAYROLL MANAGEMENT PAGE - COMPLETE WITH EXPORT
# ============================================================================

def payroll_management_page():
    """Payroll processing and payslip generation with export"""
    
    st.header("💰 Payroll & Payslips")
    st.markdown("Manage employee payroll and generate payslips")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["💰 Payroll Records", "➕ Process Payroll", "📥 Export Reports"])
    
    with tab1:
        st.subheader("Payroll History")
        
        # Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_period = st.text_input("Filter by period", placeholder="e.g., 2025-10")
        with col_f2:
            filter_status = st.selectbox("Status", ["All", "Pending", "Paid", "Cancelled"])
        
        conn = sqlite3.connect('bus_management.db')
        
        query = '''
            SELECT p.*, e.full_name, e.position
            FROM payroll p
            JOIN employees e ON p.employee_id = e.employee_id
            WHERE 1=1
        '''
        params = []
        
        if filter_period:
            query += " AND p.pay_period LIKE ?"
            params.append(f"%{filter_period}%")
        
        if filter_status != "All":
            query += " AND p.status = ?"
            params.append(filter_status)
        
        query += " ORDER BY p.created_at DESC"
        
        try:
            payroll_df = pd.read_sql_query(query, conn, params=params)
        except:
            payroll_df = pd.DataFrame()
            
        conn.close()
        
        if not payroll_df.empty:
            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                total_paid = payroll_df[payroll_df['status'] == 'Paid']['net_salary'].sum()
                st.metric("💰 Total Paid", f"${total_paid:,.2f}")
            with col2:
                pending = payroll_df[payroll_df['status'] == 'Pending']['net_salary'].sum()
                st.metric("⏳ Pending", f"${pending:,.2f}")
            with col3:
                st.metric("📊 Total Records", len(payroll_df))
            
            st.markdown("---")
            
            # Display payroll records
            for idx, row in payroll_df.iterrows():
                status_icon = "✅" if row['status'] == 'Paid' else "⏳" if row['status'] == 'Pending' else "❌"
                
                with st.expander(f"{status_icon} {row['full_name']} - {row['pay_period']} | ${row['net_salary']:,.2f}"):
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.write(f"**Employee:** {row['full_name']}")
                        st.write(f"**Position:** {row['position']}")
                        st.write(f"**Period:** {row['pay_period']}")
                        st.write(f"**Basic Salary:** ${row['basic_salary']:,.2f}")
                        st.write(f"**Allowances:** ${row['allowances']:,.2f}")
                    
                    with col_b:
                        st.write(f"**Deductions:** ${row['deductions']:,.2f}")
                        st.write(f"**Commission:** ${row['commission']:,.2f}")
                        st.write(f"**Net Salary:** ${row['net_salary']:,.2f}")
                        st.write(f"**Status:** {row['status']}")
                        if row['payment_date']:
                            st.write(f"**Payment Date:** {row['payment_date']}")
                    
                    if row['notes']:
                        st.info(f"**Notes:** {row['notes']}")
                    
                    # Action buttons
                    if row['status'] == 'Pending':
                        if st.button("✅ Mark as Paid", key=f"pay_{row['id']}"):
                            conn = sqlite3.connect('bus_management.db')
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE payroll 
                                SET status = 'Paid', payment_date = ?
                                WHERE id = ?
                            ''', (datetime.now().strftime("%Y-%m-%d"), row['id']))
                            conn.commit()
                            conn.close()
                            
                            AuditLogger.log_action(
                                action_type="Edit",
                                module="Payroll",
                                description=f"Marked payroll as paid: {row['full_name']}, Period: {row['pay_period']}, Amount: ${row['net_salary']:,.2f}",
                                affected_table="payroll",
                                affected_record_id=row['id']
                            )
                            
                            st.success("Payroll marked as paid!")
                            st.rerun()
        else:
            st.info("No payroll records found.")
    
    with tab2:
        st.subheader("Process Payroll")
        
        # Get employees
        conn = sqlite3.connect('bus_management.db')
        try:
            employees_df = pd.read_sql_query("SELECT employee_id, full_name, position, salary FROM employees WHERE status = 'Active'", conn)
        except:
            employees_df = pd.DataFrame()
        conn.close()
        
        if not employees_df.empty:
            with st.form("payroll_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    employee_options = [f"{row['employee_id']} - {row['full_name']}" for idx, row in employees_df.iterrows()]
                    selected_emp = st.selectbox("Employee*", employee_options)
                    employee_id = selected_emp.split(" - ")[0]
                    
                    # Get employee's salary
                    emp_salary = employees_df[employees_df['employee_id'] == employee_id]['salary'].values[0]
                    
                    pay_period = st.text_input("Pay Period*", placeholder="e.g., October 2025 or 2025-10")
                    basic_salary = st.number_input("Basic Salary*", value=float(emp_salary), format="%.2f")
                    allowances = st.number_input("Allowances", value=0.0, format="%.2f")
                
                with col2:
                    deductions = st.number_input("Deductions", value=0.0, format="%.2f")
                    commission = st.number_input("Commission/Bonus", value=0.0, format="%.2f")
                    payment_method = st.selectbox("Payment Method", ["Bank Transfer", "Cash", "Check", "Mobile Money"])
                
                # Calculate net salary
                net_salary = basic_salary + allowances + commission - deductions
                st.info(f"**Net Salary: ${net_salary:,.2f}**")
                
                notes = st.text_area("Notes")
                
                submitted = st.form_submit_button("💰 Process Payroll", use_container_width=True, type="primary")
                
                if submitted:
                    if not all([employee_id, pay_period, basic_salary >= 0]):
                        st.error("⚠️ Please fill in all required fields")
                    else:
                        conn = sqlite3.connect('bus_management.db')
                        cursor = conn.cursor()
                        
                        cursor.execute('''
                            INSERT INTO payroll
                            (employee_id, pay_period, basic_salary, allowances, deductions, 
                             commission, net_salary, payment_method, status, notes, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
                        ''', (employee_id, pay_period, basic_salary, allowances, deductions,
                              commission, net_salary, payment_method, notes,
                              st.session_state['user']['username']))
                        
                        conn.commit()
                        conn.close()
                        
                        emp_name = selected_emp.split(" - ")[1]
                        AuditLogger.log_action(
                            action_type="Add",
                            module="Payroll",
                            description=f"Payroll processed for {emp_name}: Period {pay_period}, Net: ${net_salary:,.2f}",
                            affected_table="payroll"
                        )
                        
                        st.success(f"✅ Payroll processed for {emp_name}!")
                        st.balloons()
        else:
            st.warning("No active employees found.")
    
    with tab3:
        st.subheader("📥 Export Payroll Reports")
        
        conn = sqlite3.connect('bus_management.db')
        try:
            payroll_export_df = pd.read_sql_query('''
                SELECT p.*, e.full_name, e.position, e.department
                FROM payroll p
                JOIN employees e ON p.employee_id = e.employee_id
                ORDER BY p.created_at DESC
            ''', conn)
        except:
            payroll_export_df = pd.DataFrame()
        conn.close()
        
        if not payroll_export_df.empty:
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                st.metric("📊 Total Records", len(payroll_export_df))
            
            with col_exp2:
                pdf_buffer = generate_hr_pdf(
                    payroll_export_df,
                    "Payroll Report",
                    {},
                    st.session_state['user']['full_name']
                )
                
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_buffer,
                    file_name=f"payroll_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col_exp3:
                excel_buffer = io.BytesIO()
                payroll_export_df.to_excel(excel_buffer, sheet_name='Payroll', index=False)
                excel_buffer.seek(0)
                
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_buffer,
                    file_name=f"payroll_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            st.markdown("---")
            st.dataframe(payroll_export_df, use_container_width=True, height=300)
        else:
            st.warning("No payroll records found.")


# ============================================================================
# LEAVE MANAGEMENT PAGE - COMPLETE WITH EXPORT
# ============================================================================

def leave_management_page():
    """Employee leave requests and approvals with export"""
    
    st.header("📅 Leave Management")
    st.markdown("Manage employee leave requests and approvals")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📅 Leave Records", "➕ New Leave Request", "📥 Export Reports"])
    
    with tab1:
        st.subheader("Leave Requests")
        
        # Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_status = st.selectbox("Status", ["All", "Pending", "Approved", "Rejected"])
        with col_f2:
            filter_type = st.selectbox("Leave Type", ["All", "Annual Leave", "Sick Leave", "Emergency Leave", "Unpaid Leave"])
        
        conn = sqlite3.connect('bus_management.db')
        
        query = '''
            SELECT l.*, e.full_name, e.position
            FROM leave_records l
            JOIN employees e ON l.employee_id = e.employee_id
            WHERE 1=1
        '''
        params = []
        
        if filter_status != "All":
            query += " AND l.status = ?"
            params.append(filter_status)
        
        if filter_type != "All":
            query += " AND l.leave_type = ?"
            params.append(filter_type)
        
        query += " ORDER BY l.created_at DESC"
        
        try:
            leave_df = pd.read_sql_query(query, conn, params=params)
        except:
            leave_df = pd.DataFrame()
            
        conn.close()
        
        if not leave_df.empty:
            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Requests", len(leave_df))
            with col2:
                pending = len(leave_df[leave_df['status'] == 'Pending'])
                st.metric("⏳ Pending", pending)
            with col3:
                approved = len(leave_df[leave_df['status'] == 'Approved'])
                st.metric("✅ Approved", approved)
            
            st.markdown("---")
            
            # Display leave records
            for idx, row in leave_df.iterrows():
                status_icon = "⏳" if row['status'] == 'Pending' else "✅" if row['status'] == 'Approved' else "❌"
                
                with st.expander(f"{status_icon} {row['full_name']} - {row['leave_type']} | {row['start_date']} to {row['end_date']}"):
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.write(f"**Employee:** {row['full_name']}")
                        st.write(f"**Position:** {row['position']}")
                        st.write(f"**Leave Type:** {row['leave_type']}")
                        st.write(f"**Start Date:** {row['start_date']}")
                        st.write(f"**End Date:** {row['end_date']}")
                    
                    with col_b:
                        # Calculate days
                        start = datetime.strptime(row['start_date'], "%Y-%m-%d")
                        end = datetime.strptime(row['end_date'], "%Y-%m-%d")
                        days = (end - start).days + 1
                        
                        st.write(f"**Days:** {days}")
                        st.write(f"**Status:** {row['status']}")
                        st.write(f"**Requested Date:** {row['created_at']}")
                    
                    if row['reason']:
                        st.info(f"**Reason:** {row['reason']}")
                    
                    if row['status'] == 'Pending':
                        st.markdown("---")
                        col_app, col_rej = st.columns(2)
                        
                        with col_app:
                            if st.button("✅ Approve", key=f"approve_leave_{row['id']}"):
                                conn = sqlite3.connect('bus_management.db')
                                cursor = conn.cursor()
                                cursor.execute('''
                                    UPDATE leave_records 
                                    SET status = 'Approved', approved_by = ?, approved_date = ?
                                    WHERE id = ?
                                ''', (st.session_state['user']['full_name'], datetime.now().strftime("%Y-%m-%d"), row['id']))
                                conn.commit()
                                conn.close()
                                
                                AuditLogger.log_action(
                                    action_type="Edit",
                                    module="Leave",
                                    description=f"Leave request approved: {row['full_name']}, Type: {row['leave_type']}, Days: {days}",
                                    affected_table="leave_records",
                                    affected_record_id=row['id']
                                )
                                
                                st.success("Leave request approved!")
                                st.rerun()
                        
                        with col_rej:
                            if st.button("❌ Reject", key=f"reject_leave_{row['id']}"):
                                conn = sqlite3.connect('bus_management.db')
                                cursor = conn.cursor()
                                cursor.execute('''
                                    UPDATE leave_records 
                                    SET status = 'Rejected', approved_by = ?, approved_date = ?
                                    WHERE id = ?
                                ''', (st.session_state['user']['full_name'], datetime.now().strftime("%Y-%m-%d"), row['id']))
                                conn.commit()
                                conn.close()
                                
                                AuditLogger.log_action(
                                    action_type="Edit",
                                    module="Leave",
                                    description=f"Leave request rejected: {row['full_name']}, Type: {row['leave_type']}",
                                    affected_table="leave_records",
                                    affected_record_id=row['id']
                                )
                                
                                st.warning("Leave request rejected!")
                                st.rerun()
        else:
            st.info("No leave records found.")
    
    with tab2:
        st.subheader("Submit New Leave Request")
        
        # Get employees
        conn = sqlite3.connect('bus_management.db')
        try:
            employees_df = pd.read_sql_query("SELECT employee_id, full_name FROM employees WHERE status = 'Active'", conn)
        except:
            employees_df = pd.DataFrame()
        conn.close()
        
        if not employees_df.empty:
            with st.form("leave_request_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    employee_options = [f"{row['employee_id']} - {row['full_name']}" for idx, row in employees_df.iterrows()]
                    selected_emp = st.selectbox("Employee*", employee_options)
                    employee_id = selected_emp.split(" - ")[0]
                    
                    leave_type = st.selectbox(
                        "Leave Type*",
                        ["Annual Leave", "Sick Leave", "Emergency Leave", "Unpaid Leave"]
                    )
                    start_date = st.date_input("Start Date*", datetime.now())
                
                with col2:
                    end_date = st.date_input("End Date*", datetime.now() + timedelta(days=1))
                    reason = st.text_area("Reason*", placeholder="Why are you taking leave?")
                
                submitted = st.form_submit_button("➕ Submit Request", use_container_width=True, type="primary")
                
                if submitted:
                    if not all([employee_id, leave_type, reason]) or start_date > end_date:
                        st.error("⚠️ Please fill in all required fields and ensure start date is before end date")
                    else:
                        conn = sqlite3.connect('bus_management.db')
                        cursor = conn.cursor()
                        
                        cursor.execute('''
                            INSERT INTO leave_records
                            (employee_id, leave_type, start_date, end_date, reason, status, created_by)
                            VALUES (?, ?, ?, ?, ?, 'Pending', ?)
                        ''', (employee_id, leave_type, start_date.strftime("%Y-%m-%d"), 
                              end_date.strftime("%Y-%m-%d"), reason, st.session_state['user']['username']))
                        
                        conn.commit()
                        conn.close()
                        
                        days = (end_date - start_date).days + 1
                        emp_name = selected_emp.split(" - ")[1]
                        AuditLogger.log_action(
                            action_type="Add",
                            module="Leave",
                            description=f"Leave request submitted by {emp_name}: Type {leave_type}, {days} days",
                            affected_table="leave_records"
                        )
                        
                        st.success("✅ Leave request submitted successfully!")
                        st.balloons()
        else:
            st.warning("No active employees found.")
    
    with tab3:
        st.subheader("📥 Export Leave Reports")
        
        conn = sqlite3.connect('bus_management.db')
        try:
            leave_export_df = pd.read_sql_query('''
                SELECT l.*, e.full_name, e.position, e.department
                FROM leave_records l
                JOIN employees e ON l.employee_id = e.employee_id
                ORDER BY l.created_at DESC
            ''', conn)
        except:
            leave_export_df = pd.DataFrame()
        conn.close()
        
        if not leave_export_df.empty:
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                st.metric("📊 Total Records", len(leave_export_df))
            
            with col_exp2:
                pdf_buffer = generate_hr_pdf(
                    leave_export_df,
                    "Leave Management Report",
                    {},
                    st.session_state['user']['full_name']
                )
                
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_buffer,
                    file_name=f"leave_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col_exp3:
                excel_buffer = io.BytesIO()
                leave_export_df.to_excel(excel_buffer, sheet_name='Leave', index=False)
                excel_buffer.seek(0)
                
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_buffer,
                    file_name=f"leave_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            st.markdown("---")
            st.dataframe(leave_export_df, use_container_width=True, height=300)
        else:
            st.warning("No leave records found.")


# ============================================================================
# DISCIPLINARY RECORDS PAGE - COMPLETE WITH EXPORT
# ============================================================================

def disciplinary_records_page():
    """Employee disciplinary records and actions with export"""
    
    st.header("⚠️ Disciplinary Records")
    st.markdown("Manage employee disciplinary actions and warnings")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["⚠️ Disciplinary Records", "➕ Add Record", "📥 Export Reports"])
    
    with tab1:
        st.subheader("Disciplinary History")
        
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_severity = st.selectbox("Severity", ["All", "Verbal Warning", "Written Warning", "Suspension", "Termination"])
        with col_f2:
            filter_status = st.selectbox("Status", ["All", "Active", "Resolved", "Appealed"])
        with col_f3:
            search_emp = st.text_input("🔍 Search employee", placeholder="Employee name")
        
        conn = sqlite3.connect('bus_management.db')
        
        query = '''
            SELECT d.*, e.full_name, e.position
            FROM disciplinary_records d
            JOIN employees e ON d.employee_id = e.employee_id
            WHERE 1=1
        '''
        params = []
        
        if filter_severity != "All":
            query += " AND d.action_type = ?"
            params.append(filter_severity)
        
        if filter_status != "All":
            query += " AND d.status = ?"
            params.append(filter_status)
        
        if search_emp:
            query += " AND e.full_name LIKE ?"
            params.append(f"%{search_emp}%")
        
        query += " ORDER BY d.created_at DESC"
        
        try:
            disc_df = pd.read_sql_query(query, conn, params=params)
        except:
            disc_df = pd.DataFrame()
            
        conn.close()
        
        if not disc_df.empty:
            # Summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Records", len(disc_df))
            with col2:
                active = len(disc_df[disc_df['status'] == 'Active'])
                st.metric("⚠️ Active", active)
            with col3:
                resolved = len(disc_df[disc_df['status'] == 'Resolved'])
                st.metric("✅ Resolved", resolved)
            
            st.markdown("---")
            
            # Display records
            for idx, row in disc_df.iterrows():
                severity_icon = "🔴" if row['action_type'] == 'Termination' else "🟠" if row['action_type'] == 'Suspension' else "🟡" if row['action_type'] == 'Written Warning' else "🟢"
                status_icon = "⚠️" if row['status'] == 'Active' else "✅" if row['status'] == 'Resolved' else "🔵"
                
                with st.expander(f"{severity_icon} {status_icon} {row['full_name']} - {row['action_type']} ({row['record_date']})"):
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.write(f"**Employee:** {row['full_name']}")
                        st.write(f"**Position:** {row['position']}")
                        st.write(f"**Action:** {row['action_type']}")
                        st.write(f"**Record Date:** {row['record_date']}")
                        st.write(f"**Status:** {row['status']}")
                    
                    with col_b:
                        st.write(f"**Issued By:** {row['issued_by']}")
                        if row['due_date']:
                            st.write(f"**Due Date:** {row['due_date']}")
                        if row['resolution_date']:
                            st.write(f"**Resolution Date:** {row['resolution_date']}")
                    
                    if row['violation_description']:
                        st.warning(f"**Violation:** {row['violation_description']}")
                    if row['action_details']:
                        st.info(f"**Details:** {row['action_details']}")
                    if row['notes']:
                        st.write(f"**Notes:** {row['notes']}")
                    
                    # Action buttons
                    if row['status'] == 'Active':
                        st.markdown("---")
                        col_res, col_app = st.columns(2)
                        
                        with col_res:
                            if st.button("✅ Mark Resolved", key=f"resolve_disc_{row['id']}"):
                                conn = sqlite3.connect('bus_management.db')
                                cursor = conn.cursor()
                                cursor.execute('''
                                    UPDATE disciplinary_records 
                                    SET status = 'Resolved', resolution_date = ?
                                    WHERE id = ?
                                ''', (datetime.now().strftime("%Y-%m-%d"), row['id']))
                                conn.commit()
                                conn.close()
                                
                                AuditLogger.log_action(
                                    action_type="Edit",
                                    module="Disciplinary",
                                    description=f"Disciplinary record resolved: {row['full_name']}, Action: {row['action_type']}",
                                    affected_table="disciplinary_records",
                                    affected_record_id=row['id']
                                )
                                
                                st.success("Record marked as resolved!")
                                st.rerun()
                        
                        with col_app:
                            if st.button("🔵 Appeal", key=f"appeal_disc_{row['id']}"):
                                conn = sqlite3.connect('bus_management.db')
                                cursor = conn.cursor()
                                cursor.execute('''
                                    UPDATE disciplinary_records 
                                    SET status = 'Appealed'
                                    WHERE id = ?
                                ''', (row['id'],))
                                conn.commit()
                                conn.close()
                                
                                AuditLogger.log_action(
                                    action_type="Edit",
                                    module="Disciplinary",
                                    description=f"Disciplinary record appealed: {row['full_name']}, Action: {row['action_type']}",
                                    affected_table="disciplinary_records",
                                    affected_record_id=row['id']
                                )
                                
                                st.info("Appeal recorded!")
                                st.rerun()
        else:
            st.info("No disciplinary records found.")
    
    with tab2:
        st.subheader("Issue Disciplinary Action")
        
        # Get employees
        conn = sqlite3.connect('bus_management.db')
        try:
            employees_df = pd.read_sql_query("SELECT employee_id, full_name, position FROM employees WHERE status = 'Active'", conn)
        except:
            employees_df = pd.DataFrame()
        conn.close()
        
        if not employees_df.empty:
            with st.form("disciplinary_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    employee_options = [f"{row['employee_id']} - {row['full_name']}" for idx, row in employees_df.iterrows()]
                    selected_emp = st.selectbox("Employee*", employee_options)
                    employee_id = selected_emp.split(" - ")[0]
                    
                    action_type = st.selectbox(
                        "Action Type*",
                        ["Verbal Warning", "Written Warning", "Suspension", "Termination"]
                    )
                    record_date = st.date_input("Record Date*", datetime.now())
                
                with col2:
                    issued_by = st.text_input("Issued By*", value=st.session_state['user']['full_name'])
                    due_date = st.date_input("Due Date (for follow-up)", datetime.now() + timedelta(days=30))
                
                violation_description = st.text_area("Violation Description*", placeholder="What was the violation?")
                action_details = st.text_area("Action Details*", placeholder="What action is being taken?")
                notes = st.text_area("Additional Notes")
                
                submitted = st.form_submit_button("⚠️ Issue Disciplinary Action", use_container_width=True, type="primary")
                
                if submitted:
                    if not all([employee_id, action_type, violation_description, action_details, issued_by]):
                        st.error("⚠️ Please fill in all required fields")
                    else:
                        conn = sqlite3.connect('bus_management.db')
                        cursor = conn.cursor()
                        
                        cursor.execute('''
                            INSERT INTO disciplinary_records
                            (employee_id, action_type, violation_description, action_details, 
                             record_date, due_date, issued_by, status, notes, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
                        ''', (employee_id, action_type, violation_description, action_details,
                              record_date.strftime("%Y-%m-%d"), due_date.strftime("%Y-%m-%d"),
                              issued_by, notes, st.session_state['user']['username']))
                        
                        conn.commit()
                        conn.close()
                        
                        emp_name = selected_emp.split(" - ")[1]
                        AuditLogger.log_action(
                            action_type="Add",
                            module="Disciplinary",
                            description=f"Disciplinary action issued to {emp_name}: {action_type}",
                            affected_table="disciplinary_records"
                        )
                        
                        st.warning(f"⚠️ Disciplinary action issued to {emp_name}")
        else:
            st.warning("No active employees found.")
    
    with tab3:
        st.subheader("📥 Export Disciplinary Reports")
        
        conn = sqlite3.connect('bus_management.db')
        try:
            disc_export_df = pd.read_sql_query('''
                SELECT d.*, e.full_name, e.position, e.department
                FROM disciplinary_records d
                JOIN employees e ON d.employee_id = e.employee_id
                ORDER BY d.created_at DESC
            ''', conn)
        except:
            disc_export_df = pd.DataFrame()
        conn.close()
        
        if not disc_export_df.empty:
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                st.metric("📊 Total Records", len(disc_export_df))
            
            with col_exp2:
                pdf_buffer = generate_hr_pdf(
                    disc_export_df,
                    "Disciplinary Records Report",
                    {},
                    st.session_state['user']['full_name']
                )
                
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_buffer,
                    file_name=f"disciplinary_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with col_exp3:
                excel_buffer = io.BytesIO()
                disc_export_df.to_excel(excel_buffer, sheet_name='Disciplinary', index=False)
                excel_buffer.seek(0)
                
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_buffer,
                    file_name=f"disciplinary_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            st.markdown("---")
            st.dataframe(disc_export_df, use_container_width=True, height=300)
        else:
            st.warning("No disciplinary records found.")