"""
pages_hr.py - Complete HR Management Module with Audit Logging and PDF/EXCEL EXPORT
Includes: Employee Management, Performance, Payroll, Leave, Disciplinary
CORRECTED VERSION - Uses database abstraction for PostgreSQL/SQLite compatibility
"""

import streamlit as st
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

# Import database abstraction layer
from database import get_connection, get_engine, USE_POSTGRES


def get_placeholder():
    """Return the correct placeholder for the current database"""
    return '%s' if USE_POSTGRES else '?'


def execute_hr_query(cursor, query, params=None):
    """Execute a query with automatic placeholder conversion for PostgreSQL"""
    if USE_POSTGRES and params:
        # Convert ? to %s for PostgreSQL
        query = query.replace('?', '%s')
    
    if params:
        cursor.execute(query, tuple(params) if isinstance(params, list) else params)
    else:
        cursor.execute(query)




def get_emp_value(emp, key_or_index, default=None):
    """
    Get value from employee row - works with both dict (PostgreSQL) and tuple (SQLite)
    
    Args:
        emp: The row from database (either dict-like or tuple)
        key_or_index: Either a string key (for dict) or int index (for tuple)
        default: Default value if not found
    
    For PostgreSQL, use string keys: get_emp_value(emp, 'status')
    For SQLite compatibility, this function handles both formats
    """
    if hasattr(emp, 'keys'):
        # Dict-like (PostgreSQL RealDictRow)
        if isinstance(key_or_index, str):
            return emp.get(key_or_index, default)
        else:
            # If index given, map to column names
            columns = ['id', 'employee_id', 'full_name', 'position', 'department', 
                      'hire_date', 'salary', 'phone', 'email', 'address', 'status',
                      'date_of_birth', 'emergency_contact', 'emergency_phone',
                      'license_number', 'license_expiry', 'defensive_driving_expiry',
                      'medical_cert_expiry', 'retest_date', 'created_by', 'created_at']
            if key_or_index < len(columns):
                return emp.get(columns[key_or_index], default)
            return default
    else:
        # Tuple (SQLite)
        if isinstance(key_or_index, int):
            try:
                return emp[key_or_index]
            except (IndexError, TypeError):
                return default
        else:
            # String key given but we have tuple - need to map
            columns = ['id', 'employee_id', 'full_name', 'position', 'department', 
                      'hire_date', 'salary', 'phone', 'email', 'address', 'status',
                      'date_of_birth', 'emergency_contact', 'emergency_phone',
                      'license_number', 'license_expiry', 'defensive_driving_expiry',
                      'medical_cert_expiry', 'retest_date', 'created_by', 'created_at']
            try:
                idx = columns.index(key_or_index)
                return emp[idx]
            except (ValueError, IndexError):
                return default


def unpack_employee(emp):
    """
    Unpack employee row into individual variables regardless of format
    Returns tuple of all employee fields
    """
    if hasattr(emp, 'keys'):
        # PostgreSQL dict-like row
        return (
            emp.get('id'),
            emp.get('employee_id'),
            emp.get('full_name'),
            emp.get('position'),
            emp.get('department'),
            emp.get('hire_date'),
            emp.get('salary', 0),
            emp.get('phone'),
            emp.get('email'),
            emp.get('address'),
            emp.get('status'),
            emp.get('date_of_birth'),
            emp.get('emergency_contact'),
            emp.get('emergency_phone'),
            emp.get('next_of_kin_relationship'),
            emp.get('national_id'),
            emp.get('license_number'),
            emp.get('license_expiry'),
            emp.get('defensive_driving_expiry'),
            emp.get('medical_cert_expiry'),
            emp.get('retest_date'),
            emp.get('created_by'),
            emp.get('created_at')
        )
    else:
        # SQLite tuple - pad with None if needed
        result = list(emp) + [None] * (23 - len(emp))
        return tuple(result[:23])


