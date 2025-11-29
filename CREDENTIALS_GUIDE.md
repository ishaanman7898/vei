# 🔐 Google OAuth Credentials Setup

## ✅ Your New Credentials

**Client ID:**
`1025952294032-12iaqmq1rp83msjul4roi1bigvivo2qg.apps.googleusercontent.com`

**Client Secret:**
`YOUR_CLIENT_SECRET` (Get this from Google Cloud Console)

---

## 📍 Where to Keep These

### 1. For Local Development (Optional)
I've updated the code to use your Client ID automatically! But if you want to be strict:
1. Create a folder named `.streamlit` in your project root
2. Create a file named `secrets.toml` inside it
3. Copy the content from `SECRETS_TEMPLATE.toml` into it

### 2. For Streamlit Cloud (REQUIRED for Production)
When you deploy your app, you MUST add these to Streamlit Cloud:

1. Go to your app dashboard: https://share.streamlit.io/
2. Click the **Settings** (gear icon) on your app
3. Click **Secrets**
4. Paste this EXACTLY:

```toml
[google_oauth]
client_id = "1025952294032-12iaqmq1rp83msjul4roi1bigvivo2qg.apps.googleusercontent.com"
client_secret = "YOUR_CLIENT_SECRET"
redirect_uri = "https://thrive-ve.streamlit.app/"
```

5. Click **Save**

---

## ⚠️ Important Note
**NEVER commit the `secrets.toml` file to GitHub!**
That's why I couldn't create it for you directly - it's blocked by `.gitignore` to keep your secrets safe.

## 🚀 Status
I've updated `auth.py` to use your new Client ID by default, so **localhost should work immediately** after a restart!
