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


@st.cache_data(ttl=600)
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
        if pd.isna(x) or x == "" or str(x).lower in ["nan", "none", ""]:
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

@st.cache_data(ttl=600)
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

@st.cache_data(ttl=600)
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

def update_inventory_delta(sku, delta):
    """Update inventory stock (stock_left) by a delta amount."""
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
        st.cache_data.clear() # Clear cache on update
        return True, ""
    except Exception as e:
        return False, str(e)

def update_stock_bought_delta(sku, delta):
    """Update inventory stock (stock_bought) by a delta amount."""
    try:
        supabase = get_authed_supabase()
        res = supabase.table("inventory").select("stock_bought").eq("sku", sku).execute()
        rows = getattr(res, "data", None)
        if not rows:
            return False, "Product not found"
        
        current_bought = rows[0].get("stock_bought", 0)
        new_bought = current_bought + delta
        
        supabase.table("inventory").update({
            "stock_bought": new_bought
        }).eq("sku", sku).execute()
        st.cache_data.clear() # Clear cache on update
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

    # Tabs for actions
    tab_left, tab_bought, tab_summary, tab_current = st.tabs([
        "Quick Adjust (Left)", 
        "Quick Adjust (Bought)",
        "Inventory Summary", 
        "Full Inventory Table"
    ])
    
    # 1. Quick Adjust (Left) Tab
    with tab_left:
        st.subheader("Quick Adjust Stock Left")
        st.caption("Increment or decrement 'Stock Left' (remaining inventory).")
        
        search_query = st.text_input("🔍 Search Product (Name or SKU)", "", key="search_left")
        
        if inv_df.empty:
            st.info("No inventory to adjust.")
        else:
            df_display = inv_df.copy()
            if search_query:
                mask = (
                    df_display["item_name"].astype(str).str.contains(search_query, case=False, na=False) | 
                    df_display["sku"].astype(str).str.contains(search_query, case=False, na=False)
                )
                df_display = df_display[mask]
            
            if "item_name" in df_display.columns:
                df_display = df_display.sort_values("item_name")
            
            st.markdown("---")
            h1, h2, h3 = st.columns([3, 1, 2])
            h1.markdown("**Product**")
            h2.markdown("**Left**")
            h3.markdown("**Adjust Left**")
            
            MAX_ITEMS = 60
            if len(df_display) > MAX_ITEMS and not search_query:
                st.warning(f"Showing first {MAX_ITEMS} items.")
                df_display = df_display.head(MAX_ITEMS)
                
            for idx, row in df_display.iterrows():
                sku = str(row.get("sku", ""))
                name = row.get("item_name", "Unknown")
                stock = int(float(str(row.get("stock_left", 0)).replace(",", "") or 0))
                
                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 2])
                    c1.write(f"**{name}**\n`{sku}`")
                    c2.write(f"**{stock}**")
                    with c3:
                        adj_c1, adj_c2, adj_c3 = st.columns([2, 1, 1])
                        amount = adj_c1.number_input("Amount", min_value=1, step=1, value=1, key=f"amt_l_{sku}", label_visibility="collapsed")
                        if adj_c2.button("➖", key=f"dec_l_{sku}"):
                            success, msg = update_inventory_delta(sku, -amount)
                            if success: st.rerun()
                            else: st.error(msg)
                        if adj_c3.button("➕", key=f"inc_l_{sku}"):
                            success, msg = update_inventory_delta(sku, amount)
                            if success: st.rerun()
                            else: st.error(msg)
                    st.markdown("---")

    # 2. Quick Adjust (Bought) Tab
    with tab_bought:
        st.subheader("Quick Adjust Stock Bought")
        st.caption("Increment or decrement 'Stock Bought' (total purchased inventory).")
        
        search_query_b = st.text_input("🔍 Search Product (Name or SKU)", "", key="search_bought")
        
        if inv_df.empty:
            st.info("No inventory to adjust.")
        else:
            df_display = inv_df.copy()
            if search_query_b:
                mask = (
                    df_display["item_name"].astype(str).str.contains(search_query_b, case=False, na=False) | 
                    df_display["sku"].astype(str).str.contains(search_query_b, case=False, na=False)
                )
                df_display = df_display[mask]
            
            if "item_name" in df_display.columns:
                df_display = df_display.sort_values("item_name")
            
            st.markdown("---")
            h1, h2, h3 = st.columns([3, 1, 2])
            h1.markdown("**Product**")
            h2.markdown("**Bought**")
            h3.markdown("**Adjust Bought**")
            
            MAX_ITEMS = 60
            if len(df_display) > MAX_ITEMS and not search_query_b:
                st.warning(f"Showing first {MAX_ITEMS} items.")
                df_display = df_display.head(MAX_ITEMS)
                
            for idx, row in df_display.iterrows():
                sku = str(row.get("sku", ""))
                name = row.get("item_name", "Unknown")
                stock = int(float(str(row.get("stock_bought", 0)).replace(",", "") or 0))
                
                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 2])
                    c1.write(f"**{name}**\n`{sku}`")
                    c2.write(f"**{stock}**")
                    with c3:
                        adj_c1, adj_c2, adj_c3 = st.columns([2, 1, 1])
                        amount = adj_c1.number_input("Amount", min_value=1, step=1, value=1, key=f"amt_b_{sku}", label_visibility="collapsed")
                        if adj_c2.button("➖", key=f"dec_b_{sku}"):
                            success, msg = update_stock_bought_delta(sku, -amount)
                            if success: st.rerun()
                            else: st.error(msg)
                        if adj_c3.button("➕", key=f"inc_b_{sku}"):
                            success, msg = update_stock_bought_delta(sku, amount)
                            if success: st.rerun()
                            else: st.error(msg)
                    st.markdown("---")

    # 3. Inventory Summary Tab
    with tab_summary:
        st.subheader("Inventory Summary")
        if not summary_df.empty:
            st.dataframe(summary_df, width='stretch', hide_index=True)
        else:
            st.info("No summary data available.")

    # 4. Full Inventory Table
    with tab_current:
        st.subheader("Current Inventory Table")
        if not inv_df.empty and "image_url" in inv_df.columns:
            missing_images = inv_df[(inv_df["image_url"] == "N/A") | (inv_df["image_url"].isna())]
            if not missing_images.empty:
                st.warning(f"⚠️ {len(missing_images)} products missing images.")
                with st.expander("View products missing images"):
                    st.dataframe(missing_images[["sku", "item_name", "image_url"]], width='stretch', hide_index=True)
        
        if inv_df.empty:
            st.warning("Inventory table is empty.")
        else:
            inv_df = inv_df.copy()
            for col in ["stock_bought", "stock_left"]:
                if col in inv_df.columns:
                    inv_df[col] = pd.to_numeric(inv_df[col], errors="coerce").fillna(0).astype(int)

            disabled_cols = [c for c in ["id", "created_at", "updated_at", "created_by"] if c in inv_df.columns]
            edited_inventory = st.data_editor(
                inv_df,
                num_rows="dynamic",
                width='stretch',
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
                    st.cache_data.clear()
                    st.success("Inventory updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save inventory: {e}")
