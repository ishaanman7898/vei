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

def show_inventory_management():
    """Show inventory management interface with Supabase inventory"""
    st.title("Inventory Management")
    st.caption("Manage inventory in Supabase. Invoice uploads add stock; sales history subtracts stock.")

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

    c_sync1, c_sync2 = st.columns([1, 3])
    with c_sync1:
        if st.button("🔄 Sync Products → Inventory", use_container_width=True):
            try:
                supabase = get_authed_supabase()
                res = supabase.rpc("sync_all_products_to_inventory").execute()
                created = getattr(res, "data", None)
                if isinstance(created, int):
                    st.success(f"Synced products to inventory. Added {created} missing inventory rows.")
                else:
                    st.success("Synced products to inventory.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to sync products to inventory: {e}")
    with c_sync2:
        st.caption("Ensures every product in `products` has an `inventory` row (0 stock by default).")

    if not summary_df.empty:
        st.subheader("Inventory Summary")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.subheader("Current Inventory")
    if inv_df.empty:
        st.warning("Inventory table is empty. Add products (auto-sync trigger) or run SELECT sync_all_products_to_inventory();")
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

        if st.button("💾 Save Inventory Changes", type="primary"):
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
                st.success("Inventory saved to Supabase.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save inventory: {e}")

    # Tabs for actions
    inv_tab1, inv_tab2 = st.tabs(["Inventory Update (Invoices)", "Old Inventory Push (Historical)"])
    
    # ====================== INVENTORY UPDATE (INVOICES) ======================
    with inv_tab1:
        st.markdown("### 📄 Update from Invoices")
        st.caption("Upload PDF or CSV invoices to **add** to your stock.")
        
        uploaded = st.file_uploader("Upload invoice files", type=["pdf","csv"], accept_multiple_files=True, key="inv_upload")
        
        if uploaded:
            all_items = {}
            with st.expander("Processing Details", expanded=False):
                for f in uploaded:
                    st.write(f"**{f.name}**")
                    items = parse_invoice(f, MASTER)
                    st.write(items)
                    for name, item_data in items.items():
                        # Normalize item_data length
                        if len(item_data) == 6: qty, inv, unit_price, total_amount, inv_date, due_date = item_data
                        elif len(item_data) == 4: qty, inv, unit_price, total_amount = item_data; inv_date=None; due_date=None
                        else: qty, inv = item_data; unit_price=None; total_amount=None; inv_date=None; due_date=None
                        
                        if name in all_items:
                            old_data = all_items[name]
                            old_qty = old_data[0]
                            all_items[name] = (old_qty + qty, f"{old_data[1]} | {inv}", unit_price or old_data[2], total_amount, inv_date or old_data[4], due_date or old_data[5])
                        else:
                            all_items[name] = (qty, inv, unit_price, total_amount, inv_date, due_date)
            
            if all_items:
                total_qty = sum(d[0] for d in all_items.values())
                st.success(f"Found {total_qty:,} items!")
                
                preview = []
                for name, d in all_items.items():
                    preview.append({
                        "Product": name, "Qty": d[0], "Invoice": d[1], 
                        "Date": d[4] if d[4] else "N/A"
                    })
                st.dataframe(pd.DataFrame(preview), use_container_width=True)
                
                if st.button("Apply Invoice Updates", type="primary", use_container_width=True):
                    with st.spinner("Updating Supabase inventory..."):
                        try:
                            supabase = get_authed_supabase()
                            current_inv = load_inventory()
                            if not current_inv.empty:
                                current_inv = current_inv.copy()
                                current_inv["sku"] = current_inv["sku"].astype(str).str.strip()
                                current_inv["item_name"] = current_inv["item_name"].astype(str).str.strip()

                            master_name_to_sku = dict(zip(MASTER["Product name"].astype(str), MASTER["SKU#"].astype(str)))
                            inv_name_to_sku = {}
                            if not current_inv.empty and "item_name" in current_inv.columns and "sku" in current_inv.columns:
                                inv_name_to_sku = dict(zip(current_inv["item_name"], current_inv["sku"]))

                            for name, item_data in all_items.items():
                                qty = int(item_data[0])
                                inv = str(item_data[1])
                                inv_date = item_data[4]
                                due_date = item_data[5]

                                sku = str(master_name_to_sku.get(name) or inv_name_to_sku.get(name) or "").strip()
                                if not sku:
                                    st.warning(f"Skipping '{name}' (no matching SKU). Add product first, then re-run.")
                                    continue

                                existing = None
                                if not current_inv.empty:
                                    m = current_inv[current_inv["sku"] == sku]
                                    if not m.empty:
                                        existing = m.iloc[0]

                                existing_bought = _safe_int(existing.get("stock_bought"), 0) if existing is not None else 0
                                existing_left = _safe_int(existing.get("stock_left"), 0) if existing is not None else 0

                                new_bought = existing_bought + qty
                                new_left = existing_left + qty
                                status = _inventory_status_from_stock_left(new_left)

                                old_inv = str(existing.get("last_updated_from_invoice", "")).strip() if existing is not None else ""
                                merged_inv = inv if not old_inv or old_inv == "nan" else f"{old_inv} | {inv}"

                                payload = {
                                    "sku": sku,
                                    "item_name": str(name).strip(),
                                    "stock_bought": new_bought,
                                    "stock_left": new_left,
                                    "status": status,
                                    "last_updated_from_invoice": merged_inv,
                                    "invoice_date": inv_date if inv_date else None,
                                    "due_date": due_date if due_date else None,
                                }
                                supabase.table("inventory").upsert(payload, on_conflict="sku").execute()

                            st.success("Inventory updated in Supabase.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update inventory in Supabase: {e}")

    # ====================== OLD INVENTORY PUSH ======================
    with inv_tab2:
        st.markdown("### 🕰️ Old Inventory Push")
        st.caption("Upload sales history CSV to **subtract** from your stock.")
        
        hist_upload = st.file_uploader("Upload sales history CSV", type=["csv"], key="hist_upload")
        
        if hist_upload:
            try:
                hist_df = pd.read_csv(hist_upload)
                st.dataframe(hist_df.head(), use_container_width=True)
                
                combined_col = None
                for c in hist_df.columns:
                    if "product(s) ordered & quantity" in c.lower():
                        combined_col = c; break
                
                sales_summary = {}
                process = False
                
                if combined_col:
                    st.info(f"✅ Detected combined column: **{combined_col}**")
                    if st.button("Process & Subtract", type="primary"):
                        process = True
                        master_products = sorted(MASTER["Product name"].tolist(), key=len, reverse=True)
                        for _, row in hist_df.iterrows():
                            cell_val = str(row[combined_col])
                            if pd.isna(cell_val) or cell_val == "nan": continue
                            temp_val = cell_val
                            for prod_name in master_products:
                                pattern = re.escape(prod_name) + r'(?:\s*[x×]\s*(\d+))?'
                                matches = list(re.finditer(pattern, temp_val, re.IGNORECASE))
                                for match in matches:
                                    qty = int(match.group(1)) if match.group(1) else 1
                                    sales_summary[prod_name] = sales_summary.get(prod_name, 0) + qty
                                if matches: temp_val = re.sub(pattern, '', temp_val, flags=re.IGNORECASE)
                else:
                    st.markdown("#### Map Columns")
                    cols = hist_df.columns.tolist()
                    c1, c2 = st.columns(2)
                    with c1: prod_col = st.selectbox("Product Name Column", cols)
                    with c2: qty_col = st.selectbox("Quantity Column", cols)
                    if st.button("Process & Subtract", type="primary"):
                        process = True
                        sales_summary = hist_df.groupby(prod_col)[qty_col].sum().to_dict()

                if process:
                    with st.spinner("Processing..."):
                        try:
                            supabase = get_authed_supabase()
                            current_inv = load_inventory()
                            if current_inv.empty:
                                st.error("Inventory table is empty; cannot subtract sales.")
                                return

                            current_inv = current_inv.copy()
                            current_inv["sku"] = current_inv["sku"].astype(str).str.strip()
                            current_inv["item_name"] = current_inv["item_name"].astype(str).str.strip()

                            master_name_to_sku = dict(zip(MASTER["Product name"].astype(str), MASTER["SKU#"].astype(str)))
                            inv_name_to_sku = dict(zip(current_inv["item_name"], current_inv["sku"]))

                            updates = 0
                            for prod_name, qty_sold in sales_summary.items():
                                if not prod_name or pd.isna(prod_name):
                                    continue
                                qty_sold = int(qty_sold)
                                if qty_sold <= 0:
                                    continue

                                sku = str(master_name_to_sku.get(prod_name) or inv_name_to_sku.get(prod_name) or "").strip()
                                if not sku:
                                    continue

                                m = current_inv[current_inv["sku"] == sku]
                                if m.empty:
                                    continue
                                existing = m.iloc[0]
                                existing_left = _safe_int(existing.get("stock_left"), 0)
                                new_left = existing_left - qty_sold
                                status = _inventory_status_from_stock_left(new_left)

                                supabase.table("inventory").upsert({
                                    "sku": sku,
                                    "item_name": str(existing.get("item_name", prod_name)).strip() or str(prod_name).strip(),
                                    "stock_bought": _safe_int(existing.get("stock_bought"), 0),
                                    "stock_left": new_left,
                                    "status": status,
                                    "last_updated_from_invoice": (str(existing.get("last_updated_from_invoice", "")).strip() or None),
                                    "invoice_date": (str(existing.get("invoice_date", "")).strip() or None),
                                    "due_date": (str(existing.get("due_date", "")).strip() or None),
                                }, on_conflict="sku").execute()
                                updates += 1

                            st.success(f"✅ Updated inventory in Supabase! Subtracted sales for {updates} products.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating inventory in Supabase: {e}")
            except Exception as e:
                st.error(f"Error: {e}")
