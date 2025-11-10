"""Python code parser for lineage extraction from pandas, polars, and pyspark."""
import ast
from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum


class DataFrameLibrary(str, Enum):
    """Supported DataFrame libraries."""
    PANDAS = "pandas"
    POLARS = "polars"
    PYSPARK = "pyspark"


@dataclass
class ColumnLineageResult:
    """Result of column lineage extraction from Python code."""
    target_column: str
    source_columns: list[str]
    expression: str
    transformation_type: str  # 'projection', 'transformation', 'aggregation', 'join'


@dataclass
class DataFrameOperation:
    """Represents a DataFrame operation in Python code."""
    operation_type: str  # 'read', 'select', 'filter', 'groupby', 'join', 'withColumn', etc.
    target_var: str  # Variable name
    source_vars: list[str]  # Source DataFrame variables
    columns: list[str]  # Columns involved
    expression: Optional[str] = None
    line_number: int = 0


class PythonLineageExtractor:
    """Extract column-level lineage from Python code (pandas, polars, pyspark)."""

    def __init__(self, library: DataFrameLibrary = DataFrameLibrary.PANDAS):
        """
        Initialize Python lineage extractor.

        Args:
            library: DataFrame library to analyze (pandas, polars, pyspark)
        """
        self.library = library
        self.operations: list[DataFrameOperation] = []
        self.dataframe_vars: dict[str, set[str]] = {}  # var_name -> columns

    def extract_lineage(
        self,
        code: str,
        target_table_fqn: str,
        schema: Optional[dict[str, dict[str, str]]] = None
    ) -> list[ColumnLineageResult]:
        """
        Extract column lineage from Python code.

        Args:
            code: Python code string
            target_table_fqn: Fully qualified name of target (e.g., output file/table)
            schema: Optional schema dictionary

        Returns:
            List of column lineage results
        """
        try:
            # Parse Python code into AST
            tree = ast.parse(code)

            # Extract DataFrame operations
            self._analyze_ast(tree)

            # Build lineage from operations
            lineage = self._build_lineage(target_table_fqn, schema)

            return lineage

        except SyntaxError as e:
            raise PythonParseError(f"Failed to parse Python code: {e}") from e
        except Exception as e:
            raise LineageExtractionError(f"Failed to extract lineage: {e}") from e

    def _analyze_ast(self, tree: ast.AST) -> None:
        """
        Analyze AST to extract DataFrame operations.

        Args:
            tree: Python AST tree
        """
        visitor = DataFrameVisitor(self.library)
        visitor.visit(tree)
        self.operations = visitor.operations
        self.dataframe_vars = visitor.dataframe_vars

    def _build_lineage(
        self,
        target_table_fqn: str,
        schema: Optional[dict[str, dict[str, str]]]
    ) -> list[ColumnLineageResult]:
        """
        Build column lineage from extracted operations.

        Args:
            target_table_fqn: Target table FQN
            schema: Schema dictionary

        Returns:
            List of column lineage results
        """
        lineage = []

        # Find final DataFrame variable (last write operation or specified target)
        final_df_var = self._find_final_dataframe()

        if not final_df_var or final_df_var not in self.dataframe_vars:
            return lineage

        # Build lineage for each column in final DataFrame
        final_columns = self.dataframe_vars[final_df_var]

        for col in final_columns:
            sources = self._trace_column_sources(final_df_var, col)

            lineage.append(ColumnLineageResult(
                target_column=f"{target_table_fqn}.{col}",
                source_columns=sorted(list(sources)),
                expression=col,
                transformation_type=self._infer_transformation_type(final_df_var, col)
            ))

        return lineage

    def _find_final_dataframe(self) -> Optional[str]:
        """Find the final DataFrame variable (last one written)."""
        if not self.operations:
            return None

        # Look for write operations first
        for op in reversed(self.operations):
            if op.operation_type in ['write', 'to_csv', 'to_parquet', 'save']:
                if op.source_vars:
                    return op.source_vars[0]

        # Otherwise return the last DataFrame variable
        for op in reversed(self.operations):
            if op.target_var and op.target_var in self.dataframe_vars:
                return op.target_var

        return None

    def _trace_column_sources(self, df_var: str, column: str) -> set[str]:
        """
        Trace sources of a column in a DataFrame variable.

        Args:
            df_var: DataFrame variable name
            column: Column name

        Returns:
            Set of source column FQNs
        """
        sources = set()

        # Find operations that created or modified this DataFrame
        for op in self.operations:
            if op.target_var == df_var:
                if op.operation_type == 'read':
                    # Direct read from source
                    if column in op.columns or not op.columns:
                        # Extract table name from read operation
                        source_table = self._extract_source_table(op)
                        sources.add(f"{source_table}.{column}")

                elif op.operation_type in ['select', 'projection']:
                    # Column projection
                    if column in op.columns:
                        # Trace back to source DataFrame
                        for source_var in op.source_vars:
                            if source_var in self.dataframe_vars:
                                sources.update(self._trace_column_sources(source_var, column))

                elif op.operation_type in ['withColumn', 'assign', 'transform']:
                    # Column transformation
                    if column in op.columns:
                        # Parse expression to find source columns
                        expr_sources = self._extract_columns_from_expression(op.expression or "")
                        for source_col in expr_sources:
                            for source_var in op.source_vars:
                                sources.update(self._trace_column_sources(source_var, source_col))

                elif op.operation_type in ['join', 'merge']:
                    # Join operation
                    if column in op.columns:
                        # Column could come from either side of join
                        for source_var in op.source_vars:
                            if source_var in self.dataframe_vars:
                                if column in self.dataframe_vars[source_var]:
                                    sources.update(self._trace_column_sources(source_var, column))

                elif op.operation_type in ['groupby', 'agg', 'aggregate']:
                    # Aggregation
                    if column in op.columns:
                        # Trace aggregation sources
                        expr_sources = self._extract_columns_from_expression(op.expression or "")
                        for source_col in expr_sources:
                            for source_var in op.source_vars:
                                sources.update(self._trace_column_sources(source_var, source_col))

        return sources

    def _extract_source_table(self, op: DataFrameOperation) -> str:
        """Extract source table name from read operation."""
        if op.expression:
            # Try to extract filename or table name
            # e.g., "customers.csv" -> "customers"
            import re
            match = re.search(r'["\']([^"\']+)["\']', op.expression)
            if match:
                path = match.group(1)
                # Extract filename without extension
                filename = path.split('/')[-1].split('.')[0]
                return filename
        return "unknown_source"

    def _extract_columns_from_expression(self, expression: str) -> list[str]:
        """Extract column names from an expression string."""
        # Simple regex-based extraction
        # This is a simplified version; real implementation would parse the expression
        import re

        # Match common patterns: df['col'], df.col, F.col('col'), pl.col('col')
        patterns = [
            r'["\'](\w+)["\']',  # String literals (column names)
            r'\.(\w+)(?!\()',    # Attribute access (df.col)
            r'col\(["\'](\w+)["\']\)',  # col('name') function
        ]

        columns = []
        for pattern in patterns:
            columns.extend(re.findall(pattern, expression))

        return list(set(columns))

    def _infer_transformation_type(self, df_var: str, column: str) -> str:
        """Infer transformation type for a column."""
        for op in reversed(self.operations):
            if op.target_var == df_var and column in op.columns:
                if op.operation_type in ['select', 'projection']:
                    return 'projection'
                elif op.operation_type in ['withColumn', 'assign', 'transform']:
                    return 'transformation'
                elif op.operation_type in ['groupby', 'agg', 'aggregate']:
                    return 'aggregation'
                elif op.operation_type in ['join', 'merge']:
                    return 'join'
        return 'projection'


