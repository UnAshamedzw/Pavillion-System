"""
migrate_database.py - Database Migration Script
Run this ONCE to add buses and routes tables to existing database
"""

import sqlite3
from datetime import datetime

DATABASE_PATH = "bus_management.db"

def migrate_database():
    """Add buses and routes tables, update income table"""
    
    print("🔄 Starting database migration...")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Create buses table
        print("📦 Creating buses table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number_plate TEXT UNIQUE NOT NULL,
                model TEXT NOT NULL,
                capacity INTEGER,
                year INTEGER,
                status TEXT DEFAULT 'Active',
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Buses table created")
        
        # 2. Create routes table
        print("📦 Creating routes table...")
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
        print("✅ Routes table created")
        
        # 3. Check if income table needs hire_destination column
        print("🔍 Checking income table structure...")
        cursor.execute("PRAGMA table_info(income)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'hire_destination' not in columns:
            print("📦 Adding hire_destination column to income table...")
            cursor.execute('ALTER TABLE income ADD COLUMN hire_destination TEXT')
            print("✅ hire_destination column added")
        else:
            print("✅ hire_destination column already exists")
        
        # 4. Extract unique buses from existing income records
        print("🚌 Extracting existing buses from income records...")
        cursor.execute("SELECT DISTINCT bus_number FROM income WHERE bus_number IS NOT NULL AND bus_number != ''")
        existing_buses = cursor.fetchall()
        
        if existing_buses:
            print(f"📋 Found {len(existing_buses)} unique buses in income records")
            
            for (bus_number,) in existing_buses:
                # Check if bus already exists
                cursor.execute("SELECT id FROM buses WHERE number_plate = ?", (bus_number,))
                if not cursor.fetchone():
                    # Add bus to buses table
                    cursor.execute('''
                        INSERT INTO buses (number_plate, model, capacity, status, notes, created_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (bus_number, 'Unknown Model', 50, 'Active', 'Migrated from income records', 'System'))
                    print(f"  ✅ Added bus: {bus_number}")
                else:
                    print(f"  ⏭️  Bus already exists: {bus_number}")
        else:
            print("ℹ️  No existing buses found in income records")
        
        # 5. Extract unique routes from existing income records
        print("🛣️  Extracting existing routes from income records...")
        cursor.execute("SELECT DISTINCT route FROM income WHERE route IS NOT NULL AND route != '' AND route != 'Hire'")
        existing_routes = cursor.fetchall()
        
        if existing_routes:
            print(f"📋 Found {len(existing_routes)} unique routes in income records")
            
            for (route_name,) in existing_routes:
                # Check if route already exists
                cursor.execute("SELECT id FROM routes WHERE name = ?", (route_name,))
                if not cursor.fetchone():
                    # Add route to routes table
                    cursor.execute('''
                        INSERT INTO routes (name, distance, description, created_by)
                        VALUES (?, ?, ?, ?)
                    ''', (route_name, None, 'Migrated from income records', 'System'))
                    print(f"  ✅ Added route: {route_name}")
                else:
                    print(f"  ⏭️  Route already exists: {route_name}")
        else:
            print("ℹ️  No existing routes found in income records")
        
        # 6. Commit all changes
        conn.commit()
        print("\n🎉 Migration completed successfully!")
        print("\n📊 Summary:")
        
        # Count buses
        cursor.execute("SELECT COUNT(*) FROM buses")
        bus_count = cursor.fetchone()[0]
        print(f"  🚌 Total buses: {bus_count}")
        
        # Count routes
        cursor.execute("SELECT COUNT(*) FROM routes")
        route_count = cursor.fetchone()[0]
        print(f"  🛣️  Total routes: {route_count}")
        
        # Count income records
        cursor.execute("SELECT COUNT(*) FROM income")
        income_count = cursor.fetchone()[0]
        print(f"  💰 Total income records: {income_count}")
        
        print("\n✅ Your database is now ready!")
        print("👉 You can now run: streamlit run app.py")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("="*60)
    print("🚌 BUS MANAGEMENT SYSTEM - DATABASE MIGRATION")
    print("="*60)
    print()
    
    response = input("⚠️  This will modify your database. Have you backed it up? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        print()
        migrate_database()
        print()
        print("="*60)
    else:
        print("\n❌ Migration cancelled. Please backup your database first:")
        print("   Backup command: cp bus_management.db bus_management_backup.db")
        print()
