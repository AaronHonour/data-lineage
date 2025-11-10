"""Unit tests for SQL Server connector."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.infrastructure.connectors.sqlserver_connector import SQLServerConnector
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


class TestSQLServerConnector:
    """Unit tests for SQL Server connector."""

    @pytest.fixture
    def sqlserver_config(self):
        """SQL Server connection configuration."""
        return {
            "host": "localhost",
            "port": 1433,
            "database": "testdb",
            "user": "sa",
            "password": "TestPass123!",
            "driver": "ODBC Driver 18 for SQL Server",
        }

    @pytest.fixture
    def sqlserver_connector(self, sqlserver_config):
        """Create SQL Server connector instance."""
        return SQLServerConnector(sqlserver_config)

    def test_init(self, sqlserver_connector, sqlserver_config):
        """Test connector initialization."""
        assert sqlserver_connector.config == sqlserver_config
        assert sqlserver_connector.engine is None

    @pytest.mark.asyncio
    async def test_test_connection_success(self, sqlserver_connector):
        """Test successful database connection."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        with patch.object(sqlserver_connector, '_get_engine', mock_get_engine):
            result = await sqlserver_connector.test_connection()

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, sqlserver_connector):
        """Test failed database connection."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Connection refused")

        async def mock_get_engine():
            return mock_engine

        with patch.object(sqlserver_connector, '_get_engine', mock_get_engine):
            with pytest.raises(ConnectorConnectionError, match="SQL Server connection failed"):
                await sqlserver_connector.test_connection()

    @pytest.mark.asyncio
    async def test_discover_datasets_empty(self, sqlserver_connector):
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

        with patch.object(sqlserver_connector, '_get_engine', mock_get_engine):
            datasets = []
            async for dataset in sqlserver_connector.discover_datasets():
                datasets.append(dataset)

        assert len(datasets) == 0

    @pytest.mark.asyncio
    async def test_discover_datasets_single_table(self, sqlserver_connector):
        """Test dataset discovery with single table."""
        # Mock table row (SQL Server uses uppercase column names)
        mock_table_row = MagicMock()
        mock_table_row.TABLE_SCHEMA = "dbo"
        mock_table_row.TABLE_NAME = "Orders"
        mock_table_row.TABLE_TYPE = "BASE TABLE"

        # Mock columns
        mock_columns = [
            ColumnMetadata(
                name="OrderID",
                data_type="int",
                ordinal_position=1,
                is_nullable=False,
                is_primary_key=True
            ),
            ColumnMetadata(
                name="CustomerID",
                data_type="int",
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

        with patch.object(sqlserver_connector, '_get_engine', mock_get_engine):
            with patch.object(sqlserver_connector, '_get_columns', mock_get_columns):
                datasets = []
                async for dataset in sqlserver_connector.discover_datasets():
                    datasets.append(dataset)

        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset.name == "Orders"
        assert dataset.schema_name == "dbo"
        assert dataset.type == "table"
        assert dataset.fully_qualified_name == "sqlserver.dbo.Orders"
        assert len(dataset.columns) == 2
        assert dataset.metadata['source_type'] == 'sqlserver'

    @pytest.mark.asyncio
    async def test_discover_datasets_view(self, sqlserver_connector):
        """Test dataset discovery with view."""
        mock_view_row = MagicMock()
        mock_view_row.TABLE_SCHEMA = "analytics"
        mock_view_row.TABLE_NAME = "CustomerSummary"
        mock_view_row.TABLE_TYPE = "VIEW"

        mock_columns = [
            ColumnMetadata(
                name="CustomerID",
                data_type="int",
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

        with patch.object(sqlserver_connector, '_get_engine', mock_get_engine):
            with patch.object(sqlserver_connector, '_get_columns', mock_get_columns):
                datasets = []
                async for dataset in sqlserver_connector.discover_datasets():
                    datasets.append(dataset)

        assert len(datasets) == 1
        assert datasets[0].type == "view"

    @pytest.mark.asyncio
    async def test_discover_datasets_error(self, sqlserver_connector):
        """Test dataset discovery handles errors."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Database error")

        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        with patch.object(sqlserver_connector, '_get_engine', mock_get_engine):
            with pytest.raises(DiscoveryError, match="Failed to discover datasets"):
                async for dataset in sqlserver_connector.discover_datasets():
                    pass

    @pytest.mark.asyncio
    async def test_discover_transformations_views(self, sqlserver_connector):
        """Test transformation discovery for views."""
        mock_view_row = MagicMock()
        mock_view_row.schema_name = "analytics"
        mock_view_row.view_name = "CustomerProfiles"
        mock_view_row.definition = "CREATE VIEW [analytics].[CustomerProfiles] AS SELECT * FROM [staging].[Customers] WHERE Active = 1"

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

        with patch.object(sqlserver_connector, '_get_engine', mock_get_engine):
            transformations = []
            async for transformation in sqlserver_connector.discover_transformations():
                transformations.append(transformation)

        assert len(transformations) == 1
        transformation = transformations[0]
        assert transformation.target_fqn == "sqlserver.analytics.CustomerProfiles"
        assert transformation.language == "sql"
        assert transformation.dialect == "tsql"
        assert transformation.type == "view"
        assert "SELECT * FROM" in transformation.code

    @pytest.mark.asyncio
    async def test_discover_transformations_error(self, sqlserver_connector):
        """Test transformation discovery handles errors."""
        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Query failed")

        mock_engine.connect.return_value = create_async_context_manager(mock_conn)

        async def mock_get_engine():
            return mock_engine

        with patch.object(sqlserver_connector, '_get_engine', mock_get_engine):
            with pytest.raises(DiscoveryError, match="Failed to discover transformations"):
                async for transformation in sqlserver_connector.discover_transformations():
                    pass

    @pytest.mark.asyncio
    async def test_get_columns(self, sqlserver_connector):
        """Test getting column metadata."""
        # Mock column data (SQL Server uses uppercase column names)
        mock_col_row1 = MagicMock()
        mock_col_row1.COLUMN_NAME = "OrderID"
        mock_col_row1.DATA_TYPE = "int"
        mock_col_row1.ORDINAL_POSITION = 1
        mock_col_row1.IS_NULLABLE = "NO"
        mock_col_row1.IS_PRIMARY_KEY = 1

        mock_col_row2 = MagicMock()
        mock_col_row2.COLUMN_NAME = "OrderDate"
        mock_col_row2.DATA_TYPE = "datetime"
        mock_col_row2.ORDINAL_POSITION = 2
        mock_col_row2.IS_NULLABLE = "YES"
        mock_col_row2.IS_PRIMARY_KEY = 0

        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([mock_col_row1, mock_col_row2])

        async def async_execute(*args, **kwargs):
            return mock_result

        mock_conn.execute = async_execute

        columns = await sqlserver_connector._get_columns(mock_conn, "dbo", "Orders")

        assert len(columns) == 2
        assert columns[0].name == "OrderID"
        assert columns[0].is_nullable is False
        assert columns[0].is_primary_key is True
        assert columns[1].name == "OrderDate"
        assert columns[1].is_nullable is True
        assert columns[1].is_primary_key is False

    @pytest.mark.asyncio
    async def test_get_engine_creates_new(self, sqlserver_connector):
        """Test engine creation on first call."""
        assert sqlserver_connector.engine is None

        with patch('app.infrastructure.connectors.sqlserver_connector.create_async_engine') as mock_create:
            mock_engine = AsyncMock()
            mock_create.return_value = mock_engine

            engine = await sqlserver_connector._get_engine()

            assert engine == mock_engine
            assert sqlserver_connector.engine == mock_engine
            mock_create.assert_called_once()

            # Verify connection string format
            call_args = mock_create.call_args[0][0]
            assert "mssql+aiodbc://" in call_args
            assert "sa" in call_args
            assert "TestPass123!" in call_args
            assert "localhost" in call_args
            assert "testdb" in call_args
            assert "driver=ODBC Driver 18" in call_args

    @pytest.mark.asyncio
    async def test_get_engine_reuses_existing(self, sqlserver_connector):
        """Test engine reuse on subsequent calls."""
        mock_engine = AsyncMock()
        sqlserver_connector.engine = mock_engine

        with patch('app.infrastructure.connectors.sqlserver_connector.create_async_engine') as mock_create:
            engine = await sqlserver_connector._get_engine()

            assert engine == mock_engine
            mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_close(self, sqlserver_connector):
        """Test closing connection."""
        mock_engine = AsyncMock()
        sqlserver_connector.engine = mock_engine

        await sqlserver_connector.close()

        mock_engine.dispose.assert_called_once()
        assert sqlserver_connector.engine is None

    @pytest.mark.asyncio
    async def test_close_no_engine(self, sqlserver_connector):
        """Test closing when no engine exists."""
        assert sqlserver_connector.engine is None

        # Should not raise an error
        await sqlserver_connector.close()

        assert sqlserver_connector.engine is None
