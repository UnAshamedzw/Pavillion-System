"""
pages_audit.py - Activity Log and Audit Trail Viewer
Administrator interface for reviewing all system activities
CORRECTED VERSION - Handles both PostgreSQL and SQLite row formats
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from audit_logger import AuditLogger
from auth import check_permission
import json


def get_log_value(log, key, default=''):
    """Helper function to get value from log entry regardless of format"""
    if hasattr(log, 'keys'):
        return log.get(key, default)
    elif hasattr(log, '_fields'):
        # Named tuple
        return getattr(log, key, default)
    else:
        # Try to access by index using a mapping
        field_map = {
            'id': 0, 'username': 1, 'user_id': 2, 'timestamp': 3,
            'action_type': 4, 'module': 5, 'description': 6,
            'ip_address': 7, 'session_id': 8, 'affected_table': 9,
            'affected_record_id': 10, 'old_values': 11, 'new_values': 12
        }
        try:
            return log[field_map.get(key, 0)] if key in field_map else default
        except (IndexError, TypeError):
            return default


def activity_log_page():
    """
    Activity Log viewer with advanced filtering
    Only accessible to administrators
    """
    
    # Check admin permissions
    if not check_permission('Admin'):
        st.error("⛔ Access Denied: Administrator privileges required")
        return
    
    st.header("📜 Activity Log & Audit Trail")
    st.markdown("Complete audit trail of all user activities in the system")
    st.markdown("---")
    
    # Filter section
    with st.expander("🔍 Filter Options", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Get all unique usernames
            try:
                all_logs = AuditLogger.get_activity_logs(limit=10000)
                usernames = ["All Users"] + sorted(list(set([get_log_value(log, 'username') for log in all_logs if get_log_value(log, 'username')])))
            except Exception:
                usernames = ["All Users"]
            selected_user = st.selectbox("👤 User", usernames)
        
        with col2:
            action_types = [
                "All Actions",
                "Add",
                "Edit", 
                "Delete",
                "View",
                "Export",
                "Import",
                "Login",
                "Logout"
            ]
            selected_action = st.selectbox("⚡ Action Type", action_types)
        
        with col3:
            modules = [
                "All Modules",
                "Income",
                "Maintenance",
                "HR",
                "Employee",
                "Payroll",
                "Leave",
                "Disciplinary",
                "User Management",
                "System"
            ]
            selected_module = st.selectbox("📦 Module", modules)
        
        with col4:
            date_range = st.selectbox(
                "📅 Date Range",
                ["Today", "Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time", "Custom"]
            )
        
        # Custom date range
        if date_range == "Custom":
            col_a, col_b = st.columns(2)
            with col_a:
                start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
            with col_b:
                end_date = st.date_input("End Date", datetime.now())
        else:
            end_date = datetime.now().date()
            if date_range == "Today":
                start_date = end_date
            elif date_range == "Last 7 Days":
                start_date = end_date - timedelta(days=7)
            elif date_range == "Last 30 Days":
                start_date = end_date - timedelta(days=30)
            elif date_range == "Last 90 Days":
                start_date = end_date - timedelta(days=90)
            else:  # All Time
                start_date = None
        
        # Apply filters button
        if st.button("🔍 Apply Filters", width="stretch"):
            st.session_state['apply_log_filters'] = True
    
    st.markdown("---")
    
    # Fetch logs with filters
    username_filter = None if selected_user == "All Users" else selected_user
    action_filter = None if selected_action == "All Actions" else selected_action
    module_filter = None if selected_module == "All Modules" else selected_module
    start_date_str = start_date.strftime("%Y-%m-%d") if start_date else None
    end_date_str = end_date.strftime("%Y-%m-%d") if end_date else None
    
    try:
        logs = AuditLogger.get_activity_logs(
            username=username_filter,
            action_type=action_filter,
            module=module_filter,
            start_date=start_date_str,
            end_date=end_date_str,
            limit=5000
        )
    except Exception as e:
        st.warning(f"Unable to fetch activity logs: {e}")
        logs = []
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Activities", len(logs))
    
    with col2:
        unique_users = len(set([get_log_value(log, 'username') for log in logs])) if logs else 0
        st.metric("👥 Unique Users", unique_users)
    
    with col3:
        if logs:
            add_count = sum(1 for log in logs if get_log_value(log, 'action_type') == 'Add')
            st.metric("➕ Additions", add_count)
        else:
            st.metric("➕ Additions", 0)
    
    with col4:
        if logs:
            delete_count = sum(1 for log in logs if get_log_value(log, 'action_type') == 'Delete')
            st.metric("🗑️ Deletions", delete_count)
        else:
            st.metric("🗑️ Deletions", 0)
    
    st.markdown("---")
    
    # Display logs
    if logs:
        st.subheader(f"📋 Activity Records ({len(logs)} entries)")
        
        # Convert to DataFrame for better display
        df_data = []
        for log in logs:
            df_data.append({
                'ID': get_log_value(log, 'id'),
                'Timestamp': get_log_value(log, 'timestamp'),
                'User': get_log_value(log, 'username'),
                'Action': get_log_value(log, 'action_type'),
                'Module': get_log_value(log, 'module'),
                'Description': get_log_value(log, 'description')
            })
        
        df = pd.DataFrame(df_data)
        
        # Display with expandable details
        for idx, log in enumerate(logs):
            timestamp = get_log_value(log, 'timestamp')
            username = get_log_value(log, 'username')
            action_type = get_log_value(log, 'action_type')
            module = get_log_value(log, 'module')
            
            with st.expander(
                f"🔹 [{timestamp}] {username} - {action_type} in {module}"
            ):
                col_x, col_y = st.columns([2, 3])
                
                with col_x:
                    st.write("**Activity Details:**")
                    st.write(f"**ID:** {get_log_value(log, 'id')}")
                    st.write(f"**User:** {username}")
                    st.write(f"**Action:** {action_type}")
                    st.write(f"**Module:** {module}")
                    st.write(f"**Time:** {timestamp}")
                
                with col_y:
                    st.write("**Description:**")
                    st.info(get_log_value(log, 'description'))
                    
                    affected_table = get_log_value(log, 'affected_table')
                    if affected_table:
                        st.write(f"**Affected Table:** {affected_table}")
                    
                    affected_record_id = get_log_value(log, 'affected_record_id')
                    if affected_record_id:
                        st.write(f"**Record ID:** {affected_record_id}")
                
                # Show old and new values if available
                old_values = get_log_value(log, 'old_values')
                new_values = get_log_value(log, 'new_values')
                
                if old_values or new_values:
                    st.markdown("---")
                    col_old, col_new = st.columns(2)
                    
                    with col_old:
                        if old_values:
                            st.write("**Previous Values:**")
                            try:
                                old_vals = json.loads(old_values)
                                st.json(old_vals)
                            except Exception:
                                st.text(old_values)
                    
                    with col_new:
                        if new_values:
                            st.write("**New Values:**")
                            try:
                                new_vals = json.loads(new_values)
                                st.json(new_vals)
                            except Exception:
                                st.text(new_values)
        
        # Export options
        st.markdown("---")
        st.subheader("📥 Export Activity Log")
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            # Export to CSV
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="📄 Download as CSV",
                data=csv_data,
                file_name=f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                width="stretch"
            )
        
        with col_exp2:
            # Export to Excel
            st.download_button(
                label="📊 Download as Excel",
                data=df.to_csv(index=False),  # You can use openpyxl for true Excel format
                file_name=f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.ms-excel",
                width="stretch"
            )
    
    else:
        st.info("📭 No activity records found matching the selected filters.")
    
    # Recent activity summary
    st.markdown("---")
    st.subheader("📊 Activity Summary by User")
    
    if logs:
        # Group by user and action type
        summary_data = {}
        for log in logs:
            user = get_log_value(log, 'username')
            action = get_log_value(log, 'action_type')
            
            if user not in summary_data:
                summary_data[user] = {}
            
            if action not in summary_data[user]:
                summary_data[user][action] = 0
            
            summary_data[user][action] += 1
        
        # Display summary
        for user, actions in summary_data.items():
            with st.expander(f"👤 {user}"):
                summary_df = pd.DataFrame([
                    {"Action Type": action, "Count": count}
                    for action, count in actions.items()
                ])
                st.dataframe(summary_df, width="stretch")


def user_activity_dashboard():
    """
    Show current user's own activity history
    Accessible to all authenticated users
    """
    st.header("📊 My Activity History")
    st.markdown("View your recent actions in the system")
    st.markdown("---")
    
    user = st.session_state['user']
    username = user['username']
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        days_back = st.selectbox("Show activities from:", [7, 30, 90, 365], index=1)
    
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # Fetch user's activities
    try:
        logs = AuditLogger.get_activity_logs(
            username=username,
            start_date=start_date,
            limit=500
        )
    except Exception as e:
        st.warning(f"Unable to fetch activity logs: {e}")
        logs = []
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📊 Total Actions", len(logs))
    
    with col2:
        add_count = sum(1 for log in logs if get_log_value(log, 'action_type') == 'Add')
        st.metric("➕ Records Added", add_count)
    
    with col3:
        edit_count = sum(1 for log in logs if get_log_value(log, 'action_type') == 'Edit')
        st.metric("✏️ Records Edited", edit_count)
    
    st.markdown("---")
    
    # Display recent activities
    if logs:
        st.subheader("Recent Activities")
        for log in logs[:50]:  # Show last 50
            timestamp = get_log_value(log, 'timestamp')
            action_type = get_log_value(log, 'action_type')
            description = get_log_value(log, 'description')
            st.text(f"🔹 [{timestamp}] {action_type} - {description}")
    else:
        st.info("No recent activity found.")