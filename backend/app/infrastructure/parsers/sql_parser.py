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
        target_table_fqn: str
    ) -> list[ColumnLineageResult]:
        """
        Extract column lineage from SQL.

        Args:
            sql: SQL query string
            target_table_fqn: Fully qualified name of target table

        Returns:
            List of column lineage results

        Raises:
            LineageExtractionError: If SQL parsing fails
        """
        try:
            # Parse SQL
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)

            # Get all columns in SELECT clause
            select_columns = self._get_select_columns(parsed)

            lineages = []
            for col_name, col_expr in select_columns.items():
                try:
                    # Use sqlglot lineage analysis
                    node = sqlglot_lineage(
                        col_name,
                        sql,
                        dialect=self.dialect,
                        schema={}  # Can provide schema for better accuracy
                    )

                    # Extract source columns
                    source_columns = self._extract_source_columns(node)

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

    def _get_select_columns(self, parsed) -> dict[str, any]:
        """Extract column names and expressions from SELECT."""
        columns = {}

        # Handle different SQL statement types
        if hasattr(parsed, 'expressions'):
            for expr in parsed.expressions:
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

    def _extract_source_columns(self, lineage_node) -> list[str]:
        """Extract source column FQNs from lineage node."""
        sources = []

        def traverse(node):
            """Recursively traverse lineage tree."""
            if hasattr(node, 'downstream'):
                for child in node.downstream:
                    traverse(child)

            # Extract column information
            if hasattr(node, 'name'):
                parts = []

                # Build FQN: [database.]schema.table.column
                if hasattr(node, 'table'):
                    table = node.table
                    if hasattr(table, 'db') and table.db:
                        parts.append(str(table.db))
                    if hasattr(table, 'schema') and table.schema:
                        parts.append(str(table.schema))
                    if hasattr(table, 'name'):
                        parts.append(str(table.name))

                parts.append(str(node.name))
                if len(parts) > 1:  # Only add if we have table context
                    sources.append('.'.join(parts))

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
