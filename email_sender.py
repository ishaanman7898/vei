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
    """Get image URL from Supabase storage for a given SKU"""
    try:
        # Try to get product with image_url
        res = supabase.table("products").select("image_url").eq("sku", sku).execute()
        if hasattr(res, 'data') and res.data and res.data[0].get('image_url'):
            return res.data[0]['image_url']
    except Exception:
        pass
    return None

def get_image_path(sku):
    """Legacy function - checks local files as fallback"""
    for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.PNG']:
        path = f"product-images/{sku}{ext}"
        if os.path.exists(path):
            return path, ext
    return None, None

def get_storage_image_list():
    """Get list of all images in Supabase storage (cached in session state)"""
    # Use session state cache to avoid repeated API calls
    cache_key = "supabase_storage_files"
    cache_time_key = "supabase_storage_files_time"
    
    import time
    current_time = time.time()
    
    # Check if cache exists and is less than 60 seconds old
    if cache_key in st.session_state and cache_time_key in st.session_state:
        if current_time - st.session_state[cache_time_key] < 60:
            return st.session_state[cache_key]
    
    # Fetch fresh data
    try:
        supabase = get_authed_supabase()
        bucket_name = "email-product-pictures"
        file_list = supabase.storage.from_(bucket_name).list()
        files = [f['name'] for f in file_list]
        
        # Cache the result
        st.session_state[cache_key] = files
        st.session_state[cache_time_key] = current_time
        
        return files
    except Exception as e:
        # Return cached data if available, even if expired
        if cache_key in st.session_state:
            return st.session_state[cache_key]
        return []

def has_image(sku, product_df=None):
    """Check if product has an image (Supabase storage or local)"""
    # Check Supabase storage using cached list
    try:
        storage_files = get_storage_image_list()
        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.PNG']:
            filename = f"{sku}{ext}"
            if filename in storage_files:
                return True
    except Exception:
        pass
    
    # Check if product has valid image_url in database
    if product_df is not None:
        try:
            match = product_df[product_df["SKU#"] == sku]
            if not match.empty and 'image_url' in match.columns:
                image_url = match.iloc[0].get('image_url')
                if image_url and str(image_url).strip() and str(image_url) not in ['nan', 'None', '', 'null']:
                    # Verify it's a valid URL
                    url_str = str(image_url).strip()
                    if url_str.startswith('http'):
                        return True
        except Exception:
            pass
    
    # Fallback to local files
    return get_image_path(sku)[0] is not None

