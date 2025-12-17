import streamlit as st
import pandas as pd
import os
import re

# Import modules
from auth import check_authentication, get_current_user, check_permission
from inventory_management import show_inventory_management
from email_sender import show_email_sender
from user_settings import show_user_settings
from user_config import get_user_config
from product_management import show_product_management


st.set_page_config(page_title="Thrive Tools", layout="wide", page_icon="❄️")

# Check authentication first
if not check_authentication():
    st.stop()

# Get current user
current_user = get_current_user()
if not current_user:
    st.error("Unable to load user information. Please log in again.")
    st.stop()
user_email = current_user.get('email', '')

# Load master product data from Supabase (removed cached version as modules now load directly)

# Sidebar navigation with permission-based options
st.sidebar.title("Thrive Tools")
st.sidebar.caption(f"👤 {current_user.get('name', current_user.get('email', 'User'))}")

# Build menu options based on permissions
menu_options = []
if check_permission("inventory_management"):
    menu_options.append("Inventory Management")
if check_permission("email_sender"):
    menu_options.append("Email Sender")
if check_permission("product_management"):
    menu_options.append("Product Management")

# Always add Settings
menu_options.append("My Settings")

if not menu_options:
    st.error("❌ You don't have permission to access any modules. Please contact administrator.")
    st.stop()

tool = st.sidebar.radio("Choose Tool", menu_options, label_visibility="collapsed")

# Single logout button for entire app
st.sidebar.markdown("---")
if st.sidebar.button("🔓 Logout", key="main_logout", use_container_width=True):
    # Clear session file
    import os
    import hashlib
    current_user = st.session_state.get('current_user')
    if current_user and current_user.get('email'):
        email_hash = hashlib.md5(current_user['email'].encode()).hexdigest()
        session_file = f"credentials/sessions/{email_hash}.json"
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
            except:
                pass
    
    st.session_state.authenticated = False
    st.session_state.current_user = None
    # Clear all session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Show selected tool (with permission check)
if tool == "Inventory Management":
    if check_permission("inventory_management"):
        # Inventory Management now loads products from Supabase directly
        show_inventory_management()
    else:
        st.error("❌ Access Denied")
        
elif tool == "Email Sender":
    if check_permission("email_sender"):
        # Get user email config
        email_config = get_user_config(user_email, "email")
        # Get user inventory config (for subtracting inventory)
        inv_config = get_user_config(user_email, "inventory")

        # Allow global SMTP override (Streamlit secrets / env vars) to bypass My Settings
        try:
            smtp_sender = st.secrets.get("SMTP_SENDER_EMAIL")
            smtp_password = st.secrets.get("SMTP_APP_PASSWORD")
        except Exception:
            smtp_sender = None
            smtp_password = None

        smtp_sender = (smtp_sender or os.getenv("SMTP_SENDER_EMAIL") or "").strip() or None
        smtp_password = (smtp_password or os.getenv("SMTP_APP_PASSWORD") or "").strip() or None
        if smtp_password:
            smtp_password = re.sub(r"\s+", "", smtp_password)

        has_global_smtp = bool(smtp_sender and smtp_password)

        if not email_config and not has_global_smtp:
            st.warning("⚠️ Please configure your Email settings in 'My Settings' first.")
        else:
            show_email_sender(email_config, inv_config)
    else:
        st.error("❌ Access Denied")
        
elif tool == "Product Management":
    if check_permission("product_management"):
        show_product_management()
    else:
        st.error("❌ Access Denied")
        

        
elif tool == "My Settings":
    show_user_settings()
