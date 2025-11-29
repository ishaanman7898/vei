import streamlit as st
import pandas as pd
import os
import json
import re
import time
import smtplib
import io
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

def get_image_path(sku):
    for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.PNG']:
        path = f"product_images/{sku}{ext}"
        if os.path.exists(path):
            return path, ext
    return None, None

def has_image(sku):
    return get_image_path(sku)[0] is not None

def subtract_inventory_from_order(cart, sku_to_name, MASTER, sheet_name):
    """Subtract items from inventory using Google Sheets"""
    try:
        from config import get_service_account_credentials
        import gspread
        from google.oauth2.service_account import Credentials
        
        creds_dict = get_service_account_credentials()
        if not creds_dict:
            return False, "No credentials"
            
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open(sheet_name)
        # Use the first worksheet by default
        sheet = spreadsheet.get_worksheet(0)
        
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Ensure required columns exist
        if "Stock Left" not in df.columns: return False, "Stock Left column missing"
        if "Item Name" not in df.columns: return False, "Item Name column missing"
        
        updates = 0
        for sku, qty in cart.items():
            # Find item by SKU or Name
            match_idx = None
            name = sku_to_name.get(sku, sku)
            
            if "SKU#" in df.columns and sku in df["SKU#"].values:
                match_idx = df[df["SKU#"] == sku].index[0]
            elif name in df["Item Name"].values:
                match_idx = df[df["Item Name"] == name].index[0]
                
            if match_idx is not None:
                current_stock = int(pd.to_numeric(df.loc[match_idx, "Stock Left"], errors='coerce') or 0)
                df.loc[match_idx, "Stock Left"] = current_stock - qty
                updates += 1
        
        if updates > 0:
            # Update status based on new stock levels
            if "Status" in df.columns:
                df["Status"] = df["Stock Left"].apply(lambda x: "Backordered" if int(x) < 0 else "In stock" if int(x) > 10 else "Low stock" if int(x) > 0 else "Out of stock")
            
            sheet.clear()
            sheet.update(values=[df.columns.tolist()] + df.values.tolist(), range_name="A1")
            return True, f"Updated {updates} items"
            
        return True, "No items matched in inventory"
        
    except Exception as e:
        return False, str(e)

