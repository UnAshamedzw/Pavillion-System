"""
pages_users.py - User and Role Management Pages
Complete user account and role/permission management
"""

import streamlit as st
from auth import (
    register_user, get_all_users, update_user_status, 
    delete_user, change_password, reset_user_password,
    update_user_role, update_user_info,
    has_permission, require_permission,
    get_available_roles, get_all_roles, get_role_permissions_by_name,
    create_custom_role, delete_role, update_role_permissions, get_role_permissions,
    grant_user_permission, revoke_user_permission, get_user_permission_overrides,
    clear_user_permission_overrides,
    ALL_PERMISSIONS, PERMISSION_CATEGORIES, PREDEFINED_ROLES
)
from audit_logger import AuditLogger
from datetime import datetime
from database import USE_POSTGRES


def get_user_value(user, key_or_index, default=None):
    """Get value from user row - works with both dict (PostgreSQL) and tuple (SQLite)"""
    if hasattr(user, 'keys'):
        if isinstance(key_or_index, str):
            return user.get(key_or_index, default)
        else:
            columns = ['id', 'username', 'full_name', 'role', 'email', 'created_at', 'last_login', 'is_active']
            if key_or_index < len(columns):
                return user.get(columns[key_or_index], default)
            return default
    else:
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
    """Admin page for managing user accounts"""
    
    if not has_permission('view_users'):
        st.error("⛔ You don't have permission to access this page.")
        return
    
    st.header("👥 User Management")
    st.markdown("Manage user accounts, roles, and permissions")
    st.markdown("---")
    
    # Tabs for different user management functions
    tab1, tab2, tab3, tab4 = st.tabs(["👥 All Users", "➕ Add New User", "🔑 Reset Password", "🔒 User Permissions"])
    
    with tab1:
        st.subheader("Registered Users")
        
        users = get_all_users()
        
        if users:
            # Summary stats
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Total Users", len(users))
            with col2:
                active_count = sum(1 for u in users if get_user_value(u, 'is_active') == 1 or get_user_value(u, 7) == 1)
                st.metric("✅ Active Users", active_count)
            with col3:
                admin_count = sum(1 for u in users if get_user_value(u, 'role') == 'System Admin' or get_user_value(u, 3) == 'System Admin')
                st.metric("👑 System Admins", admin_count)
            with col4:
                director_count = sum(1 for u in users if get_user_value(u, 'role') == 'Director' or get_user_value(u, 3) == 'Director')
                st.metric("🎯 Directors", director_count)
            
            st.markdown("---")
            
            # Filter options
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                filter_role = st.selectbox("Filter by Role", ["All Roles"] + get_available_roles())
            with col_filter2:
                filter_status = st.selectbox("Filter by Status", ["All", "Active Only", "Inactive Only"])
            
            for user in users:
                user_id, username, full_name, role, email, created_at, last_login, is_active = unpack_user(user)
                
                # Apply filters
                if filter_role != "All Roles" and role != filter_role:
                    continue
                if filter_status == "Active Only" and not is_active:
                    continue
                if filter_status == "Inactive Only" and is_active:
                    continue
                
                status_icon = "✅" if is_active else "❌"
                role_icon = "👑" if role == "System Admin" else "🎯" if role == "Director" else "👤"
                
                with st.expander(f"{status_icon} {role_icon} {full_name} (@{username}) - {role}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Username:** {username}")
                        st.write(f"**Full Name:** {full_name}")
                        st.write(f"**Email:** {email or 'Not set'}")
                        st.write(f"**Role:** {role}")
                        st.write(f"**Status:** {'Active' if is_active else 'Inactive'}")
                    
                    with col2:
                        st.write(f"**Created:** {created_at}")
                        st.write(f"**Last Login:** {last_login or 'Never'}")
                        
                        # Role-specific permissions preview
                        if role in PREDEFINED_ROLES:
                            perm_count = len(PREDEFINED_ROLES[role]['permissions'])
                            st.write(f"**Permissions:** {perm_count} permissions")
                    
                    st.markdown("---")
                    
                    # Action buttons
                    col_a, col_b, col_c, col_d = st.columns(4)
                    
                    # Edit user info
                    with col_a:
                        if has_permission('edit_user'):
                            if st.button("✏️ Edit", key=f"edit_{user_id}"):
                                st.session_state[f'editing_user_{user_id}'] = True
                                st.rerun()
                    
                    # Change role
                    with col_b:
                        if has_permission('edit_user'):
                            new_role = st.selectbox(
                                "Change Role",
                                get_available_roles(),
                                index=get_available_roles().index(role) if role in get_available_roles() else 0,
                                key=f"role_{user_id}"
                            )
                            if new_role != role:
                                if st.button("💾 Save Role", key=f"save_role_{user_id}"):
                                    if update_user_role(user_id, new_role):
                                        AuditLogger.log_action(
                                            "Update", "User Management",
                                            f"Changed role for {username} from {role} to {new_role}"
                                        )
                                        st.success(f"✅ Role updated to {new_role}")
                                        st.rerun()
                    
                    # Toggle status
                    with col_c:
                        if has_permission('edit_user'):
                            if is_active:
                                if st.button("🚫 Deactivate", key=f"deact_{user_id}"):
                                    update_user_status(user_id, False)
                                    AuditLogger.log_action(
                                        "Update", "User Management",
                                        f"Deactivated user: {username}"
                                    )
                                    st.success(f"User {username} deactivated")
                                    st.rerun()
                            else:
                                if st.button("✅ Activate", key=f"act_{user_id}"):
                                    update_user_status(user_id, True)
                                    AuditLogger.log_action(
                                        "Update", "User Management",
                                        f"Activated user: {username}"
                                    )
                                    st.success(f"User {username} activated")
                                    st.rerun()
                    
                    # Delete user
                    with col_d:
                        if has_permission('delete_user'):
                            if st.button("🗑️ Delete", key=f"del_{user_id}"):
                                st.session_state[f'confirm_delete_{user_id}'] = True
                    
                    # Confirm delete dialog
                    if st.session_state.get(f'confirm_delete_{user_id}', False):
                        st.warning(f"⚠️ Are you sure you want to delete user '{username}'?")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("✅ Yes, Delete", key=f"confirm_yes_{user_id}"):
                                delete_user(user_id)
                                AuditLogger.log_action(
                                    "Delete", "User Management",
                                    f"Deleted user: {username}"
                                )
                                st.success(f"User {username} deleted")
                                del st.session_state[f'confirm_delete_{user_id}']
                                st.rerun()
                        with col_no:
                            if st.button("❌ Cancel", key=f"confirm_no_{user_id}"):
                                del st.session_state[f'confirm_delete_{user_id}']
                                st.rerun()
                    
                    # Edit user form
                    if st.session_state.get(f'editing_user_{user_id}', False):
                        st.markdown("---")
                        st.subheader("Edit User Information")
                        with st.form(f"edit_user_form_{user_id}"):
                            new_full_name = st.text_input("Full Name", value=full_name)
                            new_email = st.text_input("Email", value=email or "")
                            
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                save_btn = st.form_submit_button("💾 Save Changes", type="primary")
                            with col_cancel:
                                cancel_btn = st.form_submit_button("❌ Cancel")
                            
                            if save_btn:
                                if update_user_info(user_id, new_full_name, new_email):
                                    AuditLogger.log_action(
                                        "Update", "User Management",
                                        f"Updated info for user: {username}"
                                    )
                                    st.success("✅ User updated successfully!")
                                    del st.session_state[f'editing_user_{user_id}']
                                    st.rerun()
                                else:
                                    st.error("Failed to update user")
                            
                            if cancel_btn:
                                del st.session_state[f'editing_user_{user_id}']
                                st.rerun()
        else:
            st.info("No users found")
    
    with tab2:
        st.subheader("➕ Add New User")
        
        if not has_permission('add_user'):
            st.warning("You don't have permission to add new users")
        else:
            with st.form("add_user_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_username = st.text_input("Username*", placeholder="e.g., jsmith")
                    new_password = st.text_input("Password*", type="password", placeholder="Minimum 6 characters")
                    confirm_password = st.text_input("Confirm Password*", type="password")
                
                with col2:
                    new_full_name = st.text_input("Full Name*", placeholder="e.g., John Smith")
                    new_email = st.text_input("Email", placeholder="e.g., john@pavillion.com")
                    new_role = st.selectbox("Role*", get_available_roles())
                
                # Show role description
                if new_role in PREDEFINED_ROLES:
                    st.info(f"**{new_role}:** {PREDEFINED_ROLES[new_role]['description']}")
                
                submitted = st.form_submit_button("➕ Create User", type="primary", use_container_width=True)
                
                if submitted:
                    if not new_username or not new_password or not new_full_name:
                        st.error("Please fill in all required fields")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        if register_user(new_username, new_password, new_full_name, new_role, new_email):
                            AuditLogger.log_action(
                                "Create", "User Management",
                                f"Created new user: {new_username} with role {new_role}"
                            )
                            st.success(f"✅ User '{new_username}' created successfully!")
                            st.rerun()
                        else:
                            st.error("Username already exists or error creating user")
    
    with tab3:
        st.subheader("🔑 Reset User Password")
        
        if not has_permission('reset_passwords'):
            st.warning("You don't have permission to reset passwords")
        else:
            users = get_all_users()
            if users:
                user_options = {f"{unpack_user(u)[2]} (@{unpack_user(u)[1]})": unpack_user(u)[0] for u in users}
                selected_user = st.selectbox("Select User", list(user_options.keys()))
                
                if selected_user:
                    with st.form("reset_password_form"):
                        new_password = st.text_input("New Password", type="password")
                        confirm_password = st.text_input("Confirm New Password", type="password")
                        
                        submitted = st.form_submit_button("🔑 Reset Password", type="primary")
                        
                        if submitted:
                            if not new_password:
                                st.error("Please enter a new password")
                            elif len(new_password) < 6:
                                st.error("Password must be at least 6 characters")
                            elif new_password != confirm_password:
                                st.error("Passwords do not match")
                            else:
                                user_id = user_options[selected_user]
                                if reset_user_password(user_id, new_password):
                                    AuditLogger.log_action(
                                        "Update", "User Management",
                                        f"Reset password for user: {selected_user}"
                                    )
                                    st.success(f"✅ Password reset successfully for {selected_user}")
                                else:
                                    st.error("Failed to reset password")
    
    with tab4:
        st.subheader("🔒 User Permission Overrides")
        st.info("Grant or revoke specific permissions for individual users. These override their role's default permissions.")
        
        if not has_permission('manage_roles'):
            st.warning("You don't have permission to manage user permissions")
        else:
            users = get_all_users()
            if users:
                user_options = {f"{unpack_user(u)[2]} (@{unpack_user(u)[1]}) - {unpack_user(u)[3]}": unpack_user(u)[0] for u in users}
                selected_user = st.selectbox("Select User", list(user_options.keys()), key="perm_user_select")
                
                if selected_user:
                    user_id = user_options[selected_user]
                    
                    # Get current overrides
                    overrides = get_user_permission_overrides(user_id)
                    
                    if overrides:
                        st.markdown("**Current Overrides:**")
                        for perm, granted in overrides.items():
                            status = "✅ Granted" if granted else "❌ Revoked"
                            st.write(f"- `{perm}`: {status}")
                        
                        if st.button("🗑️ Clear All Overrides"):
                            clear_user_permission_overrides(user_id)
                            st.success("All permission overrides cleared")
                            st.rerun()
                    
                    st.markdown("---")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Grant Additional Permission:**")
                        grant_perm = st.selectbox("Permission to Grant", list(ALL_PERMISSIONS.keys()), key="grant_perm")
                        if st.button("✅ Grant Permission"):
                            grant_user_permission(user_id, grant_perm)
                            AuditLogger.log_action(
                                "Update", "Permissions",
                                f"Granted {grant_perm} to user ID {user_id}"
                            )
                            st.success(f"Permission `{grant_perm}` granted")
                            st.rerun()
                    
                    with col2:
                        st.markdown("**Revoke Permission:**")
                        revoke_perm = st.selectbox("Permission to Revoke", list(ALL_PERMISSIONS.keys()), key="revoke_perm")
                        if st.button("❌ Revoke Permission"):
                            revoke_user_permission(user_id, revoke_perm)
                            AuditLogger.log_action(
                                "Update", "Permissions",
                                f"Revoked {revoke_perm} from user ID {user_id}"
                            )
                            st.success(f"Permission `{revoke_perm}` revoked")
                            st.rerun()


def role_management_page():
    """Page for managing roles and their permissions"""
    
    if not has_permission('manage_roles'):
        st.error("⛔ You don't have permission to access this page.")
        return
    
    st.header("🔐 Role Management")
    st.markdown("Manage roles and their associated permissions")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📋 View Roles", "➕ Create Role", "📊 Permission Matrix"])
    
    with tab1:
        st.subheader("All Roles")
        
        for role_name, role_data in PREDEFINED_ROLES.items():
            is_system = role_data['is_system_role']
            can_modify = role_data['can_be_modified']
            
            icon = "👑" if role_name == "System Admin" else "🎯" if role_name == "Director" else "👤"
            system_badge = "🔒 System Role" if is_system else "✏️ Customizable"
            
            with st.expander(f"{icon} {role_name} ({system_badge})"):
                st.write(f"**Description:** {role_data['description']}")
                st.write(f"**Permissions:** {len(role_data['permissions'])}")
                
                if not is_system:
                    st.markdown("---")
                    st.markdown("**Permissions:**")
                    
                    # Group permissions by category
                    for category, perms in PERMISSION_CATEGORIES.items():
                        role_perms = [p for p in perms if p in role_data['permissions']]
                        if role_perms:
                            st.markdown(f"*{category}:*")
                            for perm in role_perms:
                                st.write(f"  - `{perm}`: {ALL_PERMISSIONS[perm]}")
                else:
                    st.info("System roles cannot be modified. They have predefined permissions.")
    
    with tab2:
        st.subheader("➕ Create Custom Role")
        
        with st.form("create_role_form"):
            role_name = st.text_input("Role Name*", placeholder="e.g., Shift Supervisor")
            role_description = st.text_area("Description", placeholder="Describe the role's responsibilities")
            
            st.markdown("**Select Permissions:**")
            
            selected_permissions = []
            
            for category, perms in PERMISSION_CATEGORIES.items():
                st.markdown(f"**{category}**")
                cols = st.columns(3)
                for i, perm in enumerate(perms):
                    with cols[i % 3]:
                        if st.checkbox(f"`{perm}`", key=f"create_{perm}", help=ALL_PERMISSIONS[perm]):
                            selected_permissions.append(perm)
            
            submitted = st.form_submit_button("➕ Create Role", type="primary")
            
            if submitted:
                if not role_name:
                    st.error("Please enter a role name")
                elif role_name in PREDEFINED_ROLES:
                    st.error("A role with this name already exists")
                elif not selected_permissions:
                    st.error("Please select at least one permission")
                else:
                    if create_custom_role(role_name, role_description, selected_permissions):
                        AuditLogger.log_action(
                            "Create", "Role Management",
                            f"Created custom role: {role_name} with {len(selected_permissions)} permissions"
                        )
                        st.success(f"✅ Role '{role_name}' created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create role")
    
    with tab3:
        st.subheader("📊 Permission Matrix")
        st.info("Overview of all permissions by role")
        
        # Create a matrix view
        roles = list(PREDEFINED_ROLES.keys())[:6]  # Show first 6 roles for display
        
        for category, perms in PERMISSION_CATEGORIES.items():
            st.markdown(f"### {category}")
            
            # Create header row
            header = "| Permission |"
            separator = "|------------|"
            for role in roles:
                short_role = role.replace(" Manager", "").replace(" Supervisor", "")[:10]
                header += f" {short_role} |"
                separator += ":---------:|"
            
            st.markdown(header)
            st.markdown(separator)
            
            # Create data rows
            for perm in perms:
                row = f"| `{perm}` |"
                for role in roles:
                    has_perm = perm in PREDEFINED_ROLES[role]['permissions']
                    row += " ✅ |" if has_perm else " ❌ |"
                st.markdown(row)


def my_profile_page():
    """User profile page - available to all users"""
    
    st.header("👤 My Profile")
    
    user = st.session_state.get('user', {})
    
    if not user:
        st.error("Not logged in")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Profile Information")
        st.write(f"**Username:** {user.get('username', 'N/A')}")
        st.write(f"**Full Name:** {user.get('full_name', 'N/A')}")
        st.write(f"**Email:** {user.get('email', 'Not set')}")
        st.write(f"**Role:** {user.get('role', 'N/A')}")
        
        # Show role description
        role = user.get('role', '')
        if role in PREDEFINED_ROLES:
            st.info(f"**Role Description:** {PREDEFINED_ROLES[role]['description']}")
    
    with col2:
        st.subheader("🔑 Change Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            submitted = st.form_submit_button("🔐 Change Password", type="primary")
            
            if submitted:
                if not current_password or not new_password:
                    st.error("Please fill in all fields")
                elif len(new_password) < 6:
                    st.error("New password must be at least 6 characters")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                else:
                    if change_password(user['id'], current_password, new_password):
                        AuditLogger.log_action(
                            "Update", "Profile",
                            f"User changed their password"
                        )
                        st.success("✅ Password changed successfully!")
                    else:
                        st.error("Current password is incorrect")
    
    st.markdown("---")
    
    # Show user's permissions
    st.subheader("🔒 My Permissions")
    
    role = user.get('role', '')
    if role == 'System Admin':
        st.success("**System Admin** - You have access to ALL features and permissions.")
    elif role in PREDEFINED_ROLES:
        permissions = PREDEFINED_ROLES[role]['permissions']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Permissions", len(permissions))
        
        with col2:
            # Count by category
            categories_with_access = sum(1 for cat, perms in PERMISSION_CATEGORIES.items() 
                                         if any(p in permissions for p in perms))
            st.metric("Categories Access", f"{categories_with_access}/{len(PERMISSION_CATEGORIES)}")
        
        with st.expander("View All My Permissions"):
            for category, perms in PERMISSION_CATEGORIES.items():
                my_perms = [p for p in perms if p in permissions]
                if my_perms:
                    st.markdown(f"**{category}:**")
                    for perm in my_perms:
                        st.write(f"  - `{perm}`: {ALL_PERMISSIONS[perm]}")
    else:
        st.info("Contact your administrator to view your permissions.")