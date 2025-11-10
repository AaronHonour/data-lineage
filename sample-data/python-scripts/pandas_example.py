"""Example pandas data transformation script."""
import pandas as pd

# Read source data
customers = pd.read_csv('customers.csv')
orders = pd.read_csv('orders.csv')

# Select specific columns
customer_subset = customers[['customer_id', 'name', 'email']]

# Create new calculated column
orders['total_with_tax'] = orders['total_amount'] * 1.1

# Merge dataframes
enriched_orders = orders.merge(
    customer_subset,
    on='customer_id',
    how='left'
)

# Aggregation
customer_summary = enriched_orders.groupby('customer_id').agg({
    'order_id': 'count',
    'total_amount': 'sum',
    'total_with_tax': 'sum'
}).reset_index()

# Rename columns
customer_summary.columns = [
    'customer_id',
    'order_count',
    'total_spent',
    'total_with_tax'
]

# Write output
customer_summary.to_csv('customer_summary.csv', index=False)
