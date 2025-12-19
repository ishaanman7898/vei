"""
Create Inventory Records from Products
---------------------------------------
This script creates inventory records for all products in the products table.
Copies ALL product data including image_url.

Usage:
    python create_inventory_from_products.py
"""

from supabase_client import get_supabase


def create_inventory_from_products():
    """
    Create inventory records from products table
    """
    try:
        supabase = get_supabase()
        
        print("="*60)
        print("📦 CREATING INVENTORY FROM PRODUCTS")
        print("="*60)
        print()
        
        # Get all products
        print("📥 Fetching products from products table...")
        products_result = supabase.table("products").select("*").execute()
        products = products_result.data
        
        if not products:
            print("❌ No products found in products table")
            return 0
        
        print(f"✅ Found {len(products)} products")
        print()
        
        # Get existing inventory SKUs
        print("📥 Checking existing inventory...")
        inventory_result = supabase.table("inventory").select("sku").execute()
        existing_skus = {row['sku'] for row in inventory_result.data}
        
        print(f"📦 Found {len(existing_skus)} existing inventory records")
        print()
        
        # Create inventory records for products that don't exist
        new_products = [p for p in products if p['sku'] not in existing_skus]
        
        if not new_products:
            print("✅ All products already in inventory")
            return 0
        
        print(f"➕ Creating {len(new_products)} new inventory records...")
        print()
        
        created_count = 0
        failed_count = 0
        
        for product in new_products:
            try:
                inventory_record = {
                    "sku": product['sku'],
                    "item_name": product['name'],
                    "stock_bought": 0,
                    "stock_left": 0,
                    "status": "Out of stock",
                    "image_url": product.get('image_url') or 'N/A',
                    "category": product.get('category'),
                    "price": product.get('price'),
                    "description": product.get('description')
                }
                
                # Use upsert to avoid conflicts
                supabase.table("inventory").upsert(inventory_record, on_conflict="sku").execute()
                
                image_status = "✅" if product.get('image_url') and product.get('image_url') != 'N/A' else "⚠️"
                print(f"  {image_status} Created '{product['sku']}' - {product['name']}")
                created_count += 1
                
            except Exception as e:
                print(f"  ❌ Failed to create '{product['sku']}': {e}")
                failed_count += 1
        
        print()
        print("="*60)
        print("📊 SUMMARY")
        print("="*60)
        print(f"✅ Created: {created_count}")
        print(f"❌ Failed: {failed_count}")
        print("="*60)
        
        return created_count
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """Main entry point"""
    try:
        created = create_inventory_from_products()
        
        if created > 0:
            print(f"\n✅ Successfully created {created} inventory records!")
            print("\nNow run: python sync_image_urls_from_products.py")
            print("to sync any missing image URLs")
        else:
            print("\n⚠️  No inventory records were created")
            
    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
