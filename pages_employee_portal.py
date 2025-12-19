"""
pages_employee_portal.py - Employee Self-Service Portal
Pavillion Coaches Bus Management System

Features:
- Employee login (Full Name + National ID)
- View profile & employment details
- Download payslips (PDF)
- View pending loans, penalties, deductions
- View trip history & earnings
- Request leave
- Request loan
- Submit complaints/feedback
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import hashlib
import io

from database import get_connection, get_engine, USE_POSTGRES, get_placeholder
from audit_logger import AuditLogger

# PDF Generation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


# =============================================================================
# EMPLOYEE AUTHENTICATION
# =============================================================================

def get_employee_by_credentials(full_name, national_id):
    """Authenticate employee by full name and national ID"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        # Case-insensitive name match
        if USE_POSTGRES:
            cursor.execute(f"""
                SELECT id, employee_id, full_name, position, department, hire_date, 
                       salary, phone, email, status, national_id
                FROM employees 
                WHERE LOWER(full_name) = LOWER({ph}) 
                  AND national_id = {ph}
                  AND status = 'Active'
            """, (full_name, national_id))
        else:
            cursor.execute(f"""
                SELECT id, employee_id, full_name, position, department, hire_date, 
                       salary, phone, email, status, national_id
                FROM employees 
                WHERE LOWER(full_name) = LOWER({ph}) 
                  AND national_id = {ph}
                  AND status = 'Active'
            """, (full_name, national_id))
        
        result = cursor.fetchone()
        
        if result:
            # Convert to dict
            if hasattr(result, 'keys'):
                return dict(result)
            else:
                columns = ['id', 'employee_id', 'full_name', 'position', 'department', 
                          'hire_date', 'salary', 'phone', 'email', 'status', 'national_id']
                return dict(zip(columns, result))
        return None
    except Exception as e:
        print(f"Auth error: {e}")
        return None
    finally:
        conn.close()


def update_employee_last_login(employee_id):
    """Update last login timestamp"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        cursor.execute(f"""
            UPDATE employees SET last_login = CURRENT_TIMESTAMP 
            WHERE id = {ph}
        """, (employee_id,))
        conn.commit()
    except:
        pass
    finally:
        conn.close()


# =============================================================================
# DATA RETRIEVAL FUNCTIONS
# =============================================================================

def get_employee_trips(employee_id, start_date=None, end_date=None):
    """Get trip history for an employee"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = f"""
        SELECT date, bus_number, route, amount, passengers,
               driver_bonus, conductor_bonus,
               CASE 
                   WHEN driver_employee_id = {ph} THEN 'Driver'
                   WHEN conductor_employee_id = {ph} THEN 'Conductor'
               END as role
        FROM income
        WHERE driver_employee_id = {ph} OR conductor_employee_id = {ph}
    """
    params = [str(employee_id), str(employee_id), str(employee_id), str(employee_id)]
    
    if start_date:
        query += f" AND date >= {ph}"
        params.append(str(start_date))
    
    if end_date:
        query += f" AND date <= {ph}"
        params.append(str(end_date))
    
    query += " ORDER BY date DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params))
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_employee_payslips(employee_id):
    """Get payroll records for payslip generation"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = f"""
        SELECT pr.*, pp.period_name, pp.start_date, pp.end_date, pp.status as period_status
        FROM payroll_records pr
        JOIN payroll_periods pp ON pr.payroll_period_id = pp.id
        WHERE pr.employee_id = {ph}
          AND pp.status IN ('approved', 'paid')
        ORDER BY pp.start_date DESC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=(employee_id,))
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_employee_loans(employee_id):
    """Get active loans for an employee"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = f"""
        SELECT * FROM employee_loans
        WHERE employee_id = {ph}
        ORDER BY date_issued DESC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=(employee_id,))
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_employee_deductions(employee_id):
    """Get pending deductions for an employee"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = f"""
        SELECT * FROM employee_deductions
        WHERE employee_id = {ph}
        ORDER BY date_incurred DESC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=(employee_id,))
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_employee_red_tickets(employee_id):
    """Get red tickets for an employee (conductor)"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = f"""
        SELECT * FROM red_tickets
        WHERE conductor_id = {ph}
        ORDER BY ticket_date DESC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=(employee_id,))
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_employee_leave_records(employee_id):
    """Get leave records for an employee"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = f"""
        SELECT * FROM leave_records
        WHERE employee_id = {ph}
        ORDER BY start_date DESC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=(employee_id,))
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


