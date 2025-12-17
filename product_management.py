import streamlit as st
import pandas as pd
import os
import shutil
import json

from supabase_client import get_authed_supabase, get_current_supabase_user_id

def load_pwp():
    expected_columns = [
        "id",
        "name",
        "description",
        "category",
        "status",
        "sku",
        "price",
        "buy_link",
        "image_url",
        "group_name",
        "color",
        "hex_color",
        "created_at",
        "updated_at",
        "created_by",
        "specifications",
    ]

    try:
        supabase = get_authed_supabase()
        res = supabase.table("products").select(
            "id,name,description,category,status,sku,price,buy_link,image_url,group_name,color,hex_color,created_at,updated_at,created_by,specifications"
        ).execute()
        rows = getattr(res, "data", None) or []
    except Exception as e:
        st.error(f"Unable to load products from Supabase: {e}")
        return pd.DataFrame(columns=expected_columns)

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=expected_columns)

    for col in expected_columns:
        if col not in df.columns:
            df[col] = ""

    # Normalize types for Streamlit display
    df["id"] = df["id"].astype(str)
    df["sku"] = df["sku"].astype(str)
    df["name"] = df["name"].astype(str)
    df["category"] = df["category"].astype(str)
    df["status"] = df["status"].astype(str)
    df["buy_link"] = df["buy_link"].astype(str)
    df["image_url"] = df["image_url"].astype(str)
    df["group_name"] = df["group_name"].astype(str)
    df["color"] = df["color"].astype(str)
    df["hex_color"] = df["hex_color"].astype(str)
    df["created_by"] = df["created_by"].astype(str)

    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

    # Convert jsonb specifications to a JSON string for editing
    def _spec_to_str(v):
        if v is None or v == "":
            return "{}"
        if isinstance(v, str):
            # Assume already JSON-ish
            return v
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return "{}"

    df["specifications"] = df["specifications"].apply(_spec_to_str)

    # created_at/updated_at as strings for display
    if "created_at" in df.columns:
        df["created_at"] = df["created_at"].astype(str)
    if "updated_at" in df.columns:
        df["updated_at"] = df["updated_at"].astype(str)

    return df[expected_columns]

def save_pwp(df):
    try:
        supabase = get_authed_supabase()
    except Exception as e:
        st.error(f"Unable to save products to Supabase: {e}")
        return

    payload = []
    for _, row in df.iterrows():
        sku = str(row.get("sku", "")).strip()
        name = str(row.get("name", "")).strip()
        if not sku or not name:
            continue

        price_val = row.get("price")
        if price_val is None or str(price_val).strip() == "":
            price_val = None
        else:
            try:
                price_val = float(str(price_val).replace("$", "").replace(",", "").strip())
            except Exception:
                price_val = None

        specs_raw = row.get("specifications")
        specs_val = None
        if specs_raw is None or str(specs_raw).strip() == "":
            specs_val = {}
        else:
            if isinstance(specs_raw, (dict, list)):
                specs_val = specs_raw
            else:
                try:
                    specs_val = json.loads(str(specs_raw))
                except Exception:
                    st.error(f"Invalid JSON in specifications for SKU {sku}. Please fix it before saving.")
                    return

        payload.append({
            "id": str(row.get("id", "")).strip() or None,
            "sku": sku,
            "name": name,
            "description": str(row.get("description", "")).strip() or None,
            "category": str(row.get("category", "")).strip() or None,
            "status": str(row.get("status", "")).strip() or None,
            "price": price_val,
            "buy_link": str(row.get("buy_link", "")).strip() or None,
            "image_url": str(row.get("image_url", "")).strip() or None,
            "group_name": str(row.get("group_name", "")).strip() or None,
            "color": str(row.get("color", "")).strip() or None,
            "hex_color": str(row.get("hex_color", "")).strip() or None,
            "specifications": specs_val,
        })

    if not payload:
        return

    # Avoid sending empty "id" values; keep id when present to help Supabase identify rows
    for item in payload:
        if not item.get("id"):
            item.pop("id", None)

    try:
        supabase.table("products").upsert(payload, on_conflict="sku").execute()
    except Exception as e:
        st.error(f"Unable to save products to Supabase: {e}")


