"""Unit tests for PostgreSQL connector."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.infrastructure.connectors.postgres_connector import PostgreSQLConnector
from app.infrastructure.connectors.base import (
    ColumnMetadata,
    DatasetMetadata,
    TransformationMetadata,
    ConnectionError as ConnectorConnectionError,
    DiscoveryError,
)


def create_async_context_manager(return_value):
    """Helper to create async context manager mock."""
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=return_value)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    return mock_cm


class TestPostgreSQLConnector:
    """Unit tests for PostgreSQL connector."""

    @pytest.fixture
    def pg_config(self):
        """PostgreSQL connection configuration."""
        return {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "user": "testuser",
            "password": "testpass",
        }

    @pytest.fixture
    def pg_connector(self, pg_config):
        """Create PostgreSQL connector instance."""
        return PostgreSQLConnector(pg_config)

    def test_init(self, pg_connector, pg_config):
        """Test connector initialization."""
        assert pg_connector.config == pg_config
        assert pg_connector.engine is None

    @pytest.mark.asyncio
    async def test_test_connection_success(self, pg_connector):
        """Test successful database connection."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        with patch.object(pg_connector, '_get_engine', mock_get_engine):
            result = await pg_connector.test_connection()

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, pg_connector):
        """Test failed database connection."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Connection refused")

        async def mock_get_engine():
            return mock_engine

        with patch.object(pg_connector, '_get_engine', mock_get_engine):
            with pytest.raises(ConnectorConnectionError, match="PostgreSQL connection failed"):
                await pg_connector.test_connection()

    @pytest.mark.asyncio
    async def test_discover_datasets_empty(self, pg_connector):
        """Test dataset discovery with no tables."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([])

        async def async_execute(*args, **kwargs):
            return mock_result

        mock_conn.execute = async_execute
        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        with patch.object(pg_connector, '_get_engine', mock_get_engine):
            datasets = []
            async for dataset in pg_connector.discover_datasets():
                datasets.append(dataset)

        assert len(datasets) == 0

    @pytest.mark.asyncio
    async def test_discover_datasets_single_table(self, pg_connector):
        """Test dataset discovery with single table."""
        # Mock table row
        mock_table_row = MagicMock()
        mock_table_row.table_schema = "public"
        mock_table_row.table_name = "users"
        mock_table_row.table_type = "BASE TABLE"

        # Mock columns
        mock_columns = [
            ColumnMetadata(
                name="id",
                data_type="integer",
                ordinal_position=1,
                is_nullable=False,
                is_primary_key=True
            ),
            ColumnMetadata(
                name="username",
                data_type="varchar",
                ordinal_position=2,
                is_nullable=False,
                is_primary_key=False
            ),
        ]

        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([mock_table_row])

        async def async_execute(*args, **kwargs):
            return mock_result

        mock_conn.execute = async_execute
        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        async def mock_get_columns(conn, schema, table):
            return mock_columns

        with patch.object(pg_connector, '_get_engine', mock_get_engine):
            with patch.object(pg_connector, '_get_columns', mock_get_columns):
                datasets = []
                async for dataset in pg_connector.discover_datasets():
                    datasets.append(dataset)

        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset.name == "users"
        assert dataset.schema_name == "public"
        assert dataset.type == "table"
        assert dataset.fully_qualified_name == "postgres.public.users"
        assert len(dataset.columns) == 2
        assert dataset.metadata['source_type'] == 'postgres'

    @pytest.mark.asyncio
    async def test_discover_datasets_view(self, pg_connector):
        """Test dataset discovery with view."""
        mock_view_row = MagicMock()
        mock_view_row.table_schema = "analytics"
        mock_view_row.table_name = "customer_summary"
        mock_view_row.table_type = "VIEW"

        mock_columns = [
            ColumnMetadata(
                name="customer_id",
                data_type="integer",
                ordinal_position=1,
                is_nullable=False,
                is_primary_key=False
            ),
        ]

        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([mock_view_row])

        async def async_execute(*args, **kwargs):
            return mock_result

        mock_conn.execute = async_execute
        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        async def mock_get_columns(conn, schema, table):
            return mock_columns

        with patch.object(pg_connector, '_get_engine', mock_get_engine):
            with patch.object(pg_connector, '_get_columns', mock_get_columns):
                datasets = []
                async for dataset in pg_connector.discover_datasets():
                    datasets.append(dataset)

        assert len(datasets) == 1
        assert datasets[0].type == "view"

    @pytest.mark.asyncio
    async def test_discover_datasets_materialized_view(self, pg_connector):
        """Test dataset discovery with materialized view."""
        mock_matview_row = MagicMock()
        mock_matview_row.table_schema = "analytics"
        mock_matview_row.table_name = "cached_summary"
        mock_matview_row.table_type = "MATERIALIZED VIEW"

        mock_columns = []

        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([mock_matview_row])

        async def async_execute(*args, **kwargs):
            return mock_result

        mock_conn.execute = async_execute
        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        async def mock_get_columns(conn, schema, table):
            return mock_columns

        with patch.object(pg_connector, '_get_engine', mock_get_engine):
            with patch.object(pg_connector, '_get_columns', mock_get_columns):
                datasets = []
                async for dataset in pg_connector.discover_datasets():
                    datasets.append(dataset)

        assert len(datasets) == 1
        assert datasets[0].type == "materialized_view"

    @pytest.mark.asyncio
    async def test_discover_datasets_error(self, pg_connector):
        """Test dataset discovery handles errors."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Database error")

        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        with patch.object(pg_connector, '_get_engine', mock_get_engine):
            with pytest.raises(DiscoveryError, match="Failed to discover datasets"):
                async for dataset in pg_connector.discover_datasets():
                    pass

    @pytest.mark.asyncio
    async def test_discover_transformations_views(self, pg_connector):
        """Test transformation discovery for views."""
        mock_view_row = MagicMock()
        mock_view_row.schemaname = "analytics"
        mock_view_row.viewname = "customer_profiles"
        mock_view_row.definition = "SELECT * FROM staging.customers WHERE active = true"

        mock_engine = MagicMock()
        mock_conn = AsyncMock()

        # First execute call (views)
        mock_views_result = MagicMock()
        mock_views_result.__iter__.return_value = iter([mock_view_row])

        # Second execute call (materialized views)
        mock_matviews_result = MagicMock()
        mock_matviews_result.__iter__.return_value = iter([])

        execute_results = [mock_views_result, mock_matviews_result]
        execute_index = [0]

        async def async_execute(*args, **kwargs):
            result = execute_results[execute_index[0]]
            execute_index[0] += 1
            return result

        mock_conn.execute = async_execute
        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        with patch.object(pg_connector, '_get_engine', mock_get_engine):
            transformations = []
            async for transformation in pg_connector.discover_transformations():
                transformations.append(transformation)

        assert len(transformations) == 1
        transformation = transformations[0]
        assert transformation.target_fqn == "postgres.analytics.customer_profiles"
        assert transformation.language == "sql"
        assert transformation.dialect == "postgres"
        assert transformation.type == "view"
        assert "SELECT * FROM staging.customers" in transformation.code

    @pytest.mark.asyncio
    async def test_discover_transformations_materialized_views(self, pg_connector):
        """Test transformation discovery for materialized views."""
        mock_matview_row = MagicMock()
        mock_matview_row.schemaname = "analytics"
        mock_matview_row.viewname = "cached_metrics"
        mock_matview_row.definition = "SELECT COUNT(*) as total FROM orders"

        mock_engine = MagicMock()
        mock_conn = AsyncMock()

        # First execute call (views)
        mock_views_result = MagicMock()
        mock_views_result.__iter__.return_value = iter([])

        # Second execute call (materialized views)
        mock_matviews_result = MagicMock()
        mock_matviews_result.__iter__.return_value = iter([mock_matview_row])

        execute_results = [mock_views_result, mock_matviews_result]
        execute_index = [0]

        async def async_execute(*args, **kwargs):
            result = execute_results[execute_index[0]]
            execute_index[0] += 1
            return result

        mock_conn.execute = async_execute
        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        with patch.object(pg_connector, '_get_engine', mock_get_engine):
            transformations = []
            async for transformation in pg_connector.discover_transformations():
                transformations.append(transformation)

        assert len(transformations) == 1
        transformation = transformations[0]
        assert transformation.type == "materialized_view"
        assert "COUNT(*)" in transformation.code

    @pytest.mark.asyncio
    async def test_discover_transformations_error(self, pg_connector):
        """Test transformation discovery handles errors."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Query failed")

        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        with patch.object(pg_connector, '_get_engine', mock_get_engine):
            with pytest.raises(DiscoveryError, match="Failed to discover transformations"):
                async for transformation in pg_connector.discover_transformations():
                    pass

    @pytest.mark.asyncio
    async def test_get_columns(self, pg_connector):
        """Test getting column metadata."""
        # Mock column data
        mock_col_row1 = MagicMock()
        mock_col_row1.column_name = "id"
        mock_col_row1.data_type = "integer"
        mock_col_row1.ordinal_position = 1
        mock_col_row1.is_nullable = "NO"

        mock_col_row2 = MagicMock()
        mock_col_row2.column_name = "name"
        mock_col_row2.data_type = "varchar"
        mock_col_row2.ordinal_position = 2
        mock_col_row2.is_nullable = "YES"

        # Mock primary key data
        mock_pk_row = MagicMock()
        mock_pk_row.column_name = "id"

        mock_conn = AsyncMock()

        # First execute call (columns)
        mock_columns_result = MagicMock()
        mock_columns_result.__iter__.return_value = iter([mock_col_row1, mock_col_row2])

        # Second execute call (primary keys)
        mock_pk_result = MagicMock()
        mock_pk_result.__iter__.return_value = iter([mock_pk_row])

        execute_results = [mock_columns_result, mock_pk_result]
        execute_index = [0]

        async def async_execute(*args, **kwargs):
            result = execute_results[execute_index[0]]
            execute_index[0] += 1
            return result

        mock_conn.execute = async_execute

        columns = await pg_connector._get_columns(mock_conn, "public", "users")

        assert len(columns) == 2
        assert columns[0].name == "id"
        assert columns[0].is_nullable is False
        assert columns[0].is_primary_key is True
        assert columns[1].name == "name"
        assert columns[1].is_nullable is True
        assert columns[1].is_primary_key is False

    @pytest.mark.asyncio
    async def test_get_engine_creates_new(self, pg_connector):
        """Test engine creation on first call."""
        assert pg_connector.engine is None

        with patch('app.infrastructure.connectors.postgres_connector.create_async_engine') as mock_create:
            mock_engine = AsyncMock()
            mock_create.return_value = mock_engine

            engine = await pg_connector._get_engine()

            assert engine == mock_engine
            assert pg_connector.engine == mock_engine
            mock_create.assert_called_once()

            # Verify connection string format
            call_args = mock_create.call_args[0][0]
            assert "postgresql+asyncpg://" in call_args
            assert "testuser" in call_args
            assert "testpass" in call_args
            assert "localhost" in call_args
            assert "testdb" in call_args

    @pytest.mark.asyncio
    async def test_get_engine_reuses_existing(self, pg_connector):
        """Test engine reuse on subsequent calls."""
        mock_engine = AsyncMock()
        pg_connector.engine = mock_engine

        with patch('app.infrastructure.connectors.postgres_connector.create_async_engine') as mock_create:
            engine = await pg_connector._get_engine()

            assert engine == mock_engine
            mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_close(self, pg_connector):
        """Test closing connection."""
        mock_engine = AsyncMock()
        pg_connector.engine = mock_engine

        await pg_connector.close()

        mock_engine.dispose.assert_called_once()
        assert pg_connector.engine is None

    @pytest.mark.asyncio
    async def test_close_no_engine(self, pg_connector):
        """Test closing when no engine exists."""
        assert pg_connector.engine is None

        # Should not raise an error
        await pg_connector.close()

        assert pg_connector.engine is None
