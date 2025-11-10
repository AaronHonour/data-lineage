-- Staging model for customers
-- Cleans and standardizes customer data from raw source

SELECT
    customer_id,
    email,
    LOWER(TRIM(email)) as email_normalized,
    first_name,
    last_name,
    CONCAT(first_name, ' ', last_name) as full_name,
    phone,
    created_at,
    updated_at
FROM {{ source('raw', 'customers') }}
WHERE email IS NOT NULL
