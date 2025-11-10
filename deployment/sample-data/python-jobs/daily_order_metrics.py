"""
Daily Order Metrics Aggregation
Uses polars for high-performance data processing
Reads from dbt fact table and creates daily aggregates
Writes output to Delta Lake
"""

import polars as pl
from datetime import datetime
import os

# Database connection string
DB_URL = "postgresql://source_user:source_pass@postgres-source:5432/ecommerce"

# Delta Lake output path
DELTA_PATH = "/delta-lake/daily_order_metrics"

def calculate_daily_metrics():
    """
    Calculate daily order metrics using polars.

    Lineage:
    - Reads from: ecommerce.marts.fct_orders
    - Writes to: delta://daily_order_metrics
    """
    print("Starting Daily Order Metrics aggregation...")

    # Read from database using polars
    query = """
        SELECT
            order_id,
            customer_id,
            order_date,
            order_status,
            total_amount,
            unique_products,
            total_items,
            customer_tier
        FROM marts.fct_orders
    """

    df = pl.read_database(query, DB_URL)

    print(f"Loaded {len(df)} orders")

    # Aggregate by date
    daily_metrics = df.group_by('order_date').agg([
        pl.count('order_id').alias('total_orders'),
        pl.n_unique('customer_id').alias('unique_customers'),
        pl.sum('total_amount').alias('total_revenue'),
        pl.mean('total_amount').alias('avg_order_value'),
        pl.median('total_amount').alias('median_order_value'),
        pl.sum('total_items').alias('total_items_sold'),
        pl.mean('total_items').alias('avg_items_per_order'),
        pl.sum('unique_products').alias('total_unique_products'),
    ]).sort('order_date')

    # Calculate rolling metrics (7-day windows)
    daily_metrics = daily_metrics.with_columns([
        pl.col('total_revenue').rolling_sum(window_size=7).alias('revenue_7day_rolling'),
        pl.col('total_orders').rolling_mean(window_size=7).alias('orders_7day_avg'),
        pl.col('avg_order_value').rolling_mean(window_size=7).alias('aov_7day_avg'),
    ])

    # Calculate day-over-day changes
    daily_metrics = daily_metrics.with_columns([
        (pl.col('total_revenue') - pl.col('total_revenue').shift(1)).alias('revenue_dod_change'),
        ((pl.col('total_revenue') / pl.col('total_revenue').shift(1) - 1) * 100).alias('revenue_dod_pct'),
    ])

    # Add derived metrics
    daily_metrics = daily_metrics.with_columns([
        (pl.col('total_revenue') / pl.col('unique_customers')).alias('revenue_per_customer'),
        pl.col('order_date').dt.weekday().alias('day_of_week'),
        pl.col('order_date').dt.month().alias('month'),
    ])

    # Aggregate by customer tier and date
    tier_metrics = df.group_by(['order_date', 'customer_tier']).agg([
        pl.count('order_id').alias('orders'),
        pl.sum('total_amount').alias('revenue'),
    ]).sort(['order_date', 'customer_tier'])

    # Pivot tier metrics for easier analysis
    tier_pivot = tier_metrics.pivot(
        index='order_date',
        columns='customer_tier',
        values='revenue',
    )

    # Join tier data back to daily metrics
    final_metrics = daily_metrics.join(
        tier_pivot,
        on='order_date',
        how='left'
    )

    # Add metadata
    final_metrics = final_metrics.with_columns([
        pl.lit(datetime.now()).alias('analysis_timestamp'),
        pl.lit('v1.0').alias('analysis_version'),
    ])

    # Create output directory
    os.makedirs(DELTA_PATH, exist_ok=True)

    # Write to Parquet (simulating Delta Lake)
    output_file = f"{DELTA_PATH}/part-{datetime.now().strftime('%Y%m%d-%H%M%S')}.parquet"
    final_metrics.write_parquet(output_file)

    print(f"✓ Analysis complete: {len(final_metrics)} days analyzed")
    print(f"✓ Output written to: {output_file}")

    # Print summary
    print("\nOverall Metrics:")
    print(f"  Total Orders: {daily_metrics['total_orders'].sum():,}")
    print(f"  Total Revenue: ${daily_metrics['total_revenue'].sum():,.2f}")
    print(f"  Average Daily Revenue: ${daily_metrics['total_revenue'].mean():,.2f}")
    print(f"  Peak Daily Revenue: ${daily_metrics['total_revenue'].max():,.2f}")
    print(f"  Average Order Value: ${daily_metrics['avg_order_value'].mean():,.2f}")

    return final_metrics

if __name__ == "__main__":
    calculate_daily_metrics()
