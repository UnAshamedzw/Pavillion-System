"""
auth.py - User Authentication Module with Role-Based Permissions
Pavillion Coaches Bus Management System
Handles user login, registration, session management, and permissions
"""

import streamlit as st
import hashlib
import secrets
from datetime import datetime, timedelta

# Import database abstraction layer
from database import get_connection, USE_POSTGRES

# Session duration in days
SESSION_DURATION_DAYS = 7


# =============================================================================
# PASSWORD HASHING
# =============================================================================

def hash_password(password: str, salt: str = None) -> tuple:
    """
    Hash password with salt using SHA-256
    Returns: (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    pwd_salt = f"{password}{salt}".encode('utf-8')
    hashed = hashlib.sha256(pwd_salt).hexdigest()
    
    return hashed, salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """Verify if password matches the hashed password"""
    test_hash, _ = hash_password(password, salt)
    return test_hash == hashed_password


# =============================================================================
# PERMISSION DEFINITIONS
# =============================================================================

# All available permissions in the system (47 total)
ALL_PERMISSIONS = {
    # ----- FLEET / OPERATIONS -----
    'view_fleet': 'View bus fleet information',
    'add_bus': 'Add new buses to fleet',
    'edit_bus': 'Edit bus information',
    'delete_bus': 'Delete buses from fleet',
    'manage_bus_documents': 'Manage bus documents and expiry dates',
    
    'view_routes': 'View routes',
    'add_route': 'Create new routes',
    'edit_route': 'Edit route information',
    'delete_route': 'Delete routes',
    
    'view_assignments': 'View bus assignments',
    'create_assignment': 'Create bus assignments',
    'edit_assignment': 'Edit bus assignments',
    'delete_assignment': 'Delete bus assignments',
    
    # ----- INCOME / REVENUE -----
    'view_income': 'View income records',
    'add_income': 'Add income entries',
    'edit_income': 'Edit income entries',
    'delete_income': 'Delete income entries',
    'export_income': 'Export income reports',
    
    # ----- MAINTENANCE -----
    'view_maintenance': 'View maintenance records',
    'add_maintenance': 'Add maintenance entries',
    'edit_maintenance': 'Edit maintenance entries',
    'delete_maintenance': 'Delete maintenance entries',
    'export_maintenance': 'Export maintenance reports',
    
    # ----- HR / EMPLOYEES -----
    'view_employees': 'View employee information',
    'add_employee': 'Add new employees',
    'edit_employee': 'Edit employee information',
    'delete_employee': 'Delete/deactivate employees',
    'manage_employee_documents': 'Manage employee documents and expiry',
    
    'view_performance': 'View employee performance records',
    'add_performance': 'Add performance records',
    'edit_performance': 'Edit performance records',
    
    'view_leave': 'View leave requests',
    'apply_leave': 'Apply for leave (own)',
    'approve_leave': 'Approve/reject leave requests',
    'manage_leave': 'Full leave management',
    
    'view_disciplinary': 'View disciplinary records',
    'add_disciplinary': 'Add disciplinary records',
    'edit_disciplinary': 'Edit disciplinary records',
    
    # ----- PAYROLL -----
    'view_payroll': 'View payroll information',
    'manage_payroll': 'Manage payroll (add, edit, process)',
    'approve_payroll': 'Approve payroll for payment',
    'export_payroll': 'Export payroll reports',
    
    # ----- ANALYTICS / REPORTS -----
    'view_dashboard': 'View main dashboard',
    'view_bus_analysis': 'View bus-by-bus analysis',
    'view_performance_metrics': 'View performance metrics/KPIs',
    'view_revenue_history': 'View revenue history',
    'generate_reports': 'Generate PDF/Excel reports',
    
    # ----- DATA IMPORT -----
    'import_data': 'Import data from Excel/CSV',
    
    # ----- USER MANAGEMENT (System Admin only) -----
    'view_users': 'View user accounts',
    'add_user': 'Create new user accounts',
    'edit_user': 'Edit user accounts',
    'delete_user': 'Delete/deactivate user accounts',
    'manage_roles': 'Manage roles and permissions',
    'reset_passwords': 'Reset user passwords',
    
    # ----- AUDIT / SECURITY (System Admin only) -----
    'view_audit_logs': 'View audit logs',
    'view_all_activity': 'View all user activity',
    'manage_system_settings': 'Manage system-wide settings',
}

# Permission categories for UI organization
PERMISSION_CATEGORIES = {
    'Fleet Management': [
        'view_fleet', 'add_bus', 'edit_bus', 'delete_bus', 'manage_bus_documents'
    ],
    'Routes & Assignments': [
        'view_routes', 'add_route', 'edit_route', 'delete_route',
        'view_assignments', 'create_assignment', 'edit_assignment', 'delete_assignment'
    ],
    'Income / Revenue': [
        'view_income', 'add_income', 'edit_income', 'delete_income', 'export_income'
    ],
    'Maintenance': [
        'view_maintenance', 'add_maintenance', 'edit_maintenance', 'delete_maintenance', 'export_maintenance'
    ],
    'HR - Employees': [
        'view_employees', 'add_employee', 'edit_employee', 'delete_employee', 'manage_employee_documents'
    ],
    'HR - Performance': [
        'view_performance', 'add_performance', 'edit_performance'
    ],
    'HR - Leave': [
        'view_leave', 'apply_leave', 'approve_leave', 'manage_leave'
    ],
    'HR - Disciplinary': [
        'view_disciplinary', 'add_disciplinary', 'edit_disciplinary'
    ],
    'Payroll': [
        'view_payroll', 'manage_payroll', 'approve_payroll', 'export_payroll'
    ],
    'Analytics & Reports': [
        'view_dashboard', 'view_bus_analysis', 'view_performance_metrics', 
        'view_revenue_history', 'generate_reports'
    ],
    'Data Import': [
        'import_data'
    ],
    'User Management': [
        'view_users', 'add_user', 'edit_user', 'delete_user', 'manage_roles', 'reset_passwords'
    ],
    'Audit & Security': [
        'view_audit_logs', 'view_all_activity', 'manage_system_settings'
    ]
}

# =============================================================================
# PREDEFINED ROLES WITH DEFAULT PERMISSIONS
# =============================================================================

PREDEFINED_ROLES = {
    'System Admin': {
        'description': 'Full system access - all permissions',
        'permissions': list(ALL_PERMISSIONS.keys()),
        'is_system_role': True,
        'can_be_modified': False
    },
    
    'Director': {
        'description': 'Full business functionality, no system configuration',
        'permissions': [
            # Fleet
            'view_fleet', 'add_bus', 'edit_bus', 'delete_bus', 'manage_bus_documents',
            # Routes
            'view_routes', 'add_route', 'edit_route', 'delete_route',
            'view_assignments', 'create_assignment', 'edit_assignment', 'delete_assignment',
            # Income
            'view_income', 'add_income', 'edit_income', 'delete_income', 'export_income',
            # Maintenance
            'view_maintenance', 'add_maintenance', 'edit_maintenance', 'delete_maintenance', 'export_maintenance',
            # HR
            'view_employees', 'add_employee', 'edit_employee', 'delete_employee', 'manage_employee_documents',
            'view_performance', 'add_performance', 'edit_performance',
            'view_leave', 'approve_leave', 'manage_leave',
            'view_disciplinary', 'add_disciplinary', 'edit_disciplinary',
            # Payroll
            'view_payroll', 'manage_payroll', 'approve_payroll', 'export_payroll',
            # Analytics
            'view_dashboard', 'view_bus_analysis', 'view_performance_metrics', 
            'view_revenue_history', 'generate_reports',
            # Data
            'import_data',
        ],
        'is_system_role': True,
        'can_be_modified': False
    },
    
    'HR Manager': {
        'description': 'Full HR functionality',
        'permissions': [
            'view_employees', 'add_employee', 'edit_employee', 'delete_employee', 'manage_employee_documents',
            'view_performance', 'add_performance', 'edit_performance',
            'view_leave', 'approve_leave', 'manage_leave',
            'view_disciplinary', 'add_disciplinary', 'edit_disciplinary',
            'view_payroll', 'manage_payroll', 'export_payroll',
            'view_fleet', 'view_routes', 'view_assignments',
            'view_dashboard', 'view_performance_metrics', 'generate_reports',
        ],
        'is_system_role': False,
        'can_be_modified': True
    },
    
    'Operations Manager': {
        'description': 'Full operations and fleet management',
        'permissions': [
            'view_fleet', 'add_bus', 'edit_bus', 'manage_bus_documents',
            'view_routes', 'add_route', 'edit_route', 'delete_route',
            'view_assignments', 'create_assignment', 'edit_assignment', 'delete_assignment',
            'view_income', 'add_income', 'edit_income', 'delete_income', 'export_income',
            'view_maintenance', 'add_maintenance', 'edit_maintenance', 'delete_maintenance', 'export_maintenance',
            'view_employees', 'view_performance',
            'view_dashboard', 'view_bus_analysis', 'view_performance_metrics', 
            'view_revenue_history', 'generate_reports',
            'import_data',
        ],
        'is_system_role': False,
        'can_be_modified': True
    },
    
    'Finance Manager': {
        'description': 'Financial oversight and reporting',
        'permissions': [
            'view_income', 'export_income',
            'view_maintenance', 'export_maintenance',
            'view_payroll', 'manage_payroll', 'approve_payroll', 'export_payroll',
            'view_fleet', 'view_routes',
            'view_employees',
            'view_dashboard', 'view_bus_analysis', 'view_performance_metrics', 
            'view_revenue_history', 'generate_reports',
        ],
        'is_system_role': False,
        'can_be_modified': True
    },
    
    'Route Supervisor': {
        'description': 'Route and assignment management',
        'permissions': [
            'view_fleet',
            'view_routes', 'add_route', 'edit_route',
            'view_assignments', 'create_assignment', 'edit_assignment',
            'view_income', 'add_income',
            'view_employees',
            'view_dashboard',
        ],
        'is_system_role': False,
        'can_be_modified': True
    },
    
    'Workshop Supervisor': {
        'description': 'Maintenance and workshop management',
        'permissions': [
            'view_fleet', 'edit_bus', 'manage_bus_documents',
            'view_maintenance', 'add_maintenance', 'edit_maintenance', 'delete_maintenance', 'export_maintenance',
            'view_dashboard', 'view_bus_analysis',
        ],
        'is_system_role': False,
        'can_be_modified': True
    },
    
    'Payroll Officer': {
        'description': 'Payroll processing',
        'permissions': [
            'view_employees',
            'view_payroll', 'manage_payroll', 'export_payroll',
            'view_dashboard',
        ],
        'is_system_role': False,
        'can_be_modified': True
    },
    
    'Data Entry Clerk': {
        'description': 'Basic data entry',
        'permissions': [
            'view_fleet',
            'view_routes', 'view_assignments',
            'view_income', 'add_income',
            'view_maintenance', 'add_maintenance',
            'view_dashboard',
        ],
        'is_system_role': False,
        'can_be_modified': True
    },
    
    'Driver': {
        'description': 'Limited access for drivers',
        'permissions': [
            'view_routes',
            'view_assignments',
            'apply_leave',
            'view_leave',
        ],
        'is_system_role': False,
        'can_be_modified': True
    },
    
    'Conductor': {
        'description': 'Limited access for conductors',
        'permissions': [
            'view_routes',
            'view_assignments',
            'apply_leave',
            'view_leave',
        ],
        'is_system_role': False,
        'can_be_modified': True
    },
}


# =============================================================================
# DATABASE TABLE CREATION
# =============================================================================

def create_sessions_table():
    """Create sessions table for persistent login"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_valid INTEGER DEFAULT 1
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_valid INTEGER DEFAULT 1
            )
        ''')
    
    conn.commit()
    conn.close()


def create_users_table():
    """Create users table if it doesn't exist"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
    
    conn.commit()
    
    # Create default admin account if no users exist
    cursor.execute('SELECT COUNT(*) FROM users')
    result = cursor.fetchone()
    count = result['count'] if hasattr(result, 'keys') else result[0]
    
    if count == 0:
        hashed_pwd, salt = hash_password('admin123')
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO users (username, password_hash, salt, full_name, role, email)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', ('admin', hashed_pwd, salt, 'System Administrator', 'System Admin', 'admin@pavillion.com'))
        else:
            cursor.execute('''
                INSERT INTO users (username, password_hash, salt, full_name, role, email)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', hashed_pwd, salt, 'System Administrator', 'System Admin', 'admin@pavillion.com'))
    
    conn.commit()
    conn.close()


