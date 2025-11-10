"""Example PySpark data transformation script."""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Initialize Spark session
spark = SparkSession.builder.appName("DataLineage").getOrCreate()

# Read source data
customers = spark.read.csv('customers.csv', header=True, inferSchema=True)
orders = spark.read.csv('orders.csv', header=True, inferSchema=True)

# Select specific columns
customer_subset = customers.select('customer_id', 'name', 'email')

# Create new calculated column
orders_with_tax = orders.withColumn('total_with_tax', F.col('total_amount') * 1.1)

# Join dataframes
enriched_orders = orders_with_tax.join(
    customer_subset,
    on='customer_id',
    how='left'
)

# Aggregation
customer_summary = enriched_orders.groupBy('customer_id').agg(
    F.count('order_id').alias('order_count'),
    F.sum('total_amount').alias('total_spent'),
    F.sum('total_with_tax').alias('total_with_tax')
)

# Write output
customer_summary.write.csv('customer_summary.csv', header=True, mode='overwrite')
