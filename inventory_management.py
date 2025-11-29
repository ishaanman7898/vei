import streamlit as st
import pandas as pd
import os
import json
import re
import pdfplumber
# New imports
from simple_auth import update_user_config


def load_master():
    """Load PwP.csv master product list"""
    if not os.path.exists("PwP.csv"):
        st.error("PwP.csv is missing!")
        st.stop()
    df = pd.read_csv("PwP.csv")
    df["Product name"] = df["Product name"].str.strip()
    # Normalize product names (add space before x)
    df["Product name"] = df["Product name"].apply(
        lambda x: re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', str(x)) if pd.notna(x) else x
    )
    df["Product name"] = df["Product name"].apply(
        lambda x: re.sub(r'(\w)x([A-Z])', r'\1 x \2', str(x)) if pd.notna(x) else x
    )
    def clean_price(x):
        if isinstance(x, str): x = x.replace("$", "").replace(",", "").strip()
        return float(x or 0)
    df["Final Price"] = df["Final Price"].apply(clean_price)
    return df

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
                        
                        # VALIDATION: Check both PwP.csv and PPwP.csv for best product match
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
                        
                        # PRIORITY 2: Exact product name match in PwP.csv (current products)
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
                        
                        # PRIORITY 4: Partial name match in PwP.csv (current products)
                        if not is_valid and item_name:
                            normalized_item = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', item_name)
                            normalized_item = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_item)
                            item_lower = normalized_item.lower()
                            
                            for product_name in MASTER["Product name"].values:
                                normalized_product = re.sub(r'(\w)\s*x\s*([A-Z])', r'\1 x \2', str(product_name))
                                normalized_product = re.sub(r'(\w)x([A-Z])', r'\1 x \2', normalized_product)
                                prod_lower = normalized_product.lower()
                                
                                if prod_lower in item_lower or item_lower in prod_lower:
                                    matched = product_name
                                    is_valid = True
                                    break
                        
                        # PRIORITY 5 (LAST RESORT): SKU match in PwP.csv
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

def show_inventory_management(MASTER, inv_config=None):
    """Main inventory management interface"""
    st.title("Inventory Management")
    st.caption("Update your inventory from invoices or sales history.")
    
    # No longer need user inventory config - using centralized service account
        
    # Use service account credentials from config module
    try:
        from config import get_service_account_credentials
        creds_dict = get_service_account_credentials()
        
        if not creds_dict:
            st.error("❌ Service account credentials not available.")
            return
            
        sheet_name = "Inventory Recognition"
        st.info(f"🔐 Using service account: {creds_dict.get('client_email', 'N/A')}")
    except ImportError:
        st.error("❌ Configuration module not found. Please contact administrator.")
        return
    except Exception as e:
        st.error(f"❌ Error loading service account credentials: {e}")
        return

    # Connect to spreadsheet
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        spreadsheet = client.open(sheet_name)
        
    except Exception as e:
        st.error(f"❌ Error connecting to Google Sheets: {e}")
        st.info("Make sure the service account has access to the 'Inventory Recognition' sheet.")
        return

    # Select Worksheet
    try:
        worksheets = [ws.title for ws in spreadsheet.worksheets()]
        selected_tab = st.selectbox("Select Worksheet", worksheets, index=0)
        sheet = spreadsheet.worksheet(selected_tab)
    except Exception as e:
        st.error(f"Error loading worksheets: {e}")
        st.stop()

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
                
                if st.button("EXPORT TO CSV", type="primary", use_container_width=True):
                    with st.spinner("Updating..."):
                        data = sheet.get_all_records()
                        df = pd.DataFrame(data) if data else pd.DataFrame()
                        for col in ["Item Name","SKU#","Stock Bought","Stock Left","Status","Last Updated From Invoice","Invoice Date","Due Date"]:
                            if col not in df.columns: df[col] = ""
                        
                        df["Stock Bought"] = pd.to_numeric(df["Stock Bought"], errors="coerce").fillna(0).astype(int)
                        df["Stock Left"] = pd.to_numeric(df["Stock Left"], errors="coerce").fillna(0).astype(int)
                        
                        for name, item_data in all_items.items():
                            qty = item_data[0]
                            inv = item_data[1]
                            inv_date = item_data[4]
                            due_date = item_data[5]
                            
                            sku = ""
                            if name in MASTER["Product name"].values:
                                sku = MASTER[MASTER["Product name"] == name]["SKU#"].iloc[0]
                            
                            if name in df["Item Name"].values:
                                idx = df[df["Item Name"] == name].index[0]
                                df.loc[idx, "Stock Bought"] = int(df.loc[idx, "Stock Bought"]) + qty
                                df.loc[idx, "Stock Left"] = int(df.loc[idx, "Stock Left"]) + qty
                                if inv_date: df.loc[idx, "Invoice Date"] = inv_date
                                if due_date: df.loc[idx, "Due Date"] = due_date
                                old_inv = str(df.loc[idx, "Last Updated From Invoice"]).strip()
                                if old_inv and old_inv != "nan": df.loc[idx, "Last Updated From Invoice"] = f"{old_inv} | {inv}"
                                else: df.loc[idx, "Last Updated From Invoice"] = inv
                            else:
                                new_row = pd.DataFrame([{
                                    "Item Name": name, "SKU#": sku,
                                    "Stock Bought": qty, "Stock Left": qty, "Status": "In stock",
                                    "Last Updated From Invoice": inv,
                                    "Invoice Date": inv_date if inv_date else "",
                                    "Due Date": due_date if due_date else ""
                                }])
                                df = pd.concat([df, new_row], ignore_index=True)
                        
                        df["Status"] = df["Stock Left"].apply(lambda x: "Backordered" if x < 0 else "In stock" if x > 10 else "Low stock" if x > 0 else "Out of stock")
                        sheet.clear()
                        sheet.update(values=[df.columns.tolist()] + df.values.tolist(), range_name="A1")
                        st.balloons()
                        st.success("Inventory updated!")

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
                        data = sheet.get_all_records()
                        df = pd.DataFrame(data) if data else pd.DataFrame()
                        for col in ["Item Name", "Stock Left", "Status"]:
                            if col not in df.columns: df[col] = ""
                        df["Stock Left"] = pd.to_numeric(df["Stock Left"], errors="coerce").fillna(0).astype(int)
                        
                        updates = 0
                        for prod_name, qty_sold in sales_summary.items():
                            if not prod_name or pd.isna(prod_name): continue
                            qty_sold = int(qty_sold)
                            if qty_sold <= 0: continue
                            
                            sku = None
                            if prod_name in MASTER["Product name"].values:
                                sku = MASTER[MASTER["Product name"] == prod_name]["SKU#"].iloc[0]
                            
                            match_idx = None
                            if sku and sku in df["SKU#"].values:
                                match_idx = df[df["SKU#"] == sku].index[0]
                            elif prod_name in df["Item Name"].values:
                                match_idx = df[df["Item Name"] == prod_name].index[0]
                            
                            if match_idx is not None:
                                df.loc[match_idx, "Stock Left"] = int(df.loc[match_idx, "Stock Left"]) - qty_sold
                                updates += 1
                        
                        df["Status"] = df["Stock Left"].apply(lambda x: "Backordered" if x < 0 else "In stock" if x > 10 else "Low stock" if x > 0 else "Out of stock")
                        sheet.clear()
                        sheet.update(values=[df.columns.tolist()] + df.values.tolist(), range_name="A1")
                        st.success(f"✅ Updated inventory! Subtracted sales for {updates} products.")
            except Exception as e:
                st.error(f"Error: {e}")