def get_employee_requests(employee_id):
    """Get employee's pending requests"""
    conn = get_connection()
    ph = get_placeholder()
    
    query = f"""
        SELECT * FROM employee_requests
        WHERE employee_id = {ph}
        ORDER BY created_at DESC
    """
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=(employee_id,))
    except:
        df = pd.DataFrame()
    
    conn.close()
    return df


# =============================================================================
# REQUEST SUBMISSION FUNCTIONS
# =============================================================================

def submit_leave_request(employee_id, leave_type, start_date, end_date, reason):
    """Submit a leave request"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO leave_records 
                (employee_id, leave_type, start_date, end_date, reason, status)
                VALUES (%s, %s, %s, %s, %s, 'Pending')
                RETURNING id
            ''', (employee_id, leave_type, str(start_date), str(end_date), reason))
            result = cursor.fetchone()
            request_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO leave_records 
                (employee_id, leave_type, start_date, end_date, reason, status)
                VALUES (?, ?, ?, ?, ?, 'Pending')
            ''', (employee_id, leave_type, str(start_date), str(end_date), reason))
            request_id = cursor.lastrowid
        
        conn.commit()
        return request_id
    except Exception as e:
        conn.rollback()
        print(f"Leave request error: {e}")
        return None
    finally:
        conn.close()


def submit_loan_request(employee_id, amount, reason):
    """Submit a loan request"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO employee_requests 
                (employee_id, request_type, request_details, amount, status)
                VALUES (%s, 'Loan Request', %s, %s, 'pending')
                RETURNING id
            ''', (employee_id, reason, amount))
            result = cursor.fetchone()
            request_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO employee_requests 
                (employee_id, request_type, request_details, amount, status)
                VALUES (?, 'Loan Request', ?, ?, 'pending')
            ''', (employee_id, reason, amount))
            request_id = cursor.lastrowid
        
        conn.commit()
        return request_id
    except Exception as e:
        conn.rollback()
        print(f"Loan request error: {e}")
        return None
    finally:
        conn.close()


