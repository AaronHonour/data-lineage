"""Integration tests for database connectors."""
import os
import pytest
from app.infrastructure.connectors import (
    PostgreSQLConnector,
    MySQLConnector,
    SQLServerConnector,
    ConnectorFactory,
)
from app.domain.entities.data_source import DataSourceType

# Check if integration tests should run (requires running database containers)
INTEGRATION_TESTS_ENABLED = os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"

pytestmark = pytest.mark.skipif(
    not INTEGRATION_TESTS_ENABLED,
    reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable."
)


class TestPostgreSQLConnector:
    """Integration tests for PostgreSQL connector."""

    @pytest.fixture
    def pg_config(self):
        """PostgreSQL connection configuration."""
        return {
            "host": "localhost",
            "port": 5433,
            "database": "sample",
            "user": "sample",
            "password": "sample_password",
        }

    @pytest.fixture
    async def pg_connector(self, pg_config):
        """Create PostgreSQL connector instance."""
        connector = PostgreSQLConnector(pg_config)
        yield connector
        await connector.close()

    async def test_postgres_connection(self, pg_connector):
        """Test PostgreSQL connection."""
        result = await pg_connector.test_connection()
        assert result is True

    async def test_postgres_discover_datasets(self, pg_connector):
        """Test PostgreSQL dataset discovery."""
        datasets = []
        async for dataset in pg_connector.discover_datasets():
            datasets.append(dataset)

        # Should have tables from staging and analytics schemas
        assert len(datasets) > 0

        # Check we have expected tables
        dataset_names = {f"{d.schema_name}.{d.name}" for d in datasets}
        assert "staging.customers" in dataset_names
        assert "staging.orders" in dataset_names
        assert "staging.order_items" in dataset_names

        # Check column metadata
        customers = next(d for d in datasets if d.name == "customers")
        column_names = {c.name for c in customers.columns}
        assert "customer_id" in column_names
        assert "first_name" in column_names
        assert "last_name" in column_names
        assert "email" in column_names

        # Check primary key
        pk_columns = [c for c in customers.columns if c.is_primary_key]
        assert len(pk_columns) == 1
        assert pk_columns[0].name == "customer_id"

    async def test_postgres_discover_transformations(self, pg_connector):
        """Test PostgreSQL transformation discovery."""
        transformations = []
        async for transformation in pg_connector.discover_transformations():
            transformations.append(transformation)

        # Should have views from analytics schema
        assert len(transformations) > 0

        # Check we have expected views
        view_names = {t.target_fqn for t in transformations}
        assert any("customer_profiles" in name for name in view_names)
        assert any("order_summary" in name for name in view_names)

        # Check transformation metadata
        customer_profiles = next(
            t for t in transformations if "customer_profiles" in t.target_fqn
        )
        assert customer_profiles.language == "sql"
        assert customer_profiles.dialect == "postgres"
        assert customer_profiles.type in ["view", "materialized_view"]
        assert len(customer_profiles.code) > 0


class TestMySQLConnector:
    """Integration tests for MySQL connector."""

    @pytest.fixture
    def mysql_config(self):
        """MySQL connection configuration."""
        return {
            "host": "localhost",
            "port": 3306,
            "database": "sample",
            "user": "sample",
            "password": "sample_password",
        }

    @pytest.fixture
    async def mysql_connector(self, mysql_config):
        """Create MySQL connector instance."""
        connector = MySQLConnector(mysql_config)
        yield connector
        await connector.close()

    async def test_mysql_connection(self, mysql_connector):
        """Test MySQL connection."""
        result = await mysql_connector.test_connection()
        assert result is True

    async def test_mysql_discover_datasets(self, mysql_connector):
        """Test MySQL dataset discovery."""
        datasets = []
        async for dataset in mysql_connector.discover_datasets():
            datasets.append(dataset)

        # Should have tables from staging and analytics schemas
        assert len(datasets) > 0

        # Check we have expected tables
        dataset_names = {f"{d.schema_name}.{d.name}" for d in datasets}
        assert "staging.customers" in dataset_names
        assert "staging.orders" in dataset_names
        assert "staging.order_items" in dataset_names

        # Check column metadata
        customers = next(d for d in datasets if d.name == "customers")
        column_names = {c.name for c in customers.columns}
        assert "customer_id" in column_names
        assert "first_name" in column_names
        assert "last_name" in column_names
        assert "email" in column_names

        # Check primary key
        pk_columns = [c for c in customers.columns if c.is_primary_key]
        assert len(pk_columns) == 1
        assert pk_columns[0].name == "customer_id"

    async def test_mysql_discover_transformations(self, mysql_connector):
        """Test MySQL transformation discovery."""
        transformations = []
        async for transformation in mysql_connector.discover_transformations():
            transformations.append(transformation)

        # Should have views from analytics schema
        assert len(transformations) > 0

        # Check we have expected views
        view_names = {t.target_fqn for t in transformations}
        assert any("customer_profiles" in name for name in view_names)
        assert any("order_summary" in name for name in view_names)

        # Check transformation metadata
        customer_profiles = next(
            t for t in transformations if "customer_profiles" in t.target_fqn
        )
        assert customer_profiles.language == "sql"
        assert customer_profiles.dialect == "mysql"
        assert customer_profiles.type == "view"
        assert len(customer_profiles.code) > 0


