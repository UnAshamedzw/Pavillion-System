"""
pages_payroll.py - Payroll Processing Module
Pavillion Coaches Bus Management System
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import json
import io

from database import get_connection, get_engine, USE_POSTGRES, get_placeholder
from audit_logger import AuditLogger
from auth import has_permission

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


def get_system_setting(key, default=None):
    """Get a system setting value"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    try:
        cursor.execute(f"SELECT setting_value FROM system_settings WHERE setting_key = {ph}", (key,))
        result = cursor.fetchone()
        if result:
            return result['setting_value'] if hasattr(result, 'keys') else result[0]
    except:
        pass
    finally:
        conn.close()
    return default


def get_tax_brackets():
    """Get active tax brackets"""
    conn = get_connection()
    try:
        query = "SELECT * FROM tax_brackets WHERE is_active = TRUE ORDER BY min_amount"
        df = pd.read_sql_query(query, get_engine())
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def calculate_paye(gross_amount, currency='USD'):
    """Calculate PAYE tax based on Zimbabwe tax brackets"""
    brackets = get_tax_brackets()
    if brackets.empty:
        return 0
    
    brackets = brackets[brackets['currency'] == currency] if 'currency' in brackets.columns else brackets
    
    tax = 0
    for _, bracket in brackets.iterrows():
        min_amt = bracket['min_amount']
        max_amt = bracket['max_amount'] if pd.notna(bracket['max_amount']) else float('inf')
        rate = bracket['tax_rate'] / 100
        fixed = bracket.get('fixed_amount', 0) or 0
        
        if gross_amount > min_amt:
            if gross_amount <= max_amt:
                taxable_in_bracket = gross_amount - min_amt
                tax = fixed + (taxable_in_bracket * rate)
                break
    
    return round(tax, 2)


def calculate_nssa(gross_amount):
    """Calculate NSSA contribution"""
    rate = float(get_system_setting('nssa_employee_rate', '4.5'))
    return round(gross_amount * (rate / 100), 2)


def aggregate_employee_trips(start_date, end_date):
    """Aggregate trip data for employees"""
    conn = get_connection()
    ph = get_placeholder()
    
    driver_query = f"""
        SELECT 
            driver_employee_id as employee_id,
            driver_name as employee_name,
            'Driver' as role,
            COUNT(*) as total_trips,
            COUNT(DISTINCT date) as days_worked,
            SUM(amount) as total_revenue,
            SUM(COALESCE(passengers, 0)) as total_passengers,
            SUM(COALESCE(driver_bonus, 0)) as total_bonuses
        FROM income
        WHERE date >= {ph} AND date <= {ph}
          AND driver_employee_id IS NOT NULL
        GROUP BY driver_employee_id, driver_name
    """
    
    conductor_query = f"""
        SELECT 
            conductor_employee_id as employee_id,
            conductor_name as employee_name,
            'Conductor' as role,
            COUNT(*) as total_trips,
            COUNT(DISTINCT date) as days_worked,
            SUM(amount) as total_revenue,
            SUM(COALESCE(passengers, 0)) as total_passengers,
            SUM(COALESCE(conductor_bonus, 0)) as total_bonuses
        FROM income
        WHERE date >= {ph} AND date <= {ph}
          AND conductor_employee_id IS NOT NULL
        GROUP BY conductor_employee_id, conductor_name
    """
    
    params = (str(start_date), str(end_date))
    
    try:
        driver_df = pd.read_sql_query(driver_query, get_engine(), params=params)
        conductor_df = pd.read_sql_query(conductor_query, get_engine(), params=params)
        combined = pd.concat([driver_df, conductor_df], ignore_index=True)
    except Exception as e:
        print(f"Aggregation error: {e}")
        combined = pd.DataFrame()
    
    conn.close()
    return combined


