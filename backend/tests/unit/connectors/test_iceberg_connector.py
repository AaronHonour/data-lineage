"""Unit tests for Iceberg connector."""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.infrastructure.connectors.iceberg_connector import IcebergConnector
from app.infrastructure.connectors.base import (
    ConnectionError as ConnectorConnectionError,
    DiscoveryError,
)


class TestIcebergConnector:
    """Unit tests for Iceberg connector."""

    @pytest.fixture
    def temp_warehouse(self, tmp_path):
        """Create temporary Iceberg warehouse structure."""
        warehouse = tmp_path / "iceberg_warehouse"
        warehouse.mkdir()

        # Create namespace directory (database.db)
        namespace_dir = warehouse / "analytics.db"
        namespace_dir.mkdir()

        # Create table directory with metadata
        table_dir = namespace_dir / "orders"
        table_dir.mkdir()
        metadata_dir = table_dir / "metadata"
        metadata_dir.mkdir()

        # Create metadata file
        metadata = {
            "format-version": 2,
            "table-uuid": "12345-67890",
            "location": str(table_dir),
            "current-schema-id": 1,
            "current-snapshot-id": 3055729675574597004,
            "schemas": [
                {
                    "schema-id": 1,
                    "fields": [
                        {
                            "id": 1,
                            "name": "order_id",
                            "type": "long",
                            "required": True
                        },
                        {
                            "id": 2,
                            "name": "customer_id",
                            "type": "long",
                            "required": False
                        },
                        {
                            "id": 3,
                            "name": "order_date",
                            "type": "date",
                            "required": False
                        }
                    ]
                }
            ],
            "partition-specs": [
                {
                    "spec-id": 0,
                    "fields": [
                        {
                            "name": "order_date",
                            "transform": "day",
                            "source-id": 3,
                            "field-id": 1000
                        }
                    ]
                }
            ],
            "default-spec-id": 0,
            "properties": {}
        }

        metadata_file = metadata_dir / "v1.metadata.json"
        metadata_file.write_text(json.dumps(metadata))

        return warehouse

    @pytest.fixture
    def iceberg_config(self, temp_warehouse):
        """Iceberg connection configuration."""
        return {
            "catalog_type": "hadoop",
            "warehouse": str(temp_warehouse),
        }

    @pytest.fixture
    def iceberg_connector(self, iceberg_config):
        """Create Iceberg connector instance."""
        return IcebergConnector(iceberg_config)

    def test_init(self, iceberg_connector, iceberg_config):
        """Test connector initialization."""
        assert iceberg_connector.catalog_type == "hadoop"
        assert iceberg_connector.warehouse == iceberg_config["warehouse"]
        assert iceberg_connector.catalog is None

    @pytest.mark.asyncio
    async def test_test_connection_success(self, iceberg_connector, temp_warehouse):
        """Test successful connection validation."""
        result = await iceberg_connector.test_connection()
        assert result is True
        assert iceberg_connector.catalog is not None

    @pytest.mark.asyncio
    async def test_test_connection_no_warehouse(self):
        """Test connection fails when warehouse is not specified."""
        config = {"catalog_type": "hadoop"}
        connector = IcebergConnector(config)

        with pytest.raises(ConnectorConnectionError, match="Iceberg warehouse path is required"):
            await connector.test_connection()

    @pytest.mark.asyncio
    async def test_test_connection_warehouse_not_exists(self):
        """Test connection fails when warehouse doesn't exist."""
        config = {
            "catalog_type": "hadoop",
            "warehouse": "/nonexistent/warehouse"
        }
        connector = IcebergConnector(config)

        with pytest.raises(ConnectorConnectionError, match="Iceberg warehouse not found"):
            await connector.test_connection()

    @pytest.mark.asyncio
    async def test_test_connection_rest_catalog(self):
        """Test connection with REST catalog type."""
        config = {
            "catalog_type": "rest",
            "warehouse": "http://localhost:8181",
            "catalog_properties": {"uri": "http://localhost:8181"}
        }
        connector = IcebergConnector(config)

        # REST catalog doesn't check file existence
        result = await connector.test_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_discover_datasets_single_table(self, iceberg_connector, temp_warehouse):
        """Test dataset discovery with single Iceberg table."""
        datasets = []
        async for dataset in iceberg_connector.discover_datasets():
            datasets.append(dataset)

        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset.name == "orders"
        assert dataset.schema_name == "analytics"
        assert dataset.type == "table"
        assert dataset.fully_qualified_name == "iceberg.analytics.orders"
        assert len(dataset.columns) == 3
        assert dataset.metadata['source_type'] == 'iceberg'
        assert dataset.metadata['format_version'] == 2
        assert dataset.metadata['current_snapshot_id'] == 3055729675574597004

        # Check columns
        columns = dataset.columns
        assert columns[0].name == "order_id"
        assert columns[0].data_type == "long"
        assert columns[0].is_nullable is False
        assert columns[1].name == "customer_id"
        assert columns[1].is_nullable is True
        assert columns[2].name == "order_date"

        # Check partition spec
        assert "order_date" in dataset.metadata['partition_spec']

    @pytest.mark.asyncio
    async def test_discover_datasets_empty_warehouse(self, tmp_path):
        """Test dataset discovery with empty warehouse."""
        empty_warehouse = tmp_path / "empty_warehouse"
        empty_warehouse.mkdir()

        config = {
            "catalog_type": "hadoop",
            "warehouse": str(empty_warehouse)
        }
        connector = IcebergConnector(config)

        datasets = []
        async for dataset in connector.discover_datasets():
            datasets.append(dataset)

        assert len(datasets) == 0

    @pytest.mark.asyncio
    async def test_discover_datasets_no_metadata(self, tmp_path):
        """Test dataset discovery with table but no metadata file."""
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()

        # Create namespace and table without metadata
        namespace_dir = warehouse / "test.db"
        namespace_dir.mkdir()
        table_dir = namespace_dir / "empty_table"
        table_dir.mkdir()

        config = {
            "catalog_type": "hadoop",
            "warehouse": str(warehouse)
        }
        connector = IcebergConnector(config)

        datasets = []
        async for dataset in connector.discover_datasets():
            datasets.append(dataset)

        # Should skip tables without metadata
        assert len(datasets) == 0

    @pytest.mark.asyncio
    async def test_discover_transformations_with_lineage(self, tmp_path):
        """Test transformation discovery with lineage metadata."""
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()

        namespace_dir = warehouse / "analytics.db"
        namespace_dir.mkdir()

        table_dir = namespace_dir / "fact_orders"
        table_dir.mkdir()
        metadata_dir = table_dir / "metadata"
        metadata_dir.mkdir()

        # Metadata with transformation properties
        metadata = {
            "format-version": 2,
            "current-schema-id": 1,
            "schemas": [{"schema-id": 1, "fields": []}],
            "properties": {
                "lineage.sql": "SELECT * FROM staging.orders JOIN staging.customers",
                "lineage.sources": "staging.orders, staging.customers",
                "lineage.dialect": "spark"
            }
        }

        metadata_file = metadata_dir / "v1.metadata.json"
        metadata_file.write_text(json.dumps(metadata))

        config = {
            "catalog_type": "hadoop",
            "warehouse": str(warehouse)
        }
        connector = IcebergConnector(config)

        transformations = []
        async for transformation in connector.discover_transformations():
            transformations.append(transformation)

        assert len(transformations) == 1
        transform = transformations[0]
        assert transform.target_fqn == "iceberg.analytics.fact_orders"
        assert transform.language == "sql"
        assert transform.dialect == "spark"
        assert transform.type == "table"
        assert "SELECT * FROM staging.orders" in transform.code
        assert "staging.orders" in transform.source_fqns
        assert "staging.customers" in transform.source_fqns

    @pytest.mark.asyncio
    async def test_discover_transformations_no_lineage(self, iceberg_connector):
        """Test transformation discovery with no lineage metadata."""
        transformations = []
        async for transformation in iceberg_connector.discover_transformations():
            transformations.append(transformation)

        # Table has no lineage properties, should return empty
        assert len(transformations) == 0

    @pytest.mark.asyncio
    async def test_close(self, iceberg_connector):
        """Test closing connector."""
        iceberg_connector.catalog = {"type": "test"}
        await iceberg_connector.close()
        assert iceberg_connector.catalog is None

    def test_initialize_catalog_hadoop(self, iceberg_connector):
        """Test catalog initialization for hadoop type."""
        iceberg_connector._initialize_catalog()

        assert iceberg_connector.catalog is not None
        assert iceberg_connector.catalog['type'] == 'file'
        assert iceberg_connector.catalog['warehouse'] == iceberg_connector.warehouse

    def test_initialize_catalog_rest(self):
        """Test catalog initialization for REST type."""
        config = {
            "catalog_type": "rest",
            "warehouse": "http://localhost:8181",
            "catalog_properties": {"uri": "http://localhost:8181"}
        }
        connector = IcebergConnector(config)
        connector._initialize_catalog()

        assert connector.catalog is not None
        assert connector.catalog['type'] == 'rest'

    def test_initialize_catalog_reuse(self, iceberg_connector):
        """Test catalog is reused on subsequent calls."""
        iceberg_connector._initialize_catalog()
        catalog1 = iceberg_connector.catalog

        iceberg_connector._initialize_catalog()
        catalog2 = iceberg_connector.catalog

        assert catalog1 is catalog2

    def test_list_tables(self, iceberg_connector, temp_warehouse):
        """Test listing tables from warehouse."""
        iceberg_connector._initialize_catalog()
        tables = iceberg_connector._list_tables()

        assert len(tables) == 1
        assert tables[0] == ("analytics", "orders")

    def test_list_tables_multiple_namespaces(self, tmp_path):
        """Test listing tables from multiple namespaces."""
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()

        # Create multiple namespaces
        (warehouse / "ns1.db" / "table1").mkdir(parents=True)
        (warehouse / "ns1.db" / "table2").mkdir(parents=True)
        (warehouse / "ns2.db" / "table3").mkdir(parents=True)

        config = {"catalog_type": "hadoop", "warehouse": str(warehouse)}
        connector = IcebergConnector(config)
        connector._initialize_catalog()

        tables = connector._list_tables()

        assert len(tables) == 3
        assert ("ns1", "table1") in tables
        assert ("ns1", "table2") in tables
        assert ("ns2", "table3") in tables

    def test_load_table_metadata(self, iceberg_connector, temp_warehouse):
        """Test loading table metadata from file."""
        iceberg_connector._initialize_catalog()
        metadata = iceberg_connector._load_table_metadata("analytics", "orders")

        assert metadata is not None
        assert metadata['format-version'] == 2
        assert metadata['current-schema-id'] == 1

    def test_load_table_metadata_not_found(self, iceberg_connector):
        """Test loading metadata for non-existent table."""
        iceberg_connector._initialize_catalog()
        metadata = iceberg_connector._load_table_metadata("nonexistent", "table")

        assert metadata is None

    def test_parse_schema(self, iceberg_connector):
        """Test parsing Iceberg schema."""
        schemas = [
            {
                "schema-id": 1,
                "fields": [
                    {"name": "id", "type": "long", "required": True},
                    {"name": "name", "type": "string", "required": False},
                ]
            }
        ]

        columns = iceberg_connector._parse_schema(1, schemas)

        assert len(columns) == 2
        assert columns[0].name == "id"
        assert columns[0].data_type == "long"
        assert columns[0].is_nullable is False
        assert columns[1].name == "name"
        assert columns[1].data_type == "string"
        assert columns[1].is_nullable is True

    def test_parse_schema_not_found(self, iceberg_connector):
        """Test parsing schema when schema ID not found."""
        schemas = [{"schema-id": 1, "fields": []}]
        columns = iceberg_connector._parse_schema(999, schemas)

        assert len(columns) == 0

    def test_format_type_string(self, iceberg_connector):
        """Test formatting type as string."""
        assert iceberg_connector._format_type("long") == "long"
        assert iceberg_connector._format_type("string") == "string"

    def test_format_type_dict(self, iceberg_connector):
        """Test formatting complex type as dict."""
        type_info = {"type": "struct", "fields": []}
        assert iceberg_connector._format_type(type_info) == "struct"

    def test_get_partition_spec(self, iceberg_connector, temp_warehouse):
        """Test extracting partition spec from metadata."""
        iceberg_connector._initialize_catalog()
        metadata = iceberg_connector._load_table_metadata("analytics", "orders")

        partition_spec = iceberg_connector._get_partition_spec(metadata)

        assert len(partition_spec) == 1
        assert "order_date" in partition_spec

    def test_get_partition_spec_empty(self, iceberg_connector):
        """Test partition spec with no partitions."""
        metadata = {"partition-specs": []}
        partition_spec = iceberg_connector._get_partition_spec(metadata)

        assert len(partition_spec) == 0
