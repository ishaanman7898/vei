-- Create inventory table for Thrive Tools
-- This replaces Google Sheets inventory management with Supabase

-- Drop view if it exists (for re-runs)
DROP VIEW IF EXISTS inventory_summary;

-- Drop table if it exists (for re-runs)
DROP TABLE IF EXISTS inventory CASCADE;

-- Drop trigger if it exists (for re-runs)
DROP TRIGGER IF EXISTS sync_new_product_to_inventory ON products;

-- Drop function if it exists (for re-runs)
DROP FUNCTION IF EXISTS sync_inventory_for_new_product() CASCADE;

-- Drop function if it exists (for re-runs)
DROP FUNCTION IF EXISTS sync_all_products_to_inventory() CASCADE;

-- Create inventory table
CREATE TABLE inventory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_name TEXT NOT NULL,
  sku TEXT UNIQUE NOT NULL,
  stock_bought INTEGER NOT NULL DEFAULT 0,
  stock_left INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'In stock',
  last_updated_from_invoice TEXT,
  invoice_date TEXT,
  due_date TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  created_by TEXT,
  
  -- Constraints
  CONSTRAINT check_stock_bought CHECK (stock_bought >= 0),
  -- Note: stock_left can be negative for backordered items
  CONSTRAINT check_status CHECK (status IN ('In stock', 'Out of stock', 'Low stock', 'Backordered'))
);

-- Create indexes for better performance
CREATE INDEX idx_inventory_sku ON inventory(sku);
CREATE INDEX idx_inventory_status ON inventory(status);
CREATE INDEX idx_inventory_item_name ON inventory(item_name);

-- Enable Row Level Security (RLS)
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
-- Allow authenticated users to read inventory
CREATE POLICY "Allow authenticated users to read inventory" ON inventory
  FOR SELECT USING (auth.role() = 'authenticated');

-- Allow authenticated users to insert inventory
CREATE POLICY "Allow authenticated users to insert inventory" ON inventory
  FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Allow authenticated users to update their own inventory records
CREATE POLICY "Allow authenticated users to update inventory" ON inventory
  FOR UPDATE USING (auth.role() = 'authenticated');

-- Allow authenticated users to delete inventory
CREATE POLICY "Allow authenticated users to delete inventory" ON inventory
  FOR DELETE USING (auth.role() = 'authenticated');

-- Create trigger for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_inventory_updated_at 
    BEFORE UPDATE ON inventory 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-sync function to create inventory records for new products
CREATE OR REPLACE FUNCTION sync_inventory_for_new_product()
RETURNS TRIGGER AS $$
BEGIN
    -- Only create inventory record if one doesn't already exist for this SKU
    IF NOT EXISTS (
        SELECT 1 FROM inventory WHERE inventory.sku = NEW.sku
    ) THEN
        INSERT INTO inventory (
            item_name, 
            sku, 
            stock_bought, 
            stock_left, 
            status, 
            created_by
        ) VALUES (
            NEW.name,
            NEW.sku,
            0,  -- Start with 0 stock bought
            0,  -- Start with 0 stock left
            'Out of stock',  -- New products start as out of stock
            NEW.created_by
        );
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-sync new products to inventory
CREATE TRIGGER sync_new_product_to_inventory
    AFTER INSERT ON products
    FOR EACH ROW
    EXECUTE FUNCTION sync_inventory_for_new_product();

-- Function to sync existing products that don't have inventory records
CREATE OR REPLACE FUNCTION sync_all_products_to_inventory()
RETURNS INTEGER AS $$
DECLARE
    sync_count INTEGER;
BEGIN
    -- Insert inventory records for products that don't have them
    INSERT INTO inventory (
        item_name, 
        sku, 
        stock_bought, 
        stock_left, 
        status, 
        created_by
    )
    SELECT 
        p.name,
        p.sku,
        0,  -- Start with 0 stock bought
        0,  -- Start with 0 stock left
        'Out of stock',  -- New products start as out of stock
        p.created_by
    FROM products p
    WHERE NOT EXISTS (
        SELECT 1 FROM inventory i WHERE i.sku = p.sku
    );
    
    GET DIAGNOSTICS sync_count = ROW_COUNT;
    RETURN sync_count;
END;
$$ LANGUAGE plpgsql;

-- Insert sample data from current inventory
-- You can run these INSERT statements after creating the table

