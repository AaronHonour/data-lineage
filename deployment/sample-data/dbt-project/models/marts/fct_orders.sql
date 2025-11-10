-- Orders fact table
-- Denormalized order data with customer and product information

WITH order_items_agg AS (
    SELECT
        order_id,
        COUNT(DISTINCT product_id) as unique_products,
        SUM(quantity) as total_items,
        SUM(subtotal) as calculated_total
    FROM {{ source('raw', 'order_items') }}
    GROUP BY order_id
)

SELECT
    o.order_id,
    o.customer_id,
    c.email,
    c.full_name as customer_name,
    c.customer_tier,
    o.order_date,
    o.order_year,
    o.order_month,
    o.order_day,
    o.order_month_start,
    o.status as order_status,
    o.total_amount,
    oi.unique_products,
    oi.total_items,
    oi.calculated_total,
    o.shipping_address,
    o.created_at as order_created_at,
    CURRENT_TIMESTAMP as updated_at
FROM {{ ref('stg_orders') }} o
LEFT JOIN {{ ref('dim_customers') }} c ON o.customer_id = c.customer_id
LEFT JOIN order_items_agg oi ON o.order_id = oi.order_id
