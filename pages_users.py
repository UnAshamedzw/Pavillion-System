"""
pages_users.py - User Management Pages
Complete user account management with audit logging integration
"""

import streamlit as st
from auth import (
    register_user, get_all_users, update_user_status, 
    delete_user, change_password, check_permission
)
from audit_logger import AuditLogger
from datetime import datetime
from database import USE_POSTGRES


def get_user_value(user, key_or_index, default=None):
    """Get value from user row - works with both dict (PostgreSQL) and tuple (SQLite)"""
    if hasattr(user, 'keys'):
        # Dict-like (PostgreSQL)
        if isinstance(key_or_index, str):
            return user.get(key_or_index, default)
        else:
            # Map index to column name
            columns = ['id', 'username', 'full_name', 'role', 'email', 'created_at', 'last_login', 'is_active']
            if key_or_index < len(columns):
                return user.get(columns[key_or_index], default)
            return default
    else:
        # Tuple (SQLite)
        try:
            return user[key_or_index] if isinstance(key_or_index, int) else default
        except (IndexError, TypeError):
            return default


def unpack_user(user):
    """Unpack user row into tuple regardless of format"""
    if hasattr(user, 'keys'):
        return (
            user.get('id'),
            user.get('username'),
            user.get('full_name'),
            user.get('role'),
            user.get('email'),
            user.get('created_at'),
            user.get('last_login'),
            user.get('is_active')
        )
    else:
        return tuple(list(user) + [None] * (8 - len(user)))[:8]


