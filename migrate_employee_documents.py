"""
Database Migration Script - Add Document Tracking to Employees Table
Run this script ONCE to add the new columns to your existing database
"""

import sqlite3
from datetime import datetime

def migrate_database():
    """Add document tracking columns to employees table"""
    
    conn = sqlite3.connect('bus_management.db')
    cursor = conn.cursor()
    
    print("Starting database migration...")
    print("=" * 60)
    
    # List of columns to add
    columns_to_add = [
        ("date_of_birth", "DATE"),
        ("emergency_contact", "TEXT"),
        ("emergency_phone", "TEXT"),
        ("license_number", "TEXT"),
        ("license_expiry", "DATE"),
        ("defensive_driving_expiry", "DATE"),
        ("medical_cert_expiry", "DATE"),
        ("retest_date", "DATE")
    ]
    
    # Check which columns already exist
    cursor.execute("PRAGMA table_info(employees)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    # Add missing columns
    columns_added = 0
    for column_name, column_type in columns_to_add:
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE employees ADD COLUMN {column_name} {column_type}")
                print(f"✅ Added column: {column_name} ({column_type})")
                columns_added += 1
            except sqlite3.OperationalError as e:
                print(f"⚠️ Error adding {column_name}: {e}")
        else:
            print(f"⏭️ Column already exists: {column_name}")
    
    conn.commit()
    
    print("=" * 60)
    print(f"Migration completed! {columns_added} new columns added.")
    print("\n📋 Summary:")
    print(f"- Date of Birth field for age tracking")
    print(f"- Emergency contact information")
    print(f"- Driver license tracking (number and expiry)")
    print(f"- Defensive driving certificate expiry")
    print(f"- Medical certificate expiry")
    print(f"- Retest date tracking")
    print("\n🚨 Document expiry alerts will now appear 30 days before expiration!")
    
    conn.close()

if __name__ == "__main__":
    print("\n🔧 Bus Management System - Database Migration")
    print("=" * 60)
    print("This will add document tracking columns to your employees table.")
    print("=" * 60)
    
    response = input("\nProceed with migration? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        migrate_database()
        print("\n✅ Database migration successful!")
        print("You can now use the enhanced employee management features.")
    else:
        print("\n❌ Migration cancelled.")
