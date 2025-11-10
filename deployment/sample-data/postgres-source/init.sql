-- Sample e-commerce database for lineage testing
-- This represents raw operational data

-- Create schema
CREATE SCHEMA IF NOT EXISTS raw;

-- Customers table
CREATE TABLE raw.customers (
    customer_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE raw.orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES raw.customers(customer_id),
    order_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    shipping_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE raw.products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Order items table (junction table)
CREATE TABLE raw.order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES raw.orders(order_id),
    product_id INTEGER NOT NULL REFERENCES raw.products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL
);

-- Insert sample customers
INSERT INTO raw.customers (email, first_name, last_name, phone) VALUES
    ('john.doe@example.com', 'John', 'Doe', '555-0101'),
    ('jane.smith@example.com', 'Jane', 'Smith', '555-0102'),
    ('bob.johnson@example.com', 'Bob', 'Johnson', '555-0103'),
    ('alice.williams@example.com', 'Alice', 'Williams', '555-0104'),
    ('charlie.brown@example.com', 'Charlie', 'Brown', '555-0105'),
    ('diana.davis@example.com', 'Diana', 'Davis', '555-0106'),
    ('edward.miller@example.com', 'Edward', 'Miller', '555-0107'),
    ('fiona.wilson@example.com', 'Fiona', 'Wilson', '555-0108'),
    ('george.moore@example.com', 'George', 'Moore', '555-0109'),
    ('hannah.taylor@example.com', 'Hannah', 'Taylor', '555-0110');

-- Insert sample products
INSERT INTO raw.products (product_name, category, price, stock_quantity) VALUES
    ('Laptop Pro 15', 'Electronics', 1299.99, 50),
    ('Wireless Mouse', 'Electronics', 29.99, 200),
    ('USB-C Cable', 'Electronics', 19.99, 500),
    ('Desk Lamp', 'Furniture', 49.99, 100),
    ('Office Chair', 'Furniture', 299.99, 30),
    ('Notebook Set', 'Stationery', 12.99, 150),
    ('Pen Pack', 'Stationery', 8.99, 300),
    ('Monitor 27"', 'Electronics', 399.99, 40),
    ('Keyboard Mechanical', 'Electronics', 149.99, 75),
    ('Desk Organizer', 'Furniture', 24.99, 120);

-- Insert sample orders
INSERT INTO raw.orders (customer_id, order_date, status, total_amount, shipping_address) VALUES
    (1, '2024-01-15', 'delivered', 1329.98, '123 Main St, Springfield'),
    (2, '2024-01-16', 'delivered', 449.98, '456 Oak Ave, Riverside'),
    (3, '2024-01-17', 'shipped', 299.99, '789 Pine Rd, Hillside'),
    (4, '2024-01-18', 'processing', 1699.97, '321 Elm St, Lakewood'),
    (5, '2024-01-19', 'delivered', 21.98, '654 Maple Dr, Parkville'),
    (1, '2024-01-20', 'delivered', 149.99, '123 Main St, Springfield'),
    (6, '2024-01-21', 'shipped', 699.97, '987 Cedar Ln, Meadow'),
    (7, '2024-01-22', 'delivered', 29.99, '147 Birch Way, Woodland'),
    (2, '2024-01-23', 'processing', 324.98, '456 Oak Ave, Riverside'),
    (8, '2024-01-24', 'delivered', 1329.98, '258 Spruce Ct, Valley');

-- Insert sample order items
INSERT INTO raw.order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES
    -- Order 1
    (1, 1, 1, 1299.99, 1299.99),
    (1, 2, 1, 29.99, 29.99),
    -- Order 2
    (2, 8, 1, 399.99, 399.99),
    (2, 3, 2, 19.99, 39.98),
    (2, 4, 1, 49.99, 49.99),
    -- Order 3
    (3, 5, 1, 299.99, 299.99),
    -- Order 4
    (4, 1, 1, 1299.99, 1299.99),
    (4, 8, 1, 399.99, 399.99),
    -- Order 5
    (5, 6, 1, 12.99, 12.99),
    (5, 7, 1, 8.99, 8.99),
    -- Order 6
    (6, 9, 1, 149.99, 149.99),
    -- Order 7
    (7, 1, 1, 1299.99, 1299.99),
    (7, 9, 1, 149.99, 149.99),
    -- Order 8
    (8, 2, 1, 29.99, 29.99),
    -- Order 9
    (9, 5, 1, 299.99, 299.99),
    (9, 10, 1, 24.99, 24.99),
    -- Order 10
    (10, 1, 1, 1299.99, 1299.99),
    (10, 2, 1, 29.99, 29.99);

-- Create indexes for performance
CREATE INDEX idx_orders_customer_id ON raw.orders(customer_id);
CREATE INDEX idx_orders_order_date ON raw.orders(order_date);
CREATE INDEX idx_order_items_order_id ON raw.order_items(order_id);
CREATE INDEX idx_order_items_product_id ON raw.order_items(product_id);

-- Create a simple analytics view (this will be discovered as a transformation)
CREATE OR REPLACE VIEW raw.customer_order_summary AS
SELECT
    c.customer_id,
    c.email,
    c.first_name,
    c.last_name,
    COUNT(o.order_id) as total_orders,
    SUM(o.total_amount) as total_spent,
    MAX(o.order_date) as last_order_date
FROM raw.customers c
LEFT JOIN raw.orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.email, c.first_name, c.last_name;

COMMENT ON VIEW raw.customer_order_summary IS 'Aggregated customer order statistics';
