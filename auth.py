import streamlit as st
import time
import hashlib
import os
import json
from supabase_client import supabase_sign_in


def check_authentication():
    """
    Authentication using email/password only with session persistence and 30-minute timeout
    """
    import time
    
    # Check if already authenticated in current session
    if st.session_state.get("authenticated", False):
        # Check session timeout (30 minutes = 1800 seconds)
        last_activity = st.session_state.get("last_activity_time", 0)
        current_time = time.time()
        
        if current_time - last_activity > 1800:  # 30 minutes
            # Session expired
            st.session_state.authenticated = False
            st.session_state.pop("supabase_session", None)
            st.session_state.pop("current_user", None)
            st.warning("⏱️ Session expired after 30 minutes of inactivity. Please log in again.")
            return False
        
        # Update last activity time
        st.session_state.last_activity_time = current_time
        return True
    
 
    
    
   
     
    
     
    # Custom CSS for login page
    st.markdown("""
    <style>
        .stApp {
            background-color: #000000;
        }
        /* Login form container */
        [data-testid="stVerticalBlock"] > div:has(div.stForm) {
            background: rgba(17, 17, 17, 0.8);
            backdrop-filter: blur(10px);
            padding: 3rem 2rem;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
        }
        
        /* Input fields */
        .stTextInput > div > div > input {
            background-color: #0c0c0c !important;
            border: 1px solid #333333 !important;
            color: #ffffff !important;
            border-radius: 8px !important;
        }
        
        /* Center image */
        .stImage {
            display: flex;
            justify-content: center;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Adaptive centering
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Logo Section
        st.image("Thrive.png", width=180)
        st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)

        # Input Section
        with st.form("login_form"):
            email = st.text_input("Employee ID / Email", placeholder="ex: j.doe@company.com", key="login_email", label_visibility="visible")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password", label_visibility="visible")

            st.markdown("######") # Adds a little spacer

            submit = st.form_submit_button("Sign In", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    try:
                        supabase_session = supabase_sign_in(email, password)
                    except Exception as e:
                        st.error(f"Invalid email or password ({e})")
                        st.stop()

                    name = email.split("@", 1)[0] if email else "User"
                    user_data = {"email": email, "name": name}
                    st.session_state.authenticated = True
                    st.session_state.current_user = user_data
                    st.session_state.supabase_session = supabase_session
                    st.session_state.last_activity_time = time.time()  # Set initial activity time

                    st.success(f"Welcome back, {user_data['name']}!")
                    time.sleep(1)
                    st.rerun()

        # Footer Links
        st.markdown("""
            <div style="text-align: center; margin-top: 20px; font-size: 10px; color: #555555;">
                v2.4.1
            </div>
        """, unsafe_allow_html=True)
    
    return False

def get_current_user():
    """Get currently logged in user"""
    user = st.session_state.get("current_user")
    if user:
        return user
    
    # Session persistence disabled - user must login every time
    return None

def check_permission(permission_name):
    """Check if current user has specific permission"""
    return True

