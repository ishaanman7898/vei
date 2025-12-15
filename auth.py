import streamlit as st
import time
import hashlib
import os
import json
import jwt
from simple_auth import verify_login

def get_session_file(email):
    """Get session file path for a user email"""
    # Use email hash for session file name so it persists across devices
    email_hash = hashlib.md5(email.encode()).hexdigest()
    return f"credentials/sessions/{email_hash}.json"

def check_authentication():
    """
    Authentication using email/password only with session persistence
    """
    
    # Check if already authenticated in current session
    if st.session_state.get("authenticated", False):
        return True
    
    # Try to restore from any valid session file (for cross-device persistence)
    sessions_dir = "credentials/sessions"
    if os.path.exists(sessions_dir):
        for session_file in os.listdir(sessions_dir):
            if session_file.endswith('.json'):
                try:
                    with open(os.path.join(sessions_dir, session_file), 'r') as f:
                        session_data = json.load(f)
                        # Check if session is still valid (30 days)
                        if time.time() - session_data.get('timestamp', 0) < 2592000:  # 30 days
                            user_data = session_data.get('user_data')
                            if user_data and user_data.get('email'):
                                # Verify user still exists
                                from simple_auth import get_user_by_email
                                if get_user_by_email(user_data['email']):
                                    st.session_state.authenticated = True
                                    st.session_state.current_user = user_data
                                    return True
                except:
                    continue
    
    # Check if already authenticated in current session
    if st.session_state.get("authenticated", False):
        return True
    
    # Dark theme login UI
    st.markdown("""
    <style>
    .stApp {
        background: #0f172a !important;
    }
    .main {
        background: #0f172a !important;
    }
    [data-testid="stAppViewContainer"] {
        background: #0f172a !important;
    }
    .login-card {
        background: #1e293b !important;
        border-radius: 16px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        padding: 48px 40px;
        max-width: 420px;
        width: 100%;
        border: 1px solid #334155;
    }
    .login-title {
        font-size: 32px;
        font-weight: 700;
        color: #ffffff !important;
        margin-bottom: 8px;
        text-align: center;
    }
    .login-subtitle {
        font-size: 15px;
        color: #94a3b8 !important;
        text-align: center;
        margin-bottom: 32px;
    }
    .stTextInput label {
        color: #e2e8f0 !important;
    }
    .stTextInput > div > div > input {
        background: #0f172a !important;
        color: #ffffff !important;
        border-radius: 8px;
        border: 1px solid #334155 !important;
        padding: 12px 16px;
        font-size: 15px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #64748b !important;
    }
    .stButton > button {
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 15px;
        background: #6366f1 !important;
        border: none;
        color: white !important;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #4f46e5 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }
    .stMarkdown p {
        color: #94a3b8 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<h1 class="login-title">Thrive Tools</h1>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Sign in to your account</p>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your@email.com", key="login_email", label_visibility="visible")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password", label_visibility="visible")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    # Try to verify login with email/password
                    user_data = verify_login(email, password)
                    
                    if user_data:
                        # Check if user has at least one permission
                        has_any_permission = any(user_data.get('permissions', {}).values())
                        
                        if not has_any_permission:
                            st.error("Access Denied: You have no permissions assigned.")
                            st.info("Please contact your administrator to request permissions.")
                        else:
                            # Successful login - save session
                            user_data['email'] = email
                            st.session_state.authenticated = True
                            st.session_state.current_user = user_data
                            
                            # Save session to file for persistence (email-based for cross-device)
                            os.makedirs("credentials/sessions", exist_ok=True)
                            session_file = get_session_file(email)
                            session_data = {
                                'user_data': user_data,
                                'timestamp': time.time()
                            }
                            with open(session_file, 'w') as f:
                                json.dump(session_data, f)
                            
                            st.success(f"Welcome back, {user_data['name']}!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("Invalid email or password")
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Need access? Contact your administrator.")
    
    return False

def get_current_user():
    """Get currently logged in user"""
    user = st.session_state.get("current_user")
    if user:
        return user
    
    # Try to load from any valid session file
    sessions_dir = "credentials/sessions"
    if os.path.exists(sessions_dir):
        for session_file in os.listdir(sessions_dir):
            if session_file.endswith('.json'):
                try:
                    with open(os.path.join(sessions_dir, session_file), 'r') as f:
                        session_data = json.load(f)
                        if time.time() - session_data.get('timestamp', 0) < 2592000:  # 30 days
                            user_data = session_data.get('user_data')
                            if user_data and user_data.get('email'):
                                from simple_auth import get_user_by_email
                                if get_user_by_email(user_data['email']):
                                    st.session_state.authenticated = True
                                    st.session_state.current_user = user_data
                                    return user_data
                except:
                    continue
    
    return None

def check_permission(permission_name):
    """Check if current user has specific permission"""
    user = get_current_user()
    if user is None:
        return False
    return user.get("permissions", {}).get(permission_name, False)
