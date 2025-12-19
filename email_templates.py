"""
Email Templates and Test Interface for Thrive
Improved HTML email designs with preview functionality
"""

import streamlit as st
import smtplib
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage





def get_fulfillment_email_html(first_name, order_number, items_html, total):
    """Generate improved fulfillment email HTML"""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Order Complete</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f5f5f5; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <!-- Shadow effect using nested tables -->
                    <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #e0e0e0; border-radius: 16px;">
                        <tr>
                            <td style="padding: 3px;">
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 14px; overflow: hidden;">
                        
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 30px 40px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-bottom: 1px solid #e0e0e0;">
                                <img src="cid:logo" alt="Thrive" style="max-height: 120px; margin-bottom: 10px;">
                                <p style="color: #1a1a2e; font-size: 12px; margin: 0; letter-spacing: 2px; text-transform: uppercase;">Thank You For Your Order</p>
                            </td>
                        </tr>
                        
                        <!-- Celebration Icon -->
                        <tr>
                            <td style="padding: 30px 40px 0 40px; text-align: center; box-shadow: inset 0 8px 12px rgba(0,0,0,0.04);">
                                <div style="font-size: 48px; margin-bottom: 10px;">🎉</div>
                            </td>
                        </tr>
                        
                        <!-- Greeting -->
                        <tr>
                            <td style="padding: 10px 40px; text-align: center;">
                                <h1 style="margin: 0; font-size: 28px; color: #1a1a2e; font-weight: 600;">
                                    Thank you, {first_name}!
                                </h1>
                            </td>
                        </tr>
                        
                        <!-- Message -->
                        <tr>
                            <td style="padding: 10px 40px 30px 40px; text-align: center;">
                                <p style="margin: 0; font-size: 16px; color: #555; line-height: 1.6;">
                                    Your order is complete! We truly appreciate your support.
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Order Details Card -->
                        <tr>
                            <td style="padding: 0 40px 20px 40px;">
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; overflow: hidden;">
                                    <tr>
                                        <td style="padding: 25px;">
                                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                                <tr>
                                                    <td>
                                                        <p style="margin: 0 0 5px 0; font-size: 12px; color: rgba(255,255,255,0.7); text-transform: uppercase; letter-spacing: 1px;">Order Number</p>
                                                        <p style="margin: 0; font-size: 22px; color: #ffffff; font-weight: 700;">#{order_number}</p>
                                                    </td>
                                                    <td align="right">
                                                        <p style="margin: 0 0 5px 0; font-size: 12px; color: rgba(255,255,255,0.7); text-transform: uppercase; letter-spacing: 1px;">Total</p>
                                                        <p style="margin: 0; font-size: 22px; color: #ffffff; font-weight: 700;">${total:.2f}</p>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Items Section -->
                        <tr>
                            <td style="padding: 0 40px 20px 40px;">
                                <p style="margin: 0 0 15px 0; font-size: 14px; color: #888; text-transform: uppercase; letter-spacing: 1px;">What You Ordered</p>
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background: #fafafa; border-radius: 12px; overflow: hidden;">
                                    <tr>
                                        <td style="padding: 20px;">
                                            {items_html}
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Photos Notice -->
                        <tr>
                            <td style="padding: 0 40px 30px 40px;">
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td style="background: #e3f2fd; border-radius: 12px; padding: 20px;">
                                            <p style="margin: 0; font-size: 14px; color: #1565c0;">
                                                <strong>Photos of your items are attached below!</strong>
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background: #f8f9fa; padding: 30px 40px; text-align: center;">
                                <p style="margin: 0 0 15px 0; font-size: 16px; color: #1a1a2e; font-weight: 600;">
                                    Thank you for supporting <a href="https://thrive-ve.com" style="color: #667eea; text-decoration: none;">Thrive</a>! 💙
                                </p>
                                <p style="margin: 0 0 10px 0; font-size: 14px; color: #555;">
                                    Questions? Reply to this email or <a href="mailto:thrivewellness.il@veinternational.org" style="color: #667eea; text-decoration: none;">contact us</a>.
                                </p>
                                <p style="margin: 0; font-size: 12px; color: #999;">
                                    © 2025 Thrive Wellness. All rights reserved.
                                </p>
                            </td>
                        </tr>
                        
                                </table>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def generate_items_html(items):
    """Generate HTML for order items list"""
    html = ""
    for item in items:
        name = item.get('name', 'Product')
        price = item.get('price', 0)
        qty = item.get('qty', 1)
        
        if qty > 1:
            html += f"""
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 12px;">
                <tr>
                    <td style="padding: 12px; background: #ffffff; border-radius: 8px;">
                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="font-size: 15px; color: #333; font-weight: 500;">{name} <span style="color: #667eea;">x{qty}</span></td>
                                <td align="right" style="font-size: 15px; color: #1a1a2e; font-weight: 600; width: 80px;">${price * qty:.2f}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
            """
        else:
            html += f"""
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 12px;">
                <tr>
                    <td style="padding: 12px; background: #ffffff; border-radius: 8px;">
                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="font-size: 15px; color: #333; font-weight: 500;">{name}</td>
                                <td align="right" style="font-size: 15px; color: #1a1a2e; font-weight: 600;">${price:.2f}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
            """
    return html


