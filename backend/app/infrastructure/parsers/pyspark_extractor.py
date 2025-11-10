"""PySpark-specific lineage extraction from Python code."""
import ast
import re
from typing import Optional
from .python_parser import (
    DataFrameOperation,
    ColumnLineageResult,
    PythonLineageExtractor,
    DataFrameLibrary
)


class PySparkLineageExtractor(PythonLineageExtractor):
    """
    Extract column-level lineage from PySpark Python code.

    Supports common PySpark operations:
    - spark.read.csv, read.parquet, read.table
    - select, filter, where, withColumn, withColumnRenamed
    - join operations
    - groupBy/agg operations
    - write.csv, write.parquet, write.mode().save()
    """

    def __init__(self):
        """Initialize PySpark lineage extractor."""
        super().__init__(library=DataFrameLibrary.PYSPARK)

    def extract_lineage_from_file(self, file_path: str) -> list[ColumnLineageResult]:
        """
        Extract lineage from a PySpark Python file.

        Args:
            file_path: Path to Python file

        Returns:
            List of column lineage results
        """
        with open(file_path, 'r') as f:
            code = f.read()

        # Extract filename as target
        target = file_path.split('/')[-1].replace('.py', '_output')
        return self.extract_lineage(code, target)

    def _analyze_ast(self, tree: ast.AST) -> None:
        """Analyze AST for PySpark operations."""
        visitor = PySparkVisitor()
        visitor.visit(tree)
        self.operations = visitor.operations
        self.dataframe_vars = visitor.dataframe_vars


