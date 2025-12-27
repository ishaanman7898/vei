import streamlit as st
import pandas as pd
import os
import json
import re
import pdfplumber
from supabase_client import get_authed_supabase


def _inventory_status_from_stock_left(stock_left: int) -> str:
    try:
        x = int(stock_left)
    except Exception:
        x = 0
    if x < 0:
        return "Backordered"
    if x == 0:
        return "Out of stock"
    if x <= 10:
        return "Low stock"
    return "In stock"


def _safe_int(val, default=0) -> int:
    try:
        if pd.isna(val):
            return int(default)
        return int(float(str(val).replace(",", "").strip()))
    except Exception:
        return int(default)


def load_master():
    """Load Supabase products as the master product list."""
    try:
        supabase = get_authed_supabase()
        res = supabase.table("products").select("name,category,status,sku,price").execute()
        rows = getattr(res, "data", None) or []
    except Exception as e:
        st.error(f"Unable to load products from Supabase: {e}")
        st.stop()

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["Category", "Product name", "Product Status", "SKU#", "Final Price"])
        return df

    df = df.rename(columns={
        "category": "Category",
        "name": "Product name",
        "status": "Product Status",
        "sku": "SKU#",
        "price": "Final Price",
    })

    df["Product name"] = df["Product name"].astype(str).str.strip()
    df["Category"] = df["Category"].astype(str).str.strip()
    df["SKU#"] = df["SKU#"].astype(str).str.strip()
    
    # Normalize product names (add space before x)
    df["Product name"] = df["Product name"].apply(
        lambda x: re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', str(x)) if pd.notna(x) else x
    )
    df["Product name"] = df["Product name"].apply(
        lambda x: re.sub(r'(\w)x([A-Z])', r'\1 x \2', str(x)) if pd.notna(x) else x
    )
    
    # Clean price
    def clean_price(x):
        if pd.isna(x) or x == "" or str(x).lower() in ["nan", "none", ""]:
            return 0.0
        if isinstance(x, str): 
            x = x.replace("$", "").replace(",", "").strip()
        try:
            return float(x or 0)
        except:
            return 0.0
    
    df["Final Price"] = df["Final Price"].apply(clean_price)
    
    # Remove rows with empty/invalid SKUs
    df = df[df["SKU#"].notna() & (df["SKU#"].str.strip() != "")]
    df = df[df["Product name"].notna() & (df["Product name"].str.strip() != "")]
    
    return df

def load_inventory():
    """Load inventory data from Supabase"""
    try:
        supabase = get_authed_supabase()
        res = supabase.table("inventory").select("*").execute()
        rows = getattr(res, "data", None) or []
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Unable to load inventory from Supabase: {e}")
        return pd.DataFrame()

def load_inventory_summary():
    """Load inventory summary from Supabase view"""
    try:
        supabase = get_authed_supabase()
        res = supabase.table("inventory_summary").select("*").execute()
        rows = getattr(res, "data", None) or []
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Unable to load inventory summary from Supabase: {e}")
        return pd.DataFrame()

