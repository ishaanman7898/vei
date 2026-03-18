import streamlit as st
import pandas as pd
import os
import json
import re
import time
import smtplib
import io
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from supabase_client import get_authed_supabase
from email_templates import get_fulfillment_email_html, generate_items_html

def get_image_url_from_supabase(sku, supabase):
    """Get image URL from inventory table for a given SKU"""
    try:
        res = supabase.table("inventory").select("image_url").eq("sku", sku).execute()
        if hasattr(res, 'data') and res.data and res.data[0].get('image_url'):
            image_url = res.data[0]['image_url']
            if image_url and image_url != 'N/A':
                return image_url
    except Exception:
        pass
    return None

def fetch_image_from_url(url):
    """Download image from URL and return bytes"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.content
    except Exception:
        pass
    return None

@st.cache_data(ttl=600)
def load_products_from_supabase():
    """Load products from inventory table for email sender"""
    try:
        supabase = get_authed_supabase()
        res = supabase.table("inventory").select("*").execute()
        rows = getattr(res, "data", None) or []
    except Exception as e:
        st.error(f"Unable to load inventory from Supabase: {e}")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()

    df = df.rename(columns={
        "category": "Category",
        "item_name": "Product name", 
        "status": "Product Status",
        "sku": "SKU#",
        "price": "Final Price",
    })

    required_cols = ["Category", "Product name", "Product Status", "SKU#", "Final Price"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
    
    if 'image_url' not in df.columns:
        df['image_url'] = ""

    df["Product name"] = df["Product name"].astype(str).str.strip()
    df["Category"] = df["Category"].astype(str).str.strip()
    df["SKU#"] = df["SKU#"].astype(str).str.strip()
    
    if "Final Price" in df.columns:
        df["Final Price"] = df["Final Price"].fillna(0.0)
    
    return df

def subtract_inventory_from_order_supabase(cart, sku_to_name):
    """Subtract items from inventory using Supabase and return before/after stock info"""
    stock_info = []
    try:
        supabase = get_authed_supabase()
        res = supabase.table("inventory").select("*").execute()
        rows = getattr(res, "data", None) or []
        if not rows:
            return False, "No inventory data found", []
        
        inv_df = pd.DataFrame(rows)
        inv_df["sku"] = inv_df["sku"].astype(str).str.strip()
        
        updates = 0
        for sku, qty in cart.items():
            sku_str = str(sku).strip()
            name = sku_to_name.get(sku, sku)
            match = inv_df[inv_df["sku"] == sku_str]
            if match.empty:
                name_match = inv_df[inv_df["item_name"] == name]
                if not name_match.empty: match = name_match
            
            if not match.empty:
                existing = match.iloc[0]
                stock_raw = existing.get("stock_left")
                current_stock = int(stock_raw) if stock_raw is not None else 0
                new_stock = current_stock - qty
                
                status = "In stock"
                if new_stock < 0: status = "Backordered"
                elif new_stock == 0: status = "Out of stock"
                elif new_stock <= 10: status = "Low stock"
                
                supabase.table("inventory").update({
                    "stock_left": new_stock,
                    "status": status
                }).eq("sku", sku_str).execute()
                
                stock_info.append({
                    "Product": name, "Before": current_stock, "Change": -qty, "After": new_stock
                })
                updates += 1
        
        if updates > 0:
            st.cache_data.clear()
            return True, f"Updated {updates} items", stock_info
        return True, "No items matched", []
    except Exception as e:
        return False, f"Supabase error: {str(e)}", []

def parse_product_string(prods, name_to_sku, MASTER):
    """Extremely robust regex parser for products and quantities"""
    cart = {}
    if not prods or str(prods).lower() in ["nan", "none", "null", ""]:
        return cart

    all_names = [str(n).strip() for n in name_to_sku.keys() if n and str(n).strip()]
    if not all_names: return cart
    
    sorted_names = sorted(all_names, key=len, reverse=True)
    escaped_names = [re.escape(name) for name in sorted_names]
    qty_suffix = r"(?:\s*[x×\*]\s*(\d+))?"
    pattern = re.compile(f"({'|'.join(escaped_names)}){qty_suffix}", re.IGNORECASE)
    
    for match in pattern.finditer(str(prods)):
        name_matched = match.group(1)
        qty = int(match.group(2)) if match.group(2) else 1
        canonical_name = next((n for n in sorted_names if n.lower() == name_matched.lower()), name_matched)
        sku = name_to_sku.get(canonical_name)
        if sku: cart[sku] = cart.get(sku, 0) + qty
            
    return cart

def show_email_sender():
    """Main email sender interface"""
    st.title("Email Sender")
    
    MASTER = load_products_from_supabase()
    if MASTER.empty:
        st.error("No products found in inventory.")
        return
    
    sku_to_name = dict(zip(MASTER["SKU#"], MASTER["Product name"]))
    name_to_sku = {v: k for k, v in sku_to_name.items()}
    sku_to_price = {sku: float(p) if p is not None else 0.0 for sku, p in zip(MASTER["SKU#"], MASTER["Final Price"])}

    try:
        SENDER_EMAIL = st.secrets.get("SMTP_SENDER_EMAIL")
        APP_PASSWORD = st.secrets.get("SMTP_APP_PASSWORD")
    except Exception:
        SENDER_EMAIL = os.getenv("SMTP_SENDER_EMAIL")
        APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")

    if not SENDER_EMAIL or not APP_PASSWORD:
        st.error("❌ Email credentials not configured.")
        return
    
    if "orders" not in st.session_state: st.session_state.orders = []

    st.subheader("Manual & CSV Entry")
    st.caption("Paste data directly into the table. Use the CSV uploader to bulk-fill the table.")

    entry_key = "order_entry_data"
    if entry_key not in st.session_state:
        st.session_state[entry_key] = pd.DataFrame({
            "First Name": [""] * 10, "Email": [""] * 10, "Order #": [""] * 10,
            "Order Total": [""] * 10, "Products": [""] * 10
        })

    with st.expander("📂 Import from CSV"):
        uploaded_csv = st.file_uploader("Upload CSV", type=["csv"], key="entry_csv")
        if uploaded_csv and st.button("Apply CSV Data to Table"):
            try:
                df_csv = pd.read_csv(uploaded_csv)
                df_csv.columns = df_csv.columns.str.strip()
                email_col = next((c for c in df_csv.columns if "email" in c.lower()), None)
                name_col = next((c for c in df_csv.columns if "name" in c.lower()), None)
                order_col = next((c for c in df_csv.columns if "order" in c.lower() and "#" in c.lower() or "transaction" in c.lower()), None)
                prod_col = next((c for c in df_csv.columns if "product" in c.lower()), None)
                total_col = next((c for c in df_csv.columns if "total" in c.lower()), None)

                new_rows = []
                for _, row in df_csv.iterrows():
                    fname = str(row.get(name_col, "")).split()[0] if name_col and pd.notna(row.get(name_col)) else ""
                    new_rows.append({
                        "First Name": fname, "Email": str(row.get(email_col, "")),
                        "Order #": str(row.get(order_col, "")), "Order Total": str(row.get(total_col, "0")),
                        "Products": str(row.get(prod_col, ""))
                    })
                st.session_state[entry_key] = pd.DataFrame(new_rows)
                st.success("CSV applied. You can now edit the table below.")
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")

    # The table is the source of truth
    edited_df = st.data_editor(st.session_state[entry_key], num_rows="dynamic", width='stretch', key="entry_editor")

    st.markdown("---")

    # Center the subtract inventory checkbox
    _, center_col, _ = st.columns([1, 1, 1])
    with center_col:
        subtract_inv = st.checkbox("Subtract from Inventory?", value=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Table", width='stretch'):
            st.session_state[entry_key] = pd.DataFrame({
                "First Name": [""] * 10, "Email": [""] * 10, "Order #": [""] * 10,
                "Order Total": [""] * 10, "Products": [""] * 10
            })
            st.rerun()
    with col2:
        if st.button("➕ Add All to Queue", type="primary", width='stretch'):
            # Save changes before processing
            st.session_state[entry_key] = edited_df
            added = 0
            for _, row in edited_df.iterrows():
                fname, email = str(row.get("First Name", "")).strip(), str(row.get("Email", "")).strip()
                if not fname or not email or fname=="nan": continue
                onum = str(row.get("Order #", "")).strip()
                ototal_str = str(row.get("Order Total", "0")).strip()
                try: ototal = float(ototal_str.replace("$", "").replace(",", ""))
                except: ototal = 0.0
                cart = parse_product_string(row.get("Products", ""), name_to_sku, MASTER)
                if cart:
                    st.session_state.orders.append({
                        "First_Name": fname, "Email": email, "Order_Number": onum,
                        "Order_Total": ototal, "Cart": cart, "type": "fulfillment",
                        "subtract_inventory": subtract_inv
                    })
                    added += 1
            if added: st.success(f"✅ Added {added} orders!"); st.rerun()

    if st.session_state.orders:
        st.markdown("---")
        st.subheader(f"Queue – {len(st.session_state.orders)} orders")
        for i, order in enumerate(st.session_state.orders[::-1]):
            c1, c2 = st.columns([4, 1])
            with c1:
                items = ", ".join([f"{sku_to_name.get(s, s)}×{q}" for s, q in order["Cart"].items()])
                st.markdown(f"**#{order['Order_Number']}** – {order['First_Name']} – ${order['Order_Total']:.2f}<br><small>{items}</small>", unsafe_allow_html=True)
            with c2:
                if st.button("Delete", key=f"del_{i}"):
                    st.session_state.orders.pop(len(st.session_state.orders)-1-i); st.rerun()
        
        if st.button("SEND ALL EMAILS", type="primary", width='stretch'):
            server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER_EMAIL, APP_PASSWORD)
            prog = st.progress(0); all_stock_changes = []
            for idx, order in enumerate(st.session_state.orders):
                cart, total = order["Cart"], order["Order_Total"]
                msg = MIMEMultipart(); msg['From'] = f"Thrive <{SENDER_EMAIL}>"; msg['To'] = order['Email']
                items_list = [{"name": sku_to_name.get(s, s), "price": sku_to_price.get(s, 0), "qty": q} for s, q in cart.items()]
                items_rows = generate_items_html(items_list)
                
                msg['Subject'] = f"Thank you for your order #{order['Order_Number']} – Thrive"
                html = get_fulfillment_email_html(order['First_Name'], order['Order_Number'], items_rows, total)
                
                # Attach images
                supabase = get_authed_supabase()
                for sku, qty in cart.items():
                    for _ in range(qty):
                        url = get_image_url_from_supabase(sku, supabase); data = fetch_image_from_url(url) if url else None
                        if data:
                            img = MIMEImage(data); img.add_header('Content-Disposition', f'attachment; filename="{sku_to_name.get(sku, sku)}.jpg"'); msg.attach(img)
                
                msg.attach(MIMEText(html, 'html'))
                if os.path.exists("Thrive.png"):
                    with open("Thrive.png", "rb") as f:
                        logo_img = MIMEImage(f.read()); logo_img.add_header('Content-ID', '<logo>'); msg.attach(logo_img)
                
                if order.get("subtract_inventory"):
                    success, note, stock_info = subtract_inventory_from_order_supabase(cart, sku_to_name)
                    if success: all_stock_changes.extend(stock_info)
                
                server.send_message(msg); prog.progress((idx + 1) / len(st.session_state.orders)); time.sleep(0.5)
            server.quit(); st.session_state.orders = []; st.success("✅ All emails sent!")
            if all_stock_changes:
                st.markdown("### 📊 Inventory Impact")
                impact_df = pd.DataFrame(all_stock_changes)
                summary = impact_df.groupby("Product").agg({"Before": "first", "Change": "sum", "After": "last"}).reset_index()
                st.table(summary); st.bar_chart(summary.set_index("Product")["Change"])
            st.button("Done", on_click=lambda: st.rerun())