INSERT INTO inventory (item_name, sku, stock_bought, stock_left, status, last_updated_from_invoice, invoice_date, due_date) VALUES
('Divider', 'O-DI', 60, 22, 'In stock', '44640 | 44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Ice Molds', 'O-IM', 58, 29, 'In stock', '44640 | 44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Shaker Ball', 'O-SB', 61, 13, 'In stock', '44640 | 44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Anchor (Snack Compartment)', 'O-AN', 53, 25, 'In stock', '44640 | 44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Surge IV (Cucumber Lime)', 'SU-EL-7', 50, 27, 'In stock', '44640', 'Nov 05, 2025 Thrive Wellness', 'Dec 05, 2025'),
('Surge IV (Lemonade)', 'SU-EL-3', 55, 23, 'In stock', '44640 | 44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Surge IV (Strawberry)', 'SU-EL-5', 53, 19, 'In stock', '44640 | 44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Snow Cap (Modified Lid)', 'CA-SC', 55, 29, 'In stock', '44640 | 44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Peak Powder (Chocolate)', 'SU-PR-1', 65, 17, 'In stock', '44640 | 44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Peak Powder (Vanilla)', 'SU-PR-2', 62, 16, 'In stock', '44640 | 44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Iceberg (32 oz bottle) w. Ice Cap', 'BO-48', 50, 46, 'In stock', '44640', 'Nov 05, 2025 Thrive Wellness', 'Dec 05, 2025'),
('The Glacier (40 oz bottle) w. Ice Cap', 'BO-38', 50, 50, 'In stock', '44640', 'Nov 05, 2025 Thrive Wellness', 'Dec 05, 2025'),
('Alo x Thrive Bundle', 'SE-F-1', 50, -18, 'Backordered', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Fall Bundle', 'SE-F-3', 35, -1, 'Backordered', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Peleton x Thrive Bundle', 'SE-F-2', 10, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Surge IV (Blue Razzberry)', 'SU-EL-1', 7, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Surge IV (Fruit Punch)', 'SU-EL-2', 2, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Surge IV (Pina Colada)', 'SU-EL-4', 1, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('Surge IV (Tropical Vibes)', 'SU-EL-6', 1, 1, 'Low stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Glacier (Black) w. Ice Cap', 'BO-41', 8, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Glacier (Brown) w. Ice Cap', 'BO-42', 6, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Glacier (Frost Blue) w. Ice Cap', 'BO-43', 13, -2, 'Backordered', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Glacier (Maroon) w. Ice Cap', 'BO-44', 9, -1, 'Backordered', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Glacier (Orange) w. Ice Cap', 'BO-45', 8, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Glacier (White) w. Ice Cap', 'BO-46', 15, -94, 'Backordered', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Iceberg (Black) w. Ice Cap', 'BO-31', 2, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Iceberg (Brown) w. Ice Cap', 'BO-32', 5, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Iceberg (Frost Blue) w. Ice Cap', 'BO-33', 8, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Iceberg (Maroon) w. Ice Cap', 'BO-34', 1, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Iceberg (Orange) w. Ice Cap', 'BO-35', 1, 0, 'Out of stock', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025'),
('The Iceberg (White) w. Ice Cap', 'BO-36', 2, -64, 'Backordered', '44851', 'Nov 18, 2025 Thrive Wellness', 'Dec 18, 2025')
ON CONFLICT (sku) DO UPDATE SET
  item_name = EXCLUDED.item_name,
  stock_bought = EXCLUDED.stock_bought,
  stock_left = EXCLUDED.stock_left,
  status = EXCLUDED.status,
  last_updated_from_invoice = EXCLUDED.last_updated_from_invoice,
  invoice_date = EXCLUDED.invoice_date,
  due_date = EXCLUDED.due_date;

-- Create a view for easy inventory status summary
CREATE VIEW inventory_summary AS
SELECT 
    status,
    COUNT(*) as item_count,
    SUM(stock_left) as total_stock_left,
    SUM(stock_bought) as total_stock_bought
FROM inventory 
GROUP BY status
ORDER BY 
    CASE status 
        WHEN 'Backordered' THEN 1
        WHEN 'Out of stock' THEN 2
        WHEN 'Low stock' THEN 3
        WHEN 'In stock' THEN 4
    END;

-- Comments for documentation
COMMENT ON TABLE inventory IS 'Inventory management table replacing Google Sheets integration';
COMMENT ON COLUMN inventory.item_name IS 'Display name of the inventory item';
COMMENT ON COLUMN inventory.sku IS 'Unique SKU identifier that links to products table';
COMMENT ON COLUMN inventory.stock_bought IS 'Total quantity purchased/acquired';
COMMENT ON COLUMN inventory.stock_left IS 'Current available inventory quantity';
COMMENT ON COLUMN inventory.status IS 'Current inventory status: In stock, Out of stock, Low stock, Backordered';
COMMENT ON COLUMN inventory.last_updated_from_invoice IS 'Invoice numbers that triggered the last update';
COMMENT ON COLUMN inventory.invoice_date IS 'Date of the last invoice';
COMMENT ON COLUMN inventory.due_date IS 'Payment due date for the last invoice';

-- Usage instructions:
-- 1. Run this entire script in Supabase SQL Editor
-- 2. To sync existing products to inventory, run: SELECT sync_all_products_to_inventory();
-- 3. New products added via Product Management will automatically create inventory records
-- 4. Use inventory table in your Inventory Management module instead of Google Sheets