def render_entry_tabs(MASTER, sku_to_name, name_to_sku, sku_to_price, inv_config, key_prefix, allow_inventory_subtraction=True):
    entry_tab1, entry_tab2, entry_tab3 = st.tabs(["Single Entry", "Medium Entry", "Large Entry"])
    
    # Initialize cart for this tab
    cart_key = f"cart_{key_prefix}"
    if cart_key not in st.session_state: st.session_state[cart_key] = {}
    
    # --- SINGLE ENTRY ---
    with entry_tab1:
        st.markdown("#### Single Entry")
        c1, c2, c3, c4 = st.columns(4)
        with c1: first_name = st.text_input("First Name", placeholder="Emma", key=f"single_first_name_{key_prefix}")
        with c2: email = st.text_input("Customer Email", key=f"single_email_{key_prefix}")
        with c3: order_num = st.text_input("Order #", value=str(1000 + len(st.session_state.orders) + 1), key=f"single_order_num_{key_prefix}")
        with c4: order_total = st.number_input("Order Total ($)", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"single_order_total_{key_prefix}")
        note = st.text_input("Note (optional)", key=f"single_note_{key_prefix}")
        
        st.markdown("#### Click to Add")
        categories = {}
        for _, row in MASTER.iterrows():
            cat = row["Category"]
            if cat not in categories: categories[cat] = []
            categories[cat].append(row)
        
        sorted_cats = sorted(categories.keys())
        cat_cols = st.columns(len(sorted_cats))
        for col_idx, category in enumerate(sorted_cats):
            with cat_cols[col_idx]:
                st.markdown(f"**{category}**")
                for row in categories[category]:
                    sku = row["SKU#"]
                    name = row["Product name"]
                    price = float(row["Final Price"])
                    count = st.session_state[cart_key].get(sku, 0)
                    label = f"{name}\n${price:.2f}\nAdded: {count}" if count else f"{name}\n${price:.2f}"
                    if not has_image(sku): label += "\n(NO IMAGE)"
                    if st.button(label, key=f"add_{sku}_{key_prefix}", use_container_width=True):
                        st.session_state[cart_key][sku] = count + 1
                        st.rerun()
        
        if st.session_state[cart_key]:
            st.markdown("### Current Cart")
            for sku, qty in list(st.session_state[cart_key].items()):
                name = sku_to_name.get(sku, sku)
                price = sku_to_price.get(sku, 0)
                total = price * qty
                c1, c2, c3, c4 = st.columns([3, 1, 1, 0.5])
                with c1: st.write(f"**{name}**")
                with c2: st.write(f"${price:.2f} x {qty}")
                with c3: st.write(f"${total:.2f}")
                with c4:
                    if st.button("🗑️", key=f"remove_{sku}_{key_prefix}"):
                        del st.session_state[cart_key][sku]
                        st.rerun()
            
            calc_total = sum(sku_to_price.get(s, 0) * q for s, q in st.session_state[cart_key].items())
            missing = [sku_to_name.get(s, s) for s in st.session_state[cart_key] if not has_image(s)]
            disp_total = order_total if order_total > 0 else calc_total
            st.markdown(f"**Cart:** {sum(st.session_state[cart_key].values())} items • **${disp_total:.2f}**")
            
            target_sheet = None
            if allow_inventory_subtraction:
                subtract_inv = st.checkbox("Subtract from Inventory?", value=True, key=f"single_subtract_inv_{key_prefix}")
                if subtract_inv:
                    default_sheet = inv_config.get('sheet_name', 'Inventory Recognition') if inv_config else 'Inventory Recognition'
                    target_sheet = st.text_input("Inventory Sheet Name", value=default_sheet, key=f"single_sheet_{key_prefix}")
            else:
                subtract_inv = False
            
            if st.button("Add to Queue", type="primary", use_container_width=True, key=f"single_add_queue_{key_prefix}"):
                if not first_name or not email:
                    st.error("First Name + Email required")
                else:
                    # Inventory subtraction happens at SEND time now, to allow batch processing
                    # But we store the intent and target sheet
                    
                    st.session_state.orders.append({
                        "First_Name": first_name.strip(),
                        "Full_Name": f"{first_name} – {note}".strip() if note else first_name.strip(),
                        "Email": email.strip(),
                        "Order_Number": order_num,
                        "Order_Total": disp_total,
                        "Cart": st.session_state[cart_key].copy(),
                        "type": "confirmation" if not allow_inventory_subtraction else "fulfillment",
                        "subtract_inventory": subtract_inv,
                        "target_sheet": target_sheet
                    })
                    st.success("✅ Added to queue!")
                    if missing: st.warning(f"Missing images: {', '.join(missing)}")
                    st.session_state[cart_key] = {}
                    st.rerun()

    # --- MEDIUM ENTRY ---
    with entry_tab2:
        st.markdown("#### Medium Entry")
        med_key = f"medium_entry_data_{key_prefix}"
        if med_key not in st.session_state:
            st.session_state[med_key] = pd.DataFrame({
                "First Name": [""] * 5, "Email": [""] * 5, "Order #": [""] * 5,
                "Order Total": [""] * 5, "Products": [""] * 5
            })
        
        edited_df = st.data_editor(st.session_state[med_key], num_rows="dynamic", use_container_width=True, key=f"medium_entry_editor_{key_prefix}")
        st.markdown("---")
        target_sheet = None
        if allow_inventory_subtraction:
            subtract_inv = st.checkbox("Subtract from Inventory?", value=True, key=f"medium_subtract_inv_{key_prefix}")
            if subtract_inv:
                default_sheet = inv_config.get('sheet_name', 'Inventory Recognition') if inv_config else 'Inventory Recognition'
                target_sheet = st.text_input("Inventory Sheet Name", value=default_sheet, key=f"medium_sheet_{key_prefix}")
        else:
            subtract_inv = False
        
        col1, col3 = st.columns([1, 1])
        with col1:
            if st.button("🗑️ Clear Table", key=f"medium_clear_{key_prefix}", use_container_width=True):
                st.session_state[med_key] = pd.DataFrame({
                    "First Name": [""] * 5, "Email": [""] * 5, "Order #": [""] * 5,
                    "Order Total": [""] * 5, "Products": [""] * 5
                })
                st.rerun()
        with col3:
            if st.button("➕ Add All to Queue", type="primary", key=f"medium_add_{key_prefix}", use_container_width=True):
                added = 0
                for _, row in edited_df.iterrows():
                    fname = str(row.get("First Name", "")).strip()
                    email = str(row.get("Email", "")).strip()
                    if not fname or not email or fname=="nan" or email=="nan": continue
                    
                    onum = str(row.get("Order #", "")).strip()
                    ototal_str = str(row.get("Order Total", "0")).strip()
                    try: ototal = float(ototal_str.replace("$", "").replace(",", ""))
                    except: ototal = 0.0
                    
                    prods = str(row.get("Products", "")).strip()
                    cart = {}
                    if prods and prods != "nan":
                        for line in re.split(r'[,\n]', prods):
                            line = line.strip()
                            if not line: continue
                            clean = re.sub(r'\s*[×x]\s*\d+\s*$', '', line).strip()
                            qty_match = re.search(r'[×x]\s*(\d+)\s*$', line)
                            qty = int(qty_match.group(1)) if qty_match else 1
                            sku = None
                            for full, s in name_to_sku.items():
                                if clean.lower() in full.lower() or full.lower() in clean.lower():
                                    sku = s; break
                            if sku: cart[sku] = cart.get(sku, 0) + qty
                    
                    if cart:
                        st.session_state.orders.append({
                            "First_Name": fname, "Full_Name": fname, "Email": email,
                            "Order_Number": onum, "Order_Total": ototal, "Cart": cart,
                            "type": "confirmation" if not allow_inventory_subtraction else "fulfillment",
                            "subtract_inventory": subtract_inv,
                            "target_sheet": target_sheet
                        })
                        added += 1
                if added:
                    st.success(f"✅ Added {added} orders!")
                    st.rerun()

    # --- LARGE ENTRY ---
    with entry_tab3:
        st.markdown("#### Large Entry - CSV Import")
        uploaded = st.file_uploader("Choose CSV", type=["csv"], key=f"csv_upload_{key_prefix}")
        target_sheet = None
        if allow_inventory_subtraction:
            subtract_inv = st.checkbox("Subtract from Inventory?", value=True, key=f"large_subtract_inv_{key_prefix}")
            if subtract_inv:
                default_sheet = inv_config.get('sheet_name', 'Inventory Recognition') if inv_config else 'Inventory Recognition'
                target_sheet = st.text_input("Inventory Sheet Name", value=default_sheet, key=f"large_sheet_{key_prefix}")
        else:
            subtract_inv = False
        
        if uploaded and st.button("IMPORT ALL FROM CSV", type="primary", key=f"large_import_{key_prefix}"):
            df = pd.read_csv(uploaded)
            df.columns = df.columns.str.strip()
            email_col = None
            for col in df.columns:
                col_lower = col.lower().strip()
                if "customer" in col_lower and ("email" in col_lower or "mail" in col_lower):
                    email_col = col; break
            if not email_col:
                st.error("❌ Could not find customer email column!")
                st.stop()
            
            prod_col = "Product(s) Ordered & Quantity"
            for col in df.columns:
                if "product" in col.lower() and "quantity" in col.lower():
                    prod_col = col; break
            
            added = 0
            for _, row in df.iterrows():
                trans = str(row.get("Transaction No.", "Unknown"))
                email = str(row.get(email_col, "")).strip()
                if not email or email in ["nan", ""]: continue
                fname = "Customer"
                if pd.notna(row.get("Customer Name")):
                    fname = str(row["Customer Name"]).split(maxsplit=1)[0]
                
                prods = str(row.get(prod_col, ""))
                cart = {}
                for line in prods.split("\n"):
                    line = line.strip()
                    if not line: continue
                    clean = re.sub(r'[x×]\s*\d+$', '', line, flags=re.IGNORECASE).strip()
                    sku = None
                    for full, s in name_to_sku.items():
                        if clean.lower() in full.lower() or full.lower() in clean.lower():
                            sku = s; break
                    if sku:
                        q_match = re.search(r'[x×]\s*(\d+)$', line, re.IGNORECASE)
                        qty = int(q_match.group(1)) if q_match else 1
                        cart[sku] = cart.get(sku, 0) + qty
                
                if cart:
                    ototal = 0.0
                    try: ototal = float(str(row.get("Order Total", "0")).replace("$","").replace(",",""))
                    except: ototal = sum(sku_to_price.get(s, 0)*q for s,q in cart.items())
                    
                    st.session_state.orders.append({
                        "First_Name": fname, "Full_Name": fname, "Email": email,
                        "Order_Number": trans, "Order_Total": ototal, "Cart": cart,
                        "type": "confirmation" if not allow_inventory_subtraction else "fulfillment",
                        "subtract_inventory": subtract_inv,
                        "target_sheet": target_sheet
                    })
                    added += 1
            st.success(f"Imported {added} valid orders!")
            st.rerun()


