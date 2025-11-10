-- Staging model for orders

{{
  config(
    materialized='view'
  )
}}

SELECT
    order_id,
    customer_id,
    order_date,
    total_amount,
    status,
    created_at
FROM {{ source('raw', 'orders') }}
WHERE order_id IS NOT NULL
