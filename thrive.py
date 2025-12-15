import streamlit as st
import pandas as pd
import os
import re

# Import modules
from auth import check_authentication, get_current_user, check_permission
from inventory_management import show_inventory_management, load_master
from email_sender import show_email_sender
from user_settings import show_user_settings
from simple_auth import get_user_config
from product_management import show_product_management
from user_management_interface import show_user_management


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

# Load master product data
@st.cache_data
def load_master_cached():
    return load_master()

MASTER = load_master_cached()
sku_to_name = dict(zip(MASTER["SKU#"], MASTER["Product name"]))
name_to_sku = {v: k for k, v in sku_to_name.items()}
sku_to_price = {sku: float(p) for sku, p in zip(MASTER["SKU#"], MASTER["Final Price"])}
sku_to_category = dict(zip(MASTER["SKU#"], MASTER["Category"]))

# Sidebar navigation with permission-based options
st.sidebar.title("Thrive Tools")
st.sidebar.caption(f"👤 {current_user['name']}")

# Build menu options based on permissions
menu_options = []
if check_permission("inventory_management"):
    menu_options.append("Inventory Management")
if check_permission("email_sender"):
    menu_options.append("Email Sender")
if check_permission("product_management"):
    menu_options.append("Product Management")

if check_permission("user_management"):
    menu_options.append("User Management")

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
        # Inventory management now uses centralized service account credentials
        show_inventory_management(MASTER)
    else:
        st.error("❌ Access Denied")
        
elif tool == "Email Sender":
    if check_permission("email_sender"):
        # Get user email config
        email_config = get_user_config(user_email, "email")
        # Get user inventory config (for subtracting inventory)
        inv_config = get_user_config(user_email, "inventory")
        
        if not email_config:
            st.warning("⚠️ Please configure your Email settings in 'My Settings' first.")
        else:
            show_email_sender(MASTER, sku_to_name, name_to_sku, sku_to_price, sku_to_category, email_config, inv_config)
    else:
        st.error("❌ Access Denied")
        
elif tool == "Product Management":
    if check_permission("product_management"):
        show_product_management()
    else:
        st.error("❌ Access Denied")
        

        
elif tool == "User Management":
    if check_permission("user_management"):
        show_user_management()
    else:
        st.error("❌ Access Denied")

elif tool == "My Settings":
    show_user_settings()
