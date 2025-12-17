import streamlit as st
import pandas as pd
import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from auth import get_current_user
from user_config import get_user_config
from email.mime.image import MIMEImage
from supabase_client import get_authed_supabase

SUBSCRIPTIONS_FILE = "subscriptions.csv"

def get_image_path(sku):
    """Get the path to a product image if it exists"""
    for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.PNG']:
        path = f"product-images/{sku}{ext}"
        if os.path.exists(path):
            return path, ext
    return None, None

def load_subscriptions():
    """Load subscriptions from CSV or create a new DataFrame if it doesn't exist"""
    if os.path.exists(SUBSCRIPTIONS_FILE):
        df = pd.read_csv(SUBSCRIPTIONS_FILE)
        # Convert date strings to datetime objects for display
        if 'start_date' in df.columns and 'next_billing_date' in df.columns:
            df['start_date'] = pd.to_datetime(df['start_date']).dt.date
            df['next_billing_date'] = pd.to_datetime(df['next_billing_date']).dt.date
        return df
    return pd.DataFrame(columns=[
        'customer_name', 'email', 'product_sku', 'product_name', 
        'subscription_type', 'start_date', 'next_billing_date', 'status', 'notes'
    ])

def save_subscriptions(df):
    """Save subscriptions to CSV"""
    df.to_csv(SUBSCRIPTIONS_FILE, index=False)

def get_subscription_products():
    """Get list of subscription products from Supabase products, cleaned of blanks/NaNs"""
    try:
        supabase = get_authed_supabase()
        res = supabase.table("products").select("name,sku,category").ilike("category", "%subscription%").execute()
        rows = getattr(res, "data", None) or []
    except Exception:
        rows = []

    if not rows:
        return []

    df = pd.DataFrame(rows)
    valid_tuples = []
    for _, row in df.iterrows():
        name = row.get('name', '')
        sku = row.get('sku', '')
        if pd.notnull(name) and pd.notnull(sku):
            name = str(name).strip()
            sku = str(sku).strip()
            if name and sku:
                valid_tuples.append((name, sku))
    return valid_tuples

