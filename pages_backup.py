"""
pages_backup.py - Backup & Export System
Pavillion Coaches Bus Management System
Full database backup, table exports, and data management
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import get_connection, get_engine, USE_POSTGRES
from audit_logger import AuditLogger
from auth import has_permission
import io
import json
import re


# =============================================================================
# SECURITY: Table Name Validation
# =============================================================================

# Whitelist of valid table names in the system
VALID_TABLES = {
    'users', 'user_sessions', 'roles', 'role_permissions', 'user_permissions',
    'buses', 'routes', 'employees', 'income', 'maintenance', 'fuel_records',
    'general_expenses', 'inventory', 'customers', 'bookings', 'documents',
    'audit_log', 'leave_records', 'disciplinary_records', 'employee_performance',
    'contract_templates', 'generated_contracts', 'payroll_periods', 'payroll_records',
    'tax_brackets', 'system_settings', 'employee_loans', 'employee_deductions',
    'cash_reconciliation', 'red_tickets', 'employee_requests', 'employee_complaints',
    'bus_assignments', 'notifications', 'notification_recipients',
}


def validate_table_name(table_name):
    """
    Validate table name to prevent SQL injection.
    Returns True if table name is safe, False otherwise.
    """
    if not table_name:
        return False
    
    # Check against whitelist first
    if table_name.lower() in VALID_TABLES:
        return True
    
    # If not in whitelist, verify it's a valid identifier (alphanumeric + underscore only)
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
        return False
    
    # Additional check: verify table exists in database
    try:
        all_tables = get_all_tables()
        return table_name in all_tables
    except Exception as e:
        return False


def safe_table_query(table_name):
    """
    Return a safe table name for use in SQL queries.
    Raises ValueError if table name is invalid.
    """
    if not validate_table_name(table_name):
        raise ValueError(f"Invalid or unauthorized table name: {table_name}")
    return table_name


# =============================================================================
# DATABASE EXPORT FUNCTIONS
# =============================================================================

def get_all_tables():
    """Get list of all tables in the database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if USE_POSTGRES:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
    else:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
    
    tables = cursor.fetchall()
    conn.close()
    
    # Extract table names
    if tables:
        if hasattr(tables[0], 'keys'):
            return [t['table_name'] if 'table_name' in t else t['name'] for t in tables]
        else:
            return [t[0] for t in tables]
    return []


def get_table_row_count(table_name):
    """Get row count for a table"""
    # SECURITY FIX: Validate table name
    try:
        safe_name = safe_table_query(table_name)
    except ValueError as e:
        print(f"Security warning: {e}")
        return 0
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"SELECT COUNT(*) as count FROM {safe_name}")
        result = cursor.fetchone()
        count = result['count'] if hasattr(result, 'keys') else result[0]
        return count
    except Exception as e:
        return 0
    finally:
        conn.close()


def export_table_to_dataframe(table_name):
    """Export a single table to a pandas DataFrame"""
    # SECURITY FIX: Validate table name
    try:
        safe_name = safe_table_query(table_name)
    except ValueError as e:
        st.error(f"Security error: {e}")
        return pd.DataFrame()
    
    try:
        query = f"SELECT * FROM {safe_name}"
        df = pd.read_sql_query(query, get_engine())
        return df
    except Exception as e:
        st.error(f"Error exporting {table_name}: {e}")
        return pd.DataFrame()


def export_table_to_csv(table_name):
    """Export a single table to CSV format"""
    df = export_table_to_dataframe(table_name)
    if not df.empty:
        return df.to_csv(index=False)
    return ""


def export_table_to_excel(table_name):
    """Export a single table to Excel format"""
    df = export_table_to_dataframe(table_name)
    if not df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=table_name[:31])  # Excel sheet name limit
        return output.getvalue()
    return None


