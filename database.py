"""
database.py - Database initialization and management
COMPLETE FIXED VERSION with driver documents tracking
"""

import os
from datetime import datetime

# Detect if we're on Railway (PostgreSQL) or local (SQLite)
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("🐘 Using PostgreSQL database (Railway)")
else:
    import sqlite3
    print("🗄️ Using SQLite database (local development)")
    DATABASE_PATH = "bus_management.db"

def get_connection():
    """Create database connection"""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

# Alias for compatibility
get_db_connection = get_connection

def init_database():
    """Initialize all database tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        # PostgreSQL syntax
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buses (
                id SERIAL PRIMARY KEY,
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
        
        # ENHANCED EMPLOYEES TABLE with driver documents
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
                date_of_birth TEXT,
                emergency_contact TEXT,
                emergency_phone TEXT,
                license_number TEXT,
                license_expiry TEXT,
                defensive_driving_expiry TEXT,
                medical_cert_expiry TEXT,
                retest_date TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ENHANCED INCOME TABLE with employee IDs
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bus_assignments (
                id SERIAL PRIMARY KEY,
                bus_number TEXT NOT NULL,
                driver_employee_id TEXT,
                conductor_employee_id TEXT,
                assignment_date DATE NOT NULL,
                shift TEXT DEFAULT 'Full Day',
                route TEXT,
                notes TEXT,
                created_by TEXT DEFAULT 'SYSTEM',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leave_records (
                id SERIAL PRIMARY KEY,
                employee_id TEXT NOT NULL,
                leave_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'Pending',
                approved_by TEXT,
                approved_date TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payroll (
                id SERIAL PRIMARY KEY,
                employee_id TEXT NOT NULL,
                pay_period TEXT NOT NULL,
                basic_salary REAL NOT NULL,
                allowances REAL DEFAULT 0,
                deductions REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                net_salary REAL NOT NULL,
                payment_method TEXT,
                status TEXT DEFAULT 'Pending',
                payment_date TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_records (
                id SERIAL PRIMARY KEY,
                employee_id TEXT NOT NULL,
                evaluation_period TEXT NOT NULL,
                rating INTEGER NOT NULL,
                strengths TEXT,
                weaknesses TEXT,
                goals TEXT,
                evaluator TEXT,
                evaluation_date TEXT NOT NULL,
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS disciplinary_records (
                id SERIAL PRIMARY KEY,
                employee_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                violation_description TEXT,
                action_details TEXT,
                record_date TEXT NOT NULL,
                due_date TEXT,
                resolution_date TEXT,
                issued_by TEXT,
                status TEXT DEFAULT 'Active',
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_username ON activity_log(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_driver ON income(driver_employee_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_conductor ON income(conductor_employee_id)')
        
    else:
        # SQLite syntax
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
        
        # ENHANCED EMPLOYEES TABLE with driver documents
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
                date_of_birth TEXT,
                emergency_contact TEXT,
                emergency_phone TEXT,
                license_number TEXT,
                license_expiry TEXT,
                defensive_driving_expiry TEXT,
                medical_cert_expiry TEXT,
                retest_date TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ENHANCED INCOME TABLE with employee IDs
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
                assignment_date DATE NOT NULL,
                shift TEXT DEFAULT 'Full Day',
                route TEXT,
                notes TEXT,
                created_by TEXT DEFAULT 'SYSTEM',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (driver_employee_id) REFERENCES employees(employee_id),
                FOREIGN KEY (conductor_employee_id) REFERENCES employees(employee_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leave_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                leave_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'Pending',
                approved_by TEXT,
                approved_date TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payroll (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                pay_period TEXT NOT NULL,
                basic_salary REAL NOT NULL,
                allowances REAL DEFAULT 0,
                deductions REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                net_salary REAL NOT NULL,
                payment_method TEXT,
                status TEXT DEFAULT 'Pending',
                payment_date TEXT,
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                evaluation_period TEXT NOT NULL,
                rating INTEGER NOT NULL,
                strengths TEXT,
                weaknesses TEXT,
                goals TEXT,
                evaluator TEXT,
                evaluation_date TEXT NOT NULL,
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS disciplinary_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                violation_description TEXT,
                action_details TEXT,
                record_date TEXT NOT NULL,
                due_date TEXT,
                resolution_date TEXT,
                issued_by TEXT,
                status TEXT DEFAULT 'Active',
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                new_values TEXT
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_username ON activity_log(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_driver ON income(driver_employee_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_conductor ON income(conductor_employee_id)')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def verify_database():
    """Verify all required tables exist"""
    conn = get_connection()
    cursor = conn.cursor()
    
    required_tables = [
        'buses', 'routes', 'employees', 'income', 'maintenance',
        'bus_assignments', 'leave_records', 'payroll', 
        'performance_records', 'disciplinary_records', 'activity_log'
    ]
    
    missing_tables = []
    
    for table_name in required_tables:
        try:
            if USE_POSTGRES:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, (table_name,))
                exists = cursor.fetchone()[0] if USE_POSTGRES else cursor.fetchone()['exists']
                if not exists:
                    missing_tables.append(table_name)
            else:
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?;
                """, (table_name,))
                if cursor.fetchone() is None:
                    missing_tables.append(table_name)
        except Exception as e:
            print(f"❌ Error checking table {table_name}: {e}")
            missing_tables.append(table_name)
    
    conn.close()
    
    if missing_tables:
        raise Exception(f"Missing tables: {', '.join(missing_tables)}")
    
    print(f"✅ All {len(required_tables)} tables verified")
    return True