def send_subscription_email(email_config, recipient_email, customer_name, product_name, subscription_type, next_billing_date, product_sku="", notes=""):
    """Send a subscription email"""
    try:
        # Global override (recommended): Streamlit secrets / env vars
        try:
            sender_email = st.secrets.get("SMTP_SENDER_EMAIL")
            app_password = st.secrets.get("SMTP_APP_PASSWORD")
        except Exception:
            sender_email = None
            app_password = None

        sender_email = sender_email or os.getenv("SMTP_SENDER_EMAIL")
        app_password = app_password or os.getenv("SMTP_APP_PASSWORD")

        if app_password:
            import re
            app_password = re.sub(r"\s+", "", str(app_password))

        # Fallback: user config from My Settings
        if (not sender_email or not app_password) and email_config:
            sender_email = sender_email or email_config.get("email")
            password_encrypted = email_config.get("password_encrypted")

            if password_encrypted:
                from cryptography.fernet import Fernet

                key_file = "credentials/encryption.key"
                with open(key_file, 'rb') as f:
                    key = f.read()
                f = Fernet(key)
                app_password = app_password or f.decrypt(password_encrypted.encode()).decode()
            else:
                app_password = app_password or email_config.get("password")

        if app_password:
            import re
            app_password = re.sub(r"\s+", "", str(app_password))

        if not sender_email or not app_password:
            return False, "Email not configured"
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"Thrive <{sender_email}>"
        msg['To'] = recipient_email
        msg['Subject'] = f"Your {product_name} Subscription - Thrive"
        
        # Check if product image exists
        product_image_html = ""
        if product_sku:
            image_path, ext = get_image_path(product_sku)
            if image_path:
                product_image_html = f'<div style="text-align: center; margin: 20px 0;"><img src="cid:product_image" alt="{product_name}" style="max-width: 300px; height: auto; border-radius: 8px;" /></div>'
        
        # Email body with inline logo
        html = f"""
        <html>
        <head>
          <style>
            body {{ font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.7; margin: 0; padding: 20px; background: #f8f9fa; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }}
            .header {{ background: #ffffff; padding: 20px; text-align: center; border-bottom: 1px solid #eee; }}
            .content {{ padding: 40px; }}
            .greeting {{ font-size: 24px; margin: 0 0 20px 0; color: #333; font-weight: bold; }}
            .subscription-info {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 25px 0; }}
            .blue {{ color: #1E90FF; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <img src="cid:logo" alt="Thrive Logo" style="height: 50px; margin-bottom: 0px" />
            </div>
            <div class="content">
              <h2 class="greeting">Hello {customer_name},</h2>
              <p>Thank you for subscribing to our <span class="blue">{product_name}</span>.</p>
              {product_image_html}
              <div class="subscription-info">
                <h3>Subscription Details:</h3>
                <ul>
                  <li><strong>Product:</strong> {product_name}</li>
                  <li><strong>Billing Cycle:</strong> {subscription_type}</li>
                 
                </ul>
              </div>
              <p>If you have any questions, please don't hesitate to contact us.</p>
              <p>Best regards,<br>The Thrive Team</p>
            </div>
          </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        # Attach Logo Inline
        logo_path = "assets/logo.png"
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                logo_img = MIMEImage(f.read())
                logo_img.add_header('Content-ID', '<logo>')
                logo_img.add_header('Content-Disposition', 'inline; filename="logo.png"')
                msg.attach(logo_img)
        
        # Attach Product Image if it exists
        if product_sku:
            image_path, ext = get_image_path(product_sku)
            if image_path:
                with open(image_path, "rb") as f:
                    product_img = MIMEImage(f.read())
                    product_img.add_header('Content-ID', '<product_image>')
                    product_img.add_header('Content-Disposition', 'inline; filename="product.png"')
                    msg.attach(product_img)
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
        
        return True, "Email sent successfully!"
        
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"

def show_subscription_management():
    """Main function to display the subscription management interface"""
    st.title("📅 Subscription Management")
    
    # Get current user and email configuration
    current_user = get_current_user()
    user_email = current_user['email']
    email_config = get_user_config(user_email, "email")
    
    # Load data
    subscriptions = load_subscriptions()
    subscription_products = get_subscription_products()
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Manage Subscriptions", "Subscription Products", "Test Subscription"])
    
    with tab1:
        st.subheader("Customer Subscriptions")
        
        # Add new subscription
        with st.expander("➕ Add New Subscription", expanded=False):
            with st.form("add_subscription"):
                col1, col2 = st.columns(2)
                with col1:
                    customer_name = st.text_input("Customer Name*")
                    email = st.text_input("Email*")
                    
                with col2:
                    product_options = subscription_products if subscription_products else []
                    if product_options:
                        def label_fn(opt):
                            return f"{opt[0]} ({opt[1]})"
                        selected_product = st.selectbox(
                            "Product*",
                            product_options,
                            format_func=label_fn
                        )
                        product_name, product_sku = selected_product
                    else:
                        st.warning("No valid subscription products found in Supabase products.")
                        product_name = ""
                        product_sku = ""
                    
                    subscription_type = st.selectbox("Billing Cycle*", ["Monthly", "Quarterly", "Yearly"])
                
                notes = st.text_area("Notes")
                
                if st.form_submit_button("Add Subscription"):
                    if not customer_name or not email or not product_sku:
                        st.error("Please fill in all required fields (*)")
                    else:
                        # Calculate next billing date (1 month from now)
                        today = datetime.now().date()
                        if subscription_type == "Monthly":
                            next_billing = today + timedelta(days=30)
                        elif subscription_type == "Quarterly":
                            next_billing = today + timedelta(days=90)
                        else:  # Yearly
                            next_billing = today + timedelta(days=365)
                        
                        # Add new subscription
                        new_sub = pd.DataFrame([{
                            'customer_name': customer_name,
                            'email': email,
                            'product_sku': product_sku,
                            'product_name': product_name,
                            'subscription_type': subscription_type,
                            'start_date': today,
                            'next_billing_date': next_billing,
                            'status': 'Active',
                            'notes': notes
                        }])
                        
                        subscriptions = pd.concat([subscriptions, new_sub], ignore_index=True)
                        save_subscriptions(subscriptions)
                        st.success("Subscription added successfully!")
                        st.rerun()
        
        # Display and manage existing subscriptions
        st.subheader("Current Subscriptions")
        
        if not subscriptions.empty:
            # Filter controls
            col1, col2, col3 = st.columns(3)
            with col1:
                status_filter = st.selectbox(
                    "Filter by Status",
                    ["All"] + sorted(subscriptions['status'].unique().tolist())
                )
            with col2:
                product_filter = st.selectbox(
                    "Filter by Product",
                    ["All"] + sorted(subscriptions['product_name'].unique().tolist())
                )
            
            # Apply filters
            filtered_subs = subscriptions.copy()
            if status_filter != "All":
                filtered_subs = filtered_subs[filtered_subs['status'] == status_filter]
            if product_filter != "All":
                filtered_subs = filtered_subs[filtered_subs['product_name'] == product_filter]
            
            # Display table with action buttons
            for idx, sub in filtered_subs.iterrows():
                with st.container():
                    cols = st.columns([2, 2, 2, 1, 2, 2, 2, 1, 1])
                    with cols[0]:
                        st.write(sub['customer_name'])
                    with cols[1]:
                        st.write(sub['email'])
                    with cols[2]:
                        st.write(sub['product_name'])
                    with cols[3]:
                        st.write(sub['subscription_type'])
                    with cols[4]:
                        st.write(str(sub['start_date']))
                    with cols[5]:
                        st.write(str(sub['next_billing_date']))
                    with cols[6]:
                        st.write(sub['status'])
                    with cols[7]:
                        if st.button("✉️", key=f"send_{idx}"):
                            if email_config:
                                with st.spinner(f"Sending to {sub['customer_name']}..."):
                                    success, msg = send_subscription_email(
                                        email_config,
                                        sub['email'],
                                        sub['customer_name'],
                                        sub['product_name'],
                                        sub['subscription_type'],
                                        sub['next_billing_date'],
                                        product_sku=sub.get('product_sku', ''),
                                        notes=sub.get('notes', '')
                                    )
                                    if success:
                                        st.session_state[f'sent_{idx}'] = True
                                        st.success(f"Email sent to {sub['customer_name']} ({sub['email']}) for {sub['product_name']}")
                                    else:
                                        st.session_state[f'sent_{idx}'] = False
                                        st.error(f"Failed to send: {msg}")
                            else:
                                st.error("Email not configured. Please set up email in 'My Settings'.")
                    with cols[8]:
                        if st.button("🗑️", key=f"delete_{idx}"):
                            # Remove the subscription from the dataframe using the original index
                            # Find the row in the original dataframe that matches this filtered row
                            mask = (
                                (subscriptions['customer_name'] == sub['customer_name']) &
                                (subscriptions['email'] == sub['email']) &
                                (subscriptions['product_name'] == sub['product_name']) &
                                (subscriptions['start_date'] == sub['start_date'])
                            )
                            subscriptions = subscriptions[~mask]
                            save_subscriptions(subscriptions)
                            st.success(f"Deleted subscription for {sub['customer_name']}")
                            st.rerun()
                    
                    # Show status message if email was sent
                    if f'sent_{idx}' in st.session_state and st.session_state[f'sent_{idx}']:
                        st.success(f"Email sent to {sub['customer_name']} ({sub['email']}) for {sub['product_name']}")
            
            # Bulk actions
            st.subheader("Bulk Actions")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Process Due Subscriptions"):
                    due_subs = filtered_subs[
                        (filtered_subs['status'] == 'Active') & 
                        (pd.to_datetime(filtered_subs['next_billing_date']) <= pd.Timestamp.now())
                    ]
                    
                    if not due_subs.empty:
                        progress_text = "Processing subscriptions..."
                        progress_bar = st.progress(0, text=progress_text)
                        total_subs = len(due_subs)
                        
                        for i, (_, sub) in enumerate(due_subs.iterrows()):
                            # Update progress
                            progress = (i + 1) / total_subs
                            progress_bar.progress(
                                progress, 
                                text=f"Processing {i+1} of {total_subs}: {sub['customer_name']} - {sub['product_name']}"
                            )
                            
                            # Update next billing date
                            next_billing = pd.Timestamp(sub['next_billing_date'])
                            if sub['subscription_type'] == "Monthly":
                                next_billing += pd.DateOffset(months=1)
                            elif sub['subscription_type'] == "Quarterly":
                                next_billing += pd.DateOffset(months=3)
                            else:  # Yearly
                                next_billing += pd.DateOffset(years=1)
                            
                            subscriptions.loc[
                                (subscriptions['email'] == sub['email']) & 
                                (subscriptions['product_sku'] == sub['product_sku']),
                                'next_billing_date'
                            ] = next_billing.strftime('%Y-%m-%d')
                            
                            # Simulate sending email
                            time.sleep(0.5)  # Simulate processing time
                            st.toast(f"Processed: {sub['customer_name']} - Next billing: {next_billing.strftime('%Y-%m-%d')}")
                        
                        save_subscriptions(subscriptions)
                        progress_bar.empty()
                        st.success(f"✅ Processed {total_subs} subscriptions")
                        st.rerun()
                    else:
                        st.info("No subscriptions are currently due for billing.")
            
            with col2:
                if st.button("📧 Send to All (No Date Check)"):
                    if not filtered_subs.empty:
                        progress_text = "Sending emails..."
                        progress_bar = st.progress(0, text=progress_text)
                        total_subs = len(filtered_subs)
                        
                        for i, (_, sub) in enumerate(filtered_subs.iterrows()):
                            # Update progress
                            progress = (i + 1) / total_subs
                            progress_bar.progress(
                                progress, 
                                text=f"Sending to {i+1} of {total_subs}: {sub['customer_name']}"
                            )
                            
                            # Simulate sending email
                            time.sleep(0.5)  # Simulate processing time
                            st.toast(f"Sent to: {sub['customer_name']} <{sub['email']}> - {sub['product_name']}")
                        
                        progress_bar.empty()
                        st.success(f"✅ Sent emails to {total_subs} subscribers")
                        st.rerun()
                    else:
                        st.warning("No subscriptions to process")
        else:
            st.info("No subscriptions found. Add one using the form above.")
    
    with tab2:
        st.subheader("Subscription Products")
        
        if subscription_products:
            st.write("The following products are available for subscription:")
            for name, sku in subscription_products:
                st.write(f"- {name} (SKU: {sku})")
        else:
            st.warning("No subscription products found in Supabase products. Add products with 'Subscription' in their category.")
    
    with tab3:
        st.subheader("Test Subscription Email")
        st.caption("Send a test subscription email to verify the email template and content.")
        
        with st.form("test_subscription_form"):
            st.write("### Test Subscription Details")
            
            col1, col2 = st.columns(2)
            with col1:
                test_customer = st.text_input("Customer Name", "John Doe")
                test_email = st.text_input("Email", "test@example.com")
                
            with col2:
                product_options = subscription_products if subscription_products else []
                if product_options:
                    def label_fn(opt):
                        return f"{opt[0]} ({opt[1]})"
                    test_product = st.selectbox("Product", product_options, format_func=label_fn)
                    test_product_name, test_product_sku = test_product
                else:
                    st.warning("No valid subscription products found in Supabase products")
                    test_product_name = ""
                    test_product_sku = ""
                
                test_sub_type = st.selectbox("Billing Cycle", ["Monthly", "Quarterly", "Yearly"])
            
            test_notes = st.text_area("Additional Notes", "This is a test subscription email.")
            
            if st.form_submit_button("Send Test Email"):
                if test_email and test_product_name:
                    if email_config:
                        # Calculate next billing date based on subscription type
                        today = datetime.now().date()
                        if test_sub_type == "Monthly":
                            next_billing = today + timedelta(days=30)
                        elif test_sub_type == "Quarterly":
                            next_billing = today + timedelta(days=90)
                        else:  # Yearly
                            next_billing = today + timedelta(days=365)
                        
                        # Actually send the test email
                        with st.spinner(f"Sending test email to {test_email}..."):
                            success, msg = send_subscription_email(
                                email_config,
                                test_email,
                                test_customer,
                                test_product_name,
                                test_sub_type,
                                next_billing,
                                product_sku=test_product_sku,
                                notes=test_notes
                            )
                            
                            if success:
                                st.success(f"✅ Test email sent successfully to {test_email}!")
                            else:
                                st.error(f"❌ Failed to send test email: {msg}")
                    else:
                        st.error("❌ Email not configured. Please set up email in 'My Settings'.")
                else:
                    st.error("Please fill in all required fields (Email and Product)")

def load_subscription_management():
    """Load subscription data with proper type handling"""
    if os.path.exists(SUBSCRIPTIONS_FILE):
        df = pd.read_csv(SUBSCRIPTIONS_FILE)
        # Ensure all expected columns exist
        expected_columns = [
            'customer_name', 'email', 'product_sku', 'product_name', 
            'subscription_type', 'start_date', 'next_billing_date', 'status', 'notes'
        ]
        
        # Add missing columns if any
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        
        # Convert date columns to datetime
        date_columns = ['start_date', 'next_billing_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        
        return df[expected_columns]  # Return columns in consistent order
    
    # Return empty DataFrame with correct columns if file doesn't exist
    return pd.DataFrame(columns=[
        'customer_name', 'email', 'product_sku', 'product_name', 
        'subscription_type', 'start_date', 'next_billing_date', 'status', 'notes'
    ])

if __name__ == "__main__":
    show_subscription_management()