def create_permissions_tables():
    """Create the permissions and roles tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        # Roles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                is_system_role BOOLEAN DEFAULT FALSE,
                can_be_modified BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Role permissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                id SERIAL PRIMARY KEY,
                role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
                permission TEXT NOT NULL,
                UNIQUE(role_id, permission)
            )
        ''')
        
        # User custom permissions (override role permissions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_permissions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                permission TEXT NOT NULL,
                granted BOOLEAN DEFAULT TRUE,
                UNIQUE(user_id, permission)
            )
        ''')
    else:
        # SQLite version
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                is_system_role INTEGER DEFAULT 0,
                can_be_modified INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
                permission TEXT NOT NULL,
                UNIQUE(role_id, permission)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                permission TEXT NOT NULL,
                granted INTEGER DEFAULT 1,
                UNIQUE(user_id, permission)
            )
        ''')
    
    conn.commit()
    conn.close()


def initialize_predefined_roles():
    """Initialize predefined roles in the database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    for role_name, role_data in PREDEFINED_ROLES.items():
        try:
            # Check if role exists
            if USE_POSTGRES:
                cursor.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
            else:
                cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
            
            existing = cursor.fetchone()
            
            if not existing:
                # Insert role
                if USE_POSTGRES:
                    cursor.execute('''
                        INSERT INTO roles (name, description, is_system_role, can_be_modified)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    ''', (role_name, role_data['description'], 
                          role_data['is_system_role'], role_data['can_be_modified']))
                    result = cursor.fetchone()
                    # Handle both dict-like (RealDictCursor) and tuple results
                    role_id = result['id'] if hasattr(result, 'keys') else result[0]
                else:
                    cursor.execute('''
                        INSERT INTO roles (name, description, is_system_role, can_be_modified)
                        VALUES (?, ?, ?, ?)
                    ''', (role_name, role_data['description'], 
                          1 if role_data['is_system_role'] else 0, 
                          1 if role_data['can_be_modified'] else 0))
                    role_id = cursor.lastrowid
                
                # Insert permissions for this role
                for permission in role_data['permissions']:
                    if USE_POSTGRES:
                        cursor.execute('''
                            INSERT INTO role_permissions (role_id, permission)
                            VALUES (%s, %s)
                            ON CONFLICT (role_id, permission) DO NOTHING
                        ''', (role_id, permission))
                    else:
                        cursor.execute('''
                            INSERT OR IGNORE INTO role_permissions (role_id, permission)
                            VALUES (?, ?)
                        ''', (role_id, permission))
                
                conn.commit()
                print(f"✅ Initialized role: {role_name} with {len(role_data['permissions'])} permissions")
        except Exception as e:
            print(f"Error initializing role {role_name}: {e}")
            continue
    
    conn.close()


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

