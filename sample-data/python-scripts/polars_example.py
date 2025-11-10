"""Example polars data transformation script."""
import polars as pl

# Read source data
customers = pl.read_csv('customers.csv')
orders = pl.read_csv('orders.csv')

# Select specific columns
customer_subset = customers.select(['customer_id', 'name', 'email'])

# Create new calculated column
orders_with_tax = orders.with_columns(
    (pl.col('total_amount') * 1.1).alias('total_with_tax')
)

# Join dataframes
enriched_orders = orders_with_tax.join(
    customer_subset,
    on='customer_id',
    how='left'
)

# Aggregation
customer_summary = enriched_orders.groupby('customer_id').agg([
    pl.count('order_id').alias('order_count'),
    pl.sum('total_amount').alias('total_spent'),
    pl.sum('total_with_tax').alias('total_with_tax')
])

# Write output
customer_summary.write_csv('customer_summary.csv')