def load_phased_products():
    """Load PPwP.csv (Phased Products with Prices) for legacy product names"""
    if os.path.exists("PPwP.csv"):
        try:
            df = pd.read_csv("PPwP.csv")
            df["Product name"] = df["Product name"].str.strip()
            return df
        except Exception as e:
            st.warning(f"Could not load PPwP.csv: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def get_legacy_product_mapping():
    """Map legacy product names to current SKUs from PPwP.csv"""
    mapping = {}
    df = load_phased_products()
    if not df.empty:
        for _, row in df.iterrows():
            product_name = str(row["Product name"]).strip()
            sku = str(row["SKU#"]).strip()
            mapping[product_name] = sku
    return mapping

def pdf_to_csv_converter(pdf_file):
    """Convert PDF invoice to CSV format matching Zamzar output"""
    try:
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        # Extract metadata
        invoice_num = "Unknown"
        invoice_date = ""
        discount_date = ""
        due_date = ""
        invoice_total = ""
        order_placed_by = ""
        po_number = ""
        
        # Parse header information
        for i, line in enumerate(lines):
            if "Invoice number:" in line or "invoice number:" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    invoice_num = parts[1].strip().split()[0]
            elif "Invoice date:" in line or "invoice date:" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    invoice_date = parts[1].strip()
            elif "Discount date:" in line or "discount date:" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    discount_date = parts[1].strip()
            elif "Due date:" in line or "due date:" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    due_date = parts[1].strip()
            elif "Invoice total:" in line or "invoice total:" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    invoice_total = parts[1].strip()
            elif "Order placed by:" in line or "order placed by:" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    order_placed_by = parts[1].strip()
        
        # Build CSV structure
        csv_lines = []
        csv_lines.append("VE Wholesale Marketplace,,,,,")
        csv_lines.append(",,,,Invoice,")
        csv_lines.append("Email: wholesalemarketplace@veinternational.org,,,,,")
        csv_lines.append(f"Invoice number:,{invoice_num},To:,,,")
        csv_lines.append(f"Invoice date:,{invoice_date},Thrive Wellness,,,")
        csv_lines.append(f"Discount date:,{discount_date},2590 Ogden Ave,,,")
        csv_lines.append(f"Due date:,{due_date},\"Aurora, IL 60504\",,,")
        csv_lines.append(f"Invoice total:,{invoice_total},,,,")
        csv_lines.append(f"Order placed by:,{order_placed_by},,,,")
        csv_lines.append("Your PO number/Reference:,,,,,")
        csv_lines.append("Item,,SKU#,Unit price,Quantity,Amount")
        
        # Parse items from PDF (this is a simplified parser)
        csv_lines.append("Shipping cost (Ground Shipping),,,,$0.00,")
        csv_lines.append(f",,,Subtotal:,{invoice_total},")
        csv_lines.append(",,,Tax:,$0.00,")
        csv_lines.append(f",,Grand total:,,{invoice_total},")
        csv_lines.append("Please send your payment to:,,,,,")
        csv_lines.append("VE Wholesale Marketplace,,,,,")
        csv_lines.append("Bank account number: 630907145,,,,,")
        csv_lines.append(f"\"Amount: {invoice_total}\",,,,,")
        csv_lines.append(f"Payment description: INVOICE NUMBER {invoice_num},,,,,")
        csv_lines.append("Note: Please pay this invoice in a single payment. Do not combine payment of this invoice and other invoices in one payment.,,,,,")
        csv_lines.append("Payment Terms,,,,,")
        csv_lines.append("\"2% 10, Net 30 from date of invoice. Past due invoices will be charged 1.5% interest per month outstanding.\",,,,,")
        csv_lines.append("This document is used for educational purposes.,,,,,")
        
        return "\n".join(csv_lines)
    except Exception as e:
        st.error(f"Error converting PDF: {e}")
        return None

def parse_invoice(file, MASTER):
    """Parse invoice file (PDF or CSV) and extract items"""
    items = {}
    invoice_num = "Unknown"
    invoice_date = None
    due_date = None
    invoice_total = None
    
    if file.name.endswith(".pdf"):
        # PDF parsing
        try:
            with pdfplumber.open(file) as pdf:
                all_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text += text + "\n"
                
                lines = all_text.split("\n")
                
                # Extract metadata
                for line in lines:
                    line_lower = line.lower()
                    if "invoice number:" in line_lower:
                        parts = line.split(":")
                        if len(parts) > 1:
                            invoice_num = parts[1].strip().split()[0]
                    elif "invoice date:" in line_lower:
                        parts = line.split(":")
                        if len(parts) > 1:
                            invoice_date = parts[1].strip().split("To:")[0].strip()
                    elif "due date:" in line_lower:
                        parts = line.split(":")
                        if len(parts) > 1:
                            invoice_date_parts = parts[1].strip().split()
                            if invoice_date_parts:
                                due_date = " ".join(invoice_date_parts[:3])  # Get date part
                    elif "invoice total:" in line_lower:
                        parts = line.split(":")
                        if len(parts) > 1:
                            total_str = parts[1].strip().replace("$", "").replace(",", "")
                            try:
                                invoice_total = float(total_str)
                            except:
                                pass
                
                # Find the header line
                header_idx = None
                for idx, line in enumerate(lines):
                    if "Item" in line and "SKU#" in line and "Quantity" in line:
                        header_idx = idx
                        break
                
                # Parse product lines
                if header_idx is not None:
                    skip_keywords = ['shipping', 'ground shipping', 'subtotal', 'total', 'tax', 'grand total',
                                   'please send', 'payment', 'bank', 'note:', 'payment terms', 'this document',
                                   'past due', 'interest', 'net 30', 'discount', '%']
                    
                    for line in lines[header_idx + 1:]:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Skip summary/footer lines
                        line_lower = line.lower()
                        should_skip = False
                        for keyword in skip_keywords:
                            if keyword in line_lower:
                                should_skip = True
                                break
                        if should_skip:
                            continue
                        
                        # Parse line format: "Item Name SKU# $Price Qty $Amount"
                        parts = line.split()
                        if len(parts) < 3:
                            continue
                        
                        # Try to find quantity and amount (numbers)
                        qty = None
                        unit_price = None
                        total_amount = None
                        sku = None
                        
                        # Look for patterns
                        for i, part in enumerate(parts):
                            # Check for SKU patterns (alphanumeric with hyphens or long numbers)
                            if re.match(r'^[A-Z]{1,3}-[A-Z0-9]{1,5}$', part) or re.match(r'^\d{10,}$', part):
                                sku = part
                            # Check for price patterns ($X.XX)
                            elif part.startswith('$'):
                                price_val = part.replace('$', '').replace(',', '')
                                try:
                                    price_float = float(price_val)
                                    if unit_price is None:
                                        unit_price = price_float
                                    else:
                                        total_amount = price_float
                                except:
                                    pass
                            # Check for quantity (plain number between 1-1000)
                            elif part.isdigit():
                                num = int(part)
                                if 1 <= num <= 1000 and qty is None:
                                    qty = num
                        
                        # Extract item name (everything before SKU or first $)
                        item_name = ""
                        for part in parts:
                            if part == sku or part.startswith('$'):
                                break
                            item_name += part + " "
                        item_name = item_name.strip()
                        
                        # Normalize product name
                        if item_name:
                            item_name = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', item_name)
                            item_name = re.sub(r'(\w)x([A-Z])', r'\1 x \2', item_name)
                        
                        # Calculate unit price if we have total and qty
                        if unit_price is None and total_amount and qty and qty > 0:
                            unit_price = total_amount / qty
                        
                        # VALIDATION: Check both current products (MASTER) and PPwP.csv for best product match
                        is_valid = False
                        matched = None
                        matched_product_name = None
                        
                        # Load phased products
                        phased_df = load_phased_products()
                        
                        # PRIORITY 1: Exact product name match in PPwP.csv (legacy products)
                        if not is_valid and item_name and not phased_df.empty:
                            for _, row in phased_df.iterrows():
                                phased_name = str(row["Product name"]).strip()
                                # Normalize both names for comparison
                                normalized_phased = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', phased_name)
                                normalized_phased = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_phased)
                                normalized_item = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', item_name)
                                normalized_item = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_item)
                                
                                if normalized_item.lower() == normalized_phased.lower():
                                    # Found exact match in phased products, map to current product
                                    phased_sku = str(row["SKU#"]).strip()
                                    if phased_sku in MASTER["SKU#"].values:
                                        matched = MASTER[MASTER["SKU#"] == phased_sku]["Product name"].iloc[0]
                                        matched_product_name = phased_name  # Keep original name for display
                                        is_valid = True
                                        break
                        
                        # PRIORITY 2: Exact product name match in MASTER (current products)
                        if not is_valid and item_name:
                            normalized_item = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', item_name)
                            normalized_item = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_item)
                            for product_name in MASTER["Product name"].values:
                                normalized_product = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', str(product_name))
                                normalized_product = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_product)
                                
                                if normalized_item.lower() == normalized_product.lower():
                                    matched = product_name
                                    is_valid = True
                                    break
                        
                        # PRIORITY 3: Partial name match in PPwP.csv (legacy products)
                        if not is_valid and item_name and not phased_df.empty:
                            normalized_item = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', item_name)
                            normalized_item = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_item)
                            item_lower = normalized_item.lower()
                            
                            for _, row in phased_df.iterrows():
                                phased_name = str(row["Product name"]).strip()
                                normalized_phased = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', phased_name)
                                normalized_phased = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_phased)
                                phased_lower = normalized_phased.lower()
                                
                                if phased_lower in item_lower or item_lower in phased_lower:
                                    phased_sku = str(row["SKU#"]).strip()
                                    if phased_sku in MASTER["SKU#"].values:
                                        matched = MASTER[MASTER["SKU#"] == phased_sku]["Product name"].iloc[0]
                                        matched_product_name = phased_name
                                        is_valid = True
                                        break
                        
                        # PRIORITY 4: Partial name match in MASTER (current products)
                        if not is_valid and item_name:
                            normalized_item = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', item_name)
                            normalized_item = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_item)
                            for product_name in MASTER["Product name"].values:
                                normalized_product = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', str(product_name))
                                normalized_product = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_product)
                                prod_lower = normalized_product.lower()
                                
                                if prod_lower in item_lower or item_lower in prod_lower:
                                    matched = product_name
                                    is_valid = True
                                    break
                        
                        # PRIORITY 5 (LAST RESORT): SKU match in MASTER
                        if not is_valid and sku and sku in MASTER["SKU#"].values:
                            matched = MASTER[MASTER["SKU#"] == sku]["Product name"].iloc[0]
                            is_valid = True
                        
                        # Only add if valid and has quantity
                        if is_valid and matched and qty and qty > 0:
                            display_name = matched_product_name if matched_product_name else matched
                            items[matched] = (qty, invoice_num, unit_price, total_amount, invoice_date, due_date)
        except Exception as e:
            st.error(f"Error parsing PDF: {e}")
            return {}
    
    elif file.name.endswith(".csv"):
        df_raw = pd.read_csv(file)
        
        # Extract invoice metadata
        for _, row in df_raw.iterrows():
            for col in df_raw.columns:
                cell = str(row[col]) if pd.notna(row[col]) else ""
                cell_lower = cell.lower()
                
                if "invoice number:" in cell_lower:
                    cols = df_raw.columns.tolist()
                    idx = cols.index(col)
                    if idx + 1 < len(cols):
                        invoice_num = str(row[cols[idx + 1]]).strip()
                
                if "invoice date:" in cell_lower:
                    cols = df_raw.columns.tolist()
                    idx = cols.index(col)
                    if idx + 1 < len(cols):
                        invoice_date = str(row[cols[idx + 1]]).strip()
                
                if "due date:" in cell_lower:
                    cols = df_raw.columns.tolist()
                    idx = cols.index(col)
                    if idx + 1 < len(cols):
                        due_date = str(row[cols[idx + 1]]).strip()
                
                if "invoice total:" in cell_lower:
                    cols = df_raw.columns.tolist()
                    idx = cols.index(col)
                    if idx + 1 < len(cols):
                        total_str = str(row[cols[idx + 1]]).replace("$", "").replace(",", "").strip()
                        try:
                            invoice_total = float(total_str)
                        except:
                            pass
        
        # Find header row
        header_row = None
        item_col_idx = None
        sku_col_idx = None
        qty_col_idx = None
        unit_price_col_idx = None
        amount_col_idx = None
        
        for idx, row in df_raw.iterrows():
            row_str = " ".join([str(x) for x in row if pd.notna(x)]).lower()
            first_cell = str(row.iloc[0]).strip().lower() if pd.notna(row.iloc[0]) else ""
            
            if first_cell == "item" and ("sku" in row_str or "quantity" in row_str):
                header_row = idx
                for col_idx, val in enumerate(row):
                    val_str = str(val).strip().lower() if pd.notna(val) else ""
                    if val_str == "item": item_col_idx = col_idx
                    elif "sku" in val_str or val_str == "sku#": sku_col_idx = col_idx
                    elif "quantity" in val_str or "qty" in val_str: qty_col_idx = col_idx
                    elif "unit" in val_str and "price" in val_str: unit_price_col_idx = col_idx
                    elif val_str == "amount": amount_col_idx = col_idx
                break
        
        if header_row is not None:
            skip_keywords = ['shipping', 'shipping cost', 'ground shipping', 'subtotal', 'total', 'tax', 'grand total', 'nan', '', 
                            'please send', 'payment', 'bank', 'note:', 'payment terms', 
                            'this document', 'amount:', 'invoice total:', 'discount']
            
            for idx in range(header_row + 1, len(df_raw)):
                row = df_raw.iloc[idx]
                
                item_name = ""
                if item_col_idx is not None and item_col_idx < len(row):
                    item_name = str(row.iloc[item_col_idx]).strip() if pd.notna(row.iloc[item_col_idx]) else ""
                
                if not item_name: continue
                
                item_lower = item_name.lower()
                should_skip = False
                for keyword in skip_keywords:
                    if keyword and keyword.lower() in item_lower:
                        should_skip = True; break
                if should_skip: continue
                
                item_name = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', item_name)
                item_name = re.sub(r'(\w)x([A-Z])', r'\1 x \2', item_name)
                item_name = item_name.strip()
                
                sku = ""
                if sku_col_idx is not None and sku_col_idx < len(row):
                    sku = str(row.iloc[sku_col_idx]).strip() if pd.notna(row.iloc[sku_col_idx]) else ""
                
                qty = None
                if qty_col_idx is not None and qty_col_idx < len(row):
                    try:
                        qty_val = row.iloc[qty_col_idx]
                        if pd.notna(qty_val):
                            qty = int(float(str(qty_val).replace(",", "")))
                    except: pass
                
                if qty is None or qty <= 0:
                    for col_idx in range(len(row)):
                        if col_idx == item_col_idx or col_idx == sku_col_idx: continue
                        try:
                            val = row.iloc[col_idx]
                            if pd.notna(val):
                                val_str = str(val).strip()
                                qty_candidate = int(float(val_str.replace(",", "").replace("$", "")))
                                if 1 <= qty_candidate <= 10000:
                                    qty = qty_candidate; break
                        except: continue
                
                unit_price = None
                if unit_price_col_idx is not None and unit_price_col_idx < len(row):
                    try:
                        unit_val = row.iloc[unit_price_col_idx]
                        if pd.notna(unit_val):
                            unit_str = str(unit_val).replace("$", "").replace(",", "").strip()
                            unit_price = float(unit_str)
                    except: pass
                
                total_amount = None
                if amount_col_idx is not None and amount_col_idx < len(row):
                    try:
                        amount_val = row.iloc[amount_col_idx]
                        if pd.notna(amount_val):
                            amount_str = str(amount_val).replace("$", "").replace(",", "").strip()
                            total_amount = float(amount_str)
                    except: pass
                
                if unit_price is None and total_amount and qty and qty > 0:
                    unit_price = total_amount / qty
                
                if qty and qty > 0:
                    matched = None
                    if sku:
                        if sku in MASTER["SKU#"].values:
                            matched = MASTER[MASTER["SKU#"] == sku]["Product name"].iloc[0]
                        else:
                            for master_sku in MASTER["SKU#"].values:
                                if str(master_sku).strip() == str(sku).strip():
                                    matched = MASTER[MASTER["SKU#"] == master_sku]["Product name"].iloc[0]; break
                    
                    if not matched and item_name:
                        normalized_item = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', item_name)
                        normalized_item = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_item)
                        item_lower = normalized_item.lower()
                        
                        for product_name in MASTER["Product name"].values:
                            normalized_product = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', str(product_name))
                            normalized_product = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_product)
                            prod_lower = normalized_product.lower()
                            
                            if prod_lower in item_lower or item_lower in prod_lower:
                                matched = product_name; break
                    
                    if matched:
                        items[matched] = (qty, invoice_num, unit_price, total_amount, invoice_date, due_date)
                    else:
                        items[item_name] = (qty, invoice_num, unit_price, total_amount, invoice_date, due_date)
    
    return items

