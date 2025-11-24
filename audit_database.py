"""
database.py - Database initialization with audit trail support
"""

import sqlite3
from datetime import datetime

def init_database():
    """Initialize all database tables including audit trail"""
    conn = sqlite3.connect('bus_management.db')
    cursor = conn.cursor()
    
    # Existing tables (income, maintenance, employees, etc.)
    # ... your existing table creation code ...
    
    # NEW: Activity Log Table for Audit Trail
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
    
    # Create indexes for better query performance
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
    
    print("✅ Database initialized with audit trail support")


def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect('bus_management.db')
    conn.row_factory = sqlite3.Row
    return conn