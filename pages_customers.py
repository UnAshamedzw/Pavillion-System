"""
pages_customers.py - Customer/Booking Management Module
Pavillion Coaches Bus Management System
CRM for private hires with quotation and invoice PDF generation
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES
from audit_logger import AuditLogger
from auth import has_permission
import io


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_customers(search=None, status=None):
    """Get all customers"""
    conn = get_connection()
    
    query = """
        SELECT id, customer_name, contact_person, phone, email, address,
               customer_type, notes, status, created_at
        FROM customers
        WHERE 1=1
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if search:
        query += f" AND (customer_name LIKE {ph} OR phone LIKE {ph} OR email LIKE {ph})"
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])
    
    if status:
        query += f" AND status = {ph}"
        params.append(status)
    
    query += " ORDER BY customer_name"
    
    df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    conn.close()
    return df


def add_customer(customer_name, contact_person, phone, email, address,
                customer_type, notes=None, created_by=None):
    """Add a new customer"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO customers (
                    customer_name, contact_person, phone, email, address,
                    customer_type, notes, status, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (customer_name, contact_person, phone, email, address,
                  customer_type, notes, 'Active', created_by))
            result = cursor.fetchone()
            customer_id = result['id'] if hasattr(result, 'keys') else result[0]
        else:
            cursor.execute("""
                INSERT INTO customers (
                    customer_name, contact_person, phone, email, address,
                    customer_type, notes, status, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (customer_name, contact_person, phone, email, address,
                  customer_type, notes, 'Active', created_by))
            customer_id = cursor.lastrowid
        
        conn.commit()
        return customer_id
    except Exception as e:
        print(f"Error adding customer: {e}")
        return None
    finally:
        conn.close()


def update_customer(customer_id, **kwargs):
    """Update customer details"""
    conn = get_connection()
    cursor = conn.cursor()
    
    set_clauses = []
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = {ph}")
        params.append(value)
    
    if not set_clauses:
        return False
    
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    params.append(customer_id)
    
    query = f"UPDATE customers SET {', '.join(set_clauses)} WHERE id = {ph}"
    
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating customer: {e}")
        return False
    finally:
        conn.close()


def get_bookings(customer_id=None, status=None, start_date=None, end_date=None):
    """Get bookings with optional filters"""
    conn = get_connection()
    
    query = """
        SELECT b.*, c.customer_name, c.phone as customer_phone, c.email as customer_email
        FROM bookings b
        LEFT JOIN customers c ON b.customer_id = c.id
        WHERE 1=1
    """
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    if customer_id:
        query += f" AND b.customer_id = {ph}"
        params.append(customer_id)
    
    if status:
        query += f" AND b.status = {ph}"
        params.append(status)
    
    if start_date:
        query += f" AND b.trip_date >= {ph}"
        params.append(start_date)
    
    if end_date:
        query += f" AND b.trip_date <= {ph}"
        params.append(end_date)
    
    query += " ORDER BY b.trip_date DESC, b.created_at DESC"
    
    df = pd.read_sql_query(query, get_engine(), params=tuple(params) if params else None)
    conn.close()
    return df


def add_booking(customer_id, trip_date, pickup_time, pickup_location, dropoff_location,
               trip_type, num_passengers, bus_type, distance_km, duration_hours,
               base_rate, total_amount, deposit_amount, notes=None, created_by=None):
    """Add a new booking"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Generate booking reference
    booking_ref = f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    balance = total_amount - (deposit_amount or 0)
    
    try:
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO bookings (
                    booking_ref, customer_id, trip_date, pickup_time, pickup_location,
                    dropoff_location, trip_type, num_passengers, bus_type, distance_km,
                    duration_hours, base_rate, total_amount, deposit_amount, balance,
                    notes, status, payment_status, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (booking_ref, customer_id, trip_date, pickup_time, pickup_location,
                  dropoff_location, trip_type, num_passengers, bus_type, distance_km,
                  duration_hours, base_rate, total_amount, deposit_amount, balance,
                  notes, 'Pending', 'Unpaid', created_by))
            result = cursor.fetchone()
            booking_id = result['id'] if hasattr(result, 'keys') else result[0]
        else:
            cursor.execute("""
                INSERT INTO bookings (
                    booking_ref, customer_id, trip_date, pickup_time, pickup_location,
                    dropoff_location, trip_type, num_passengers, bus_type, distance_km,
                    duration_hours, base_rate, total_amount, deposit_amount, balance,
                    notes, status, payment_status, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (booking_ref, customer_id, trip_date, pickup_time, pickup_location,
                  dropoff_location, trip_type, num_passengers, bus_type, distance_km,
                  duration_hours, base_rate, total_amount, deposit_amount, balance,
                  notes, 'Pending', 'Unpaid', created_by))
            booking_id = cursor.lastrowid
        
        conn.commit()
        return booking_id, booking_ref
    except Exception as e:
        print(f"Error adding booking: {e}")
        return None, None
    finally:
        conn.close()