def update_inventory_delta(sku, delta):
    """Update inventory stock by a delta amount."""
    try:
        supabase = get_authed_supabase()
        res = supabase.table("inventory").select("stock_left").eq("sku", sku).execute()
        rows = getattr(res, "data", None)
        if not rows:
            return False, "Product not found"
        
        current_left = rows[0].get("stock_left", 0)
        new_left = current_left + delta
        status = _inventory_status_from_stock_left(new_left)
        
        supabase.table("inventory").update({
            "stock_left": new_left,
            "status": status
        }).eq("sku", sku).execute()
        return True, ""
    except Exception as e:
        return False, str(e)

def show_inventory_management():
    """Show inventory management interface with Supabase inventory"""
   
    st.title("Inventory Management")
    st.caption("Track stock levels, adjust inventory, and view summaries.")

    MASTER = load_master()
    if MASTER.empty:
        st.error("No products found in Supabase. Please add products first.")
        return

    inv_df = load_inventory()
    summary_df = load_inventory_summary()

    # Auto-sync products to inventory once per session to ensure new products appear with 0 stock
    if "inventory_autosynced" not in st.session_state:
        try:
            supabase = get_authed_supabase()
            supabase.rpc("sync_all_products_to_inventory").execute()
        except Exception:
            # Non-fatal; user can manually sync below
            pass
        st.session_state["inventory_autosynced"] = True

    # Auto-sync images from storage to inventory once per session
    if "inventory_images_synced" not in st.session_state:
        try:
            supabase = get_authed_supabase()
            bucket_name = "email-product-pictures"
            files = supabase.storage.from_(bucket_name).list()
            
            for file in files:
                filename = file.get('name', '')
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    sku = filename.rsplit('.', 1)[0]
                    public_url = supabase.storage.from_(bucket_name).get_public_url(filename)
                    
                    # Update inventory with image URL
                    supabase.table("inventory").update({
                        "image_url": public_url
                    }).eq("sku", sku).execute()
        except Exception:
            # Non-fatal; user can manually sync below
            pass
        st.session_state["inventory_images_synced"] = True

    # Auto-sync happens via database triggers - no manual sync needed
    st.caption("💡 Products and images sync automatically from the products table")

    # Tabs for actions
    tab_adjust, tab_summary, tab_current = st.tabs([
        "Quick Adjust (+/-)", 
        "Inventory Summary", 
        "Full Inventory Table"
    ])
    
    # 1. Quick Adjust Tab
    with tab_adjust:
        st.subheader("Quick Adjust Inventory")
        st.caption("Increment or decrement stock levels by any amount.")
        
        search_query = st.text_input("🔍 Search Product (Name or SKU)", "")
        
        if inv_df.empty:
            st.info("No inventory to adjust.")
        else:
            # Prepare display dataframe
            df_display = inv_df.copy()
            if search_query:
                mask = (
                    df_display["item_name"].astype(str).str.contains(search_query, case=False, na=False) | 
                    df_display["sku"].astype(str).str.contains(search_query, case=False, na=False)
                )
                df_display = df_display[mask]
            
            # Sort by name
            if "item_name" in df_display.columns:
                df_display = df_display.sort_values("item_name")
            
            # Display rows
            st.markdown("---")
            h1, h2, h3 = st.columns([3, 1, 2])
            h1.markdown("**Product**")
            h2.markdown("**Left**")
            h3.markdown("**Adjust Amount**")
            
            # Limit display
            MAX_ITEMS = 60
            if len(df_display) > MAX_ITEMS and not search_query:
                st.warning(f"Showing first {MAX_ITEMS} items. Use search to find specific products.")
                df_display = df_display.head(MAX_ITEMS)
                
            for idx, row in df_display.iterrows():
                sku = str(row.get("sku", ""))
                name = row.get("item_name", "Unknown")
                stock = int(float(str(row.get("stock_left", 0)).replace(",", "") or 0))
                
                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 2])
                    c1.write(f"**{name}**\n`{sku}`")
                    c2.write(f"**{stock}**")
                    
                    # Dynamic adjustment
                    with c3:
                        adj_c1, adj_c2, adj_c3 = st.columns([2, 1, 1])
                        amount = adj_c1.number_input("Amount", min_value=1, step=1, value=1, key=f"amt_{sku}", label_visibility="collapsed")
                        
                        if adj_c2.button("➖", key=f"dec_{sku}", help=f"Decrease by {amount}"):
                            success, msg = update_inventory_delta(sku, -amount)
                            if success: st.rerun()
                            else: st.error(msg)
                            
                        if adj_c3.button("➕", key=f"inc_{sku}", help=f"Increase by {amount}"):
                            success, msg = update_inventory_delta(sku, amount)
                            if success: st.rerun()
                            else: st.error(msg)
                        
                    st.markdown("---")

    # 2. Inventory Summary Tab
    with tab_summary:
        st.subheader("Inventory Summary")
        if not summary_df.empty:
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
        else:
            st.info("No summary data available.")

    # 3. Full Inventory Table
    with tab_current:
        st.subheader("Current Inventory Table")
        # Check for missing images
        if not inv_df.empty and "image_url" in inv_df.columns:
            missing_images = inv_df[(inv_df["image_url"] == "N/A") | (inv_df["image_url"].isna())]
            if not missing_images.empty:
                st.warning(f"⚠️ {len(missing_images)} products missing images. Upload images in Product Management → Images tab.")
                with st.expander("View products missing images"):
                    st.dataframe(missing_images[["sku", "item_name", "image_url"]], use_container_width=True, hide_index=True)
        
        if inv_df.empty:
            st.warning("Inventory table is empty. Add products to get started.")
        else:
            inv_df = inv_df.copy()
            for col in ["stock_bought", "stock_left"]:
                if col in inv_df.columns:
                    inv_df[col] = pd.to_numeric(inv_df[col], errors="coerce").fillna(0).astype(int)

            disabled_cols = [c for c in ["id", "created_at", "updated_at", "created_by"] if c in inv_df.columns]
            edited_inventory = st.data_editor(
                inv_df,
                num_rows="dynamic",
                use_container_width=True,
                disabled=disabled_cols,
                key="inventory_editor",
            )

            if st.button("💾 Save Bulk Changes", type="primary"):
                supabase = get_authed_supabase()
                payload_rows = []
                for _, r in edited_inventory.iterrows():
                    sku = str(r.get("sku", "")).strip()
                    item_name = str(r.get("item_name", "")).strip()
                    if not sku or not item_name:
                        continue
                    stock_bought = _safe_int(r.get("stock_bought", 0), 0)
                    stock_left = _safe_int(r.get("stock_left", 0), 0)
                    status = str(r.get("status", "")).strip() or _inventory_status_from_stock_left(stock_left)
                    payload_rows.append({
                        "sku": sku,
                        "item_name": item_name,
                        "stock_bought": stock_bought,
                        "stock_left": stock_left,
                        "status": status,
                        "last_updated_from_invoice": (str(r.get("last_updated_from_invoice", "")).strip() or None),
                        "invoice_date": (str(r.get("invoice_date", "")).strip() or None),
                        "due_date": (str(r.get("due_date", "")).strip() or None),
                    })
                try:
                    if payload_rows:
                        supabase.table("inventory").upsert(payload_rows, on_conflict="sku").execute()
                    st.success("Inventory updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save inventory: {e}")