def export_all_tables_to_excel():
    """Export all tables to a single Excel file with multiple sheets"""
    tables = get_all_tables()
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for table in tables:
            df = export_table_to_dataframe(table)
            if not df.empty:
                # Excel sheet names have 31 char limit
                sheet_name = table[:31]
                df.to_excel(writer, index=False, sheet_name=sheet_name)
    
    return output.getvalue()


def export_filtered_data(table_name, start_date=None, end_date=None, date_column='date'):
    """Export table data with date filtering"""
    # SECURITY FIX: Validate table name
    try:
        safe_name = safe_table_query(table_name)
    except ValueError as e:
        st.error(f"Security error: {e}")
        return pd.DataFrame()
    
    conn = get_connection()
    
    query = f"SELECT * FROM {safe_name}"
    params = []
    
    # Check if table has the date column
    try:
        test_df = pd.read_sql_query(f"SELECT * FROM {safe_name} LIMIT 1", get_engine())
        if date_column not in test_df.columns:
            # Try common date column names
            for col in ['date', 'created_at', 'timestamp', 'assignment_date', 'incident_date', 'start_date']:
                if col in test_df.columns:
                    date_column = col
                    break
            else:
                # No date column found, export all
                return export_table_to_dataframe(safe_name)
    except Exception as e:
        return export_table_to_dataframe(safe_name)
    
    # Validate date_column is alphanumeric to prevent injection
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', date_column):
        return export_table_to_dataframe(safe_name)
    
    ph = '%s' if USE_POSTGRES else '?'
    
    if start_date and end_date:
        query += f" WHERE {date_column} >= {ph} AND {date_column} <= {ph}"
        params = [str(start_date), str(end_date)]
    elif start_date:
        query += f" WHERE {date_column} >= {ph}"
        params = [str(start_date)]
    elif end_date:
        query += f" WHERE {date_column} <= {ph}"
        params = [str(end_date)]
    
    query += f" ORDER BY {date_column} DESC"
    
    try:
        df = pd.read_sql_query(query, get_engine(), params=params)
        return df
    except Exception as e:
        st.warning(f"Could not filter by date: {e}")
        return export_table_to_dataframe(safe_name)


def get_database_summary():
    """Get summary statistics for the entire database"""
    tables = get_all_tables()
    summary = []
    
    for table in tables:
        # Tables from get_all_tables are already validated
        count = get_table_row_count(table)
        summary.append({
            'Table': table,
            'Records': count
        })
    
    return pd.DataFrame(summary)