def get_pending_deductions(employee_id, start_date, end_date):
    """Get pending deductions for an employee"""
    conn = get_connection()
    ph = get_placeholder()
    try:
        query = f"""
            SELECT * FROM employee_deductions
            WHERE employee_id = {ph} AND status = 'pending'
              AND date_incurred >= {ph} AND date_incurred <= {ph}
        """
        df = pd.read_sql_query(query, get_engine(), params=(employee_id, str(start_date), str(end_date)))
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def get_active_loans(employee_id):
    """Get active loans for an employee"""
    conn = get_connection()
    ph = get_placeholder()
    try:
        query = f"""
            SELECT * FROM employee_loans
            WHERE employee_id = {ph} AND status = 'active' AND balance > 0
        """
        df = pd.read_sql_query(query, get_engine(), params=(employee_id,))
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def create_payroll_period(period_name, period_type, start_date, end_date, 
                          driver_rate, conductor_rate, currency, created_by):
    """Create a new payroll period"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO payroll_periods 
                (period_name, period_type, start_date, end_date, 
                 driver_commission_rate, conductor_commission_rate, currency, created_by, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'draft')
                RETURNING id
            ''', (period_name, period_type, start_date, end_date, 
                  driver_rate, conductor_rate, currency, created_by))
            result = cursor.fetchone()
            period_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO payroll_periods 
                (period_name, period_type, start_date, end_date, 
                 driver_commission_rate, conductor_commission_rate, currency, created_by, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft')
            ''', (period_name, period_type, str(start_date), str(end_date), 
                  driver_rate, conductor_rate, currency, created_by))
            period_id = cursor.lastrowid
        
        conn.commit()
        return period_id
    except Exception as e:
        conn.rollback()
        print(f"Error creating payroll period: {e}")
        return None
    finally:
        conn.close()


def save_payroll_record(period_id, emp_data):
    """Save a payroll record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO payroll_records 
                (payroll_period_id, employee_id, employee_name, employee_role, department,
                 total_trips, total_days_worked, total_revenue_handled, total_passengers,
                 base_salary, commission_rate, commission_amount, bonuses, gross_earnings,
                 paye_tax, nssa_employee, nssa_employer, loan_deductions, penalty_deductions,
                 total_deductions, net_pay, currency, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft')
                RETURNING id
            ''', (
                period_id, emp_data['employee_id'], emp_data['employee_name'],
                emp_data['role'], emp_data.get('department', ''),
                emp_data.get('total_trips', 0), emp_data.get('days_worked', 0),
                emp_data.get('total_revenue', 0), emp_data.get('total_passengers', 0),
                emp_data.get('base_salary', 0), emp_data.get('commission_rate', 0),
                emp_data.get('commission_amount', 0), emp_data.get('bonuses', 0),
                emp_data['gross_earnings'], emp_data['paye_tax'],
                emp_data['nssa_employee'], emp_data.get('nssa_employer', 0),
                emp_data.get('loan_deductions', 0), emp_data.get('penalty_deductions', 0),
                emp_data['total_deductions'], emp_data['net_pay'],
                emp_data.get('currency', 'USD')
            ))
            result = cursor.fetchone()
            record_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO payroll_records 
                (payroll_period_id, employee_id, employee_name, employee_role, department,
                 total_trips, total_days_worked, total_revenue_handled, total_passengers,
                 base_salary, commission_rate, commission_amount, bonuses, gross_earnings,
                 paye_tax, nssa_employee, nssa_employer, loan_deductions, penalty_deductions,
                 total_deductions, net_pay, currency, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
            ''', (
                period_id, emp_data['employee_id'], emp_data['employee_name'],
                emp_data['role'], emp_data.get('department', ''),
                emp_data.get('total_trips', 0), emp_data.get('days_worked', 0),
                emp_data.get('total_revenue', 0), emp_data.get('total_passengers', 0),
                emp_data.get('base_salary', 0), emp_data.get('commission_rate', 0),
                emp_data.get('commission_amount', 0), emp_data.get('bonuses', 0),
                emp_data['gross_earnings'], emp_data['paye_tax'],
                emp_data['nssa_employee'], emp_data.get('nssa_employer', 0),
                emp_data.get('loan_deductions', 0), emp_data.get('penalty_deductions', 0),
                emp_data['total_deductions'], emp_data['net_pay'],
                emp_data.get('currency', 'USD')
            ))
            record_id = cursor.lastrowid
        
        conn.commit()
        return record_id
    except Exception as e:
        conn.rollback()
        print(f"Error saving payroll record: {e}")
        return None
    finally:
        conn.close()


def get_payroll_periods(status=None):
    """Get payroll periods"""
    conn = get_connection()
    query = "SELECT * FROM payroll_periods WHERE 1=1"
    params = []
    
    if status:
        ph = get_placeholder()
        query += f" AND status = {ph}"
        params.append(status)
    
    query += " ORDER BY start_date DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def get_payroll_records(period_id):
    """Get payroll records for a period"""
    conn = get_connection()
    ph = get_placeholder()
    try:
        query = f"SELECT * FROM payroll_records WHERE payroll_period_id = {ph} ORDER BY employee_name"
        df = pd.read_sql_query(query, get_engine(), params=(period_id,))
    except:
        df = pd.DataFrame()
    conn.close()
    return df