class PySparkVisitor(ast.NodeVisitor):
    """AST visitor specialized for PySpark DataFrame operations."""

    def __init__(self):
        """Initialize PySpark visitor."""
        self.operations: list[DataFrameOperation] = []
        self.dataframe_vars: dict[str, set[str]] = {}
        self.import_aliases: dict[str, str] = {}
        self.spark_session_var: Optional[str] = None

    def visit_Import(self, node: ast.Import) -> None:
        """Track import statements."""
        for alias in node.names:
            if 'pyspark' in alias.name:
                self.import_aliases[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from-import statements."""
        if node.module and 'pyspark' in node.module:
            for alias in node.names:
                self.import_aliases[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statements."""
        if not node.targets or not isinstance(node.targets[0], ast.Name):
            self.generic_visit(node)
            return

        target_var = node.targets[0].id

        # Track SparkSession creation
        if isinstance(node.value, ast.Call) and self._is_spark_session_builder(node.value):
            self.spark_session_var = target_var
            self.generic_visit(node)
            return

        if isinstance(node.value, ast.Call):
            self._analyze_pyspark_call(node.value, target_var, node.lineno)

        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Visit standalone expressions (e.g., df.write.parquet())."""
        if isinstance(node.value, ast.Call):
            self._analyze_pyspark_call(node.value, None, node.lineno)
        self.generic_visit(node)

    def _is_spark_session_builder(self, call: ast.Call) -> bool:
        """Check if call is SparkSession.builder...getOrCreate()."""
        if isinstance(call.func, ast.Attribute):
            if call.func.attr == 'getOrCreate':
                return True
        return False

    def _analyze_pyspark_call(
        self,
        call: ast.Call,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Analyze PySpark method calls."""
        func_name = self._get_method_name(call)

        if not func_name:
            return

        # Read operations
        if func_name in ['csv', 'parquet', 'json', 'orc', 'table', 'jdbc', 'load']:
            self._extract_read_op(call, func_name, target_var, lineno)

        # Select/filter operations
        elif func_name in ['select', 'filter', 'where', 'selectExpr']:
            self._extract_select_op(call, func_name, target_var, lineno)

        # Column operations
        elif func_name in ['withColumn', 'withColumnRenamed', 'drop']:
            self._extract_column_op(call, func_name, target_var, lineno)

        # Join operations
        elif func_name == 'join':
            self._extract_join_op(call, target_var, lineno)

        # GroupBy
        elif func_name in ['groupBy', 'groupby']:
            self._extract_groupby_op(call, target_var, lineno)

        # Aggregation after groupBy
        elif func_name in ['agg', 'count', 'sum', 'avg', 'max', 'min']:
            self._extract_agg_op(call, func_name, target_var, lineno)

        # Write operations
        elif func_name in ['csv', 'parquet', 'json', 'orc', 'save', 'saveAsTable'] and self._is_write_call(call):
            self._extract_write_op(call, func_name, lineno)

    def _extract_read_op(
        self,
        call: ast.Call,
        func_name: str,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract PySpark read operation."""
        if not target_var:
            return

        expression = self._node_to_code(call)

        op = DataFrameOperation(
            operation_type='read',
            target_var=target_var,
            source_vars=[],
            columns=[],
            expression=expression,
            line_number=lineno
        )
        self.operations.append(op)
        self.dataframe_vars[target_var] = set()

    def _extract_select_op(
        self,
        call: ast.Call,
        func_name: str,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract PySpark select/filter operation."""
        if not target_var:
            return

        # Get source dataframe
        source_var = self._get_dataframe_var(call.func)
        if not source_var:
            return

        # Extract columns from arguments
        columns = []
        for arg in call.args:
            # PySpark uses col('name'), F.col('name'), or just 'name'
            if isinstance(arg, ast.Call):
                col_name = self._extract_col_name(arg)
                if col_name:
                    columns.append(col_name)
            elif isinstance(arg, ast.Constant):
                columns.append(str(arg.value))
            elif isinstance(arg, ast.Str):
                columns.append(arg.s)

        op_type = 'select' if func_name in ['select', 'selectExpr'] else 'transform'

        op = DataFrameOperation(
            operation_type=op_type,
            target_var=target_var,
            source_vars=[source_var] if source_var else [],
            columns=columns,
            expression=self._node_to_code(call),
            line_number=lineno
        )
        self.operations.append(op)

        # Update dataframe columns
        if columns and func_name == 'select':
            self.dataframe_vars[target_var] = set(columns)
        elif source_var and source_var in self.dataframe_vars:
            self.dataframe_vars[target_var] = self.dataframe_vars[source_var].copy()

    def _extract_column_op(
        self,
        call: ast.Call,
        func_name: str,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract PySpark withColumn/withColumnRenamed operation."""
        if not target_var:
            return

        # Get source dataframe
        source_var = self._get_dataframe_var(call.func)
        if not source_var:
            return

        # Extract column name (first argument)
        col_name = None
        if call.args:
            arg = call.args[0]
            if isinstance(arg, ast.Constant):
                col_name = str(arg.value)
            elif isinstance(arg, ast.Str):
                col_name = arg.s

        columns = [col_name] if col_name else []

        op = DataFrameOperation(
            operation_type='transform',
            target_var=target_var,
            source_vars=[source_var],
            columns=columns,
            expression=self._node_to_code(call),
            line_number=lineno
        )
        self.operations.append(op)

        # Update dataframe columns
        if source_var in self.dataframe_vars:
            self.dataframe_vars[target_var] = self.dataframe_vars[source_var].copy()
            if col_name:
                self.dataframe_vars[target_var].add(col_name)

    def _extract_join_op(
        self,
        call: ast.Call,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract PySpark join operation."""
        if not target_var:
            return

        # Get left dataframe
        left_var = self._get_dataframe_var(call.func)

        # Get right dataframe (first argument)
        right_var = None
        if call.args:
            right_var = self._get_dataframe_var(call.args[0])

        if not left_var or not right_var:
            return

        # Combine columns from both dataframes
        left_cols = self.dataframe_vars.get(left_var, set())
        right_cols = self.dataframe_vars.get(right_var, set())
        all_cols = list(left_cols | right_cols)

        op = DataFrameOperation(
            operation_type='join',
            target_var=target_var,
            source_vars=[left_var, right_var],
            columns=all_cols,
            expression=self._node_to_code(call),
            line_number=lineno
        )
        self.operations.append(op)
        self.dataframe_vars[target_var] = set(all_cols)

    def _extract_groupby_op(
        self,
        call: ast.Call,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract PySpark groupBy operation."""
        if not target_var:
            return

        # Get source dataframe
        source_var = self._get_dataframe_var(call.func)
        if not source_var:
            return

        # Extract groupby columns
        groupby_cols = []
        for arg in call.args:
            if isinstance(arg, ast.Constant):
                groupby_cols.append(str(arg.value))
            elif isinstance(arg, ast.Str):
                groupby_cols.append(arg.s)
            elif isinstance(arg, ast.Call):
                col_name = self._extract_col_name(arg)
                if col_name:
                    groupby_cols.append(col_name)

        op = DataFrameOperation(
            operation_type='groupby',
            target_var=target_var,
            source_vars=[source_var],
            columns=groupby_cols,
            expression=self._node_to_code(call),
            line_number=lineno
        )
        self.operations.append(op)

    def _extract_agg_op(
        self,
        call: ast.Call,
        func_name: str,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract PySpark aggregation operation."""
        if not target_var:
            return

        # Get source (usually a GroupedData object)
        source_var = self._get_dataframe_var(call.func)
        if not source_var:
            return

        # Extract aggregation columns from arguments
        agg_cols = []
        for arg in call.args:
            if isinstance(arg, ast.Dict):
                # agg({'col': 'sum'}) syntax
                for key in arg.keys:
                    if isinstance(key, ast.Constant):
                        agg_cols.append(str(key.value))
                    elif isinstance(key, ast.Str):
                        agg_cols.append(key.s)

        op = DataFrameOperation(
            operation_type='aggregate',
            target_var=target_var,
            source_vars=[source_var],
            columns=agg_cols,
            expression=self._node_to_code(call),
            line_number=lineno
        )
        self.operations.append(op)

    def _extract_write_op(
        self,
        call: ast.Call,
        func_name: str,
        lineno: int
    ) -> None:
        """Extract PySpark write operation."""
        # Get source dataframe by traversing back through .write
        source_var = self._get_write_source_var(call)

        op = DataFrameOperation(
            operation_type='write',
            target_var=None,
            source_vars=[source_var] if source_var else [],
            columns=[],
            expression=self._node_to_code(call),
            line_number=lineno
        )
        self.operations.append(op)

    # Helper methods
    def _get_method_name(self, call: ast.Call) -> Optional[str]:
        """Get method name from call."""
        if isinstance(call.func, ast.Name):
            return call.func.id
        elif isinstance(call.func, ast.Attribute):
            return call.func.attr
        return None

    def _get_dataframe_var(self, node: ast.AST) -> Optional[str]:
        """Get dataframe variable name from node."""
        if isinstance(node, ast.Attribute):
            # Traverse back to find the base variable
            current = node.value
            while isinstance(current, ast.Attribute):
                current = current.value
            if isinstance(current, ast.Name):
                return current.id
        elif isinstance(node, ast.Name):
            return node.id
        return None

    def _get_write_source_var(self, call: ast.Call) -> Optional[str]:
        """Get source dataframe for write operation (df.write.parquet())."""
        # The pattern is: df.write.parquet() so we need to go back two levels
        if isinstance(call.func, ast.Attribute):
            # call.func.value is .write
            write_node = call.func.value
            if isinstance(write_node, ast.Attribute):
                # write_node.value is the dataframe
                return self._get_dataframe_var(write_node.value)
        return None

    def _is_write_call(self, call: ast.Call) -> bool:
        """Check if this is a write call (df.write.method())."""
        if isinstance(call.func, ast.Attribute):
            # Check if parent is .write
            if isinstance(call.func.value, ast.Attribute):
                if call.func.value.attr == 'write':
                    return True
        return False

    def _extract_col_name(self, call_node: ast.Call) -> Optional[str]:
        """Extract column name from col('name') or F.col('name') call."""
        if isinstance(call_node.func, ast.Attribute):
            if call_node.func.attr == 'col' and call_node.args:
                arg = call_node.args[0]
                if isinstance(arg, ast.Constant):
                    return str(arg.value)
                elif isinstance(arg, ast.Str):
                    return arg.s
        elif isinstance(call_node.func, ast.Name):
            if call_node.func.id == 'col' and call_node.args:
                arg = call_node.args[0]
                if isinstance(arg, ast.Constant):
                    return str(arg.value)
                elif isinstance(arg, ast.Str):
                    return arg.s
        return None

    def _node_to_code(self, node: ast.AST) -> str:
        """Convert AST node back to code string."""
        if hasattr(ast, 'unparse'):
            return ast.unparse(node)
        else:
            return ast.dump(node)
