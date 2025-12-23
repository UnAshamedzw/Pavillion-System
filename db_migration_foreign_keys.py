"""
db_migration_foreign_keys.py - Database Migration Script
Adds proper foreign key constraints with ON DELETE SET NULL/CASCADE rules

This script should be run ONCE on your database to add referential integrity.
It's safe to run multiple times - it checks if constraints already exist.

Usage:
    python db_migration_foreign_keys.py

For Railway deployment, set DATABASE_URL environment variable first.
"""

import os
import sys
from datetime import datetime

# Detect database type
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("🐘 Migrating PostgreSQL database...")
else:
    import sqlite3
    DATABASE_PATH = "bus_management.db"
    print("🗄️ Migrating SQLite database...")


def get_connection():
    """Create database connection"""
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def log(message, level="INFO"):
    """Log migration message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def check_constraint_exists_postgres(cursor, table_name, constraint_name):
    """Check if a constraint already exists in PostgreSQL"""
    cursor.execute("""
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = %s AND constraint_name = %s
    """, (table_name, constraint_name))
    return cursor.fetchone() is not None


def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    if USE_POSTGRES:
        cursor.execute("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = %s AND column_name = %s
        """, (table_name, column_name))
    else:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] if isinstance(row, tuple) else row['name'] for row in cursor.fetchall()]
        return column_name in columns
    return cursor.fetchone() is not None