def update_booking(booking_id, **kwargs):
    """Update booking details"""
    conn = get_connection()
    cursor = conn.cursor()
    
    set_clauses = []
    params = []
    ph = '%s' if USE_POSTGRES else '?'
    
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = {ph}")
        params.append(value)
    
    if not set_clauses:
        return False
    
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    params.append(booking_id)
    
    query = f"UPDATE bookings SET {', '.join(set_clauses)} WHERE id = {ph}"
    
    try:
        cursor.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating booking: {e}")
        return False
    finally:
        conn.close()


def get_booking_by_id(booking_id):
    """Get a single booking by ID"""
    conn = get_connection()
    
    ph = '%s' if USE_POSTGRES else '?'
    query = f"""
        SELECT b.*, c.customer_name, c.contact_person, c.phone as customer_phone, 
               c.email as customer_email, c.address as customer_address
        FROM bookings b
        LEFT JOIN customers c ON b.customer_id = c.id
        WHERE b.id = {ph}
    """
    
    df = pd.read_sql_query(query, get_engine(), params=(booking_id,))
    conn.close()
    
    if not df.empty:
        return df.iloc[0].to_dict()
    return None


def get_customer_by_id(customer_id):
    """Get a single customer by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    ph = '%s' if USE_POSTGRES else '?'
    cursor.execute(f"SELECT * FROM customers WHERE id = {ph}", (customer_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        if hasattr(result, 'keys'):
            return dict(result)
        else:
            columns = ['id', 'customer_name', 'contact_person', 'phone', 'email', 
                      'address', 'customer_type', 'notes', 'status', 'created_by',
                      'created_at', 'updated_at']
            return dict(zip(columns, result))
    return None


def get_active_buses():
    """Get active buses for selection"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT bus_number, registration_number, make, model, capacity
        FROM buses WHERE status = 'Active'
        ORDER BY capacity DESC
    """)
    
    buses = cursor.fetchall()
    conn.close()
    return buses


# =============================================================================
# PDF GENERATION FUNCTIONS
# =============================================================================

def generate_quotation_pdf(booking_data):
    """Generate a quotation PDF using reportlab"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], 
                                  fontSize=24, alignment=TA_CENTER, spaceAfter=20)
    header_style = ParagraphStyle('Header', parent=styles['Normal'],
                                   fontSize=12, alignment=TA_CENTER)
    normal_style = styles['Normal']
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontName='Helvetica-Bold')
    
    story = []
    
    # Company Header
    story.append(Paragraph("PAVILLION COACHES", title_style))
    story.append(Paragraph("Premium Bus Charter Services", header_style))
    story.append(Paragraph("Tel: +263 XXX XXX XXX | Email: info@pavillioncoaches.co.zw", header_style))
    story.append(Spacer(1, 20))
    
    # Quotation Title
    story.append(Paragraph("QUOTATION", ParagraphStyle('QuoteTitle', parent=styles['Heading1'],
                                                        fontSize=20, alignment=TA_CENTER,
                                                        textColor=colors.darkblue)))
    story.append(Spacer(1, 10))
    
    # Quotation details
    quote_ref = f"QT{booking_data.get('booking_ref', '')[2:]}" if booking_data.get('booking_ref') else f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}"
    quote_date = datetime.now().strftime('%d %B %Y')
    valid_until = (datetime.now() + timedelta(days=14)).strftime('%d %B %Y')
    
    details_data = [
        ['Quotation Reference:', quote_ref, 'Date:', quote_date],
        ['Valid Until:', valid_until, '', '']
    ]
    
    details_table = Table(details_data, colWidths=[100, 150, 60, 150])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 20))
    
    # Customer Details
    story.append(Paragraph("CUSTOMER DETAILS", bold_style))
    story.append(Spacer(1, 5))
    
    customer_data = [
        ['Customer:', booking_data.get('customer_name', 'N/A')],
        ['Contact Person:', booking_data.get('contact_person', 'N/A')],
        ['Phone:', booking_data.get('customer_phone', 'N/A')],
        ['Email:', booking_data.get('customer_email', 'N/A')],
    ]
    
    customer_table = Table(customer_data, colWidths=[100, 350])
    customer_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(customer_table)
    story.append(Spacer(1, 20))
    
    # Trip Details
    story.append(Paragraph("TRIP DETAILS", bold_style))
    story.append(Spacer(1, 5))
    
    trip_data = [
        ['Trip Date:', str(booking_data.get('trip_date', 'TBD'))],
        ['Pickup Time:', str(booking_data.get('pickup_time', 'TBD'))],
        ['Pickup Location:', booking_data.get('pickup_location', 'TBD')],
        ['Dropoff Location:', booking_data.get('dropoff_location', 'TBD')],
        ['Trip Type:', booking_data.get('trip_type', 'Charter')],
        ['Passengers:', str(booking_data.get('num_passengers', 'TBD'))],
        ['Bus Type:', booking_data.get('bus_type', 'TBD')],
        ['Est. Distance:', f"{booking_data.get('distance_km', 0)} km"],
        ['Est. Duration:', f"{booking_data.get('duration_hours', 0)} hours"],
    ]
    
    trip_table = Table(trip_data, colWidths=[100, 350])
    trip_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(trip_table)
    story.append(Spacer(1, 20))
    
    # Pricing
    story.append(Paragraph("PRICING", bold_style))
    story.append(Spacer(1, 5))
    
    total = float(booking_data.get('total_amount', 0))
    deposit = float(booking_data.get('deposit_amount', 0))
    
    pricing_data = [
        ['Description', 'Amount (USD)'],
        ['Bus Charter Service', f"${total:,.2f}"],
        ['', ''],
        ['TOTAL', f"${total:,.2f}"],
        ['Deposit Required (50%)', f"${deposit:,.2f}"],
        ['Balance Due on Trip Day', f"${total - deposit:,.2f}"],
    ]
    
    pricing_table = Table(pricing_data, colWidths=[350, 100])
    pricing_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 3), (-1, 3), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(pricing_table)
    story.append(Spacer(1, 30))
    
    # Terms and Conditions
    story.append(Paragraph("TERMS AND CONDITIONS", bold_style))
    story.append(Spacer(1, 5))
    
    terms = [
        "1. A 50% deposit is required to confirm your booking.",
        "2. Balance payment is due on the day of the trip.",
        "3. Cancellations within 48 hours of trip date are non-refundable.",
        "4. Prices are valid for 14 days from the date of this quotation.",
        "5. Any additional waiting time will be charged at $20/hour.",
        "6. Route changes on the day may incur additional charges.",
    ]
    
    for term in terms:
        story.append(Paragraph(term, normal_style))
    
    story.append(Spacer(1, 30))
    
    # Footer
    story.append(Paragraph("Thank you for choosing Pavillion Coaches!", 
                          ParagraphStyle('Footer', parent=styles['Normal'],
                                        alignment=TA_CENTER, fontName='Helvetica-Oblique')))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_invoice_pdf(booking_data):
    """Generate an invoice PDF using reportlab"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], 
                                  fontSize=24, alignment=TA_CENTER, spaceAfter=20)
    header_style = ParagraphStyle('Header', parent=styles['Normal'],
                                   fontSize=12, alignment=TA_CENTER)
    normal_style = styles['Normal']
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontName='Helvetica-Bold')
    
    story = []
    
    # Company Header
    story.append(Paragraph("PAVILLION COACHES", title_style))
    story.append(Paragraph("Premium Bus Charter Services", header_style))
    story.append(Paragraph("Tel: +263 XXX XXX XXX | Email: info@pavillioncoaches.co.zw", header_style))
    story.append(Spacer(1, 20))
    
    # Invoice Title
    story.append(Paragraph("TAX INVOICE", ParagraphStyle('InvTitle', parent=styles['Heading1'],
                                                          fontSize=20, alignment=TA_CENTER,
                                                          textColor=colors.darkgreen)))
    story.append(Spacer(1, 10))
    
    # Invoice details
    inv_ref = f"INV{booking_data.get('booking_ref', '')[2:]}" if booking_data.get('booking_ref') else f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"
    inv_date = datetime.now().strftime('%d %B %Y')
    due_date = (datetime.now() + timedelta(days=7)).strftime('%d %B %Y')
    
    details_data = [
        ['Invoice Number:', inv_ref, 'Invoice Date:', inv_date],
        ['Booking Ref:', booking_data.get('booking_ref', 'N/A'), 'Due Date:', due_date]
    ]
    
    details_table = Table(details_data, colWidths=[100, 150, 80, 130])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 20))
    
    # Bill To
    story.append(Paragraph("BILL TO:", bold_style))
    story.append(Spacer(1, 5))
    
    bill_to_data = [
        [booking_data.get('customer_name', 'N/A')],
        [booking_data.get('customer_address', '') or 'Address not provided'],
        [f"Phone: {booking_data.get('customer_phone', 'N/A')}"],
        [f"Email: {booking_data.get('customer_email', 'N/A')}"],
    ]
    
    bill_table = Table(bill_to_data, colWidths=[450])
    bill_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(bill_table)
    story.append(Spacer(1, 20))
    
    # Service Details
    story.append(Paragraph("SERVICE DETAILS", bold_style))
    story.append(Spacer(1, 5))
    
    total = float(booking_data.get('total_amount', 0))
    deposit_paid = float(booking_data.get('deposit_amount', 0))
    balance = total - deposit_paid
    
    service_data = [
        ['Description', 'Trip Date', 'Details', 'Amount'],
        ['Bus Charter Service', 
         str(booking_data.get('trip_date', 'N/A')),
         f"{booking_data.get('pickup_location', '')} to {booking_data.get('dropoff_location', '')}",
         f"${total:,.2f}"],
        [f"Bus Type: {booking_data.get('bus_type', 'N/A')}", 
         f"Passengers: {booking_data.get('num_passengers', 'N/A')}",
         f"Distance: {booking_data.get('distance_km', 0)} km",
         ''],
    ]
    
    service_table = Table(service_data, colWidths=[150, 80, 150, 80])
    service_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, 1), 0.5, colors.grey),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(service_table)
    story.append(Spacer(1, 20))
    
    # Payment Summary
    summary_data = [
        ['', 'Subtotal:', f"${total:,.2f}"],
        ['', 'VAT (0%):', '$0.00'],
        ['', 'TOTAL:', f"${total:,.2f}"],
        ['', '', ''],
        ['', 'Deposit Paid:', f"(${deposit_paid:,.2f})"],
        ['', 'BALANCE DUE:', f"${balance:,.2f}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[280, 100, 80])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold'),
        ('FONTNAME', (1, 5), (-1, 5), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('BACKGROUND', (1, 2), (-1, 2), colors.lightgrey),
        ('BACKGROUND', (1, 5), (-1, 5), colors.lightgreen),
        ('LINEABOVE', (1, 2), (-1, 2), 1, colors.black),
        ('LINEABOVE', (1, 5), (-1, 5), 1, colors.black),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 30))
    
    # Payment Instructions
    story.append(Paragraph("PAYMENT INSTRUCTIONS", bold_style))
    story.append(Spacer(1, 5))
    
    payment_info = [
        "Bank: First Capital Bank",
        "Account Name: Pavillion Coaches (Pvt) Ltd",
        "Account Number: 1234567890",
        "Branch: Harare",
        "",
        "Mobile Money: EcoCash - 077X XXX XXX",
        "",
        "Please use your Invoice Number as payment reference.",
    ]
    
    for info in payment_info:
        story.append(Paragraph(info, normal_style))
    
    story.append(Spacer(1, 20))
    
    # Footer
    story.append(Paragraph("Thank you for your business!", 
                          ParagraphStyle('Footer', parent=styles['Normal'],
                                        alignment=TA_CENTER, fontName='Helvetica-Oblique')))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


# =============================================================================
# PAGE FUNCTIONS
# =============================================================================

def customer_management_page():
    """Customer and booking management page"""
    
    st.header("👥 Customer & Booking Management")
    st.markdown("Manage customers, bookings, quotations, and invoices")
    st.markdown("---")
    
    can_add = has_permission('add_income')
    can_edit = has_permission('edit_income')
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Customers", 
        "📅 New Booking", 
        "📋 All Bookings",
        "📄 Quotations",
        "🧾 Invoices"
    ])
    
    with tab1:
        st.subheader("👥 Customer Management")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            search = st.text_input("🔍 Search Customers", placeholder="Name, phone, or email...")
        
        with col2:
            status_filter = st.selectbox("Status", ["All", "Active", "Inactive"])
        
        # Add new customer
        with st.expander("➕ Add New Customer"):
            if not can_add:
                st.warning("You don't have permission to add customers")
            else:
                with st.form("add_customer_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        cust_name = st.text_input("Customer/Company Name*")
                        contact_person = st.text_input("Contact Person")
                        phone = st.text_input("Phone*")
                    
                    with col2:
                        email = st.text_input("Email")
                        address = st.text_area("Address", height=68)
                        cust_type = st.selectbox("Customer Type", 
                                                ["Individual", "Corporate", "School", "Church", "NGO", "Government", "Other"])
                    
                    notes = st.text_area("Notes", height=68)
                    
                    if st.form_submit_button("➕ Add Customer", type="primary"):
                        if not cust_name or not phone:
                            st.error("Customer name and phone are required")
                        else:
                            cust_id = add_customer(
                                customer_name=cust_name,
                                contact_person=contact_person,
                                phone=phone,
                                email=email,
                                address=address,
                                customer_type=cust_type,
                                notes=notes,
                                created_by=st.session_state['user']['username']
                            )
                            
                            if cust_id:
                                AuditLogger.log_action("Create", "Customers", f"Added customer: {cust_name}")
                                st.success(f"✅ Customer added! (ID: {cust_id})")
                                st.rerun()
                            else:
                                st.error("Error adding customer")
        
        # Display customers
        st.markdown("---")
        
        status_val = None if status_filter == "All" else status_filter
        customers_df = get_customers(search=search if search else None, status=status_val)
        
        if customers_df.empty:
            st.info("No customers found")
        else:
            st.markdown(f"**{len(customers_df)} customers found**")
            
            display_df = customers_df[[
                'id', 'customer_name', 'contact_person', 'phone', 'email', 
                'customer_type', 'status'
            ]].copy()
            display_df.columns = ['ID', 'Name', 'Contact', 'Phone', 'Email', 'Type', 'Status']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("📅 Create New Booking")
        
        if not can_add:
            st.warning("You don't have permission to create bookings")
        else:
            # Customer selection
            customers_df = get_customers(status='Active')
            
            if customers_df.empty:
                st.warning("No customers found. Please add a customer first.")
            else:
                cust_options = {
                    f"{row['customer_name']} ({row['phone']})": row['id']
                    for _, row in customers_df.iterrows()
                }
                
                with st.form("new_booking_form"):
                    st.markdown("#### Customer & Trip Details")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        selected_customer = st.selectbox("Select Customer*", list(cust_options.keys()))
                        trip_date = st.date_input("Trip Date*", min_value=datetime.now().date())
                        pickup_time = st.time_input("Pickup Time*")
                        pickup_location = st.text_input("Pickup Location*")
                    
                    with col2:
                        trip_type = st.selectbox("Trip Type", 
                                                ["One Way", "Return", "Multi-Day", "Airport Transfer", "Wedding", "Funeral", "Tour"])
                        dropoff_location = st.text_input("Dropoff Location*")
                        num_passengers = st.number_input("Number of Passengers*", min_value=1, value=20)
                        
                        buses = get_active_buses()
                        bus_options = ["Select bus..."]
                        for bus in buses:
                            if hasattr(bus, 'keys'):
                                bus_options.append(f"{bus['make']} {bus['model']} ({bus['capacity']} seats)")
                            else:
                                bus_options.append(f"{bus[2]} {bus[3]} ({bus[4]} seats)")
                        
                        bus_type = st.selectbox("Bus Type", bus_options)
                    
                    st.markdown("---")
                    st.markdown("#### Distance & Pricing")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        distance_km = st.number_input("Estimated Distance (km)", min_value=0, value=100)
                        duration_hours = st.number_input("Estimated Duration (hours)", min_value=0.5, value=2.0, step=0.5)
                    
                    with col2:
                        base_rate = st.number_input("Rate per km ($)", min_value=0.0, value=2.50, step=0.10)
                        
                        # Auto-calculate total
                        calculated_total = distance_km * base_rate
                        total_amount = st.number_input("Total Amount ($)*", min_value=0.0, value=calculated_total, step=10.0)
                    
                    with col3:
                        deposit_pct = st.slider("Deposit %", 0, 100, 50)
                        deposit_amount = total_amount * (deposit_pct / 100)
                        st.metric("Deposit Amount", f"${deposit_amount:,.2f}")
                    
                    notes = st.text_area("Additional Notes")
                    
                    if st.form_submit_button("📅 Create Booking", type="primary", use_container_width=True):
                        customer_id = cust_options[selected_customer]
                        
                        if not pickup_location or not dropoff_location:
                            st.error("Pickup and dropoff locations are required")
                        else:
                            booking_id, booking_ref = add_booking(
                                customer_id=customer_id,
                                trip_date=str(trip_date),
                                pickup_time=pickup_time.strftime('%H:%M'),
                                pickup_location=pickup_location,
                                dropoff_location=dropoff_location,
                                trip_type=trip_type,
                                num_passengers=num_passengers,
                                bus_type=bus_type if bus_type != "Select bus..." else "TBD",
                                distance_km=distance_km,
                                duration_hours=duration_hours,
                                base_rate=base_rate,
                                total_amount=total_amount,
                                deposit_amount=deposit_amount,
                                notes=notes,
                                created_by=st.session_state['user']['username']
                            )
                            
                            if booking_id:
                                AuditLogger.log_action("Create", "Bookings", 
                                                      f"Created booking {booking_ref} for customer ID:{customer_id}")
                                st.success(f"✅ Booking created! Reference: **{booking_ref}**")
                                st.balloons()
                            else:
                                st.error("Error creating booking")
    
    with tab3:
        st.subheader("📋 All Bookings")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            booking_status = st.selectbox("Status", 
                                         ["All", "Pending", "Confirmed", "Completed", "Cancelled"])
        
        with col2:
            date_from = st.date_input("From Date", value=datetime.now().date() - timedelta(days=30), key="book_from")
        
        with col3:
            date_to = st.date_input("To Date", value=datetime.now().date() + timedelta(days=30), key="book_to")
        
        status_val = None if booking_status == "All" else booking_status
        bookings_df = get_bookings(status=status_val, start_date=str(date_from), end_date=str(date_to))
        
        if bookings_df.empty:
            st.info("No bookings found")
        else:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Bookings", len(bookings_df))
            with col2:
                st.metric("Total Value", f"${bookings_df['total_amount'].sum():,.2f}")
            with col3:
                pending = len(bookings_df[bookings_df['status'] == 'Pending'])
                st.metric("Pending", pending)
            with col4:
                confirmed = len(bookings_df[bookings_df['status'] == 'Confirmed'])
                st.metric("Confirmed", confirmed)
            
            st.markdown("---")
            
            display_df = bookings_df[[
                'booking_ref', 'customer_name', 'trip_date', 'pickup_location',
                'dropoff_location', 'total_amount', 'status', 'payment_status'
            ]].copy()
            display_df.columns = ['Ref', 'Customer', 'Trip Date', 'Pickup', 
                                 'Dropoff', 'Amount ($)', 'Status', 'Payment']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Update booking status
            st.markdown("---")
            st.markdown("### Update Booking Status")
            
            if can_edit:
                booking_options = {
                    f"{row['booking_ref']} - {row['customer_name']} ({row['trip_date']})": row['id']
                    for _, row in bookings_df.iterrows()
                }
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    selected_booking = st.selectbox("Select Booking", list(booking_options.keys()))
                
                with col2:
                    new_status = st.selectbox("New Status", ["Pending", "Confirmed", "Completed", "Cancelled"])
                
                with col3:
                    new_payment = st.selectbox("Payment Status", ["Unpaid", "Deposit Paid", "Paid"])
                
                if st.button("💾 Update Booking"):
                    booking_id = booking_options[selected_booking]
                    if update_booking(booking_id, status=new_status, payment_status=new_payment):
                        AuditLogger.log_action("Update", "Bookings", f"Updated booking ID:{booking_id}")
                        st.success("✅ Booking updated!")
                        st.rerun()
    
    with tab4:
        st.subheader("📄 Generate Quotation")
        
        bookings_df = get_bookings()
        
        if bookings_df.empty:
            st.info("No bookings found. Create a booking first to generate a quotation.")
        else:
            booking_options = {
                f"{row['booking_ref']} - {row['customer_name']} ({row['trip_date']})": row['id']
                for _, row in bookings_df.iterrows()
            }
            
            selected = st.selectbox("Select Booking for Quotation", list(booking_options.keys()))
            
            if selected:
                booking_id = booking_options[selected]
                booking_data = get_booking_by_id(booking_id)
                
                if booking_data:
                    # Show preview
                    st.markdown("### Quotation Preview")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Customer:** {booking_data.get('customer_name')}")
                        st.markdown(f"**Trip Date:** {booking_data.get('trip_date')}")
                        st.markdown(f"**Route:** {booking_data.get('pickup_location')} → {booking_data.get('dropoff_location')}")
                    
                    with col2:
                        st.markdown(f"**Passengers:** {booking_data.get('num_passengers')}")
                        st.markdown(f"**Total:** ${float(booking_data.get('total_amount', 0)):,.2f}")
                        st.markdown(f"**Deposit:** ${float(booking_data.get('deposit_amount', 0)):,.2f}")
                    
                    st.markdown("---")
                    
                    if st.button("📄 Generate Quotation PDF", type="primary"):
                        with st.spinner("Generating PDF..."):
                            pdf_buffer = generate_quotation_pdf(booking_data)
                            
                            st.download_button(
                                label="⬇️ Download Quotation PDF",
                                data=pdf_buffer,
                                file_name=f"Quotation_{booking_data.get('booking_ref', 'QT')}.pdf",
                                mime="application/pdf"
                            )
                            
                            AuditLogger.log_action("Generate", "Quotation", 
                                                  f"Generated quotation for {booking_data.get('booking_ref')}")
                            st.success("✅ Quotation generated!")
    
    with tab5:
        st.subheader("🧾 Generate Invoice")
        
        # Only show confirmed or completed bookings for invoicing
        bookings_df = get_bookings()
        invoiceable = bookings_df[bookings_df['status'].isin(['Confirmed', 'Completed'])]
        
        if invoiceable.empty:
            st.info("No confirmed bookings found. Confirm a booking first to generate an invoice.")
        else:
            booking_options = {
                f"{row['booking_ref']} - {row['customer_name']} ({row['trip_date']}) - {row['payment_status']}": row['id']
                for _, row in invoiceable.iterrows()
            }
            
            selected = st.selectbox("Select Booking for Invoice", list(booking_options.keys()))
            
            if selected:
                booking_id = booking_options[selected]
                booking_data = get_booking_by_id(booking_id)
                
                if booking_data:
                    # Show preview
                    st.markdown("### Invoice Preview")
                    
                    total = float(booking_data.get('total_amount', 0))
                    deposit = float(booking_data.get('deposit_amount', 0))
                    balance = total - deposit
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Customer:** {booking_data.get('customer_name')}")
                        st.markdown(f"**Trip Date:** {booking_data.get('trip_date')}")
                        st.markdown(f"**Route:** {booking_data.get('pickup_location')} → {booking_data.get('dropoff_location')}")
                    
                    with col2:
                        st.markdown(f"**Total Amount:** ${total:,.2f}")
                        st.markdown(f"**Deposit Paid:** ${deposit:,.2f}")
                        st.markdown(f"**Balance Due:** ${balance:,.2f}")
                    
                    st.markdown("---")
                    
                    if st.button("🧾 Generate Invoice PDF", type="primary"):
                        with st.spinner("Generating PDF..."):
                            pdf_buffer = generate_invoice_pdf(booking_data)
                            
                            st.download_button(
                                label="⬇️ Download Invoice PDF",
                                data=pdf_buffer,
                                file_name=f"Invoice_{booking_data.get('booking_ref', 'INV')}.pdf",
                                mime="application/pdf"
                            )
                            
                            AuditLogger.log_action("Generate", "Invoice", 
                                                  f"Generated invoice for {booking_data.get('booking_ref')}")
                            st.success("✅ Invoice generated!")