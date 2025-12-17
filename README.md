# Thrive Tools - Streamlit Application

A comprehensive tools suite for Thrive VE business operations, deployed on Streamlit Cloud with Supabase backend.

**Live Application**: https://thrive-ve.streamlit.app/

## Architecture

This application uses **Supabase** as the primary database for product management and user authentication, with legacy CSV support for bulk operations.

### Core Components
- **Supabase Database**: Product catalog, user management, authentication
- **Streamlit Frontend**: Web interface for all tools
- **Google Sheets Integration**: Inventory synchronization (legacy)
- **SMTP Integration**: Email automation with user-configurable credentials

## Features

### 1. **Product Management**
- Full Supabase product catalog management
- Add/edit products with specifications, images, and variants
- Real-time synchronization with database
- Support for product groups, colors, and hex codes

### 2. **Inventory Management**
- Real-time Google Sheets integration for inventory tracking
- Products loaded from Supabase database
- Add, update, and manage product inventory
- Centralized credentials for all users

### 3. **Email Management**
- Automated order confirmation emails
- PDF invoice generation
- Products loaded from Supabase for email templates
- Individual user email configurations (requires personal app passwords)

### 4. **User Settings**
- Personal email configuration
- Inventory sheet preferences

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

## Database Schema

### Supabase Products Table
```sql
products (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  description text,
  category text,
  status text,
  sku text UNIQUE NOT NULL,
  price numeric,
  buy_link text,
  image_url text,
  group_name text,
  color text,
  hex_color text,
  specifications jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  created_by text
)
```

## Setup & Deployment

### Requirements
```
streamlit>=1.28.0
pandas>=2.0.0
supabase>=2.0.0
gspread>=5.10.0
google-auth>=2.22.0
openpyxl>=3.1.0
pdfplumber>=0.9.0
streamlit-google-oauth>=0.1.0
cryptography>=41.0.0
```

### Google OAuth Setup
See [GOOGLE_AUTH_SETUP.md](GOOGLE_AUTH_SETUP.md) for detailed instructions on configuring Google OAuth authentication.

### Supabase Setup
1. Create a new Supabase project
2. Create the `products` table using the schema above
3. Enable Row Level Security (RLS) for proper access control
4. Add your Supabase credentials to Streamlit secrets:
   ```toml
   SUPABASE_URL = "your-project-url"
   SUPABASE_ANON_KEY = "your-anon-key"
   ```

### Streamlit Cloud Deployment
1. Push code to GitHub repository
2. Connect to Streamlit Cloud
3. Add Supabase credentials and Google OAuth credentials to Streamlit secrets
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
