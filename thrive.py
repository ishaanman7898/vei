import streamlit as st
import os
import re
import hashlib

# Import modules
from auth import check_authentication, get_current_user, check_permission
from inventory_management import show_inventory_management
from email_sender import show_email_sender
from product_merger import show_product_merger

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
    
    /* Version container styling */
    .version-container {
        color: #555555;
        font-size: 10px;
        text-align: center;
        padding: 10px 0;
    }
    
    /* Better spacing */
    .block-container {
        padding-top: 2rem;
    }
    
    /* Hide Streamlit branding (keep header visible so sidebar toggle works) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    header::before {content: ""; display: block;}

    /* Force sidebar always open — hide the collapse/expand toggle arrow */
    [data-testid="collapsedControl"] {display: none !important;}
    button[kind="header"] {display: none !important;}

    /* Prevent sidebar from sliding off-screen */
    [data-testid="stSidebar"] {
        transform: none !important;
        min-width: 244px !important;
        width: 244px !important;
    }
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
    menu_options.append("Product Merger")

    if len(menu_options) <= 0:
        st.error("No module access. Contact admin.")
        st.stop()
    
    st.markdown("### Navigation")
    tool = st.radio("Navigation", menu_options, label_visibility="collapsed")
    
    # Logout button at bottom
    st.markdown("---")
    if st.button("Logout", width='stretch'):
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Version at bottom
    st.markdown("---")
    st.markdown('<div class="version-container">v2.5.0</div>', unsafe_allow_html=True)

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

elif tool == "Product Merger":
    show_product_merger()

