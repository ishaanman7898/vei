import streamlit as st
import json
import time
from simple_auth import update_user_config, get_user_config

def show_user_settings():
    st.title("⚙️ My Settings")
    st.caption("Manage your personal credentials for Email and Inventory tools.")
    
    # Check for success messages from previous run
    if "settings_success" in st.session_state:
        st.success(st.session_state.settings_success)
        del st.session_state.settings_success
    
    user = st.session_state.current_user
    email = user['email']
    
    # Get current configs
    email_config = get_user_config(email, "email") or {}
    inv_config = get_user_config(email, "inventory") or {}
    
    tab1, tab2 = st.tabs(["📧 Email Sender Setup", "📦 Inventory Setup"])
    
    # --- EMAIL SETTINGS ---
    with tab1:
        st.subheader("Email Configuration")
        st.info("Required for sending emails via the Email Sender tool.")
        
        with st.form("email_settings_form"):
            sender_email = st.text_input(
                "Your Gmail Address", 
                value=email_config.get("email", ""),
                placeholder="you@gmail.com"
            )
            
            app_password = st.text_input(
                "App Password", 
                value=email_config.get("password", ""),
                type="password",
                help="Generate this in your email account settings"
            )
            
            st.markdown("[How to get an App Password?](https://support.google.com/accounts/answer/185833)")
            
            if st.form_submit_button("💾 Save Email Settings", type="primary"):
                if not sender_email or not app_password:
                    st.error("Please fill in both fields")
                else:
                    # Encrypt the password before saving
                    from cryptography.fernet import Fernet
                    import base64
                    
                    # Get encryption key
                    key_file = "credentials/encryption.key"
                    with open(key_file, 'rb') as f:
                        key = f.read()
                    f = Fernet(key)
                    encrypted_password = f.encrypt(app_password.encode()).decode()
                    
                    config = {"email": sender_email, "password_encrypted": encrypted_password}
                    update_user_config(email, "email", config)
                    # Update session immediately
                    if "config" not in st.session_state.current_user:
                        st.session_state.current_user["config"] = {}
                    st.session_state.current_user["config"]["email"] = config
                    
                    st.session_state.settings_success = "✅ Email settings saved successfully!"
                    st.rerun()

    # --- INVENTORY SETTINGS ---
    with tab2:
        st.subheader("Inventory Configuration")
        st.info("Required for syncing with spreadsheet.")
        
        with st.form("inv_settings_form"):
            sheet_name = st.text_input(
                "Sheet Name", 
                value=inv_config.get("sheet_name", "Inventory Recognition"),
                placeholder="e.g., VEI Inventory 2025",
                help="This will use the admin-configured credentials"
            )
            
            st.info("🔐 Inventory access uses admin-configured credentials")
            st.info("No need to provide your own credentials - the system will use the default credentials")
            
            if st.form_submit_button("💾 Save Inventory Settings", type="primary"):
                if not sheet_name:
                    st.error("Please enter a sheet name")
                else:
                    config = {
                        "sheet_name": sheet_name
                    }
                    update_user_config(email, "inventory", config)
                    # Update session immediately
                    if "config" not in st.session_state.current_user:
                        st.session_state.current_user["config"] = {}
                    st.session_state.current_user["config"]["inventory"] = config
                    
                    st.session_state.settings_success = "✅ Inventory settings saved successfully!"
                    st.rerun()