def generate_employee_id(position, conn):
    """
    Automatically generate the next employee ID based on position/role
    
    Rules:
    - Drivers: PavD001, PavD002, PavD003...
    - Conductors: PavC001, PavC002, PavC003...
    - Mechanics/Office Staff/Others: Pav001, Pav002, Pav003...
    """
    cursor = conn.cursor()
    
    position_lower = position.lower()
    
    if 'driver' in position_lower:
        prefix = 'PavD'
        pattern = 'PavD%'
    elif 'conductor' in position_lower:
        prefix = 'PavC'
        pattern = 'PavC%'
    else:
        prefix = 'Pav'
        pattern = 'Pav%'
    
    # Use database-agnostic query
    if USE_POSTGRES:
        if 'driver' in position_lower or 'conductor' in position_lower:
            query = """
                SELECT employee_id 
                FROM employees 
                WHERE employee_id LIKE %s 
                ORDER BY CAST(SUBSTRING(employee_id FROM LENGTH(%s)+1) AS INTEGER) DESC
                LIMIT 1
            """
            cursor.execute(query, (pattern, prefix))
        else:
            query = """
                SELECT employee_id 
                FROM employees 
                WHERE employee_id LIKE %s 
                AND employee_id NOT LIKE 'PavD%%' 
                AND employee_id NOT LIKE 'PavC%%'
                ORDER BY CAST(SUBSTRING(employee_id FROM LENGTH(%s)+1) AS INTEGER) DESC
                LIMIT 1
            """
            cursor.execute(query, (pattern, prefix))
    else:
        if 'driver' in position_lower or 'conductor' in position_lower:
            query = """
                SELECT employee_id 
                FROM employees 
                WHERE employee_id LIKE ? 
                ORDER BY CAST(SUBSTR(employee_id, LENGTH(?)+1) AS INTEGER) DESC
                LIMIT 1
            """
            cursor.execute(query, (pattern, prefix))
        else:
            query = """
                SELECT employee_id 
                FROM employees 
                WHERE employee_id LIKE ? 
                AND employee_id NOT LIKE 'PavD%' 
                AND employee_id NOT LIKE 'PavC%'
                ORDER BY CAST(SUBSTR(employee_id, LENGTH(?)+1) AS INTEGER) DESC
                LIMIT 1
            """
            cursor.execute(query, (pattern, prefix))
    
    result = cursor.fetchone()
    
    if result:
        # Handle both dict-like (PostgreSQL) and tuple (SQLite) results
        if hasattr(result, 'keys'):
            last_id = result['employee_id']
        else:
            last_id = result[0]
        numeric_part = ''.join(filter(str.isdigit, last_id))
        if numeric_part:
            next_number = int(numeric_part) + 1
        else:
            next_number = 1
    else:
        next_number = 1
    
    new_id = f"{prefix}{next_number:03d}"
    return new_id