def create_session(user_id: int) -> str:
    """Create a new session token for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=SESSION_DURATION_DAYS)
    
    if USE_POSTGRES:
        cursor.execute('''
            INSERT INTO user_sessions (user_id, session_token, expires_at)
            VALUES (%s, %s, %s)
        ''', (user_id, session_token, expires_at))
    else:
        cursor.execute('''
            INSERT INTO user_sessions (user_id, session_token, expires_at)
            VALUES (?, ?, ?)
        ''', (user_id, session_token, expires_at))
    
    conn.commit()
    conn.close()
    
    return session_token


def validate_session(session_token: str) -> dict:
    """Validate a session token and return user info if valid"""
    if not session_token:
        return None
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            SELECT s.user_id, s.expires_at, s.is_valid,
                   u.id, u.username, u.full_name, u.role, u.email, u.is_active
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = %s
        ''', (session_token,))
    else:
        cursor.execute('''
            SELECT s.user_id, s.expires_at, s.is_valid,
                   u.id, u.username, u.full_name, u.role, u.email, u.is_active
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_token = ?
        ''', (session_token,))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return None
    
    if hasattr(result, 'keys'):
        expires_at = result['expires_at']
        is_valid = result['is_valid']
        is_active = result['is_active']
        user_id = result['id']
        username = result['username']
        full_name = result['full_name']
        role = result['role']
        email = result['email']
    else:
        _, expires_at, is_valid, user_id, username, full_name, role, email, is_active = result
    
    if not is_valid or not is_active:
        return None
    
    if isinstance(expires_at, str):
        expires_at = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
    
    if datetime.now() > expires_at:
        return None
    
    return {
        'id': user_id,
        'username': username,
        'full_name': full_name,
        'role': role,
        'email': email,
        'session_token': session_token
    }


def invalidate_session(session_token: str):
    """Invalidate a session token (logout)"""
    if not session_token:
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('UPDATE user_sessions SET is_valid = 0 WHERE session_token = %s', (session_token,))
    else:
        cursor.execute('UPDATE user_sessions SET is_valid = 0 WHERE session_token = ?', (session_token,))
    
    conn.commit()
    conn.close()


def restore_session():
    """Try to restore session from query params on page load"""
    if st.session_state.get('authenticated', False):
        return True
    
    session_token = st.query_params.get('session')
    if session_token:
        user = validate_session(session_token)
        if user:
            st.session_state['authenticated'] = True
            st.session_state['user'] = user
            st.session_state['session_token'] = session_token
            # Clear cached permissions when restoring session
            if 'user_permissions' in st.session_state:
                del st.session_state['user_permissions']
            return True
        else:
            del st.query_params['session']
    
    return False


# =============================================================================
# USER AUTHENTICATION
# =============================================================================

def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user and return user details if successful"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            SELECT id, username, password_hash, salt, full_name, role, email, is_active
            FROM users WHERE username = %s
        ''', (username,))
    else:
        cursor.execute('''
            SELECT id, username, password_hash, salt, full_name, role, email, is_active
            FROM users WHERE username = ?
        ''', (username,))
    
    user = cursor.fetchone()
    
    if user:
        if hasattr(user, 'keys'):
            user_id = user['id']
            db_username = user['username']
            password_hash = user['password_hash']
            salt = user['salt']
            full_name = user['full_name']
            role = user['role']
            email = user['email']
            is_active = user['is_active']
        else:
            user_id, db_username, password_hash, salt, full_name, role, email, is_active = user
        
        if is_active == 1:
            if verify_password(password, password_hash, salt):
                if USE_POSTGRES:
                    cursor.execute('UPDATE users SET last_login = %s WHERE id = %s', (datetime.now(), user_id))
                else:
                    cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now(), user_id))
                conn.commit()
                conn.close()
                
                session_id = secrets.token_hex(16)
                
                return {
                    'id': user_id,
                    'username': db_username,
                    'full_name': full_name,
                    'role': role,
                    'email': email,
                    'session_id': session_id
                }
    
    conn.close()
    return None


def register_user(username: str, password: str, full_name: str, role: str, email: str = None) -> bool:
    """Register a new user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        hashed_pwd, salt = hash_password(password)
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO users (username, password_hash, salt, full_name, role, email)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (username, hashed_pwd, salt, full_name, role, email))
        else:
            cursor.execute('''
                INSERT INTO users (username, password_hash, salt, full_name, role, email)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, hashed_pwd, salt, full_name, role, email))
        
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Change user password"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('SELECT password_hash, salt FROM users WHERE id = %s', (user_id,))
    else:
        cursor.execute('SELECT password_hash, salt FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        if hasattr(result, 'keys'):
            password_hash = result['password_hash']
            salt = result['salt']
        else:
            password_hash, salt = result[0], result[1]
        
        if verify_password(old_password, password_hash, salt):
            new_hash, new_salt = hash_password(new_password)
            if USE_POSTGRES:
                cursor.execute('UPDATE users SET password_hash = %s, salt = %s WHERE id = %s', (new_hash, new_salt, user_id))
            else:
                cursor.execute('UPDATE users SET password_hash = ?, salt = ? WHERE id = ?', (new_hash, new_salt, user_id))
            conn.commit()
            conn.close()
            return True
    
    conn.close()
    return False


def reset_user_password(user_id: int, new_password: str) -> bool:
    """Admin function to reset a user's password"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        new_hash, new_salt = hash_password(new_password)
        if USE_POSTGRES:
            cursor.execute('UPDATE users SET password_hash = %s, salt = %s WHERE id = %s', (new_hash, new_salt, user_id))
        else:
            cursor.execute('UPDATE users SET password_hash = ?, salt = ? WHERE id = ?', (new_hash, new_salt, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def get_all_users():
    """Get all users (excluding password info)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, full_name, role, email, created_at, last_login, is_active
        FROM users ORDER BY created_at DESC
    ''')
    
    users = cursor.fetchall()
    conn.close()
    return users