def user_management_page():
    """
    Admin page for managing user accounts
    Full CRUD operations with audit logging
    """
    
    # Check if user has admin permissions
    if not check_permission('Admin'):
        st.error("⛔ You don't have permission to access this page. Admin access required.")
        return
    
    st.header("👥 User Management")
    st.markdown("Manage user accounts, roles, and permissions")
    st.markdown("---")
    
    # Tabs for different user management functions
    tab1, tab2, tab3 = st.tabs(["👥 All Users", "➕ Add New User", "🔑 Change Password"])
    
    with tab1:
        st.subheader("Registered Users")
        
        users = get_all_users()
        
        if users:
            # Summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Users", len(users))
            with col2:
                active_count = sum(1 for u in users if get_user_value(u, 'is_active') == 1 or get_user_value(u, 7) == 1)
                st.metric("✅ Active Users", active_count)
            with col3:
                admin_count = sum(1 for u in users if get_user_value(u, 'role') == 'Admin' or get_user_value(u, 3) == 'Admin')
                st.metric("👑 Administrators", admin_count)
            
            st.markdown("---")
            
            for user in users:
                user_id, username, full_name, role, email, created_at, last_login, is_active = unpack_user(user)
                
                # Status indicator
                status_icon = "✅" if is_active else "❌"
                
                with st.expander(f"{status_icon} {full_name} (@{username}) - {role}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Username:** {username}")
                        st.write(f"**Full Name:** {full_name}")
                        st.write(f"**Role:** {role}")
                        st.write(f"**Email:** {email or 'N/A'}")
                    
                    with col2:
                        st.write(f"**Created:** {created_at}")
                        st.write(f"**Last Login:** {last_login or 'Never'}")
                        st.write(f"**Status:** {'Active' if is_active else 'Inactive'}")
                        st.write(f"**User ID:** {user_id}")
                    
                    st.markdown("---")
                    
                    # Action buttons
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        # Prevent admin from deactivating themselves
                        if user_id != st.session_state['user']['id']:
                            if is_active:
                                if st.button(f"🚫 Deactivate", key=f"deactivate_{user_id}"):
                                    update_user_status(user_id, False)
                                    
                                    # Log the action
                                    AuditLogger.log_user_action(
                                        action_type="Edit",
                                        target_username=username,
                                        details="Account deactivated"
                                    )
                                    
                                    st.success(f"User {username} deactivated")
                                    st.rerun()
                            else:
                                if st.button(f"✅ Activate", key=f"activate_{user_id}"):
                                    update_user_status(user_id, True)
                                    
                                    # Log the action
                                    AuditLogger.log_user_action(
                                        action_type="Edit",
                                        target_username=username,
                                        details="Account activated"
                                    )
                                    
                                    st.success(f"User {username} activated")
                                    st.rerun()
                        else:
                            st.info("You cannot deactivate your own account")
                    
                    with col_b:
                        # Reset password button (admin feature)
                        if st.button(f"🔑 Reset Password", key=f"reset_{user_id}"):
                            st.session_state[f'show_reset_{user_id}'] = True
                        
                        if st.session_state.get(f'show_reset_{user_id}', False):
                            with st.form(f"reset_form_{user_id}"):
                                new_pwd = st.text_input("New Password", type="password")
                                confirm_pwd = st.text_input("Confirm Password", type="password")
                                
                                if st.form_submit_button("Reset Password"):
                                    if new_pwd == confirm_pwd and len(new_pwd) >= 6:
                                        from auth import hash_password
                                        from database import get_connection, USE_POSTGRES
                                        
                                        hashed_pwd, salt = hash_password(new_pwd)
                                        conn = get_connection()
                                        cursor = conn.cursor()
                                        if USE_POSTGRES:
                                            cursor.execute('''
                                                UPDATE users SET password_hash = %s, salt = %s 
                                                WHERE id = %s
                                            ''', (hashed_pwd, salt, user_id))
                                        else:
                                            cursor.execute('''
                                                UPDATE users SET password_hash = ?, salt = ? 
                                                WHERE id = ?
                                            ''', (hashed_pwd, salt, user_id))
                                        conn.commit()
                                        conn.close()
                                        
                                        # Log the action
                                        AuditLogger.log_user_action(
                                            action_type="Edit",
                                            target_username=username,
                                            details="Password reset by administrator"
                                        )
                                        
                                        st.success("Password reset successfully!")
                                        st.session_state[f'show_reset_{user_id}'] = False
                                        st.rerun()
                                    else:
                                        st.error("Passwords don't match or too short")
                    
                    with col_c:
                        # Prevent admin from deleting themselves
                        if user_id != st.session_state['user']['id']:
                            if st.button(f"🗑️ Delete", key=f"delete_{user_id}", type="secondary"):
                                if st.session_state.get(f'confirm_delete_{user_id}', False):
                                    delete_user(user_id)
                                    
                                    # Log the action
                                    AuditLogger.log_user_action(
                                        action_type="Delete",
                                        target_username=username,
                                        details="User account deleted"
                                    )
                                    
                                    st.success(f"User {username} deleted")
                                    st.rerun()
                                else:
                                    st.session_state[f'confirm_delete_{user_id}'] = True
                                    st.warning("Click again to confirm deletion")
                        else:
                            st.info("You cannot delete your own account")
        else:
            st.info("No users found in the system")
    
    with tab2:
        st.subheader("Add New User")
        st.markdown("Create a new user account with role-based permissions")
        
        with st.form("new_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input(
                    "Username*", 
                    help="Unique username for login (no spaces)",
                    placeholder="e.g., john_doe"
                )
                new_full_name = st.text_input(
                    "Full Name*",
                    placeholder="e.g., John Doe"
                )
                new_email = st.text_input(
                    "Email",
                    help="Optional",
                    placeholder="e.g., john@example.com"
                )
            
            with col2:
                new_role = st.selectbox(
                    "Role*", 
                    ["User", "Manager", "Admin"],
                    help="Admin: Full access | Manager: Operations & HR | User: Basic access"
                )
                new_password = st.text_input(
                    "Password*", 
                    type="password",
                    help="Minimum 6 characters"
                )
                confirm_password = st.text_input(
                    "Confirm Password*", 
                    type="password"
                )
            
            st.markdown("---")
            st.markdown("**Role Permissions:**")
            
            col_perm1, col_perm2, col_perm3 = st.columns(3)
            with col_perm1:
                st.info("**User:**\n- View records\n- Add income\n- Add maintenance")
            with col_perm2:
                st.info("**Manager:**\n- All User permissions\n- Edit records\n- HR management")
            with col_perm3:
                st.info("**Admin:**\n- All permissions\n- User management\n- System settings")
            
            submitted = st.form_submit_button("➕ Create User", width="stretch", type="primary")
            
            if submitted:
                # Validation
                if not all([new_username, new_full_name, new_password, confirm_password]):
                    st.error("⚠️ Please fill in all required fields")
                elif ' ' in new_username:
                    st.error("⚠️ Username cannot contain spaces")
                elif new_password != confirm_password:
                    st.error("⚠️ Passwords do not match")
                elif len(new_password) < 6:
                    st.error("⚠️ Password must be at least 6 characters long")
                else:
                    # Try to register user
                    success = register_user(
                        username=new_username,
                        password=new_password,
                        full_name=new_full_name,
                        role=new_role,
                        email=new_email if new_email else None
                    )
                    
                    if success:
                        # Log the action
                        AuditLogger.log_user_action(
                            action_type="Add",
                            target_username=new_username,
                            details=f"New {new_role} account created: {new_full_name}"
                        )
                        
                        st.success(f"✅ User '{new_username}' created successfully!")
                        st.balloons()
                        
                        # Show credentials
                        st.info(f"""
                        **Account Created:**
                        - Username: `{new_username}`
                        - Password: `{new_password}`
                        - Role: {new_role}
                        
                        Please share these credentials with the user securely.
                        """)
                    else:
                        st.error("❌ Username already exists. Please choose a different username.")
    
    with tab3:
        st.subheader("Change Your Password")
        st.markdown("Update your password for security")
        
        with st.form("change_password_form"):
            old_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password", help="Minimum 6 characters")
            confirm_new_password = st.text_input("Confirm New Password", type="password")
            
            st.markdown("---")
            st.markdown("**Password Requirements:**")
            st.markdown("- ✅ Minimum 6 characters\n- ✅ Must not match current password")
            
            submitted = st.form_submit_button("🔑 Change Password", width="stretch", type="primary")
            
            if submitted:
                if not all([old_password, new_password, confirm_new_password]):
                    st.error("⚠️ Please fill in all fields")
                elif new_password != confirm_new_password:
                    st.error("⚠️ New passwords do not match")
                elif len(new_password) < 6:
                    st.error("⚠️ Password must be at least 6 characters long")
                elif old_password == new_password:
                    st.error("⚠️ New password must be different from current password")
                else:
                    success = change_password(
                        user_id=st.session_state['user']['id'],
                        old_password=old_password,
                        new_password=new_password
                    )
                    
                    if success:
                        # Log the action
                        AuditLogger.log_action(
                            action_type="Edit",
                            module="User Management",
                            description="Password changed successfully"
                        )
                        
                        st.success("✅ Password changed successfully!")
                        st.info("Please use your new password for future logins.")
                    else:
                        st.error("❌ Current password is incorrect")


