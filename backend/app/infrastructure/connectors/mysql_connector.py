"""MySQL metadata connector."""
from typing import AsyncIterator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text

from .base import (
    BaseConnector,
    ColumnMetadata,
    DatasetMetadata,
    TransformationMetadata,
    ConnectionError as ConnectorConnectionError,
    DiscoveryError,
)


class MySQLConnector(BaseConnector):
    """MySQL metadata connector."""

    def __init__(self, connection_config: dict[str, any]):
        """
        Initialize MySQL connector.

        Args:
            connection_config: Should contain: user, password, host, port, database
        """
        super().__init__(connection_config)
        self.engine: Optional[AsyncEngine] = None

    async def test_connection(self) -> bool:
        """Test MySQL connection."""
        try:
            engine = await self._get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            raise ConnectorConnectionError(f"MySQL connection failed: {e}") from e

    async def discover_datasets(self) -> AsyncIterator[DatasetMetadata]:
        """Discover tables and views from information_schema."""
        engine = await self._get_engine()

        query = text("""
            SELECT
                table_schema,
                table_name,
                table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
            ORDER BY table_schema, table_name
        """)

        try:
            async with engine.connect() as conn:
                result = await conn.execute(query)

                for row in result:
                    # Get columns for this table
                    columns = await self._get_columns(
                        conn, row.table_schema, row.table_name
                    )

                    # Determine dataset type
                    dataset_type = 'view' if row.table_type == 'VIEW' else 'table'

                    yield DatasetMetadata(
                        fully_qualified_name=f"mysql.{row.table_schema}.{row.table_name}",
                        name=row.table_name,
                        schema_name=row.table_schema,
                        type=dataset_type,
                        columns=columns,
                        metadata={
                            'source_type': 'mysql',
                            'table_type': row.table_type
                        }
                    )
        except Exception as e:
            raise DiscoveryError(f"Failed to discover datasets: {e}") from e

    async def discover_transformations(self) -> AsyncIterator[TransformationMetadata]:
        """Extract SQL from views."""
        engine = await self._get_engine()

        # Get views and their definitions
        views_query = text("""
            SELECT
                table_schema,
                table_name,
                view_definition
            FROM information_schema.views
            WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
        """)

        try:
            async with engine.connect() as conn:
                result = await conn.execute(views_query)
                for row in result:
                    yield TransformationMetadata(
                        source_fqns=[],  # Will be parsed from SQL
                        target_fqn=f"mysql.{row.table_schema}.{row.table_name}",
                        code=row.view_definition,
                        language='sql',
                        dialect='mysql',
                        type='view'
                    )

        except Exception as e:
            raise DiscoveryError(f"Failed to discover transformations: {e}") from e

    async def _get_columns(
        self, conn, schema: str, table: str
    ) -> list[ColumnMetadata]:
        """Get column metadata for a table."""
        # Get column information
        columns_query = text("""
            SELECT
                column_name,
                data_type,
                ordinal_position,
                is_nullable,
                column_key
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            ORDER BY ordinal_position
        """)

        result = await conn.execute(
            columns_query, {"schema": schema, "table": table}
        )
        columns_data = list(result)

        return [
            ColumnMetadata(
                name=row.column_name,
                data_type=row.data_type,
                ordinal_position=row.ordinal_position,
                is_nullable=(row.is_nullable == 'YES'),
                is_primary_key=(row.column_key == 'PRI')
            )
            for row in columns_data
        ]

    async def _get_engine(self) -> AsyncEngine:
        """Get or create async engine."""
        if not self.engine:
            connection_string = (
                f"mysql+aiomysql://{self.config['user']}:"
                f"{self.config['password']}@{self.config['host']}:"
                f"{self.config.get('port', 3306)}/{self.config['database']}"
            )
            self.engine = create_async_engine(
                connection_string,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10
            )
        return self.engine

    async def close(self) -> None:
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