def update_user_status(user_id: int, is_active: bool) -> bool:
    """Activate or deactivate a user account"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('UPDATE users SET is_active = %s WHERE id = %s', (1 if is_active else 0, user_id))
    else:
        cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (1 if is_active else 0, user_id))
    conn.commit()
    conn.close()
    return True


def update_user_role(user_id: int, new_role: str) -> bool:
    """Update a user's role"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('UPDATE users SET role = %s WHERE id = %s', (new_role, user_id))
        else:
            cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def update_user_info(user_id: int, full_name: str, email: str) -> bool:
    """Update a user's basic info"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('UPDATE users SET full_name = %s, email = %s WHERE id = %s', (full_name, email, user_id))
        else:
            cursor.execute('UPDATE users SET full_name = ?, email = ? WHERE id = ?', (full_name, email, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def delete_user(user_id: int) -> bool:
    """Delete a user account"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
    else:
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True


# =============================================================================
# PERMISSION CHECKING FUNCTIONS
# =============================================================================

def get_user_permissions(user_id: int, user_role: str) -> set:
    """Get all permissions for a user based on their role and any custom overrides"""
    # System Admin has all permissions
    if user_role == 'System Admin':
        return set(ALL_PERMISSIONS.keys())
    
    # Director has all business permissions
    if user_role == 'Director':
        return set(PREDEFINED_ROLES['Director']['permissions'])
    
    # Check if role exists in predefined roles (for roles not yet in database)
    if user_role in PREDEFINED_ROLES:
        permissions = set(PREDEFINED_ROLES[user_role]['permissions'])
    else:
        permissions = set()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get role permissions from database
        if USE_POSTGRES:
            cursor.execute('''
                SELECT rp.permission 
                FROM role_permissions rp
                JOIN roles r ON rp.role_id = r.id
                WHERE r.name = %s
            ''', (user_role,))
        else:
            cursor.execute('''
                SELECT rp.permission 
                FROM role_permissions rp
                JOIN roles r ON rp.role_id = r.id
                WHERE r.name = ?
            ''', (user_role,))
        
        for row in cursor.fetchall():
            perm = row['permission'] if hasattr(row, 'keys') else row[0]
            permissions.add(perm)
        
        # Get user-specific overrides
        if USE_POSTGRES:
            cursor.execute('SELECT permission, granted FROM user_permissions WHERE user_id = %s', (user_id,))
        else:
            cursor.execute('SELECT permission, granted FROM user_permissions WHERE user_id = ?', (user_id,))
        
        for row in cursor.fetchall():
            if hasattr(row, 'keys'):
                perm, granted = row['permission'], row['granted']
            else:
                perm, granted = row[0], row[1]
            
            if granted:
                permissions.add(perm)
            else:
                permissions.discard(perm)
    
    except Exception:
        pass
    finally:
        conn.close()
    
    return permissions


