import json
import hashlib
import base64

def hash_sensitive_data(data, parent_key=""):
    """Hash sensitive data like passwords and API keys"""
    if isinstance(data, str):
        # For passwords, use SHA-256
        return hashlib.sha256(data.encode()).hexdigest()
    elif isinstance(data, dict):
        return {k: hash_sensitive_data(v, k) if k in ['password', 'private_key', 'private_key_id'] else v 
                for k, v in data.items()}
    elif isinstance(data, list):
        return [hash_sensitive_data(item, parent_key) for item in data]
    else:
        return data

def clean_auth_users():
    """Clean and hash sensitive data in auth_users.json"""
    with open('credentials/auth_users.json', 'r') as f:
        data = json.load(f)
    
    # Hash all sensitive data
    cleaned_data = hash_sensitive_data(data)
    
    # Remove the inventory service_account since we're hardcoding it now
    if 'admin@thrive.com' in cleaned_data:
        if 'config' in cleaned_data['admin@thrive.com']:
            if 'inventory' in cleaned_data['admin@thrive.com']['config']:
                del cleaned_data['admin@thrive.com']['config']['inventory']
    
    with open('credentials/auth_users.json', 'w') as f:
        json.dump(cleaned_data, f, indent=2)

if __name__ == "__main__":
    clean_auth_users()
    print("Auth users file cleaned and hashed")