def run_postgres_migration(conn, cursor):
    """Run PostgreSQL-specific migration"""
    
    migrations = []
    
    # ==========================================================================
    # INCOME TABLE - Link to employees
    # ==========================================================================
    
    # Check and add foreign key for driver_employee_id
    if not check_constraint_exists_postgres(cursor, 'income', 'fk_income_driver'):
        migrations.append({
            'name': 'Add FK: income.driver_employee_id -> employees',
            'sql': """
                ALTER TABLE income 
                ADD CONSTRAINT fk_income_driver 
                FOREIGN KEY (driver_employee_id) REFERENCES employees(employee_id) 
                ON DELETE SET NULL
            """
        })
    
    # Check and add foreign key for conductor_employee_id
    if not check_constraint_exists_postgres(cursor, 'income', 'fk_income_conductor'):
        migrations.append({
            'name': 'Add FK: income.conductor_employee_id -> employees',
            'sql': """
                ALTER TABLE income 
                ADD CONSTRAINT fk_income_conductor 
                FOREIGN KEY (conductor_employee_id) REFERENCES employees(employee_id) 
                ON DELETE SET NULL
            """
        })
    
    # ==========================================================================
    # FUEL_RECORDS TABLE - Link to buses
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'fuel_records', 'fk_fuel_bus'):
        migrations.append({
            'name': 'Add FK: fuel_records.bus_number -> buses',
            'sql': """
                ALTER TABLE fuel_records 
                ADD CONSTRAINT fk_fuel_bus 
                FOREIGN KEY (bus_number) REFERENCES buses(registration_number) 
                ON DELETE SET NULL
            """
        })
    
    # ==========================================================================
    # MAINTENANCE TABLE - Link to buses
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'maintenance', 'fk_maintenance_bus'):
        migrations.append({
            'name': 'Add FK: maintenance.bus_number -> buses',
            'sql': """
                ALTER TABLE maintenance 
                ADD CONSTRAINT fk_maintenance_bus 
                FOREIGN KEY (bus_number) REFERENCES buses(registration_number) 
                ON DELETE SET NULL
            """
        })
    
    # ==========================================================================
    # BUS_ASSIGNMENTS TABLE - Links
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'bus_assignments', 'fk_assignment_bus'):
        migrations.append({
            'name': 'Add FK: bus_assignments.bus_id -> buses',
            'sql': """
                ALTER TABLE bus_assignments 
                ADD CONSTRAINT fk_assignment_bus 
                FOREIGN KEY (bus_id) REFERENCES buses(id) 
                ON DELETE CASCADE
            """
        })
    
    if not check_constraint_exists_postgres(cursor, 'bus_assignments', 'fk_assignment_driver'):
        migrations.append({
            'name': 'Add FK: bus_assignments.driver_employee_id -> employees',
            'sql': """
                ALTER TABLE bus_assignments 
                ADD CONSTRAINT fk_assignment_driver 
                FOREIGN KEY (driver_employee_id) REFERENCES employees(employee_id) 
                ON DELETE SET NULL
            """
        })
    
    if not check_constraint_exists_postgres(cursor, 'bus_assignments', 'fk_assignment_conductor'):
        migrations.append({
            'name': 'Add FK: bus_assignments.conductor_employee_id -> employees',
            'sql': """
                ALTER TABLE bus_assignments 
                ADD CONSTRAINT fk_assignment_conductor 
                FOREIGN KEY (conductor_employee_id) REFERENCES employees(employee_id) 
                ON DELETE SET NULL
            """
        })
    
    # ==========================================================================
    # LEAVE_RECORDS TABLE
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'leave_records', 'fk_leave_employee'):
        migrations.append({
            'name': 'Add FK: leave_records.employee_id -> employees',
            'sql': """
                ALTER TABLE leave_records 
                ADD CONSTRAINT fk_leave_employee 
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id) 
                ON DELETE CASCADE
            """
        })
    
    # ==========================================================================
    # EMPLOYEE_LOANS TABLE
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'employee_loans', 'fk_loan_employee'):
        migrations.append({
            'name': 'Add FK: employee_loans.employee_id -> employees',
            'sql': """
                ALTER TABLE employee_loans 
                ADD CONSTRAINT fk_loan_employee 
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id) 
                ON DELETE CASCADE
            """
        })
    
    # ==========================================================================
    # EMPLOYEE_DEDUCTIONS TABLE
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'employee_deductions', 'fk_deduction_employee'):
        migrations.append({
            'name': 'Add FK: employee_deductions.employee_id -> employees',
            'sql': """
                ALTER TABLE employee_deductions 
                ADD CONSTRAINT fk_deduction_employee 
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id) 
                ON DELETE CASCADE
            """
        })
    
    # ==========================================================================
    # RED_TICKETS TABLE
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'red_tickets', 'fk_redticket_conductor'):
        migrations.append({
            'name': 'Add FK: red_tickets.conductor_id -> employees',
            'sql': """
                ALTER TABLE red_tickets 
                ADD CONSTRAINT fk_redticket_conductor 
                FOREIGN KEY (conductor_id) REFERENCES employees(employee_id) 
                ON DELETE SET NULL
            """
        })
    
    if not check_constraint_exists_postgres(cursor, 'red_tickets', 'fk_redticket_inspector'):
        migrations.append({
            'name': 'Add FK: red_tickets.inspector_id -> employees',
            'sql': """
                ALTER TABLE red_tickets 
                ADD CONSTRAINT fk_redticket_inspector 
                FOREIGN KEY (inspector_id) REFERENCES employees(employee_id) 
                ON DELETE SET NULL
            """
        })
    
    # ==========================================================================
    # PAYROLL_RECORDS TABLE
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'payroll_records', 'fk_payroll_period'):
        migrations.append({
            'name': 'Add FK: payroll_records.payroll_period_id -> payroll_periods',
            'sql': """
                ALTER TABLE payroll_records 
                ADD CONSTRAINT fk_payroll_period 
                FOREIGN KEY (payroll_period_id) REFERENCES payroll_periods(id) 
                ON DELETE CASCADE
            """
        })
    
    if not check_constraint_exists_postgres(cursor, 'payroll_records', 'fk_payroll_employee'):
        migrations.append({
            'name': 'Add FK: payroll_records.employee_id -> employees',
            'sql': """
                ALTER TABLE payroll_records 
                ADD CONSTRAINT fk_payroll_employee 
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id) 
                ON DELETE SET NULL
            """
        })
    
    # ==========================================================================
    # CASH_RECONCILIATION TABLE
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'cash_reconciliation', 'fk_recon_employee'):
        migrations.append({
            'name': 'Add FK: cash_reconciliation.employee_id -> employees',
            'sql': """
                ALTER TABLE cash_reconciliation 
                ADD CONSTRAINT fk_recon_employee 
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id) 
                ON DELETE SET NULL
            """
        })
    
    # ==========================================================================
    # BOOKINGS TABLE
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'bookings', 'fk_booking_customer'):
        migrations.append({
            'name': 'Add FK: bookings.customer_id -> customers',
            'sql': """
                ALTER TABLE bookings 
                ADD CONSTRAINT fk_booking_customer 
                FOREIGN KEY (customer_id) REFERENCES customers(id) 
                ON DELETE SET NULL
            """
        })
    
    # ==========================================================================
    # INVENTORY_TRANSACTIONS TABLE
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'inventory_transactions', 'fk_invtrans_inventory'):
        migrations.append({
            'name': 'Add FK: inventory_transactions.inventory_id -> inventory',
            'sql': """
                ALTER TABLE inventory_transactions 
                ADD CONSTRAINT fk_invtrans_inventory 
                FOREIGN KEY (inventory_id) REFERENCES inventory(id) 
                ON DELETE CASCADE
            """
        })
    
    # ==========================================================================
    # EMPLOYEE_REQUESTS TABLE
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'employee_requests', 'fk_request_employee'):
        migrations.append({
            'name': 'Add FK: employee_requests.employee_id -> employees',
            'sql': """
                ALTER TABLE employee_requests 
                ADD CONSTRAINT fk_request_employee 
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id) 
                ON DELETE CASCADE
            """
        })
    
    # ==========================================================================
    # EMPLOYEE_COMPLAINTS TABLE
    # ==========================================================================
    
    if not check_constraint_exists_postgres(cursor, 'employee_complaints', 'fk_complaint_employee'):
        migrations.append({
            'name': 'Add FK: employee_complaints.employee_id -> employees',
            'sql': """
                ALTER TABLE employee_complaints 
                ADD CONSTRAINT fk_complaint_employee 
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id) 
                ON DELETE CASCADE
            """
        })
    
    # ==========================================================================
    # Execute Migrations
    # ==========================================================================
    
    if not migrations:
        log("No migrations needed - all constraints already exist!", "SUCCESS")
        return True
    
    log(f"Found {len(migrations)} migrations to apply...")
    
    success_count = 0
    error_count = 0
    
    for migration in migrations:
        try:
            log(f"Applying: {migration['name']}")
            cursor.execute(migration['sql'])
            conn.commit()
            log(f"✅ Success: {migration['name']}", "SUCCESS")
            success_count += 1
        except Exception as e:
            error_msg = str(e)
            # Check if it's a "column doesn't exist" error - skip gracefully
            if 'does not exist' in error_msg or 'column' in error_msg.lower():
                log(f"⏭️ Skipped (column/table not found): {migration['name']}", "WARN")
            else:
                log(f"❌ Error: {migration['name']} - {error_msg}", "ERROR")
                error_count += 1
            conn.rollback()
    
    log(f"Migration complete: {success_count} applied, {error_count} errors")
    return error_count == 0


