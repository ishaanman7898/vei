"""
Migration script to upload product images to Supabase Storage
and update the products table with image URLs
Compresses images before upload to optimize email loading
"""
import os
from pathlib import Path
from PIL import Image
import io
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_standalone_supabase():
    """Get Supabase client without Streamlit session"""
    url = os.getenv("SUPABASE_URL", "").strip().strip('"').strip("'")
    key = os.getenv("SUPABASE_ANON_KEY", "").strip().strip('"').strip("'")
    
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env file")
    
    return create_client(url, key)

def compress_image(image_path, max_width=800, quality=85):
    """
    Compress and resize image for email optimization
    
    Args:
        image_path: Path to original image
        max_width: Maximum width in pixels (default 800px)
        quality: JPEG quality 1-100 (default 85)
    
    Returns:
        Compressed image bytes and format
    """
    img = Image.open(image_path)
    
    # Convert RGBA to RGB if needed (for JPEG)
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
    output.seek(0)
    
    return output.read(), 'image/jpeg'

def migrate_product_images():
    """Upload all product images from local folder to Supabase storage"""
    
    supabase = get_standalone_supabase()
    bucket_name = "email-product-pictures"
    local_images_dir = "product-images"
    
    # Get all image files
    image_extensions = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(Path(local_images_dir).glob(f"*{ext}"))
    
    print(f"Found {len(image_files)} images to migrate")
    print("Compressing and uploading...\n")
    
    uploaded = 0
    skipped = 0
    errors = 0
    total_original_size = 0
    total_compressed_size = 0
    
    for image_path in image_files:
        filename = image_path.stem + '.jpg'  # Save all as .jpg after compression
        sku = image_path.stem  # Filename without extension
        
        try:
            # Get original size
            original_size = os.path.getsize(image_path)
            total_original_size += original_size
            
            # Compress image
            print(f"Compressing {image_path.name}...", end=" ")
            compressed_data, content_type = compress_image(image_path)
            compressed_size = len(compressed_data)
            total_compressed_size += compressed_size
            
            reduction = ((original_size - compressed_size) / original_size) * 100
            print(f"({original_size//1024}KB → {compressed_size//1024}KB, -{reduction:.0f}%)", end=" ")
            
            # Upload to Supabase storage
            result = supabase.storage.from_(bucket_name).upload(
                path=filename,
                file=compressed_data,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            
            # Get public URL
            public_url = supabase.storage.from_(bucket_name).get_public_url(filename)
            
            # Update products table with image URL
            update_result = supabase.table("products").update({
                "image_url": public_url
            }).eq("sku", sku).execute()
            
            if hasattr(update_result, 'data') and update_result.data:
                print(f"✅ Linked to SKU: {sku}")
                uploaded += 1
            else:
                print(f"⚠️ Uploaded but no product found with SKU: {sku}")
                skipped += 1
                
        except Exception as e:
            print(f"❌ Error: {e}")
            errors += 1
    
    total_reduction = ((total_original_size - total_compressed_size) / total_original_size) * 100 if total_original_size > 0 else 0
    
    print("\n" + "="*50)
    print(f"Migration Complete!")
    print(f"✅ Successfully uploaded: {uploaded}")
    print(f"⚠️ Uploaded but not linked: {skipped}")
    print(f"❌ Errors: {errors}")
    print(f"\n📦 Storage saved: {(total_original_size - total_compressed_size)//1024}KB ({total_reduction:.1f}% reduction)")
    print(f"   Original: {total_original_size//1024}KB → Compressed: {total_compressed_size//1024}KB")
    print("="*50)
    
    return uploaded, skipped, errors

if __name__ == "__main__":
    print("Starting product image migration to Supabase...")
    print("="*50)
    migrate_product_images()