class DataFrameVisitor(ast.NodeVisitor):
    """AST visitor to extract DataFrame operations."""

    def __init__(self, library: DataFrameLibrary):
        """Initialize visitor."""
        self.library = library
        self.operations: list[DataFrameOperation] = []
        self.dataframe_vars: dict[str, set[str]] = {}

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statements to track DataFrame operations."""
        # Get target variable name
        if not node.targets or not isinstance(node.targets[0], ast.Name):
            self.generic_visit(node)
            return

        target_var = node.targets[0].id

        # Analyze the value being assigned
        if isinstance(node.value, ast.Call):
            self._analyze_call(node.value, target_var, node.lineno)

        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Visit expression statements (e.g., df.to_csv())."""
        if isinstance(node.value, ast.Call):
            self._analyze_call(node.value, None, node.lineno)
        self.generic_visit(node)

    def _analyze_call(self, call: ast.Call, target_var: Optional[str], lineno: int) -> None:
        """Analyze a function call to extract DataFrame operation."""
        # Get function name
        func_name = self._get_func_name(call)

        if not func_name:
            return

        # Determine operation type based on function name and library
        if self.library == DataFrameLibrary.PANDAS:
            self._analyze_pandas_call(call, func_name, target_var, lineno)
        elif self.library == DataFrameLibrary.POLARS:
            self._analyze_polars_call(call, func_name, target_var, lineno)
        elif self.library == DataFrameLibrary.PYSPARK:
            self._analyze_pyspark_call(call, func_name, target_var, lineno)

    def _get_func_name(self, call: ast.Call) -> Optional[str]:
        """Extract function name from call."""
        if isinstance(call.func, ast.Name):
            return call.func.id
        elif isinstance(call.func, ast.Attribute):
            return call.func.attr
        return None

    def _analyze_pandas_call(
        self,
        call: ast.Call,
        func_name: str,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Analyze pandas-specific function call."""
        # Read operations
        if func_name in ['read_csv', 'read_parquet', 'read_sql', 'read_excel']:
            self._extract_pandas_read(call, func_name, target_var, lineno)

        # Select/filter operations
        elif func_name in ['filter', '__getitem__']:
            self._extract_pandas_select(call, func_name, target_var, lineno)

        # Column operations
        elif func_name in ['assign', 'apply', 'map']:
            self._extract_pandas_transform(call, func_name, target_var, lineno)

        # Join operations
        elif func_name in ['merge', 'join', 'concat']:
            self._extract_pandas_join(call, func_name, target_var, lineno)

        # Aggregation operations
        elif func_name in ['groupby', 'agg', 'aggregate', 'sum', 'mean', 'count']:
            self._extract_pandas_agg(call, func_name, target_var, lineno)

        # Write operations
        elif func_name in ['to_csv', 'to_parquet', 'to_sql', 'to_excel']:
            self._extract_pandas_write(call, func_name, target_var, lineno)

    def _analyze_polars_call(
        self,
        call: ast.Call,
        func_name: str,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Analyze polars-specific function call."""
        # Similar structure to pandas but with polars-specific methods
        if func_name in ['read_csv', 'read_parquet', 'read_database', 'scan_csv']:
            self._extract_polars_read(call, func_name, target_var, lineno)
        elif func_name in ['select', 'filter', 'with_columns']:
            self._extract_polars_select(call, func_name, target_var, lineno)
        elif func_name in ['join']:
            self._extract_polars_join(call, func_name, target_var, lineno)
        elif func_name in ['groupby', 'agg']:
            self._extract_polars_agg(call, func_name, target_var, lineno)
        elif func_name in ['write_csv', 'write_parquet']:
            self._extract_polars_write(call, func_name, target_var, lineno)

    def _analyze_pyspark_call(
        self,
        call: ast.Call,
        func_name: str,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Analyze pyspark-specific function call."""
        # Similar structure but with pyspark-specific methods
        if func_name in ['read', 'table']:
            self._extract_pyspark_read(call, func_name, target_var, lineno)
        elif func_name in ['select', 'filter', 'where', 'withColumn']:
            self._extract_pyspark_select(call, func_name, target_var, lineno)
        elif func_name in ['join']:
            self._extract_pyspark_join(call, func_name, target_var, lineno)
        elif func_name in ['groupBy', 'agg']:
            self._extract_pyspark_agg(call, func_name, target_var, lineno)
        elif func_name in ['write', 'save']:
            self._extract_pyspark_write(call, func_name, target_var, lineno)

    # Pandas extraction methods (simplified implementations)
    def _extract_pandas_read(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract pandas read operation."""
        if not target_var:
            return

        expression = ast.unparse(call) if hasattr(ast, 'unparse') else ""

        op = DataFrameOperation(
            operation_type='read',
            target_var=target_var,
            source_vars=[],
            columns=[],  # All columns from source
            expression=expression,
            line_number=lineno
        )
        self.operations.append(op)
        self.dataframe_vars[target_var] = set()  # Will be populated later

    def _extract_pandas_select(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract pandas select/filter operation."""
        # Simplified implementation
        pass

    def _extract_pandas_transform(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract pandas transformation operation."""
        pass

    def _extract_pandas_join(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract pandas join operation."""
        pass

    def _extract_pandas_agg(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract pandas aggregation operation."""
        pass

    def _extract_pandas_write(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract pandas write operation."""
        pass

    # Polars extraction methods (placeholders)
    def _extract_polars_read(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract polars read operation."""
        pass

    def _extract_polars_select(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract polars select operation."""
        pass

    def _extract_polars_join(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract polars join operation."""
        pass

    def _extract_polars_agg(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract polars aggregation operation."""
        pass

    def _extract_polars_write(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract polars write operation."""
        pass

    # PySpark extraction methods (placeholders)
    def _extract_pyspark_read(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract pyspark read operation."""
        pass

    def _extract_pyspark_select(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract pyspark select operation."""
        pass

    def _extract_pyspark_join(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract pyspark join operation."""
        pass

    def _extract_pyspark_agg(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract pyspark aggregation operation."""
        pass

    def _extract_pyspark_write(self, call: ast.Call, func_name: str, target_var: Optional[str], lineno: int) -> None:
        """Extract pyspark write operation."""
        pass


class PythonParseError(Exception):
    """Exception raised when Python code parsing fails."""
    pass


class LineageExtractionError(Exception):
    """Exception raised when lineage extraction fails."""
    pass
