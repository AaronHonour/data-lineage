-- Customer dimension with aggregated metrics
-- Combines customer data with order statistics

WITH customer_orders AS (
    SELECT
        customer_id,
        COUNT(*) as lifetime_orders,
        SUM(total_amount) as lifetime_value,
        AVG(total_amount) as avg_order_value,
        MIN(order_date) as first_order_date,
        MAX(order_date) as last_order_date,
        MAX(order_date) - MIN(order_date) as customer_tenure_days
    FROM {{ ref('stg_orders') }}
    GROUP BY customer_id
)

SELECT
    c.customer_id,
    c.email,
    c.email_normalized,
    c.first_name,
    c.last_name,
    c.full_name,
    c.phone,
    c.created_at as customer_created_at,
    co.lifetime_orders,
    COALESCE(co.lifetime_value, 0) as lifetime_value,
    COALESCE(co.avg_order_value, 0) as avg_order_value,
    co.first_order_date,
    co.last_order_date,
    co.customer_tenure_days,
    CASE
        WHEN co.lifetime_value IS NULL THEN 'no_orders'
        WHEN co.lifetime_value < 100 THEN 'bronze'
        WHEN co.lifetime_value < 500 THEN 'silver'
        WHEN co.lifetime_value < 1000 THEN 'gold'
        ELSE 'platinum'
    END as customer_tier,
    CURRENT_TIMESTAMP as updated_at
FROM {{ ref('stg_customers') }} c
LEFT JOIN customer_orders co ON c.customer_id = co.customer_id
