import streamlit as st
import pandas as pd
import os
import shutil

def load_pwp():
    if os.path.exists("PwP.csv"):
        return pd.read_csv("PwP.csv")
    return pd.DataFrame(columns=["Category", "Product name", "SKU#", "Unit price", "Final Price", "Profit Margin", "Wholesale", "Store Manager", "POS", "Buy Button Links"])

def save_pwp(df):
    df.to_csv("PwP.csv", index=False)

def show_product_management():
    st.title("Product Management")
    st.caption("View, edit, and add products to your catalog (PwP.csv).")

    # Load data
    df = load_pwp()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["View & Edit Products", "Add New Product", "Product Merger"])

    # --- VIEW & EDIT ---
    with tab1:
        st.subheader("Current Product Catalog")
        st.info("💡 Edit cells directly below and click 'Save Changes' to update PwP.csv")
        
        # We want to allow editing of specific columns
        # The user mentioned: names, sku, unit number (assuming Unit price/Final Price)
        
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            key="product_editor",
            column_config={
                "Product name": st.column_config.TextColumn("Product Name", required=True),
                "SKU#": st.column_config.TextColumn("SKU", required=True),
                "Category": st.column_config.TextColumn("Category"),
                "Unit price": st.column_config.TextColumn("Unit Price"),
                "Final Price": st.column_config.TextColumn("Final Price"),
                "Buy Button Links": st.column_config.LinkColumn("Buy Link")
            }
        )

        if st.button("💾 Save Changes", type="primary"):
            save_pwp(edited_df)
            st.success("Product catalog updated successfully!")
            st.cache_data.clear() # Clear cache so other tools see changes
            st.rerun()

    # --- ADD NEW PRODUCT ---
    with tab2:
        st.subheader("Add New Product")
        
        with st.form("add_product_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("Product Name*", help="Required")
                new_sku = st.text_input("SKU*", help="Required - must be unique")
                new_category = st.selectbox("Category", options=sorted(df["Category"].unique().tolist()) + ["New Category..."])
                if new_category == "New Category...":
                    new_category = st.text_input("Enter New Category Name")
                
                new_unit_price = st.text_input("Unit Price (e.g. $10.00)*", value="$0.00", help="Cost to you")
                new_final_price = st.text_input("Final Price (e.g. $19.99)*", value="$0.00", help="Selling price")
            
            with c2:
                new_profit_margin = st.text_input("Profit Margin (e.g. 100.50%)", value="", help="Leave empty to auto-calculate from Unit Price and Final Price")
                new_buy_link = st.text_input("Buy Button Link", value="", help="URL for the buy button")
                
                st.write("**Product Availability:**")
                new_wholesale = st.checkbox("Wholesale", value=True)
                new_store_manager = st.checkbox("Store Manager", value=True)
                new_pos = st.checkbox("POS", value=True)
                
                # Image Upload
                uploaded_image = st.file_uploader("Product Image", type=['png', 'jpg', 'jpeg'])
            
            submitted = st.form_submit_button("Add Product", type="primary")
            
            if submitted:
                if not new_name or not new_sku:
                    st.error("Product Name and SKU are required!")
                else:
                    # Check if SKU already exists
                    if new_sku in df["SKU#"].values:
                        st.error(f"SKU '{new_sku}' already exists!")
                    else:
                        # Calculate profit margin
                        margin = new_profit_margin.strip()
                        if not margin:
                            # Auto-calculate from prices
                            try:
                                # Extract numeric values from price strings
                                import re
                                unit_val = float(re.sub(r'[^\d.]', '', new_unit_price))
                                final_val = float(re.sub(r'[^\d.]', '', new_final_price))
                                
                                if unit_val > 0:
                                    profit_pct = ((final_val - unit_val) / unit_val) * 100
                                    margin = f"{profit_pct:.2f}%"
                                else:
                                    margin = "0.00%"
                            except:
                                margin = "0.00%"
                        
                        # Ensure margin has % sign
                        if margin and not margin.endswith("%"):
                            margin = margin + "%"
                        
                        # Create new row
                        new_row = {
                            "Category": new_category,
                            "Product name": new_name,
                            "SKU#": new_sku,
                            "Unit price": new_unit_price,
                            "Final Price": new_final_price,
                            "Profit Margin": margin,
                            "Wholesale": str(new_wholesale).upper(),
                            "Store Manager": str(new_store_manager).upper(),
                            "POS": str(new_pos).upper(),
                            "Buy Button Links": new_buy_link
                        }
                        
                        # Save Image
                        if uploaded_image:
                            os.makedirs("product_images", exist_ok=True)
                            # Get extension
                            ext = os.path.splitext(uploaded_image.name)[1]
                            if not ext: ext = ".png"
                            
                            image_path = f"product_images/{new_sku}{ext}"
                            with open(image_path, "wb") as f:
                                f.write(uploaded_image.getbuffer())
                            st.info(f"Image saved to {image_path}")
                        
                        # Append to DataFrame
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        save_pwp(df)
                        
                        # Show detailed confirmation
                        st.success(f"✅ Successfully added '{new_name}' to PwP.csv!")
                        st.info(f"""
                        **Product Details Saved:**
                        - **Product Name:** {new_name}
                        - **SKU:** {new_sku}
                        - **Category:** {new_category}
                        - **Unit Price:** {new_unit_price}
                        - **Final Price:** {new_final_price}
                        - **Profit Margin:** {margin}
                        - **Buy Link:** {new_buy_link if new_buy_link else "None"}
                        - **Wholesale:** {str(new_wholesale).upper()}
                        - **Store Manager:** {str(new_store_manager).upper()}
                        - **POS:** {str(new_pos).upper()}
                        """)
                        st.balloons()
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
