-- seed_products.sql

-- Ensure this supplier exists
INSERT INTO users (email, wallet_address, role)
VALUES
  ('supplier@example.com', '0xYourSupplierWalletAddress', 'supplier')
ON CONFLICT (email) DO NOTHING;

-- Seed two example products
INSERT INTO products (title, category, origin, price_per_kg, owner_email)
VALUES
  ('Whey Protein', 'Dairy', 'Netherlands', 2.75, 'supplier@example.com'),
  ('Coffee Beans', 'Beverage', 'Colombia', 5.00, 'supplier@example.com');

-- Optional: verify
SELECT id, title, owner_email FROM products ORDER BY id DESC LIMIT 5;