def upsert_product_image_url(sku: str, image_url: str):
    try:
        supabase = get_authed_supabase()
        supabase.table("products").upsert({"sku": sku, "image_url": image_url}, on_conflict="sku").execute()
    except Exception as e:
        st.warning(f"Image saved locally but failed to update Supabase image_url: {e}")

def show_product_management():
    st.title("Product Management")
    st.caption("View, edit, and add products to your catalog (Supabase products).")

    # Load data
    df = load_pwp()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["View & Edit Products", "Add New Product", "Product Merger"])

    # --- VIEW & EDIT ---
    with tab1:
        st.subheader("Current Product Catalog")
        st.info("💡 Edit cells directly below and click 'Save Changes' to update Supabase")
        
        # Create a copy of the dataframe for editing
        editable_df = df.copy()
        if "price" in editable_df.columns:
            editable_df["price"] = pd.to_numeric(editable_df["price"], errors="coerce")
        
        # Configure columns for the data editor
        column_config = {
            "id": st.column_config.TextColumn("id"),
            "name": st.column_config.TextColumn("name", required=True),
            "description": st.column_config.TextColumn("description"),
            "category": st.column_config.TextColumn("category"),
            "status": st.column_config.SelectboxColumn(
                "status",
                options=["In Store", "Out of Stock", "Discontinued", "Removal Requested", "Phased Out", "Product in Design"],
            ),
            "sku": st.column_config.TextColumn("sku", required=True),
            "price": st.column_config.NumberColumn("price", format="%.2f"),
            "buy_link": st.column_config.LinkColumn("buy_link"),
            "image_url": st.column_config.TextColumn("image_url"),
            "group_name": st.column_config.TextColumn("group_name"),
            "color": st.column_config.TextColumn("color"),
            "hex_color": st.column_config.TextColumn("hex_color"),
            "created_at": st.column_config.TextColumn("created_at"),
            "updated_at": st.column_config.TextColumn("updated_at"),
            "created_by": st.column_config.TextColumn("created_by"),
            "specifications": st.column_config.TextColumn("specifications", help="JSON"),
        }
        
        # Display the data editor
        edited_df = st.data_editor(
            editable_df,
            column_config=column_config,
            num_rows="dynamic",
            use_container_width=True,
            disabled=["id", "created_at", "updated_at", "created_by"],
            key="product_editor"
        )

        if st.button("💾 Save Changes", type="primary"):
            save_pwp(edited_df)
            st.success("Product catalog updated successfully!")
            st.cache_data.clear() # Clear cache so other tools see changes
            st.rerun()

    # --- ADD NEW PRODUCT ---
    with tab2:
        st.subheader("Add New Product")
        
        # Specifications editor outside the form (st.button not allowed in st.form)
        specs_key = "new_product_specs_editor"
        if specs_key not in st.session_state:
            st.session_state[specs_key] = pd.DataFrame({
                "Specification name (e.g., capacity, material)": [""],
                "Value (e.g., 40 oz, Stainless Steel)": [""],
            })

        st.markdown("**Specifications:**")
        specs_df = st.data_editor(
            st.session_state[specs_key],
            num_rows="dynamic",
            use_container_width=True,
            key="new_specs_table"
        )
        st.session_state[specs_key] = specs_df

        if st.button("Add Specification", key="add_spec_row"):
            st.session_state[specs_key] = pd.concat(
                [
                    st.session_state[specs_key],
                    pd.DataFrame({
                        "Specification name (e.g., capacity, material)": [""],
                        "Value (e.g., 40 oz, Stainless Steel)": [""],
                    })
                ],
                ignore_index=True
            )
            st.rerun()

        with st.form("add_product_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("Product Name", help="Required")
                new_sku = st.text_input("SKU", help="Required - must be unique")

                new_description = st.text_area(
                    "Description",
                    help="Detailed product description"
                )

                category_options = sorted([c for c in df.get("category", pd.Series(dtype=str)).dropna().unique().tolist() if str(c).strip()])
                new_category = st.selectbox(
                    "Category",
                    options=category_options + (["New Category..."] if True else []),
                    index=0 if category_options else 0,
                )
                
                if new_category == "New Category...":
                    new_category = st.text_input("Enter New Category Name")

                new_status = st.selectbox(
                    "Status",
                    ["In Store", "Out of Stock", "Discontinued", "Removal Requested", "Phased Out", "Product in Design"],
                    index=0
                )

                new_final_price = st.number_input("Price", min_value=0.0, value=0.0, step=0.01, format="%.2f")

                new_group_name = st.text_input("Group Name", value="")
                new_color = st.text_input("Color/Variant", value="")
                new_hex_color = st.text_input("Hex Color", value="#000000", help="Example: #800000")
            
            with c2:
                new_buy_link = st.text_input("Buy Link", 
                    value="", 
                    help="URL for the buy button")

                uploaded_image = st.file_uploader("Product Image", type=['png', 'jpg', 'jpeg'])
            
            submitted = st.form_submit_button("Add Product", type="primary")
            
            if submitted:
                if not new_name or not new_sku:
                    st.error("Product Name and SKU are required!")
                else:
                    # Check if SKU already exists
                    if "sku" in df.columns and str(new_sku).strip() in df["sku"].astype(str).values:
                        st.error(f"SKU '{new_sku}' already exists!")
                    else:
                        user_id = get_current_supabase_user_id()
                        image_url = None

                        specs_val = {}
                        for _, r in st.session_state[specs_key].iterrows():
                            k = str(r.get("Specification name (e.g., capacity, material)", "")).strip()
                            v = str(r.get("Value (e.g., 40 oz, Stainless Steel)", "")).strip()
                            if k:
                                specs_val[k] = v
                        
                        # Save Image
                        if uploaded_image:
                            os.makedirs("product-images", exist_ok=True)
                            # Get extension
                            ext = os.path.splitext(uploaded_image.name)[1]
                            if not ext: ext = ".png"
                            
                            image_path = f"product-images/{new_sku}{ext}"
                            with open(image_path, "wb") as f:
                                f.write(uploaded_image.getbuffer())
                            st.info(f"Image saved to {image_path}")
                            image_url = f"/product-images/{new_sku}{ext}"

                        payload = {
                            "sku": str(new_sku).strip(),
                            "name": str(new_name).strip(),
                            "category": str(new_category).strip() or None,
                            "status": str(new_status).strip() or None,
                            "price": float(new_final_price) if new_final_price is not None else None,
                            "buy_link": str(new_buy_link).strip() or None,
                            "description": str(new_description).strip() or None,
                            "group_name": str(new_group_name).strip() or None,
                            "color": str(new_color).strip() or None,
                            "hex_color": str(new_hex_color).strip() or None,
                            "created_by": user_id,
                            "specifications": specs_val,
                        }
                        if image_url:
                            payload["image_url"] = image_url

                        try:
                            supabase = get_authed_supabase()
                            supabase.table("products").insert(payload).execute()
                        except Exception as e:
                            st.error(f"Failed to add product to Supabase: {e}")
                            return
                        
                        # Show detailed confirmation
                        st.success(f"✅ Successfully added '{new_name}' to Supabase!")
                        st.cache_data.clear()
                        
                        # Clear form by deleting the form-related session state
                        if "add_product_form" in st.session_state:
                            del st.session_state["add_product_form"]
                        
                        st.rerun()

    # --- PRODUCT MERGER ---
    with tab3:
        st.subheader("Product Merger")
        st.caption("Merge Orders CSV and Items CSV into a consolidated format.")
        
        c1, c2 = st.columns(2)
        with c1:
            orders_file = st.file_uploader("Upload Orders CSV", type=["csv"], help="Contains billing/shipping info")
        with c2:
            items_file = st.file_uploader("Upload Items CSV", type=["csv"], help="Contains item details")
            
        if orders_file and items_file:
            if st.button("Merge Files", type="primary"):
                try:
                    # Read CSVs
                    df_orders = pd.read_csv(orders_file)
                    df_items = pd.read_csv(items_file)
                    
                    # Normalize columns (strip whitespace)
                    df_orders.columns = df_orders.columns.str.strip()
                    df_items.columns = df_items.columns.str.strip()
                    
                    # Check for required join column
                    join_col = "Transaction no"
                    if join_col not in df_orders.columns:
                        st.error(f"Orders CSV missing '{join_col}' column")
                        st.stop()
                    if join_col not in df_items.columns:
                        st.error(f"Items CSV missing '{join_col}' column")
                        st.stop()
                        
                    # Process Items: Aggregate items per transaction
                    # Expected format: "Product A x 2, Product B x 1"
                    
                    # Ensure quantity is numeric
                    if "Quantity" in df_items.columns:
                        df_items["Quantity"] = pd.to_numeric(df_items["Quantity"], errors='coerce').fillna(1).astype(int)
                    else:
                        df_items["Quantity"] = 1
                        
                    # Create formatted item string "Name" or "Name x Qty"
                    df_items["Formatted_Item"] = df_items.apply(
                        lambda x: (f"{x['Item name']}" if x['Quantity'] == 1 else f"{x['Item name']} x {x['Quantity']}") if pd.notna(x.get('Item name')) else "", axis=1
                    )
                    
                    # Group by Transaction no and join items with double space
                    items_agg = df_items.groupby(join_col)["Formatted_Item"].apply(lambda x: "  ".join(filter(None, x))).reset_index()
                    items_agg.rename(columns={"Formatted_Item": "Product(s) Ordered & Quantity"}, inplace=True)
                    
                    # Merge Orders with Aggregated Items
                    merged_df = pd.merge(df_orders, items_agg, on=join_col, how="left")
                    
                    # Create final dataframe with specific columns
                    final_df = pd.DataFrame()
                    
                    # Map columns
                    final_df["Web or Booth"] = "Website"
                    final_df["Transaction No."] = merged_df[join_col]
                    final_df["Purchase Date"] = merged_df.get("Date", "N/A")
                    final_df["Customer Name"] = merged_df.get("Billing name", "N/A")
                    final_df["Company"] = merged_df.get("Billing company", "N/A")
                    final_df["City"] = merged_df.get("Billing city", "N/A")
                    final_df["State"] = merged_df.get("Billing state/province", "N/A")
                    final_df["Customer E-Mail"] = merged_df.get("Customer email", "N/A")
                    final_df["Product(s) Ordered & Quantity"] = merged_df.get("Product(s) Ordered & Quantity", "N/A")
                    final_df["Order Subtotal"] = merged_df.get("Subtotal", "N/A")
                    final_df["Discount Applied"] = merged_df.get("Discount", "N/A")
                    final_df["Shipping"] = merged_df.get("Shipping", "N/A")
                    final_df["Tax"] = merged_df.get("Tax", "N/A")
                    final_df["Order Total"] = merged_df.get("Total", "N/A")
                    final_df["Shipping Status"] = "N/A"
                    
                    # Fill NaN with "N/A"
                    final_df = final_df.fillna("N/A")
                    
                    st.success("✅ Files merged successfully!")
                    st.dataframe(final_df)
                    
                    # Convert to CSV
                    csv = final_df.to_csv(index=False).encode('utf-8')
                    
                    st.download_button(
                        label="Download Merged CSV",
                        data=csv,
                        file_name="merged_products.csv",
                        mime="text/csv",
                        type="primary"
                    )
                    
                except Exception as e:
                    st.error(f"Error merging files: {str(e)}")
