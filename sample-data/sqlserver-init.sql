-- Sample SQL Server database initialization script
-- This creates a realistic data warehouse scenario for testing lineage

-- Create schemas
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'staging')
BEGIN
    EXEC('CREATE SCHEMA staging');
END;
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'analytics')
BEGIN
    EXEC('CREATE SCHEMA analytics');
END;
GO

-- Staging tables (raw data)
CREATE TABLE staging.customers (
    customer_id INT PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    created_at DATETIME DEFAULT GETDATE()
);

CREATE TABLE staging.orders (
    order_id INT PRIMARY KEY,
    customer_id INT FOREIGN KEY REFERENCES staging.customers(customer_id),
    order_date DATETIME,
    total_amount DECIMAL(10, 2),
    status VARCHAR(50),
    created_at DATETIME DEFAULT GETDATE()
);

CREATE TABLE staging.order_items (
    order_item_id INT PRIMARY KEY,
    order_id INT FOREIGN KEY REFERENCES staging.orders(order_id),
    product_id INT,
    product_name VARCHAR(255),
    quantity INT,
    unit_price DECIMAL(10, 2),
    created_at DATETIME DEFAULT GETDATE()
);
GO

-- Insert sample data
INSERT INTO staging.customers (customer_id, first_name, last_name, email, phone) VALUES
(1, 'John', 'Doe', 'john.doe@example.com', '555-0101'),
(2, 'Jane', 'Smith', 'jane.smith@example.com', '555-0102'),
(3, 'Bob', 'Johnson', 'bob.johnson@example.com', '555-0103'),
(4, 'Alice', 'Williams', 'alice.williams@example.com', '555-0104'),
(5, 'Charlie', 'Brown', 'charlie.brown@example.com', '555-0105');

INSERT INTO staging.orders (order_id, customer_id, order_date, total_amount, status) VALUES
(101, 1, '2024-01-15 10:30:00', 150.00, 'completed'),
(102, 2, '2024-01-16 14:20:00', 75.50, 'completed'),
(103, 1, '2024-01-17 09:15:00', 220.00, 'completed'),
(104, 3, '2024-01-18 16:45:00', 95.25, 'pending'),
(105, 4, '2024-01-19 11:00:00', 310.00, 'completed');

INSERT INTO staging.order_items (order_item_id, order_id, product_id, product_name, quantity, unit_price) VALUES
(1, 101, 1001, 'Widget A', 2, 25.00),
(2, 101, 1002, 'Gadget B', 1, 100.00),
(3, 102, 1001, 'Widget A', 3, 25.00),
(4, 103, 1003, 'Tool C', 1, 150.00),
(5, 103, 1002, 'Gadget B', 1, 70.00),
(6, 104, 1001, 'Widget A', 1, 25.00),
(7, 104, 1004, 'Device D', 2, 35.00),
(8, 105, 1003, 'Tool C', 2, 155.00);
GO

-- Create indexes for better performance
CREATE INDEX idx_orders_customer ON staging.orders(customer_id);
CREATE INDEX idx_orders_date ON staging.orders(order_date);
CREATE INDEX idx_order_items_order ON staging.order_items(order_id);
CREATE INDEX idx_order_items_product ON staging.order_items(product_id);
GO

-- Analytics views (transformations that will show lineage)

-- View 1: Customer full names
CREATE VIEW analytics.customer_profiles AS
SELECT
    customer_id,
    first_name + ' ' + last_name AS full_name,
    email,
    phone,
    created_at
FROM staging.customers;
GO

-- View 2: Order summaries with customer info
CREATE VIEW analytics.order_summary AS
SELECT
    o.order_id,
    o.customer_id,
    c.first_name + ' ' + c.last_name AS customer_name,
    o.order_date,
    o.total_amount,
    o.status
FROM staging.orders o
JOIN staging.customers c ON o.customer_id = c.customer_id;
GO

-- View 3: Customer lifetime value
CREATE VIEW analytics.customer_lifetime_value AS
SELECT
    c.customer_id,
    c.first_name + ' ' + c.last_name AS customer_name,
    c.email,
    COUNT(o.order_id) AS total_orders,
    SUM(o.total_amount) AS total_spent,
    AVG(o.total_amount) AS avg_order_value,
    MAX(o.order_date) AS last_order_date
FROM staging.customers c
LEFT JOIN staging.orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name, c.email;
GO

-- View 4: Product performance
CREATE VIEW analytics.product_performance AS
SELECT
    oi.product_id,
    oi.product_name,
    COUNT(DISTINCT oi.order_id) AS times_ordered,
    SUM(oi.quantity) AS total_quantity_sold,
    SUM(oi.quantity * oi.unit_price) AS total_revenue,
    AVG(oi.unit_price) AS avg_unit_price
FROM staging.order_items oi
JOIN staging.orders o ON oi.order_id = o.order_id
WHERE o.status = 'completed'
GROUP BY oi.product_id, oi.product_name;
GO

-- View 5: Complex multi-level transformation
CREATE VIEW analytics.customer_product_affinity AS
SELECT
    c.customer_id,
    c.first_name + ' ' + c.last_name AS customer_name,
    oi.product_name,
    COUNT(*) AS purchase_count,
    SUM(oi.quantity) AS total_quantity,
    SUM(oi.quantity * oi.unit_price) AS total_spent_on_product
FROM staging.customers c
JOIN staging.orders o ON c.customer_id = o.customer_id
JOIN staging.order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.first_name, c.last_name, oi.product_name;
GO

-- View 6: Daily sales summary
CREATE VIEW analytics.daily_sales_summary AS
SELECT
    CAST(o.order_date AS DATE) AS sale_date,
    COUNT(DISTINCT o.order_id) AS total_orders,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    SUM(o.total_amount) AS total_revenue,
    AVG(o.total_amount) AS avg_order_value
FROM staging.orders o
WHERE o.status = 'completed'
GROUP BY CAST(o.order_date AS DATE);
GO
