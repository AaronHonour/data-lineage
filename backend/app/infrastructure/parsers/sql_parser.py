"""SQL parser for lineage extraction using sqlglot."""
import sqlglot
from sqlglot.lineage import lineage as sqlglot_lineage
from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class ColumnLineageResult:
    """Result of column lineage extraction."""
    target_column: str
    source_columns: list[str]
    expression: str


class SQLLineageExtractor:
    """Extract column-level lineage from SQL using sqlglot."""

    def __init__(self, dialect: str = 'postgres'):
        """
        Initialize SQL lineage extractor.

        Args:
            dialect: SQL dialect (postgres, mysql, tsql, spark, etc.)
        """
        self.dialect = dialect

    def extract_lineage(
        self,
        sql: str,
        target_table_fqn: str,
        schema: Optional[dict[str, dict[str, str]]] = None
    ) -> list[ColumnLineageResult]:
        """
        Extract column lineage from SQL.

        Args:
            sql: SQL query string
            target_table_fqn: Fully qualified name of target table
            schema: Optional schema dictionary in format:
                    {"table_name": {"column_name": "column_type", ...}, ...}

        Returns:
            List of column lineage results

        Raises:
            LineageExtractionError: If SQL parsing fails
        """
        try:
            # Parse SQL
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)

            # Use empty dict if no schema provided
            if schema is None:
                schema = {}

            # Build alias mapping (alias -> real table name)
            alias_map = self._build_alias_map(parsed)

            # Get all columns in SELECT clause (pass schema for * expansion)
            select_columns = self._get_select_columns(parsed, schema=schema)

            lineages = []
            for col_name, col_expr in select_columns.items():
                try:
                    # Use sqlglot lineage analysis with schema
                    node = sqlglot_lineage(
                        col_name,
                        sql,
                        dialect=self.dialect,
                        schema=schema
                    )

                    # Extract source columns and resolve aliases
                    source_columns = self._extract_source_columns(node, alias_map)

                    lineages.append(ColumnLineageResult(
                        target_column=f"{target_table_fqn}.{col_name}",
                        source_columns=source_columns,
                        expression=str(col_expr)
                    ))
                except Exception as e:
                    # If lineage extraction fails for specific column,
                    # at least capture the column with empty sources
                    lineages.append(ColumnLineageResult(
                        target_column=f"{target_table_fqn}.{col_name}",
                        source_columns=[],
                        expression=str(col_expr)
                    ))

            return lineages

        except Exception as e:
            raise LineageExtractionError(f"Failed to parse SQL: {e}") from e

    def _get_select_columns(self, parsed, schema: dict = None) -> dict[str, any]:
        """Extract column names and expressions from SELECT."""
        columns = {}

        # Handle different SQL statement types
        if hasattr(parsed, 'expressions'):
            for expr in parsed.expressions:
                # Check if this is SELECT *
                if isinstance(expr, sqlglot.exp.Star):
                    # Expand * using schema if available
                    if schema:
                        # Get table names from FROM clause
                        for table in parsed.find_all(sqlglot.exp.Table):
                            table_name = str(table.name)
                            if table_name in schema:
                                # Add each column from the table
                                for col_name in schema[table_name].keys():
                                    # Create a Column expression for each
                                    col_expr = sqlglot.exp.Column(
                                        this=sqlglot.exp.Identifier(this=col_name),
                                        table=sqlglot.exp.Identifier(this=table_name)
                                    )
                                    columns[col_name] = col_expr
                    else:
                        # If no schema, use * as-is
                        columns['*'] = expr
                else:
                    # Get column name (alias or expression itself)
                    if hasattr(expr, 'alias'):
                        col_name = expr.alias or self._extract_column_name(expr)
                    else:
                        col_name = self._extract_column_name(expr)

                    columns[col_name] = expr

        return columns

    def _extract_column_name(self, expr) -> str:
        """Extract column name from expression."""
        # Handle different expression types
        if hasattr(expr, 'name'):
            return str(expr.name)
        return str(expr)

    def _build_alias_map(self, parsed) -> dict[str, str]:
        """
        Build mapping of table aliases to real table names.

        Returns:
            Dictionary mapping alias -> real_table_name
        """
        alias_map = {}

        # Find all tables and their aliases
        for table in parsed.find_all(sqlglot.exp.Table):
            real_name = str(table.name)

            # Check if table has an alias
            if hasattr(table, 'alias') and table.alias:
                alias_name = str(table.alias)
                alias_map[alias_name] = real_name

        return alias_map

    def _extract_source_columns(self, lineage_node, alias_map: dict[str, str] = None) -> list[str]:
        """
        Extract source column FQNs from lineage node.

        Args:
            lineage_node: The lineage node to extract from
            alias_map: Optional mapping of aliases to real table names
        """
        sources = []
        if alias_map is None:
            alias_map = {}

        def traverse(node):
            """Recursively traverse lineage tree."""
            # If this node has downstream dependencies, traverse them
            if hasattr(node, 'downstream') and node.downstream:
                for child in node.downstream:
                    traverse(child)

                    # Extract column name from downstream node
                    # The downstream node's name contains the full table.column format
                    if hasattr(child, 'name') and child.name:
                        # Check if this is actually a column reference (not just a table)
                        # Downstream leaf nodes typically have names like 'table.column'
                        name = str(child.name)
                        if '.' in name:  # Has table context
                            # Resolve alias if present
                            parts = name.split('.')
                            if len(parts) >= 2:
                                table_or_alias = parts[0]
                                column = '.'.join(parts[1:])  # Handle nested parts

                                # Resolve alias to real table name
                                real_table = alias_map.get(table_or_alias, table_or_alias)
                                resolved_name = f"{real_table}.{column}"
                                sources.append(resolved_name)
                            else:
                                sources.append(name)

        traverse(lineage_node)
        return list(set(sources))  # Remove duplicates

    def validate_sql(self, sql: str) -> tuple[bool, Optional[str]]:
        """
        Validate SQL syntax.

        Args:
            sql: SQL query string

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            sqlglot.parse_one(sql, dialect=self.dialect)
            return True, None
        except Exception as e:
            return False, str(e)

    def get_referenced_tables(self, sql: str) -> list[str]:
        """
        Get all tables referenced in SQL query.

        Args:
            sql: SQL query string

        Returns:
            List of table FQNs
        """
        try:
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)
            tables = []

            for table in parsed.find_all(sqlglot.exp.Table):
                parts = []
                if hasattr(table, 'db') and table.db:
                    parts.append(str(table.db))
                if hasattr(table, 'schema') and table.schema:
                    parts.append(str(table.schema))
                if hasattr(table, 'name'):
                    parts.append(str(table.name))

                if parts:
                    tables.append('.'.join(parts))

            return list(set(tables))
        except Exception:
            return []


class LineageExtractionError(Exception):
    """Exception raised when lineage extraction fails."""
    pass
