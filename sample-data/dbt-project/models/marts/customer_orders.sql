-- Mart model combining customers and orders

{{
  config(
    materialized='table'
  )
}}

WITH customers AS (
    SELECT * FROM {{ ref('stg_customers') }}
),

orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
),

customer_orders AS (
    SELECT
        c.customer_id,
        c.full_name,
        c.email,
        o.order_id,
        o.order_date,
        o.total_amount,
        o.status
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
)

SELECT * FROM customer_orders
