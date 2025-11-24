"""
database.py - Database initialization and management
Enhanced with buses, routes, and hire support - FIXED SCHEMA
"""

import sqlite3
import os
from datetime import datetime

DATABASE_PATH = "bus_management.db"

def get_connection():
    """Create database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize all database tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create buses table - WITH BOTH bus_number AND registration_number
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT UNIQUE NOT NULL,
            registration_number TEXT UNIQUE,
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
    
    # Create routes table
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
    
    # Create employees table
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
    
    # Create income table with hire support
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT NOT NULL,
            route TEXT NOT NULL,
            hire_destination TEXT,
            driver_name TEXT,
            conductor_name TEXT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            notes TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create maintenance table
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
    
    # Create leave records table
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
    
    # Create payroll table
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
    
    # Create performance records table
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
    
    # Create disciplinary records table
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
    
    # Create audit table
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
    
    # Create activity log table
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
    
    # Create indexes for activity log
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_activity_username 
        ON activity_log(username)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_activity_timestamp 
        ON activity_log(timestamp)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_activity_action_type 
        ON activity_log(action_type)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_activity_module 
        ON activity_log(module)
    ''')
    
    conn.commit()
    conn.close()

def log_audit_trail(username, action, table_name, record_id, old_values=None, new_values=None):
    """Log actions to audit trail"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_trail (username, action, table_name, record_id, old_values, new_values)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (username, action, table_name, record_id, str(old_values), str(new_values)))
    conn.commit()
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
    return buses

def get_active_buses():
    """Get active buses only"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM buses WHERE status = "Active" ORDER BY bus_number')
    buses = cursor.fetchall()
    conn.close()
    return buses

def add_bus(bus_number, model, capacity, year=None, status='Active', notes=None, created_by=None):
    """Add new bus"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO buses (bus_number, model, capacity, year, status, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (bus_number, model, capacity, year, status, notes, created_by))
        conn.commit()
        bus_id = cursor.lastrowid
        log_audit_trail(created_by or 'System', 'INSERT', 'buses', bus_id, None, 
                       {'bus_number': bus_number, 'model': model})
        return bus_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def update_bus(bus_id, bus_number, model, capacity, year=None, status='Active', notes=None):
    """Update bus details"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE buses 
        SET bus_number = ?, model = ?, capacity = ?, year = ?, status = ?, notes = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (bus_number, model, capacity, year, status, notes, bus_id))
    conn.commit()
    conn.close()

def delete_bus(bus_id):
    """Delete a bus"""
    conn = get_connection()
    cursor = conn.cursor()
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
    return routes

def add_route(name, distance=None, description=None, created_by=None):
    """Add new route"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO routes (name, distance, description, created_by)
            VALUES (?, ?, ?, ?)
        ''', (name, distance, description, created_by))
        conn.commit()
        route_id = cursor.lastrowid
        log_audit_trail(created_by or 'System', 'INSERT', 'routes', route_id, None, 
                       {'name': name, 'distance': distance})
        return route_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def update_route(route_id, name, distance=None, description=None):
    """Update route details"""
    conn = get_connection()
    cursor = conn.cursor()
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
    cursor.execute('DELETE FROM routes WHERE id = ?', (route_id,))
    conn.commit()
    conn.close()

# ============================================================================
# EMPLOYEE FUNCTIONS
# ============================================================================

def get_employees_by_role(role):
    """Get all employees with a specific role"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM employees WHERE position LIKE ? AND status = "Active"', (f'%{role}%',))
    employees = cursor.fetchall()
    conn.close()
    return employees

def get_employee_by_id(emp_id):
    """Get employee by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM employees WHERE id = ?', (emp_id,))
    employee = cursor.fetchone()
    conn.close()
    return employee

def get_all_employees(filters=None):
    """Get all employees with optional filters"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM employees WHERE 1=1'
    params = []
    
    if filters:
        if filters.get('department'):
            query += ' AND department = ?'
            params.append(filters['department'])
        if filters.get('position'):
            query += ' AND position LIKE ?'
            params.append(f"%{filters['position']}%")
        if filters.get('status'):
            query += ' AND status = ?'
            params.append(filters['status'])
    
    query += ' ORDER BY full_name'
    cursor.execute(query, params)
    employees = cursor.fetchall()
    conn.close()
    return employees

# ============================================================================
# INCOME FUNCTIONS
# ============================================================================

def get_income_records(filters=None):
    """Get income records with optional filters"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM income WHERE 1=1'
    params = []
    
    if filters:
        if filters.get('date'):
            query += ' AND date = ?'
            params.append(filters['date'])
        if filters.get('bus_number'):
            query += ' AND bus_number LIKE ?'
            params.append(f"%{filters['bus_number']}%")
        if filters.get('route'):
            query += ' AND route LIKE ?'
            params.append(f"%{filters['route']}%")
        if filters.get('driver_name'):
            query += ' AND driver_name LIKE ?'
            params.append(f"%{filters['driver_name']}%")
    
    query += ' ORDER BY date DESC, id DESC'
    cursor.execute(query, params)
    records = cursor.fetchall()
    conn.close()
    return records

def add_income_record(bus_number, route, hire_destination, driver_name, conductor_name,
                     date, amount, notes=None, created_by=None):
    """Add new income record"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO income (bus_number, route, hire_destination, driver_name, conductor_name,
                           date, amount, notes, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (bus_number, route, hire_destination, driver_name, conductor_name, 
          date, amount, notes, created_by))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    log_audit_trail(created_by or 'System', 'INSERT', 'income', record_id, None,
                   {'bus_number': bus_number, 'route': route, 'amount': amount})
    return record_id