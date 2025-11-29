# Quick Start Guide - Thrive Tools with Google OAuth

## For Administrators

### Initial Setup (One-time)

1. **Configure Google OAuth** (See GOOGLE_AUTH_SETUP.md for details)
   ```
   - Create OAuth credentials in Google Cloud Console
   - Add to Streamlit Cloud secrets
   ```

2. **Sync Users**
   ```bash
   python sync_users.py
   ```
   This reads the CSV and creates user accounts.

3. **Deploy to Streamlit**
   ```bash
   git add .
   git commit -m "Added Google OAuth and access control"
   git push
   ```

### Managing Users

**To Add a User:**
1. Edit `Secure Access - Thrive Tools - Sheet1.csv`
2. Add row with: Name, Email, Permissions (TRUE/FALSE)
3. Run: `python sync_users.py`
4. Commit and push changes

**To Update Permissions:**
1. Edit CSV permissions
2. Run: `python sync_users.py`
3. Commit and push

**To Remove Access:**
1. Delete row from CSV or set all permissions to FALSE
2. Run: `python sync_users.py`
3. Commit and push

## For End Users

### Logging In

**Option 1: Google OAuth (Recommended)**
1. Go to https://thrive-ve.streamlit.app/
2. Click "Sign in with Google"
3. Use your @k12.ipsd.org email

**Option 2: Email/Password**
1. Go to https://thrive-ve.streamlit.app/
2. Enter email and password
3. Default password: `ChangeMe123!` (change immediately!)

### First-Time Setup

1. **Login** with Google or email/password
2. **Go to "My Settings"** in the sidebar
3. **Configure Email** (if you need email functionality):
   - Enter your email address
   - Enter your Gmail app password ([How to get app password](https://support.google.com/accounts/answer/185833))
   - Save settings

### Using the App

**Available Tools** (based on your permissions):
- 📦 **Inventory Management**: Add/edit inventory in Google Sheets
- 📧 **Email Sender**: Send order confirmations with invoices
- 🏷️ **Product Management**: Manage product catalog
- 👥 **User Management**: Admin only - manage user permissions

### Getting Help

**Can't Login?**
- Verify you're using an authorized @k12.ipsd.org email
- Check with administrators if you should have access

**Email Not Working?**
- Configure your email app password in "My Settings"
- Make sure you're using a Gmail app-specific password

**Permission Issues?**
- Contact your administrator to update your permissions

## Permissions Explained

| Permission | What It Allows |
|-----------|----------------|
| **Inventory Management** | View and edit inventory in Google Sheets |
| **Product Management** | Add/edit products and upload images |
| **Email Management** | Send automated order confirmation emails |
| **User/Admin Permissions** | Manage users and view all settings (Admin only) |

## Technical Details

### Authentication Flow
```
User → Login Page → Google OAuth OR Email/Password
     → CSV Check → Permission Assignment → App Access
```

### Data Storage
- **User Accounts**: `credentials/auth_users.json`
- **Access Control**: `Secure Access - Thrive Tools - Sheet1.csv`
- **Inventory**: Google Sheets (shared service account)
- **Email Passwords**: Encrypted in auth_users.json

### Security
- ✅ Google OAuth SSO
- ✅ CSV whitelist
- ✅ Per-user permissions
- ✅ Encrypted email passwords
- ✅ Session-based authentication

## Troubleshooting

### "Access Denied" Error
→ Your email is not in the authorized list. Contact admin.

### "No Permissions Assigned" Error
→ Your permissions are all set to FALSE. Contact admin.

### Google OAuth Not Working
→ Contact admin - OAuth credentials may not be configured.

### Email Functionality Not Available
→ Configure your email settings in "My Settings" first.

## Contact & Support

**Administrators:**
- Ishaan Manoor: ishaanman2724@k12.ipsd.org
- Vinanya Penumadula: vinanyapen4832@k12.ipsd.org

**Live App:**
🔗 https://thrive-ve.streamlit.app/

**Documentation:**
- README.md - Project overview
- GOOGLE_AUTH_SETUP.md - OAuth setup
- DEPLOYMENT_CHECKLIST.md - Deployment steps
- IMPLEMENTATION_SUMMARY.md - Technical details
