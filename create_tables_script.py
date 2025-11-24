"""
create_missing_tables.py - Create Missing Database Tables
Run this script to create buses, drivers, and conductors tables
"""

import sqlite3
import pandas as pd
from datetime import datetime

def create_buses_table(conn):
    """Create buses table with fleet information and document tracking"""
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT UNIQUE NOT NULL,
            registration_number TEXT,
            make TEXT,
            model TEXT,
            year INTEGER,
            capacity INTEGER,
            status TEXT DEFAULT 'Active',
            purchase_date DATE,
            purchase_cost REAL,
            zinara_licence_expiry DATE,
            vehicle_insurance_expiry DATE,
            passenger_insurance_expiry DATE,
            fitness_expiry DATE,
            route_permit_expiry DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("✅ Buses table created successfully with document tracking")
    conn.commit()


def create_drivers_table(conn):
    """Create drivers table with employee information"""
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE,
            name TEXT NOT NULL,
            license_number TEXT,
            license_expiry DATE,
            phone TEXT,
            email TEXT,
            address TEXT,
            date_of_birth DATE,
            hire_date DATE,
            status TEXT DEFAULT 'Active',
            salary REAL,
            commission_rate REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("✅ Drivers table created successfully")
    conn.commit()


def create_conductors_table(conn):
    """Create conductors table with employee information"""
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conductors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            date_of_birth DATE,
            hire_date DATE,
            status TEXT DEFAULT 'Active',
            salary REAL,
            commission_rate REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("✅ Conductors table created successfully")
    conn.commit()


def populate_buses_from_income(conn):
    """Extract unique buses from income table and populate buses table"""
    try:
        # Get unique bus numbers from income table
        income_df = pd.read_sql_query("SELECT DISTINCT bus_number FROM income ORDER BY bus_number", conn)
        
        if income_df.empty:
            print("⚠️ No buses found in income table")
            return
        
        cursor = conn.cursor()
        count = 0
        
        for bus_number in income_df['bus_number']:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO buses (bus_number, status)
                    VALUES (?, 'Active')
                """, (bus_number,))
                if cursor.rowcount > 0:
                    count += 1
            except Exception as e:
                print(f"Error inserting bus {bus_number}: {e}")
        
        conn.commit()
        print(f"✅ Populated {count} buses from income records")
        
    except Exception as e:
        print(f"⚠️ Could not populate buses: {e}")


def populate_drivers_from_income(conn):
    """Extract unique drivers from income table and populate drivers table"""
    try:
        # Get unique driver names from income table
        income_df = pd.read_sql_query(
            "SELECT DISTINCT driver_name FROM income WHERE driver_name IS NOT NULL ORDER BY driver_name", 
            conn
        )
        
        if income_df.empty:
            print("⚠️ No drivers found in income table")
            return
        
        cursor = conn.cursor()
        count = 0
        
        for idx, driver_name in enumerate(income_df['driver_name'], start=1):
            try:
                employee_id = f"DRV{idx:04d}"
                cursor.execute("""
                    INSERT OR IGNORE INTO drivers (employee_id, name, status, hire_date)
                    VALUES (?, ?, 'Active', ?)
                """, (employee_id, driver_name, datetime.now().date()))
                if cursor.rowcount > 0:
                    count += 1
            except Exception as e:
                print(f"Error inserting driver {driver_name}: {e}")
        
        conn.commit()
        print(f"✅ Populated {count} drivers from income records")
        
    except Exception as e:
        print(f"⚠️ Could not populate drivers: {e}")


def populate_conductors_from_income(conn):
    """Extract unique conductors from income table and populate conductors table"""
    try:
        # Get unique conductor names from income table
        income_df = pd.read_sql_query(
            "SELECT DISTINCT conductor_name FROM income WHERE conductor_name IS NOT NULL ORDER BY conductor_name", 
            conn
        )
        
        if income_df.empty:
            print("⚠️ No conductors found in income table")
            return
        
        cursor = conn.cursor()
        count = 0
        
        for idx, conductor_name in enumerate(income_df['conductor_name'], start=1):
            try:
                employee_id = f"CND{idx:04d}"
                cursor.execute("""
                    INSERT OR IGNORE INTO conductors (employee_id, name, status, hire_date)
                    VALUES (?, ?, 'Active', ?)
                """, (employee_id, conductor_name, datetime.now().date()))
                if cursor.rowcount > 0:
                    count += 1
            except Exception as e:
                print(f"Error inserting conductor {conductor_name}: {e}")
        
        conn.commit()
        print(f"✅ Populated {count} conductors from income records")
        
    except Exception as e:
        print(f"⚠️ Could not populate conductors: {e}")


def verify_tables(conn):
    """Verify that tables were created and show row counts"""
    cursor = conn.cursor()
    
    print("\n" + "="*50)
    print("DATABASE TABLE VERIFICATION")
    print("="*50)
    
    tables = ['buses', 'drivers', 'conductors']
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ {table.upper()}: {count} records")
        except Exception as e:
            print(f"❌ {table.upper()}: Error - {e}")
    
    print("="*50)


def main():
    """Main function to create all missing tables"""
    print("="*50)
    print("CREATING MISSING DATABASE TABLES")
    print("="*50)
    print()
    
    # Connect to database
    conn = sqlite3.connect('bus_management.db')
    
    try:
        # Create tables
        print("Step 1: Creating tables...")
        create_buses_table(conn)
        create_drivers_table(conn)
        create_conductors_table(conn)
        
        print("\nStep 2: Populating tables from existing data...")
        populate_buses_from_income(conn)
        populate_drivers_from_income(conn)
        populate_conductors_from_income(conn)
        
        # Verify
        verify_tables(conn)
        
        print("\n✅ All tables created successfully!")
        print("\n💡 You can now use the Performance Metrics page!")
        print("\n📝 Note: You can edit these records later through the application")
        print("   to add more details like license numbers, phone numbers, etc.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
