"""
database.py - Database initialization and management
Enhanced with buses, routes, and hire support - POSTGRES + SQLITE SUPPORT
CORRECTED VERSION - Proper PostgreSQL table creation with SQLAlchemy support
"""

import os
from datetime import datetime

# Detect if we're on Railway (PostgreSQL) or local (SQLite)
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from sqlalchemy import create_engine
    # Convert postgres:// to postgresql:// for SQLAlchemy
    SQLALCHEMY_URL = DATABASE_URL.replace('postgres://', 'postgresql://') if DATABASE_URL.startswith('postgres://') else DATABASE_URL
    _engine = create_engine(SQLALCHEMY_URL)
    print("🐘 Using PostgreSQL database (Railway)")
else:
    import sqlite3
    from sqlalchemy import create_engine
    DATABASE_PATH = "bus_management.db"
    _engine = create_engine(f'sqlite:///{DATABASE_PATH}')
    print("🗄️ Using SQLite database (local development)")


def get_connection():
    """Create database connection for direct queries"""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def get_engine():
    """Get SQLAlchemy engine for pandas operations"""
    return _engine


def get_placeholder():
    """Return the correct placeholder for the current database"""
    return '%s' if USE_POSTGRES else '?'


def execute_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """Execute a database query with automatic placeholder conversion."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Convert ? to %s for PostgreSQL
    if USE_POSTGRES and params:
        query = query.replace('?', '%s')
    
    try:
        cursor.execute(query, params or ())
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        elif commit:
            conn.commit()
            if 'RETURNING' in query.upper() and USE_POSTGRES:
                result = cursor.fetchone()
                result = result['id'] if result else None
            elif not USE_POSTGRES:
                result = cursor.lastrowid
            else:
                result = None
        else:
            result = None
            
        return result
    finally:
        conn.close()


def init_database():
    """Initialize all database tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("=" * 50)
    print("🔄 Starting database initialization...")
    
    try:
        if USE_POSTGRES:
            # ============================================================================
            # PostgreSQL TABLES
            # ============================================================================
            
            # BUSES TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS buses (
                    id SERIAL PRIMARY KEY,
                    bus_number TEXT UNIQUE NOT NULL,
                    registration_number TEXT,
                    make TEXT,
                    model TEXT NOT NULL,
                    capacity INTEGER,
                    year INTEGER,
                    status TEXT DEFAULT 'Active',
                    purchase_date TEXT,
                    purchase_cost REAL,
                    zinara_licence_expiry TEXT,
                    vehicle_insurance_expiry TEXT,
                    passenger_insurance_expiry TEXT,
                    fitness_expiry TEXT,
                    route_permit_expiry TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ROUTES TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS routes (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    distance REAL,
                    description TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # EMPLOYEES TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id SERIAL PRIMARY KEY,
                    employee_id TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    department TEXT,
                    email TEXT,
                    phone TEXT,
                    status TEXT DEFAULT 'Active',
                    hire_date TEXT,
                    salary REAL,
                    commission_rate REAL DEFAULT 0,
                    address TEXT,
                    emergency_contact TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # INCOME TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS income (
                    id SERIAL PRIMARY KEY,
                    bus_number TEXT NOT NULL,
                    route TEXT NOT NULL,
                    hire_destination TEXT,
                    driver_employee_id TEXT,
                    driver_name TEXT,
                    conductor_employee_id TEXT,
                    conductor_name TEXT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # MAINTENANCE TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS maintenance (
                    id SERIAL PRIMARY KEY,
                    bus_number TEXT NOT NULL,
                    maintenance_type TEXT NOT NULL,
                    mechanic_name TEXT,
                    date TEXT NOT NULL,
                    cost REAL NOT NULL,
                    status TEXT DEFAULT 'Completed',
                    description TEXT,
                    parts_used TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # BUS_ASSIGNMENTS TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bus_assignments (
                    id SERIAL PRIMARY KEY,
                    bus_number TEXT NOT NULL,
                    driver_employee_id TEXT,
                    conductor_employee_id TEXT,
                    assignment_date TEXT NOT NULL,
                    shift TEXT DEFAULT 'Full Day',
                    route TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # LEAVE_RECORDS TABLE (no foreign key constraints to avoid issues)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leave_records (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    leave_type TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    reason TEXT,
                    status TEXT DEFAULT 'Pending',
                    approved_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # PAYROLL TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payroll (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    month TEXT NOT NULL,
                    basic_salary REAL NOT NULL,
                    commission REAL DEFAULT 0,
                    deductions REAL DEFAULT 0,
                    net_salary REAL NOT NULL,
                    status TEXT DEFAULT 'Pending',
                    paid_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # PERFORMANCE_RECORDS TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_records (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    rating_period TEXT NOT NULL,
                    rating REAL NOT NULL,
                    comments TEXT,
                    reviewed_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # DISCIPLINARY_RECORDS TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS disciplinary_records (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    incident_date TEXT NOT NULL,
                    incident_type TEXT NOT NULL,
                    description TEXT,
                    action_taken TEXT,
                    reported_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # AUDIT_TRAIL TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    username TEXT,
                    action TEXT NOT NULL,
                    table_name TEXT,
                    record_id INTEGER,
                    old_values TEXT,
                    new_values TEXT,
                    ip_address TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # ACTIVITY_LOG TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_log (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL,
                    user_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    action_type TEXT NOT NULL,
                    module TEXT NOT NULL,
                    description TEXT NOT NULL,
                    ip_address TEXT,
                    session_id TEXT,
                    affected_table TEXT,
                    affected_record_id INTEGER,
                    old_values TEXT,
                    new_values TEXT
                )
            ''')
            
            # FUEL_RECORDS TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fuel_records (
                    id SERIAL PRIMARY KEY,
                    bus_number TEXT NOT NULL,
                    date TEXT NOT NULL,
                    liters REAL NOT NULL,
                    cost_per_liter REAL NOT NULL,
                    total_cost REAL NOT NULL,
                    odometer_reading REAL,
                    previous_odometer REAL,
                    km_traveled REAL,
                    fuel_efficiency REAL,
                    fuel_station TEXT,
                    payment_method TEXT DEFAULT 'Cash',
                    receipt_number TEXT,
                    filled_by TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # TRIPS TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trips (
                    id SERIAL PRIMARY KEY,
                    bus_number TEXT NOT NULL,
                    route_id INTEGER,
                    route_name TEXT NOT NULL,
                    driver_id INTEGER,
                    driver_name TEXT,
                    conductor_id INTEGER,
                    conductor_name TEXT,
                    trip_date TEXT NOT NULL,
                    departure_time TEXT,
                    arrival_time TEXT,
                    duration_minutes INTEGER,
                    passengers INTEGER NOT NULL DEFAULT 0,
                    revenue REAL NOT NULL DEFAULT 0,
                    revenue_per_passenger REAL,
                    trip_type TEXT DEFAULT 'Scheduled',
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # DOCUMENTS TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    document_name TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    entity_name TEXT,
                    issue_date TEXT,
                    expiry_date TEXT,
                    days_to_expiry INTEGER,
                    days_until_expiry INTEGER,
                    status TEXT DEFAULT 'Active',
                    document_number TEXT,
                    issuing_authority TEXT,
                    file_data TEXT,
                    file_name TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # CUSTOMERS TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id SERIAL PRIMARY KEY,
                    customer_name TEXT NOT NULL,
                    contact_person TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    customer_type TEXT DEFAULT 'Individual',
                    notes TEXT,
                    status TEXT DEFAULT 'Active',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # BOOKINGS TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id SERIAL PRIMARY KEY,
                    booking_ref TEXT UNIQUE NOT NULL,
                    customer_id INTEGER REFERENCES customers(id),
                    trip_date TEXT NOT NULL,
                    pickup_time TEXT,
                    pickup_location TEXT,
                    dropoff_location TEXT,
                    trip_type TEXT DEFAULT 'One Way',
                    num_passengers INTEGER,
                    bus_type TEXT,
                    assigned_bus TEXT,
                    assigned_driver TEXT,
                    distance_km REAL,
                    duration_hours REAL,
                    base_rate REAL,
                    total_amount REAL NOT NULL,
                    deposit_amount REAL DEFAULT 0,
                    balance REAL,
                    notes TEXT,
                    status TEXT DEFAULT 'Pending',
                    payment_status TEXT DEFAULT 'Unpaid',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # INVENTORY TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    part_number TEXT NOT NULL,
                    part_name TEXT NOT NULL,
                    category TEXT,
                    description TEXT,
                    quantity INTEGER DEFAULT 0,
                    unit TEXT DEFAULT 'Piece',
                    unit_cost REAL DEFAULT 0,
                    total_value REAL DEFAULT 0,
                    reorder_level INTEGER DEFAULT 5,
                    supplier TEXT,
                    location TEXT,
                    notes TEXT,
                    status TEXT DEFAULT 'Active',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # INVENTORY_TRANSACTIONS TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory_transactions (
                    id SERIAL PRIMARY KEY,
                    inventory_id INTEGER REFERENCES inventory(id),
                    part_name TEXT,
                    transaction_type TEXT NOT NULL,
                    quantity_change INTEGER NOT NULL,
                    quantity_before INTEGER,
                    quantity_after INTEGER,
                    unit_cost REAL,
                    total_value REAL,
                    reference TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # GENERAL_EXPENSES TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS general_expenses (
                    id SERIAL PRIMARY KEY,
                    expense_date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    description TEXT NOT NULL,
                    vendor TEXT,
                    amount REAL NOT NULL,
                    payment_method TEXT,
                    payment_status TEXT DEFAULT 'Unpaid',
                    receipt_number TEXT,
                    recurring BOOLEAN DEFAULT FALSE,
                    recurring_frequency TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # CASH_LEFT TABLE - Track cash left at rank before trips
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cash_left (
                    id SERIAL PRIMARY KEY,
                    date_left TEXT NOT NULL,
                    bus_number TEXT NOT NULL,
                    driver_name TEXT,
                    driver_employee_id TEXT,
                    conductor_name TEXT,
                    conductor_employee_id TEXT,
                    amount REAL NOT NULL,
                    supervisor_name TEXT NOT NULL,
                    route TEXT,
                    reason TEXT,
                    status TEXT DEFAULT 'pending',
                    date_collected TEXT,
                    collected_by TEXT,
                    collection_notes TEXT,
                    linked_income_id INTEGER,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # CONTRACT_TEMPLATES TABLE
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contract_templates (
                    id SERIAL PRIMARY KEY,
                    template_name TEXT UNIQUE NOT NULL,
                    template_content TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # SYSTEM_SETTINGS TABLE (for notifications, etc.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    id SERIAL PRIMARY KEY,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            try:
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_username ON activity_log(username)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_date ON income(date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_bus ON income(bus_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_maintenance_date ON maintenance(date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_bus_assignments_date ON bus_assignments(assignment_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_fuel_date ON fuel_records(date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_fuel_bus ON fuel_records(bus_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trips_date ON trips(trip_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trips_bus ON trips(bus_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_trips_route ON trips(route_name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_entity ON documents(entity_type, entity_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_expiry ON documents(expiry_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(customer_name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(trip_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_part ON inventory(part_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory(category)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_trans_item ON inventory_transactions(inventory_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_date ON general_expenses(expense_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_category ON general_expenses(category)')
            except Exception as e:
                print(f"Index creation note: {e}")
            
        else:
            # ============================================================================
            # SQLite TABLES
            # ============================================================================
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS buses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bus_number TEXT UNIQUE NOT NULL,
                    registration_number TEXT,
                    make TEXT,
                    model TEXT NOT NULL,
                    capacity INTEGER,
                    year INTEGER,
                    status TEXT DEFAULT 'Active',
                    purchase_date TEXT,
                    purchase_cost REAL,
                    zinara_licence_expiry TEXT,
                    vehicle_insurance_expiry TEXT,
                    passenger_insurance_expiry TEXT,
                    fitness_expiry TEXT,
                    route_permit_expiry TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS routes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    distance REAL,
                    description TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    department TEXT,
                    email TEXT,
                    phone TEXT,
                    status TEXT DEFAULT 'Active',
                    hire_date TEXT,
                    salary REAL,
                    commission_rate REAL DEFAULT 0,
                    address TEXT,
                    emergency_contact TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS income (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bus_number TEXT NOT NULL,
                    route TEXT NOT NULL,
                    hire_destination TEXT,
                    driver_employee_id TEXT,
                    driver_name TEXT,
                    conductor_employee_id TEXT,
                    conductor_name TEXT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS maintenance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bus_number TEXT NOT NULL,
                    maintenance_type TEXT NOT NULL,
                    mechanic_name TEXT,
                    date TEXT NOT NULL,
                    cost REAL NOT NULL,
                    status TEXT DEFAULT 'Completed',
                    description TEXT,
                    parts_used TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bus_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bus_number TEXT NOT NULL,
                    driver_employee_id TEXT,
                    conductor_employee_id TEXT,
                    assignment_date TEXT NOT NULL,
                    shift TEXT DEFAULT 'Full Day',
                    route TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leave_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    leave_type TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    reason TEXT,
                    status TEXT DEFAULT 'Pending',
                    approved_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payroll (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    month TEXT NOT NULL,
                    basic_salary REAL NOT NULL,
                    commission REAL DEFAULT 0,
                    deductions REAL DEFAULT 0,
                    net_salary REAL NOT NULL,
                    status TEXT DEFAULT 'Pending',
                    paid_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    rating_period TEXT NOT NULL,
                    rating REAL NOT NULL,
                    comments TEXT,
                    reviewed_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS disciplinary_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    incident_date TEXT NOT NULL,
                    incident_type TEXT NOT NULL,
                    description TEXT,
                    action_taken TEXT,
                    reported_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    username TEXT,
                    action TEXT NOT NULL,
                    table_name TEXT,
                    record_id INTEGER,
                    old_values TEXT,
                    new_values TEXT,
                    ip_address TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    user_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    action_type TEXT NOT NULL,
                    module TEXT NOT NULL,
                    description TEXT NOT NULL,
                    ip_address TEXT,
                    session_id TEXT,
                    affected_table TEXT,
                    affected_record_id INTEGER,
                    old_values TEXT,
                    new_values TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # FUEL_RECORDS TABLE (SQLite)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fuel_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bus_number TEXT NOT NULL,
                    date TEXT NOT NULL,
                    liters REAL NOT NULL,
                    cost_per_liter REAL NOT NULL,
                    total_cost REAL NOT NULL,
                    odometer_reading REAL,
                    previous_odometer REAL,
                    km_traveled REAL,
                    fuel_efficiency REAL,
                    fuel_station TEXT,
                    payment_method TEXT DEFAULT 'Cash',
                    receipt_number TEXT,
                    filled_by TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # TRIPS TABLE (SQLite)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bus_number TEXT NOT NULL,
                    route_id INTEGER,
                    route_name TEXT NOT NULL,
                    driver_id INTEGER,
                    driver_name TEXT,
                    conductor_id INTEGER,
                    conductor_name TEXT,
                    trip_date TEXT NOT NULL,
                    departure_time TEXT,
                    arrival_time TEXT,
                    duration_minutes INTEGER,
                    passengers INTEGER NOT NULL DEFAULT 0,
                    revenue REAL NOT NULL DEFAULT 0,
                    revenue_per_passenger REAL,
                    trip_type TEXT DEFAULT 'Scheduled',
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # DOCUMENTS TABLE (SQLite)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_name TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    entity_name TEXT,
                    issue_date TEXT,
                    expiry_date TEXT,
                    days_to_expiry INTEGER,
                    days_until_expiry INTEGER,
                    status TEXT DEFAULT 'Active',
                    document_number TEXT,
                    issuing_authority TEXT,
                    file_data TEXT,
                    file_name TEXT,
                    file_type TEXT,
                    file_size INTEGER,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # CUSTOMERS TABLE (SQLite)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    contact_person TEXT,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    customer_type TEXT DEFAULT 'Individual',
                    notes TEXT,
                    status TEXT DEFAULT 'Active',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # BOOKINGS TABLE (SQLite)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_ref TEXT UNIQUE NOT NULL,
                    customer_id INTEGER,
                    trip_date TEXT NOT NULL,
                    pickup_time TEXT,
                    pickup_location TEXT,
                    dropoff_location TEXT,
                    trip_type TEXT DEFAULT 'One Way',
                    num_passengers INTEGER,
                    bus_type TEXT,
                    assigned_bus TEXT,
                    assigned_driver TEXT,
                    distance_km REAL,
                    duration_hours REAL,
                    base_rate REAL,
                    total_amount REAL NOT NULL,
                    deposit_amount REAL DEFAULT 0,
                    balance REAL,
                    notes TEXT,
                    status TEXT DEFAULT 'Pending',
                    payment_status TEXT DEFAULT 'Unpaid',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')
            
            # Create indexes for SQLite
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_username ON activity_log(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_date ON income(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_bus ON income(bus_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_maintenance_date ON maintenance(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bus_assignments_date ON bus_assignments(assignment_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_fuel_date ON fuel_records(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_fuel_bus ON fuel_records(bus_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trips_date ON trips(trip_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trips_bus ON trips(bus_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trips_route ON trips(route_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_entity ON documents(entity_type, entity_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_expiry ON documents(expiry_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(customer_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(trip_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status)')
            
            # INVENTORY TABLE (SQLite)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    part_number TEXT NOT NULL,
                    part_name TEXT NOT NULL,
                    category TEXT,
                    description TEXT,
                    quantity INTEGER DEFAULT 0,
                    unit TEXT DEFAULT 'Piece',
                    unit_cost REAL DEFAULT 0,
                    total_value REAL DEFAULT 0,
                    reorder_level INTEGER DEFAULT 5,
                    supplier TEXT,
                    location TEXT,
                    notes TEXT,
                    status TEXT DEFAULT 'Active',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # INVENTORY_TRANSACTIONS TABLE (SQLite)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inventory_id INTEGER,
                    part_name TEXT,
                    transaction_type TEXT NOT NULL,
                    quantity_change INTEGER NOT NULL,
                    quantity_before INTEGER,
                    quantity_after INTEGER,
                    unit_cost REAL,
                    total_value REAL,
                    reference TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inventory_id) REFERENCES inventory(id)
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_part ON inventory(part_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_trans_item ON inventory_transactions(inventory_id)')
            
            # GENERAL_EXPENSES TABLE (SQLite)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS general_expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expense_date TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    description TEXT NOT NULL,
                    vendor TEXT,
                    amount REAL NOT NULL,
                    payment_method TEXT,
                    payment_status TEXT DEFAULT 'Unpaid',
                    receipt_number TEXT,
                    recurring INTEGER DEFAULT 0,
                    recurring_frequency TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # CASH_LEFT TABLE (SQLite) - Track cash left at rank before trips
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cash_left (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_left TEXT NOT NULL,
                    bus_number TEXT NOT NULL,
                    driver_name TEXT,
                    driver_employee_id TEXT,
                    conductor_name TEXT,
                    conductor_employee_id TEXT,
                    amount REAL NOT NULL,
                    supervisor_name TEXT NOT NULL,
                    route TEXT,
                    reason TEXT,
                    status TEXT DEFAULT 'pending',
                    date_collected TEXT,
                    collected_by TEXT,
                    collection_notes TEXT,
                    linked_income_id INTEGER,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # CONTRACT_TEMPLATES TABLE (SQLite)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contract_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_name TEXT UNIQUE NOT NULL,
                    template_content TEXT NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # SYSTEM_SETTINGS TABLE (for notifications, etc.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_date ON general_expenses(expense_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_category ON general_expenses(category)')
        
        conn.commit()
        print("✅ Database initialized successfully")
        print("✅ Database tables created")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during database initialization: {e}")
        raise e
    finally:
        conn.close()


def migrate_database():
    """Run database migrations to add missing columns to existing tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    print("🔄 Running database migrations...")
    
    # Check and add missing columns to income table
    try:
        if USE_POSTGRES:
            cursor.execute("""
                ALTER TABLE income 
                ADD COLUMN IF NOT EXISTS driver_employee_id TEXT
            """)
            cursor.execute("""
                ALTER TABLE income 
                ADD COLUMN IF NOT EXISTS conductor_employee_id TEXT
            """)
        else:
            # SQLite: check if columns exist
            cursor.execute("PRAGMA table_info(income)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'driver_employee_id' not in columns:
                cursor.execute("ALTER TABLE income ADD COLUMN driver_employee_id TEXT")
            if 'conductor_employee_id' not in columns:
                cursor.execute("ALTER TABLE income ADD COLUMN conductor_employee_id TEXT")
        
        # Add new employee fields for contract generation
        if USE_POSTGRES:
            cursor.execute("""
                ALTER TABLE employees 
                ADD COLUMN IF NOT EXISTS national_id TEXT
            """)
            cursor.execute("""
                ALTER TABLE employees 
                ADD COLUMN IF NOT EXISTS date_of_birth TEXT
            """)
            cursor.execute("""
                ALTER TABLE employees 
                ADD COLUMN IF NOT EXISTS emergency_phone TEXT
            """)
            cursor.execute("""
                ALTER TABLE employees 
                ADD COLUMN IF NOT EXISTS next_of_kin_relationship TEXT
            """)
        else:
            # SQLite: check if columns exist
            cursor.execute("PRAGMA table_info(employees)")
            emp_columns = [col[1] for col in cursor.fetchall()]
            
            if 'national_id' not in emp_columns:
                cursor.execute("ALTER TABLE employees ADD COLUMN national_id TEXT")
            if 'date_of_birth' not in emp_columns:
                cursor.execute("ALTER TABLE employees ADD COLUMN date_of_birth TEXT")
            if 'emergency_phone' not in emp_columns:
                cursor.execute("ALTER TABLE employees ADD COLUMN emergency_phone TEXT")
            if 'next_of_kin_relationship' not in emp_columns:
                cursor.execute("ALTER TABLE employees ADD COLUMN next_of_kin_relationship TEXT")
        
        conn.commit()
        print("✅ Migrations completed")
    except Exception as e:
        conn.rollback()
        print(f"Migration note: {e}")
    finally:
        conn.close()
    
    # Second migration batch - add trip fields to income table
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            # Add trip-related columns to income table
            cursor.execute("ALTER TABLE income ADD COLUMN IF NOT EXISTS passengers INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE income ADD COLUMN IF NOT EXISTS trip_type TEXT DEFAULT 'Scheduled'")
            cursor.execute("ALTER TABLE income ADD COLUMN IF NOT EXISTS departure_time TEXT")
            cursor.execute("ALTER TABLE income ADD COLUMN IF NOT EXISTS arrival_time TEXT")
            cursor.execute("ALTER TABLE income ADD COLUMN IF NOT EXISTS revenue_per_passenger REAL")
        else:
            # SQLite
            cursor.execute("PRAGMA table_info(income)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'passengers' not in columns:
                cursor.execute("ALTER TABLE income ADD COLUMN passengers INTEGER DEFAULT 0")
            if 'trip_type' not in columns:
                cursor.execute("ALTER TABLE income ADD COLUMN trip_type TEXT DEFAULT 'Scheduled'")
            if 'departure_time' not in columns:
                cursor.execute("ALTER TABLE income ADD COLUMN departure_time TEXT")
            if 'arrival_time' not in columns:
                cursor.execute("ALTER TABLE income ADD COLUMN arrival_time TEXT")
            if 'revenue_per_passenger' not in columns:
                cursor.execute("ALTER TABLE income ADD COLUMN revenue_per_passenger REAL")
        
        conn.commit()
        print("✅ Trip fields added to income table")
    except Exception as e:
        conn.rollback()
        print(f"Trip migration note: {e}")
    finally:
        conn.close()
    
    # ==========================================================================
    # PAYROLL SYSTEM MIGRATIONS - Phase 1
    # ==========================================================================
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        print("🔄 Running payroll system migrations...")
        
        if USE_POSTGRES:
            # Add bonus fields to income table
            cursor.execute("ALTER TABLE income ADD COLUMN IF NOT EXISTS driver_bonus REAL DEFAULT 0")
            cursor.execute("ALTER TABLE income ADD COLUMN IF NOT EXISTS conductor_bonus REAL DEFAULT 0")
            cursor.execute("ALTER TABLE income ADD COLUMN IF NOT EXISTS bonus_reason TEXT")
            
            # Add self-service login fields to employees
            cursor.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS can_login BOOLEAN DEFAULT FALSE")
            cursor.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS last_login TIMESTAMP")
            cursor.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS base_salary REAL DEFAULT 0")
            cursor.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS pay_frequency TEXT DEFAULT 'monthly'")
            
            # PAYROLL_PERIODS TABLE - Defines pay periods
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payroll_periods (
                    id SERIAL PRIMARY KEY,
                    period_name TEXT NOT NULL,
                    period_type TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    status TEXT DEFAULT 'draft',
                    currency TEXT DEFAULT 'USD',
                    driver_commission_rate REAL DEFAULT 8.0,
                    conductor_commission_rate REAL DEFAULT 5.0,
                    notes TEXT,
                    created_by TEXT,
                    processed_by TEXT,
                    processed_at TIMESTAMP,
                    approved_by TEXT,
                    approved_at TIMESTAMP,
                    paid_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # PAYROLL_RECORDS TABLE - Individual payroll per employee
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payroll_records (
                    id SERIAL PRIMARY KEY,
                    payroll_period_id INTEGER REFERENCES payroll_periods(id),
                    employee_id INTEGER NOT NULL,
                    employee_name TEXT NOT NULL,
                    employee_role TEXT NOT NULL,
                    department TEXT,
                    
                    total_trips INTEGER DEFAULT 0,
                    total_days_worked INTEGER DEFAULT 0,
                    total_revenue_handled REAL DEFAULT 0,
                    total_passengers INTEGER DEFAULT 0,
                    
                    base_salary REAL DEFAULT 0,
                    commission_rate REAL DEFAULT 0,
                    commission_amount REAL DEFAULT 0,
                    bonuses REAL DEFAULT 0,
                    overtime_pay REAL DEFAULT 0,
                    other_allowances REAL DEFAULT 0,
                    gross_earnings REAL DEFAULT 0,
                    
                    paye_tax REAL DEFAULT 0,
                    nssa_employee REAL DEFAULT 0,
                    nssa_employer REAL DEFAULT 0,
                    loan_deductions REAL DEFAULT 0,
                    penalty_deductions REAL DEFAULT 0,
                    other_deductions REAL DEFAULT 0,
                    total_deductions REAL DEFAULT 0,
                    
                    net_pay REAL DEFAULT 0,
                    currency TEXT DEFAULT 'USD',
                    
                    calculation_details TEXT,
                    notes TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # PAY_RULES TABLE - Configurable pay rules
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pay_rules (
                    id SERIAL PRIMARY KEY,
                    rule_name TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    applies_to TEXT,
                    calculation_method TEXT NOT NULL,
                    value REAL,
                    percentage REAL,
                    min_threshold REAL,
                    max_cap REAL,
                    is_active BOOLEAN DEFAULT TRUE,
                    effective_from DATE,
                    effective_to DATE,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # TAX_BRACKETS TABLE - PAYE tax brackets
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tax_brackets (
                    id SERIAL PRIMARY KEY,
                    bracket_name TEXT NOT NULL,
                    min_amount REAL NOT NULL,
                    max_amount REAL,
                    tax_rate REAL NOT NULL,
                    fixed_amount REAL DEFAULT 0,
                    currency TEXT DEFAULT 'USD',
                    is_active BOOLEAN DEFAULT TRUE,
                    effective_from DATE,
                    effective_to DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # EMPLOYEE_DEDUCTIONS TABLE - Track all deductions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_deductions (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    deduction_type TEXT NOT NULL,
                    description TEXT,
                    amount REAL NOT NULL,
                    date_incurred DATE NOT NULL,
                    is_recurring BOOLEAN DEFAULT FALSE,
                    applied_to_payroll_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # LOANS TABLE - Track employee loans
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_loans (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    loan_type TEXT NOT NULL,
                    principal_amount REAL NOT NULL,
                    amount_paid REAL DEFAULT 0,
                    balance REAL NOT NULL,
                    monthly_deduction REAL,
                    date_issued DATE NOT NULL,
                    expected_end_date DATE,
                    status TEXT DEFAULT 'active',
                    approved_by TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # LOAN_PAYMENTS TABLE - Track loan repayments
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS loan_payments (
                    id SERIAL PRIMARY KEY,
                    loan_id INTEGER REFERENCES employee_loans(id),
                    employee_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    payment_date DATE NOT NULL,
                    payment_method TEXT DEFAULT 'payroll',
                    payroll_record_id INTEGER,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # RED_TICKETS TABLE - Inspector-issued tickets
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS red_tickets (
                    id SERIAL PRIMARY KEY,
                    ticket_date DATE NOT NULL,
                    conductor_id INTEGER NOT NULL,
                    conductor_name TEXT,
                    inspector_id INTEGER NOT NULL,
                    inspector_name TEXT,
                    bus_number TEXT,
                    route TEXT,
                    trip_id INTEGER,
                    amount REAL NOT NULL,
                    passenger_count INTEGER DEFAULT 1,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    applied_to_payroll_id INTEGER,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # DAILY_RECONCILIATION TABLE - Daily shortfalls and issues
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_reconciliation (
                    id SERIAL PRIMARY KEY,
                    reconciliation_date DATE NOT NULL,
                    employee_id INTEGER NOT NULL,
                    employee_name TEXT,
                    employee_role TEXT,
                    bus_number TEXT,
                    route TEXT,
                    
                    expected_amount REAL DEFAULT 0,
                    actual_amount REAL DEFAULT 0,
                    shortage_amount REAL DEFAULT 0,
                    overage_amount REAL DEFAULT 0,
                    
                    fuel_expected REAL DEFAULT 0,
                    fuel_actual REAL DEFAULT 0,
                    fuel_overuse REAL DEFAULT 0,
                    fuel_overuse_cost REAL DEFAULT 0,
                    
                    damage_amount REAL DEFAULT 0,
                    damage_description TEXT,
                    
                    other_deductions REAL DEFAULT 0,
                    other_deductions_description TEXT,
                    
                    notes TEXT,
                    status TEXT DEFAULT 'pending',
                    applied_to_payroll_id INTEGER,
                    reconciled_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # PAYSLIPS TABLE - Generated payslips
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payslips (
                    id SERIAL PRIMARY KEY,
                    payslip_number TEXT UNIQUE,
                    payroll_record_id INTEGER REFERENCES payroll_records(id),
                    employee_id INTEGER NOT NULL,
                    period_name TEXT,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    pdf_data BYTEA,
                    emailed_at TIMESTAMP,
                    downloaded_at TIMESTAMP,
                    created_by TEXT
                )
            ''')
            
            # EMPLOYEE_REQUESTS TABLE - Leave, loan requests from self-service
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_requests (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    request_type TEXT NOT NULL,
                    request_details TEXT,
                    amount REAL,
                    start_date DATE,
                    end_date DATE,
                    status TEXT DEFAULT 'pending',
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    review_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # EMPLOYEE_COMPLAINTS TABLE - Complaints from self-service
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_complaints (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    priority TEXT DEFAULT 'normal',
                    status TEXT DEFAULT 'open',
                    assigned_to TEXT,
                    resolved_by TEXT,
                    resolved_at TIMESTAMP,
                    resolution_notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # SYSTEM_SETTINGS TABLE - Configurable settings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    id SERIAL PRIMARY KEY,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    setting_type TEXT DEFAULT 'text',
                    category TEXT,
                    description TEXT,
                    updated_by TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
        else:
            # SQLite versions
            cursor.execute("PRAGMA table_info(income)")
            income_cols = [col[1] for col in cursor.fetchall()]
            if 'driver_bonus' not in income_cols:
                cursor.execute("ALTER TABLE income ADD COLUMN driver_bonus REAL DEFAULT 0")
            if 'conductor_bonus' not in income_cols:
                cursor.execute("ALTER TABLE income ADD COLUMN conductor_bonus REAL DEFAULT 0")
            if 'bonus_reason' not in income_cols:
                cursor.execute("ALTER TABLE income ADD COLUMN bonus_reason TEXT")
            
            cursor.execute("PRAGMA table_info(employees)")
            emp_cols = [col[1] for col in cursor.fetchall()]
            if 'can_login' not in emp_cols:
                cursor.execute("ALTER TABLE employees ADD COLUMN can_login INTEGER DEFAULT 0")
            if 'last_login' not in emp_cols:
                cursor.execute("ALTER TABLE employees ADD COLUMN last_login TEXT")
            if 'base_salary' not in emp_cols:
                cursor.execute("ALTER TABLE employees ADD COLUMN base_salary REAL DEFAULT 0")
            if 'pay_frequency' not in emp_cols:
                cursor.execute("ALTER TABLE employees ADD COLUMN pay_frequency TEXT DEFAULT 'monthly'")
            
            # Create new tables for SQLite
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payroll_periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period_name TEXT NOT NULL,
                    period_type TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    currency TEXT DEFAULT 'USD',
                    driver_commission_rate REAL DEFAULT 8.0,
                    conductor_commission_rate REAL DEFAULT 5.0,
                    notes TEXT,
                    created_by TEXT,
                    processed_by TEXT,
                    processed_at TEXT,
                    approved_by TEXT,
                    approved_at TEXT,
                    paid_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payroll_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payroll_period_id INTEGER,
                    employee_id INTEGER NOT NULL,
                    employee_name TEXT NOT NULL,
                    employee_role TEXT NOT NULL,
                    department TEXT,
                    total_trips INTEGER DEFAULT 0,
                    total_days_worked INTEGER DEFAULT 0,
                    total_revenue_handled REAL DEFAULT 0,
                    total_passengers INTEGER DEFAULT 0,
                    base_salary REAL DEFAULT 0,
                    commission_rate REAL DEFAULT 0,
                    commission_amount REAL DEFAULT 0,
                    bonuses REAL DEFAULT 0,
                    overtime_pay REAL DEFAULT 0,
                    other_allowances REAL DEFAULT 0,
                    gross_earnings REAL DEFAULT 0,
                    paye_tax REAL DEFAULT 0,
                    nssa_employee REAL DEFAULT 0,
                    nssa_employer REAL DEFAULT 0,
                    loan_deductions REAL DEFAULT 0,
                    penalty_deductions REAL DEFAULT 0,
                    other_deductions REAL DEFAULT 0,
                    total_deductions REAL DEFAULT 0,
                    net_pay REAL DEFAULT 0,
                    currency TEXT DEFAULT 'USD',
                    calculation_details TEXT,
                    notes TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pay_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    applies_to TEXT,
                    calculation_method TEXT NOT NULL,
                    value REAL,
                    percentage REAL,
                    min_threshold REAL,
                    max_cap REAL,
                    is_active INTEGER DEFAULT 1,
                    effective_from TEXT,
                    effective_to TEXT,
                    created_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tax_brackets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bracket_name TEXT NOT NULL,
                    min_amount REAL NOT NULL,
                    max_amount REAL,
                    tax_rate REAL NOT NULL,
                    fixed_amount REAL DEFAULT 0,
                    currency TEXT DEFAULT 'USD',
                    is_active INTEGER DEFAULT 1,
                    effective_from TEXT,
                    effective_to TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_deductions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    deduction_type TEXT NOT NULL,
                    description TEXT,
                    amount REAL NOT NULL,
                    date_incurred TEXT NOT NULL,
                    is_recurring INTEGER DEFAULT 0,
                    applied_to_payroll_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_loans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    loan_type TEXT NOT NULL,
                    principal_amount REAL NOT NULL,
                    amount_paid REAL DEFAULT 0,
                    balance REAL NOT NULL,
                    monthly_deduction REAL,
                    date_issued TEXT NOT NULL,
                    expected_end_date TEXT,
                    status TEXT DEFAULT 'active',
                    approved_by TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS loan_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loan_id INTEGER,
                    employee_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    payment_date TEXT NOT NULL,
                    payment_method TEXT DEFAULT 'payroll',
                    payroll_record_id INTEGER,
                    notes TEXT,
                    created_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS red_tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_date TEXT NOT NULL,
                    conductor_id INTEGER NOT NULL,
                    conductor_name TEXT,
                    inspector_id INTEGER NOT NULL,
                    inspector_name TEXT,
                    bus_number TEXT,
                    route TEXT,
                    trip_id INTEGER,
                    amount REAL NOT NULL,
                    passenger_count INTEGER DEFAULT 1,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    applied_to_payroll_id INTEGER,
                    created_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_reconciliation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reconciliation_date TEXT NOT NULL,
                    employee_id INTEGER NOT NULL,
                    employee_name TEXT,
                    employee_role TEXT,
                    bus_number TEXT,
                    route TEXT,
                    expected_amount REAL DEFAULT 0,
                    actual_amount REAL DEFAULT 0,
                    shortage_amount REAL DEFAULT 0,
                    overage_amount REAL DEFAULT 0,
                    fuel_expected REAL DEFAULT 0,
                    fuel_actual REAL DEFAULT 0,
                    fuel_overuse REAL DEFAULT 0,
                    fuel_overuse_cost REAL DEFAULT 0,
                    damage_amount REAL DEFAULT 0,
                    damage_description TEXT,
                    other_deductions REAL DEFAULT 0,
                    other_deductions_description TEXT,
                    notes TEXT,
                    status TEXT DEFAULT 'pending',
                    applied_to_payroll_id INTEGER,
                    reconciled_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payslips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payslip_number TEXT UNIQUE,
                    payroll_record_id INTEGER,
                    employee_id INTEGER NOT NULL,
                    period_name TEXT,
                    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    pdf_data BLOB,
                    emailed_at TEXT,
                    downloaded_at TEXT,
                    created_by TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    request_type TEXT NOT NULL,
                    request_details TEXT,
                    amount REAL,
                    start_date TEXT,
                    end_date TEXT,
                    status TEXT DEFAULT 'pending',
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    review_notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_complaints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    priority TEXT DEFAULT 'normal',
                    status TEXT DEFAULT 'open',
                    assigned_to TEXT,
                    resolved_by TEXT,
                    resolved_at TEXT,
                    resolution_notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT,
                    setting_type TEXT DEFAULT 'text',
                    category TEXT,
                    description TEXT,
                    updated_by TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        conn.commit()
        print("✅ Payroll system tables created")
        
    except Exception as e:
        conn.rollback()
        print(f"Payroll migration error: {e}")
    finally:
        conn.close()
    
    # Insert default tax brackets and settings
    _insert_default_payroll_settings()


def _insert_default_payroll_settings():
    """Insert default tax brackets and system settings for payroll"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        ph = '%s' if USE_POSTGRES else '?'
        
        # Check if tax brackets already exist
        cursor.execute("SELECT COUNT(*) FROM tax_brackets")
        result = cursor.fetchone()
        count = result[0] if isinstance(result, tuple) else result.get('count', 0)
        
        if count == 0:
            # Insert Zimbabwe PAYE tax brackets (USD)
            tax_brackets = [
                ('Bracket 1 - Tax Free', 0, 100, 0, 0, 'USD'),
                ('Bracket 2 - 20%', 100.01, 300, 20, 0, 'USD'),
                ('Bracket 3 - 25%', 300.01, 500, 25, 40, 'USD'),
                ('Bracket 4 - 30%', 500.01, 1000, 30, 90, 'USD'),
                ('Bracket 5 - 35%', 1000.01, 2000, 35, 240, 'USD'),
                ('Bracket 6 - 40%', 2000.01, None, 40, 590, 'USD'),
            ]
            
            for bracket in tax_brackets:
                if USE_POSTGRES:
                    cursor.execute(f'''
                        INSERT INTO tax_brackets (bracket_name, min_amount, max_amount, tax_rate, fixed_amount, currency, is_active)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, TRUE)
                        ON CONFLICT DO NOTHING
                    ''', bracket)
                else:
                    cursor.execute(f'''
                        INSERT OR IGNORE INTO tax_brackets (bracket_name, min_amount, max_amount, tax_rate, fixed_amount, currency, is_active)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 1)
                    ''', bracket)
            
            print("✅ Default tax brackets inserted")
        
        # Check if system settings already exist
        cursor.execute("SELECT COUNT(*) FROM system_settings")
        result = cursor.fetchone()
        count = result[0] if isinstance(result, tuple) else result.get('count', 0)
        
        if count == 0:
            # Insert default settings
            settings = [
                ('nssa_employee_rate', '4.5', 'number', 'payroll', 'NSSA employee contribution rate (%)'),
                ('nssa_employer_rate', '4.5', 'number', 'payroll', 'NSSA employer contribution rate (%)'),
                ('default_driver_commission', '8.0', 'number', 'payroll', 'Default driver commission rate (%)'),
                ('default_conductor_commission', '5.0', 'number', 'payroll', 'Default conductor commission rate (%)'),
                ('default_currency', 'USD', 'text', 'payroll', 'Default currency for payroll'),
                ('company_name', 'PAVILLION COACHES', 'text', 'company', 'Company name for documents'),
                ('company_cell', '0772 679 680', 'text', 'company', 'Company cell phone'),
                ('company_work', '+263 24 2770931', 'text', 'company', 'Company work phone'),
                ('company_email', 'info@pavillioncoaches.co.zw', 'text', 'company', 'Company email'),
                ('company_address', 'Harare, Zimbabwe', 'text', 'company', 'Company address'),
            ]
            
            for setting in settings:
                if USE_POSTGRES:
                    cursor.execute(f'''
                        INSERT INTO system_settings (setting_key, setting_value, setting_type, category, description)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
                        ON CONFLICT (setting_key) DO NOTHING
                    ''', setting)
                else:
                    cursor.execute(f'''
                        INSERT OR IGNORE INTO system_settings (setting_key, setting_value, setting_type, category, description)
                        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
                    ''', setting)
            
            print("✅ Default system settings inserted")
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        print(f"Default settings error: {e}")
    finally:
        conn.close()


def verify_database():
    """Verify that all required tables exist"""
    conn = get_connection()
    cursor = conn.cursor()
    
    required_tables = [
        'buses', 'routes', 'employees', 'income', 'maintenance',
        'bus_assignments', 'leave_records', 'payroll', 
        'performance_records', 'disciplinary_records', 'activity_log'
    ]
    
    missing_tables = []
    
    for table in required_tables:
        try:
            if USE_POSTGRES:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, (table,))
                exists = cursor.fetchone()
                # Handle RealDictRow
                if hasattr(exists, 'get'):
                    exists = exists.get('exists', False)
                elif isinstance(exists, tuple):
                    exists = exists[0]
                else:
                    exists = bool(exists)
            else:
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,)
                )
                exists = cursor.fetchone() is not None
            
            if exists:
                print(f"✅ Table exists: {table}")
            else:
                print(f"❌ Missing table: {table}")
                missing_tables.append(table)
                
        except Exception as e:
            print(f"❌ Error checking table {table}: {e}")
            missing_tables.append(table)
    
    conn.close()
    
    if missing_tables:
        raise Exception(f"Missing tables: {', '.join(missing_tables)}")
    
    print("✅ All database tables verified")


def log_audit_trail(username, action, table_name, record_id=None, old_values=None, new_values=None):
    """Log an audit trail entry"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO audit_trail (username, action, table_name, record_id, old_values, new_values)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (username, action, table_name, record_id, str(old_values), str(new_values)))
        else:
            cursor.execute('''
                INSERT INTO audit_trail (username, action, table_name, record_id, old_values, new_values)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, action, table_name, record_id, str(old_values), str(new_values)))
        
        conn.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
    finally:
        conn.close()


# ============================================================================
# BUS MANAGEMENT FUNCTIONS
# ============================================================================

def get_all_buses():
    """Get all buses"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM buses ORDER BY bus_number')
    buses = cursor.fetchall()
    conn.close()
    return [dict(bus) if hasattr(bus, 'keys') else bus for bus in buses]


def get_active_buses():
    """Get active buses only"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('SELECT * FROM buses WHERE status = %s ORDER BY bus_number', ('Active',))
    else:
        cursor.execute('SELECT * FROM buses WHERE status = ? ORDER BY bus_number', ('Active',))
    
    buses = cursor.fetchall()
    conn.close()
    return [dict(bus) if hasattr(bus, 'keys') else bus for bus in buses]


def get_bus_by_number(bus_number):
    """Get a bus by its bus number"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('SELECT * FROM buses WHERE bus_number = %s', (bus_number,))
    else:
        cursor.execute('SELECT * FROM buses WHERE bus_number = ?', (bus_number,))
    
    bus = cursor.fetchone()
    conn.close()
    return dict(bus) if bus and hasattr(bus, 'keys') else bus


def add_bus(bus_number, model, capacity, year=None, status='Active', notes=None, created_by=None, registration_number=None):
    """Add new bus"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO buses (bus_number, registration_number, model, capacity, year, status, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (bus_number, registration_number, model, capacity, year, status, notes, created_by))
            result = cursor.fetchone()
            bus_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO buses (bus_number, registration_number, model, capacity, year, status, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bus_number, registration_number, model, capacity, year, status, notes, created_by))
            bus_id = cursor.lastrowid
        
        conn.commit()
        log_audit_trail(created_by or 'System', 'INSERT', 'buses', bus_id, None, 
                       {'bus_number': bus_number, 'model': model})
        return bus_id
    except Exception as e:
        print(f"Error adding bus: {e}")
        return None
    finally:
        conn.close()


def update_bus(bus_id, bus_number, model, capacity, year=None, status='Active', notes=None, registration_number=None):
    """Update bus details"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            UPDATE buses 
            SET bus_number = %s, registration_number = %s, model = %s, capacity = %s, year = %s, status = %s, notes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (bus_number, registration_number, model, capacity, year, status, notes, bus_id))
    else:
        cursor.execute('''
            UPDATE buses 
            SET bus_number = ?, registration_number = ?, model = ?, capacity = ?, year = ?, status = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (bus_number, registration_number, model, capacity, year, status, notes, bus_id))
    
    conn.commit()
    conn.close()


def delete_bus(bus_id):
    """Delete a bus"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('DELETE FROM buses WHERE id = %s', (bus_id,))
    else:
        cursor.execute('DELETE FROM buses WHERE id = ?', (bus_id,))
    
    conn.commit()
    conn.close()


# ============================================================================
# ROUTE MANAGEMENT FUNCTIONS
# ============================================================================

def get_all_routes():
    """Get all routes"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM routes ORDER BY name')
    routes = cursor.fetchall()
    conn.close()
    return [dict(route) if hasattr(route, 'keys') else route for route in routes]


def add_route(name, distance=None, description=None, created_by=None):
    """Add new route"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO routes (name, distance, description, created_by)
                VALUES (%s, %s, %s, %s) RETURNING id
            ''', (name, distance, description, created_by))
            result = cursor.fetchone()
            route_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO routes (name, distance, description, created_by)
                VALUES (?, ?, ?, ?)
            ''', (name, distance, description, created_by))
            route_id = cursor.lastrowid
        
        conn.commit()
        return route_id
    except Exception:
        return None
    finally:
        conn.close()


def update_route(route_id, name, distance=None, description=None):
    """Update route details"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            UPDATE routes 
            SET name = %s, distance = %s, description = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (name, distance, description, route_id))
    else:
        cursor.execute('''
            UPDATE routes 
            SET name = ?, distance = ?, description = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (name, distance, description, route_id))
    
    conn.commit()
    conn.close()


def delete_route(route_id):
    """Delete a route"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('DELETE FROM routes WHERE id = %s', (route_id,))
    else:
        cursor.execute('DELETE FROM routes WHERE id = ?', (route_id,))
    
    conn.commit()
    conn.close()


# ============================================================================
# EMPLOYEE HELPER FUNCTIONS
# ============================================================================

def get_active_drivers():
    """Get list of active drivers from employees table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute("""
            SELECT employee_id, full_name 
            FROM employees 
            WHERE position LIKE %s AND status = %s
            ORDER BY full_name
        """, ('%Driver%', 'Active'))
    else:
        cursor.execute("""
            SELECT employee_id, full_name 
            FROM employees 
            WHERE position LIKE ? AND status = ?
            ORDER BY full_name
        """, ('%Driver%', 'Active'))
    
    drivers = cursor.fetchall()
    conn.close()
    return drivers


def get_active_conductors():
    """Get list of active conductors from employees table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute("""
            SELECT employee_id, full_name 
            FROM employees 
            WHERE position LIKE %s AND status = %s
            ORDER BY full_name
        """, ('%Conductor%', 'Active'))
    else:
        cursor.execute("""
            SELECT employee_id, full_name 
            FROM employees 
            WHERE position LIKE ? AND status = ?
            ORDER BY full_name
        """, ('%Conductor%', 'Active'))
    
    conductors = cursor.fetchall()
    conn.close()
    return conductors


def get_active_mechanics():
    """Get list of active mechanics from employees table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute("""
            SELECT employee_id, full_name 
            FROM employees 
            WHERE position LIKE %s AND status = %s
            ORDER BY full_name
        """, ('%Mechanic%', 'Active'))
    else:
        cursor.execute("""
            SELECT employee_id, full_name 
            FROM employees 
            WHERE position LIKE ? AND status = ?
            ORDER BY full_name
        """, ('%Mechanic%', 'Active'))
    
    mechanics = cursor.fetchall()
    conn.close()
    return mechanics


# ============================================================================
# INCOME MANAGEMENT FUNCTIONS
# ============================================================================

def add_income_record(bus_number, route, date, amount, driver_name=None, conductor_name=None,
                      hire_destination=None, notes=None, created_by=None,
                      driver_employee_id=None, conductor_employee_id=None,
                      passengers=0, trip_type='Scheduled', departure_time=None, arrival_time=None,
                      driver_bonus=0, conductor_bonus=0, bonus_reason=None):
    """Add new income/trip record with optional bonus"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Calculate revenue per passenger
    revenue_per_passenger = amount / passengers if passengers and passengers > 0 else None
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO income (bus_number, route, hire_destination, driver_employee_id, driver_name,
                                   conductor_employee_id, conductor_name, date, amount, notes, created_by,
                                   passengers, trip_type, departure_time, arrival_time, revenue_per_passenger,
                                   driver_bonus, conductor_bonus, bonus_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (bus_number, route, hire_destination, driver_employee_id, driver_name,
                  conductor_employee_id, conductor_name, date, amount, notes, created_by,
                  passengers, trip_type, departure_time, arrival_time, revenue_per_passenger,
                  driver_bonus or 0, conductor_bonus or 0, bonus_reason))
            result = cursor.fetchone()
            record_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO income (bus_number, route, hire_destination, driver_employee_id, driver_name,
                                   conductor_employee_id, conductor_name, date, amount, notes, created_by,
                                   passengers, trip_type, departure_time, arrival_time, revenue_per_passenger,
                                   driver_bonus, conductor_bonus, bonus_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bus_number, route, hire_destination, driver_employee_id, driver_name,
                  conductor_employee_id, conductor_name, date, amount, notes, created_by,
                  passengers, trip_type, departure_time, arrival_time, revenue_per_passenger,
                  driver_bonus or 0, conductor_bonus or 0, bonus_reason))
            record_id = cursor.lastrowid
        
        conn.commit()
        return record_id
    except Exception as e:
        print(f"Error adding income record: {e}")
        return None
    finally:
        conn.close()


def update_income_record(record_id, bus_number, route, date, amount, driver_name=None, 
                        conductor_name=None, hire_destination=None, notes=None):
    """Update income record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            UPDATE income 
            SET bus_number = %s, route = %s, hire_destination = %s, driver_name = %s,
                conductor_name = %s, date = %s, amount = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (bus_number, route, hire_destination, driver_name, conductor_name, date, amount, notes, record_id))
    else:
        cursor.execute('''
            UPDATE income 
            SET bus_number = ?, route = ?, hire_destination = ?, driver_name = ?,
                conductor_name = ?, date = ?, amount = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (bus_number, route, hire_destination, driver_name, conductor_name, date, amount, notes, record_id))
    
    conn.commit()
    conn.close()


def delete_income_record(record_id):
    """Delete income record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('DELETE FROM income WHERE id = %s', (record_id,))
    else:
        cursor.execute('DELETE FROM income WHERE id = ?', (record_id,))
    
    conn.commit()
    conn.close()


# ============================================================================
# MAINTENANCE MANAGEMENT FUNCTIONS
# ============================================================================

def add_maintenance_record(bus_number, maintenance_type, date, cost, mechanic_name=None,
                          status='Completed', description=None, parts_used=None, created_by=None):
    """Add new maintenance record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO maintenance (bus_number, maintenance_type, mechanic_name, date, cost, 
                                        status, description, parts_used, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (bus_number, maintenance_type, mechanic_name, date, cost, status, description, parts_used, created_by))
            result = cursor.fetchone()
            record_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO maintenance (bus_number, maintenance_type, mechanic_name, date, cost, 
                                        status, description, parts_used, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bus_number, maintenance_type, mechanic_name, date, cost, status, description, parts_used, created_by))
            record_id = cursor.lastrowid
        
        conn.commit()
        return record_id
    except Exception as e:
        print(f"Error adding maintenance record: {e}")
        return None
    finally:
        conn.close()


