-- Staging model for customers
-- ref: https://docs.getdbt.com/docs/building-a-dbt-project/building-models

{{
  config(
    materialized='view'
  )
}}

SELECT
    customer_id,
    first_name,
    last_name,
    first_name || ' ' || last_name AS full_name,
    email,
    phone,
    created_at
FROM {{ source('raw', 'customers') }}
WHERE customer_id IS NOT NULL
