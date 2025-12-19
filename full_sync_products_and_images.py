"""
Full Sync: Products to Inventory + Images
------------------------------------------
This script performs a complete sync:
1. Syncs all products from products table to inventory table (with 0 stock, N/A images)
2. Then syncs all images from email-product-pictures bucket to inventory table

Usage:
    python full_sync_products_and_images.py
    
Note: This uses the SQL function to bypass RLS policies
"""

from supabase_client import get_supabase


def sync_products_to_inventory():
    """
    Sync all products from products table to inventory table
    Copies ALL product data including image_url, category, price, description
    Uses the SQL function to bypass RLS policies
    """
    try:
        supabase = get_supabase()
        
        print("🔄 Syncing products to inventory using SQL function...")
        print("   (Copying ALL product data including image_url, category, price, description)")
        
        # Call the SQL function that syncs products to inventory
        result = supabase.rpc("sync_products_to_inventory_auto").execute()
        
        inserted_count = result.data if result.data else 0
        
        if inserted_count > 0:
            print(f"✅ Added {inserted_count} new products to inventory with all product data")
        else:
            print("✅ All products already in inventory")
        
        return inserted_count
        
    except Exception as e:
        print(f"❌ Error syncing products: {e}")
        print("⚠️  Make sure you've run the setup_inventory_sync.sql script first!")
        return 0


def sync_images_to_inventory():
    """
    Sync all images from email-product-pictures bucket to inventory table
    """
    try:
        supabase = get_supabase()
        bucket_name = "email-product-pictures"
        
        print("\n🖼️  Syncing images to inventory...")
        
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
                skipped_count += 1
                continue
            
            # Extract SKU from filename (remove extension)
            sku = filename.rsplit('.', 1)[0]
            
            if not sku:
                skipped_count += 1
                continue
            
            try:
                # Generate public URL
                public_url = supabase.storage.from_(bucket_name).get_public_url(filename)
                
                # Check if SKU exists in inventory
                check_result = supabase.table("inventory").select("sku").eq("sku", sku).execute()
                
                if not check_result.data:
                    print(f"  ⚠️  SKU '{sku}' not in inventory - skipping")
                    skipped_count += 1
                    continue
                
                # Update inventory with image URL
                update_result = supabase.table("inventory").update({
                    "image_url": public_url
                }).eq("sku", sku).execute()
                
                if update_result.data:
                    print(f"  ✅ Updated '{sku}' with image URL")
                    updated_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                print(f"  ❌ Error processing '{filename}': {e}")
                error_count += 1
        
        return updated_count, skipped_count, error_count
        
    except Exception as e:
        print(f"❌ Error syncing images: {e}")
        return 0, 0, 0


def main():
    """Main entry point"""
    print("="*60)
    print("🚀 FULL SYNC: PRODUCTS → INVENTORY → IMAGES")
    print("="*60)
    print()
    
    try:
        # Step 1: Sync products to inventory
        print("STEP 1: Sync Products to Inventory")
        print("-" * 60)
        products_added = sync_products_to_inventory()
        
        # Step 2: Sync images to inventory
        print("\nSTEP 2: Sync Images to Inventory")
        print("-" * 60)
        images_updated, images_skipped, images_errors = sync_images_to_inventory()
        
        # Summary
        print("\n" + "="*60)
        print("📊 SYNC SUMMARY")
        print("="*60)
        print(f"Products added to inventory: {products_added}")
        print(f"Images synced to inventory:  {images_updated}")
        print(f"Images skipped:              {images_skipped}")
        print(f"Errors:                      {images_errors}")
        print("="*60)
        
        if products_added > 0 or images_updated > 0:
            print("\n✅ Sync completed successfully!")
        else:
            print("\n⚠️  No changes made - everything already synced")
            
    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