def has_permission(permission: str) -> bool:
    """Check if current logged-in user has a specific permission"""
    if not st.session_state.get('authenticated', False):
        return False
    
    user = st.session_state.get('user', {})
    user_id = user.get('id')
    user_role = user.get('role', '')
    
    # System Admin has all permissions
    if user_role == 'System Admin':
        return True
    
    # Get user's permissions (cached in session state for performance)
    if 'user_permissions' not in st.session_state:
        st.session_state['user_permissions'] = get_user_permissions(user_id, user_role)
    
    return permission in st.session_state['user_permissions']


def has_any_permission(permissions: list) -> bool:
    """Check if user has ANY of the listed permissions"""
    return any(has_permission(p) for p in permissions)


def has_all_permissions(permissions: list) -> bool:
    """Check if user has ALL of the listed permissions"""
    return all(has_permission(p) for p in permissions)


def require_permission(permission: str) -> bool:
    """Require a permission for a page or action"""
    if not has_permission(permission):
        st.error("🚫 Access Denied: You don't have permission to access this feature.")
        st.info(f"Required permission: `{permission}` - {ALL_PERMISSIONS.get(permission, 'Unknown')}")
        return False
    return True


def check_permission(required_role: str) -> bool:
    """Legacy function - Check if current user has required role"""
    if not st.session_state.get('authenticated', False):
        return False
    
    user_role = st.session_state['user']['role']
    
    # System Admin has all permissions
    if user_role == 'System Admin':
        return True
    
    # Map old role names to new
    role_mapping = {
        'Admin': ['System Admin'],
        'Manager': ['System Admin', 'Director', 'HR Manager', 'Operations Manager', 'Finance Manager'],
        'User': list(PREDEFINED_ROLES.keys())
    }
    
    allowed_roles = role_mapping.get(required_role, [required_role])
    return user_role in allowed_roles


