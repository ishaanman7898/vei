"""
Sync Storage Images to Inventory
---------------------------------
This script syncs all images from the 'email-product-pictures' bucket
to the inventory table by:
1. Reading all files from the bucket
2. Extracting SKU from filename (e.g., "ABC-123.jpg" -> "ABC-123")
3. Generating public URL for each image
4. Updating inventory table with the image URL for matching SKU

Usage:
    python sync_storage_to_inventory.py
"""

from supabase_client import get_supabase


def sync_storage_images_to_inventory():
    """
    Sync all images from email-product-pictures bucket to inventory table
    
    Returns:
        tuple: (updated_count, skipped_count, error_count)
    """
    try:
        supabase = get_supabase()
        bucket_name = "email-product-pictures"
        
        print(f"🔍 Fetching images from '{bucket_name}' bucket...")
        
        # List all files in the bucket
        files = supabase.storage.from_(bucket_name).list()
        
        if not files:
            print("❌ No files found in bucket")
            return 0, 0, 0
        
        print(f"✅ Found {len(files)} files in bucket")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for file in files:
            filename = file.get('name', '')
            
            # Skip non-image files
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                print(f"⏭️  Skipping non-image file: {filename}")
                skipped_count += 1
                continue
            
            # Extract SKU from filename (remove extension)
            sku = filename.rsplit('.', 1)[0]
            
            if not sku:
                print(f"⚠️  Skipping file with no SKU: {filename}")
                skipped_count += 1
                continue
            
            try:
                # Generate public URL
                public_url = supabase.storage.from_(bucket_name).get_public_url(filename)
                
                # Check if SKU exists in inventory
                check_result = supabase.table("inventory").select("sku").eq("sku", sku).execute()
                
                if not check_result.data:
                    print(f"⚠️  SKU '{sku}' not found in inventory - skipping")
                    skipped_count += 1
                    continue
                
                # Update inventory with image URL
                update_result = supabase.table("inventory").update({
                    "image_url": public_url
                }).eq("sku", sku).execute()
                
                if update_result.data:
                    print(f"✅ Updated SKU '{sku}' with image URL")
                    updated_count += 1
                else:
                    print(f"⚠️  Failed to update SKU '{sku}'")
                    error_count += 1
                    
            except Exception as e:
                print(f"❌ Error processing '{filename}': {e}")
                error_count += 1
        
        print("\n" + "="*50)
        print(f"📊 SYNC COMPLETE")
        print(f"✅ Updated: {updated_count}")
        print(f"⏭️  Skipped: {skipped_count}")
        print(f"❌ Errors: {error_count}")
        print("="*50)
        
        return updated_count, skipped_count, error_count
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 0, 0, 0


def main():
    """Main entry point"""
    print("="*50)
    print("🖼️  SYNC STORAGE IMAGES TO INVENTORY")
    print("="*50)
    print()
    
    try:
        updated, skipped, errors = sync_storage_images_to_inventory()
        
        if updated > 0:
            print(f"\n✅ Successfully synced {updated} images to inventory!")
        else:
            print("\n⚠️  No images were synced")
            
    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
