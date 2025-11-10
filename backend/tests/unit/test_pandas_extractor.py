"""Unit tests for pandas lineage extractor."""
import pytest
from app.infrastructure.parsers.pandas_extractor import PandasLineageExtractor


class TestPandasLineageExtractor:
    """Test pandas lineage extraction."""

    def test_simple_read_operation(self):
        """Test extraction of simple read operation."""
        code = """
import pandas as pd

df = pd.read_csv('customers.csv')
"""
        extractor = PandasLineageExtractor()
        lineage = extractor.extract_lineage(code, "output")

        # Should extract read operation
        assert len(extractor.operations) == 1
        assert extractor.operations[0].operation_type == 'read'
        assert extractor.operations[0].target_var == 'df'

    def test_column_selection(self):
        """Test extraction of column selection."""
        code = """
import pandas as pd

df = pd.read_csv('customers.csv')
subset = df[['customer_id', 'name', 'email']]
"""
        extractor = PandasLineageExtractor()
        lineage = extractor.extract_lineage(code, "output")

        # Should have read and select operations
        assert len(extractor.operations) == 2

        select_op = extractor.operations[1]
        assert select_op.operation_type == 'select'
        assert 'customer_id' in select_op.columns
        assert 'name' in select_op.columns
        assert 'email' in select_op.columns

    def test_column_assignment(self):
        """Test extraction of column assignment."""
        code = """
import pandas as pd

df = pd.read_csv('orders.csv')
df['total_with_tax'] = df['total_amount'] * 1.1
"""
        extractor = PandasLineageExtractor()
        lineage = extractor.extract_lineage(code, "output")

        # Should have read and assign operations
        assert len(extractor.operations) == 2

        assign_op = extractor.operations[1]
        assert assign_op.operation_type == 'assign'
        assert 'total_with_tax' in assign_op.columns

    def test_merge_operation(self):
        """Test extraction of merge operation."""
        code = """
import pandas as pd

customers = pd.read_csv('customers.csv')
orders = pd.read_csv('orders.csv')
enriched = orders.merge(customers, on='customer_id', how='left')
"""
        extractor = PandasLineageExtractor()
        lineage = extractor.extract_lineage(code, "output")

        # Should have 2 reads and 1 merge
        assert len(extractor.operations) == 3

        merge_op = extractor.operations[2]
        assert merge_op.operation_type == 'join'
        assert 'orders' in merge_op.source_vars
        assert 'customers' in merge_op.source_vars

    def test_write_operation(self):
        """Test extraction of write operation."""
        code = """
import pandas as pd

df = pd.read_csv('data.csv')
df.to_csv('output.csv', index=False)
"""
        extractor = PandasLineageExtractor()
        lineage = extractor.extract_lineage(code, "output")

        # Should have read and write operations
        assert len(extractor.operations) == 2

        write_op = extractor.operations[1]
        assert write_op.operation_type == 'write'
        assert 'df' in write_op.source_vars

    def test_full_pipeline(self):
        """Test extraction from full pandas pipeline."""
        code = """
import pandas as pd

# Read
customers = pd.read_csv('customers.csv')
orders = pd.read_csv('orders.csv')

# Transform
customer_subset = customers[['customer_id', 'name', 'email']]
orders['total_with_tax'] = orders['total_amount'] * 1.1

# Join
enriched = orders.merge(customer_subset, on='customer_id', how='left')

# Write
enriched.to_csv('enriched_orders.csv', index=False)
"""
        extractor = PandasLineageExtractor()
        lineage = extractor.extract_lineage(code, "enriched_orders")

        # Should extract all operations
        assert len(extractor.operations) >= 6

        # Verify operation types
        op_types = [op.operation_type for op in extractor.operations]
        assert 'read' in op_types
        assert 'select' in op_types
        assert 'assign' in op_types
        assert 'join' in op_types
        assert 'write' in op_types