def fetch_image_from_url(url):
    """Download image from URL and return bytes"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.content
    except Exception:
        pass
    return None

def load_products_from_supabase():
    """Load products from Supabase and format for email sender compatibility"""
    try:
        supabase = get_authed_supabase()
        res = supabase.table("products").select("*").execute()
        rows = getattr(res, "data", None) or []
    except Exception as e:
        st.error(f"Unable to load products from Supabase: {e}")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()

    # Rename columns to match expected format for email sender
    df = df.rename(columns={
        "category": "Category",
        "name": "Product name", 
        "status": "Product Status",
        "sku": "SKU#",
        "price": "Final Price",
    })

    # Ensure required columns exist
    required_cols = ["Category", "Product name", "Product Status", "SKU#", "Final Price"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
    
    # Keep image_url if it exists
    if 'image_url' not in df.columns:
        df['image_url'] = ""

    df["Product name"] = df["Product name"].astype(str).str.strip()
    df["Category"] = df["Category"].astype(str).str.strip()
    df["SKU#"] = df["SKU#"].astype(str).str.strip()
    
    return df

def subtract_inventory_from_order_supabase(cart, sku_to_name, MASTER):
    """Subtract items from inventory using Supabase"""
    try:
        supabase = get_authed_supabase()
        
        # Load current inventory
        res = supabase.table("inventory").select("*").execute()
        rows = getattr(res, "data", None) or []
        if not rows:
            return False, "No inventory data found"
        
        inv_df = pd.DataFrame(rows)
        inv_df["sku"] = inv_df["sku"].astype(str).str.strip()
        
        updates = 0
        for sku, qty in cart.items():
            sku_str = str(sku).strip()
            name = sku_to_name.get(sku, sku)
            
            # Find inventory record by SKU
            match = inv_df[inv_df["sku"] == sku_str]
            if match.empty:
                # Try by item name as fallback
                name_match = inv_df[inv_df["item_name"] == name]
                if not name_match.empty:
                    match = name_match
            
            if not match.empty:
                existing = match.iloc[0]
                current_stock = int(existing.get("stock_left", 0))
                new_stock = current_stock - qty
                
                # Calculate new status
                if new_stock < 0:
                    status = "Backordered"
                elif new_stock == 0:
                    status = "Out of stock"
                elif new_stock <= 10:
                    status = "Low stock"
                else:
                    status = "In stock"
                
                # Update inventory in Supabase
                supabase.table("inventory").update({
                    "stock_left": new_stock,
                    "status": status
                }).eq("sku", sku_str).execute()
                updates += 1
        
        if updates > 0:
            return True, f"Updated {updates} items in Supabase"
        else:
            return True, "No items matched in inventory"
            
    except Exception as e:
        return False, f"Supabase error: {str(e)}"

def subtract_inventory_from_order(cart, sku_to_name, MASTER, sheet_name):
    """Legacy wrapper - use Supabase version"""
    return subtract_inventory_from_order_supabase(cart, sku_to_name, MASTER)

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
            # Get values with safe defaults
            sku = str(row.get("SKU#", "")).strip()
            cat = str(row.get("Category", "Other")).strip()
            name = str(row.get("Product name", "")).strip()
            status = str(row.get("Product Status", "")).strip()
            
            # Skip rows with missing essential data
            if not sku or not name or sku.lower() in ["nan", "none", ""] or name.lower() in ["nan", "none", ""]:
                continue
            
            # Filter out Phased Out products - they should never be sent in emails
            if status and status.lower() == "phased out":
                continue
            
            # Use "Other" category if empty
            if not cat or cat.lower() in ["nan", "none", ""]:
                cat = "Other"
            
            if cat not in categories: 
                categories[cat] = []
            categories[cat].append(row)
        
        sorted_cats = sorted(categories.keys())
        if not sorted_cats:
            st.warning("No products available to add.")
        else:
            cat_cols = st.columns(len(sorted_cats))
            for col_idx, category in enumerate(sorted_cats):
                with cat_cols[col_idx]:
                    st.markdown(f"**{category}**")
                    for idx, row in enumerate(categories[category]):
                        sku = row["SKU#"]
                        name = row["Product name"]
                        price = float(row.get("Final Price", 0))
                        count = st.session_state[cart_key].get(sku, 0)
                        
                        # Build label with NO IMAGE indicator
                        if not has_image(sku, MASTER):
                            if count:
                                label = f"{name}\n${price:.2f}\nAdded: {count}\n🚫 NO IMAGE"
                            else:
                                label = f"{name}\n${price:.2f}\n🚫 NO IMAGE"
                        else:
                            label = f"{name}\n${price:.2f}\nAdded: {count}" if count else f"{name}\n${price:.2f}"
                        
                        if st.button(label, key=f"add_{sku}_{key_prefix}_{col_idx}_{idx}_{count}", use_container_width=True):
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
            missing = [sku_to_name.get(s, s) for s in st.session_state[cart_key] if not has_image(s, MASTER)]
            disp_total = order_total if order_total > 0 else calc_total
            st.markdown(f"**Cart:** {sum(st.session_state[cart_key].values())} items • **${disp_total:.2f}**")
            
            # Show warning if products missing images
            if missing:
                st.error(f"⚠️ **Cannot send email - Missing images for:** {', '.join(missing)}")
                st.info("💡 Add images in Product Management → Product Images tab")
            
            target_sheet = None
            if allow_inventory_subtraction:
                subtract_inv = st.checkbox("Subtract from Inventory?", value=True, key=f"single_subtract_inv_{key_prefix}")
                if subtract_inv:
                    default_sheet = inv_config.get('sheet_name', 'VEI Inventory') if inv_config else 'VEI Inventory'
                    target_sheet = st.text_input("Inventory Sheet Name", value=default_sheet, key=f"single_sheet_{key_prefix}")
            else:
                subtract_inv = False
            
            if st.button("Add to Queue", type="primary", use_container_width=True, key=f"single_add_queue_{key_prefix}", disabled=len(missing) > 0):
                if not first_name or not email:
                    st.error("First Name + Email required")
                elif missing:
                    st.error(f"Cannot add to queue - Missing images for: {', '.join(missing)}")
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
                    st.success("✅ Order added to queue!")
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
        # Update session state with edited dataframe
        st.session_state[med_key] = edited_df
        
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
                skipped_missing_images = []
                
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
                            # Validate product is not phased out before adding to cart
                            if sku:
                                # Check product status in MASTER
                                product_row = MASTER[MASTER["SKU#"] == sku]
                                if not product_row.empty:
                                    status = str(product_row.iloc[0].get("Product Status", "")).strip()
                                    if status and status.lower() == "phased out":
                                        continue  # Skip phased out products
                                cart[sku] = cart.get(sku, 0) + qty
                    
                    if cart:
                        # Check for missing images
                        missing = [sku_to_name.get(s, s) for s in cart.keys() if not has_image(s, MASTER)]
                        if missing:
                            skipped_missing_images.append(f"{fname} (Order #{onum}): {', '.join(missing)}")
                            continue
                        
                        st.session_state.orders.append({
                            "First_Name": fname, "Full_Name": fname, "Email": email,
                            "Order_Number": onum, "Order_Total": ototal, "Cart": cart,
                            "type": "confirmation" if not allow_inventory_subtraction else "fulfillment",
                            "subtract_inventory": subtract_inv,
                            "target_sheet": target_sheet
                        })
                        added += 1
                
                if skipped_missing_images:
                    st.error(f"⚠️ **Skipped {len(skipped_missing_images)} orders - Missing images:**")
                    for skip_msg in skipped_missing_images:
                        st.warning(skip_msg)
                    st.info("💡 Add images in Product Management → Product Images tab")
                
                if added:
                    st.success(f"✅ Added {added} orders to queue!")
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
            skipped_missing_images = []
            
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
                    # Validate product is not phased out before adding to cart
                    if sku:
                        # Check product status in MASTER
                        product_row = MASTER[MASTER["SKU#"] == sku]
                        if not product_row.empty:
                            status = str(product_row.iloc[0].get("Product Status", "")).strip()
                            if status and status.lower() == "phased out":
                                continue  # Skip phased out products
                        q_match = re.search(r'[x×]\s*(\d+)$', line, re.IGNORECASE)
                        qty = int(q_match.group(1)) if q_match else 1
                        cart[sku] = cart.get(sku, 0) + qty
                
                if cart:
                    # Check for missing images
                    missing = [sku_to_name.get(s, s) for s in cart.keys() if not has_image(s, MASTER)]
                    if missing:
                        skipped_missing_images.append(f"{fname} (Order #{trans}): {', '.join(missing)}")
                        continue
                    
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
            
            if skipped_missing_images:
                st.error(f"⚠️ **Skipped {len(skipped_missing_images)} orders - Missing images:**")
                for skip_msg in skipped_missing_images[:10]:  # Show first 10
                    st.warning(skip_msg)
                if len(skipped_missing_images) > 10:
                    st.warning(f"... and {len(skipped_missing_images) - 10} more")
                st.info("💡 Add images in Product Management → Product Images tab")
            
            if added > 0:
                st.success(f"✅ Imported {added} valid orders to queue!")
            else:
                st.warning("No valid orders found in CSV.")
            st.rerun()


def show_email_sender(email_config=None, inv_config=None):
    """Main email sender interface"""
    st.title("📧 Email Sender")
    st.caption("Send automated fulfillment and confirmation emails to customers.")
    
    # Load products from Supabase
    MASTER = load_products_from_supabase()
    if MASTER.empty:
        st.error("No products found. Please add products in Product Management first.")
        return
    
    # Create lookup dictionaries
    sku_to_name = dict(zip(MASTER["SKU#"], MASTER["Product name"]))
    name_to_sku = {v: k for k, v in sku_to_name.items()}
    sku_to_price = {sku: float(p) for sku, p in zip(MASTER["SKU#"], MASTER["Final Price"])}
    sku_to_category = dict(zip(MASTER["SKU#"], MASTER["Category"]))

    # Get SMTP credentials from environment
    try:
        SENDER_EMAIL = st.secrets.get("SMTP_SENDER_EMAIL")
        APP_PASSWORD = st.secrets.get("SMTP_APP_PASSWORD")
    except Exception:
        SENDER_EMAIL = None
        APP_PASSWORD = None

    SENDER_EMAIL = SENDER_EMAIL or os.getenv("SMTP_SENDER_EMAIL")
    APP_PASSWORD = APP_PASSWORD or os.getenv("SMTP_APP_PASSWORD")

    if APP_PASSWORD:
        APP_PASSWORD = re.sub(r"\s+", "", str(APP_PASSWORD))

    if not SENDER_EMAIL or not APP_PASSWORD:
        st.error("❌ Email credentials not configured. Set SMTP_SENDER_EMAIL and SMTP_APP_PASSWORD in environment variables.")
        return
    
    if "orders" not in st.session_state: 
        st.session_state.orders = []
    
    # Entry tabs
    render_entry_tabs(MASTER, sku_to_name, name_to_sku, sku_to_price, inv_config, "tab1")
    
    # Refresh image cache button
    st.markdown("---")
    if st.button("🔄 Refresh Image Cache", help="Refresh image availability from Supabase"):
        if "supabase_storage_files" in st.session_state:
            del st.session_state["supabase_storage_files"]
        if "supabase_storage_files_time" in st.session_state:
            del st.session_state["supabase_storage_files_time"]
        st.success("Image cache refreshed!")
        st.rerun()

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
        
        # Check if any orders have products without images
        orders_with_missing_images = []
        for order in st.session_state.orders:
            missing = [sku_to_name.get(s, s) for s in order["Cart"].keys() if not has_image(s, MASTER)]
            if missing:
                orders_with_missing_images.append({
                    "order": order,
                    "missing": missing
                })
        
        if orders_with_missing_images:
            st.error(f"⚠️ **Cannot send - {len(orders_with_missing_images)} orders have products without images:**")
            for item in orders_with_missing_images[:5]:  # Show first 5
                st.warning(f"Order #{item['order']['Order_Number']} ({item['order']['First_Name']}): {', '.join(item['missing'])}")
            if len(orders_with_missing_images) > 5:
                st.warning(f"... and {len(orders_with_missing_images) - 5} more orders")
            st.info("💡 Remove these orders from queue or add images in Product Management → Product Images tab")
        
        if st.button("SEND ALL EMAILS", type="primary", use_container_width=True, disabled=len(orders_with_missing_images) > 0):
            if orders_with_missing_images:
                st.error("Cannot send - some orders have products without images. Please fix or remove them from queue.")
                st.stop()
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            prog = st.progress(0)
            sent = 0
            
            for idx, order in enumerate(st.session_state.orders):
                cart = order["Cart"].copy()  # Work with a copy
                
                # Final safety check: Remove any phased out products before sending
                phased_out_removed = []
                for sku in list(cart.keys()):
                    product_row = MASTER[MASTER["SKU#"] == sku]
                    if not product_row.empty:
                        status = str(product_row.iloc[0].get("Product Status", "")).strip()
                        if status and status.lower() == "phased out":
                            phased_out_removed.append(sku_to_name.get(sku, sku))
                            del cart[sku]
                
                # Skip this order if all products were phased out
                if not cart:
                    st.warning(f"Skipped order #{order['Order_Number']} - all products are phased out")
                    continue
                
                # Show warning if some products were removed
                if phased_out_removed:
                    st.warning(f"Removed phased out products from order #{order['Order_Number']}: {', '.join(phased_out_removed)}")
                
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
                    
                    # Generate items HTML using the new template function
                    items_list = []
                    for sku, qty in cart.items():
                        name = sku_to_name.get(sku, sku)
                        price = sku_to_price.get(sku, 0)
                        items_list.append({"name": name, "price": price, "qty": qty})
                    
                    items_html = generate_items_html(items_list)
                    
                    # Use the new fulfillment email template
                    html = get_fulfillment_email_html(order['First_Name'], order['Order_Number'], items_html, total)
                    msg.attach(MIMEText(html, 'html'))
                    
                    # Attach product images ONLY for fulfillment
                    supabase = get_authed_supabase()
                    for sku in all_skus:
                        # Try Supabase first
                        image_url = get_image_url_from_supabase(sku, supabase)
                        image_data = None
                        filename = f"{sku_to_name.get(sku, sku)}.jpg"
                        
                        if image_url:
                            image_data = fetch_image_from_url(image_url)
                        
                        # Fallback to local files if Supabase fails
                        if not image_data:
                            path, ext = get_image_path(sku)
                            if path:
                                with open(path, "rb") as f:
                                    image_data = f.read()
                                filename = f"{sku_to_name.get(sku, sku)}{ext}"
                        
                        if image_data:
                            img = MIMEImage(image_data)
                            img.add_header('Content-Disposition', f'attachment; filename="{filename}"')
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
                    if order.get("subtract_inventory"):
                        success, note = subtract_inventory_from_order_supabase(cart, sku_to_name, MASTER)
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
                time.sleep(0.75)
            
            server.quit()
            
            # Show notification at top of page
            st.success(f"✅ **All emails sent successfully!** {sent}/{len(st.session_state.orders)} emails delivered.")
            st.info(f"📧 Email batch completed. All {sent} order{'s' if sent != 1 else ''} have been processed and sent.")
            
            st.session_state.orders = []
            time.sleep(2)
            st.rerun()