def submit_complaint(employee_id, subject, category, description):
    """Submit a complaint or feedback"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO employee_complaints 
                (employee_id, subject, category, description, status)
                VALUES (%s, %s, %s, %s, 'open')
                RETURNING id
            ''', (employee_id, subject, category, description))
            result = cursor.fetchone()
            complaint_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO employee_complaints 
                (employee_id, subject, category, description, status)
                VALUES (?, ?, ?, ?, 'open')
            ''', (employee_id, subject, category, description))
            complaint_id = cursor.lastrowid
        
        conn.commit()
        return complaint_id
    except Exception as e:
        conn.rollback()
        print(f"Complaint error: {e}")
        return None
    finally:
        conn.close()


# =============================================================================
# PAYSLIP PDF GENERATION
# =============================================================================

def generate_employee_payslip(payroll_record):
    """Generate PDF payslip for employee"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm,
                           leftMargin=15*mm, rightMargin=15*mm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], 
                                  fontSize=18, alignment=TA_CENTER, spaceAfter=5)
    header_style = ParagraphStyle('Header', parent=styles['Normal'],
                                   fontSize=10, alignment=TA_CENTER)
    
    story = []
    
    # Company Header
    story.append(Paragraph("PAVILLION COACHES", title_style))
    story.append(Paragraph("Cell: 0772 679 680 | Work: +263 24 2770931", header_style))
    story.append(Spacer(1, 10))
    
    # Payslip Title
    story.append(Paragraph("PAYSLIP", ParagraphStyle(
        'PayslipTitle', fontSize=16, alignment=TA_CENTER, 
        textColor=colors.darkblue, fontName='Helvetica-Bold'
    )))
    story.append(Spacer(1, 10))
    
    # Employee Info
    info_data = [
        ['Employee:', payroll_record.get('employee_name', 'N/A'), 
         'Role:', payroll_record.get('employee_role', 'N/A')],
        ['Period:', payroll_record.get('period_name', 'N/A'), 
         'Currency:', payroll_record.get('currency', 'USD')],
    ]
    
    info_table = Table(info_data, colWidths=[70, 160, 60, 140])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    # Work Summary for drivers/conductors
    if payroll_record.get('employee_role') in ['Driver', 'Conductor']:
        story.append(Paragraph("WORK SUMMARY", ParagraphStyle(
            'Section', fontSize=11, fontName='Helvetica-Bold', textColor=colors.darkblue
        )))
        
        work_data = [
            ['Total Trips:', str(payroll_record.get('total_trips', 0)),
             'Days Worked:', str(payroll_record.get('total_days_worked', 0))],
            ['Revenue Handled:', f"${payroll_record.get('total_revenue_handled', 0):,.2f}",
             'Passengers:', str(payroll_record.get('total_passengers', 0))],
        ]
        
        work_table = Table(work_data, colWidths=[100, 110, 100, 110])
        work_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(work_table)
        story.append(Spacer(1, 10))
    
    # Earnings & Deductions
    story.append(Paragraph("EARNINGS & DEDUCTIONS", ParagraphStyle(
        'Section', fontSize=11, fontName='Helvetica-Bold', textColor=colors.darkblue
    )))
    
    symbol = '$'
    
    pay_data = [
        ['EARNINGS', '', 'DEDUCTIONS', ''],
        ['Base Salary', f"{symbol}{payroll_record.get('base_salary', 0):,.2f}", 
         'PAYE Tax', f"{symbol}{payroll_record.get('paye_tax', 0):,.2f}"],
        ['Commission', f"{symbol}{payroll_record.get('commission_amount', 0):,.2f}", 
         'NSSA', f"{symbol}{payroll_record.get('nssa_employee', 0):,.2f}"],
        ['Bonuses', f"{symbol}{payroll_record.get('bonuses', 0):,.2f}", 
         'Loan Repayment', f"{symbol}{payroll_record.get('loan_deductions', 0):,.2f}"],
        ['Allowances', f"{symbol}{payroll_record.get('other_allowances', 0):,.2f}", 
         'Penalties', f"{symbol}{payroll_record.get('penalty_deductions', 0):,.2f}"],
        ['', '', 'Other', f"{symbol}{payroll_record.get('other_deductions', 0):,.2f}"],
        ['GROSS EARNINGS', f"{symbol}{payroll_record.get('gross_earnings', 0):,.2f}", 
         'TOTAL DEDUCTIONS', f"{symbol}{payroll_record.get('total_deductions', 0):,.2f}"],
    ]
    
    pay_table = Table(pay_data, colWidths=[110, 90, 110, 90])
    pay_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('BACKGROUND', (0, -1), (1, -1), colors.lightgreen),
        ('BACKGROUND', (2, -1), (3, -1), colors.Color(1, 0.85, 0.85)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(pay_table)
    story.append(Spacer(1, 15))
    
    # Net Pay
    net_pay_data = [
        ['NET PAY', f"{symbol}{payroll_record.get('net_pay', 0):,.2f}"]
    ]
    
    net_table = Table(net_pay_data, colWidths=[300, 100])
    net_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.2, 0.4, 0.6)),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(net_table)
    story.append(Spacer(1, 20))
    
    # Footer
    story.append(Paragraph(
        "This is a computer-generated payslip.",
        ParagraphStyle('Footer', fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
    ))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# =============================================================================
# MAIN PORTAL PAGE
# =============================================================================

def employee_portal_page():
    """Employee Self-Service Portal main page"""
    
    # Check if employee is logged in
    if 'portal_employee' not in st.session_state:
        show_portal_login()
        return
    
    employee = st.session_state['portal_employee']
    
    # Portal Header
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1B4F72 0%, #2E86AB 100%); 
                padding: 20px; border-radius: 10px; margin-bottom: 20px;">
        <h2 style="color: white; margin: 0;">👋 Welcome, {employee['full_name']}</h2>
        <p style="color: #E8E8E8; margin: 5px 0 0 0;">{employee['position']} | {employee['department']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Logout button
    col1, col2, col3 = st.columns([6, 1, 1])
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            del st.session_state['portal_employee']
            st.rerun()
    
    # Navigation tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏠 Dashboard",
        "📄 My Payslips",
        "📊 My Trips",
        "💳 Loans & Deductions",
        "📅 Leave",
        "📝 Requests"
    ])
    
    with tab1:
        portal_dashboard(employee)
    
    with tab2:
        portal_payslips(employee)
    
    with tab3:
        portal_trips(employee)
    
    with tab4:
        portal_loans_deductions(employee)
    
    with tab5:
        portal_leave(employee)
    
    with tab6:
        portal_requests(employee)


