"""
auth.py - User Authentication Module
Handles user login, registration, and session management
CORRECTED VERSION - Uses database abstraction for PostgreSQL/SQLite compatibility
WITH PERSISTENT SESSIONS - Sessions persist across page refreshes
"""

import streamlit as st
import hashlib
import secrets
from datetime import datetime, timedelta

# Import database abstraction layer
from database import get_connection, USE_POSTGRES

# Session duration in days
SESSION_DURATION_DAYS = 7


def hash_password(password: str, salt: str = None) -> tuple:
    """
    Hash password with salt using SHA-256
    Returns: (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Combine password and salt, then hash
    pwd_salt = f"{password}{salt}".encode('utf-8')
    hashed = hashlib.sha256(pwd_salt).hexdigest()
    
    return hashed, salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """Verify if password matches the hashed password"""
    test_hash, _ = hash_password(password, salt)
    return test_hash == hashed_password


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


def create_session(user_id: int) -> str:
    """Create a new session token for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Generate unique session token
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=SESSION_DURATION_DAYS)
    
    # Invalidate old sessions for this user (optional - allows only one active session)
    # Uncomment the following if you want single-session per user:
    # if USE_POSTGRES:
    #     cursor.execute('UPDATE user_sessions SET is_valid = 0 WHERE user_id = %s', (user_id,))
    # else:
    #     cursor.execute('UPDATE user_sessions SET is_valid = 0 WHERE user_id = ?', (user_id,))
    
    # Insert new session
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
    """
    Validate a session token and return user info if valid
    Returns: user dict or None
    """
    if not session_token:
        return None
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get session and user info
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
    
    # Handle both dict-like and tuple results
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
    
    # Check if session is still valid
    if not is_valid or not is_active:
        return None
    
    # Check expiration
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
    # Handle both dict-like (PostgreSQL) and tuple (SQLite) results
    count = result['count'] if hasattr(result, 'keys') else result[0]
    
    if count == 0:
        hashed_pwd, salt = hash_password('admin123')
        if USE_POSTGRES:
            cursor.execute('''
                INSERT INTO users (username, password_hash, salt, full_name, role, email)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', ('admin', hashed_pwd, salt, 'System Administrator', 'Admin', 'admin@busmanagement.com'))
        else:
            cursor.execute('''
                INSERT INTO users (username, password_hash, salt, full_name, role, email)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', hashed_pwd, salt, 'System Administrator', 'Admin', 'admin@busmanagement.com'))
    
    conn.commit()
    conn.close()


def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate user and return user details if successful
    Returns: dict with user info or None if authentication fails
    """
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
        # Handle both dict-like (PostgreSQL) and tuple (SQLite) results
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
        
        if is_active == 1:  # Check if user is active
            if verify_password(password, password_hash, salt):
                # Update last login
                if USE_POSTGRES:
                    cursor.execute('''
                        UPDATE users SET last_login = %s WHERE id = %s
                    ''', (datetime.now(), user_id))
                else:
                    cursor.execute('''
                        UPDATE users SET last_login = ? WHERE id = ?
                    ''', (datetime.now(), user_id))
                conn.commit()
                conn.close()
                
                # Generate unique session ID
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
    """
    Register a new user
    Returns: True if successful, False if username already exists
    """
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
    """
    Change user password
    Returns: True if successful, False if old password is incorrect
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Verify old password
    if USE_POSTGRES:
        cursor.execute('SELECT password_hash, salt FROM users WHERE id = %s', (user_id,))
    else:
        cursor.execute('SELECT password_hash, salt FROM users WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        # Handle both dict-like and tuple results
        if hasattr(result, 'keys'):
            password_hash = result['password_hash']
            salt = result['salt']
        else:
            password_hash, salt = result[0], result[1]
        
        if verify_password(old_password, password_hash, salt):
            # Update with new password
            new_hash, new_salt = hash_password(new_password)
            if USE_POSTGRES:
                cursor.execute('''
                    UPDATE users SET password_hash = %s, salt = %s WHERE id = %s
                ''', (new_hash, new_salt, user_id))
            else:
                cursor.execute('''
                    UPDATE users SET password_hash = ?, salt = ? WHERE id = ?
                ''', (new_hash, new_salt, user_id))
            conn.commit()
            conn.close()
            return True
    
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


def login_page():
    """Display login page"""
    st.title("🔐 Bus Management System Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Please login to continue")
        
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        # Remember me checkbox
        remember_me = st.checkbox("Remember me for 7 days", value=True)
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            if st.button("🔓 Login", width="stretch"):
                if username and password:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state['authenticated'] = True
                        st.session_state['user'] = user
                        
                        # Create persistent session if remember me is checked
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
    # Invalidate the session token in the database
    session_token = st.session_state.get('session_token') or st.query_params.get('session')
    if session_token:
        invalidate_session(session_token)
    
    # Clear session state
    st.session_state['authenticated'] = False
    st.session_state['user'] = None
    st.session_state['session_token'] = None
    
    # Clear query params
    if 'session' in st.query_params:
        del st.query_params['session']
    
    st.rerun()


def restore_session():
    """
    Try to restore session from query params on page load
    Call this at the start of your app before checking authentication
    Returns: True if session was restored, False otherwise
    """
    # Already authenticated in current session
    if st.session_state.get('authenticated', False):
        return True
    
    # Try to restore from query params
    session_token = st.query_params.get('session')
    if session_token:
        user = validate_session(session_token)
        if user:
            st.session_state['authenticated'] = True
            st.session_state['user'] = user
            st.session_state['session_token'] = session_token
            return True
        else:
            # Invalid or expired session - clear it
            del st.query_params['session']
    
    return False


def require_auth(func):
    """Decorator to require authentication for a page"""
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authenticated', False):
            login_page()
            return
        return func(*args, **kwargs)
    return wrapper


def check_permission(required_role: str) -> bool:
    """
    Check if current user has required role
    Roles hierarchy: Admin > Manager > User
    """
    if not st.session_state.get('authenticated', False):
        return False
    
    user_role = st.session_state['user']['role']
    
    role_hierarchy = {'Admin': 3, 'Manager': 2, 'User': 1}
    
    return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)