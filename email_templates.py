"""
Email Templates for Thrive
All styles are inline — <style> tags get stripped by Gmail/Outlook.
"""

import streamlit as st
import smtplib
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# ── Shared layout constants ──────────────────────────────────────────────────
_OUTER_BG   = "#f4f4f0"
_CARD_BG    = "#ffffff"
_BORDER     = "#e4e4e0"
_TEXT_DARK  = "#1a1a1a"
_TEXT_BODY  = "#4a4a4a"
_TEXT_MUTED = "#888888"
_ACCENT     = "#2d6a4f"   # deep forest green


def _base_wrapper(content_rows: str) -> str:
    """Wraps content in the shared email shell (outer bg + centered card)."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:{_OUTER_BG};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:{_OUTER_BG};padding:40px 16px;">
  <tr><td align="center">
    <table role="presentation" width="560" cellspacing="0" cellpadding="0" style="background-color:{_CARD_BG};border:1px solid {_BORDER};border-radius:8px;overflow:hidden;">

      <!-- Logo header -->
      <tr>
        <td style="padding:32px 40px 24px 40px;border-bottom:1px solid {_BORDER};">
          <img src="cid:logo" alt="Thrive" style="height:52px;display:block;">
        </td>
      </tr>

      {content_rows}

      <!-- Footer -->
      <tr>
        <td style="padding:24px 40px;border-top:1px solid {_BORDER};">
          <p style="margin:0 0 6px 0;font-size:13px;color:{_TEXT_MUTED};line-height:1.5;">
            Questions about your order? Reply to this email or reach us at
            <a href="mailto:thrivewellness.il@veinternational.org" style="color:{_ACCENT};text-decoration:none;">thrivewellness.il@veinternational.org</a>.
          </p>
          <p style="margin:0;font-size:12px;color:{_TEXT_MUTED};">
            &copy; 2025 Thrive &nbsp;·&nbsp; <a href="https://thrive-ve.com" style="color:{_TEXT_MUTED};text-decoration:none;">thrive-ve.com</a>
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


def generate_items_html(items: list[dict]) -> str:
    """Receipt-style item rows — name left, price right, separator between rows."""
    rows = ""
    for i, item in enumerate(items):
        name  = item.get("name", "Product")
        price = float(item.get("price", 0))
        qty   = int(item.get("qty", 1))
        total = price * qty
        qty_label = f" &times; {qty}" if qty > 1 else ""
        border = f"border-top:1px solid {_BORDER};" if i > 0 else ""
        rows += f"""
      <tr>
        <td style="{border}padding:12px 0;font-size:14px;color:{_TEXT_BODY};line-height:1.4;">
          {name}{qty_label}
        </td>
        <td style="{border}padding:12px 0;font-size:14px;color:{_TEXT_DARK};font-weight:600;text-align:right;white-space:nowrap;">
          ${total:.2f}
        </td>
      </tr>"""
    return rows


def get_fulfillment_email_html(first_name: str, order_number: str, items_rows: str, total: float) -> str:
    """
    Fulfillment / thank-you email.
    items_rows should come from generate_items_html().
    Product photos are attached separately by the sender.
    """
    content = f"""
      <!-- Greeting -->
      <tr>
        <td style="padding:36px 40px 0 40px;">
          <p style="margin:0 0 8px 0;font-size:22px;font-weight:600;color:{_TEXT_DARK};">
            Hi {first_name}, your order is on its way!
          </p>
          <p style="margin:0;font-size:15px;color:{_TEXT_BODY};line-height:1.6;">
            Thanks for your order — we really appreciate your support.
            Here's a summary of what you got, and photos of each item are attached below.
          </p>
        </td>
      </tr>

      <!-- Order meta -->
      <tr>
        <td style="padding:24px 40px 0 40px;">
          <p style="margin:0;font-size:12px;font-weight:600;color:{_TEXT_MUTED};text-transform:uppercase;letter-spacing:.08em;">
            Order #{order_number}
          </p>
        </td>
      </tr>

      <!-- Items table -->
      <tr>
        <td style="padding:12px 40px 0 40px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
            {items_rows}
            <!-- Total row -->
            <tr>
              <td style="border-top:2px solid {_TEXT_DARK};padding:12px 0 0 0;font-size:14px;font-weight:600;color:{_TEXT_DARK};">
                Total
              </td>
              <td style="border-top:2px solid {_TEXT_DARK};padding:12px 0 0 0;font-size:14px;font-weight:600;color:{_TEXT_DARK};text-align:right;">
                ${total:.2f}
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- Sign-off -->
      <tr>
        <td style="padding:32px 40px 36px 40px;">
          <p style="margin:0;font-size:15px;color:{_TEXT_BODY};line-height:1.6;">
            Thank you again — it means a lot to us.<br>
            <span style="color:{_TEXT_DARK};font-weight:600;">The Thrive Team</span>
          </p>
        </td>
      </tr>"""

    return _base_wrapper(content)


def get_confirmation_email_html(first_name: str, order_number: str, items_rows: str, total: float) -> str:
    """
    Order-received / confirmation email (no images attached).
    """
    content = f"""
      <!-- Greeting -->
      <tr>
        <td style="padding:36px 40px 0 40px;">
          <p style="margin:0 0 8px 0;font-size:22px;font-weight:600;color:{_TEXT_DARK};">
            Hi {first_name}, we got your order!
          </p>
          <p style="margin:0;font-size:15px;color:{_TEXT_BODY};line-height:1.6;">
            Thanks for ordering — we're on it. Here's what you ordered, and
            we'll follow up once it's been processed.
          </p>
        </td>
      </tr>

      <!-- Order meta -->
      <tr>
        <td style="padding:24px 40px 0 40px;">
          <p style="margin:0;font-size:12px;font-weight:600;color:{_TEXT_MUTED};text-transform:uppercase;letter-spacing:.08em;">
            Order #{order_number}
          </p>
        </td>
      </tr>

      <!-- Items table -->
      <tr>
        <td style="padding:12px 40px 0 40px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
            {items_rows}
            <!-- Total row -->
            <tr>
              <td style="border-top:2px solid {_TEXT_DARK};padding:12px 0 0 0;font-size:14px;font-weight:600;color:{_TEXT_DARK};">
                Total
              </td>
              <td style="border-top:2px solid {_TEXT_DARK};padding:12px 0 0 0;font-size:14px;font-weight:600;color:{_TEXT_DARK};text-align:right;">
                ${total:.2f}
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- Sign-off -->
      <tr>
        <td style="padding:32px 40px 36px 40px;">
          <p style="margin:0;font-size:15px;color:{_TEXT_BODY};line-height:1.6;">
            We'll reach back out shortly. Thanks again!<br>
            <span style="color:{_TEXT_DARK};font-weight:600;">The Thrive Team</span>
          </p>
        </td>
      </tr>"""

    return _base_wrapper(content)


# ── Preview tool (accessible via __main__ only, not in main nav) ─────────────

def show_email_test_interface():
    """Preview and test send email templates."""
    st.title("Email Template Preview")
    st.caption("Preview the email templates before sending.")

    col1, col2 = st.columns(2)
    with col1:
        test_name  = st.text_input("Customer Name", value="Alex")
        test_order = st.text_input("Order Number", value="1042")
        test_email = st.text_input("Send test to", placeholder="your@email.com")
    with col2:
        email_type = st.selectbox("Email Type", ["Fulfillment", "Confirmation"])

    sample_items = [
        {"name": "The Glacier (Brown) w. Ice Cap", "price": 99.99, "qty": 1},
        {"name": "Surge IV (Blue Razzberry)",       "price": 29.99, "qty": 2},
        {"name": "Peak Powder (Chocolate)",          "price": 49.99, "qty": 1},
    ]
    total      = sum(i["price"] * i["qty"] for i in sample_items)
    items_rows = generate_items_html(sample_items)

    if email_type == "Fulfillment":
        html = get_fulfillment_email_html(test_name, test_order, items_rows, total)
    else:
        html = get_confirmation_email_html(test_name, test_order, items_rows, total)

    # Swap cid:logo for base64 in preview
    import base64
    logo_b64 = ""
    if os.path.exists("Thrive.png"):
        with open("Thrive.png", "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
    preview = html.replace('src="cid:logo"', f'src="data:image/png;base64,{logo_b64}"')

    st.markdown("---")
    with st.expander("Email Preview", expanded=True):
        st.components.v1.html(preview, height=750, scrolling=True)

    st.markdown("---")
    if st.button("Send Test Email", type="primary", disabled=not test_email):
        try:
            from dotenv import load_dotenv
            load_dotenv()
            sender = os.getenv("SMTP_SENDER_EMAIL", "").strip().strip('"').strip("'")
            pw     = re.sub(r"\s+", "", os.getenv("SMTP_APP_PASSWORD", "").strip().strip('"').strip("'"))
            if not sender or not pw:
                st.error("SMTP credentials not found in .env")
                return
            msg = MIMEMultipart()
            msg["From"]    = f"Thrive <{sender}>"
            msg["To"]      = test_email
            msg["Subject"] = f"[TEST] {'Thank you' if email_type == 'Fulfillment' else 'We got your order'} #{test_order} – Thrive"
            msg.attach(MIMEText(html, "html"))
            if os.path.exists("Thrive.png"):
                with open("Thrive.png", "rb") as f:
                    logo_img = MIMEImage(f.read())
                    logo_img.add_header("Content-ID", "<logo>")
                    logo_img.add_header("Content-Disposition", "inline; filename=logo.png")
                    msg.attach(logo_img)
            with st.spinner("Sending..."):
                srv = smtplib.SMTP("smtp.gmail.com", 587)
                srv.starttls()
                srv.login(sender, pw)
                srv.send_message(msg)
                srv.quit()
            st.success(f"Test email sent to {test_email}")
        except smtplib.SMTPAuthenticationError:
            st.error("Authentication failed — check SMTP credentials.")
        except Exception as e:
            st.error(f"Failed: {e}")

    with st.expander("Raw HTML"):
        st.code(html, language="html")


if __name__ == "__main__":
    st.set_page_config(page_title="Email Preview", layout="wide")
    show_email_test_interface()
