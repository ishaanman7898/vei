"""
Sync Image URLs from Products to Inventory
-------------------------------------------
This script pulls image_url from products table and updates inventory table
by matching SKU units.

Usage:
    python sync_image_urls_from_products.py
"""

from supabase_client import get_supabase


def sync_image_urls():
    """
    Pull image URLs from products table and update inventory table by matching SKU
    """
    try:
        supabase = get_supabase()
        
        print("="*60)
        print("🔄 SYNCING IMAGE URLs FROM PRODUCTS TO INVENTORY")
        print("="*60)
        print()
        
        # Get all products with image URLs
        print("📥 Fetching products from products table...")
        products_result = supabase.table("products").select("sku, image_url").execute()
        products = products_result.data
        
        if not products:
            print("❌ No products found in products table")
            return 0
        
        print(f"✅ Found {len(products)} products")
        print()
        
        # Get all inventory records
        print("📥 Fetching inventory records...")
        inventory_result = supabase.table("inventory").select("sku, image_url").execute()
        inventory = inventory_result.data
        
        if not inventory:
            print("❌ No inventory records found")
            return 0
        
        print(f"✅ Found {len(inventory)} inventory records")
        print()
        
        # Create a map of SKU to image_url from products
        product_images = {}
        for product in products:
            sku = product.get('sku')
            image_url = product.get('image_url')
            if sku and image_url and image_url != 'N/A':
                product_images[sku] = image_url
        
        print(f"📊 Found {len(product_images)} products with valid image URLs")
        print()
        
        # Update inventory records
        print("🔄 Updating inventory with image URLs...")
        updated_count = 0
        skipped_count = 0
        
        for inv_record in inventory:
            sku = inv_record.get('sku')
            current_image = inv_record.get('image_url')
            
            # Check if this SKU has an image URL in products table
            if sku in product_images:
                new_image_url = product_images[sku]
                
                # Only update if different
                if current_image != new_image_url:
                    try:
                        supabase.table("inventory").update({
                            "image_url": new_image_url
                        }).eq("sku", sku).execute()
                        
                        print(f"  ✅ Updated SKU '{sku}': {new_image_url[:50]}...")
                        updated_count += 1
                    except Exception as e:
                        print(f"  ❌ Failed to update SKU '{sku}': {e}")
                else:
                    skipped_count += 1
            else:
                # No image URL in products table for this SKU
                if current_image == 'N/A' or not current_image:
                    print(f"  ⚠️  SKU '{sku}' has no image in products table")
                skipped_count += 1
        
        print()
        print("="*60)
        print("📊 SYNC COMPLETE")
        print("="*60)
        print(f"✅ Updated: {updated_count}")
        print(f"⏭️  Skipped: {skipped_count}")
        print("="*60)
        
        return updated_count
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0


def main():
    """Main entry point"""
    try:
        updated = sync_image_urls()
        
        if updated > 0:
            print(f"\n✅ Successfully synced {updated} image URLs from products to inventory!")
        else:
            print("\n⚠️  No image URLs were synced")
            
    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
