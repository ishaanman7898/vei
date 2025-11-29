import streamlit as st
import time
import pandas as pd
import os
import json
import jwt
from simple_auth import verify_login

def load_access_control():
    """Load the secure access CSV file"""
    ACCESS_CONTROL_CSV = "Secure Access - Thrive Tools - Sheet1.csv"
    if os.path.exists(ACCESS_CONTROL_CSV):
        df = pd.read_csv(ACCESS_CONTROL_CSV)
        df = df.dropna(how='all')
        return df
    return None

def get_user_permissions(email):
    """Get user permissions from the access control CSV"""
    df = load_access_control()
    
    if df is None:
        return None
    
    # Find user by email
    user_row = df[df['Email'].str.lower() == email.lower()]
    
    if user_row.empty:
        return None
    
    # Get permissions
    user_data = user_row.iloc[0]
    permissions = {
        "name": user_data.get('Name', 'Unknown User'),
        "email": email,
        "permissions": {
            "inventory_management": user_data.get('Inventory Management', False) == True or str(user_data.get('Inventory Management', '')).upper() == 'TRUE',
            "product_management": user_data.get('Product Management', False) == True or str(user_data.get('Product Management', '')).upper() == 'TRUE',
            "email_sender": user_data.get('Email Management', False) == True or str(user_data.get('Email Management', '')).upper() == 'TRUE',
            "user_management": user_data.get('User/Admin Permissions', False) == True or str(user_data.get('User/Admin Permissions', '')).upper() == 'TRUE',
        },
        "is_admin": str(user_data.get('Notes', '')).strip().upper() == 'ADMIN'
    }
    
    return permissions

def check_authentication():
    """
    Authentication using email/password only
    """
    
    # Check if already authenticated
    if st.session_state.get("authenticated", False):
        return True
    
    # Display login UI
    st.markdown("<h1 style='text-align: center;'>🔐 Thrive Tools</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #666;'>Sign in to continue</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Email/password login form
        st.markdown("### 📧 Sign in with email/password")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your@email.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Enter password", key="login_password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("❌ Please enter both email and password")
                else:
                    # Try to verify login with email/password
                    user_data = verify_login(email, password)
                    
                    if user_data:
                        # Check if user exists in access control CSV
                        csv_permissions = get_user_permissions(email)
                        
                        if csv_permissions:
                            # Use permissions from CSV (override auth_users.json)
                            user_data = csv_permissions
                        
                        # Check if user has at least one permission
                        has_any_permission = any(user_data.get('permissions', {}).values())
                        
                        if not has_any_permission:
                            st.error(f"❌ Access Denied: You have no permissions assigned.")
                            st.info("Please contact your administrator to request permissions.")
                        else:
                            # Successful login
                            user_data['email'] = email
                            st.session_state.authenticated = True
                            st.session_state.current_user = user_data
                            
                            st.success(f"✅ Welcome back, {user_data['name']}!")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("❌ Invalid email or password")
        
        st.caption("Need access? Contact your administrator.")
    
    return False

def get_current_user():
    """Get currently logged in user"""
    return st.session_state.get("current_user")

def check_permission(permission_name):
    """Check if current user has specific permission"""
    user = get_current_user()
    if user is None:
        return False
    return user.get("permissions", {}).get(permission_name, False)