def generate_sql_backup():
    """Generate SQL statements for database backup (structure + data)"""
    tables = get_all_tables()
    sql_statements = []
    
    sql_statements.append("-- Pavillion Coaches Database Backup")
    sql_statements.append(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sql_statements.append("-- Database: " + ("PostgreSQL" if USE_POSTGRES else "SQLite"))
    sql_statements.append("")
    
    for table in tables:
        # SECURITY: Tables from get_all_tables are validated; validate again for safety
        if not validate_table_name(table):
            continue
            
        df = export_table_to_dataframe(table)
        
        if df.empty:
            continue
        
        sql_statements.append(f"-- Table: {table}")
        sql_statements.append(f"-- Records: {len(df)}")
        
        # Generate INSERT statements
        for _, row in df.iterrows():
            columns = ', '.join(df.columns)
            values = []
            for val in row:
                if pd.isna(val):
                    values.append('NULL')
                elif isinstance(val, str):
                    # Escape single quotes
                    escaped = val.replace("'", "''")
                    values.append(f"'{escaped}'")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                else:
                    values.append(f"'{str(val)}'")
            
            values_str = ', '.join(values)
            sql_statements.append(f"INSERT INTO {table} ({columns}) VALUES ({values_str});")
        
        sql_statements.append("")
    
    return '\n'.join(sql_statements)


# =============================================================================
# REPORT GENERATION FUNCTIONS
# =============================================================================

def generate_financial_report(start_date, end_date):
    """Generate a financial summary report"""
    report = {}
    
    # Income
    try:
        income_df = export_filtered_data('income', start_date, end_date)
        report['income'] = {
            'total': income_df['amount'].sum() if not income_df.empty else 0,
            'count': len(income_df),
            'by_route': income_df.groupby('route')['amount'].sum().to_dict() if not income_df.empty else {}
        }
    except Exception as e:
        report['income'] = {'total': 0, 'count': 0, 'by_route': {}}
    
    # Maintenance
    try:
        maint_df = export_filtered_data('maintenance', start_date, end_date)
        report['maintenance'] = {
            'total': maint_df['cost'].sum() if not maint_df.empty else 0,
            'count': len(maint_df),
            'by_type': maint_df.groupby('maintenance_type')['cost'].sum().to_dict() if not maint_df.empty else {}
        }
    except Exception as e:
        report['maintenance'] = {'total': 0, 'count': 0, 'by_type': {}}
    
    # Fuel
    try:
        fuel_df = export_filtered_data('fuel_records', start_date, end_date)
        report['fuel'] = {
            'total': fuel_df['total_cost'].sum() if not fuel_df.empty else 0,
            'liters': fuel_df['liters'].sum() if not fuel_df.empty else 0,
            'count': len(fuel_df)
        }
    except Exception as e:
        report['fuel'] = {'total': 0, 'liters': 0, 'count': 0}
    
    # Payroll
    try:
        payroll_df = export_filtered_data('payroll', start_date, end_date, 'month')
        report['payroll'] = {
            'total': payroll_df['net_salary'].sum() if not payroll_df.empty else 0,
            'count': len(payroll_df)
        }
    except Exception as e:
        report['payroll'] = {'total': 0, 'count': 0}
    
    # Calculate totals
    report['summary'] = {
        'total_income': report['income']['total'],
        'total_expenses': report['maintenance']['total'] + report['fuel']['total'] + report['payroll']['total'],
        'net_profit': report['income']['total'] - (report['maintenance']['total'] + report['fuel']['total'] + report['payroll']['total'])
    }
    
    return report


def generate_fleet_report():
    """Generate fleet status report"""
    report = {}
    
    try:
        buses_df = export_table_to_dataframe('buses')
        if not buses_df.empty:
            report['total_buses'] = len(buses_df)
            report['active_buses'] = len(buses_df[buses_df['status'] == 'Active'])
            report['inactive_buses'] = len(buses_df[buses_df['status'] != 'Active'])
            
            # Check for expiring documents
            today = datetime.now().date()
            expiry_cols = ['zinara_licence_expiry', 'vehicle_insurance_expiry', 
                          'passenger_insurance_expiry', 'fitness_expiry', 'route_permit_expiry']
            
            expiring_soon = 0
            expired = 0
            
            for col in expiry_cols:
                if col in buses_df.columns:
                    for val in buses_df[col].dropna():
                        try:
                            exp_date = datetime.strptime(str(val), '%Y-%m-%d').date()
                            if exp_date < today:
                                expired += 1
                            elif exp_date < today + timedelta(days=30):
                                expiring_soon += 1
                        except Exception as e:
                            pass
            
            report['expired_documents'] = expired
            report['expiring_soon'] = expiring_soon
    except Exception as e:
        report = {'total_buses': 0, 'active_buses': 0, 'inactive_buses': 0, 
                 'expired_documents': 0, 'expiring_soon': 0}
    
    return report


def generate_hr_report():
    """Generate HR summary report"""
    report = {}
    
    try:
        emp_df = export_table_to_dataframe('employees')
        if not emp_df.empty:
            report['total_employees'] = len(emp_df)
            report['active_employees'] = len(emp_df[emp_df['status'] == 'Active'])
            report['by_position'] = emp_df.groupby('position').size().to_dict()
    except Exception as e:
        report = {'total_employees': 0, 'active_employees': 0, 'by_position': {}}
    
    try:
        leave_df = export_table_to_dataframe('leave_records')
        if not leave_df.empty:
            report['pending_leave'] = len(leave_df[leave_df['status'] == 'Pending'])
            report['approved_leave'] = len(leave_df[leave_df['status'] == 'Approved'])
    except Exception as e:
        report['pending_leave'] = 0
        report['approved_leave'] = 0
    
    return report


# =============================================================================
# PAGE FUNCTION
# =============================================================================

def backup_export_page():
    """Main backup and export page"""
    
    st.header("💾 Backup & Export")
    st.markdown("Export data, create backups, and generate reports")
    st.markdown("---")
    
    # Check permissions
    can_export = has_permission('export_income') or has_permission('generate_reports')
    
    if not can_export:
        st.warning("You don't have permission to export data. Contact your administrator.")
        return
    
    # Tabs for different functions
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Export Tables", "💾 Full Backup", "📈 Reports", "🗄️ Database Info"])
    
    with tab1:
        st.subheader("📊 Export Individual Tables")
        
        tables = get_all_tables()
        
        if not tables:
            st.warning("No tables found in database")
        else:
            # Table selection
            col1, col2 = st.columns(2)
            
            with col1:
                selected_table = st.selectbox("Select Table to Export", tables)
            
            with col2:
                export_format = st.selectbox("Export Format", ["CSV", "Excel"])
            
            # Show table preview
            if selected_table:
                row_count = get_table_row_count(selected_table)
                st.info(f"📋 **{selected_table}** contains **{row_count:,}** records")
                
                # Date filter option
                st.markdown("#### Filter by Date (Optional)")
                use_date_filter = st.checkbox("Filter by date range")
                
                start_date = None
                end_date = None
                
                if use_date_filter:
                    col1, col2 = st.columns(2)
                    with col1:
                        start_date = st.date_input("From Date", value=datetime.now().date() - timedelta(days=30))
                    with col2:
                        end_date = st.date_input("To Date", value=datetime.now().date())
                
                # Preview
                st.markdown("#### Preview (First 10 rows)")
                preview_df = export_table_to_dataframe(selected_table)
                if not preview_df.empty:
                    st.dataframe(preview_df.head(10), use_container_width=True, hide_index=True)
                
                # Export button
                st.markdown("---")
                
                if st.button(f"📥 Export {selected_table}", type="primary"):
                    with st.spinner("Preparing export..."):
                        if use_date_filter:
                            export_df = export_filtered_data(selected_table, start_date, end_date)
                        else:
                            export_df = export_table_to_dataframe(selected_table)
                        
                        if not export_df.empty:
                            if export_format == "CSV":
                                csv_data = export_df.to_csv(index=False)
                                st.download_button(
                                    label="⬇️ Download CSV",
                                    data=csv_data,
                                    file_name=f"{selected_table}_{datetime.now().strftime('%Y%m%d')}.csv",
                                    mime="text/csv"
                                )
                            else:
                                output = io.BytesIO()
                                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                    export_df.to_excel(writer, index=False, sheet_name=selected_table[:31])
                                
                                st.download_button(
                                    label="⬇️ Download Excel",
                                    data=output.getvalue(),
                                    file_name=f"{selected_table}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            
                            AuditLogger.log_action(
                                "Export", "Backup",
                                f"Exported table: {selected_table} ({len(export_df)} records)"
                            )
                            st.success(f"✅ Exported {len(export_df)} records!")
                        else:
                            st.warning("No data to export")
    
    with tab2:
        st.subheader("💾 Full Database Backup")
        st.markdown("Download a complete backup of all your data")
        
        # Database summary
        st.markdown("#### Database Summary")
        summary_df = get_database_summary()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📊 Total Tables", len(summary_df))
        with col2:
            st.metric("📝 Total Records", f"{summary_df['Records'].sum():,}")
        
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Backup options
        st.markdown("#### Backup Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 📗 Excel Backup")
            st.caption("All tables in one Excel file with separate sheets")
            
            if st.button("📥 Generate Excel Backup", type="primary"):
                with st.spinner("Generating Excel backup..."):
                    excel_data = export_all_tables_to_excel()
                    
                    st.download_button(
                        label="⬇️ Download Excel Backup",
                        data=excel_data,
                        file_name=f"pavillion_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    AuditLogger.log_action(
                        "Backup", "System",
                        f"Generated full Excel backup ({len(get_all_tables())} tables)"
                    )
                    st.success("✅ Excel backup ready!")
        
        with col2:
            st.markdown("##### 📄 SQL Backup")
            st.caption("SQL statements to recreate all data")
            
            if st.button("📥 Generate SQL Backup"):
                with st.spinner("Generating SQL backup..."):
                    sql_data = generate_sql_backup()
                    
                    st.download_button(
                        label="⬇️ Download SQL Backup",
                        data=sql_data,
                        file_name=f"pavillion_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
                        mime="text/plain"
                    )
                    
                    AuditLogger.log_action(
                        "Backup", "System",
                        "Generated full SQL backup"
                    )
                    st.success("✅ SQL backup ready!")
        
        st.markdown("---")
        
        # Individual table exports
        st.markdown("#### Export All Tables as CSV (ZIP)")
        st.caption("Download each table as a separate CSV file")
        
        if st.button("📥 Generate CSV Backup (All Tables)"):
            with st.spinner("Generating CSV files..."):
                import zipfile
                
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for table in get_all_tables():
                        csv_data = export_table_to_csv(table)
                        if csv_data:
                            zip_file.writestr(f"{table}.csv", csv_data)
                
                st.download_button(
                    label="⬇️ Download CSV ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"pavillion_csv_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip"
                )
                
                AuditLogger.log_action(
                    "Backup", "System",
                    "Generated CSV ZIP backup"
                )
                st.success("✅ CSV backup ready!")
    
    with tab3:
        st.subheader("📈 Generate Reports")
        
        # Date range for reports
        col1, col2 = st.columns(2)
        with col1:
            report_start = st.date_input("Report From", value=datetime.now().date().replace(day=1), key="report_start")
        with col2:
            report_end = st.date_input("Report To", value=datetime.now().date(), key="report_end")
        
        st.markdown("---")
        
        # Financial Report
        st.markdown("### 💰 Financial Report")
        
        if st.button("📊 Generate Financial Report", type="primary"):
            with st.spinner("Generating report..."):
                report = generate_financial_report(report_start, report_end)
                
                st.markdown(f"#### Financial Summary: {report_start} to {report_end}")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("💵 Total Income", f"${report['income']['total']:,.2f}")
                with col2:
                    st.metric("🔧 Maintenance", f"${report['maintenance']['total']:,.2f}")
                with col3:
                    st.metric("⛽ Fuel", f"${report['fuel']['total']:,.2f}")
                with col4:
                    profit = report['summary']['net_profit']
                    st.metric("📈 Net Profit", f"${profit:,.2f}", 
                             delta="Profit" if profit > 0 else "Loss",
                             delta_color="normal" if profit > 0 else "inverse")
                
                # Detailed breakdown
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("##### Income by Route")
                    if report['income']['by_route']:
                        for route, amount in sorted(report['income']['by_route'].items(), key=lambda x: x[1], reverse=True):
                            st.write(f"- **{route}**: ${amount:,.2f}")
                    else:
                        st.info("No income data")
                
                with col2:
                    st.markdown("##### Expenses by Type")
                    if report['maintenance']['by_type']:
                        for mtype, cost in sorted(report['maintenance']['by_type'].items(), key=lambda x: x[1], reverse=True):
                            st.write(f"- **{mtype}**: ${cost:,.2f}")
                    else:
                        st.info("No maintenance data")
                
                # Export report
                report_data = {
                    'Period': f"{report_start} to {report_end}",
                    'Total Income': report['income']['total'],
                    'Income Transactions': report['income']['count'],
                    'Maintenance Cost': report['maintenance']['total'],
                    'Maintenance Jobs': report['maintenance']['count'],
                    'Fuel Cost': report['fuel']['total'],
                    'Fuel Liters': report['fuel']['liters'],
                    'Payroll Cost': report['payroll']['total'],
                    'Total Expenses': report['summary']['total_expenses'],
                    'Net Profit/Loss': report['summary']['net_profit']
                }
                
                report_df = pd.DataFrame([report_data])
                csv_report = report_df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download Report CSV",
                    data=csv_report,
                    file_name=f"financial_report_{report_start}_{report_end}.csv",
                    mime="text/csv"
                )
                
                AuditLogger.log_action(
                    "Report", "Financial",
                    f"Generated financial report: {report_start} to {report_end}"
                )
        
        st.markdown("---")
        
        # Fleet Report
        st.markdown("### 🚌 Fleet Status Report")
        
        if st.button("🚌 Generate Fleet Report"):
            with st.spinner("Generating report..."):
                report = generate_fleet_report()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("🚌 Total Buses", report['total_buses'])
                with col2:
                    st.metric("✅ Active", report['active_buses'])
                with col3:
                    st.metric("⚠️ Expiring Soon", report['expiring_soon'])
                with col4:
                    st.metric("❌ Expired", report['expired_documents'])
                
                AuditLogger.log_action("Report", "Fleet", "Generated fleet status report")
        
        st.markdown("---")
        
        # HR Report
        st.markdown("### 👥 HR Summary Report")
        
        if st.button("👥 Generate HR Report"):
            with st.spinner("Generating report..."):
                report = generate_hr_report()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("👥 Total Staff", report['total_employees'])
                with col2:
                    st.metric("✅ Active", report['active_employees'])
                with col3:
                    st.metric("📅 Pending Leave", report['pending_leave'])
                with col4:
                    st.metric("✅ Approved Leave", report['approved_leave'])
                
                if report['by_position']:
                    st.markdown("##### Staff by Position")
                    for position, count in sorted(report['by_position'].items(), key=lambda x: x[1], reverse=True):
                        st.write(f"- **{position}**: {count}")
                
                AuditLogger.log_action("Report", "HR", "Generated HR summary report")
    
    with tab4:
        st.subheader("🗄️ Database Information")
        
        # Database type
        db_type = "PostgreSQL (Railway)" if USE_POSTGRES else "SQLite (Local)"
        st.info(f"**Database Type:** {db_type}")
        
        # Table details
        st.markdown("### Table Details")
        
        tables = get_all_tables()
        
        for table in tables:
            count = get_table_row_count(table)
            
            with st.expander(f"📋 {table} ({count:,} records)"):
                # Get sample data and column info
                df = export_table_to_dataframe(table)
                
                if not df.empty:
                    st.markdown("**Columns:**")
                    col_info = []
                    for col in df.columns:
                        dtype = str(df[col].dtype)
                        non_null = df[col].notna().sum()
                        col_info.append({
                            'Column': col,
                            'Type': dtype,
                            'Non-Null': f"{non_null}/{len(df)}"
                        })
                    
                    st.dataframe(pd.DataFrame(col_info), use_container_width=True, hide_index=True)
                    
                    st.markdown("**Sample Data (5 rows):**")
                    st.dataframe(df.head(5), use_container_width=True, hide_index=True)
                else:
                    st.info("Table is empty")
        
        st.markdown("---")
        
        # Storage estimate
        st.markdown("### 💿 Storage Estimate")
        
        total_records = sum(get_table_row_count(t) for t in tables)
        
        # Rough estimate: ~500 bytes per record average
        estimated_size_kb = (total_records * 500) / 1024
        estimated_size_mb = estimated_size_kb / 1024
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Tables", len(tables))
        with col2:
            st.metric("📝 Total Records", f"{total_records:,}")
        with col3:
            if estimated_size_mb >= 1:
                st.metric("💿 Est. Size", f"{estimated_size_mb:.1f} MB")
            else:
                st.metric("💿 Est. Size", f"{estimated_size_kb:.0f} KB")