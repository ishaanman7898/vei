import streamlit as st
import pandas as pd
import io


def show_product_merger():
    st.title("Product Merger")
    st.markdown("Upload the **Orders CSV** and **Products CSV** from Shopify to generate a merged order report.")

    col1, col2 = st.columns(2)
    with col1:
        orders_file = st.file_uploader("Upload Orders CSV", type=["csv"], key="merger_orders")
    with col2:
        products_file = st.file_uploader("Upload Products CSV", type=["csv"], key="merger_products")

    if orders_file and products_file:
        try:
            orders_df = pd.read_csv(orders_file)
            products_df = pd.read_csv(products_file)
        except Exception as e:
            st.error(f"Error reading CSV files: {e}")
            return

        # Strip whitespace from column names
        orders_df.columns = orders_df.columns.str.strip()
        products_df.columns = products_df.columns.str.strip()

        # Validate required columns
        required_orders = {"Transaction no", "Date", "Billing name", "Billing company",
                           "Billing city", "Billing state/province", "Customer email",
                           "Subtotal", "Discount", "Shipping", "Tax", "Total"}
        required_products = {"Transaction no", "Item name", "Quantity"}

        missing_orders = required_orders - set(orders_df.columns)
        missing_products = required_products - set(products_df.columns)

        if missing_orders:
            st.error(f"Orders CSV is missing columns: {', '.join(missing_orders)}")
            return
        if missing_products:
            st.error(f"Products CSV is missing columns: {', '.join(missing_products)}")
            return

        # Build Product(s) Ordered & Quantity per transaction
        products_df["Transaction no"] = products_df["Transaction no"].astype(str).str.strip()
        products_df["Item name"] = products_df["Item name"].astype(str).str.strip()
        products_df["Quantity"] = products_df["Quantity"].fillna(1)

        def aggregate_items(group):
            parts = []
            for _, row in group.iterrows():
                qty = row["Quantity"]
                try:
                    qty = int(float(qty))
                except (ValueError, TypeError):
                    qty = row["Quantity"]
                parts.append(f"{row['Item name']} x{qty}")
            return ", ".join(parts)

        products_grouped = (
            products_df.groupby("Transaction no")
            .apply(aggregate_items)
            .reset_index()
        )
        products_grouped.columns = ["Transaction no", "Product(s) Ordered & Quantity"]

        # Prepare orders — drop duplicate transaction rows (Shopify repeats per line item)
        orders_df["Transaction no"] = orders_df["Transaction no"].astype(str).str.strip()
        orders_df = orders_df.drop_duplicates(subset="Transaction no")

        merged = orders_df.merge(products_grouped, on="Transaction no", how="left")

        # Build output dataframe
        output = pd.DataFrame()
        output["Web or Booth"] = "N/A"
        output["Transaction No."] = merged["Transaction no"]
        output["Purchase Date"] = merged["Date"]
        output["Customer Name"] = merged["Billing name"]
        output["Company"] = merged["Billing company"]
        output["City"] = merged["Billing city"]
        output["State"] = merged["Billing state/province"]
        output["Customer E-Mail"] = merged["Customer email"]
        output["Product(s) Ordered & Quantity"] = merged["Product(s) Ordered & Quantity"]
        output["Order Subtotal"] = merged["Subtotal"]
        output["Discount Applied"] = merged["Discount"]
        output["Shipping"] = merged["Shipping"]
        output["Tax"] = merged["Tax"]
        output["Order Total"] = merged["Total"]
        output["Shipping Status"] = ""
        output["Notes"] = ""

        st.success(f"Merged {len(output)} orders successfully.")
        st.dataframe(output, use_container_width=True)

        csv_bytes = output.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Merged CSV",
            data=csv_bytes,
            file_name="merged_orders.csv",
            mime="text/csv",
        )
