"""
migrate_database.py - Run this script to update the database schema
Usage: python migrate_database.py
"""

import sqlite3
import os
from datetime import datetime

def backup_database():
    """Create a backup of the database before migration"""
    db_file = 'bus_management.db'
    
    if not os.path.exists(db_file):
        print(f"❌ Database file '{db_file}' not found!")
        return False
    
    # Create backup with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'bus_management_backup_{timestamp}.db'
    
    try:
        import shutil
        shutil.copy2(db_file, backup_file)
        print(f"✅ Backup created: {backup_file}")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def migrate_income_table():
    """Add employee ID columns to income table"""
    
    print("\n🔄 Starting migration...")
    
    conn = sqlite3.connect('bus_management.db')
    cursor = conn.cursor()
    
    try:
        # Check if migration is needed
        cursor.execute("PRAGMA table_info(income)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'driver_employee_id' in columns and 'conductor_employee_id' in columns:
            print("✅ Database already migrated! No changes needed.")
            return True
        
        print("📝 Migration needed. Updating schema...")
        
        # Step 1: Create new table with proper schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS income_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bus_number TEXT NOT NULL,
                route TEXT NOT NULL,
                hire_destination TEXT,
                driver_employee_id TEXT,
                driver_name TEXT,
                conductor_employee_id TEXT,
                conductor_name TEXT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Created new income table structure")
        
        # Step 2: Copy existing data
        cursor.execute('''
            INSERT INTO income_new 
            (id, bus_number, route, hire_destination, driver_name, conductor_name, 
             date, amount, notes, created_by, created_at)
            SELECT id, bus_number, route, hire_destination, driver_name, conductor_name, 
                   date, amount, notes, created_by, created_at
            FROM income
        ''')
        
        rows_copied = cursor.rowcount
        print(f"✅ Copied {rows_copied} existing records")
        
        # Step 3: Drop old table and rename new one
        cursor.execute('DROP TABLE income')
        cursor.execute('ALTER TABLE income_new RENAME TO income')
        print("✅ Replaced old table with new structure")
        
        # Step 4: Update existing records to populate employee IDs
        cursor.execute('''
            UPDATE income
            SET driver_employee_id = (
                SELECT employee_id 
                FROM employees 
                WHERE employees.full_name = income.driver_name 
                AND employees.position LIKE '%Driver%'
                LIMIT 1
            )
            WHERE driver_employee_id IS NULL AND driver_name IS NOT NULL
        ''')
        
        drivers_updated = cursor.rowcount
        print(f"✅ Updated {drivers_updated} driver employee IDs")
        
        cursor.execute('''
            UPDATE income
            SET conductor_employee_id = (
                SELECT employee_id 
                FROM employees 
                WHERE employees.full_name = income.conductor_name 
                AND employees.position LIKE '%Conductor%'
                LIMIT 1
            )
            WHERE conductor_employee_id IS NULL AND conductor_name IS NOT NULL
        ''')
        
        conductors_updated = cursor.rowcount
        print(f"✅ Updated {conductors_updated} conductor employee IDs")
        
        # Commit all changes
        conn.commit()
        print("\n🎉 Migration completed successfully!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM income")
        total_records = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM income WHERE driver_employee_id IS NOT NULL")
        matched_drivers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM income WHERE conductor_employee_id IS NOT NULL")
        matched_conductors = cursor.fetchone()[0]
        
        print("\n📊 Migration Summary:")
        print(f"   Total income records: {total_records}")
        print(f"   Drivers matched: {matched_drivers}/{total_records}")
        print(f"   Conductors matched: {matched_conductors}/{total_records}")
        
        if matched_drivers < total_records or matched_conductors < total_records:
            print("\n⚠️  Warning: Some employees could not be matched.")
            print("   This is normal if:")
            print("   - Employee names have changed")
            print("   - Employees were deleted")
            print("   - Names don't match exactly")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

def verify_migration():
    """Verify the migration was successful"""
    
    print("\n🔍 Verifying migration...")
    
    conn = sqlite3.connect('bus_management.db')
    cursor = conn.cursor()
    
    try:
        # Check table structure
        cursor.execute("PRAGMA table_info(income)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        required_columns = ['driver_employee_id', 'conductor_employee_id']
        missing = [col for col in required_columns if col not in columns]
        
        if missing:
            print(f"❌ Missing columns: {', '.join(missing)}")
            return False
        
        print("✅ All required columns present")
        
        # Check data integrity
        cursor.execute("SELECT COUNT(*) FROM income")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM income WHERE date IS NOT NULL AND amount IS NOT NULL")
        valid = cursor.fetchone()[0]
        
        if total != valid:
            print(f"⚠️  Warning: {total - valid} records have missing data")
        else:
            print(f"✅ All {total} records are valid")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
        
    finally:
        conn.close()

def main():
    """Main migration process"""
    
    print("=" * 60)
    print("🚌 Pavillion Coaches - Database Migration Tool")
    print("=" * 60)
    print("\nThis will update the income table to store employee IDs")
    print("\n⚠️  IMPORTANT: A backup will be created automatically")
    
    response = input("\nContinue with migration? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("\n❌ Migration cancelled by user")
        return
    
    # Step 1: Backup
    if not backup_database():
        print("\n❌ Cannot proceed without backup")
        return
    
    # Step 2: Migrate
    if not migrate_income_table():
        print("\n❌ Migration failed. Your backup is safe.")
        return
    
    # Step 3: Verify
    if not verify_migration():
        print("\n⚠️  Migration completed but verification found issues")
        print("   Please check your data before continuing")
        return
    
    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Test your application")
    print("2. If everything works, you can delete the backup file")
    print("3. If there are issues, restore from backup")
    print("\n💡 Backup location: bus_management_backup_*.db")

if __name__ == "__main__":
    main()