class TestSQLServerConnector:
    """Integration tests for SQL Server connector."""

    @pytest.fixture
    def sqlserver_config(self):
        """SQL Server connection configuration."""
        return {
            "host": "localhost",
            "port": 1433,
            "database": "sample",
            "user": "sa",
            "password": "SamplePassword123!",
            "driver": "ODBC Driver 18 for SQL Server",
        }

    @pytest.fixture
    async def sqlserver_connector(self, sqlserver_config):
        """Create SQL Server connector instance."""
        connector = SQLServerConnector(sqlserver_config)
        yield connector
        await connector.close()

    async def test_sqlserver_connection(self, sqlserver_connector):
        """Test SQL Server connection."""
        result = await sqlserver_connector.test_connection()
        assert result is True

    async def test_sqlserver_discover_datasets(self, sqlserver_connector):
        """Test SQL Server dataset discovery."""
        datasets = []
        async for dataset in sqlserver_connector.discover_datasets():
            datasets.append(dataset)

        # Should have tables from staging and analytics schemas
        assert len(datasets) > 0

        # Check we have expected tables
        dataset_names = {f"{d.schema_name}.{d.name}" for d in datasets}
        assert "staging.customers" in dataset_names
        assert "staging.orders" in dataset_names
        assert "staging.order_items" in dataset_names

        # Check column metadata
        customers = next(d for d in datasets if d.name == "customers")
        column_names = {c.name for c in customers.columns}
        assert "customer_id" in column_names
        assert "first_name" in column_names
        assert "last_name" in column_names
        assert "email" in column_names

        # Check primary key
        pk_columns = [c for c in customers.columns if c.is_primary_key]
        assert len(pk_columns) == 1
        assert pk_columns[0].name == "customer_id"

    async def test_sqlserver_discover_transformations(self, sqlserver_connector):
        """Test SQL Server transformation discovery."""
        transformations = []
        async for transformation in sqlserver_connector.discover_transformations():
            transformations.append(transformation)

        # Should have views from analytics schema
        assert len(transformations) > 0

        # Check we have expected views
        view_names = {t.target_fqn for t in transformations}
        assert any("customer_profiles" in name for name in view_names)
        assert any("order_summary" in name for name in view_names)

        # Check transformation metadata
        customer_profiles = next(
            t for t in transformations if "customer_profiles" in t.target_fqn
        )
        assert customer_profiles.language == "sql"
        assert customer_profiles.dialect == "tsql"
        assert customer_profiles.type == "view"
        assert len(customer_profiles.code) > 0


class TestConnectorFactory:
    """Integration tests for Connector Factory."""

    def test_factory_create_postgres(self):
        """Test factory creates PostgreSQL connector."""
        config = {
            "host": "localhost",
            "port": 5433,
            "database": "sample",
            "user": "sample",
            "password": "sample_password",
        }
        connector = ConnectorFactory.create(DataSourceType.POSTGRES.value, config)
        assert isinstance(connector, PostgreSQLConnector)

    def test_factory_create_mysql(self):
        """Test factory creates MySQL connector."""
        config = {
            "host": "localhost",
            "port": 3306,
            "database": "sample",
            "user": "sample",
            "password": "sample_password",
        }
        connector = ConnectorFactory.create(DataSourceType.MYSQL.value, config)
        assert isinstance(connector, MySQLConnector)

    def test_factory_create_sqlserver(self):
        """Test factory creates SQL Server connector."""
        config = {
            "host": "localhost",
            "port": 1433,
            "database": "sample",
            "user": "sa",
            "password": "SamplePassword123!",
        }
        connector = ConnectorFactory.create(DataSourceType.SQLSERVER.value, config)
        assert isinstance(connector, SQLServerConnector)

    def test_factory_unsupported_type(self):
        """Test factory raises error for unsupported type."""
        with pytest.raises(ValueError, match="Unsupported data source type"):
            ConnectorFactory.create("unsupported", {})

    def test_factory_get_supported_types(self):
        """Test factory returns supported types."""
        supported = ConnectorFactory.get_supported_types()
        assert DataSourceType.POSTGRES.value in supported
        assert DataSourceType.MYSQL.value in supported
        assert DataSourceType.SQLSERVER.value in supported
