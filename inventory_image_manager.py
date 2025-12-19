"""
Inventory Image Manager
-----------------------
This script manages product images for the inventory system:
1. Pulls images from 'email-product-pictures' bucket in Supabase Storage
2. Creates public URLs for each product image
3. Associates SKU with the product image
4. Updates inventory table with image URLs
5. Compresses and uploads new images to Supabase Storage

Usage:
    python inventory_image_manager.py
"""

import streamlit as st
import pandas as pd
from PIL import Image
import io
from supabase_client import get_authed_supabase


def get_storage_images():
    """Get list of all images in email-product-pictures bucket"""
    try:
        supabase = get_authed_supabase()
        bucket_name = "email-product-pictures"
        
        # List all files in bucket
        files = supabase.storage.from_(bucket_name).list()
        
        return files
    except Exception as e:
        st.error(f"Failed to fetch images from storage: {e}")
        return []


def generate_public_url(sku: str, bucket_name: str = "email-product-pictures") -> str:
    """Generate public URL for a product image"""
    try:
        supabase = get_authed_supabase()
        filename = f"{sku}.jpg"
        
        # Get public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(filename)
        
        return public_url
    except Exception as e:
        st.error(f"Failed to generate URL for SKU {sku}: {e}")
        return None


def update_inventory_image_url(sku: str, image_url: str):
    """Update inventory table with image URL for a specific SKU"""
    try:
        supabase = get_authed_supabase()
        
        # Update inventory table
        supabase.table("inventory").update({
            "image_url": image_url
        }).eq("sku", sku).execute()
        
        return True
    except Exception as e:
        st.error(f"Failed to update inventory for SKU {sku}: {e}")
        return False


def sync_all_inventory_images():
    """
    Sync all images from storage to inventory table
    - Reads from email-product-pictures bucket
    - Generates public URLs
    - Updates inventory table
    """
    try:
        supabase = get_authed_supabase()
        bucket_name = "email-product-pictures"
        
        # Get all files from storage
        files = supabase.storage.from_(bucket_name).list()
        
        updated_count = 0
        skipped_count = 0
        
        for file in files:
            filename = file.get('name', '')
            
            # Extract SKU from filename (remove .jpg extension)
            if filename.endswith('.jpg'):
                sku = filename.replace('.jpg', '')
                
                # Generate public URL
                public_url = supabase.storage.from_(bucket_name).get_public_url(filename)
                
                # Update inventory
                result = supabase.table("inventory").update({
                    "image_url": public_url
                }).eq("sku", sku).execute()
                
                if result:
                    updated_count += 1
                else:
                    skipped_count += 1
        
        return updated_count, skipped_count
    except Exception as e:
        st.error(f"Failed to sync images: {e}")
        return 0, 0


