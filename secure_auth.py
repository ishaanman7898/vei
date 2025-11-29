import json
import hashlib
from cryptography.fernet import Fernet
import base64

# Generate or load encryption key
def get_encryption_key():
    """Get or create encryption key for sensitive data"""
    key_file = "credentials/encryption.key"
    try:
        with open(key_file, 'rb') as f:
            return f.read()
    except:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        return key

def encrypt_data(data):
    """Encrypt sensitive data"""
    key = get_encryption_key()
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data):
    """Decrypt sensitive data"""
    key = get_encryption_key()
    f = Fernet(key)
    return f.decrypt(encrypted_data.encode()).decode()

def hash_password(password):
    """Hash password for verification"""
    return hashlib.sha256(password.encode()).hexdigest()

def secure_auth_users():
    """Secure auth_users.json by encrypting sensitive data"""
    with open('credentials/auth_users.json', 'r') as f:
        data = json.load(f)
    
    # Encrypt email password
    if 'admin@thrive.com' in data:
        if 'config' in data['admin@thrive.com']:
            if 'email' in data['admin@thrive.com']['config']:
                if 'password' in data['admin@thrive.com']['config']['email']:
                    password = data['admin@thrive.com']['config']['email']['password']
                    encrypted_password = encrypt_data(password)
                    data['admin@thrive.com']['config']['email']['password_encrypted'] = encrypted_password
                    del data['admin@thrive.com']['config']['email']['password']
    
    with open('credentials/auth_users.json', 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    secure_auth_users()
    print("Auth users secured with encryption")
