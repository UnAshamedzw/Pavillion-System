"""
database_fix.py - Run this ONCE to fix the database schema

This script:
1. Removes the old drivers and conductors tables (if they exist)
2. Updates bus_assignments to reference employees table directly
3. Preserves all existing data

Run this before using the updated code!
"""

import sqlite3
from datetime import datetime

def fix_database_schema():
    """Fix database schema to use employees table for assignments"""
    
    conn = sqlite3.connect('bus_management.db')
    cursor = conn.cursor()
    
    print("🔧 Starting database schema update...")
    
    try:
        # Step 1: Check if bus_assignments table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='bus_assignments'
        """)
        
        if cursor.fetchone():
            print("✅ Found bus_assignments table")
            
            # Step 2: Create new bus_assignments table with correct structure
            print("📋 Creating new bus_assignments table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bus_assignments_new (
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
            """)
            print("✅ Created new bus_assignments_new table")
            
            # Step 3: Check what columns exist in old table
            cursor.execute("PRAGMA table_info(bus_assignments)")
            old_columns = [col[1] for col in cursor.fetchall()]
            print(f"📋 Found columns in old table: {', '.join(old_columns)}")
            
            # Step 4: Migrate existing data (if any) with flexible column handling
            # Build SELECT query based on available columns
            select_cols = []
            if 'id' in old_columns:
                select_cols.append('id')
            if 'bus_number' in old_columns:
                select_cols.append('bus_number')
            if 'assignment_date' in old_columns:
                select_cols.append('assignment_date')
            if 'shift' in old_columns:
                select_cols.append('shift')
            if 'route' in old_columns:
                select_cols.append('route')
            if 'notes' in old_columns:
                select_cols.append('notes')
            if 'created_by' in old_columns:
                select_cols.append('created_by')
            if 'created_at' in old_columns:
                select_cols.append('created_at')
            
            if select_cols:
                query = f"SELECT {', '.join(select_cols)} FROM bus_assignments"
                cursor.execute(query)
                old_assignments = cursor.fetchall()
                
                if old_assignments:
                    print(f"📦 Migrating {len(old_assignments)} existing assignments...")
                    for assignment in old_assignments:
                        # Build INSERT with matching columns
                        placeholders = ', '.join(['?' for _ in select_cols])
                        cursor.execute(f"""
                            INSERT INTO bus_assignments_new 
                            ({', '.join(select_cols)})
                            VALUES ({placeholders})
                        """, assignment)
                    print(f"✅ Migrated {len(old_assignments)} assignments")
                else:
                    print("ℹ️ No existing assignments to migrate")
            
            # Step 5: Try to migrate driver/conductor references if old tables exist
            print("\n🔄 Attempting to migrate driver/conductor references...")
            
            # Check if old driver/conductor tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('drivers', 'conductors')")
            old_tables_exist = cursor.fetchall()
            
            if old_tables_exist and 'driver_id' in old_columns and 'conductor_id' in old_columns:
                print("📋 Found old driver/conductor tables, attempting to link to employees...")
                
                # Try to match drivers by name to employees
                cursor.execute("""
                    UPDATE bus_assignments_new
                    SET driver_employee_id = (
                        SELECT e.employee_id 
                        FROM employees e
                        WHERE e.full_name = (
                            SELECT name FROM drivers WHERE id = 
                            (SELECT driver_id FROM bus_assignments WHERE bus_assignments.id = bus_assignments_new.id)
                        )
                        AND e.position LIKE '%Driver%'
                        LIMIT 1
                    )
                    WHERE driver_employee_id IS NULL
                """)
                
                # Try to match conductors by name to employees
                cursor.execute("""
                    UPDATE bus_assignments_new
                    SET conductor_employee_id = (
                        SELECT e.employee_id 
                        FROM employees e
                        WHERE e.full_name = (
                            SELECT name FROM conductors WHERE id = 
                            (SELECT conductor_id FROM bus_assignments WHERE bus_assignments.id = bus_assignments_new.id)
                        )
                        AND e.position LIKE '%Conductor%'
                        LIMIT 1
                    )
                    WHERE conductor_employee_id IS NULL
                """)
                
                print("✅ Attempted to link assignments to employees")
            else:
                print("ℹ️ No old driver/conductor tables to migrate from")
            
            # Step 6: Drop old table and rename new one
            cursor.execute("DROP TABLE bus_assignments")
            cursor.execute("ALTER TABLE bus_assignments_new RENAME TO bus_assignments")
            print("✅ Replaced old bus_assignments table")
        else:
            # Create table from scratch
            cursor.execute("""
                CREATE TABLE bus_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bus_number TEXT NOT NULL,
                    driver_employee_id TEXT,
                    conductor_employee_id TEXT,
                    assignment_date DATE NOT NULL,
                    shift TEXT,
                    route TEXT,
                    notes TEXT,
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (driver_employee_id) REFERENCES employees(employee_id),
                    FOREIGN KEY (conductor_employee_id) REFERENCES employees(employee_id)
                )
            """)
            print("✅ Created new bus_assignments table")
        
        # Step 7: Drop old drivers and conductors tables if they exist
        cursor.execute("DROP TABLE IF EXISTS drivers")
        cursor.execute("DROP TABLE IF EXISTS conductors")
        print("✅ Removed old drivers and conductors tables")
        
        # Commit changes
        conn.commit()
        print("\n✅ Database schema updated successfully!")
        print("\n📋 Summary:")
        print("   - bus_assignments now references employees table directly")
        print("   - Old drivers and conductors tables removed")
        print("   - All employee data should be managed through HR module")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error updating database: {e}")
        print("Please check the error and try again")
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE SCHEMA UPDATE")
    print("=" * 60)
    print("\nThis will update your database to fix assignment issues.")
    print("Your data will be preserved.\n")
    
    response = input("Continue? (yes/no): ").lower()
    
    if response == 'yes':
        fix_database_schema()
    else:
        print("Update cancelled.")