def my_profile_page():
    """
    Page for users to view and edit their profile
    Accessible to all authenticated users
    """
    st.header("👤 My Profile")
    st.markdown("View and manage your account information")
    st.markdown("---")
    
    user = st.session_state['user']
    
    # Profile display
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Avatar placeholder
        st.markdown("### 👤")
        st.markdown(f"### {user['full_name']}")
    
    with col2:
        st.markdown("### Account Information")
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.write(f"**Username:** {user['username']}")
            st.write(f"**Role:** {user['role']}")
        
        with info_col2:
            st.write(f"**Email:** {user.get('email', 'Not set')}")
            st.write(f"**User ID:** {user['id']}")
    
    st.markdown("---")
    
    # Role permissions display
    st.subheader("🔐 Your Permissions")
    
    role = user['role']
    
    if role == 'Admin':
        st.success("""
        **Administrator - Full Access**
        - ✅ All operations (Income, Maintenance)
        - ✅ All HR functions
        - ✅ User management
        - ✅ Activity logs and audit trail
        - ✅ System configuration
        - ✅ Bus analysis and reports
        """)
    elif role == 'Manager':
        st.info("""
        **Manager - Extended Access**
        - ✅ All operations (Income, Maintenance)
        - ✅ All HR functions
        - ✅ Bus analysis and reports
        - ✅ Data import/export
        - ❌ User management (Admin only)
        - ❌ System activity logs (Admin only)
        """)
    else:  # User
        st.warning("""
        **User - Standard Access**
        - ✅ View operations data
        - ✅ Add income records
        - ✅ Add maintenance records
        - ✅ View own activity
        - ❌ Edit/delete records (Manager/Admin only)
        - ❌ HR functions (Manager/Admin only)
        - ❌ User management (Admin only)
        """)
    
    st.markdown("---")
    
    # Quick password change
    with st.expander("🔑 Change Password", expanded=False):
        with st.form("quick_password_change"):
            old_pwd = st.text_input("Current Password", type="password", key="profile_old_pwd")
            new_pwd = st.text_input("New Password", type="password", key="profile_new_pwd", 
                                    help="Minimum 6 characters")
            confirm_pwd = st.text_input("Confirm New Password", type="password", key="profile_confirm_pwd")
            
            if st.form_submit_button("Update Password", type="primary"):
                if new_pwd == confirm_pwd and len(new_pwd) >= 6:
                    if change_password(user['id'], old_pwd, new_pwd):
                        # Log the action
                        AuditLogger.log_action(
                            action_type="Edit",
                            module="User Management",
                            description="Password changed from profile page"
                        )
                        
                        st.success("✅ Password updated successfully!")
                    else:
                        st.error("❌ Current password is incorrect")
                else:
                    st.error("⚠️ Passwords don't match or are too short (min 6 characters)")
    
    st.markdown("---")
    
    # Activity summary
    st.subheader("📊 Your Activity Summary")
    
    username = user['username']
    summary = AuditLogger.get_user_activity_summary(username)
    
    if summary:
        col_sum1, col_sum2, col_sum3 = st.columns(3)
        
        # Display top 3 activities
        for idx, (action_type, count) in enumerate(summary[:3]):
            if idx == 0:
                with col_sum1:
                    st.metric(f"{action_type} Actions", count)
            elif idx == 1:
                with col_sum2:
                    st.metric(f"{action_type} Actions", count)
            else:
                with col_sum3:
                    st.metric(f"{action_type} Actions", count)
        
        # Full activity breakdown
        with st.expander("📋 View Full Activity Breakdown"):
            import pandas as pd
            
            df = pd.DataFrame(summary, columns=['Action Type', 'Count'])
            st.dataframe(df, width="stretch")
            
            # Link to full activity page
            st.info("💡 View your complete activity history in **System → My Activity**")
    else:
        st.info("No activity recorded yet. Start using the system to see your activity here!")
    
    st.markdown("---")
    
    # Account statistics
    st.subheader("📈 Account Statistics")
    
    # Get user's first login and total activities
    from database import get_connection, USE_POSTGRES
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get account creation date
    if USE_POSTGRES:
        cursor.execute('SELECT created_at, last_login FROM users WHERE id = %s', (user['id'],))
    else:
        cursor.execute('SELECT created_at, last_login FROM users WHERE id = ?', (user['id'],))
    account_info = cursor.fetchone()
    
    # Get total activity count
    if USE_POSTGRES:
        cursor.execute('SELECT COUNT(*) FROM activity_log WHERE username = %s', (username,))
    else:
        cursor.execute('SELECT COUNT(*) FROM activity_log WHERE username = ?', (username,))
    result = cursor.fetchone()
    total_activities = result['count'] if hasattr(result, 'keys') else result[0]
    
    conn.close()
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        if account_info:
            created = account_info.get('created_at') if hasattr(account_info, 'keys') else account_info[0]
            if created:
                st.metric("📅 Member Since", str(created)[:10])
    
    with col_stat2:
        if account_info:
            last_login = account_info.get('last_login') if hasattr(account_info, 'keys') else account_info[1]
            if last_login:
                st.metric("🕐 Last Login", str(last_login)[:16])
            else:
                st.metric("🕐 Last Login", "Current session")
        else:
            st.metric("🕐 Last Login", "Current session")
    
    with col_stat3:
        st.metric("⚡ Total Activities", total_activities)