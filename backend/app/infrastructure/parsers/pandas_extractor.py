"""Pandas-specific lineage extraction from Python code."""
import ast
import re
from typing import Optional
from .python_parser import (
    DataFrameOperation,
    ColumnLineageResult,
    PythonLineageExtractor,
    DataFrameLibrary
)


class PandasLineageExtractor(PythonLineageExtractor):
    """
    Extract column-level lineage from pandas Python code.

    Supports common pandas operations:
    - read_csv, read_parquet, read_sql
    - Column selection: df[['col1', 'col2']]
    - Column assignment: df['new_col'] = df['old_col']
    - merge/join operations
    - groupby/agg operations
    - to_csv, to_parquet writes
    """

    def __init__(self):
        """Initialize pandas lineage extractor."""
        super().__init__(library=DataFrameLibrary.PANDAS)

    def extract_lineage_from_file(self, file_path: str) -> list[ColumnLineageResult]:
        """
        Extract lineage from a pandas Python file.

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
        """Analyze AST for pandas operations."""
        visitor = PandasVisitor()
        visitor.visit(tree)
        self.operations = visitor.operations
        self.dataframe_vars = visitor.dataframe_vars


class PandasVisitor(ast.NodeVisitor):
    """AST visitor specialized for pandas DataFrame operations."""

    def __init__(self):
        """Initialize pandas visitor."""
        self.operations: list[DataFrameOperation] = []
        self.dataframe_vars: dict[str, set[str]] = {}
        self.import_aliases: dict[str, str] = {}  # Track 'import pandas as pd'

    def visit_Import(self, node: ast.Import) -> None:
        """Track import statements."""
        for alias in node.names:
            if alias.name == 'pandas':
                self.import_aliases[alias.asname or 'pandas'] = 'pandas'
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from-import statements."""
        if node.module == 'pandas':
            for alias in node.names:
                self.import_aliases[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statements."""
        if not node.targets or not isinstance(node.targets[0], (ast.Name, ast.Subscript)):
            self.generic_visit(node)
            return

        # Handle df = pd.read_csv(...)
        if isinstance(node.targets[0], ast.Name):
            target_var = node.targets[0].id

            if isinstance(node.value, ast.Call):
                self._analyze_pandas_call(node.value, target_var, node.lineno)

        # Handle df['new_col'] = ...
        elif isinstance(node.targets[0], ast.Subscript):
            self._analyze_column_assignment(node)

        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        """Visit standalone expressions (e.g., df.to_csv())."""
        if isinstance(node.value, ast.Call):
            self._analyze_pandas_call(node.value, None, node.lineno)
        self.generic_visit(node)

    def _analyze_pandas_call(
        self,
        call: ast.Call,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Analyze pandas method calls."""
        func_name = self._get_method_name(call)

        if not func_name:
            return

        # Read operations
        if func_name in ['read_csv', 'read_parquet', 'read_sql', 'read_excel', 'read_json']:
            self._extract_read_op(call, func_name, target_var, lineno)

        # Column selection
        elif func_name == '__getitem__' and self._is_column_selection(call):
            self._extract_select_op(call, target_var, lineno)

        # Merge/Join
        elif func_name in ['merge', 'join']:
            self._extract_join_op(call, func_name, target_var, lineno)

        # GroupBy/Agg
        elif func_name in ['groupby']:
            self._extract_groupby_op(call, target_var, lineno)

        # Write operations
        elif func_name in ['to_csv', 'to_parquet', 'to_sql', 'to_excel', 'to_json']:
            self._extract_write_op(call, func_name, lineno)

    def _analyze_column_assignment(self, node: ast.Assign) -> None:
        """Analyze column assignment: df['new_col'] = expression."""
        subscript = node.targets[0]

        if not isinstance(subscript.value, ast.Name):
            return

        df_var = subscript.value.id

        # Extract column name
        if isinstance(subscript.slice, ast.Constant):
            col_name = subscript.slice.value
        else:
            return

        # Get source columns from expression
        source_cols = self._extract_columns_from_node(node.value)

        # Record operation
        op = DataFrameOperation(
            operation_type='assign',
            target_var=df_var,
            source_vars=[df_var],
            columns=[col_name],
            expression=self._node_to_code(node.value),
            line_number=node.lineno
        )
        self.operations.append(op)

        # Update dataframe columns
        if df_var not in self.dataframe_vars:
            self.dataframe_vars[df_var] = set()
        self.dataframe_vars[df_var].add(col_name)

    def _extract_read_op(
        self,
        call: ast.Call,
        func_name: str,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract pandas read operation."""
        if not target_var:
            return

        # Get source filename
        expression = self._node_to_code(call)

        op = DataFrameOperation(
            operation_type='read',
            target_var=target_var,
            source_vars=[],
            columns=[],  # Will be determined from schema or actual execution
            expression=expression,
            line_number=lineno
        )
        self.operations.append(op)

        # Initialize empty column set
        self.dataframe_vars[target_var] = set()

    def _extract_select_op(
        self,
        call: ast.Call,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract column selection operation: df[['col1', 'col2']]."""
        if not target_var:
            return

        # Get source dataframe
        if not isinstance(call.func, ast.Attribute):
            return

        source_var = self._get_dataframe_var(call.func.value)
        if not source_var:
            return

        # Extract selected columns
        columns = []
        if call.args:
            columns = self._extract_column_list(call.args[0])

        op = DataFrameOperation(
            operation_type='select',
            target_var=target_var,
            source_vars=[source_var],
            columns=columns,
            expression=self._node_to_code(call),
            line_number=lineno
        )
        self.operations.append(op)

        # Update dataframe columns
        self.dataframe_vars[target_var] = set(columns)

    def _extract_join_op(
        self,
        call: ast.Call,
        func_name: str,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract merge/join operation."""
        if not target_var:
            return

        # Get left dataframe (the one calling merge)
        if isinstance(call.func, ast.Attribute):
            left_var = self._get_dataframe_var(call.func.value)
        else:
            return

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

        # Update dataframe columns
        self.dataframe_vars[target_var] = set(all_cols)

    def _extract_groupby_op(
        self,
        call: ast.Call,
        target_var: Optional[str],
        lineno: int
    ) -> None:
        """Extract groupby operation."""
        # GroupBy is complex - simplified implementation
        if not target_var:
            return

        # Get source dataframe
        if isinstance(call.func, ast.Attribute):
            source_var = self._get_dataframe_var(call.func.value)
        else:
            return

        if not source_var:
            return

        # Extract groupby columns
        groupby_cols = []
        if call.args:
            groupby_cols = self._extract_column_list(call.args[0])

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
        """Extract write operation."""
        # Get source dataframe
        if isinstance(call.func, ast.Attribute):
            source_var = self._get_dataframe_var(call.func.value)
        else:
            return

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

    def _is_column_selection(self, call: ast.Call) -> bool:
        """Check if __getitem__ call is column selection."""
        # df[['col1', 'col2']] or df['col']
        if not call.args:
            return False
        arg = call.args[0]
        return isinstance(arg, (ast.List, ast.Constant, ast.Str))

    def _get_dataframe_var(self, node: ast.AST) -> Optional[str]:
        """Get dataframe variable name from node."""
        if isinstance(node, ast.Name):
            return node.id
        return None

    def _extract_column_list(self, node: ast.AST) -> list[str]:
        """Extract list of column names from node."""
        columns = []

        if isinstance(node, ast.List):
            for elt in node.elts:
                if isinstance(elt, ast.Constant):
                    columns.append(str(elt.value))
                elif isinstance(elt, ast.Str):  # Python 3.7 compatibility
                    columns.append(elt.s)
        elif isinstance(node, ast.Constant):
            columns.append(str(node.value))
        elif isinstance(node, ast.Str):
            columns.append(node.s)

        return columns

    def _extract_columns_from_node(self, node: ast.AST) -> list[str]:
        """Extract column names referenced in an expression node."""
        columns = []

        # Walk the AST to find subscripts (df['col'])
        for child in ast.walk(node):
            if isinstance(child, ast.Subscript):
                if isinstance(child.slice, ast.Constant):
                    columns.append(str(child.slice.value))
                elif isinstance(child.slice, ast.Str):
                    columns.append(child.slice.s)

        return columns

    def _node_to_code(self, node: ast.AST) -> str:
        """Convert AST node back to code string."""
        if hasattr(ast, 'unparse'):
            return ast.unparse(node)
        else:
            # Fallback for Python < 3.9
            return ast.dump(node)
