"""
auth.py - User Authentication Module with Role-Based Permissions
Pavillion Coaches Bus Management System
Handles user login, registration, session management, and permissions
"""

import streamlit as st
import hashlib
import secrets
import re
from datetime import datetime, timedelta

# Import database abstraction layer
from database import get_connection, USE_POSTGRES

# Session duration in days
SESSION_DURATION_DAYS = 7

# Password complexity requirements
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True
PASSWORD_SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

def validate_password_complexity(password: str) -> tuple:
    """
    Validate password meets complexity requirements.
    Returns: (is_valid, list_of_errors)
    """
    errors = []
    
    # Check length
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")
    
    if len(password) > PASSWORD_MAX_LENGTH:
        errors.append(f"Password must be no more than {PASSWORD_MAX_LENGTH} characters")
    
    # Check for uppercase
    if PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter (A-Z)")
    
    # Check for lowercase
    if PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter (a-z)")
    
    # Check for digit
    if PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        errors.append("Password must contain at least one number (0-9)")
    
    # Check for special character
    if PASSWORD_REQUIRE_SPECIAL:
        special_pattern = f'[{re.escape(PASSWORD_SPECIAL_CHARS)}]'
        if not re.search(special_pattern, password):
            errors.append(f"Password must contain at least one special character ({PASSWORD_SPECIAL_CHARS[:10]}...)")
    
    # Check for common weak passwords
    weak_passwords = [
        'password', 'password1', 'password123', '12345678', '123456789',
        'qwerty123', 'admin123', 'letmein', 'welcome1', 'monkey123',
        'abc12345', 'pass1234', 'master123', 'hello123', 'shadow123'
    ]
    if password.lower() in weak_passwords:
        errors.append("Password is too common. Please choose a stronger password")
    
    # Check for sequential characters
    if re.search(r'(012|123|234|345|456|567|678|789|890)', password):
        errors.append("Password should not contain sequential numbers")
    
    if re.search(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):
        errors.append("Password should not contain sequential letters")
    
    return len(errors) == 0, errors


def get_password_strength(password: str) -> tuple:
    """
    Calculate password strength score.
    Returns: (score 0-100, strength_label, color)
    """
    if not password:
        return 0, "None", "gray"
    
    score = 0
    
    # Length scoring (up to 30 points)
    length = len(password)
    if length >= 8:
        score += 10
    if length >= 12:
        score += 10
    if length >= 16:
        score += 10
    
    # Character variety (up to 40 points)
    if re.search(r'[a-z]', password):
        score += 10
    if re.search(r'[A-Z]', password):
        score += 10
    if re.search(r'\d', password):
        score += 10
    if re.search(r'[^a-zA-Z0-9]', password):
        score += 10
    
    # Complexity bonus (up to 30 points)
    unique_chars = len(set(password))
    if unique_chars >= 6:
        score += 10
    if unique_chars >= 10:
        score += 10
    if unique_chars >= 14:
        score += 10
    
    # Determine label and color
    if score < 30:
        return score, "Weak", "red"
    elif score < 50:
        return score, "Fair", "orange"
    elif score < 70:
        return score, "Good", "yellow"
    elif score < 90:
        return score, "Strong", "lightgreen"
    else:
        return score, "Very Strong", "green"


def get_password_requirements_text() -> str:
    """Get formatted password requirements text"""
    requirements = [
        f"• At least {PASSWORD_MIN_LENGTH} characters long"
    ]
    
    if PASSWORD_REQUIRE_UPPERCASE:
        requirements.append("• At least one uppercase letter (A-Z)")
    if PASSWORD_REQUIRE_LOWERCASE:
        requirements.append("• At least one lowercase letter (a-z)")
    if PASSWORD_REQUIRE_DIGIT:
        requirements.append("• At least one number (0-9)")
    if PASSWORD_REQUIRE_SPECIAL:
        requirements.append(f"• At least one special character ({PASSWORD_SPECIAL_CHARS[:10]}...)")
    
    return "\n".join(requirements)


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

