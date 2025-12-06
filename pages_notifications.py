"""
pages_notifications.py - Email Notification System
Pavillion Coaches Bus Management System
Automatically sends email notifications for critical alerts
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES
from audit_logger import AuditLogger
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os


# =============================================================================
# DATABASE FUNCTIONS FOR NOTIFICATION SETTINGS
# =============================================================================

def get_notification_settings():
    """Get notification settings from database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT setting_key, setting_value FROM system_settings WHERE setting_key LIKE 'notif_%'")
        rows = cursor.fetchall()
        
        settings = {}
        for row in rows:
            if hasattr(row, 'keys'):
                settings[row['setting_key']] = row['setting_value']
            else:
                settings[row[0]] = row[1]
        
        return settings
    except:
        return {}
    finally:
        conn.close()


def save_notification_setting(key, value):
    """Save a notification setting"""
    conn = get_connection()
    cursor = conn.cursor()
    ph = '%s' if USE_POSTGRES else '?'
    
    try:
        # Check if exists
        cursor.execute(f"SELECT id FROM system_settings WHERE setting_key = {ph}", (key,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute(f"UPDATE system_settings SET setting_value = {ph} WHERE setting_key = {ph}", (value, key))
        else:
            cursor.execute(f"INSERT INTO system_settings (setting_key, setting_value) VALUES ({ph}, {ph})", (key, value))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving setting: {e}")
        return False
    finally:
        conn.close()


def create_settings_table():
    """Create system_settings table if it doesn't exist"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    id SERIAL PRIMARY KEY,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        conn.commit()
    except Exception as e:
        print(f"Table may already exist: {e}")
    finally:
        conn.close()


# =============================================================================
# ALERT COLLECTION FUNCTIONS
# =============================================================================

def get_bus_document_alerts(days_threshold=7):
    """Get critical bus document alerts"""
    conn = get_connection()
    
    query = """
        SELECT bus_number, 
               zinara_licence_expiry, vehicle_insurance_expiry, passenger_insurance_expiry,
               fitness_expiry
        FROM buses 
        WHERE status = 'Active'
    """
    
    df = pd.read_sql_query(query, get_engine())
    conn.close()
    
    alerts = []
    today = datetime.now().date()
    threshold_date = today + timedelta(days=days_threshold)
    
    doc_fields = [
        ('zinara_licence_expiry', 'ZINARA License'),
        ('vehicle_insurance_expiry', 'Vehicle Insurance'),
        ('passenger_insurance_expiry', 'Passenger Insurance'),
        ('fitness_expiry', 'Fitness Certificate')
    ]
    
    for _, row in df.iterrows():
        for field, doc_name in doc_fields:
            if row[field]:
                try:
                    exp_date = datetime.strptime(str(row[field]), '%Y-%m-%d').date()
                    days_left = (exp_date - today).days
                    
                    if days_left < 0:
                        alerts.append({
                            'type': 'bus_document',
                            'severity': 'EXPIRED',
                            'bus': row['bus_number'],
                            'document': doc_name,
                            'expiry_date': exp_date.strftime('%d/%m/%Y'),
                            'days': abs(days_left),
                            'message': f"🔴 {row['bus_number']}: {doc_name} EXPIRED {abs(days_left)} days ago"
                        })
                    elif days_left <= days_threshold:
                        alerts.append({
                            'type': 'bus_document',
                            'severity': 'CRITICAL' if days_left <= 3 else 'WARNING',
                            'bus': row['bus_number'],
                            'document': doc_name,
                            'expiry_date': exp_date.strftime('%d/%m/%Y'),
                            'days': days_left,
                            'message': f"🟠 {row['bus_number']}: {doc_name} expires in {days_left} days ({exp_date.strftime('%d/%m/%Y')})"
                        })
                except:
                    pass
    
    return alerts


def get_employee_document_alerts(days_threshold=7):
    """Get critical employee document alerts"""
    conn = get_connection()
    
    query = """
        SELECT employee_id, full_name, position,
               license_expiry, defensive_driving_expiry, medical_cert_expiry, retest_date
        FROM employees 
        WHERE status = 'Active'
    """
    
    df = pd.read_sql_query(query, get_engine())
    conn.close()
    
    alerts = []
    today = datetime.now().date()
    threshold_date = today + timedelta(days=days_threshold)
    
    doc_fields = [
        ('license_expiry', 'Driver License'),
        ('defensive_driving_expiry', 'Defensive Driving Certificate'),
        ('medical_cert_expiry', 'Medical Certificate'),
        ('retest_date', 'Retest Date')
    ]
    
    for _, row in df.iterrows():
        for field, doc_name in doc_fields:
            if row[field]:
                try:
                    exp_date = datetime.strptime(str(row[field]), '%Y-%m-%d').date()
                    days_left = (exp_date - today).days
                    
                    if days_left < 0:
                        alerts.append({
                            'type': 'employee_document',
                            'severity': 'EXPIRED',
                            'employee': row['full_name'],
                            'employee_id': row['employee_id'],
                            'document': doc_name,
                            'expiry_date': exp_date.strftime('%d/%m/%Y'),
                            'days': abs(days_left),
                            'message': f"🔴 {row['full_name']} ({row['employee_id']}): {doc_name} EXPIRED {abs(days_left)} days ago"
                        })
                    elif days_left <= days_threshold:
                        alerts.append({
                            'type': 'employee_document',
                            'severity': 'CRITICAL' if days_left <= 3 else 'WARNING',
                            'employee': row['full_name'],
                            'employee_id': row['employee_id'],
                            'document': doc_name,
                            'expiry_date': exp_date.strftime('%d/%m/%Y'),
                            'days': days_left,
                            'message': f"🟠 {row['full_name']} ({row['employee_id']}): {doc_name} expires in {days_left} days"
                        })
                except:
                    pass
    
    return alerts


def get_low_inventory_alerts(threshold=5):
    """Get low inventory alerts"""
    conn = get_connection()
    
    try:
        query = f"""
            SELECT part_number, part_name, quantity, minimum_stock, category
            FROM inventory 
            WHERE quantity <= minimum_stock OR quantity <= {threshold}
        """
        
        df = pd.read_sql_query(query, get_engine())
        conn.close()
        
        alerts = []
        for _, row in df.iterrows():
            qty = row['quantity']
            min_stock = row.get('minimum_stock', threshold)
            
            if qty == 0:
                severity = 'EXPIRED'  # Using EXPIRED for "Out of Stock"
                message = f"🔴 OUT OF STOCK: {row['part_name']} ({row['part_number']})"
            elif qty <= min_stock:
                severity = 'CRITICAL'
                message = f"🟠 LOW STOCK: {row['part_name']} ({row['part_number']}) - Only {qty} left"
            else:
                continue
            
            alerts.append({
                'type': 'inventory',
                'severity': severity,
                'part_name': row['part_name'],
                'part_number': row['part_number'],
                'quantity': qty,
                'message': message
            })
        
        return alerts
    except:
        return []


def get_overdue_maintenance_alerts():
    """Get overdue maintenance alerts"""
    conn = get_connection()
    
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        
        query = f"""
            SELECT bus_number, maintenance_type, description, scheduled_date
            FROM maintenance 
            WHERE status = 'Scheduled' AND scheduled_date < '{today}'
        """
        
        df = pd.read_sql_query(query, get_engine())
        conn.close()
        
        alerts = []
        for _, row in df.iterrows():
            alerts.append({
                'type': 'maintenance',
                'severity': 'CRITICAL',
                'bus': row['bus_number'],
                'maintenance_type': row['maintenance_type'],
                'message': f"🔧 OVERDUE: {row['bus_number']} - {row['maintenance_type']} was scheduled for {row['scheduled_date']}"
            })
        
        return alerts
    except:
        return []


def get_unpaid_expenses_alerts():
    """Get unpaid/overdue expense alerts"""
    conn = get_connection()
    
    try:
        query = """
            SELECT expense_date, category, description, amount, payment_status
            FROM general_expenses 
            WHERE payment_status IN ('Unpaid', 'Pending Approval')
            ORDER BY expense_date
            LIMIT 20
        """
        
        df = pd.read_sql_query(query, get_engine())
        conn.close()
        
        alerts = []
        for _, row in df.iterrows():
            alerts.append({
                'type': 'expense',
                'severity': 'WARNING',
                'category': row['category'],
                'amount': row['amount'],
                'message': f"💰 {row['payment_status'].upper()}: {row['category']} - {row['description']} (${row['amount']:,.2f})"
            })
        
        return alerts
    except:
        return []


def get_all_critical_alerts(days_threshold=7):
    """Collect all critical alerts"""
    all_alerts = {
        'bus_documents': get_bus_document_alerts(days_threshold),
        'employee_documents': get_employee_document_alerts(days_threshold),
        'inventory': get_low_inventory_alerts(),
        'maintenance': get_overdue_maintenance_alerts(),
        'expenses': get_unpaid_expenses_alerts()
    }
    
    # Count by severity
    expired_count = sum(1 for alerts in all_alerts.values() for a in alerts if a.get('severity') == 'EXPIRED')
    critical_count = sum(1 for alerts in all_alerts.values() for a in alerts if a.get('severity') == 'CRITICAL')
    warning_count = sum(1 for alerts in all_alerts.values() for a in alerts if a.get('severity') == 'WARNING')
    
    return {
        'alerts': all_alerts,
        'summary': {
            'expired': expired_count,
            'critical': critical_count,
            'warning': warning_count,
            'total': expired_count + critical_count + warning_count
        }
    }


# =============================================================================
# EMAIL FUNCTIONS
# =============================================================================

def send_email_via_resend(api_key, sender_email, recipient_emails, subject, html_body):
    """Send email using Resend API"""
    import requests
    
    # Ensure recipient_emails is a list
    if isinstance(recipient_emails, str):
        recipient_emails = [e.strip() for e in recipient_emails.split(',') if e.strip()]
    
    url = "https://api.resend.com/emails"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "from": sender_email,
        "to": recipient_emails,
        "subject": subject,
        "html": html_body
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            return True, "Email sent successfully via Resend"
        else:
            error_msg = response.json().get('message', response.text)
            return False, f"Resend API error ({response.status_code}): {error_msg}"
            
    except requests.exceptions.Timeout:
        return False, "Request timed out"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def send_email_via_smtp(smtp_server, smtp_port, sender_email, sender_password, recipient_emails, subject, html_body):
    """Send email using SMTP (fallback)"""
    import socket
    
    socket.setdefaulttimeout(30)
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipient_emails) if isinstance(recipient_emails, list) else recipient_emails
        
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        if isinstance(recipient_emails, str):
            recipient_emails = [recipient_emails]
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_emails, msg.as_string())
        server.quit()
        
        return True, "Email sent successfully via SMTP"
        
    except Exception as e:
        return False, f"SMTP error: {str(e)}"


def send_email(settings, recipient_emails, subject, html_body):
    """Send email using configured method (Resend API or SMTP)"""
    
    email_method = settings.get('notif_email_method', 'resend')
    
    if email_method == 'resend':
        api_key = settings.get('notif_resend_api_key', '')
        sender_email = settings.get('notif_sender_email', 'onboarding@resend.dev')
        
        if not api_key:
            return False, "Resend API key not configured"
        
        return send_email_via_resend(api_key, sender_email, recipient_emails, subject, html_body)
    else:
        # SMTP method
        smtp_server = settings.get('notif_smtp_server', 'smtp.gmail.com')
        smtp_port = int(settings.get('notif_smtp_port', 587))
        sender_email = settings.get('notif_sender_email', '')
        sender_password = settings.get('notif_sender_password', '')
        
        if not sender_email or not sender_password:
            return False, "SMTP credentials not configured"
        
        return send_email_via_smtp(smtp_server, smtp_port, sender_email, sender_password, recipient_emails, subject, html_body)


def build_alert_email_html(alerts_data, company_name="Pavillion Coaches"):
    """Build HTML email body for alerts"""
    
    summary = alerts_data['summary']
    alerts = alerts_data['alerts']
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: #1a365d; color: white; padding: 20px; text-align: center; }}
            .summary {{ background-color: #f7fafc; padding: 15px; margin: 20px 0; border-radius: 8px; }}
            .summary-box {{ display: inline-block; padding: 10px 20px; margin: 5px; border-radius: 5px; text-align: center; }}
            .expired {{ background-color: #fed7d7; color: #c53030; }}
            .critical {{ background-color: #feebc8; color: #c05621; }}
            .warning {{ background-color: #fefcbf; color: #975a16; }}
            .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #4299e1; background-color: #f7fafc; }}
            .section h3 {{ margin-top: 0; color: #2b6cb0; }}
            .alert-item {{ padding: 8px 0; border-bottom: 1px solid #e2e8f0; }}
            .alert-expired {{ color: #c53030; }}
            .alert-critical {{ color: #c05621; }}
            .alert-warning {{ color: #975a16; }}
            .footer {{ text-align: center; padding: 20px; color: #718096; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚌 {company_name}</h1>
            <h2>Critical Alerts Notification</h2>
            <p>{datetime.now().strftime('%A, %d %B %Y at %H:%M')}</p>
        </div>
        
        <div class="summary">
            <h3>📊 Alert Summary</h3>
            <div class="summary-box expired">
                <strong>{summary['expired']}</strong><br>Expired
            </div>
            <div class="summary-box critical">
                <strong>{summary['critical']}</strong><br>Critical
            </div>
            <div class="summary-box warning">
                <strong>{summary['warning']}</strong><br>Warning
            </div>
        </div>
    """
    
    # Bus Documents Section
    if alerts['bus_documents']:
        html += """
        <div class="section">
            <h3>🚗 Bus Document Alerts</h3>
        """
        for alert in sorted(alerts['bus_documents'], key=lambda x: x.get('days', 999)):
            css_class = f"alert-{alert['severity'].lower()}"
            html += f'<div class="alert-item {css_class}">{alert["message"]}</div>'
        html += "</div>"
    
    # Employee Documents Section
    if alerts['employee_documents']:
        html += """
        <div class="section">
            <h3>👤 Employee Document Alerts</h3>
        """
        for alert in sorted(alerts['employee_documents'], key=lambda x: x.get('days', 999)):
            css_class = f"alert-{alert['severity'].lower()}"
            html += f'<div class="alert-item {css_class}">{alert["message"]}</div>'
        html += "</div>"
    
    # Inventory Section
    if alerts['inventory']:
        html += """
        <div class="section">
            <h3>📦 Inventory Alerts</h3>
        """
        for alert in alerts['inventory']:
            css_class = f"alert-{alert['severity'].lower()}"
            html += f'<div class="alert-item {css_class}">{alert["message"]}</div>'
        html += "</div>"
    
    # Maintenance Section
    if alerts['maintenance']:
        html += """
        <div class="section">
            <h3>🔧 Overdue Maintenance</h3>
        """
        for alert in alerts['maintenance']:
            html += f'<div class="alert-item alert-critical">{alert["message"]}</div>'
        html += "</div>"
    
    # Expenses Section
    if alerts['expenses']:
        html += """
        <div class="section">
            <h3>💰 Unpaid Expenses</h3>
        """
        for alert in alerts['expenses'][:10]:  # Limit to 10
            html += f'<div class="alert-item alert-warning">{alert["message"]}</div>'
        if len(alerts['expenses']) > 10:
            html += f'<div class="alert-item">...and {len(alerts["expenses"]) - 10} more</div>'
        html += "</div>"
    
    html += f"""
        <div class="footer">
            <p>This is an automated notification from {company_name} Bus Management System.</p>
            <p>Please log in to the system to take action on these alerts.</p>
        </div>
    </body>
    </html>
    """
    
    return html


def send_alert_notification():
    """Send alert notification email"""
    settings = get_notification_settings()
    
    if not settings.get('notif_enabled') == 'true':
        return False, "Notifications are disabled"
    
    # Get recipient emails
    recipient_emails = settings.get('notif_recipients', '').split(',')
    recipient_emails = [e.strip() for e in recipient_emails if e.strip()]
    
    if not recipient_emails:
        return False, "No recipient emails configured"
    
    # Check if email method is configured
    email_method = settings.get('notif_email_method', 'resend')
    if email_method == 'resend':
        if not settings.get('notif_resend_api_key'):
            return False, "Resend API key not configured"
    else:
        if not settings.get('notif_sender_email') or not settings.get('notif_sender_password'):
            return False, "SMTP credentials not configured"
    
    # Get alerts
    days_threshold = int(settings.get('notif_days_threshold', 7))
    alerts_data = get_all_critical_alerts(days_threshold)
    
    if alerts_data['summary']['total'] == 0:
        return True, "No alerts to send"
    
    # Build and send email
    html_body = build_alert_email_html(alerts_data)
    subject = f"🚨 Pavillion Coaches: {alerts_data['summary']['total']} Alert(s) Require Attention"
    
    success, message = send_email(settings, recipient_emails, subject, html_body)
    
    if success:
        # Log the notification
        AuditLogger.log_action(
            "Send",
            "Notifications",
            f"Sent alert notification with {alerts_data['summary']['total']} alerts to {', '.join(recipient_emails)}"
        )
    
    return success, message


# =============================================================================
# PAGE FUNCTION
# =============================================================================

def notification_settings_page():
    """Notification Settings Page"""
    
    st.header("🔔 Notification Settings")
    st.markdown("Configure automatic email notifications for critical alerts")
    
    # Ensure settings table exists
    create_settings_table()
    
    # Get current settings
    settings = get_notification_settings()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["⚙️ Email Configuration", "📋 Alert Settings", "🧪 Test & Send"])
    
    with tab1:
        st.subheader("Email Configuration")
        
        # Email method selection
        email_method = st.radio(
            "Email Service",
            ["resend", "smtp"],
            index=0 if settings.get('notif_email_method', 'resend') == 'resend' else 1,
            format_func=lambda x: "📧 Resend API (Recommended)" if x == "resend" else "📮 SMTP (Gmail/Other)",
            horizontal=True
        )
        
        st.markdown("---")
        
        if email_method == "resend":
            st.info("""
            **Resend Setup (Free - 100 emails/day):**
            1. Go to **https://resend.com** and create a free account
            2. Get your **API Key** from the dashboard
            3. Use `onboarding@resend.dev` as sender for testing
            4. Or verify your own domain for custom sender email
            """)
            
            with st.form("resend_config_form"):
                resend_api_key = st.text_input(
                    "Resend API Key*",
                    value=settings.get('notif_resend_api_key', ''),
                    type="password",
                    placeholder="re_xxxxxxxxx..."
                )
                
                sender_email = st.text_input(
                    "Sender Email",
                    value=settings.get('notif_sender_email', 'onboarding@resend.dev'),
                    help="Use 'onboarding@resend.dev' for testing, or your verified domain email"
                )
                
                recipients = st.text_area(
                    "Recipient Emails*",
                    value=settings.get('notif_recipients', ''),
                    placeholder="email1@gmail.com, email2@gmail.com",
                    help="Comma-separated list of email addresses"
                )
                
                enabled = st.toggle(
                    "Enable Email Notifications",
                    value=settings.get('notif_enabled') == 'true'
                )
                
                if st.form_submit_button("💾 Save Resend Settings", type="primary"):
                    save_notification_setting('notif_email_method', 'resend')
                    save_notification_setting('notif_resend_api_key', resend_api_key)
                    save_notification_setting('notif_sender_email', sender_email)
                    save_notification_setting('notif_recipients', recipients)
                    save_notification_setting('notif_enabled', 'true' if enabled else 'false')
                    
                    AuditLogger.log_action("Update", "Settings", "Updated Resend email settings")
                    st.success("✅ Resend settings saved!")
        
        else:
            st.warning("""
            ⚠️ **Note:** SMTP may not work on Render.com (ports blocked).
            We recommend using **Resend API** instead.
            """)
            
            st.info("""
            **For Gmail SMTP:**
            1. Enable 2-Factor Authentication on your Google account
            2. Go to Google Account → Security → App Passwords
            3. Generate a new App Password for "Mail"
            4. Use that App Password below (not your regular password)
            """)
            
            with st.form("smtp_config_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    smtp_server = st.text_input(
                        "SMTP Server",
                        value=settings.get('notif_smtp_server', 'smtp.gmail.com'),
                        help="For Gmail: smtp.gmail.com"
                    )
                    
                    smtp_port = st.selectbox(
                        "SMTP Port",
                        [587, 465, 25],
                        index=[587, 465, 25].index(int(settings.get('notif_smtp_port', 587))) if settings.get('notif_smtp_port') else 0,
                        help="For Gmail: 587 (TLS) or 465 (SSL)"
                    )
                    
                    sender_email = st.text_input(
                        "Sender Email",
                        value=settings.get('notif_sender_email', ''),
                        placeholder="your-email@gmail.com"
                    )
                
                with col2:
                    sender_password = st.text_input(
                        "App Password",
                        value=settings.get('notif_sender_password', ''),
                        type="password",
                        help="Use App Password, not your regular password"
                    )
                    
                    recipients = st.text_area(
                        "Recipient Emails",
                        value=settings.get('notif_recipients', ''),
                        placeholder="email1@gmail.com, email2@gmail.com",
                        help="Comma-separated list of email addresses"
                    )
                
                enabled = st.toggle(
                    "Enable Email Notifications",
                    value=settings.get('notif_enabled') == 'true'
                )
                
                if st.form_submit_button("💾 Save SMTP Settings", type="primary"):
                    save_notification_setting('notif_email_method', 'smtp')
                    save_notification_setting('notif_smtp_server', smtp_server)
                    save_notification_setting('notif_smtp_port', str(smtp_port))
                    save_notification_setting('notif_sender_email', sender_email)
                    save_notification_setting('notif_sender_password', sender_password)
                    save_notification_setting('notif_recipients', recipients)
                    save_notification_setting('notif_enabled', 'true' if enabled else 'false')
                    
                    AuditLogger.log_action("Update", "Settings", "Updated SMTP email settings")
                    st.success("✅ SMTP settings saved!")
    
    with tab2:
        st.subheader("Alert Settings")
        
        with st.form("alert_settings_form"):
            days_threshold = st.slider(
                "Alert Threshold (Days)",
                min_value=1,
                max_value=30,
                value=int(settings.get('notif_days_threshold', 7)),
                help="Send alerts for documents expiring within this many days"
            )
            
            st.markdown("**Alert Types to Include:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                include_bus_docs = st.checkbox(
                    "🚗 Bus Document Expiry",
                    value=settings.get('notif_include_bus_docs', 'true') == 'true'
                )
                include_emp_docs = st.checkbox(
                    "👤 Employee Document Expiry",
                    value=settings.get('notif_include_emp_docs', 'true') == 'true'
                )
                include_inventory = st.checkbox(
                    "📦 Low Inventory Alerts",
                    value=settings.get('notif_include_inventory', 'true') == 'true'
                )
            
            with col2:
                include_maintenance = st.checkbox(
                    "🔧 Overdue Maintenance",
                    value=settings.get('notif_include_maintenance', 'true') == 'true'
                )
                include_expenses = st.checkbox(
                    "💰 Unpaid Expenses",
                    value=settings.get('notif_include_expenses', 'false') == 'true'
                )
            
            if st.form_submit_button("💾 Save Alert Settings", type="primary"):
                save_notification_setting('notif_days_threshold', str(days_threshold))
                save_notification_setting('notif_include_bus_docs', 'true' if include_bus_docs else 'false')
                save_notification_setting('notif_include_emp_docs', 'true' if include_emp_docs else 'false')
                save_notification_setting('notif_include_inventory', 'true' if include_inventory else 'false')
                save_notification_setting('notif_include_maintenance', 'true' if include_maintenance else 'false')
                save_notification_setting('notif_include_expenses', 'true' if include_expenses else 'false')
                
                st.success("✅ Alert settings saved!")
    
    with tab3:
        st.subheader("Test & Send Notifications")
        
        # Preview current alerts
        st.markdown("### 📊 Current Alerts Preview")
        
        days_threshold = int(settings.get('notif_days_threshold', 7))
        alerts_data = get_all_critical_alerts(days_threshold)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🔴 Expired", alerts_data['summary']['expired'])
        with col2:
            st.metric("🟠 Critical", alerts_data['summary']['critical'])
        with col3:
            st.metric("🟡 Warning", alerts_data['summary']['warning'])
        with col4:
            st.metric("📊 Total", alerts_data['summary']['total'])
        
        # Show alerts breakdown
        with st.expander("View All Alerts", expanded=False):
            for category, alerts in alerts_data['alerts'].items():
                if alerts:
                    st.markdown(f"**{category.replace('_', ' ').title()}:** {len(alerts)} alert(s)")
                    for alert in alerts[:5]:
                        st.write(f"  - {alert['message']}")
                    if len(alerts) > 5:
                        st.write(f"  ... and {len(alerts) - 5} more")
        
        st.markdown("---")
        
        # Test email button
        st.markdown("### 📧 Send Notifications")
        
        # Show current config
        email_method = settings.get('notif_email_method', 'resend')
        if email_method == 'resend':
            st.info(f"📧 Using **Resend API** | Sender: `{settings.get('notif_sender_email', 'Not set')}`")
        else:
            st.info(f"📮 Using **SMTP** | Server: `{settings.get('notif_smtp_server', 'Not set')}`")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧪 Send Test Email", type="secondary", use_container_width=True):
                # Check configuration
                if email_method == 'resend':
                    if not settings.get('notif_resend_api_key'):
                        st.error("Please configure Resend API key first")
                    elif not settings.get('notif_recipients'):
                        st.error("Please add recipient email addresses")
                    else:
                        with st.spinner("Sending test email via Resend..."):
                            success, message = send_alert_notification()
                            if success:
                                st.success(f"✅ {message}")
                            else:
                                st.error(f"❌ Failed: {message}")
                else:
                    if not settings.get('notif_sender_email') or not settings.get('notif_sender_password'):
                        st.error("Please configure SMTP settings first")
                    else:
                        with st.spinner("Sending test email via SMTP..."):
                            success, message = send_alert_notification()
                            if success:
                                st.success(f"✅ {message}")
                            else:
                                st.error(f"❌ Failed: {message}")
        
        with col2:
            if st.button("📧 Send Alert Now", type="primary", use_container_width=True):
                if alerts_data['summary']['total'] == 0:
                    st.info("No alerts to send!")
                elif not settings.get('notif_enabled') == 'true':
                    st.warning("Notifications are disabled. Enable them in Email Configuration.")
                else:
                    with st.spinner("Sending notification..."):
                        success, message = send_alert_notification()
                        if success:
                            st.success(f"✅ {message}")
                        else:
                            st.error(f"❌ Failed: {message}")
        
        st.markdown("---")
        
        # Scheduling info
        st.markdown("### ⏰ Automatic Scheduling")
        st.info("""
        **To send notifications automatically on a schedule:**
        
        You can set up a scheduled task to call the notification endpoint. Options:
        
        1. **Render.com Cron Jobs** - Add a cron job in your Render dashboard
        2. **External Scheduler** - Use a service like cron-job.org (free)
        3. **GitHub Actions** - Set up a scheduled workflow
        
        The system will automatically check for alerts and send emails when triggered.
        """)