# ============================================================================
# EMPLOYEE HELPER FUNCTIONS
# ============================================================================

def get_active_drivers():
    """Get list of active drivers - READ ONLY"""
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
            WHERE position LIKE '%Driver%' AND status = 'Active'
            ORDER BY full_name
        """)
    
    drivers = cursor.fetchall()
    conn.close()
    return drivers

def get_active_conductors():
    """Get list of active conductors - READ ONLY"""
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
            WHERE position LIKE '%Conductor%' AND status = 'Active'
            ORDER BY full_name
        """)
    
    conductors = cursor.fetchall()
    conn.close()
    return conductors

def get_active_mechanics():
    """Get list of active mechanics - READ ONLY"""
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
            WHERE position LIKE '%Mechanic%' AND status = 'Active'
            ORDER BY full_name
        """)
    
    mechanics = cursor.fetchall()
    conn.close()
    return mechanics

def check_employee_usage(employee_id):
    """Check if employee is used in any records"""
    conn = get_connection()
    cursor = conn.cursor()
    
    usage = {
        'income_records': 0,
        'assignments': 0,
        'payroll': 0,
        'performance': 0,
        'leave': 0,
        'disciplinary': 0,
        'can_delete': False
    }
    
    try:
        # Check income records
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) as count FROM income WHERE driver_employee_id = %s OR conductor_employee_id = %s", 
                         (employee_id, employee_id))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM income WHERE driver_employee_id = ? OR conductor_employee_id = ?", 
                         (employee_id, employee_id))
        usage['income_records'] = cursor.fetchone()[0] if USE_POSTGRES else cursor.fetchone()['count']
        
        # Check assignments
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) as count FROM bus_assignments WHERE driver_employee_id = %s OR conductor_employee_id = %s", 
                         (employee_id, employee_id))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM bus_assignments WHERE driver_employee_id = ? OR conductor_employee_id = ?", 
                         (employee_id, employee_id))
        usage['assignments'] = cursor.fetchone()[0] if USE_POSTGRES else cursor.fetchone()['count']
        
        # Check payroll
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) as count FROM payroll WHERE employee_id = %s", (employee_id,))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM payroll WHERE employee_id = ?", (employee_id,))
        usage['payroll'] = cursor.fetchone()[0] if USE_POSTGRES else cursor.fetchone()['count']
        
        # Check performance records
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) as count FROM performance_records WHERE employee_id = %s", (employee_id,))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM performance_records WHERE employee_id = ?", (employee_id,))
        usage['performance'] = cursor.fetchone()[0] if USE_POSTGRES else cursor.fetchone()['count']
        
        # Check leave records
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) as count FROM leave_records WHERE employee_id = %s", (employee_id,))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM leave_records WHERE employee_id = ?", (employee_id,))
        usage['leave'] = cursor.fetchone()[0] if USE_POSTGRES else cursor.fetchone()['count']
        
        # Check disciplinary records
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) as count FROM disciplinary_records WHERE employee_id = %s", (employee_id,))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM disciplinary_records WHERE employee_id = ?", (employee_id,))
        usage['disciplinary'] = cursor.fetchone()[0] if USE_POSTGRES else cursor.fetchone()['count']
        
        # Can only delete if no records exist
        total_usage = sum([usage['income_records'], usage['assignments'], usage['payroll'], 
                          usage['performance'], usage['leave'], usage['disciplinary']])
        usage['can_delete'] = total_usage == 0
        usage['total_records'] = total_usage
        
    except Exception as e:
        print(f"Error checking employee usage: {e}")
    finally:
        conn.close()
    
    return usage

def get_expiring_driver_documents(days_threshold=30):
    """Get drivers with expiring documents"""
    conn = get_connection()
    cursor = conn.cursor()
    
    from datetime import datetime, timedelta
    
    alerts = []
    current_date = datetime.now().date()
    threshold_date = current_date + timedelta(days=days_threshold)
    
    # Check all document types for drivers
    document_checks = [
        ('license_expiry', 'Driver License'),
        ('defensive_driving_expiry', 'Defensive Driving Certificate'),
        ('medical_cert_expiry', 'Medical Certificate'),
        ('retest_date', 'Retest Due')
    ]
    
    for date_column, doc_name in document_checks:
        if USE_POSTGRES:
            query = f"""
                SELECT employee_id, full_name, position, {date_column}
                FROM employees
                WHERE {date_column} IS NOT NULL
                AND {date_column}::date <= %s
                AND status = %s
                AND position LIKE %s
                ORDER BY {date_column}
            """
            cursor.execute(query, (threshold_date.strftime('%Y-%m-%d'), 'Active', '%Driver%'))
        else:
            query = f"""
                SELECT employee_id, full_name, position, {date_column}
                FROM employees
                WHERE {date_column} IS NOT NULL
                AND {date_column} != ''
                AND date({date_column}) <= date(?)
                AND status = 'Active'
                AND position LIKE '%Driver%'
                ORDER BY {date_column}
            """
            cursor.execute(query, (threshold_date.strftime('%Y-%m-%d'),))
        
        results = cursor.fetchall()
        
        for row in results:
            emp_id = row[0] if USE_POSTGRES else row['employee_id']
            name = row[1] if USE_POSTGRES else row['full_name']
            position = row[2] if USE_POSTGRES else row['position']
            expiry_date = row[3] if USE_POSTGRES else row[date_column]
            
            try:
                expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
                days_until = (expiry - current_date).days
                
                if days_until < 0:
                    urgency = 'expired'
                elif days_until <= 7:
                    urgency = 'critical'
                elif days_until <= 14:
                    urgency = 'warning'
                else:
                    urgency = 'info'
                
                alerts.append({
                    'employee_id': emp_id,
                    'name': name,
                    'position': position,
                    'document': doc_name,
                    'expiry_date': expiry_date,
                    'days_until': days_until,
                    'urgency': urgency,
                    'expired': days_until < 0
                })
            except ValueError:
                continue
    
    conn.close()
    
    # Sort by urgency and days remaining
    alerts.sort(key=lambda x: (not x['expired'], x['days_until']))
    
    return alerts

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
    
    if USE_POSTGRES:
        cursor.execute('SELECT * FROM buses WHERE status = %s ORDER BY bus_number', ('Active',))
    else:
        cursor.execute('SELECT * FROM buses WHERE status = "Active" ORDER BY bus_number')
    
    buses = cursor.fetchall()
    conn.close()
    return buses

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
            bus_id = cursor.fetchone()[0]
        else:
            cursor.execute('''
                INSERT INTO buses (bus_number, registration_number, model, capacity, year, status, notes, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bus_number, registration_number, model, capacity, year, status, notes, created_by))
            bus_id = cursor.lastrowid
        
        conn.commit()
        return bus_id
    except Exception:
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
            SET bus_number = %s, registration_number = %s, model = %s, capacity = %s, 
                year = %s, status = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (bus_number, registration_number, model, capacity, year, status, notes, bus_id))
    else:
        cursor.execute('''
            UPDATE buses 
            SET bus_number = ?, registration_number = ?, model = ?, capacity = ?, 
                year = ?, status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
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

def check_bus_usage(bus_number):
    """Check if bus is used in any records"""
    conn = get_connection()
    cursor = conn.cursor()
    
    usage = {
        'income_records': 0,
        'maintenance_records': 0,
        'assignments': 0,
        'can_delete': False
    }
    
    try:
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) FROM income WHERE bus_number = %s", (bus_number,))
            usage['income_records'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM maintenance WHERE bus_number = %s", (bus_number,))
            usage['maintenance_records'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bus_assignments WHERE bus_number = %s", (bus_number,))
            usage['assignments'] = cursor.fetchone()[0]
        else:
            cursor.execute("SELECT COUNT(*) as count FROM income WHERE bus_number = ?", (bus_number,))
            usage['income_records'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM maintenance WHERE bus_number = ?", (bus_number,))
            usage['maintenance_records'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM bus_assignments WHERE bus_number = ?", (bus_number,))
            usage['assignments'] = cursor.fetchone()['count']
        
        total_usage = sum([usage['income_records'], usage['maintenance_records'], usage['assignments']])
        usage['can_delete'] = total_usage == 0
        usage['total_records'] = total_usage
        
    except Exception as e:
        print(f"Error checking bus usage: {e}")
    finally:
        conn.close()
    
    return usage

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
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO routes (name, distance, description, created_by)
                VALUES (%s, %s, %s, %s) RETURNING id
            ''', (name, distance, description, created_by))
            route_id = cursor.fetchone()[0]
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