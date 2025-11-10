"""Polars-specific lineage extraction from Python code."""
import ast
import re
from typing import Optional
from .python_parser import (
    DataFrameOperation,
    ColumnLineageResult,
    PythonLineageExtractor,
    DataFrameLibrary
)


class PolarsLineageExtractor(PythonLineageExtractor):
    """
    Extract column-level lineage from polars Python code.

    Supports common polars operations:
    - read_csv, read_parquet, scan_csv, scan_parquet
    - select, filter, with_columns
    - join operations
    - groupby/agg operations
    - write_csv, write_parquet
    """

    def __init__(self):
        """Initialize polars lineage extractor."""
        super().__init__(library=DataFrameLibrary.POLARS)

    def extract_lineage_from_file(self, file_path: str) -> list[ColumnLineageResult]:
        """
        Extract lineage from a polars Python file.

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
        """Analyze AST for polars operations."""
        visitor = PolarsVisitor()
        visitor.visit(tree)
        self.operations = visitor.operations
        self.dataframe_vars = visitor.dataframe_vars


class PolarsVisitor(ast.NodeVisitor):
    """AST visitor specialized for polars DataFrame operations."""

    def __init__(self):
        """Initialize polars visitor."""
        self.operations: list[DataFrameOperation] = []
        self.dataframe_vars: dict[str, set[str]] = {}
        self.import_aliases: dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> None:
        """Track import statements."""
        for alias in node.names:
            if alias.name == 'polars':
                self.import_aliases[alias.asname or 'polars'] = 'polars'
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from-import statements."""
        if node.module == 'polars':
            for alias in node.names:
                self.import_aliases[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statements."""
        if not node.targets or not isinstance(node.targets[0], ast.Name):
            self.generic_visit(node)
            return

        target_var = node.targets[0].id

        if isinstance(node.value, ast.Call):
            self._analyze_polars_call(node.value, target_var, node.lineno)

        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Visit standalone expressions (e.g., df.write_csv())."""
        if isinstance(node.value, ast.Call):
            self._analyze_polars_call(node.value, None, node.lineno)
        self.generic_visit(node)

    def _analyze_polars_call(
        self,
        call: ast.Call,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Analyze polars method calls."""
        func_name = self._get_method_name(call)

        if not func_name:
            return

        # Read operations
        if func_name in ['read_csv', 'read_parquet', 'read_json', 'read_database',
                          'scan_csv', 'scan_parquet', 'scan_ipc']:
            self._extract_read_op(call, func_name, target_var, lineno)

        # Select/filter operations
        elif func_name in ['select', 'filter', 'with_columns']:
            self._extract_select_op(call, func_name, target_var, lineno)

        # Join operations
        elif func_name == 'join':
            self._extract_join_op(call, target_var, lineno)

        # GroupBy
        elif func_name in ['groupby', 'group_by']:
            self._extract_groupby_op(call, target_var, lineno)

        # Write operations
        elif func_name in ['write_csv', 'write_parquet', 'write_json', 'write_database']:
            self._extract_write_op(call, func_name, lineno)

    def _extract_read_op(
        self,
        call: ast.Call,
        func_name: str,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract polars read operation."""
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
        """Extract polars select/filter/with_columns operation."""
        if not target_var:
            return

        # Get source dataframe
        source_var = self._get_dataframe_var(call.func)
        if not source_var:
            return

        # Extract columns from arguments
        columns = []
        for arg in call.args:
            # Polars uses pl.col('name') syntax
            if isinstance(arg, ast.Call):
                col_name = self._extract_col_name(arg)
                if col_name:
                    columns.append(col_name)
            elif isinstance(arg, ast.Constant):
                columns.append(str(arg.value))
            elif isinstance(arg, ast.Str):
                columns.append(arg.s)

        op_type = 'select' if func_name == 'select' else 'transform'

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
        if columns:
            self.dataframe_vars[target_var] = set(columns)
        elif source_var and source_var in self.dataframe_vars:
            self.dataframe_vars[target_var] = self.dataframe_vars[source_var].copy()

    def _extract_join_op(
        self,
        call: ast.Call,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract polars join operation."""
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
        """Extract polars groupby operation."""
        if not target_var:
            return

        # Get source dataframe
        source_var = self._get_dataframe_var(call.func)
        if not source_var:
            return

        # Extract groupby columns
        groupby_cols = []
        if call.args:
            for arg in call.args:
                if isinstance(arg, ast.Constant):
                    groupby_cols.append(str(arg.value))
                elif isinstance(arg, ast.Str):
                    groupby_cols.append(arg.s)
                elif isinstance(arg, ast.List):
                    for elt in arg.elts:
                        if isinstance(elt, ast.Constant):
                            groupby_cols.append(str(elt.value))

        op = DataFrameOperation(
            operation_type='groupby',
            target_var=target_var,
            source_vars=[source_var],
            columns=groupby_cols,
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
        """Extract polars write operation."""
        # Get source dataframe
        source_var = self._get_dataframe_var(call.func)

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
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            return node.value.id
        elif isinstance(node, ast.Name):
            return node.id
        return None

    def _extract_col_name(self, call_node: ast.Call) -> Optional[str]:
        """Extract column name from pl.col('name') call."""
        if isinstance(call_node.func, ast.Attribute):
            if call_node.func.attr == 'col' and call_node.args:
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
