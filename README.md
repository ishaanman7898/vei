# Thrive Tools - Streamlit Application

A comprehensive tools suite for Thrive VE business operations, deployed on Streamlit Cloud.

**Live Application**: https://thrive-ve.streamlit.app/

## Features

### 1. **Inventory Management**
- Real-time Google Sheets integration for inventory tracking
- Add, update, and manage product inventory
- Centralized credentials for all users

### 2. **Email Management**
- Automated order confirmation emails
- PDF invoice generation
- Individual user email configurations (requires personal app passwords)

### 3. **Product Management**
- Add and edit products
- Upload product images
- Manage product catalog

### 4. **User Management** (Admin only)
- Manage user permissions
- View user access levels
- Configure user settings

## Authentication

### Google OAuth (Primary)
Users can sign in with their Google accounts (@k12.ipsd.org domain). Access is controlled via the "Secure Access - Thrive Tools - Sheet1.csv" file.

### Email/Password (Fallback)
Traditional email/password authentication is available for users without Google accounts.

## Access Control

User permissions are managed through `Secure Access - Thrive Tools - Sheet1.csv`:
- **Inventory Management**: Access to inventory tools
- **Product Management**: Ability to manage products
- **Email Management**: Access to email sender tools
- **User/Admin Permissions**: Administrative access

## Setup & Deployment

### Requirements
```
streamlit>=1.28.0
pandas>=2.0.0
gspread>=5.10.0
google-auth>=2.22.0
openpyxl>=3.1.0
pdfplumber>=0.9.0
streamlit-google-oauth>=0.1.0
cryptography>=41.0.0
```

### Google OAuth Setup
See [GOOGLE_AUTH_SETUP.md](GOOGLE_AUTH_SETUP.md) for detailed instructions on configuring Google OAuth authentication.

### Streamlit Cloud Deployment
1. Push code to GitHub repository
2. Connect to Streamlit Cloud
3. Add Google OAuth credentials to Streamlit secrets (Settings > Secrets)
4. Deploy!

## File Structure

```
veiwriter/
├── thrive.py                 # Main application
├── auth.py                   # Hybrid authentication (Google + email/password)
├── google_auth.py            # Google OAuth implementation
├── simple_auth.py            # Email/password authentication
├── inventory_management.py   # Inventory tools
├── email_sender.py          # Email automation
├── product_management.py    # Product catalog management
├── user_management_interface.py  # User administration
├── user_settings.py         # User settings interface
├── credentials/             # Authentication & service account credentials
├── product_images/          # Product image uploads
└── Secure Access - Thrive Tools - Sheet1.csv  # Access control list
```

## Configuration

### Google Sheets (Inventory)
- Universal credentials configured for all users
- Service account credentials stored in `credentials/` folder
- Sheet name configurable in `credentials/auth_users.json`

### Email Settings
- Each user must configure their own email app password
- Settings accessible via "My Settings" menu
- Supports Gmail with app-specific passwords

## Security

- Google OAuth integration for secure authentication
- Access control based on CSV whitelist
- Email passwords encrypted at rest
- Service account credentials for Google Sheets
- All sensitive data stored in Streamlit secrets (production)

## Support

For access or permission issues, contact administrators:
- Ishaan Manoor (ishaanman2724@k12.ipsd.org)
- Vinanya Penumadula (vinanyapen4832@k12.ipsd.org)

## License

Private repository for Thrive VE internal use only.
