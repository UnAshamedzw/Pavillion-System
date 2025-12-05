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
                      driver_employee_id=None, conductor_employee_id=None):
    """Add new income record"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO income (bus_number, route, hire_destination, driver_employee_id, driver_name,
                                   conductor_employee_id, conductor_name, date, amount, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (bus_number, route, hire_destination, driver_employee_id, driver_name,
                  conductor_employee_id, conductor_name, date, amount, notes, created_by))
            result = cursor.fetchone()
            record_id = result['id'] if result else None
        else:
            cursor.execute('''
                INSERT INTO income (bus_number, route, hire_destination, driver_employee_id, driver_name,
                                   conductor_employee_id, conductor_name, date, amount, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bus_number, route, hire_destination, driver_employee_id, driver_name,
                  conductor_employee_id, conductor_name, date, amount, notes, created_by))
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