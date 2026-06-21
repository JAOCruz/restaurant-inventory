-- Restaurant Inventory Database Schema for SQLite
-- Used by scripts/init_db.sh and as a reference for local development.
-- For PostgreSQL, see schema.postgres.sql.

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    contact_name VARCHAR(150),
    phone VARCHAR(30),
    email VARCHAR(150),
    address TEXT
);

CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    category_id INTEGER,
    supplier_id INTEGER,
    unit VARCHAR(20) NOT NULL,
    reorder_level NUMERIC(12, 3) NOT NULL DEFAULT 0,
    reorder_quantity NUMERIC(12, 3) NOT NULL DEFAULT 0,
    current_stock NUMERIC(12, 3) NOT NULL DEFAULT 0,
    cost_per_unit NUMERIC(12, 2),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_ingredients_non_negative_stock CHECK (current_stock >= 0),
    CONSTRAINT ck_ingredients_reorder_level CHECK (reorder_level >= 0),
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS stock_transactions (
    id INTEGER PRIMARY KEY,
    ingredient_id INTEGER NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    quantity NUMERIC(12, 3) NOT NULL,
    reference VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_transactions_positive_quantity CHECK (quantity > 0),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
);

-- Indexes for common query patterns.
CREATE INDEX IF NOT EXISTS idx_ingredients_category ON ingredients(category_id);
CREATE INDEX IF NOT EXISTS idx_ingredients_supplier ON ingredients(supplier_id);
CREATE INDEX IF NOT EXISTS idx_ingredients_sku ON ingredients(sku);
CREATE INDEX IF NOT EXISTS idx_transactions_ingredient ON stock_transactions(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created ON stock_transactions(created_at);
