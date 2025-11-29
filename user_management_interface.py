import streamlit as st
import time
from simple_auth import (
    get_all_auth_users,
    update_user_permissions,
    delete_user,
    register_user,
    hash_password,
    load_auth_users,
    save_auth_users
)

def show_user_management():
    """User management interface for simple auth"""
    st.title("User Management")
    st.caption("Manage user accounts and permissions")
    
    # Tabs for different actions
    tab1, tab2 = st.tabs(["👥 View Users", "➕ Add New User"])
    
    # --- VIEW USERS ---
    with tab1:
        st.subheader("Current Users")
        
        users = get_all_auth_users()
        
        if not users:
            st.info("No users found")
        else:
            for user in users:
                email = user['email']
                name = user['name']
                perms = user['permissions']
                
                with st.expander(f"👤 {name} - {email}", expanded=False):
                    st.write(f"**Email:** {email}")
                    st.write(f"**Name:** {name}")
                    
                    st.markdown("#### Permissions")
                    
                    # Permission toggles
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        inventory = st.checkbox(
                            "📦 Inventory Management",
                            value=perms.get('inventory_management', False),
                            key=f"inv_{email}"
                        )
                        email_sender = st.checkbox(
                            "📧 Email Sender",
                            value=perms.get('email_sender', False),
                            key=f"email_{email}"
                        )
                    
                    with col2:
                        product = st.checkbox(
                            "🛍️ Product Management",
                            value=perms.get('product_management', False),
                            key=f"prod_{email}"
                        )
                        user_mgmt = st.checkbox(
                            "👥 User Management",
                            value=perms.get('user_management', False),
                            key=f"user_{email}"
                        )
                    
                    st.markdown("---")
                    
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        if st.button("💾 Save Permissions", key=f"save_{email}", use_container_width=True):
                            new_permissions = {
                                "inventory_management": inventory,
                                "email_sender": email_sender,
                                "product_management": product,
                                "user_management": user_mgmt
                            }
                            if update_user_permissions(email, new_permissions):
                                st.success("✅ Permissions updated!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Failed to update permissions")
                    
                    with col_b:
                        # Reset password
                        with st.popover("🔑 Reset Password"):
                            new_pwd = st.text_input("New Password", type="password", key=f"newpwd_{email}")
                            if st.button("Reset", key=f"reset_{email}"):
                                if new_pwd and len(new_pwd) >= 6:
                                    users_db = load_auth_users()
                                    users_db[email]["password_hash"] = hash_password(new_pwd)
                                    save_auth_users(users_db)
                                    st.success("✅ Password reset!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Password must be at least 6 characters")
                    
                    with col_c:
                        if email != "admin@thrive.com":  # Don't allow deleting admin
                            if st.button("🗑️ Delete User", key=f"del_{email}", use_container_width=True):
                                if delete_user(email):
                                    st.success("User deleted")
                                    time.sleep(1)
                                    st.rerun()
                        else:
                            st.caption("(Admin cannot be deleted)")
    
    # --- ADD NEW USER ---
    with tab2:
        st.subheader("Add New User")
        
        with st.form("add_user_form"):
            name = st.text_input("Full Name*", placeholder="John Doe")
            email = st.text_input("Email*", placeholder="user@example.com")
            password = st.text_input("Password*", type="password", placeholder="Minimum 6 characters")
            
            st.markdown("#### Permissions")
            st.caption("Select which modules this user can access")
            
            col1, col2 = st.columns(2)
            
            with col1:
                perm_inv = st.checkbox("📦 Inventory Management", value=True, key="new_inv")
                perm_email = st.checkbox("📧 Email Sender", value=True, key="new_email")
            
            with col2:
                perm_prod = st.checkbox("🛍️ Product Management", value=True, key="new_prod")
                perm_user = st.checkbox("👥 User Management", value=True, key="new_user")
            
            submitted = st.form_submit_button("Add User", type="primary", use_container_width=True)
            
            if submitted:
                if not name or not email or not password:
                    st.error("All fields are required!")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters!")
                else:
                    # Create user with selected permissions
                    success, message = register_user(email, password, name)
                    
                    if success:
                        # Update permissions if not default
                        permissions = {
                            "inventory_management": perm_inv,
                            "email_sender": perm_email,
                            "product_management": perm_prod,
                            "user_management": perm_user
                        }
                        update_user_permissions(email, permissions)
                        
                        st.success(f"✅ User added successfully!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