def show_email_sender(MASTER, sku_to_name, name_to_sku, sku_to_price, sku_to_category, email_config=None, inv_config=None):
    """Main email sender interface"""
    st.title("Email Sender")
    st.caption("Send automated emails and order confirmations.")
    
    if not email_config:
        st.error("❌ Email credentials not configured. Please go to 'My Settings' to set them up.")
        return

    SENDER_EMAIL = email_config.get("email")
    
    # Handle encrypted password
    password_encrypted = email_config.get("password_encrypted")
    if password_encrypted:
        # Decrypt the password
        from cryptography.fernet import Fernet
        import base64
        
        # Get encryption key
        key_file = "credentials/encryption.key"
        with open(key_file, 'rb') as f:
            key = f.read()
        f = Fernet(key)
        APP_PASSWORD = f.decrypt(password_encrypted.encode()).decode()
    else:
        # Fallback to plain password (for backward compatibility)
        APP_PASSWORD = email_config.get("password")
    
    if not SENDER_EMAIL or not APP_PASSWORD:
         st.error("❌ Incomplete email configuration. Please check 'My Settings'.")
         return
    
    if "orders" not in st.session_state: st.session_state.orders = []
    
    # Main tabs: Automated Email Sender and Order Confirmation
    main_tab1, main_tab2 = st.tabs(["Automated Email Sender", "Automated Order Confirmation"])
    
    # ====================== AUTOMATED EMAIL SENDER ======================
    with main_tab1:
        st.subheader("Automated Email Sender")
        st.caption("**How to use:** Choose an entry method below based on how many orders you need to process.")
        render_entry_tabs(MASTER, sku_to_name, name_to_sku, sku_to_price, inv_config, "tab1")
        
    # ====================== CONFIRMATION SENDER ======================
    with main_tab2:
        st.subheader("Automated Order Confirmation Sender")
        st.caption("This tool uses the same email credentials and queue as the Automated Email Sender.")
        render_entry_tabs(MASTER, sku_to_name, name_to_sku, sku_to_price, inv_config, "tab2", allow_inventory_subtraction=False)

    # ====================== QUEUE & SEND ======================
    if st.session_state.orders:
        st.markdown("---")
        st.subheader(f"Queue – {len(st.session_state.orders)} orders")
        for i, order in enumerate(st.session_state.orders[::-1]):
            total = order.get("Order_Total", sum(sku_to_price.get(s, 0)*q for s,q in order["Cart"].items()))
            c1, c3 = st.columns([4, 1])
            with c1:
                items = ", ".join(f"{sku_to_name.get(s,s)}×{q}" for s,q in order["Cart"].items())
                st.markdown(f"**#{order['Order_Number']}** – {order['First_Name']} – ${total:.2f}<br><small>{items}</small>", unsafe_allow_html=True)
            with c3:
                if st.button("Delete", key=f"del_{i}"):
                    st.session_state.orders.pop(len(st.session_state.orders)-1-i)
                    st.rerun()
        
        if st.button("Delete All in Queue"):
            st.session_state.orders = []
            st.rerun()
        
        if st.button("SEND ALL EMAILS", type="primary", use_container_width=True):
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            prog = st.progress(0)
            sent = 0
            
            for idx, order in enumerate(st.session_state.orders):
                cart = order["Cart"]
                total = order.get("Order_Total", sum(sku_to_price.get(s, 0) * q for s, q in cart.items()))
                items_html = ""
                all_skus = []
                for sku, qty in cart.items():
                    name = sku_to_name.get(sku, sku)
                    price = sku_to_price.get(sku, 0)
                    if qty == 1: items_html += f'<div class="item">• {name} – ${price:.2f}</div>'
                    else: items_html += f'<div class="item">• {name} × {qty} – ${price * qty:.2f}</div>'
                    all_skus.extend([sku] * qty)
                
                msg = MIMEMultipart()
                msg['From'] = f"Thrive <{SENDER_EMAIL}>"
                msg['To'] = order['Email']
                # Determine email type
                order_type = order.get("type", "fulfillment")
                
                msg = MIMEMultipart()
                msg['From'] = f"Thrive <{SENDER_EMAIL}>"
                msg['To'] = order['Email']
                
                if order_type == "confirmation":
                    # --- CONFIRMATION EMAIL (No Images, Simple Text) ---
                    msg['Subject'] = f"We received your order #{order['Order_Number']} – Thrive"
                    
                    html = f"""
                    <html>
                    <head>
                      <style>
                        body {{ font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.7; margin: 0; padding: 20px; background: #f8f9fa; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }}
                        .header {{ background: #ffffff; padding: 20px; text-align: center; border-bottom: 1px solid #eee; }}
                        .header img {{ max-height: 80px; }}
                        .content {{ padding: 40px; }}
                        .greeting {{ font-size: 24px; margin: 0 0 20px 0; color: #333; font-weight: bold; }}
                        .items {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 25px 0; }}
                        .item {{ margin: 12px 0; font-size: 16px; color: #333; }}
                        .blue {{ color: #1E90FF; }}
                      </style>
                    </head>
                    <body>
                      <div class="container">
                        <div class="header">
                          <img src="cid:logo" alt="Thrive Logo">
                        </div>
                        <div class="content">
                          <h2 class="greeting">Hello {order['First_Name']},</h2>
                          <p>We received your order <span class="blue">#{order['Order_Number']}</span>.</p>
                          <p>Here is what you ordered:</p>
                          <div class="items">{items_html}</div>
                          <p><strong>Total:</strong> ${total:.2f}</p>
                          <p>We will process it shortly!</p>
                          <p>Best,<br>The Thrive Team</p>
                        </div>
                      </div>
                    </body>
                    </html>
                    """
                    msg.attach(MIMEText(html, 'html'))
                    
                else:
                    # --- FULFILLMENT EMAIL (With Images, Thank You) ---
                    msg['Subject'] = f"Thank you for your order #{order['Order_Number']} – Thrive"
                    
                    html = f"""
                    <html>
                    <head>
                      <style>
                        body {{ font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.7; margin: 0; padding: 20px; background: #f8f9fa; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }}
                        .header {{ background: #ffffff; padding: 20px; text-align: center; border-bottom: 1px solid #eee; }}
                        .header img {{ max-height: 80px; }}
                        .content {{ padding: 40px; }}
                        .greeting {{ font-size: 24px; margin: 0 0 20px 0; color: #333; font-weight: bold; }}
                        .name {{ color: #333; font-weight: bold; }}
                        .order-info {{ background: #e3f2fd; padding: 15px 20px; border-radius: 10px; font-size: 16px; margin: 20px 0; }}
                        .items {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 25px 0; }}
                        .item {{ margin: 12px 0; font-size: 16px; color: #333; }}
                        .blue {{ color: #1E90FF; }}
                      </style>
                    </head>
                    <body>
                      <div class="container">
                        <div class="header">
                          <img src="cid:logo" alt="Thrive Logo">
                        </div>
                        <div class="content">
                          <h2 class="greeting">Hello <span class="name">{order['First_Name']}</span>,</h2>
                          <p>Thank you for your purchase at <span class="blue">Thrive</span>!</p>
                          <div class="order-info">
                            <strong>Order #:</strong> {order['Order_Number']}<br>
                            <strong>Total:</strong> ${total:.2f}
                          </div>
                          <p>Here's what you ordered:</p>
                          <div class="items">{items_html}</div>
                          <p>We've attached photos of your exact items below!</p>
                          <p>Thank you for supporting us,<br>The Thrive Team</p>
                        </div>
                      </div>
                    </body>
                    </html>
                    """
                    msg.attach(MIMEText(html, 'html'))
                    
                    # Attach product images ONLY for fulfillment
                    for sku in all_skus:
                        path, ext = get_image_path(sku)
                        if path:
                            with open(path, "rb") as f:
                                img = MIMEImage(f.read())
                                img.add_header('Content-Disposition', f'attachment; filename="{sku_to_name.get(sku, sku)}{ext}"')
                                msg.attach(img)
                
                # Attach Logo
                logo_path = "assets/logo.png"
                if os.path.exists(logo_path):
                    with open(logo_path, "rb") as f:
                        logo_img = MIMEImage(f.read())
                        logo_img.add_header('Content-ID', '<logo>')
                        logo_img.add_header('Content-Disposition', 'inline; filename="logo.png"')
                        msg.attach(logo_img)
                    
                    # Handle Inventory Subtraction
                    if order.get("subtract_inventory") and order.get("target_sheet"):
                        success, note = subtract_inventory_from_order(cart, sku_to_name, MASTER, order["target_sheet"])
                        if success:
                            st.toast(f"Inventory updated for {order['First_Name']}: {note}")
                        else:
                            st.error(f"Inventory update failed for {order['First_Name']}: {note}")
                
                try:
                    server.send_message(msg)
                    st.success(f"Sent → {order['First_Name']}")
                    sent += 1
                except Exception as e:
                    st.error(f"Failed → {order['Email']}: {e}")
                prog.progress((idx + 1) / len(st.session_state.orders))
                time.sleep(1)
            
            server.quit()
            st.balloons()
            st.success(f"✅ SUCCESS! Sent {sent}/{len(st.session_state.orders)} emails!")
            st.session_state.orders = []
            time.sleep(2)
            st.rerun()
