"""
create_fleet_tables.py - Create Missing Fleet Management Tables
This creates the drivers, conductors, and bus_assignments tables
"""

import sqlite3
from datetime import datetime

DATABASE_PATH = "bus_management.db"

def create_fleet_tables():
    """Create drivers, conductors, and bus_assignments tables"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("🔧 Creating Fleet Management Tables...")
    print("="*60)
    
    try:
        # Create drivers table
        print("\n📋 Creating drivers table...")
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
        print("✅ Drivers table created")
        
        # Create conductors table
        print("\n📋 Creating conductors table...")
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
        print("✅ Conductors table created")
        
        # Create bus_assignments table
        print("\n📋 Creating bus_assignments table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bus_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bus_number TEXT NOT NULL,
                driver_id INTEGER,
                conductor_id INTEGER,
                assignment_date DATE NOT NULL,
                shift TEXT,
                route TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (driver_id) REFERENCES drivers(id),
                FOREIGN KEY (conductor_id) REFERENCES conductors(id)
            )
        """)
        print("✅ Bus assignments table created")
        
        conn.commit()
        
        # Now migrate existing employees to drivers/conductors
        print("\n🔄 Migrating existing employees...")
        migrate_employees(cursor, conn)
        
        print("\n" + "="*60)
        print("✅ SUCCESS! All fleet tables created.")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def migrate_employees(cursor, conn):
    """Migrate existing employees to drivers and conductors tables"""
    
    try:
        # Check if employees table exists and has data
        cursor.execute("SELECT COUNT(*) FROM employees")
        emp_count = cursor.fetchone()[0]
        
        if emp_count == 0:
            print("   ℹ️  No employees to migrate")
            return
        
        # Migrate drivers
        cursor.execute("""
            SELECT employee_id, full_name, phone, email, hire_date, salary, address
            FROM employees
            WHERE position LIKE '%Driver%' AND status = 'Active'
        """)
        drivers = cursor.fetchall()
        
        driver_count = 0
        for driver in drivers:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO drivers (employee_id, name, phone, email, hire_date, salary, address, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')
                """, driver)
                if cursor.rowcount > 0:
                    driver_count += 1
            except Exception as e:
                print(f"   ⚠️  Error migrating driver {driver[1]}: {e}")
        
        if driver_count > 0:
            print(f"   ✅ Migrated {driver_count} drivers from employees table")
        
        # Migrate conductors
        cursor.execute("""
            SELECT employee_id, full_name, phone, email, hire_date, salary, address
            FROM employees
            WHERE position LIKE '%Conductor%' AND status = 'Active'
        """)
        conductors = cursor.fetchall()
        
        conductor_count = 0
        for conductor in conductors:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO conductors (employee_id, name, phone, email, hire_date, salary, address, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')
                """, conductor)
                if cursor.rowcount > 0:
                    conductor_count += 1
            except Exception as e:
                print(f"   ⚠️  Error migrating conductor {conductor[1]}: {e}")
        
        if conductor_count > 0:
            print(f"   ✅ Migrated {conductor_count} conductors from employees table")
        
        conn.commit()
        
        if driver_count == 0 and conductor_count == 0:
            print("   ℹ️  No drivers or conductors found in employees table")
            print("   💡 You can add them manually in Fleet Management")
        
    except Exception as e:
        print(f"   ⚠️  Migration note: {e}")

def verify_tables():
    """Verify that all tables were created successfully"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("📊 VERIFICATION REPORT")
    print("="*60)
    
    tables_to_check = ['drivers', 'conductors', 'bus_assignments']
    
    for table in tables_to_check:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ {table.upper()}: {count} records")
        except Exception as e:
            print(f"❌ {table.upper()}: Error - {e}")
    
    conn.close()
    
    print("="*60)
    print("✅ All tables are ready!")
    print("\n💡 You can now:")
    print("   1. Go to Fleet Management")
    print("   2. View/Add Drivers and Conductors")
    print("   3. Create Bus Assignments")
    print("="*60)

def main():
    """Main function"""
    print("\n" + "="*60)
    print("🚌 FLEET MANAGEMENT - CREATE MISSING TABLES")
    print("="*60)
    print("\nThis will create:")
    print("  • drivers table")
    print("  • conductors table")
    print("  • bus_assignments table")
    print("\nIt will also migrate existing drivers/conductors from employees.")
    
    response = input("\nPress ENTER to continue or CTRL+C to cancel...")
    
    create_fleet_tables()
    verify_tables()
    
    print("\n✅ Setup complete! Restart your Streamlit app.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled.")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