# =============================================================================
# ROLE MANAGEMENT
# =============================================================================

def get_all_roles():
    """Get all roles from database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, description, is_system_role, can_be_modified
        FROM roles
        ORDER BY is_system_role DESC, name
    ''')
    
    roles = cursor.fetchall()
    conn.close()
    
    return roles


def get_available_roles():
    """Get list of role names for dropdowns"""
    return list(PREDEFINED_ROLES.keys())


def get_role_permissions_by_name(role_name: str) -> list:
    """Get permissions for a role by name"""
    if role_name in PREDEFINED_ROLES:
        return PREDEFINED_ROLES[role_name]['permissions']
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('''
            SELECT rp.permission 
            FROM role_permissions rp
            JOIN roles r ON rp.role_id = r.id
            WHERE r.name = %s
        ''', (role_name,))
    else:
        cursor.execute('''
            SELECT rp.permission 
            FROM role_permissions rp
            JOIN roles r ON rp.role_id = r.id
            WHERE r.name = ?
        ''', (role_name,))
    
    permissions = [row['permission'] if hasattr(row, 'keys') else row[0] for row in cursor.fetchall()]
    conn.close()
    
    return permissions


def get_role_permissions(role_id: int) -> list:
    """Get all permissions for a specific role"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('SELECT permission FROM role_permissions WHERE role_id = %s', (role_id,))
    else:
        cursor.execute('SELECT permission FROM role_permissions WHERE role_id = ?', (role_id,))
    
    permissions = [row['permission'] if hasattr(row, 'keys') else row[0] for row in cursor.fetchall()]
    conn.close()
    
    return permissions


