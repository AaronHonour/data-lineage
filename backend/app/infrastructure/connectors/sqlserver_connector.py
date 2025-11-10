"""SQL Server metadata connector."""
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


class SQLServerConnector(BaseConnector):
    """SQL Server metadata connector."""

    def __init__(self, connection_config: dict[str, any]):
        """
        Initialize SQL Server connector.

        Args:
            connection_config: Should contain: user, password, host, port, database, driver (optional)
        """
        super().__init__(connection_config)
        self.engine: Optional[AsyncEngine] = None

    async def test_connection(self) -> bool:
        """Test SQL Server connection."""
        try:
            engine = await self._get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            raise ConnectorConnectionError(f"SQL Server connection failed: {e}") from e

    async def discover_datasets(self) -> AsyncIterator[DatasetMetadata]:
        """Discover tables and views from INFORMATION_SCHEMA."""
        engine = await self._get_engine()

        query = text("""
            SELECT
                TABLE_SCHEMA,
                TABLE_NAME,
                TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA')
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """)

        try:
            async with engine.connect() as conn:
                result = await conn.execute(query)

                for row in result:
                    # Get columns for this table
                    columns = await self._get_columns(
                        conn, row.TABLE_SCHEMA, row.TABLE_NAME
                    )

                    # Determine dataset type
                    dataset_type = 'view' if row.TABLE_TYPE == 'VIEW' else 'table'

                    yield DatasetMetadata(
                        fully_qualified_name=f"sqlserver.{row.TABLE_SCHEMA}.{row.TABLE_NAME}",
                        name=row.TABLE_NAME,
                        schema_name=row.TABLE_SCHEMA,
                        type=dataset_type,
                        columns=columns,
                        metadata={
                            'source_type': 'sqlserver',
                            'table_type': row.TABLE_TYPE
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
                s.name AS schema_name,
                v.name AS view_name,
                m.definition
            FROM sys.views v
            INNER JOIN sys.schemas s ON v.schema_id = s.schema_id
            INNER JOIN sys.sql_modules m ON v.object_id = m.object_id
            WHERE s.name NOT IN ('sys', 'INFORMATION_SCHEMA')
        """)

        try:
            async with engine.connect() as conn:
                result = await conn.execute(views_query)
                for row in result:
                    yield TransformationMetadata(
                        source_fqns=[],  # Will be parsed from SQL
                        target_fqn=f"sqlserver.{row.schema_name}.{row.view_name}",
                        code=row.definition,
                        language='sql',
                        dialect='tsql',
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
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.ORDINAL_POSITION,
                c.IS_NULLABLE,
                CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS IS_PRIMARY_KEY
            FROM INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN (
                SELECT ku.TABLE_SCHEMA, ku.TABLE_NAME, ku.COLUMN_NAME
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                    ON tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                    AND tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                    AND tc.TABLE_SCHEMA = ku.TABLE_SCHEMA
                    AND tc.TABLE_NAME = ku.TABLE_NAME
            ) pk ON c.TABLE_SCHEMA = pk.TABLE_SCHEMA
                AND c.TABLE_NAME = pk.TABLE_NAME
                AND c.COLUMN_NAME = pk.COLUMN_NAME
            WHERE c.TABLE_SCHEMA = :schema AND c.TABLE_NAME = :table
            ORDER BY c.ORDINAL_POSITION
        """)

        result = await conn.execute(
            columns_query, {"schema": schema, "table": table}
        )
        columns_data = list(result)

        return [
            ColumnMetadata(
                name=row.COLUMN_NAME,
                data_type=row.DATA_TYPE,
                ordinal_position=row.ORDINAL_POSITION,
                is_nullable=(row.IS_NULLABLE == 'YES'),
                is_primary_key=(row.IS_PRIMARY_KEY == 1)
            )
            for row in columns_data
        ]

    async def _get_engine(self) -> AsyncEngine:
        """Get or create async engine."""
        if not self.engine:
            # Default driver
            driver = self.config.get('driver', 'ODBC Driver 18 for SQL Server')

            connection_string = (
                f"mssql+aiodbc://{self.config['user']}:"
                f"{self.config['password']}@{self.config['host']}:"
                f"{self.config.get('port', 1433)}/{self.config['database']}"
                f"?driver={driver}&TrustServerCertificate=yes"
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