def compress_and_upload_image(sku: str, image_file, max_width: int = 800, quality: int = 85):
    """
    Compress an image and upload to Supabase Storage
    
    Args:
        sku: Product SKU
        image_file: Uploaded file object
        max_width: Maximum width for resizing (default 800px)
        quality: JPEG quality (default 85)
    
    Returns:
        public_url: Public URL of uploaded image, or None if failed
    """
    try:
        supabase = get_authed_supabase()
        bucket_name = "email-product-pictures"
        
        # Open and compress image
        img = Image.open(image_file)
        
        # Convert RGBA to RGB if needed
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        
        # Resize if too large
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Compress to bytes
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        compressed_data = output.getvalue()
        
        # Upload to Supabase
        filename = f"{sku}.jpg"
        
        result = supabase.storage.from_(bucket_name).upload(
            path=filename,
            file=compressed_data,
            file_options={"content-type": "image/jpeg", "upsert": "true"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(filename)
        
        # Update inventory table
        update_inventory_image_url(sku, public_url)
        
        return public_url
    except Exception as e:
        st.error(f"Failed to compress and upload image: {e}")
        return None


def get_inventory_missing_images():
    """Get all inventory items with missing images (N/A or NULL)"""
    try:
        supabase = get_authed_supabase()
        
        # Query inventory for missing images
        result = supabase.table("inventory").select("sku, item_name, image_url").or_(
            "image_url.eq.N/A,image_url.is.null"
        ).execute()
        
        return pd.DataFrame(result.data)
    except Exception as e:
        st.error(f"Failed to fetch inventory with missing images: {e}")
        return pd.DataFrame()


def show_inventory_image_manager():
    """Streamlit UI for managing inventory images"""
    st.title("🖼️ Inventory Image Manager")
    st.caption("Manage product images for email campaigns")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📤 Upload Images", "🔄 Sync Images", "📋 Missing Images"])
    
    # --- UPLOAD IMAGES ---
    with tab1:
        st.subheader("Upload Product Images")
        st.info("Upload images for products. They will be compressed and stored in Supabase.")
        
        # Get inventory data
        try:
            supabase = get_authed_supabase()
            inv_result = supabase.table("inventory").select("sku, item_name").execute()
            inventory_df = pd.DataFrame(inv_result.data)
        except Exception as e:
            st.error(f"Failed to load inventory: {e}")
            return
        
        if inventory_df.empty:
            st.warning("No products in inventory. Add products first.")
            return
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # SKU selector
            sku_options = sorted(inventory_df["sku"].tolist())
            selected_sku = st.selectbox("Select Product SKU", options=sku_options)
            
            # Show product name
            if selected_sku:
                item_name = inventory_df[inventory_df["sku"] == selected_sku]["item_name"].iloc[0]
                st.caption(f"Product: **{item_name}**")
            
            # File uploader
            uploaded_file = st.file_uploader(
                "Choose product image",
                type=['png', 'jpg', 'jpeg'],
                help="Image will be compressed and uploaded to Supabase"
            )
        
        with col2:
            st.markdown("**Compression Settings**")
            max_width = st.number_input("Max Width (px)", min_value=400, max_value=2000, value=800, step=100)
            quality = st.slider("JPEG Quality", min_value=60, max_value=100, value=85, step=5)
        
        if uploaded_file and selected_sku:
            if st.button("📤 Upload & Compress", type="primary"):
                with st.spinner("Compressing and uploading..."):
                    # Get original size
                    original_size = len(uploaded_file.getvalue())
                    
                    # Compress and upload
                    public_url = compress_and_upload_image(selected_sku, uploaded_file, max_width, quality)
                    
                    if public_url:
                        # Calculate compression stats
                        uploaded_file.seek(0)  # Reset file pointer
                        img = Image.open(uploaded_file)
                        output = io.BytesIO()
                        
                        if img.mode == 'RGBA':
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            background.paste(img, mask=img.split()[3])
                            img = background
                        
                        if img.width > max_width:
                            ratio = max_width / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                        
                        img.save(output, format='JPEG', quality=quality, optimize=True)
                        compressed_size = len(output.getvalue())
                        reduction = ((original_size - compressed_size) / original_size) * 100
                        
                        st.success(f"✅ Image uploaded successfully!")
                        st.info(f"📊 Compressed: {original_size//1024}KB → {compressed_size//1024}KB (-{reduction:.0f}%)")
                        st.info(f"🔗 URL: {public_url}")
                        st.cache_data.clear()
    
    # --- SYNC IMAGES ---
    with tab2:
        st.subheader("Sync Images from Storage")
        st.info("Sync all images from 'email-product-pictures' bucket to inventory table")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Sync All Images", type="primary"):
                with st.spinner("Syncing images..."):
                    updated, skipped = sync_all_inventory_images()
                    st.success(f"✅ Synced {updated} images")
                    if skipped > 0:
                        st.warning(f"⚠️ Skipped {skipped} images (no matching SKU in inventory)")
                    st.cache_data.clear()
        
        with col2:
            st.caption("This will update inventory table with public URLs for all images in storage")
        
        # Show current images in storage
        st.markdown("### Images in Storage")
        files = get_storage_images()
        
        if files:
            st.caption(f"Found {len(files)} images in storage")
            
            # Display in table
            file_data = []
            for file in files:
                filename = file.get('name', '')
                if filename.endswith('.jpg'):
                    sku = filename.replace('.jpg', '')
                    file_data.append({
                        "SKU": sku,
                        "Filename": filename,
                        "Size": f"{file.get('metadata', {}).get('size', 0) // 1024}KB"
                    })
            
            if file_data:
                st.dataframe(pd.DataFrame(file_data), use_container_width=True)
        else:
            st.info("No images found in storage")
    
    # --- MISSING IMAGES ---
    with tab3:
        st.subheader("Products Missing Images")
        st.info("These products have 'N/A' or no image URL in inventory")
        
        missing_df = get_inventory_missing_images()
        
        if missing_df.empty:
            st.success("✅ All products have images!")
        else:
            st.caption(f"Found {len(missing_df)} products without images")
            st.dataframe(missing_df, use_container_width=True)
            
            # Quick upload for missing images
            st.markdown("### Quick Upload")
            selected_missing_sku = st.selectbox(
                "Select SKU to upload image",
                options=missing_df["sku"].tolist(),
                key="missing_sku_selector"
            )
            
            if selected_missing_sku:
                item_name = missing_df[missing_df["sku"] == selected_missing_sku]["item_name"].iloc[0]
                st.caption(f"Product: **{item_name}**")
                
                quick_upload = st.file_uploader(
                    "Upload image",
                    type=['png', 'jpg', 'jpeg'],
                    key="quick_upload"
                )
                
                if quick_upload:
                    if st.button("📤 Upload", type="primary", key="quick_upload_btn"):
                        with st.spinner("Uploading..."):
                            public_url = compress_and_upload_image(selected_missing_sku, quick_upload)
                            if public_url:
                                st.success(f"✅ Image uploaded for {selected_missing_sku}")
                                st.cache_data.clear()
                                st.rerun()


if __name__ == "__main__":
    show_inventory_image_manager()
