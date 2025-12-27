import streamlit as st
import os
import re
import hashlib

# Import modules
from auth import check_authentication, get_current_user, check_permission
from inventory_management import show_inventory_management
from email_sender import show_email_sender
from product_management import show_product_management
from email_templates import show_email_test_interface

# Page config
st.set_page_config(
    page_title="Thrive Tools", 
    layout="wide", 
    page_icon="Thrive.png",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Sidebar styling - Dark theme */
    [data-testid="stSidebar"] {
        background-color: #1a1a1a;
    }
    
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    
    /* Sidebar radio buttons - better visibility */
    [data-testid="stSidebar"] .stRadio > div {
        gap: 0.5rem;
    }
    
    [data-testid="stSidebar"] .stRadio label {
        background-color: #2d2d2d;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 0.25rem 0;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    [data-testid="stSidebar"] .stRadio label:hover {
        background-color: #3d3d3d;
    }
    
    [data-testid="stSidebar"] .stRadio label[data-baseweb="radio"] > div:first-child {
        background-color: #4d4d4d;
    }
    
    /* Remove highlight on selected radio button */
    [data-testid="stSidebar"] .stRadio input:checked + div {
        background-color: #2d2d2d !important;
    }
    
    /* Button alignment */
    .stButton > button {
        width: 100%;
    }
    
    /* Better spacing */
    .block-container {
        padding-top: 2rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Check authentication first
if not check_authentication():
    st.stop()

# Get current user
current_user = get_current_user()
if not current_user:
    st.error("Unable to load user information. Please log in again.")
    st.stop()

user_email = current_user.get('email', '')
user_name = current_user.get('name', current_user.get('email', 'User'))

# Sidebar
with st.sidebar:
    # Logo/Title
    st.image("Thrive.png", width=100)
    st.markdown("## Thrive Tools")
    st.caption(f"👤 {user_name}")
    st.markdown("---")
    
    # Build menu options based on permissions
    menu_options = []
    if check_permission("inventory_management"):
        menu_options.append("Inventory")
    if check_permission("email_sender"):
        menu_options.append("Email Sender")
    if check_permission("product_management"):
        menu_options.append("Products")
    
    if len(menu_options) <= 0:
        st.error("No module access. Contact admin.")
        st.stop()
    
    tool = st.radio("Navigation", menu_options, label_visibility="collapsed")
    
    # Spacer
    st.markdown("---")
    
    # Logout button at bottom
    if st.button("Logout", use_container_width=True):
        # Clear session file
        if current_user and current_user.get('email'):
            email_hash = hashlib.md5(current_user['email'].encode()).hexdigest()
            session_file = f"credentials/sessions/{email_hash}.json"
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                except:
                    pass
        
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Main content area
if tool == "Inventory":
    if check_permission("inventory_management"):
        show_inventory_management()
    else:
        st.error("Access Denied")

elif tool == "Email Sender":
    if check_permission("email_sender"):
        show_email_sender()
    else:
        st.error("Access Denied")

elif tool == "Products":
    if check_permission("product_management"):
        show_product_management()
    else:
        st.error("Access Denied")