def update_role_permissions(role_id: int, permissions: list) -> bool:
    """Update permissions for a role"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('DELETE FROM role_permissions WHERE role_id = %s', (role_id,))
        else:
            cursor.execute('DELETE FROM role_permissions WHERE role_id = ?', (role_id,))
        
        for perm in permissions:
            if USE_POSTGRES:
                cursor.execute('INSERT INTO role_permissions (role_id, permission) VALUES (%s, %s)', (role_id, perm))
            else:
                cursor.execute('INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)', (role_id, perm))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating role permissions: {e}")
        return False
    finally:
        conn.close()


def create_custom_role(name: str, description: str, permissions: list) -> bool:
    """Create a new custom role"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO roles (name, description, is_system_role, can_be_modified)
                VALUES (%s, %s, FALSE, TRUE)
                RETURNING id
            ''', (name, description))
            result = cursor.fetchone()
            role_id = result['id'] if hasattr(result, 'keys') else result[0]
        else:
            cursor.execute('''
                INSERT INTO roles (name, description, is_system_role, can_be_modified)
                VALUES (?, ?, 0, 1)
            ''', (name, description))
            role_id = cursor.lastrowid
        
        for perm in permissions:
            if USE_POSTGRES:
                cursor.execute('INSERT INTO role_permissions (role_id, permission) VALUES (%s, %s)', (role_id, perm))
            else:
                cursor.execute('INSERT INTO role_permissions (role_id, permission) VALUES (?, ?)', (role_id, perm))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating role: {e}")
        return False
    finally:
        conn.close()


def delete_role(role_id: int) -> bool:
    """Delete a custom role (cannot delete system roles)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('SELECT is_system_role FROM roles WHERE id = %s', (role_id,))
        else:
            cursor.execute('SELECT is_system_role FROM roles WHERE id = ?', (role_id,))
        
        result = cursor.fetchone()
        if result:
            is_system = result['is_system_role'] if hasattr(result, 'keys') else result[0]
            if is_system:
                return False
        
        if USE_POSTGRES:
            cursor.execute('DELETE FROM role_permissions WHERE role_id = %s', (role_id,))
            cursor.execute('DELETE FROM roles WHERE id = %s', (role_id,))
        else:
            cursor.execute('DELETE FROM role_permissions WHERE role_id = ?', (role_id,))
            cursor.execute('DELETE FROM roles WHERE id = ?', (role_id,))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting role: {e}")
        return False
    finally:
        conn.close()


# =============================================================================
# USER PERMISSION OVERRIDES
# =============================================================================

def grant_user_permission(user_id: int, permission: str) -> bool:
    """Grant a specific permission to a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO user_permissions (user_id, permission, granted)
                VALUES (%s, %s, TRUE)
                ON CONFLICT (user_id, permission) DO UPDATE SET granted = TRUE
            ''', (user_id, permission))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO user_permissions (user_id, permission, granted)
                VALUES (?, ?, 1)
            ''', (user_id, permission))
        
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def revoke_user_permission(user_id: int, permission: str) -> bool:
    """Revoke a specific permission from a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO user_permissions (user_id, permission, granted)
                VALUES (%s, %s, FALSE)
                ON CONFLICT (user_id, permission) DO UPDATE SET granted = FALSE
            ''', (user_id, permission))
        else:
            cursor.execute('''
                INSERT OR REPLACE INTO user_permissions (user_id, permission, granted)
                VALUES (?, ?, 0)
            ''', (user_id, permission))
        
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_user_permission_overrides(user_id: int) -> dict:
    """Get user's permission overrides"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute('SELECT permission, granted FROM user_permissions WHERE user_id = %s', (user_id,))
    else:
        cursor.execute('SELECT permission, granted FROM user_permissions WHERE user_id = ?', (user_id,))
    
    overrides = {}
    for row in cursor.fetchall():
        if hasattr(row, 'keys'):
            overrides[row['permission']] = row['granted']
        else:
            overrides[row[0]] = row[1]
    
    conn.close()
    return overrides


def clear_user_permission_overrides(user_id: int) -> bool:
    """Clear all permission overrides for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute('DELETE FROM user_permissions WHERE user_id = %s', (user_id,))
        else:
            cursor.execute('DELETE FROM user_permissions WHERE user_id = ?', (user_id,))
        
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# =============================================================================
# PAGE ACCESS MAPPING
# =============================================================================

