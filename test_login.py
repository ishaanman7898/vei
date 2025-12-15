import streamlit as st
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the auth module
from auth import check_authentication

# Set page config
st.set_page_config(page_title="Test Login", layout="wide")

# Test the login page
check_authentication()
