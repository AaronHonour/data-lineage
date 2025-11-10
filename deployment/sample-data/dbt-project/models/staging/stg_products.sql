-- Staging model for products
-- Standardizes product data

SELECT
    product_id,
    product_name,
    LOWER(category) as category,
    price,
    stock_quantity,
    created_at,
    CASE
        WHEN price < 50 THEN 'low'
        WHEN price < 200 THEN 'medium'
        ELSE 'high'
    END as price_tier
FROM {{ source('raw', 'products') }}
WHERE price > 0