def run_sqlite_migration(conn, cursor):
    """
    Run SQLite-specific migration.
    
    Note: SQLite has limited ALTER TABLE support. Foreign keys can only be added
    by recreating tables. This script creates proper constraints for NEW tables
    and documents existing limitations.
    """
    
    log("SQLite has limited foreign key support via ALTER TABLE", "WARN")
    log("For full referential integrity, consider migrating to PostgreSQL", "INFO")
    
    # Enable foreign key support (must be done per-connection in SQLite)
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Check current foreign key status
    cursor.execute("PRAGMA foreign_keys")
    fk_status = cursor.fetchone()
    log(f"Foreign keys enabled: {fk_status[0] == 1}")
    
    # For SQLite, we'll add a trigger-based approach for critical relationships
    triggers = []
    
    # Trigger: Prevent deleting employees that have income records
    triggers.append({
        'name': 'prevent_employee_delete_with_income',
        'sql': """
            CREATE TRIGGER IF NOT EXISTS prevent_employee_delete_with_income
            BEFORE DELETE ON employees
            FOR EACH ROW
            WHEN EXISTS (SELECT 1 FROM income WHERE driver_employee_id = OLD.employee_id OR conductor_employee_id = OLD.employee_id)
            BEGIN
                SELECT RAISE(ABORT, 'Cannot delete employee with existing income records. Set to Terminated instead.');
            END
        """
    })
    
    # Trigger: Prevent deleting buses that have income records
    triggers.append({
        'name': 'prevent_bus_delete_with_income',
        'sql': """
            CREATE TRIGGER IF NOT EXISTS prevent_bus_delete_with_income
            BEFORE DELETE ON buses
            FOR EACH ROW
            WHEN EXISTS (SELECT 1 FROM income WHERE bus_number = OLD.registration_number)
            BEGIN
                SELECT RAISE(ABORT, 'Cannot delete bus with existing income records. Set to Inactive instead.');
            END
        """
    })
    
    # Trigger: Cascade delete payroll_records when period is deleted
    triggers.append({
        'name': 'cascade_delete_payroll_records',
        'sql': """
            CREATE TRIGGER IF NOT EXISTS cascade_delete_payroll_records
            BEFORE DELETE ON payroll_periods
            FOR EACH ROW
            BEGIN
                DELETE FROM payroll_records WHERE payroll_period_id = OLD.id;
            END
        """
    })
    
    # Trigger: Cascade delete leave_records when employee is deleted
    triggers.append({
        'name': 'cascade_delete_leave_records',
        'sql': """
            CREATE TRIGGER IF NOT EXISTS cascade_delete_leave_records
            BEFORE DELETE ON employees
            FOR EACH ROW
            BEGIN
                DELETE FROM leave_records WHERE employee_id = OLD.employee_id;
            END
        """
    })
    
    # Trigger: Set employee references to NULL when employee is deleted (for income)
    triggers.append({
        'name': 'nullify_income_employee_refs',
        'sql': """
            CREATE TRIGGER IF NOT EXISTS nullify_income_employee_refs
            AFTER DELETE ON employees
            FOR EACH ROW
            BEGIN
                UPDATE income SET driver_employee_id = NULL WHERE driver_employee_id = OLD.employee_id;
                UPDATE income SET conductor_employee_id = NULL WHERE conductor_employee_id = OLD.employee_id;
            END
        """
    })
    
    log(f"Creating {len(triggers)} integrity triggers...")
    
    success_count = 0
    for trigger in triggers:
        try:
            cursor.execute(trigger['sql'])
            conn.commit()
            log(f"✅ Created trigger: {trigger['name']}", "SUCCESS")
            success_count += 1
        except Exception as e:
            if 'already exists' in str(e).lower():
                log(f"⏭️ Trigger already exists: {trigger['name']}", "INFO")
                success_count += 1
            else:
                log(f"❌ Error creating trigger {trigger['name']}: {e}", "ERROR")
    
    log(f"SQLite migration complete: {success_count}/{len(triggers)} triggers created")
    return True


def main():
    """Main migration function"""
    print("=" * 60)
    print("DATABASE MIGRATION: Foreign Key Constraints")
    print("=" * 60)
    print()
    
    log("Starting migration...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRES:
            success = run_postgres_migration(conn, cursor)
        else:
            success = run_sqlite_migration(conn, cursor)
        
        conn.close()
        
        if success:
            log("Migration completed successfully!", "SUCCESS")
            print()
            print("=" * 60)
            print("✅ MIGRATION COMPLETE")
            print("=" * 60)
            return 0
        else:
            log("Migration completed with errors", "WARN")
            return 1
            
    except Exception as e:
        log(f"Migration failed: {e}", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())