def show_email_test_interface():
    """Show email template test interface"""
    st.write("DEBUG: Function called")  # Debug line
    
    try:
        st.title("📧 Email Template Tester")
        st.caption("Preview and test the improved email templates")
        
        # Test data inputs
        st.markdown("### Test Data")
    except Exception as e:
        st.error(f"Error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return
    col1, col2 = st.columns(2)
    
    with col1:
        test_name = st.text_input("Customer Name", value="John")
        test_order = st.text_input("Order Number", value="1001")
        test_email = st.text_input("Send Test To (your email)", placeholder="your@email.com")
    
    with col2:
        email_type = st.selectbox("Email Type", ["Fulfillment"])
    
    # Sample items
    st.markdown("### Sample Items")
    sample_items = [
        {"name": "The Glacier (Brown) w. Ice Cap", "price": 99.99, "qty": 1},
        {"name": "Surge IV (Blue Razzberry)", "price": 29.99, "qty": 2},
        {"name": "Peak Powder (Chocolate)", "price": 49.99, "qty": 1},
    ]
    
    # Calculate total
    total = sum(item['price'] * item['qty'] for item in sample_items)
    
    # Generate items HTML
    items_html = generate_items_html(sample_items)
    
    # Generate email HTML
    html = get_fulfillment_email_html(test_name, test_order, items_html, total)
    
    # Preview
    st.markdown("---")
    st.markdown("### Email Preview")
    
    # Convert logo to base64 for preview
    import base64
    logo_path = "assets/logo.png"
    logo_base64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
    
    # Replace cid:logo with base64 for preview
    preview_html = html.replace('src="cid:logo"', f'src="data:image/png;base64,{logo_base64}"')
    
    # Show preview using components.html for proper rendering
    with st.expander("📧 View Email Preview", expanded=True):
        st.components.v1.html(preview_html, height=800, scrolling=True)
    
    # Send test email
    st.markdown("---")
    st.markdown("### Send Test Email")
    
    if st.button("📤 Send Test Email", type="primary", disabled=not test_email):
        if not test_email:
            st.error("Please enter your email address")
        else:
            try:
                # Load environment variables
                from dotenv import load_dotenv
                load_dotenv()
                
                # Get SMTP credentials from .env
                SENDER_EMAIL = os.getenv("SMTP_SENDER_EMAIL")
                APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")
                
                # Clean up credentials
                if SENDER_EMAIL:
                    SENDER_EMAIL = SENDER_EMAIL.strip().strip('"').strip("'")
                if APP_PASSWORD:
                    APP_PASSWORD = APP_PASSWORD.strip().strip('"').strip("'")
                    APP_PASSWORD = re.sub(r"\s+", "", str(APP_PASSWORD))
                
                if not SENDER_EMAIL or not APP_PASSWORD:
                    st.error("❌ SMTP credentials not found in .env file")
                    st.info("Make sure SMTP_SENDER_EMAIL and SMTP_APP_PASSWORD are set in your .env file")
                    return
                
                # Create message
                msg = MIMEMultipart()
                msg['From'] = f"Thrive <{SENDER_EMAIL}>"
                msg['To'] = test_email
                msg['Subject'] = f"[TEST] Thank you for your order #{test_order} – Thrive"
                
                msg.attach(MIMEText(html, 'html'))
                
                # Attach logo - use assets/logo.png (transparent version)
                logo_path = "assets/logo.png"
                if os.path.exists(logo_path):
                    with open(logo_path, "rb") as f:
                        logo_img = MIMEImage(f.read())
                        logo_img.add_header('Content-ID', '<logo>')
                        logo_img.add_header('Content-Disposition', 'inline; filename="logo.png"')
                        msg.attach(logo_img)
                
                # Attach sample product images
                for idx, item in enumerate(sample_items):
                    # For demo, attach the logo as sample product images
                    # In production, you'd fetch actual product images from Supabase
                    if os.path.exists(logo_path):
                        with open(logo_path, "rb") as f:
                            product_img = MIMEImage(f.read())
                            product_img.add_header('Content-Disposition', f'attachment; filename="{item["name"]}.png"')
                            msg.attach(product_img)
                
                # Send email
                with st.spinner(f"Sending test email to {test_email}..."):
                    server = smtplib.SMTP('smtp.gmail.com', 587)
                    server.starttls()
                    server.login(SENDER_EMAIL, APP_PASSWORD)
                    server.send_message(msg)
                    server.quit()
                
                st.success(f"✅ Test email sent successfully!")
                st.info(f"📬 Sent from: {SENDER_EMAIL}")
                st.info(f"📧 Sent to: {test_email}")
                st.caption("Check your inbox (and spam folder) for the test email.")
                
            except smtplib.SMTPAuthenticationError:
                st.error("❌ Authentication failed. Check your SMTP credentials in .env file.")
            except smtplib.SMTPException as e:
                st.error(f"❌ SMTP error: {e}")
            except Exception as e:
                st.error(f"❌ Failed to send: {e}")
    
    # Show raw HTML option
    with st.expander("View Raw HTML"):
        st.code(html, language="html")


if __name__ == "__main__":
    st.set_page_config(page_title="Email Template Tester", layout="wide", page_icon="📧")
    show_email_test_interface()
