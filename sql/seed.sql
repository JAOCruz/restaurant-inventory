-- Seed data for local development and demos.

INSERT INTO categories (name, description) VALUES
    ('Produce', 'Fresh fruits and vegetables'),
    ('Dairy', 'Milk, cheese, eggs, and cream'),
    ('Meat & Poultry', 'Beef, chicken, pork, and lamb'),
    ('Seafood', 'Fish and shellfish'),
    ('Dry Goods', 'Grains, pulses, flour, and pasta'),
    ('Beverages', 'Soft drinks, juices, and bar stock'),
    ('Cleaning', 'Cleaning and sanitation supplies');

INSERT INTO suppliers (name, contact_name, phone, email, address) VALUES
    ('Green Valley Produce', 'Maria Gonzalez', '555-0101', 'maria@greenvalley.example', '123 Farm Rd'),
    ('Dairy Direct', 'Tom Miller', '555-0102', 'tom@dairydirect.example', '456 Dairy Ln'),
    ('Prime Meats', 'Sarah Lee', '555-0103', 'sarah@primemeats.example', '789 Butcher St'),
    ('Ocean Fresh', 'David Kim', '555-0104', 'david@oceanfresh.example', '321 Harbor Ave'),
    ('Wholesale Pantry', 'Lisa Chen', '555-0105', 'lisa@wholesalepantry.example', '654 Warehouse Blvd');

INSERT INTO ingredients (sku, name, unit, category_id, supplier_id, reorder_level, reorder_quantity, current_stock, cost_per_unit) VALUES
    ('TOM-001', 'Roma Tomatoes', 'kg', 1, 1, 5.0, 10.0, 12.5, 2.50),
    ('LET-001', 'Romaine Lettuce', 'piece', 1, 1, 10.0, 20.0, 18.0, 1.75),
    ('CHE-001', 'Mozzarella Cheese', 'kg', 2, 2, 3.0, 8.0, 5.0, 8.00),
    ('MIL-001', 'Whole Milk', 'liter', 2, 2, 10.0, 25.0, 22.0, 1.20),
    ('BEEF-001', 'Ground Beef 80/20', 'kg', 3, 3, 8.0, 20.0, 15.0, 9.50),
    ('CHKN-001', 'Chicken Breast', 'kg', 3, 3, 10.0, 30.0, 28.0, 7.25),
    ('FSH-001', 'Atlantic Salmon', 'kg', 4, 4, 4.0, 12.0, 6.5, 18.00),
    ('RICE-001', 'Arborio Rice', 'kg', 5, 5, 5.0, 15.0, 20.0, 3.40),
    ('PASTA-001', 'Spaghetti Pasta', 'kg', 5, 5, 4.0, 10.0, 7.0, 2.10),
    ('OIL-001', 'Olive Oil Extra Virgin', 'liter', 5, 5, 3.0, 10.0, 8.0, 12.50);