def delete_maintenance_record(record_id):
    """Delete maintenance record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('DELETE FROM maintenance WHERE id = %s', (record_id,))
    else:
        cursor.execute('DELETE FROM maintenance WHERE id = ?', (record_id,))
    
    conn.commit()
    conn.close()


# ============================================================================
# BUS ASSIGNMENT FUNCTIONS
# ============================================================================

def get_assignments_by_date(assignment_date):
    """Get all assignments for a specific date"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            SELECT 
                ba.id,
                ba.bus_number,
                e_driver.full_name as driver_name,
                e_conductor.full_name as conductor_name,
                ba.assignment_date,
                ba.shift,
                ba.route,
                ba.notes,
                ba.driver_employee_id,
                ba.conductor_employee_id
            FROM bus_assignments ba
            LEFT JOIN employees e_driver ON ba.driver_employee_id = e_driver.employee_id
            LEFT JOIN employees e_conductor ON ba.conductor_employee_id = e_conductor.employee_id
            WHERE ba.assignment_date = %s
            ORDER BY ba.bus_number
        ''', (assignment_date,))
    else:
        cursor.execute('''
            SELECT 
                ba.id,
                ba.bus_number,
                e_driver.full_name as driver_name,
                e_conductor.full_name as conductor_name,
                ba.assignment_date,
                ba.shift,
                ba.route,
                ba.notes,
                ba.driver_employee_id,
                ba.conductor_employee_id
            FROM bus_assignments ba
            LEFT JOIN employees e_driver ON ba.driver_employee_id = e_driver.employee_id
            LEFT JOIN employees e_conductor ON ba.conductor_employee_id = e_conductor.employee_id
            WHERE ba.assignment_date = ?
            ORDER BY ba.bus_number
        ''', (assignment_date,))
    
    assignments = cursor.fetchall()
    conn.close()
    return [dict(a) if hasattr(a, 'keys') else a for a in assignments]


def add_bus_assignment(bus_number, driver_employee_id, conductor_employee_id, assignment_date,
                      shift='Full Day', route=None, notes=None, created_by=None):
    """Add new bus assignment"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO bus_assignments (bus_number, driver_employee_id, conductor_employee_id,
                                            assignment_date, shift, route, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (bus_number, driver_employee_id, conductor_employee_id, assignment_date, shift, route, notes, created_by))
            result = cursor.fetchone()
            assignment_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO bus_assignments (bus_number, driver_employee_id, conductor_employee_id,
                                            assignment_date, shift, route, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bus_number, driver_employee_id, conductor_employee_id, assignment_date, shift, route, notes, created_by))
            assignment_id = cursor.lastrowid
        
        conn.commit()
        return assignment_id
    except Exception as e:
        print(f"Error adding assignment: {e}")
        return None
    finally:
        conn.close()


def delete_bus_assignment(assignment_id):
    """Delete bus assignment"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('DELETE FROM bus_assignments WHERE id = %s', (assignment_id,))
    else:
        cursor.execute('DELETE FROM bus_assignments WHERE id = ?', (assignment_id,))
    
    conn.commit()
    conn.close()