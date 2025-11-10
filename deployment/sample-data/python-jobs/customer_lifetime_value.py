"""
Customer Lifetime Value Analysis
Uses pandas to read from dbt marts and create aggregated analytics
Writes output to Delta Lake
"""

import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
import os

# Database connection (will read from dbt marts schema)
DB_URL = "postgresql://source_user:source_pass@postgres-source:5432/ecommerce"

# Delta Lake output path
DELTA_PATH = "/delta-lake/customer_ltv"

def calculate_customer_ltv():
    """
    Calculate customer lifetime value with advanced metrics.

    Lineage:
    - Reads from: ecommerce.marts.dim_customers
    - Writes to: delta://customer_ltv
    """
    print("Starting Customer LTV analysis...")

    # Connect to database
    engine = create_engine(DB_URL)

    # Read customer dimension data
    query = """
        SELECT
            customer_id,
            email,
            full_name,
            lifetime_orders,
            lifetime_value,
            avg_order_value,
            first_order_date,
            last_order_date,
            customer_tenure_days,
            customer_tier
        FROM marts.dim_customers
        WHERE lifetime_orders > 0
    """

    df = pd.read_sql(query, engine)

    print(f"Loaded {len(df)} customers with orders")

    # Calculate advanced LTV metrics
    df['avg_days_between_orders'] = df['customer_tenure_days'] / df['lifetime_orders']
    df['projected_annual_orders'] = 365 / df['avg_days_between_orders'].clip(lower=1)
    df['projected_annual_value'] = df['projected_annual_orders'] * df['avg_order_value']

    # Calculate 3-year LTV projection
    df['ltv_3year_projection'] = df['projected_annual_value'] * 3

    # Categorize customers by behavior
    df['customer_segment'] = pd.cut(
        df['lifetime_orders'],
        bins=[0, 1, 3, 5, float('inf')],
        labels=['one_time', 'occasional', 'regular', 'loyal']
    )

    # Value segment
    df['value_segment'] = pd.cut(
        df['lifetime_value'],
        bins=[0, 200, 500, 1000, float('inf')],
        labels=['low', 'medium', 'high', 'vip']
    )

    # Add metadata
    df['analysis_date'] = datetime.now()
    df['analysis_version'] = 'v1.0'

    # Create output directory if it doesn't exist
    os.makedirs(DELTA_PATH, exist_ok=True)

    # Write to Parquet (simulating Delta Lake for demo)
    output_file = f"{DELTA_PATH}/part-{datetime.now().strftime('%Y%m%d-%H%M%S')}.parquet"
    df.to_parquet(output_file, index=False, engine='pyarrow')

    print(f"✓ Analysis complete: {len(df)} customers analyzed")
    print(f"✓ Output written to: {output_file}")

    # Print summary statistics
    print("\nSummary Statistics:")
    print(f"  Total LTV: ${df['lifetime_value'].sum():,.2f}")
    print(f"  Average LTV: ${df['lifetime_value'].mean():,.2f}")
    print(f"  Median LTV: ${df['lifetime_value'].median():,.2f}")
    print(f"  3-Year Projected LTV: ${df['ltv_3year_projection'].sum():,.2f}")
    print("\nCustomer Segments:")
    print(df['customer_segment'].value_counts())
    print("\nValue Segments:")
    print(df['value_segment'].value_counts())

    engine.dispose()

    return df

if __name__ == "__main__":
    calculate_customer_ltv()
