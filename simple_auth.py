import json
import hashlib
import os

AUTH_FILE = "credentials/auth_users.json"

def hash_password(password):
    """Hash password with SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_auth_db():
    """Initialize auth database with default admin"""
    if not os.path.exists(AUTH_FILE):
        os.makedirs("credentials", exist_ok=True)
        default_users = {
            "admin@thrive.com": {
                "password_hash": hash_password("admin123"),
                "name": "Admin User",
                "permissions": {
                    "inventory_management": True,
                    "email_sender": True,
                    "product_management": True,
                    "user_management": True
                }
            }
        }
        with open(AUTH_FILE, "w") as f:
            json.dump(default_users, f, indent=2)

def load_auth_users():
    """Load all authenticated users"""
    init_auth_db()
    with open(AUTH_FILE, "r") as f:
        return json.load(f)

def save_auth_users(users):
    """Save users to database"""
    with open(AUTH_FILE, "w") as f:
        json.dump(users, f, indent=2)

def verify_login(email, password):
    """Verify email and password"""
    users = load_auth_users()
    if email in users:
        stored_hash = users[email]["password_hash"]
        if hash_password(password) == stored_hash:
            user_data = users[email].copy()
            user_data["email"] = email
            return user_data
    return None

def get_user_by_email(email):
    """Get user data by email (including email field)"""
    users = load_auth_users()
    if email in users:
        user_data = users[email].copy()
        user_data["email"] = email
        return user_data
    return None

def register_user(email, password, name):
    """Register a new user with basic permissions"""
    users = load_auth_users()
    if email in users:
        return False, "Email already exists"
    users[email] = {
        "password_hash": hash_password(password),
        "name": name,
        "permissions": {
            "inventory_management": False,
            "email_sender": False,
            "product_management": False,
            "user_management": False
        }
    }
    # Note: Inventory config is no longer needed since using centralized credentials
    # Email config will be added separately when user configures email settings
    
    save_auth_users(users)
    return True, "User created successfully"

def update_user_permissions(email, permissions):
    """Update user permissions"""
    users = load_auth_users()
    if email in users:
        users[email]["permissions"] = permissions
        save_auth_users(users)
        return True
    return False

def get_all_auth_users():
    """Get all users for management"""
    users = load_auth_users()
    user_list = []
    for email, data in users.items():
        user_list.append({
            "email": email,
            "name": data["name"],
            "permissions": data["permissions"]
        })
    return user_list

def update_user_config(email, config_type, config_data):
    """Update specific configuration for a user (email or inventory)"""
    users = load_auth_users()
    if email in users:
        if "config" not in users[email]:
            users[email]["config"] = {}
        
        users[email]["config"][config_type] = config_data
        save_auth_users(users)
        return True
    return False

def get_user_config(email, config_type):
    """Get specific configuration for a user"""
    users = load_auth_users()
    if email in users:
        return users[email].get("config", {}).get(config_type)
    return None

def delete_user(email):
    """Delete a user"""
    users = load_auth_users()
    if email in users:
        del users[email]
        save_auth_users(users)
        return True
    return False
