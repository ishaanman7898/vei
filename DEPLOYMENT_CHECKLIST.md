# Streamlit Deployment Checklist

## Pre-Deployment Steps

### 1. Google OAuth Setup
- [ ] Go to [Google Cloud Console](https://console.cloud.google.com/)
- [ ] Create/select a project for "Thrive Tools"
- [ ] Enable Google+ API or Google Identity
- [ ] Create OAuth 2.0 Client ID credentials
  - Application type: Web application
  - Authorized redirect URI: `https://thrive-ve.streamlit.app/`
- [ ] Copy Client ID and Client Secret

### 2. Streamlit Cloud Setup
- [ ] Push code to GitHub
- [ ] Connect GitHub repo to Streamlit Cloud
- [ ] Configure app settings in Streamlit Cloud dashboard

### 3. Configure Secrets in Streamlit Cloud
- [ ] Go to app Settings > Secrets
- [ ] Add Google OAuth credentials:
  ```toml
  [google_oauth]
  client_id = "YOUR_GOOGLE_CLIENT_ID"
  client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
  redirect_uri = "https://thrive-ve.streamlit.app/"
  ```

### 4. Verify Access Control
- [ ] Ensure `Secure Access - Thrive Tools - Sheet1.csv` is up to date
- [ ] Run `python sync_users.py` to sync users to auth_users.json
- [ ] Verify all authorized users are listed with correct permissions

### 5. Test Locally (Optional)
- [ ] Create `.streamlit/secrets.toml` with local OAuth credentials
- [ ] Run `streamlit run thrive.py`
- [ ] Test both Google OAuth and email/password login
- [ ] Verify permissions are working correctly

## Post-Deployment Steps

### 1. Test Authentication
- [ ] Visit https://thrive-ve.streamlit.app/
- [ ] Test Google OAuth login with authorized @k12.ipsd.org account
- [ ] Test email/password login (if applicable)
- [ ] Test with unauthorized account (should be denied)

### 2. Test Permissions
- [ ] Login with different user roles
- [ ] Verify Inventory Management access
- [ ] Verify Product Management access
- [ ] Verify Email Management access
- [ ] Verify Admin/User Management access

### 3. Verify Integrations
- [ ] Test Google Sheets connection (Inventory)
- [ ] Test email sending functionality
- [ ] Test product image uploads
- [ ] Test user settings configuration

### 4. Security Verification
- [ ] Ensure credentials folder is not exposed
- [ ] Verify email passwords are encrypted
- [ ] Check that unauthorized users cannot access
- [ ] Test logout functionality

## Ongoing Maintenance

### Adding New Users
1. Add user to `Secure Access - Thrive Tools - Sheet1.csv`
2. Run `python sync_users.py` to sync to auth_users.json
3. Commit and push changes
4. User can now login with Google OAuth or default password

### Updating Permissions
1. Update `Secure Access - Thrive Tools - Sheet1.csv`
2. Run `python sync_users.py` to apply changes
3. Commit and push changes
4. Changes take effect immediately on next login

### Removing User Access
1. Remove user from CSV or set all permissions to FALSE
2. Run `python sync_users.py`
3. Commit and push changes

## Troubleshooting

### Google OAuth Not Working
- Verify client ID and secret in Streamlit secrets
- Check that redirect URI matches exactly: `https://thrive-ve.streamlit.app/`
- Ensure Google+ API is enabled in Google Cloud Console

### User Can't Login
- Check if user email is in `Secure Access - Thrive Tools - Sheet1.csv`
- Verify user has at least one permission set to TRUE
- Check auth_users.json is synced with CSV

### Permission Issues
- Run `python sync_users.py` to refresh permissions
- Check CSV file has correct TRUE/FALSE values
- Verify user logged out and back in to refresh session

## Support Contacts

**Administrators:**
- Ishaan Manoor: ishaanman2724@k12.ipsd.org
- Vinanya Penumadula: vinanyapen4832@k12.ipsd.org

**Live App:**
https://thrive-ve.streamlit.app/
