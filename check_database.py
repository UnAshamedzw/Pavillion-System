"""
check_database.py - Inspect your database structure
Run this to see what tables exist in your database
"""

import sqlite3

DATABASE_PATH = "bus_management.db"

def inspect_database():
    """Inspect the database and show all tables and their structures"""
    
    print("="*70)
    print("🔍 DATABASE INSPECTION TOOL")
    print("="*70)
    print()
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        if not tables:
            print("❌ No tables found in database!")
            print("\n💡 This appears to be a new database.")
            print("   Solution: Just run 'streamlit run app.py' and it will create all tables.")
            return
        
        print(f"📊 Found {len(tables)} table(s):\n")
        
        for (table_name,) in tables:
            print(f"📋 Table: {table_name}")
            print("-" * 70)
            
            # Get table structure
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("  Columns:")
            for col in columns:
                col_id, name, data_type, not_null, default, pk = col
                pk_text = " [PRIMARY KEY]" if pk else ""
                not_null_text = " NOT NULL" if not_null else ""
                default_text = f" DEFAULT {default}" if default else ""
                print(f"    • {name} ({data_type}){not_null_text}{default_text}{pk_text}")
            
            # Get record count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"\n  Records: {count}")
            
            # Show sample data if records exist
            if count > 0 and count <= 3:
                print(f"\n  Sample data:")
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                for row in rows:
                    print(f"    {row}")
            
            print()
        
        conn.close()
        
        # Check for required tables
        table_names = [t[0] for t in tables]
        print("\n" + "="*70)
        print("✅ MIGRATION STATUS CHECK")
        print("="*70 + "\n")
        
        required_tables = {
            'buses': '🚌 Buses table',
            'routes': '🛣️  Routes table',
            'income': '💰 Income table',
            'maintenance': '🔧 Maintenance table',
            'employees': '👥 Employees table'
        }
        
        missing_tables = []
        for table, description in required_tables.items():
            if table in table_names:
                print(f"✅ {description}: EXISTS")
            else:
                print(f"❌ {description}: MISSING")
                missing_tables.append(table)
        
        if missing_tables:
            print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
            print("\n💡 Solution:")
            print("   Just run: streamlit run app.py")
            print("   The app will create all missing tables automatically!")
        else:
            print("\n🎉 All required tables exist!")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_database()