def show_portal_login():
    """Show employee login form"""
    
    st.markdown("""
    <div style="text-align: center; padding: 40px 0;">
        <h1>🚌 Employee Self-Service Portal</h1>
        <p style="color: #666;">PAVILLION COACHES</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="background: #f8f9fa; padding: 30px; border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        """, unsafe_allow_html=True)
        
        st.markdown("### 🔐 Employee Login")
        st.markdown("Enter your details to access the portal")
        
        full_name = st.text_input("Full Name", placeholder="Enter your full name as registered")
        national_id = st.text_input("National ID", placeholder="Enter your National ID number", type="password")
        
        if st.button("🔑 Login", type="primary", use_container_width=True):
            if not full_name or not national_id:
                st.error("Please enter both your name and National ID")
            else:
                employee = get_employee_by_credentials(full_name.strip(), national_id.strip())
                
                if employee:
                    st.session_state['portal_employee'] = employee
                    update_employee_last_login(employee['id'])
                    
                    AuditLogger.log_action(
                        "Login", "Employee Portal",
                        f"Employee {employee['full_name']} logged into self-service portal"
                    )
                    
                    st.success(f"✅ Welcome, {employee['full_name']}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials or account not active. Please contact HR.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("""
        <div style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
            <p>Having trouble logging in? Contact HR Department</p>
        </div>
        """, unsafe_allow_html=True)


def portal_dashboard(employee):
    """Employee dashboard with summary"""
    
    st.subheader("📊 My Dashboard")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    # Get this month's data
    today = datetime.now().date()
    month_start = today.replace(day=1)
    
    trips_df = get_employee_trips(employee['id'], start_date=month_start, end_date=today)
    loans_df = get_employee_loans(employee['id'])
    deductions_df = get_employee_deductions(employee['id'])
    
    with col1:
        month_trips = len(trips_df) if not trips_df.empty else 0
        st.metric("🚌 Trips This Month", month_trips)
    
    with col2:
        if not trips_df.empty:
            month_revenue = trips_df['amount'].sum()
            st.metric("💰 Revenue Handled", f"${month_revenue:,.2f}")
        else:
            st.metric("💰 Revenue Handled", "$0.00")
    
    with col3:
        active_loans = loans_df[loans_df['status'] == 'active'] if not loans_df.empty else pd.DataFrame()
        total_loan_balance = active_loans['balance'].sum() if not active_loans.empty else 0
        st.metric("💳 Loan Balance", f"${total_loan_balance:,.2f}")
    
    with col4:
        pending_ded = deductions_df[deductions_df['status'] == 'pending'] if not deductions_df.empty else pd.DataFrame()
        total_pending = pending_ded['amount'].sum() if not pending_ded.empty else 0
        st.metric("⚠️ Pending Deductions", f"${total_pending:,.2f}")
    
    st.markdown("---")
    
    # Profile Information
    st.markdown("### 👤 My Profile")
    
    profile_col1, profile_col2 = st.columns(2)
    
    with profile_col1:
        st.markdown(f"""
        **Employee ID:** {employee.get('employee_id', 'N/A')}  
        **Full Name:** {employee.get('full_name', 'N/A')}  
        **Position:** {employee.get('position', 'N/A')}  
        **Department:** {employee.get('department', 'N/A')}  
        """)
    
    with profile_col2:
        st.markdown(f"""
        **Hire Date:** {employee.get('hire_date', 'N/A')}  
        **Phone:** {employee.get('phone', 'N/A')}  
        **Email:** {employee.get('email', 'N/A')}  
        **Status:** ✅ {employee.get('status', 'N/A')}  
        """)
    
    st.markdown("---")
    
    # Recent Activity
    st.markdown("### 📋 Recent Trips")
    
    recent_trips = get_employee_trips(employee['id'])
    
    if not recent_trips.empty:
        display_df = recent_trips.head(5)[['date', 'bus_number', 'route', 'amount', 'role']].copy()
        display_df.columns = ['Date', 'Bus', 'Route', 'Amount', 'Role']
        display_df['Amount'] = display_df['Amount'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent trips recorded")


def portal_payslips(employee):
    """View and download payslips"""
    
    st.subheader("📄 My Payslips")
    
    payslips = get_employee_payslips(employee['id'])
    
    if payslips.empty:
        st.info("No payslips available yet. Payslips will appear here after payroll is processed.")
        return
    
    st.markdown(f"**{len(payslips)} payslip(s) available**")
    
    for idx, row in payslips.iterrows():
        period_name = row.get('period_name', 'Unknown Period')
        net_pay = row.get('net_pay', 0)
        status = row.get('period_status', 'N/A')
        
        with st.expander(f"📄 {period_name} - ${net_pay:,.2f}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                **Period:** {period_name}  
                **Gross Earnings:** ${row.get('gross_earnings', 0):,.2f}  
                **Total Deductions:** ${row.get('total_deductions', 0):,.2f}  
                **Net Pay:** ${net_pay:,.2f}  
                """)
                
                if row.get('employee_role') in ['Driver', 'Conductor']:
                    st.markdown(f"""
                    **Trips:** {row.get('total_trips', 0)} | **Days Worked:** {row.get('total_days_worked', 0)}  
                    **Commission Rate:** {row.get('commission_rate', 0)}%  
                    """)
            
            with col2:
                # Generate PDF
                payslip_data = row.to_dict()
                pdf_bytes = generate_employee_payslip(payslip_data)
                
                st.download_button(
                    label="⬇️ Download PDF",
                    data=pdf_bytes,
                    file_name=f"Payslip_{period_name.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key=f"payslip_{idx}"
                )