# All available permissions in the system
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
    
    # ----- FUEL MANAGEMENT -----
    'view_fuel': 'View fuel records',
    'add_fuel': 'Add fuel entries',
    'edit_fuel': 'Edit fuel entries',
    'delete_fuel': 'Delete fuel entries',
    
    # ----- TRIP MANAGEMENT -----
    'view_trips': 'View trip records',
    'add_trip': 'Add trip entries',
    'edit_trip': 'Edit trip entries',
    'delete_trip': 'Delete trip entries',
    
    # ----- INVENTORY -----
    'view_inventory': 'View inventory/parts',
    'add_inventory': 'Add inventory items',
    'edit_inventory': 'Edit inventory items',
    'delete_inventory': 'Delete inventory items',
    'manage_stock': 'Manage stock levels (add/remove)',
    
    # ----- CUSTOMERS & BOOKINGS -----
    'view_customers': 'View customers and bookings',
    'add_customer': 'Add customers',
    'edit_customer': 'Edit customer information',
    'delete_customer': 'Delete customers',
    'manage_bookings': 'Manage customer bookings',
    
    # ----- DOCUMENTS -----
    'view_documents': 'View document management',
    'add_documents': 'Upload documents',
    'delete_documents': 'Delete documents',
    
    # ----- EXPENSES -----
    'view_expenses': 'View general expenses',
    'add_expense': 'Add expense entries',
    'edit_expense': 'Edit expense entries',
    'delete_expense': 'Delete expense entries',
    'approve_expense': 'Approve expenses for payment',
    
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
    
    # ----- CONTRACTS -----
    'view_contracts': 'View employment contracts',
    'generate_contracts': 'Generate employee contracts',
    'edit_contract_templates': 'Edit contract templates',
    
    # ----- PAYROLL -----
    'view_payroll': 'View payroll information',
    'manage_payroll': 'Manage payroll (add, edit, process)',
    'approve_payroll': 'Approve payroll for payment',
    'export_payroll': 'Export payroll reports',
    'view_payslips': 'View payslips',
    'generate_payslips': 'Generate payslips',
    
    # ----- LOANS & DEDUCTIONS -----
    'view_loans': 'View employee loans',
    'manage_loans': 'Manage employee loans (approve, edit)',
    'view_deductions': 'View employee deductions',
    'add_deduction': 'Add employee deductions/penalties',
    'edit_deduction': 'Edit deductions',
    
    # ----- RED TICKETS -----
    'view_red_tickets': 'View red tickets',
    'add_red_ticket': 'Issue red tickets',
    'edit_red_ticket': 'Edit red tickets',
    'delete_red_ticket': 'Delete red tickets',
    
    # ----- DAILY RECONCILIATION -----
    'view_reconciliation': 'View daily reconciliation',
    'add_reconciliation': 'Add daily reconciliation entries',
    'edit_reconciliation': 'Edit reconciliation entries',
    
    # ----- EMPLOYEE SELF-SERVICE -----
    'view_own_payslips': 'View own payslips',
    'view_own_loans': 'View own loans',
    'request_leave': 'Request leave',
    'request_loan': 'Request loan',
    'submit_complaint': 'Submit complaints',
    
    # ----- ANALYTICS / REPORTS -----
    'view_dashboard': 'View main dashboard',
    'view_bus_analysis': 'View bus-by-bus analysis',
    'view_performance_metrics': 'View performance metrics/KPIs',
    'view_revenue_history': 'View revenue history',
    'view_profit_loss': 'View profit & loss reports',
    'view_route_profitability': 'View route profitability analysis',
    'view_driver_scoring': 'View driver scoring/performance',
    'view_alerts': 'View alerts dashboard',
    'generate_reports': 'Generate PDF/Excel reports',
    
    # ----- DATA IMPORT/EXPORT -----
    'import_data': 'Import data from Excel/CSV',
    'export_data': 'Export data and backups',
    'manage_backup': 'Manage system backups',
    
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
    'manage_notifications': 'Manage notification settings',
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
    'Fuel Management': [
        'view_fuel', 'add_fuel', 'edit_fuel', 'delete_fuel'
    ],
    'Trip Management': [
        'view_trips', 'add_trip', 'edit_trip', 'delete_trip'
    ],
    'Inventory / Parts': [
        'view_inventory', 'add_inventory', 'edit_inventory', 'delete_inventory', 'manage_stock'
    ],
    'Customers & Bookings': [
        'view_customers', 'add_customer', 'edit_customer', 'delete_customer', 'manage_bookings'
    ],
    'Documents': [
        'view_documents', 'add_documents', 'delete_documents'
    ],
    'General Expenses': [
        'view_expenses', 'add_expense', 'edit_expense', 'delete_expense', 'approve_expense'
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
    'HR - Contracts': [
        'view_contracts', 'generate_contracts', 'edit_contract_templates'
    ],
    'Payroll': [
        'view_payroll', 'manage_payroll', 'approve_payroll', 'export_payroll'
    ],
    'Analytics & Reports': [
        'view_dashboard', 'view_bus_analysis', 'view_performance_metrics', 
        'view_revenue_history', 'view_profit_loss', 'view_route_profitability',
        'view_driver_scoring', 'view_alerts', 'generate_reports'
    ],
    'Data Import/Export': [
        'import_data', 'export_data', 'manage_backup'
    ],
    'User Management': [
        'view_users', 'add_user', 'edit_user', 'delete_user', 'manage_roles', 'reset_passwords'
    ],
    'System & Security': [
        'view_audit_logs', 'view_all_activity', 'manage_system_settings', 'manage_notifications'
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
            # Fuel
            'view_fuel', 'add_fuel', 'edit_fuel', 'delete_fuel',
            # Trips
            'view_trips', 'add_trip', 'edit_trip', 'delete_trip',
            # Inventory
            'view_inventory', 'add_inventory', 'edit_inventory', 'delete_inventory', 'manage_stock',
            # Customers
            'view_customers', 'add_customer', 'edit_customer', 'delete_customer', 'manage_bookings',
            # Documents
            'view_documents', 'add_documents', 'delete_documents',
            # Expenses
            'view_expenses', 'add_expense', 'edit_expense', 'delete_expense', 'approve_expense',
            # HR
            'view_employees', 'add_employee', 'edit_employee', 'delete_employee', 'manage_employee_documents',
            'view_performance', 'add_performance', 'edit_performance',
            'view_leave', 'approve_leave', 'manage_leave',
            'view_disciplinary', 'add_disciplinary', 'edit_disciplinary',
            'view_contracts', 'generate_contracts', 'edit_contract_templates',
            # Payroll - Full control including approval
            'view_payroll', 'manage_payroll', 'approve_payroll', 'export_payroll',
            'view_payslips', 'generate_payslips',
            'view_loans', 'manage_loans', 'view_deductions', 'add_deduction', 'edit_deduction',
            'view_red_tickets', 'add_red_ticket', 'edit_red_ticket', 'delete_red_ticket',
            'view_reconciliation', 'add_reconciliation', 'edit_reconciliation',
            # Analytics
            'view_dashboard', 'view_bus_analysis', 'view_performance_metrics', 
            'view_revenue_history', 'view_profit_loss', 'view_route_profitability',
            'view_driver_scoring', 'view_alerts', 'generate_reports',
            # Data
            'import_data', 'export_data', 'manage_backup',
        ],
        'is_system_role': True,
        'can_be_modified': False
    },
    
    'Administration Manager': {
        'description': 'Full administrative control - monitors entire admin operations',
        'permissions': list(ALL_PERMISSIONS.keys()),  # All permissions like System Admin
        'is_system_role': True,
        'can_be_modified': False
    },
    
    'HR Manager': {
        'description': 'Full HR functionality including payroll processing',
        'permissions': [
            'view_employees', 'add_employee', 'edit_employee', 'delete_employee', 'manage_employee_documents',
            'view_performance', 'add_performance', 'edit_performance',
            'view_leave', 'approve_leave', 'manage_leave',
            'view_disciplinary', 'add_disciplinary', 'edit_disciplinary',
            'view_contracts', 'generate_contracts', 'edit_contract_templates',
            # Payroll - Process but not final approve
            'view_payroll', 'manage_payroll', 'export_payroll',
            'view_payslips', 'generate_payslips',
            'view_loans', 'manage_loans', 'view_deductions', 'add_deduction', 'edit_deduction',
            'view_red_tickets', 'add_red_ticket', 'edit_red_ticket',
            'view_reconciliation', 'add_reconciliation', 'edit_reconciliation',
            # View operations
            'view_fleet', 'view_routes', 'view_assignments',
            'view_income', 'view_fuel', 'view_trips',
            'view_dashboard', 'view_performance_metrics', 'view_driver_scoring', 'generate_reports',
            'export_data',
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
            'view_fuel', 'add_fuel', 'edit_fuel', 'delete_fuel',
            'view_trips', 'add_trip', 'edit_trip', 'delete_trip',
            'view_inventory', 'add_inventory', 'edit_inventory', 'manage_stock',
            'view_customers', 'add_customer', 'edit_customer', 'manage_bookings',
            'view_documents', 'add_documents',
            'view_expenses', 'add_expense', 'edit_expense',
            'view_employees', 'view_performance',
            # Reconciliation & Red Tickets
            'view_reconciliation', 'add_reconciliation', 'edit_reconciliation',
            'view_red_tickets', 'add_red_ticket', 'edit_red_ticket',
            'view_deductions', 'add_deduction',
            'view_dashboard', 'view_bus_analysis', 'view_performance_metrics', 
            'view_revenue_history', 'view_profit_loss', 'view_route_profitability',
            'view_driver_scoring', 'view_alerts', 'generate_reports',
            'import_data', 'export_data',
        ],
        'is_system_role': False,
        'can_be_modified': True
    },
    
    'Finance Manager': {
        'description': 'Financial oversight and reporting',
        'permissions': [
            'view_income', 'export_income',
            'view_maintenance', 'export_maintenance',
            'view_fuel', 'view_trips',
            'view_expenses', 'add_expense', 'edit_expense', 'approve_expense',
            'view_inventory',
            'view_customers',
            'view_payroll', 'manage_payroll', 'approve_payroll', 'export_payroll',
            'view_fleet', 'view_routes',
            'view_employees',
            'view_dashboard', 'view_bus_analysis', 'view_performance_metrics', 
            'view_revenue_history', 'view_profit_loss', 'view_route_profitability',
            'view_alerts', 'generate_reports',
            'export_data',
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
            'view_fuel', 'add_fuel',
            'view_trips', 'add_trip', 'edit_trip',
            'view_employees',
            'view_dashboard', 'view_route_profitability', 'view_driver_scoring',
        ],
        'is_system_role': False,
        'can_be_modified': True
    },
    
    'Workshop Supervisor': {
        'description': 'Maintenance and workshop management',
        'permissions': [
            'view_fleet', 'edit_bus', 'manage_bus_documents',
            'view_maintenance', 'add_maintenance', 'edit_maintenance', 'delete_maintenance', 'export_maintenance',
            'view_inventory', 'add_inventory', 'edit_inventory', 'manage_stock',
            'view_documents', 'add_documents',
            'view_dashboard', 'view_bus_analysis', 'view_alerts',
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
    
    'Stores Supervisor': {
        'description': 'Inventory and stores management',
        'permissions': [
            'view_inventory', 'add_inventory', 'edit_inventory', 'delete_inventory', 'manage_stock',
            'view_documents', 'add_documents',
            'view_maintenance',
            'view_fleet',
            'view_dashboard', 'view_alerts',
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


def register_user(username: str, password: str, full_name: str, role: str, email: str = None) -> tuple:
    """
    Register a new user with password validation.
    Returns: (success: bool, error_message: str or None)
    """
    # Validate password complexity
    is_valid, errors = validate_password_complexity(password)
    if not is_valid:
        return False, errors[0]  # Return first error
    
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
        return True, None
    except Exception as e:
        conn.close()
        if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
            return False, "Username already exists"
        return False, f"Registration failed: {str(e)}"


def change_password(user_id: int, old_password: str, new_password: str) -> tuple:
    """
    Change user password with validation.
    Returns: (success: bool, error_message: str or None)
    """
    # Validate new password complexity
    is_valid, errors = validate_password_complexity(new_password)
    if not is_valid:
        return False, errors[0]
    
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
            # Check new password is different from old
            if old_password == new_password:
                conn.close()
                return False, "New password must be different from current password"
            
            new_hash, new_salt = hash_password(new_password)
            if USE_POSTGRES:
                cursor.execute('UPDATE users SET password_hash = %s, salt = %s WHERE id = %s', (new_hash, new_salt, user_id))
            else:
                cursor.execute('UPDATE users SET password_hash = ?, salt = ? WHERE id = ?', (new_hash, new_salt, user_id))
            conn.commit()
            conn.close()
            return True, None
        else:
            conn.close()
            return False, "Current password is incorrect"
    
    conn.close()
    return False, "User not found"


def reset_user_password(user_id: int, new_password: str) -> tuple:
    """
    Admin function to reset a user's password with validation.
    Returns: (success: bool, error_message: str or None)
    """
    # Validate new password complexity
    is_valid, errors = validate_password_complexity(new_password)
    if not is_valid:
        return False, errors[0]
    
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
        return True, None
    except Exception as e:
        conn.close()
        return False, f"Password reset failed: {str(e)}"


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

def get_user_role() -> str:
    """Get the current user's role from session state"""
    user = st.session_state.get('user', {})
    return user.get('role', 'Viewer')


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
    '🏠 Home': [],  # Everyone can access their landing page
    '📈 Operations Dashboard': ['view_dashboard'],  # Full dashboard - restricted
    '🔔 Alerts': ['view_dashboard'],  # Alerts for authorized users
    '🚌 Trip & Income Entry': ['view_income', 'add_income'],  # Combined entry
    '📋 Daily Reconciliation': ['view_reconciliation', 'add_reconciliation'],  # Cash reconciliation & red tickets
    '🔧 Maintenance Entry': ['view_maintenance', 'add_maintenance'],
    '⛽ Fuel Entry': ['view_fuel', 'add_fuel'],
    '💸 General Expenses': ['view_expenses', 'add_expense'],
    '📄 Documents': ['view_documents'],
    '📦 Inventory': ['view_inventory'],
    '👥 Customers & Bookings': ['view_customers'],
    '📥 Import from Excel': ['import_data'],
    '💰 Revenue History': ['view_revenue_history'],
    '🚌 Fleet Management': ['view_fleet'],
    '🛣️ Routes & Assignments': ['view_routes', 'view_assignments'],
    '✅ Approvals Center': ['approve_payroll', 'approve_leave', 'view_employees'],  # Approvals - HR/Admin
    '👥 Employee Management': ['view_employees'],
    '📝 Contract Generator': ['view_contracts', 'generate_contracts'],
    '📊 Employee Performance': ['view_performance'],
    '💰 Payroll & Payslips': ['view_payroll'],
    '📅 Leave Management': ['view_leave'],
    '⚠️ Disciplinary Records': ['view_disciplinary'],
    '🚌 Bus-by-Bus Analysis': ['view_bus_analysis'],
    '📈 Performance Metrics': ['view_performance_metrics'],
    '⛽ Fuel Analysis': ['view_fuel', 'view_bus_analysis'],
    '🚌 Trip Analysis': ['view_trips', 'view_bus_analysis'],
    '💰 Route Profitability': ['view_route_profitability'],
    '🏆 Driver Scoring': ['view_driver_scoring'],
    '📊 Profit & Loss': ['view_profit_loss'],
    '🚨 Alerts Dashboard': ['view_alerts'],
    '👤 My Profile': [],  # Everyone can access their own profile
    '📊 My Activity': [],  # Everyone can view their own activity
    '👥 User Management': ['view_users'],
    '📜 Activity Log': ['view_audit_logs'],
    '🔐 Role Management': ['manage_roles'],
    '💾 Backup & Export': ['export_data', 'manage_backup'],
    '🔔 Notification Settings': ['manage_notifications'],
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
            if st.button("🔓 Login", use_container_width=True):
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
            if st.button("ℹ️ Help", use_container_width=True):
                st.info("""
                **Default Admin Account:**
                - Username: `admin`
                - Password: `admin123`
                
                Please change the default password after first login.
                """)
        
        # Employee Portal Link
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; padding: 15px; background: #f0f8ff; border-radius: 8px; margin-top: 10px;">
            <p style="margin: 0; color: #666;">Are you an employee?</p>
            <p style="margin: 5px 0 0 0; font-size: 14px;">
                Access the <strong>Employee Self-Service Portal</strong> to view payslips, trips, and submit requests.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("👤 Employee Portal Login", use_container_width=True, type="secondary"):
            st.session_state['show_employee_portal'] = True
            st.rerun()

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