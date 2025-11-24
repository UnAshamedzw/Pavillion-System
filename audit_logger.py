"""
audit_logger.py - Comprehensive Activity Tracking and Audit Trail System
Automatically logs all user actions for accountability and compliance
"""

import sqlite3
import streamlit as st
from datetime import datetime
import json
from typing import Optional, Dict, Any

class AuditLogger:
    """
    Centralized audit logging system for tracking all user activities
    """
    
    # Action type constants
    ACTION_ADD = "Add"
    ACTION_EDIT = "Edit"
    ACTION_DELETE = "Delete"
    ACTION_VIEW = "View"
    ACTION_EXPORT = "Export"
    ACTION_IMPORT = "Import"
    ACTION_LOGIN = "Login"
    ACTION_LOGOUT = "Logout"
    
    # Module constants
    MODULE_INCOME = "Income"
    MODULE_MAINTENANCE = "Maintenance"
    MODULE_HR = "HR"
    MODULE_EMPLOYEE = "Employee"
    MODULE_PAYROLL = "Payroll"
    MODULE_LEAVE = "Leave"
    MODULE_DISCIPLINARY = "Disciplinary"
    MODULE_USER = "User Management"
    MODULE_SYSTEM = "System"
    
    @staticmethod
    def log_action(
        action_type: str,
        module: str,
        description: str,
        affected_table: Optional[str] = None,
        affected_record_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None
    ):
        """
        Log a user action to the audit trail
        
        Args:
            action_type: Type of action (Add, Edit, Delete, View, etc.)
            module: Module/feature area (Income, HR, etc.)
            description: Human-readable description of the action
            affected_table: Database table affected (optional)
            affected_record_id: ID of the affected record (optional)
            old_values: Previous values before change (optional)
            new_values: New values after change (optional)
        """
        # Get current user from session
        if not st.session_state.get('authenticated', False):
            return  # Don't log if not authenticated
        
        user = st.session_state.get('user', {})
        username = user.get('username', 'Unknown')
        user_id = user.get('id', None)
        
        # Get session ID (for tracking user sessions)
        session_id = st.session_state.get('session_id', None)
        
        try:
            conn = sqlite3.connect('bus_management.db')
            cursor = conn.cursor()
            
            # Convert dictionaries to JSON strings
            old_values_json = json.dumps(old_values) if old_values else None
            new_values_json = json.dumps(new_values) if new_values else None
            
            cursor.execute('''
                INSERT INTO activity_log (
                    username, user_id, timestamp, action_type, module, 
                    description, session_id, affected_table, 
                    affected_record_id, old_values, new_values
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                username,
                user_id,
                datetime.now(),
                action_type,
                module,
                description,
                session_id,
                affected_table,
                affected_record_id,
                old_values_json,
                new_values_json
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Audit logging error: {e}")
            # Fail silently - don't disrupt user operations
    
    @staticmethod
    def log_income_add(bus_number: str, route: str, amount: float, date: str):
        """Convenience method for logging income additions"""
        description = f"Added income record: Bus {bus_number}, Route {route}, Amount ${amount:.2f}, Date {date}"
        AuditLogger.log_action(
            action_type=AuditLogger.ACTION_ADD,
            module=AuditLogger.MODULE_INCOME,
            description=description,
            affected_table="income",
            new_values={
                "bus_number": bus_number,
                "route": route,
                "amount": amount,
                "date": date
            }
        )
    
    @staticmethod
    def log_income_edit(record_id: int, bus_number: str, old_data: dict, new_data: dict):
        """Convenience method for logging income edits"""
        description = f"Updated income record for Bus {bus_number} (ID: {record_id})"
        AuditLogger.log_action(
            action_type=AuditLogger.ACTION_EDIT,
            module=AuditLogger.MODULE_INCOME,
            description=description,
            affected_table="income",
            affected_record_id=record_id,
            old_values=old_data,
            new_values=new_data
        )
    
    @staticmethod
    def log_income_delete(record_id: int, bus_number: str, date: str):
        """Convenience method for logging income deletions"""
        description = f"Deleted income record: Bus {bus_number}, Date {date} (ID: {record_id})"
        AuditLogger.log_action(
            action_type=AuditLogger.ACTION_DELETE,
            module=AuditLogger.MODULE_INCOME,
            description=description,
            affected_table="income",
            affected_record_id=record_id
        )
    
    @staticmethod
    def log_maintenance_add(bus_number: str, maintenance_type: str, cost: float, date: str):
        """Convenience method for logging maintenance additions"""
        description = f"Added maintenance: Bus {bus_number}, Type {maintenance_type}, Cost ${cost:.2f}, Date {date}"
        AuditLogger.log_action(
            action_type=AuditLogger.ACTION_ADD,
            module=AuditLogger.MODULE_MAINTENANCE,
            description=description,
            affected_table="maintenance",
            new_values={
                "bus_number": bus_number,
                "maintenance_type": maintenance_type,
                "cost": cost,
                "date": date
            }
        )
    
    @staticmethod
    def log_maintenance_edit(record_id: int, bus_number: str, old_data: dict, new_data: dict):
        """Convenience method for logging maintenance edits"""
        description = f"Updated maintenance record for Bus {bus_number} (ID: {record_id})"
        AuditLogger.log_action(
            action_type=AuditLogger.ACTION_EDIT,
            module=AuditLogger.MODULE_MAINTENANCE,
            description=description,
            affected_table="maintenance",
            affected_record_id=record_id,
            old_values=old_data,
            new_values=new_data
        )
    
    @staticmethod
    def log_maintenance_delete(record_id: int, bus_number: str, date: str):
        """Convenience method for logging maintenance deletions"""
        description = f"Deleted maintenance record: Bus {bus_number}, Date {date} (ID: {record_id})"
        AuditLogger.log_action(
            action_type=AuditLogger.ACTION_DELETE,
            module=AuditLogger.MODULE_MAINTENANCE,
            description=description,
            affected_table="maintenance",
            affected_record_id=record_id
        )
    
    @staticmethod
    def log_employee_action(action_type: str, employee_name: str, details: str):
        """Convenience method for logging employee-related actions"""
        description = f"{action_type} employee: {employee_name} - {details}"
        AuditLogger.log_action(
            action_type=action_type,
            module=AuditLogger.MODULE_EMPLOYEE,
            description=description,
            affected_table="employees"
        )
    
    @staticmethod
    def log_data_import(module: str, record_count: int, file_name: str):
        """Convenience method for logging bulk data imports"""
        description = f"Imported {record_count} records to {module} from file: {file_name}"
        AuditLogger.log_action(
            action_type=AuditLogger.ACTION_IMPORT,
            module=module,
            description=description
        )
    
    @staticmethod
    def log_data_export(module: str, record_count: int, export_format: str):
        """Convenience method for logging data exports"""
        description = f"Exported {record_count} records from {module} as {export_format}"
        AuditLogger.log_action(
            action_type=AuditLogger.ACTION_EXPORT,
            module=module,
            description=description
        )
    
    @staticmethod
    def log_user_action(action_type: str, target_username: str, details: str):
        """Convenience method for logging user management actions"""
        description = f"{action_type} user: {target_username} - {details}"
        AuditLogger.log_action(
            action_type=action_type,
            module=AuditLogger.MODULE_USER,
            description=description,
            affected_table="users"
        )
    
    @staticmethod
    def get_activity_logs(
        username: Optional[str] = None,
        action_type: Optional[str] = None,
        module: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ):
        """
        Retrieve activity logs with optional filtering
        
        Args:
            username: Filter by username
            action_type: Filter by action type
            module: Filter by module
            start_date: Filter by start date (YYYY-MM-DD)
            end_date: Filter by end date (YYYY-MM-DD)
            limit: Maximum number of records to return
        
        Returns:
            List of log entries
        """
        conn = sqlite3.connect('bus_management.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM activity_log WHERE 1=1"
        params = []
        
        if username:
            query += " AND username = ?"
            params.append(username)
        
        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)
        
        if module:
            query += " AND module = ?"
            params.append(module)
        
        if start_date:
            query += " AND DATE(timestamp) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(timestamp) <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
        conn.close()
        
        return logs
    
    @staticmethod
    def get_user_activity_summary(username: str):
        """Get activity summary for a specific user"""
        conn = sqlite3.connect('bus_management.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                action_type,
                COUNT(*) as count
            FROM activity_log
            WHERE username = ?
            GROUP BY action_type
            ORDER BY count DESC
        ''', (username,))
        
        summary = cursor.fetchall()
        conn.close()
        
        return summary
    
    @staticmethod
    def get_recent_activities(limit: int = 50):
        """Get most recent activities across all users"""
        conn = sqlite3.connect('bus_management.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM activity_log
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        activities = cursor.fetchall()
        conn.close()
        
        return activities


# Convenience function for easy imports
def log_action(action_type: str, module: str, description: str, **kwargs):
    """
    Simple wrapper function for logging actions
    Can be called from anywhere in the application
    
    Example usage:
        log_action("Add", "Income", "Added income for Bus PAV-07")
    """
    AuditLogger.log_action(action_type, module, description, **kwargs)