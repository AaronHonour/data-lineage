-- Sample auxiliary database (MySQL) for lineage testing
-- This represents data from auxiliary systems (inventory, shipping)

-- Create databases
CREATE DATABASE IF NOT EXISTS auxiliary;
USE auxiliary;

-- Inventory table
CREATE TABLE inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    warehouse_location VARCHAR(100) NOT NULL,
    quantity_available INT NOT NULL DEFAULT 0,
    quantity_reserved INT NOT NULL DEFAULT 0,
    reorder_point INT NOT NULL DEFAULT 10,
    last_restocked_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_product_id (product_id),
    INDEX idx_warehouse (warehouse_location)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Shipping/Deliveries table
CREATE TABLE deliveries (
    delivery_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    tracking_number VARCHAR(100) NOT NULL UNIQUE,
    carrier VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    shipped_at TIMESTAMP NULL,
    delivered_at TIMESTAMP NULL,
    estimated_delivery_date DATE NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_order_id (order_id),
    INDEX idx_tracking (tracking_number),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Warehouse locations table
CREATE TABLE warehouses (
    warehouse_id INT AUTO_INCREMENT PRIMARY KEY,
    warehouse_code VARCHAR(20) NOT NULL UNIQUE,
    warehouse_name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    country VARCHAR(50) NOT NULL DEFAULT 'USA',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert sample warehouses
INSERT INTO warehouses (warehouse_code, warehouse_name, city, state) VALUES
    ('WH-EAST', 'East Coast Distribution Center', 'New York', 'NY'),
    ('WH-WEST', 'West Coast Distribution Center', 'Los Angeles', 'CA'),
    ('WH-CENTRAL', 'Central Distribution Center', 'Chicago', 'IL'),
    ('WH-SOUTH', 'Southern Distribution Center', 'Dallas', 'TX');

-- Insert sample inventory (product_id corresponds to PostgreSQL products)
INSERT INTO inventory (product_id, warehouse_location, quantity_available, quantity_reserved, reorder_point, last_restocked_at) VALUES
    (1, 'WH-EAST', 25, 5, 10, '2024-01-10 10:00:00'),
    (1, 'WH-WEST', 15, 3, 10, '2024-01-12 14:30:00'),
    (1, 'WH-CENTRAL', 10, 2, 10, '2024-01-08 09:15:00'),
    (2, 'WH-EAST', 100, 10, 20, '2024-01-15 11:00:00'),
    (2, 'WH-WEST', 80, 5, 20, '2024-01-14 16:45:00'),
    (3, 'WH-EAST', 250, 20, 50, '2024-01-16 13:20:00'),
    (3, 'WH-WEST', 200, 15, 50, '2024-01-13 10:30:00'),
    (4, 'WH-CENTRAL', 60, 5, 15, '2024-01-11 15:00:00'),
    (5, 'WH-EAST', 15, 3, 5, '2024-01-09 12:00:00'),
    (5, 'WH-CENTRAL', 10, 2, 5, '2024-01-10 14:00:00'),
    (6, 'WH-EAST', 80, 8, 25, '2024-01-17 09:00:00'),
    (7, 'WH-EAST', 150, 10, 40, '2024-01-18 10:00:00'),
    (8, 'WH-WEST', 20, 4, 8, '2024-01-12 11:30:00'),
    (8, 'WH-CENTRAL', 15, 3, 8, '2024-01-14 13:45:00'),
    (9, 'WH-EAST', 40, 6, 12, '2024-01-15 15:20:00'),
    (10, 'WH-CENTRAL', 70, 7, 20, '2024-01-16 16:00:00');

-- Insert sample deliveries (order_id corresponds to PostgreSQL orders)
INSERT INTO deliveries (order_id, tracking_number, carrier, status, shipped_at, delivered_at, estimated_delivery_date) VALUES
    (1, 'TRK1001234567', 'FedEx', 'delivered', '2024-01-16 10:00:00', '2024-01-18 14:30:00', '2024-01-18'),
    (2, 'TRK1001234568', 'UPS', 'delivered', '2024-01-17 09:30:00', '2024-01-19 11:15:00', '2024-01-19'),
    (3, 'TRK1001234569', 'FedEx', 'in_transit', '2024-01-18 11:00:00', NULL, '2024-01-22'),
    (5, 'TRK1001234570', 'USPS', 'delivered', '2024-01-20 08:45:00', '2024-01-22 15:00:00', '2024-01-22'),
    (6, 'TRK1001234571', 'UPS', 'delivered', '2024-01-21 10:15:00', '2024-01-23 13:30:00', '2024-01-23'),
    (7, 'TRK1001234572', 'FedEx', 'in_transit', '2024-01-22 09:00:00', NULL, '2024-01-25'),
    (8, 'TRK1001234573', 'USPS', 'delivered', '2024-01-23 14:20:00', '2024-01-25 10:45:00', '2024-01-25');

-- Create a view for low stock alerts
CREATE OR REPLACE VIEW low_stock_alerts AS
SELECT
    i.inventory_id,
    i.product_id,
    i.warehouse_location,
    w.warehouse_name,
    i.quantity_available,
    i.reorder_point,
    (i.reorder_point - i.quantity_available) AS units_below_threshold
FROM inventory i
JOIN warehouses w ON i.warehouse_location = w.warehouse_code
WHERE i.quantity_available <= i.reorder_point
ORDER BY units_below_threshold DESC;

-- Create a view for delivery performance
CREATE OR REPLACE VIEW delivery_performance AS
SELECT
    d.delivery_id,
    d.order_id,
    d.carrier,
    d.status,
    d.shipped_at,
    d.delivered_at,
    d.estimated_delivery_date,
    CASE
        WHEN d.delivered_at IS NOT NULL THEN
            DATEDIFF(DATE(d.delivered_at), d.estimated_delivery_date)
        ELSE NULL
    END AS days_difference,
    CASE
        WHEN d.delivered_at IS NOT NULL AND DATE(d.delivered_at) <= d.estimated_delivery_date THEN 'on_time'
        WHEN d.delivered_at IS NOT NULL AND DATE(d.delivered_at) > d.estimated_delivery_date THEN 'late'
        ELSE 'pending'
    END AS delivery_status
FROM deliveries d;