def update_period_status(period_id, status, user):
    """Update payroll period status"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = get_placeholder()
    
    try:
        if status == 'approved':
            query = f"UPDATE payroll_periods SET status = {ph}, approved_by = {ph}, approved_at = CURRENT_TIMESTAMP WHERE id = {ph}"
            cursor.execute(query, (status, user, period_id))
        elif status == 'processing':
            query = f"UPDATE payroll_periods SET status = {ph}, processed_by = {ph}, processed_at = CURRENT_TIMESTAMP WHERE id = {ph}"
            cursor.execute(query, (status, user, period_id))
        else:
            query = f"UPDATE payroll_periods SET status = {ph} WHERE id = {ph}"
            cursor.execute(query, (status, period_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating status: {e}")
        return False
    finally:
        conn.close()


def push_to_expenses(period_id, period_name, total_amount, user):
    """Push payroll to expenses"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO expenses 
                (expense_date, category, description, amount, payment_method, status, created_by)
                VALUES (CURRENT_DATE, 'Salaries & Wages', %s, %s, 'Bank Transfer', 'Paid', %s)
            ''', (f"Payroll - {period_name}", total_amount, user))
        else:
            cursor.execute('''
                INSERT INTO expenses 
                (expense_date, category, description, amount, payment_method, status, created_by)
                VALUES (DATE('now'), 'Salaries & Wages', ?, ?, 'Bank Transfer', 'Paid', ?)
            ''', (f"Payroll - {period_name}", total_amount, user))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error pushing to expenses: {e}")
        return False
    finally:
        conn.close()


def generate_payslip_pdf(record, period_info):
    """Generate payslip PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER)
    
    story = []
    
    # Header
    company_name = get_system_setting('company_name', 'PAVILLION COACHES')
    story.append(Paragraph(company_name, title_style))
    story.append(Paragraph("PAYSLIP", ParagraphStyle('Sub', fontSize=14, alignment=TA_CENTER, textColor=colors.darkblue)))
    story.append(Spacer(1, 10))
    
    # Employee info
    info_data = [
        ['Employee:', record['employee_name'], 'Role:', record['employee_role']],
        ['Period:', period_info.get('period_name', 'N/A'), 'Currency:', record.get('currency', 'USD')],
    ]
    info_table = Table(info_data, colWidths=[70, 150, 60, 120])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    # Earnings & Deductions
    symbol = '$' if record.get('currency', 'USD') == 'USD' else 'ZiG '
    
    pay_data = [
        ['EARNINGS', '', 'DEDUCTIONS', ''],
        ['Base Salary', f"{symbol}{record.get('base_salary', 0):,.2f}", 'PAYE Tax', f"{symbol}{record.get('paye_tax', 0):,.2f}"],
        ['Commission', f"{symbol}{record.get('commission_amount', 0):,.2f}", 'NSSA', f"{symbol}{record.get('nssa_employee', 0):,.2f}"],
        ['Bonuses', f"{symbol}{record.get('bonuses', 0):,.2f}", 'Loans', f"{symbol}{record.get('loan_deductions', 0):,.2f}"],
        ['', '', 'Penalties', f"{symbol}{record.get('penalty_deductions', 0):,.2f}"],
        ['GROSS', f"{symbol}{record.get('gross_earnings', 0):,.2f}", 'TOTAL', f"{symbol}{record.get('total_deductions', 0):,.2f}"],
    ]
    
    pay_table = Table(pay_data, colWidths=[100, 90, 100, 90])
    pay_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
    ]))
    story.append(pay_table)
    story.append(Spacer(1, 15))
    
    # Net Pay
    net_data = [['NET PAY', f"{symbol}{record.get('net_pay', 0):,.2f}"]]
    net_table = Table(net_data, colWidths=[280, 100])
    net_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.2, 0.4, 0.6)),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(net_table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def payroll_processing_page():
    """Main payroll page"""
    st.header("💰 Payroll Processing")
    
    can_process = has_permission('manage_payroll')
    can_approve = has_permission('approve_payroll')
    can_view = has_permission('view_payroll')
    
    if not can_view:
        st.warning("You don't have permission to view payroll.")
        return
    
    tab1, tab2, tab3 = st.tabs(["📊 Generate Payroll", "📋 Payroll History", "📄 Payslips"])
    
    with tab1:
        if not can_process:
            st.warning("You don't have permission to process payroll.")
        else:
            generate_payroll_section()
    
    with tab2:
        payroll_history_section(can_approve)
    
    with tab3:
        payslips_section()


def generate_payroll_section():
    """Generate payroll section"""
    st.subheader("📊 Generate New Payroll")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        period_type = st.selectbox("Period Type", ["Monthly", "Weekly", "Custom"])
    
    with col2:
        year = st.selectbox("Year", range(datetime.now().year, 2020, -1))
    
    with col3:
        if period_type == "Monthly":
            month = st.selectbox("Month", range(1, 13), index=datetime.now().month - 1,
                               format_func=lambda x: datetime(2000, x, 1).strftime('%B'))
        else:
            month = 1
    
    with col4:
        currency = st.selectbox("Currency", ["USD", "ZiG"])
    
    # Calculate dates
    if period_type == "Monthly":
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        period_name = start_date.strftime('%B %Y')
    elif period_type == "Custom":
        col_a, col_b = st.columns(2)
        with col_a:
            start_date = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=30))
        with col_b:
            end_date = st.date_input("End Date", value=datetime.now().date())
        period_name = f"Custom: {start_date} to {end_date}"
    else:
        start_date = datetime.now().date() - timedelta(days=7)
        end_date = datetime.now().date()
        period_name = f"Week ending {end_date}"
    
    st.info(f"📅 Period: **{period_name}**")
    
    # Commission rates
    st.markdown("### 💵 Commission Rates")
    rate_col1, rate_col2 = st.columns(2)
    
    with rate_col1:
        driver_rate = st.slider("Driver Rate (%)", 0.0, 20.0, 8.0, 0.5)
    with rate_col2:
        conductor_rate = st.slider("Conductor Rate (%)", 0.0, 15.0, 5.0, 0.5)
    
    if st.button("📊 Preview Payroll", type="primary", use_container_width=True):
        with st.spinner("Calculating..."):
            trip_data = aggregate_employee_trips(start_date, end_date)
            
            if trip_data.empty:
                st.warning("No trip data found for this period.")
                return
            
            payroll_preview = []
            
            for _, row in trip_data.iterrows():
                emp_id = row['employee_id']
                role = row['role']
                comm_rate = driver_rate if role == 'Driver' else conductor_rate
                commission = row['total_revenue'] * (comm_rate / 100)
                bonuses = row.get('total_bonuses', 0) or 0
                gross = commission + bonuses
                
                paye = calculate_paye(gross, currency)
                nssa = calculate_nssa(gross)
                
                # Get deductions
                ded_df = get_pending_deductions(emp_id, start_date, end_date)
                penalty_total = ded_df['amount'].sum() if not ded_df.empty else 0
                
                loans_df = get_active_loans(emp_id)
                loan_ded = loans_df['monthly_deduction'].sum() if not loans_df.empty and 'monthly_deduction' in loans_df.columns else 0
                
                total_ded = paye + nssa + loan_ded + penalty_total
                net_pay = max(0, gross - total_ded)
                
                payroll_preview.append({
                    'employee_id': emp_id,
                    'employee_name': row['employee_name'],
                    'role': role,
                    'total_trips': row['total_trips'],
                    'days_worked': row['days_worked'],
                    'total_revenue': row['total_revenue'],
                    'total_passengers': row['total_passengers'],
                    'commission_rate': comm_rate,
                    'commission_amount': round(commission, 2),
                    'bonuses': round(bonuses, 2),
                    'gross_earnings': round(gross, 2),
                    'paye_tax': paye,
                    'nssa_employee': nssa,
                    'nssa_employer': nssa,
                    'loan_deductions': round(loan_ded, 2),
                    'penalty_deductions': round(penalty_total, 2),
                    'total_deductions': round(total_ded, 2),
                    'net_pay': round(net_pay, 2),
                    'currency': currency,
                })
            
            st.session_state['payroll_preview'] = payroll_preview
            st.session_state['period_info'] = {
                'period_name': period_name,
                'period_type': period_type.lower(),
                'start_date': start_date,
                'end_date': end_date,
                'driver_rate': driver_rate,
                'conductor_rate': conductor_rate,
                'currency': currency,
            }
    
    # Show preview
    if 'payroll_preview' in st.session_state:
        preview = st.session_state['payroll_preview']
        period_info = st.session_state['period_info']
        
        st.markdown(f"### 📋 Preview: {period_info['period_name']}")
        
        total_net = sum(p['net_pay'] for p in preview)
        col1, col2, col3 = st.columns(3)
        col1.metric("Employees", len(preview))
        col2.metric("Total Gross", f"${sum(p['gross_earnings'] for p in preview):,.2f}")
        col3.metric("Total Net", f"${total_net:,.2f}")
        
        df = pd.DataFrame(preview)[['employee_name', 'role', 'total_trips', 'commission_amount', 'bonuses', 'gross_earnings', 'total_deductions', 'net_pay']]
        df.columns = ['Employee', 'Role', 'Trips', 'Commission', 'Bonuses', 'Gross', 'Deductions', 'Net']
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        if st.button("✅ Save Payroll", type="primary", use_container_width=True):
            period_id = create_payroll_period(
                period_info['period_name'], period_info['period_type'],
                period_info['start_date'], period_info['end_date'],
                period_info['driver_rate'], period_info['conductor_rate'],
                period_info['currency'], st.session_state['user']['username']
            )
            
            if period_id:
                for emp in preview:
                    save_payroll_record(period_id, emp)
                
                update_period_status(period_id, 'processing', st.session_state['user']['username'])
                AuditLogger.log_action("Create", "Payroll", f"Created payroll: {period_info['period_name']}")
                st.success("✅ Payroll saved! Awaiting approval.")
                del st.session_state['payroll_preview']
                del st.session_state['period_info']
                st.rerun()


def payroll_history_section(can_approve):
    """Payroll history section"""
    st.subheader("📋 Payroll History")
    
    periods = get_payroll_periods()
    
    if periods.empty:
        st.info("No payroll periods found.")
        return
    
    for _, period in periods.iterrows():
        status_icon = {'draft': '📝', 'processing': '⏳', 'approved': '✅', 'paid': '💰'}.get(period['status'], '❓')
        
        with st.expander(f"{status_icon} {period['period_name']} - {period['status'].upper()}"):
            records = get_payroll_records(period['id'])
            
            if not records.empty:
                total = records['net_pay'].sum()
                st.metric("Total Net Pay", f"${total:,.2f}")
                
                display_df = records[['employee_name', 'employee_role', 'gross_earnings', 'total_deductions', 'net_pay']].copy()
                display_df.columns = ['Employee', 'Role', 'Gross', 'Deductions', 'Net']
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Approval buttons
                if period['status'] == 'processing' and can_approve:
                    if st.button(f"✅ Approve", key=f"approve_{period['id']}"):
                        update_period_status(period['id'], 'approved', st.session_state['user']['username'])
                        st.success("Approved!")
                        st.rerun()
                
                if period['status'] == 'approved' and can_approve:
                    if st.button(f"💰 Mark as Paid", key=f"pay_{period['id']}"):
                        push_to_expenses(period['id'], period['period_name'], total, st.session_state['user']['username'])
                        update_period_status(period['id'], 'paid', st.session_state['user']['username'])
                        st.success("Marked as paid and pushed to expenses!")
                        st.rerun()


def payslips_section():
    """Payslips section"""
    st.subheader("📄 Generate Payslips")
    
    periods = get_payroll_periods('paid')
    if periods.empty:
        periods = get_payroll_periods('approved')
    
    if periods.empty:
        st.info("No approved/paid payroll periods. Approve a payroll first.")
        return
    
    period_options = {f"{p['period_name']}": p['id'] for _, p in periods.iterrows()}
    selected = st.selectbox("Select Period", list(period_options.keys()))
    
    if selected:
        period_id = period_options[selected]
        period_info = periods[periods['id'] == period_id].iloc[0].to_dict()
        records = get_payroll_records(period_id)
        
        if not records.empty:
            emp_options = {r['employee_name']: idx for idx, r in records.iterrows()}
            selected_emp = st.selectbox("Select Employee", list(emp_options.keys()))
            
            if selected_emp and st.button("📄 Generate Payslip", type="primary"):
                record = records.iloc[emp_options[selected_emp]].to_dict()
                pdf_data = generate_payslip_pdf(record, period_info)
                
                st.download_button(
                    "⬇️ Download Payslip PDF",
                    data=pdf_data,
                    file_name=f"Payslip_{selected_emp}_{selected}.pdf",
                    mime="application/pdf"
                )
