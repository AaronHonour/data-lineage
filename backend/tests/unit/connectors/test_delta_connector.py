"""Unit tests for Delta Lake connector."""
import pytest
import json
from pathlib import Path
from app.infrastructure.connectors.delta_connector import DeltaLakeConnector
from app.infrastructure.connectors.base import (
    ConnectionError as ConnectorConnectionError,
    DiscoveryError,
)


class TestDeltaLakeConnector:
    """Unit tests for Delta Lake connector."""

    @pytest.fixture
    def temp_delta_storage(self, tmp_path):
        """Create temporary Delta Lake storage structure."""
        storage = tmp_path / "delta_storage"
        storage.mkdir()

        # Create namespace directory
        namespace_dir = storage / "analytics"
        namespace_dir.mkdir()

        # Create Delta table directory with _delta_log
        table_dir = namespace_dir / "orders"
        table_dir.mkdir()
        delta_log_dir = table_dir / "_delta_log"
        delta_log_dir.mkdir()

        # Create commit file with metadata
        schema = {
            "type": "struct",
            "fields": [
                {"name": "order_id", "type": "long", "nullable": False, "metadata": {}},
                {"name": "customer_id", "type": "long", "nullable": True, "metadata": {}},
                {"name": "order_date", "type": "date", "nullable": True, "metadata": {}},
                {"name": "total", "type": "decimal(10,2)", "nullable": True, "metadata": {}}
            ]
        }

        commit_data = [
            {
                "protocol": {
                    "minReaderVersion": 1,
                    "minWriterVersion": 2
                }
            },
            {
                "metaData": {
                    "id": "12345-67890",
                    "name": "orders",
                    "schemaString": json.dumps(schema),
                    "partitionColumns": ["order_date"],
                    "createdTime": 1609459200000,
                    "configuration": {}
                }
            },
            {
                "add": {
                    "path": "part-00000.parquet",
                    "size": 1024,
                    "modificationTime": 1609459200000
                }
            }
        ]

        commit_file = delta_log_dir / "00000000000000000000.json"
        with open(commit_file, 'w') as f:
            for action in commit_data:
                f.write(json.dumps(action) + '\n')

        return storage

    @pytest.fixture
    def delta_config(self, temp_delta_storage):
        """Delta Lake connection configuration."""
        return {
            "storage_path": str(temp_delta_storage),
            "catalog_type": "file"
        }

    @pytest.fixture
    def delta_connector(self, delta_config):
        """Create Delta Lake connector instance."""
        return DeltaLakeConnector(delta_config)

    def test_init(self, delta_connector, delta_config):
        """Test connector initialization."""
        assert delta_connector.storage_path == delta_config["storage_path"]
        assert delta_connector.catalog_type == "file"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, delta_connector):
        """Test successful connection validation."""
        result = await delta_connector.test_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_no_storage_path(self):
        """Test connection fails when storage path is not specified."""
        config = {"catalog_type": "file"}
        connector = DeltaLakeConnector(config)

        with pytest.raises(ConnectorConnectionError, match="Delta Lake storage path is required"):
            await connector.test_connection()

    @pytest.mark.asyncio
    async def test_test_connection_storage_not_exists(self):
        """Test connection fails when storage doesn't exist."""
        config = {
            "storage_path": "/nonexistent/storage",
            "catalog_type": "file"
        }
        connector = DeltaLakeConnector(config)

        with pytest.raises(ConnectorConnectionError, match="Delta Lake storage not found"):
            await connector.test_connection()

    @pytest.mark.asyncio
    async def test_test_connection_s3_path(self):
        """Test connection with S3 path (doesn't check existence)."""
        config = {
            "storage_path": "s3://bucket/delta/tables",
            "catalog_type": "file"
        }
        connector = DeltaLakeConnector(config)

        # S3 paths don't check file existence
        result = await connector.test_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_discover_datasets_single_table(self, delta_connector):
        """Test dataset discovery with single Delta table."""
        datasets = []
        async for dataset in delta_connector.discover_datasets():
            datasets.append(dataset)

        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset.name == "orders"
        assert dataset.schema_name == "analytics"
        assert dataset.type == "table"
        assert dataset.fully_qualified_name == "delta.analytics.orders"
        assert len(dataset.columns) == 4
        assert dataset.metadata['source_type'] == 'delta'
        assert dataset.metadata['table_version'] == 0
        assert "order_date" in dataset.metadata['partition_columns']

        # Check columns
        columns = dataset.columns
        assert columns[0].name == "order_id"
        assert columns[0].data_type == "long"
        assert columns[0].is_nullable is False
        assert columns[1].name == "customer_id"
        assert columns[1].is_nullable is True
        assert columns[2].name == "order_date"
        assert columns[3].name == "total"

    @pytest.mark.asyncio
    async def test_discover_datasets_empty_storage(self, tmp_path):
        """Test dataset discovery with empty storage."""
        empty_storage = tmp_path / "empty_storage"
        empty_storage.mkdir()

        config = {"storage_path": str(empty_storage), "catalog_type": "file"}
        connector = DeltaLakeConnector(config)

        datasets = []
        async for dataset in connector.discover_datasets():
            datasets.append(dataset)

        assert len(datasets) == 0

    @pytest.mark.asyncio
    async def test_discover_datasets_no_metadata(self, tmp_path):
        """Test dataset discovery with Delta log but no metadata."""
        storage = tmp_path / "storage"
        storage.mkdir()

        # Create table with empty delta log
        table_dir = storage / "default" / "empty_table"
        table_dir.mkdir(parents=True)
        delta_log_dir = table_dir / "_delta_log"
        delta_log_dir.mkdir()

        config = {"storage_path": str(storage), "catalog_type": "file"}
        connector = DeltaLakeConnector(config)

        datasets = []
        async for dataset in connector.discover_datasets():
            datasets.append(dataset)

        # Should skip tables without valid metadata
        assert len(datasets) == 0

    @pytest.mark.asyncio
    async def test_discover_transformations_with_sql(self, tmp_path):
        """Test transformation discovery with SQL in commit info."""
        storage = tmp_path / "storage"
        storage.mkdir()

        namespace_dir = storage / "analytics"
        namespace_dir.mkdir()

        table_dir = namespace_dir / "fact_sales"
        table_dir.mkdir()
        delta_log_dir = table_dir / "_delta_log"
        delta_log_dir.mkdir()

        # Create commit with transformation metadata
        schema = {"type": "struct", "fields": []}
        commit_data = [
            {"metaData": {"id": "123", "schemaString": json.dumps(schema), "partitionColumns": []}},
            {
                "commitInfo": {
                    "version": 0,
                    "timestamp": 1609459200000,
                    "operation": "MERGE",
                    "operationParameters": {
                        "sql": "MERGE INTO fact_sales USING staging.sales ON fact_sales.id = staging.sales.id",
                        "sourceTable": "staging.sales"
                    }
                }
            }
        ]

        commit_file = delta_log_dir / "00000000000000000000.json"
        with open(commit_file, 'w') as f:
            for action in commit_data:
                f.write(json.dumps(action) + '\n')

        config = {"storage_path": str(storage), "catalog_type": "file"}
        connector = DeltaLakeConnector(config)

        transformations = []
        async for transformation in connector.discover_transformations():
            transformations.append(transformation)

        assert len(transformations) == 1
        transform = transformations[0]
        assert transform.target_fqn == "delta.analytics.fact_sales"
        assert transform.language == "sql"
        assert transform.dialect == "spark"
        assert transform.type == "table"
        assert "MERGE INTO fact_sales" in transform.code
        assert "staging.sales" in transform.source_fqns

    @pytest.mark.asyncio
    async def test_discover_transformations_no_sql(self, delta_connector):
        """Test transformation discovery with no SQL metadata."""
        transformations = []
        async for transformation in delta_connector.discover_transformations():
            transformations.append(transformation)

        # Table has no transformation metadata, should return empty
        assert len(transformations) == 0

    @pytest.mark.asyncio
    async def test_close(self, delta_connector):
        """Test closing connector (no-op for Delta)."""
        # Should not raise an error
        await delta_connector.close()

    def test_discover_delta_tables(self, delta_connector):
        """Test discovering Delta tables from storage."""
        tables = delta_connector._discover_delta_tables()

        assert len(tables) == 1
        table_path, namespace, table_name = tables[0]
        assert namespace == "analytics"
        assert table_name == "orders"
        assert "_delta_log" in table_path or "orders" in table_path

    def test_discover_delta_tables_multiple(self, tmp_path):
        """Test discovering multiple Delta tables."""
        storage = tmp_path / "storage"
        storage.mkdir()

        # Create multiple tables
        for ns in ["sales", "marketing"]:
            ns_dir = storage / ns
            ns_dir.mkdir()
            for table in ["customers", "orders"]:
                table_dir = ns_dir / table
                table_dir.mkdir()
                (table_dir / "_delta_log").mkdir()

        config = {"storage_path": str(storage), "catalog_type": "file"}
        connector = DeltaLakeConnector(config)

        tables = connector._discover_delta_tables()

        assert len(tables) == 4
        namespaces = [t[1] for t in tables]
        assert "sales" in namespaces
        assert "marketing" in namespaces

    def test_load_delta_metadata(self, delta_connector, temp_delta_storage):
        """Test loading Delta table metadata."""
        table_path = str(temp_delta_storage / "analytics" / "orders")
        metadata = delta_connector._load_delta_metadata(table_path)

        assert metadata is not None
        assert metadata['version'] == 0
        assert metadata['partitionColumns'] == ["order_date"]
        assert metadata['schema'] is not None

    def test_load_delta_metadata_not_found(self, delta_connector):
        """Test loading metadata for non-existent table."""
        metadata = delta_connector._load_delta_metadata("/nonexistent/table")
        assert metadata is None

    def test_get_latest_version(self, delta_connector, temp_delta_storage):
        """Test getting latest version from Delta log."""
        delta_log_path = temp_delta_storage / "analytics" / "orders" / "_delta_log"
        version = delta_connector._get_latest_version(delta_log_path)

        assert version == 0

    def test_get_latest_version_multiple_commits(self, tmp_path):
        """Test getting latest version with multiple commits."""
        delta_log_dir = tmp_path / "_delta_log"
        delta_log_dir.mkdir()

        # Create multiple commit files
        (delta_log_dir / "00000000000000000000.json").touch()
        (delta_log_dir / "00000000000000000001.json").touch()
        (delta_log_dir / "00000000000000000005.json").touch()

        config = {"storage_path": str(tmp_path), "catalog_type": "file"}
        connector = DeltaLakeConnector(config)

        version = connector._get_latest_version(delta_log_dir)

        assert version == 5

    def test_get_latest_version_no_commits(self, tmp_path):
        """Test getting version from empty Delta log."""
        delta_log_dir = tmp_path / "_delta_log"
        delta_log_dir.mkdir()

        config = {"storage_path": str(tmp_path), "catalog_type": "file"}
        connector = DeltaLakeConnector(config)

        version = connector._get_latest_version(delta_log_dir)

        assert version is None

    def test_parse_delta_schema(self, delta_connector):
        """Test parsing Delta schema string."""
        schema_string = json.dumps({
            "type": "struct",
            "fields": [
                {"name": "id", "type": "integer", "nullable": False, "metadata": {}},
                {"name": "name", "type": "string", "nullable": True, "metadata": {}},
            ]
        })

        columns = delta_connector._parse_delta_schema(schema_string)

        assert len(columns) == 2
        assert columns[0].name == "id"
        assert columns[0].data_type == "integer"
        assert columns[0].is_nullable is False
        assert columns[1].name == "name"
        assert columns[1].data_type == "string"
        assert columns[1].is_nullable is True

    def test_parse_delta_schema_empty(self, delta_connector):
        """Test parsing empty schema."""
        columns = delta_connector._parse_delta_schema(None)
        assert len(columns) == 0

        columns = delta_connector._parse_delta_schema("")
        assert len(columns) == 0

    def test_parse_delta_schema_invalid_json(self, delta_connector):
        """Test parsing invalid JSON schema."""
        columns = delta_connector._parse_delta_schema("invalid json")
        assert len(columns) == 0

    def test_format_delta_type_string(self, delta_connector):
        """Test formatting type as string."""
        assert delta_connector._format_delta_type("integer") == "integer"
        assert delta_connector._format_delta_type("string") == "string"

    def test_format_delta_type_dict(self, delta_connector):
        """Test formatting complex type as dict."""
        type_info = {"type": "array", "elementType": "string"}
        assert delta_connector._format_delta_type(type_info) == "array"

    def test_load_commit_history(self, tmp_path):
        """Test loading commit history."""
        table_dir = tmp_path / "table"
        table_dir.mkdir()
        delta_log_dir = table_dir / "_delta_log"
        delta_log_dir.mkdir()

        # Create multiple commits with commitInfo
        for version in range(3):
            commit_data = [
                {
                    "commitInfo": {
                        "version": version,
                        "timestamp": 1609459200000 + version,
                        "operation": "WRITE" if version == 0 else "APPEND",
                        "operationParameters": {"mode": "Append"}
                    }
                }
            ]

            commit_file = delta_log_dir / f"{version:020d}.json"
            with open(commit_file, 'w') as f:
                for action in commit_data:
                    f.write(json.dumps(action) + '\n')

        config = {"storage_path": str(tmp_path), "catalog_type": "file"}
        connector = DeltaLakeConnector(config)

        commits = connector._load_commit_history(str(table_dir), limit=10)

        # Should return commits in reverse order (newest first)
        assert len(commits) == 3
        assert commits[0]['version'] == 2
        assert commits[1]['version'] == 1
        assert commits[2]['version'] == 0

    def test_load_commit_history_limit(self, tmp_path):
        """Test loading commit history with limit."""
        table_dir = tmp_path / "table"
        table_dir.mkdir()
        delta_log_dir = table_dir / "_delta_log"
        delta_log_dir.mkdir()

        # Create 5 commits
        for version in range(5):
            commit_data = [{"commitInfo": {"version": version, "operation": "WRITE"}}]
            commit_file = delta_log_dir / f"{version:020d}.json"
            with open(commit_file, 'w') as f:
                for action in commit_data:
                    f.write(json.dumps(action) + '\n')

        config = {"storage_path": str(tmp_path), "catalog_type": "file"}
        connector = DeltaLakeConnector(config)

        commits = connector._load_commit_history(str(table_dir), limit=2)

        # Should only return 2 most recent
        assert len(commits) == 2
        assert commits[0]['version'] == 4
        assert commits[1]['version'] == 3

    def test_load_commit_history_no_commits(self, tmp_path):
        """Test loading commit history from empty log."""
        table_dir = tmp_path / "table"
        table_dir.mkdir()
        delta_log_dir = table_dir / "_delta_log"
        delta_log_dir.mkdir()

        config = {"storage_path": str(tmp_path), "catalog_type": "file"}
        connector = DeltaLakeConnector(config)

        commits = connector._load_commit_history(str(table_dir))

        assert len(commits) == 0