def get_expiring_documents(days_threshold=30):
    """
    Check for documents expiring within the specified days
    Returns: List of alerts with employee info and expiring document type
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    alerts = []
    current_date = datetime.now().date()
    threshold_date = current_date + timedelta(days=days_threshold)
    
    # Check all document types
    document_checks = [
        ('license_expiry', 'Driver License'),
        ('defensive_driving_expiry', 'Defensive Driving Certificate'),
        ('medical_cert_expiry', 'Medical Certificate'),
        ('retest_date', 'Retest Due')
    ]
    
    for date_column, doc_name in document_checks:
        try:
            if USE_POSTGRES:
                query = f"""
                    SELECT employee_id, full_name, position, {date_column}
                    FROM employees
                    WHERE {date_column} IS NOT NULL
                    AND {date_column} != ''
                    AND {date_column}::DATE <= %s::DATE
                    AND status = 'Active'
                    ORDER BY {date_column}
                """
                cursor.execute(query, (threshold_date.strftime('%Y-%m-%d'),))
            else:
                query = f"""
                    SELECT employee_id, full_name, position, {date_column}
                    FROM employees
                    WHERE {date_column} IS NOT NULL
                    AND {date_column} != ''
                    AND date({date_column}) <= date(?)
                    AND status = 'Active'
                    ORDER BY {date_column}
                """
                cursor.execute(query, (threshold_date.strftime('%Y-%m-%d'),))
            
            results = cursor.fetchall()
            
            for row in results:
                # Handle both dict and tuple formats
                if hasattr(row, 'keys'):
                    emp_id = row['employee_id']
                    name = row['full_name']
                    position = row['position']
                    expiry_date = row[date_column]
                else:
                    emp_id, name, position, expiry_date = row
                
                try:
                    expiry = datetime.strptime(str(expiry_date), '%Y-%m-%d').date()
                    days_until = (expiry - current_date).days
                    
                    urgency = 'critical' if days_until <= 7 else 'warning' if days_until <= 14 else 'info'
                    
                    alerts.append({
                        'employee_id': emp_id,
                        'name': name,
                        'position': position,
                        'document': doc_name,
                        'expiry_date': str(expiry_date),
                        'days_until': days_until,
                        'urgency': urgency,
                        'expired': days_until < 0
                    })
                except ValueError:
                    continue
        except Exception as e:
            # Column might not exist in database yet
            print(f"Note: Could not check {date_column}: {e}")
            continue
    
    conn.close()
    
    # Sort by urgency and days remaining
    alerts.sort(key=lambda x: (x['expired'], x['days_until']))
    
    return alerts


def display_document_expiry_alerts():
    """Display document expiry alerts on the homepage - collapsed by default"""
    
    try:
        alerts = get_expiring_documents(days_threshold=30)
    except Exception as e:
        return
    
    if not alerts:
        return
    
    # Count alerts by urgency
    expired = [a for a in alerts if a['expired']]
    critical = [a for a in alerts if a['urgency'] == 'critical' and not a['expired']]
    warning = [a for a in alerts if a['urgency'] == 'warning']
    info = [a for a in alerts if a['urgency'] == 'info']
    
    # Calculate totals for summary
    total_urgent = len(expired) + len(critical) + len(warning)
    
    if total_urgent == 0 and len(info) == 0:
        return
    
    # Determine header based on severity
    if expired:
        header_icon = "🚨"
        header_text = f"Employee Documents: {len(expired)} Expired, {len(critical)} Critical, {len(warning)} Warning"
    elif critical:
        header_icon = "⚠️"
        header_text = f"Employee Documents: {len(critical)} Critical, {len(warning)} Warning"
    elif warning:
        header_icon = "📋"
        header_text = f"Employee Documents: {len(warning)} Expiring Soon"
    else:
        header_icon = "ℹ️"
        header_text = f"Employee Documents: {len(info)} Upcoming Renewals"
    
    # Single collapsed expander with all alerts
    with st.expander(f"{header_icon} {header_text}", expanded=False):
        # Summary metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🔴 Expired", len(expired))
        with col2:
            st.metric("🟠 Critical", len(critical))
        with col3:
            st.metric("🟡 Warning", len(warning))
        with col4:
            st.metric("ℹ️ Upcoming", len(info))
        
        st.markdown("---")
        
        # Display alerts by category
        if expired:
            st.markdown("#### 🔴 Expired Documents")
            for alert in expired:
                st.error(f"❌ **{alert['name']}** ({alert['position']}) - {alert['document']}: Expired {abs(alert['days_until'])} days ago")
        
        if critical:
            st.markdown("#### 🟠 Critical (≤7 days)")
            for alert in critical:
                st.warning(f"⏰ **{alert['name']}** ({alert['position']}) - {alert['document']}: Expires in {alert['days_until']} days")
        
        if warning:
            st.markdown("#### 🟡 Warning (≤14 days)")
            for alert in warning:
                st.info(f"📅 **{alert['name']}** ({alert['position']}) - {alert['document']}: Expires in {alert['days_until']} days")
        
        if info:
            st.markdown("#### ℹ️ Upcoming (≤30 days)")
            for alert in info:
                st.write(f"📆 **{alert['name']}** ({alert['position']}) - {alert['document']}: Expires in {alert['days_until']} days")
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
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            filter_dept = st.selectbox("Department", ["All", "Operations", "Maintenance", "Administration", "HR"])
        with col_f2:
            filter_status = st.selectbox("Status", ["All", "Active", "On Leave", "Terminated"])
        with col_f3:
            filter_position = st.selectbox("Position Type", ["All", "Drivers", "Conductors", "Other Staff"])
        with col_f4:
            search_name = st.text_input("🔍 Search by name", placeholder="Employee name")
        
        # Check for expiring documents
        with st.expander("⚠️ Document Expiry Alerts", expanded=False):
            display_document_expiry_alerts()
        
        st.markdown("---")
        
        # Fetch employees
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, employee_id, full_name, position, department, hire_date, 
                   salary, phone, email, address, status, date_of_birth, 
                   emergency_contact, emergency_phone, license_number, license_expiry,
                   defensive_driving_expiry, medical_cert_expiry, retest_date,
                   created_by, created_at 
            FROM employees WHERE 1=1
        """
        params = []
        
        if filter_dept != "All":
            query += " AND department = ?"
            params.append(filter_dept)
        
        if filter_status != "All":
            query += " AND status = ?"
            params.append(filter_status)
        
        if filter_position == "Drivers":
            query += " AND position LIKE '%Driver%'"
        elif filter_position == "Conductors":
            query += " AND position LIKE '%Conductor%'"
        elif filter_position == "Other Staff":
            query += " AND position NOT LIKE '%Driver%' AND position NOT LIKE '%Conductor%'"
        
        if search_name:
            query += " AND full_name LIKE ?"
            params.append(f"%{search_name}%")
        
        query += " ORDER BY full_name"
        
        execute_hr_query(cursor, query, params)
        employees = cursor.fetchall()
        conn.close()
        
        if employees:
            # Summary stats
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            with col_stat1:
                st.metric("👥 Total Employees", len(employees))
            with col_stat2:
                active_count = sum(1 for emp in employees if get_emp_value(emp, 'status') == 'Active')
                st.metric("✅ Active", active_count)
            with col_stat3:
                drivers_count = sum(1 for emp in employees if 'driver' in (get_emp_value(emp, 'position') or '').lower())
                st.metric("🚗 Drivers", drivers_count)
            with col_stat4:
                total_salary = sum(get_emp_value(emp, 'salary', 0) or 0 for emp in employees)
                st.metric("💰 Total Salary", f"${total_salary:,.2f}")
            
            st.markdown("---")
            
            # Display employees
            for emp in employees:
                (emp_id, employee_id, full_name, position, department, hire_date, 
                 salary, phone, email, address, status, dob, emerg_contact, emerg_phone,
                 nok_relationship, national_id, license_num, license_exp, defensive_exp, 
                 medical_exp, retest, created_by, created_at) = unpack_employee(emp)
                
                status_icon = "✅" if status == "Active" else "⏸️" if status == "On Leave" else "❌"
                
                # Check for expiring documents
                doc_warnings = []
                if position and 'driver' in position.lower():
                    current_date = datetime.now().date()
                    threshold = current_date + timedelta(days=30)
                    
                    if license_exp:
                        try:
                            exp_date = datetime.strptime(license_exp, '%Y-%m-%d').date()
                            if exp_date <= threshold:
                                days_left = (exp_date - current_date).days
                                if days_left < 0:
                                    doc_warnings.append(f"🔴 License EXPIRED")
                                elif days_left <= 7:
                                    doc_warnings.append(f"🟠 License expires in {days_left} days")
                                else:
                                    doc_warnings.append(f"🟡 License expires in {days_left} days")
                        except:
                            pass
                    
                    # Check other documents similarly
                    for exp_date, doc_name in [(defensive_exp, "Defensive"), (medical_exp, "Medical"), (retest, "Retest")]:
                        if exp_date:
                            try:
                                exp = datetime.strptime(exp_date, '%Y-%m-%d').date()
                                if exp <= threshold:
                                    days_left = (exp - current_date).days
                                    if days_left < 0:
                                        doc_warnings.append(f"🔴 {doc_name} EXPIRED")
                                    elif days_left <= 7:
                                        doc_warnings.append(f"🟠 {doc_name} expires in {days_left} days")
                            except:
                                pass
                
                # Build expander title
                title = f"{status_icon} {full_name} - {position} ({employee_id})"
                if doc_warnings:
                    title += f" ⚠️ {len(doc_warnings)} Alert(s)"
                
                with st.expander(title):
                    # Show document warnings first if any
                    if doc_warnings:
                        st.warning("**⚠️ Document Alerts:**")
                        for warning in doc_warnings:
                            st.markdown(f"- {warning}")
                        st.markdown("---")
                    
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.markdown("##### 👤 Basic Information")
                        st.write(f"**Employee ID:** {employee_id}")
                        st.write(f"**National ID:** {national_id or 'N/A'}")
                        st.write(f"**Position:** {position}")
                        st.write(f"**Department:** {department}")
                        st.write(f"**Salary:** ${salary:,.2f}")
                        st.write(f"**Status:** {status}")
                        st.write(f"**Hire Date:** {hire_date}")
                        if dob:
                            age = (datetime.now().date() - datetime.strptime(dob, '%Y-%m-%d').date()).days // 365
                            st.write(f"**Age:** {age} years")
                    
                    with col_info2:
                        st.markdown("##### 📞 Contact Information")
                        st.write(f"**Phone:** {phone or 'N/A'}")
                        st.write(f"**Email:** {email or 'N/A'}")
                        st.write(f"**Address:** {address or 'N/A'}")
                        
                        if emerg_contact:
                            st.markdown("##### 🆘 Next of Kin")
                            st.write(f"**Name:** {emerg_contact}")
                            st.write(f"**Phone:** {emerg_phone or 'N/A'}")
                            st.write(f"**Relationship:** {nok_relationship or 'N/A'}")
                    
                    # Driver documents section
                    if 'driver' in position.lower():
                        st.markdown("---")
                        st.markdown("##### 🚗 Driver Documents")
                        
                        doc_col1, doc_col2 = st.columns(2)
                        
                        with doc_col1:
                            if license_num:
                                st.write(f"**License Number:** {license_num}")
                            if license_exp:
                                days_to_exp = (datetime.strptime(license_exp, '%Y-%m-%d').date() - datetime.now().date()).days
                                if days_to_exp < 0:
                                    st.error(f"**License Expiry:** {license_exp} (EXPIRED)")
                                elif days_to_exp <= 30:
                                    st.warning(f"**License Expiry:** {license_exp} ({days_to_exp} days)")
                                else:
                                    st.info(f"**License Expiry:** {license_exp}")
                            
                            if defensive_exp:
                                days_to_exp = (datetime.strptime(defensive_exp, '%Y-%m-%d').date() - datetime.now().date()).days
                                if days_to_exp < 0:
                                    st.error(f"**Defensive Driving:** {defensive_exp} (EXPIRED)")
                                elif days_to_exp <= 30:
                                    st.warning(f"**Defensive Driving:** {defensive_exp} ({days_to_exp} days)")
                                else:
                                    st.info(f"**Defensive Driving:** {defensive_exp}")
                        
                        with doc_col2:
                            if medical_exp:
                                days_to_exp = (datetime.strptime(medical_exp, '%Y-%m-%d').date() - datetime.now().date()).days
                                if days_to_exp < 0:
                                    st.error(f"**Medical Certificate:** {medical_exp} (EXPIRED)")
                                elif days_to_exp <= 30:
                                    st.warning(f"**Medical Certificate:** {medical_exp} ({days_to_exp} days)")
                                else:
                                    st.info(f"**Medical Certificate:** {medical_exp}")
                            
                            if retest:
                                days_to_exp = (datetime.strptime(retest, '%Y-%m-%d').date() - datetime.now().date()).days
                                if days_to_exp < 0:
                                    st.error(f"**Retest Date:** {retest} (OVERDUE)")
                                elif days_to_exp <= 30:
                                    st.warning(f"**Retest Date:** {retest} ({days_to_exp} days)")
                                else:
                                    st.info(f"**Retest Date:** {retest}")
                    
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
                                conn = get_connection()
                                cursor = conn.cursor()
                                execute_hr_query(cursor, "UPDATE employees SET status = 'Terminated' WHERE id = ?", (emp_id,))
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
                                conn = get_connection()
                                cursor = conn.cursor()
                                execute_hr_query(cursor, "DELETE FROM employees WHERE id = ?", (emp_id,))
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
                    
                    # Edit mode (includes all new fields)
                    if st.session_state.get(f'edit_emp_mode_{emp_id}', False):
                        st.markdown("---")
                        st.markdown("**Edit Employee:**")
                        
                        with st.form(f"edit_emp_form_{emp_id}"):
                            st.markdown("#### 👤 Basic Information")
                            edit_col1, edit_col2 = st.columns(2)
                            
                            with edit_col1:
                                new_full_name = st.text_input("Full Name", value=full_name)
                                new_national_id = st.text_input("National ID Number", value=national_id or "", placeholder="e.g., 63-123456-A-42")
                                new_position = st.text_input("Position", value=position)
                                new_department = st.selectbox(
                                    "Department",
                                    ["Operations", "Maintenance", "Administration", "HR"],
                                    index=["Operations", "Maintenance", "Administration", "HR"].index(department) if department in ["Operations", "Maintenance", "Administration", "HR"] else 0
                                )
                                new_salary = st.number_input("Salary", value=float(salary))
                                new_status = st.selectbox(
                                    "Status",
                                    ["Active", "On Leave", "Terminated"],
                                    index=["Active", "On Leave", "Terminated"].index(status) if status in ["Active", "On Leave", "Terminated"] else 0
                                )
                            
                            with edit_col2:
                                if dob:
                                    new_dob = st.date_input("Date of Birth", value=datetime.strptime(dob, '%Y-%m-%d'))
                                else:
                                    new_dob = st.date_input("Date of Birth", value=datetime(1990, 1, 1))
                                
                                new_phone = st.text_input("Phone", value=phone or "")
                                new_email = st.text_input("Email", value=email or "")
                                new_address = st.text_area("Address", value=address or "")
                            
                            st.markdown("#### 🆘 Next of Kin / Emergency Contact")
                            emerg_col1, emerg_col2 = st.columns(2)
                            
                            with emerg_col1:
                                new_emerg_contact = st.text_input("Next of Kin Name", value=emerg_contact or "")
                                new_emerg_phone = st.text_input("Next of Kin Phone", value=emerg_phone or "")
                            with emerg_col2:
                                relationship_options = ["Spouse", "Parent", "Sibling", "Child", "Other Relative", "Friend", "Other"]
                                current_rel_index = relationship_options.index(nok_relationship) if nok_relationship in relationship_options else 0
                                new_nok_relationship = st.selectbox("Relationship", relationship_options, index=current_rel_index)
                            
                            # Driver documents
                            if 'driver' in new_position.lower():
                                st.markdown("#### 🚗 Driver Documents")
                                doc_edit_col1, doc_edit_col2 = st.columns(2)
                                
                                with doc_edit_col1:
                                    new_license_num = st.text_input("License Number", value=license_num or "")
                                    if license_exp:
                                        new_license_exp = st.date_input("License Expiry", value=datetime.strptime(license_exp, '%Y-%m-%d'))
                                    else:
                                        new_license_exp = st.date_input("License Expiry", value=datetime.now() + timedelta(days=365))
                                    
                                    if defensive_exp:
                                        new_defensive_exp = st.date_input("Defensive Driving Expiry", value=datetime.strptime(defensive_exp, '%Y-%m-%d'))
                                    else:
                                        new_defensive_exp = st.date_input("Defensive Driving Expiry", value=datetime.now() + timedelta(days=365))
                                
                                with doc_edit_col2:
                                    if medical_exp:
                                        new_medical_exp = st.date_input("Medical Certificate Expiry", value=datetime.strptime(medical_exp, '%Y-%m-%d'))
                                    else:
                                        new_medical_exp = st.date_input("Medical Certificate Expiry", value=datetime.now() + timedelta(days=365))
                                    
                                    if retest:
                                        new_retest = st.date_input("Next Retest Date", value=datetime.strptime(retest, '%Y-%m-%d'))
                                    else:
                                        new_retest = st.date_input("Next Retest Date", value=datetime.now() + timedelta(days=180))
                            else:
                                new_license_num = None
                                new_license_exp = None
                                new_defensive_exp = None
                                new_medical_exp = None
                                new_retest = None
                            
                            col_save, col_cancel = st.columns(2)
                            
                            with col_save:
                                if st.form_submit_button("💾 Save", width="stretch"):
                                    conn = get_connection()
                                    cursor = conn.cursor()
                                    execute_hr_query(cursor, '''
                                        UPDATE employees
                                        SET full_name = ?, position = ?, department = ?, salary = ?,
                                            phone = ?, email = ?, address = ?, status = ?, date_of_birth = ?,
                                            emergency_contact = ?, emergency_phone = ?, next_of_kin_relationship = ?,
                                            national_id = ?, license_number = ?,
                                            license_expiry = ?, defensive_driving_expiry = ?, 
                                            medical_cert_expiry = ?, retest_date = ?
                                        WHERE id = ?
                                    ''', (new_full_name, new_position, new_department, new_salary,
                                          new_phone, new_email, new_address, new_status,
                                          new_dob.strftime("%Y-%m-%d") if new_dob else None,
                                          new_emerg_contact, new_emerg_phone, new_nok_relationship,
                                          new_national_id, new_license_num,
                                          new_license_exp.strftime("%Y-%m-%d") if new_license_exp else None,
                                          new_defensive_exp.strftime("%Y-%m-%d") if new_defensive_exp else None,
                                          new_medical_exp.strftime("%Y-%m-%d") if new_medical_exp else None,
                                          new_retest.strftime("%Y-%m-%d") if new_retest else None,
                                          emp_id))
                                    conn.commit()
                                    conn.close()
                                    
                                    AuditLogger.log_action(
                                        action_type="Edit",
                                        module="Employee",
                                        description=f"Updated employee: {new_full_name} (ID: {employee_id})",
                                        affected_table="employees",
                                        affected_record_id=emp_id
                                    )
                                    
                                    st.success("Employee updated!")
                                    st.session_state[f'edit_emp_mode_{emp_id}'] = False
                                    st.rerun()
                            
                            with col_cancel:
                                if st.form_submit_button("❌ Cancel", width="stretch"):
                                    st.session_state[f'edit_emp_mode_{emp_id}'] = False
                                    st.rerun()
        else:
            st.info("No employees found. Add your first employee in the 'Add New Employee' tab.")
    
    with tab2:
        st.subheader("Add New Employee")
        
        # Position selection for auto-ID generation
        position_preview = st.selectbox(
            "Position/Role*",
            ["Bus Driver", "Conductor", "Mechanic", "Office Staff", "HR Staff", 
             "Supervisor", "Manager", "Other"],
            key="position_preview"
        )
        
        # Generate and display auto ID
        conn_preview = get_connection()
        auto_employee_id = generate_employee_id(position_preview, conn_preview)
        conn_preview.close()
        
        st.info(f"🆔 **Auto-Generated Employee ID:** `{auto_employee_id}`")
        st.caption("This ID is automatically assigned based on the selected position")
        
        st.markdown("---")
        
        with st.form("new_employee_form"):
            # Basic Information
            st.markdown("#### 👤 Basic Information")
            col1, col2 = st.columns(2)
            
            with col1:
                st.text_input("Employee ID* (Auto-Generated)", value=auto_employee_id, disabled=True)
                full_name = st.text_input("Full Name*", placeholder="e.g., John Doe")
                position = st.selectbox(
                    "Position/Role*",
                    ["Bus Driver", "Conductor", "Mechanic", "Office Staff", "HR Staff", 
                     "Supervisor", "Manager", "Other"],
                    index=["Bus Driver", "Conductor", "Mechanic", "Office Staff", "HR Staff", 
                           "Supervisor", "Manager", "Other"].index(position_preview)
                )
                department = st.selectbox("Department*", ["Operations", "Maintenance", "Administration", "HR"])
            
            with col2:
                national_id = st.text_input("National ID Number*", placeholder="e.g., 63-123456-A-42")
                date_of_birth = st.date_input("Date of Birth", 
                    value=datetime(1990, 1, 1),
                    min_value=datetime(1940, 1, 1),
                    max_value=datetime.now() - timedelta(days=365*18))  # Must be 18+
                hire_date = st.date_input("Hire Date*", datetime.now())
                salary = st.number_input("Salary*", min_value=0.0, step=100.0, format="%.2f")
            
            st.markdown("---")
            
            # Contact Information
            st.markdown("#### 📞 Contact Information")
            col3, col4 = st.columns(2)
            
            with col3:
                phone = st.text_input("Phone", placeholder="+263 xxx xxx xxx")
                email = st.text_input("Email", placeholder="employee@example.com")
            
            with col4:
                address = st.text_area("Residential Address", placeholder="Full residential address...")
            
            st.markdown("---")
            
            # Emergency Contact / Next of Kin
            st.markdown("#### 🆘 Next of Kin / Emergency Contact")
            col_nok1, col_nok2 = st.columns(2)
            
            with col_nok1:
                emergency_contact = st.text_input("Next of Kin Name*", placeholder="Full name")
                emergency_phone = st.text_input("Next of Kin Phone*", placeholder="+263 xxx xxx xxx")
            
            with col_nok2:
                next_of_kin_relationship = st.selectbox("Relationship*", 
                    ["Spouse", "Parent", "Sibling", "Child", "Other Relative", "Friend", "Other"])
            
            # Driver-specific documents (only show if position is Driver)
            if 'driver' in position.lower():
                st.markdown("---")
                st.markdown("#### 🚗 Driver Documents & Certifications")
                
                col5, col6 = st.columns(2)
                
                with col5:
                    license_number = st.text_input("Driver License Number*", placeholder="e.g., 12345678")
                    license_expiry = st.date_input("License Expiry Date*", 
                        value=datetime.now() + timedelta(days=365))
                    defensive_driving_expiry = st.date_input("Defensive Driving Cert Expiry", 
                        value=datetime.now() + timedelta(days=365))
                
                with col6:
                    medical_cert_expiry = st.date_input("Medical Certificate Expiry", 
                        value=datetime.now() + timedelta(days=365))
                    retest_date = st.date_input("Next Retest Date", 
                        value=datetime.now() + timedelta(days=180))
                
                st.info("📅 **Reminder:** You'll receive alerts 30 days before any document expires")
            else:
                license_number = None
                license_expiry = None
                defensive_driving_expiry = None
                medical_cert_expiry = None
                retest_date = None
            
            st.markdown("---")
            
            # Info box
            with st.expander("ℹ️ About Employee ID System"):
                st.write("""
                **Automatic ID Assignment:**
                - **Drivers**: PavD001, PavD002, PavD003... (for bus pairing & income tracking)
                - **Conductors**: PavC001, PavC002, PavC003... (for bus pairing & income tracking)
                - **Other Staff**: Pav001, Pav002, Pav003... (Mechanics, Office Staff, HR, etc.)
                
                The system automatically assigns the next available ID based on your selected position.
                """)
            
            submitted = st.form_submit_button("➕ Add Employee", width="stretch", type="primary")
            
            if submitted:
                # Validation
                required_fields = [full_name, position, department, salary > 0, national_id, emergency_contact]
                
                if 'driver' in position.lower():
                    required_fields.extend([license_number, license_expiry])
                
                if not all(required_fields):
                    st.error("⚠️ Please fill in all required fields")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    # Generate final employee ID
                    final_employee_id = generate_employee_id(position, conn)
                    
                    try:
                        execute_hr_query(cursor, '''
                            INSERT INTO employees 
                            (employee_id, full_name, position, department, hire_date, salary, 
                             phone, email, address, status, date_of_birth, emergency_contact, 
                             emergency_phone, next_of_kin_relationship, national_id,
                             license_number, license_expiry, 
                             defensive_driving_expiry, medical_cert_expiry, retest_date, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            final_employee_id, full_name, position, department, 
                            hire_date.strftime("%Y-%m-%d"), salary, phone, email, address,
                            date_of_birth.strftime("%Y-%m-%d") if date_of_birth else None,
                            emergency_contact, emergency_phone, next_of_kin_relationship, national_id,
                            license_number,
                            license_expiry.strftime("%Y-%m-%d") if license_expiry else None,
                            defensive_driving_expiry.strftime("%Y-%m-%d") if defensive_driving_expiry else None,
                            medical_cert_expiry.strftime("%Y-%m-%d") if medical_cert_expiry else None,
                            retest_date.strftime("%Y-%m-%d") if retest_date else None,
                            st.session_state['user']['username']
                        ))
                        
                        conn.commit()
                        
                        AuditLogger.log_action(
                            action_type="Add",
                            module="Employee",
                            description=f"New employee added: {full_name} (ID: {final_employee_id}), {position}, {department}, Salary: ${salary:,.2f}",
                            affected_table="employees"
                        )
                        
                        st.success(f"✅ Employee {full_name} added successfully with ID: **{final_employee_id}**")
                        
                        # Check if any documents expire soon
                        if 'driver' in position.lower():
                            alerts = get_expiring_documents(days_threshold=30)
                            driver_alerts = [a for a in alerts if a['employee_id'] == final_employee_id]
                            if driver_alerts:
                                st.warning(f"⚠️ Note: {len(driver_alerts)} document(s) expire within 30 days for this driver")
                        
                        st.balloons()
                        
                    except sqlite3.IntegrityError:
                        st.error(f"❌ Employee ID '{final_employee_id}' already exists! Please refresh the page.")
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
        conn = get_connection()
        
        query = "SELECT * FROM employees WHERE 1=1"
        params = []
        
        if exp_dept != "All":
            query += " AND department = ?"
            params.append(exp_dept)
        
        if exp_status != "All":
            query += " AND status = ?"
            params.append(exp_status)
        
        export_df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
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
                    width="stretch"
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
                    width="stretch"
                )
            
            st.markdown("---")
            st.write("### Preview of Export Data")
            st.dataframe(export_df, width="stretch", height=300)
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
        
        conn = get_connection()
        
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
        
        conn = get_connection()
        try:
            employees_df = pd.read_sql_query("SELECT employee_id, full_name, position FROM employees WHERE status = 'Active'", get_engine())
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
                
                submitted = st.form_submit_button("➕ Submit Evaluation", width="stretch", type="primary")
                
                if submitted:
                    if not all([employee_id, evaluation_period, rating, evaluator]):
                        st.error("⚠️ Please fill in all required fields")
                    else:
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        execute_hr_query(cursor, '''
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
        
        conn = get_connection()
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
                    width="stretch"
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
                    width="stretch"
                )
            
            st.markdown("---")
            st.dataframe(perf_export_df, width="stretch", height=300)
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
        
        conn = get_connection()
        
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
            payroll_df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
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
                            conn = get_connection()
                            cursor = conn.cursor()
                            execute_hr_query(cursor, '''
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
        conn = get_connection()
        try:
            employees_df = pd.read_sql_query("SELECT employee_id, full_name, position, salary FROM employees WHERE status = 'Active'", get_engine())
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
                
                submitted = st.form_submit_button("💰 Process Payroll", width="stretch", type="primary")
                
                if submitted:
                    if not all([employee_id, pay_period, basic_salary >= 0]):
                        st.error("⚠️ Please fill in all required fields")
                    else:
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        execute_hr_query(cursor, '''
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
        
        conn = get_connection()
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
                    width="stretch"
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
                    width="stretch"
                )
            
            st.markdown("---")
            st.dataframe(payroll_export_df, width="stretch", height=300)
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
        
        conn = get_connection()
        
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
            leave_df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
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
                                conn = get_connection()
                                cursor = conn.cursor()
                                execute_hr_query(cursor, '''
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
                                conn = get_connection()
                                cursor = conn.cursor()
                                execute_hr_query(cursor, '''
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
        conn = get_connection()
        try:
            employees_df = pd.read_sql_query("SELECT employee_id, full_name FROM employees WHERE status = 'Active'", get_engine())
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
                
                submitted = st.form_submit_button("➕ Submit Request", width="stretch", type="primary")
                
                if submitted:
                    if not all([employee_id, leave_type, reason]) or start_date > end_date:
                        st.error("⚠️ Please fill in all required fields and ensure start date is before end date")
                    else:
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        execute_hr_query(cursor, '''
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
        
        conn = get_connection()
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
                    width="stretch"
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
                    width="stretch"
                )
            
            st.markdown("---")
            st.dataframe(leave_export_df, width="stretch", height=300)
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
        
        conn = get_connection()
        
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
            disc_df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
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
                                conn = get_connection()
                                cursor = conn.cursor()
                                execute_hr_query(cursor, '''
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
                                conn = get_connection()
                                cursor = conn.cursor()
                                execute_hr_query(cursor, '''
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
        conn = get_connection()
        try:
            employees_df = pd.read_sql_query("SELECT employee_id, full_name, position FROM employees WHERE status = 'Active'", get_engine())
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
                
                submitted = st.form_submit_button("⚠️ Issue Disciplinary Action", width="stretch", type="primary")
                
                if submitted:
                    if not all([employee_id, action_type, violation_description, action_details, issued_by]):
                        st.error("⚠️ Please fill in all required fields")
                    else:
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        execute_hr_query(cursor, '''
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
        
        conn = get_connection()
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
                    width="stretch"
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
                    width="stretch"
                )
            
            st.markdown("---")
            st.dataframe(disc_export_df, width="stretch", height=300)
        else:
            st.warning("No disciplinary records found.")