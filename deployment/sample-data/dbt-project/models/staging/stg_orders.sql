-- Staging model for orders
-- Cleans and enriches order data

SELECT
    order_id,
    customer_id,
    order_date,
    status,
    total_amount,
    shipping_address,
    created_at,
    EXTRACT(YEAR FROM order_date) as order_year,
    EXTRACT(MONTH FROM order_date) as order_month,
    EXTRACT(DAY FROM order_date) as order_day,
    DATE_TRUNC('month', order_date) as order_month_start
FROM {{ source('raw', 'orders') }}
WHERE total_amount > 0
