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
from changelog import show_changelog

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
    /* Global background */
    .stApp {
        background-color: #000000;
        color: #ffffff;
    }
    
    /* Sidebar styling - Dark theme */
    [data-testid="stSidebar"] {
        background-color: #111111;
        border-right: 1px solid #333333;
    }
    
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    
    /* Sidebar radio buttons - better visibility */
    [data-testid="stSidebar"] .stRadio > div {
        gap: 0.5rem;
    }
    
    [data-testid="stSidebar"] .stRadio label {
        background-color: #1a1a1a;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 0.25rem 0;
        cursor: pointer;
        transition: all 0.2s;
        border: 1px solid #333333;
    }
    
    [data-testid="stSidebar"] .stRadio label:hover {
        background-color: #262626;
        border-color: #444444;
    }
    
    /* Selected radio button */
    [data-testid="stSidebar"] .stRadio div[data-at="stHorizontalRadio"] div[data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
    }
    
    /* Button alignment */
    .stButton > button {
        width: 100%;
        background-color: #262626;
        color: white;
        border: 1px solid #444444;
    }
    
    .stButton > button:hover {
        background-color: #333333;
        border-color: #555555;
    }
    
    /* Version button styling */
    .version-container button {
        background-color: transparent !important;
        border: none !important;
        color: #555555 !important;
        font-size: 10px !important;
        text-align: left !important;
        padding: 0 !important;
        min-height: unset !important;
        line-height: unset !important;
    }
    
    .version-container button:hover {
        color: #888888 !important;
        text-decoration: underline !important;
        background-color: transparent !important;
    }
    
    /* Better spacing */
    .block-container {
        padding-top: 2rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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

# Sidebar
with st.sidebar:
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
    
    st.markdown("### Navigation")
    tool = st.radio("Navigation", menu_options, label_visibility="collapsed")
    
    # Logout button at bottom
    st.markdown("---")
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
    
    # Version button at bottom
    st.markdown("---")
    st.markdown('<div class="version-container">', unsafe_allow_html=True)
    if st.button(f"v2.4.1", key="version_btn", help="View Changelog", use_container_width=True):
        st.session_state["show_changelog"] = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Main content area
if st.session_state.get("show_changelog"):
    show_changelog()
elif tool == "Inventory":
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