def portal_trips(employee):
    """View trip history and earnings"""
    
    st.subheader("📊 My Trips & Earnings")
    
    # Date filter
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("From", value=datetime.now().date().replace(day=1), key="trip_start")
    
    with col2:
        end_date = st.date_input("To", value=datetime.now().date(), key="trip_end")
    
    trips = get_employee_trips(employee['id'], start_date=start_date, end_date=end_date)
    
    if trips.empty:
        st.info("No trips recorded for the selected period")
        return
    
    # Summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🚌 Total Trips", len(trips))
    
    with col2:
        st.metric("💰 Total Revenue", f"${trips['amount'].sum():,.2f}")
    
    with col3:
        total_bonuses = (trips['driver_bonus'].sum() if 'driver_bonus' in trips.columns else 0) + \
                       (trips['conductor_bonus'].sum() if 'conductor_bonus' in trips.columns else 0)
        st.metric("🎁 Total Bonuses", f"${total_bonuses:,.2f}")
    
    with col4:
        total_passengers = trips['passengers'].sum() if 'passengers' in trips.columns else 0
        st.metric("👥 Passengers", int(total_passengers))
    
    st.markdown("---")
    
    # Trip list
    display_df = trips[['date', 'bus_number', 'route', 'amount', 'passengers', 'role']].copy()
    display_df.columns = ['Date', 'Bus', 'Route', 'Amount', 'Passengers', 'Role']
    display_df['Amount'] = display_df['Amount'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Export option
    csv = trips.to_csv(index=False)
    st.download_button(
        "📥 Export to CSV",
        data=csv,
        file_name=f"my_trips_{start_date}_{end_date}.csv",
        mime="text/csv"
    )


def portal_loans_deductions(employee):
    """View loans and deductions"""
    
    st.subheader("💳 My Loans & Deductions")
    
    tab_loans, tab_deductions, tab_red_tickets = st.tabs(["💳 Loans", "⚠️ Deductions", "🎫 Red Tickets"])
    
    with tab_loans:
        loans = get_employee_loans(employee['id'])
        
        if loans.empty:
            st.success("✅ No loans on record")
        else:
            active_loans = loans[loans['status'] == 'active']
            
            if not active_loans.empty:
                st.markdown("### Active Loans")
                
                for _, loan in active_loans.iterrows():
                    with st.expander(f"💳 {loan.get('loan_type', 'Loan')} - Balance: ${loan.get('balance', 0):,.2f}"):
                        st.markdown(f"""
                        **Principal Amount:** ${loan.get('principal_amount', 0):,.2f}  
                        **Amount Paid:** ${loan.get('amount_paid', 0):,.2f}  
                        **Remaining Balance:** ${loan.get('balance', 0):,.2f}  
                        **Monthly Deduction:** ${loan.get('monthly_deduction', 0):,.2f}  
                        **Date Issued:** {loan.get('date_issued', 'N/A')}  
                        """)
            else:
                st.success("✅ No active loans")
            
            # Loan history
            paid_loans = loans[loans['status'] == 'paid']
            if not paid_loans.empty:
                st.markdown("### Loan History")
                st.dataframe(paid_loans[['loan_type', 'principal_amount', 'date_issued', 'status']], 
                            use_container_width=True, hide_index=True)
    
    with tab_deductions:
        deductions = get_employee_deductions(employee['id'])
        
        if deductions.empty:
            st.success("✅ No deductions on record")
        else:
            pending = deductions[deductions['status'] == 'pending']
            
            if not pending.empty:
                st.warning(f"⚠️ You have {len(pending)} pending deduction(s)")
                
                for _, ded in pending.iterrows():
                    st.markdown(f"""
                    - **{ded.get('deduction_type', 'Deduction')}**: ${ded.get('amount', 0):,.2f}  
                      *{ded.get('description', 'No description')}* - {ded.get('date_incurred', 'N/A')}
                    """)
            else:
                st.success("✅ No pending deductions")
    
    with tab_red_tickets:
        red_tickets = get_employee_red_tickets(employee['id'])
        
        if red_tickets.empty:
            st.success("✅ No red tickets on record")
        else:
            pending_tickets = red_tickets[red_tickets['status'] == 'pending']
            
            if not pending_tickets.empty:
                st.warning(f"🎫 You have {len(pending_tickets)} pending red ticket(s)")
                
                total_pending = pending_tickets['amount'].sum()
                st.metric("Total Pending Amount", f"${total_pending:,.2f}")
                
                display_df = pending_tickets[['ticket_date', 'amount', 'description', 'inspector_name']].copy()
                display_df.columns = ['Date', 'Amount', 'Description', 'Issued By']
                display_df['Amount'] = display_df['Amount'].apply(lambda x: f"${x:,.2f}")
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.success("✅ No pending red tickets")


def portal_leave(employee):
    """View leave records and request leave"""
    
    st.subheader("📅 Leave Management")
    
    tab_history, tab_request = st.tabs(["📋 Leave History", "➕ Request Leave"])
    
    with tab_history:
        leave_records = get_employee_leave_records(employee['id'])
        
        if leave_records.empty:
            st.info("No leave records found")
        else:
            # Summary
            approved = len(leave_records[leave_records['status'] == 'Approved'])
            pending = len(leave_records[leave_records['status'] == 'Pending'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Requests", len(leave_records))
            with col2:
                st.metric("Approved", approved)
            with col3:
                st.metric("Pending", pending)
            
            st.markdown("---")
            
            for _, record in leave_records.iterrows():
                status_icon = "✅" if record.get('status') == 'Approved' else "⏳" if record.get('status') == 'Pending' else "❌"
                
                st.markdown(f"""
                {status_icon} **{record.get('leave_type', 'Leave')}** - {record.get('status', 'N/A')}  
                📅 {record.get('start_date', 'N/A')} to {record.get('end_date', 'N/A')}  
                *{record.get('reason', 'No reason provided')}*
                """)
                st.markdown("---")
    
    with tab_request:
        st.markdown("### ➕ New Leave Request")
        
        leave_type = st.selectbox("Leave Type", [
            "Annual Leave", "Sick Leave", "Compassionate Leave", 
            "Maternity Leave", "Paternity Leave", "Unpaid Leave", "Other"
        ])
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=datetime.now().date(), key="leave_start")
        with col2:
            end_date = st.date_input("End Date", value=datetime.now().date(), key="leave_end")
        
        reason = st.text_area("Reason", placeholder="Please explain the reason for your leave request...")
        
        if st.button("📤 Submit Leave Request", type="primary"):
            if end_date < start_date:
                st.error("End date cannot be before start date")
            elif not reason:
                st.error("Please provide a reason for your leave request")
            else:
                request_id = submit_leave_request(
                    employee['id'], leave_type, start_date, end_date, reason
                )
                
                if request_id:
                    st.success("✅ Leave request submitted successfully!")
                    st.info("Your request is pending approval. You will be notified once it's reviewed.")
                    st.rerun()
                else:
                    st.error("Error submitting leave request. Please try again.")


def portal_requests(employee):
    """View and submit requests"""
    
    st.subheader("📝 My Requests")
    
    tab_loan, tab_complaint, tab_history = st.tabs(["💰 Request Loan", "📝 Submit Feedback", "📋 Request History"])
    
    with tab_loan:
        st.markdown("### 💰 Loan Request")
        st.info("Submit a loan request to HR. Your request will be reviewed and you'll be notified of the decision.")
        
        loan_amount = st.number_input("Loan Amount ($)", min_value=10.0, step=10.0)
        loan_reason = st.text_area("Purpose of Loan", placeholder="Explain why you need this loan...")
        
        if st.button("📤 Submit Loan Request", type="primary"):
            if loan_amount <= 0:
                st.error("Please enter a valid loan amount")
            elif not loan_reason:
                st.error("Please explain the purpose of the loan")
            else:
                request_id = submit_loan_request(employee['id'], loan_amount, loan_reason)
                
                if request_id:
                    st.success("✅ Loan request submitted successfully!")
                    st.info("Your request will be reviewed by HR. You'll be notified of the decision.")
                else:
                    st.error("Error submitting loan request. Please try again.")
    
    with tab_complaint:
        st.markdown("### 📝 Feedback / Complaint")
        st.info("Submit feedback, suggestions, or complaints. All submissions are confidential.")
        
        categories = ["Workplace Issue", "Pay/Benefits", "Equipment/Tools", 
                     "Safety Concern", "Suggestion", "Other"]
        
        subject = st.text_input("Subject", placeholder="Brief summary of your feedback")
        category = st.selectbox("Category", categories)
        description = st.text_area("Description", placeholder="Provide details about your feedback or complaint...")
        
        if st.button("📤 Submit Feedback", type="primary", key="submit_complaint"):
            if not subject:
                st.error("Please enter a subject")
            elif not description:
                st.error("Please provide a description")
            else:
                complaint_id = submit_complaint(employee['id'], subject, category, description)
                
                if complaint_id:
                    st.success("✅ Feedback submitted successfully!")
                    st.info("Your submission has been received. HR will review and respond if necessary.")
                else:
                    st.error("Error submitting feedback. Please try again.")
    
    with tab_history:
        st.markdown("### 📋 My Request History")
        
        requests = get_employee_requests(employee['id'])
        
        if requests.empty:
            st.info("No requests submitted yet")
        else:
            for _, req in requests.iterrows():
                status = req.get('status', 'pending')
                status_icon = "✅" if status == 'approved' else "⏳" if status == 'pending' else "❌"
                
                with st.expander(f"{status_icon} {req.get('request_type', 'Request')} - {status.upper()}"):
                    st.markdown(f"""
                    **Type:** {req.get('request_type', 'N/A')}  
                    **Details:** {req.get('request_details', 'N/A')}  
                    **Amount:** ${req.get('amount', 0):,.2f}  
                    **Status:** {status.upper()}  
                    **Submitted:** {req.get('created_at', 'N/A')}  
                    """)
                    
                    if req.get('review_notes'):
                        st.markdown(f"**Review Notes:** {req.get('review_notes')}")