PAGE_PERMISSIONS = {
    '📈 Dashboard': ['view_dashboard'],
    '🔔 Alerts': ['view_dashboard'],  # Same as dashboard - all users can see alerts
    '📊 Income Entry': ['view_income', 'add_income'],
    '🚌 Trip Entry': ['view_income', 'add_income'],  # Using income permissions for trips
    '🔧 Maintenance Entry': ['view_maintenance', 'add_maintenance'],
    '⛽ Fuel Entry': ['view_maintenance', 'add_maintenance'],  # Using maintenance permissions for fuel
    '📄 Documents': ['view_fleet', 'view_employees'],  # Document management permission
    '📦 Inventory': ['view_maintenance', 'add_maintenance'],  # Inventory permission
    '👥 Customers & Bookings': ['view_income', 'add_income'],  # Booking/customer permission
    '📥 Import from Excel': ['import_data'],
    '💰 Revenue History': ['view_revenue_history'],
    '🚌 Fleet Management': ['view_fleet'],
    '🛣️ Routes & Assignments': ['view_routes', 'view_assignments'],
    '👥 Employee Management': ['view_employees'],
    '📊 Employee Performance': ['view_performance'],
    '💰 Payroll & Payslips': ['view_payroll'],
    '📅 Leave Management': ['view_leave'],
    '⚠️ Disciplinary Records': ['view_disciplinary'],
    '🚌 Bus-by-Bus Analysis': ['view_bus_analysis'],
    '📈 Performance Metrics': ['view_performance_metrics'],
    '⛽ Fuel Analysis': ['view_bus_analysis', 'view_performance_metrics'],  # Analytics permission
    '🚌 Trip Analysis': ['view_bus_analysis', 'view_performance_metrics'],  # Analytics permission
    '💰 Route Profitability': ['view_bus_analysis', 'view_performance_metrics'],  # Analytics permission
    '🏆 Driver Scoring': ['view_performance', 'view_performance_metrics'],  # Performance permission
    '👤 My Profile': [],  # Everyone can access their own profile
    '📊 My Activity': [],  # Everyone can view their own activity
    '👥 User Management': ['view_users'],
    '📜 Activity Log': ['view_audit_logs'],
    '🔐 Role Management': ['manage_roles'],
}


def can_access_page(page_name: str) -> bool:
    """Check if current user can access a specific page"""
    required_permissions = PAGE_PERMISSIONS.get(page_name, [])
    
    if not required_permissions:
        return True
    
    return has_any_permission(required_permissions)


def get_accessible_menu_items(menu_items: list) -> list:
    """Filter menu items based on user permissions"""
    return [item for item in menu_items if can_access_page(item)]


# =============================================================================
# LOGIN / LOGOUT UI
# =============================================================================

def login_page():
    """Display login page"""
    st.title("🔐 Pavillion Coaches - Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Please login to continue")
        
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        remember_me = st.checkbox("Remember me for 7 days", value=True)
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("🔓 Login", width="stretch"):
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state['authenticated'] = True
                        st.session_state['user'] = user
                        # Clear cached permissions
                        if 'user_permissions' in st.session_state:
                            del st.session_state['user_permissions']
                        
                        if remember_me:
                            session_token = create_session(user['id'])
                            st.query_params['session'] = session_token
                            st.session_state['session_token'] = session_token
                        
                        st.success(f"Welcome back, {user['full_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.warning("Please enter both username and password")
        
        with col_b:
            if st.button("ℹ️ Help", width="stretch"):
                st.info("""
                **Default Admin Account:**
                - Username: `admin`
                - Password: `admin123`
                
                Please change the default password after first login.
                """)


def logout():
    """Logout current user and invalidate session"""
    session_token = st.session_state.get('session_token') or st.query_params.get('session')
    if session_token:
        invalidate_session(session_token)
    
    st.session_state['authenticated'] = False
    st.session_state['user'] = None
    st.session_state['session_token'] = None
    
    # Clear cached permissions
    if 'user_permissions' in st.session_state:
        del st.session_state['user_permissions']
    
    if 'session' in st.query_params:
        del st.query_params['session']
    
    st.rerun()


def require_auth(func):
    """Decorator to require authentication for a page"""
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authenticated', False):
            login_page()
            return
        return func(*args, **kwargs)
    return wrapper