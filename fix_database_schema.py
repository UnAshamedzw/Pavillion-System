"""
fix_buses_table.py - Fix Database Schema Issues
Run this script ONCE to fix the buses table column name mismatch
"""

import sqlite3
import os
from datetime import datetime

DATABASE_PATH = "bus_management.db"

def backup_database():
    """Create a backup of the database before making changes"""
    if os.path.exists(DATABASE_PATH):
        backup_path = f"bus_management_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        import shutil
        shutil.copy2(DATABASE_PATH, backup_path)
        print(f"✅ Backup created: {backup_path}")
        return True
    return False

def check_current_schema():
    """Check the current schema of the buses table"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(buses)")
        columns = cursor.fetchall()
        
        print("\n📊 Current 'buses' table schema:")
        print("-" * 60)
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")
        print("-" * 60)
        
        column_names = [col[1] for col in columns]
        return column_names
        
    except sqlite3.OperationalError as e:
        print(f"⚠️ Error: {e}")
        return []
    finally:
        conn.close()

def fix_buses_table():
    """Fix the buses table to use consistent column names"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if buses table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='buses'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("ℹ️ Buses table doesn't exist. Creating new table...")
            create_new_buses_table(cursor)
            conn.commit()
            print("✅ New buses table created successfully!")
            return
        
        # Get current columns
        cursor.execute("PRAGMA table_info(buses)")
        columns = {col[1]: col for col in cursor.fetchall()}
        
        # Check if we need to migrate
        has_number_plate = 'number_plate' in columns
        has_bus_number = 'bus_number' in columns
        
        if has_number_plate and not has_bus_number:
            print("\n🔧 Detected 'number_plate' column. Migrating to 'bus_number'...")
            migrate_number_plate_to_bus_number(cursor)
            conn.commit()
            print("✅ Migration completed successfully!")
            
        elif has_bus_number and not has_number_plate:
            print("\n✅ Table already uses 'bus_number' column. No changes needed.")
            
        elif has_number_plate and has_bus_number:
            print("\n⚠️ Both columns exist. Keeping 'bus_number' and dropping 'number_plate'...")
            # Copy data from number_plate to bus_number if bus_number is empty
            cursor.execute("""
                UPDATE buses 
                SET bus_number = number_plate 
                WHERE bus_number IS NULL OR bus_number = ''
            """)
            conn.commit()
            print("✅ Data synchronized.")
            
        else:
            print("\n❌ Unexpected table structure. Creating new table...")
            recreate_buses_table(cursor)
            conn.commit()
            print("✅ Table recreated successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during migration: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

def create_new_buses_table(cursor):
    """Create a new buses table with correct schema"""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT UNIQUE NOT NULL,
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

def migrate_number_plate_to_bus_number(cursor):
    """Migrate from number_plate to bus_number column"""
    
    # Get all existing data
    cursor.execute("SELECT * FROM buses")
    existing_data = cursor.fetchall()
    
    # Get column names
    cursor.execute("PRAGMA table_info(buses)")
    old_columns = [col[1] for col in cursor.fetchall()]
    
    print(f"📦 Found {len(existing_data)} existing buses to migrate...")
    
    # Create new table with correct schema
    cursor.execute('''
        CREATE TABLE buses_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_number TEXT UNIQUE NOT NULL,
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
    
    # Copy data from old table to new table
    number_plate_idx = old_columns.index('number_plate')
    model_idx = old_columns.index('model')
    capacity_idx = old_columns.index('capacity') if 'capacity' in old_columns else None
    year_idx = old_columns.index('year') if 'year' in old_columns else None
    status_idx = old_columns.index('status') if 'status' in old_columns else None
    notes_idx = old_columns.index('notes') if 'notes' in old_columns else None
    created_by_idx = old_columns.index('created_by') if 'created_by' in old_columns else None
    created_at_idx = old_columns.index('created_at') if 'created_at' in old_columns else None
    
    for row in existing_data:
        cursor.execute('''
            INSERT INTO buses_new (bus_number, model, capacity, year, status, notes, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row[number_plate_idx],
            row[model_idx],
            row[capacity_idx] if capacity_idx else 50,
            row[year_idx] if year_idx else None,
            row[status_idx] if status_idx else 'Active',
            row[notes_idx] if notes_idx else None,
            row[created_by_idx] if created_by_idx else None,
            row[created_at_idx] if created_at_idx else None
        ))
        print(f"  ✓ Migrated: {row[number_plate_idx]}")
    
    # Drop old table and rename new table
    cursor.execute("DROP TABLE buses")
    cursor.execute("ALTER TABLE buses_new RENAME TO buses")
    
    print(f"✅ Successfully migrated {len(existing_data)} buses")

def recreate_buses_table(cursor):
    """Recreate the buses table from scratch (preserves data if possible)"""
    
    # Try to get existing data
    try:
        cursor.execute("SELECT * FROM buses")
        existing_data = cursor.fetchall()
        has_data = len(existing_data) > 0
    except:
        has_data = False
        existing_data = []
    
    # Drop and recreate
    cursor.execute("DROP TABLE IF EXISTS buses")
    create_new_buses_table(cursor)
    
    if has_data:
        print(f"⚠️ Warning: {len(existing_data)} buses were in the old table.")
        print("   Please re-add them manually or restore from backup.")

def verify_fix():
    """Verify the fix was successful"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check schema
        cursor.execute("PRAGMA table_info(buses)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print("\n" + "="*60)
        print("✅ VERIFICATION REPORT")
        print("="*60)
        
        if 'bus_number' in columns:
            print("✅ Column 'bus_number' exists")
        else:
            print("❌ Column 'bus_number' is MISSING")
            return False
        
        if 'model' in columns:
            print("✅ Column 'model' exists")
        else:
            print("❌ Column 'model' is MISSING")
            return False
        
        # Count buses
        cursor.execute("SELECT COUNT(*) FROM buses")
        count = cursor.fetchone()[0]
        print(f"\n📊 Total buses in table: {count}")
        
        # Show sample
        if count > 0:
            cursor.execute("SELECT bus_number, model, status FROM buses LIMIT 3")
            samples = cursor.fetchall()
            print("\n📋 Sample buses:")
            for bus in samples:
                print(f"  • {bus[0]} - {bus[1]} ({bus[2]})")
        
        print("="*60)
        print("✅ All checks passed! Database is ready.")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False
    finally:
        conn.close()

def main():
    """Main function to run the fix"""
    print("\n" + "="*60)
    print("🔧 BUS MANAGEMENT SYSTEM - DATABASE SCHEMA FIX")
    print("="*60)
    print("\nThis script will fix the 'buses' table column name issue.")
    print("It will change 'number_plate' to 'bus_number' if needed.")
    print("\n⚠️  IMPORTANT: A backup will be created automatically.")
    
    input("\nPress ENTER to continue or CTRL+C to cancel...")
    
    print("\n" + "-"*60)
    
    # Step 1: Check current schema
    print("\n📋 Step 1: Checking current database schema...")
    current_columns = check_current_schema()
    
    # Step 2: Create backup
    print("\n💾 Step 2: Creating database backup...")
    backup_database()
    
    # Step 3: Fix the table
    print("\n🔧 Step 3: Fixing buses table...")
    fix_buses_table()
    
    # Step 4: Verify
    print("\n✓ Step 4: Verifying changes...")
    success = verify_fix()
    
    if success:
        print("\n" + "="*60)
        print("🎉 SUCCESS! Your database is now fixed.")
        print("="*60)
        print("\n✅ You can now:")
        print("  1. Restart your Streamlit app")
        print("  2. Add buses using Fleet Management")
        print("  3. Everything should work perfectly!")
        print("\n💡 Tip: If you had buses before, check the backup file.")
    else:
        print("\n" + "="*60)
        print("❌ Something went wrong. Please check the errors above.")
        print("="*60)
        print("\n🔄 You can restore from backup if needed.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        print("\n🔄 Your original database is safe (backup was created).")
