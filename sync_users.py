"""
Sync users from Secure Access CSV to auth_users.json
This script helps maintain consistency between the access control CSV and the authentication database
"""

import pandas as pd
import json
from simple_auth import hash_password, load_auth_users, save_auth_users

ACCESS_CSV = "Secure Access - Thrive Tools - Sheet1.csv"

def sync_users_from_csv():
    """Sync users from the access control CSV to auth_users.json"""
    
    # Load CSV
    df = pd.read_csv(ACCESS_CSV)
    df = df.dropna(how='all')  # Remove empty rows
    
    # Load existing users
    users = load_auth_users()
    
    synced_count = 0
    updated_count = 0
    
    for _, row in df.iterrows():
        email = row.get('Email')
        name = row.get('Name')
        
        if pd.isna(email) or pd.isna(name):
            continue
        
        email = str(email).strip()
        name = str(name).strip()
        
        # Parse permissions
        permissions = {
            "inventory_management": str(row.get('Inventory Management', '')).upper() == 'TRUE',
            "product_management": str(row.get('Product Management', '')).upper() == 'TRUE',
            "email_sender": str(row.get('Email Management', '')).upper() == 'TRUE',
            "user_management": str(row.get('User/Admin Permissions', '')).upper() == 'TRUE',
        }
        
        # Check if user exists
        if email in users:
            # Update permissions
            users[email]['permissions'] = permissions
            users[email]['name'] = name
            updated_count += 1
            print(f"✓ Updated: {name} ({email})")
        else:
            # Create new user with default password
            default_password = "ChangeMe123!"
            users[email] = {
                "password_hash": hash_password(default_password),
                "name": name,
                "permissions": permissions,
                "config": {}
            }
            synced_count += 1
            print(f"+ Added: {name} ({email}) - Default password: {default_password}")
    
    # Save updated users
    save_auth_users(users)
    
    print(f"\n✅ Sync complete!")
    print(f"   - New users added: {synced_count}")
    print(f"   - Existing users updated: {updated_count}")
    
    if synced_count > 0:
        print(f"\n⚠️  IMPORTANT: New users have default password 'ChangeMe123!'")
        print(f"   They should change it immediately in 'My Settings'")

if __name__ == "__main__":
    print("=" * 60)
    print("Syncing users from Secure Access CSV to auth_users.json")
    print("=" * 60)
    print()
    
    sync_users_from_csv()
