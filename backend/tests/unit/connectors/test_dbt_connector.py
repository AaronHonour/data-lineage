"""Unit tests for dbt connector."""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from app.infrastructure.connectors.dbt_connector import (
    DbtConnector,
    DbtProjectParser,
)
from app.infrastructure.connectors.base import (
    ConnectionError as ConnectorConnectionError,
    DiscoveryError,
)


class TestDbtConnector:
    """Unit tests for dbt connector."""

    @pytest.fixture
    def temp_dbt_project(self, tmp_path):
        """Create temporary dbt project structure."""
        project_dir = tmp_path / "dbt_project"
        project_dir.mkdir()

        # Create dbt_project.yml
        dbt_project_yml = project_dir / "dbt_project.yml"
        dbt_project_yml.write_text("name: test_project\nversion: '1.0.0'\n")

        # Create target directory
        target_dir = project_dir / "target"
        target_dir.mkdir()

        return project_dir

    @pytest.fixture
    def dbt_config(self, temp_dbt_project):
        """dbt connection configuration."""
        return {
            "project_dir": str(temp_dbt_project),
        }

    @pytest.fixture
    def dbt_connector(self, dbt_config):
        """Create dbt connector instance."""
        return DbtConnector(dbt_config)

    @pytest.fixture
    def sample_manifest(self):
        """Sample dbt manifest data."""
        return {
            "metadata": {
                "adapter_type": "postgres",
                "dbt_version": "1.5.0"
            },
            "nodes": {
                "model.project.customers": {
                    "unique_id": "model.project.customers",
                    "name": "customers",
                    "schema": "analytics",
                    "database": "prod",
                    "resource_type": "model",
                    "raw_sql": "select * from {{ ref('stg_customers') }}",
                    "compiled_sql": "select * from analytics.stg_customers",
                    "depends_on": {
                        "nodes": ["model.project.stg_customers"]
                    },
                    "columns": {
                        "customer_id": {
                            "name": "customer_id",
                            "data_type": "integer"
                        },
                        "email": {
                            "name": "email",
                            "data_type": "varchar"
                        }
                    },
                    "tags": ["daily"],
                    "config": {
                        "materialized": "table"
                    }
                },
                "model.project.stg_customers": {
                    "unique_id": "model.project.stg_customers",
                    "name": "stg_customers",
                    "schema": "staging",
                    "database": "prod",
                    "resource_type": "model",
                    "raw_sql": "select * from {{ source('raw', 'customers') }}",
                    "compiled_sql": "select * from raw.customers",
                    "depends_on": {
                        "nodes": ["source.project.raw.customers"]
                    },
                    "columns": {},
                    "tags": [],
                    "config": {
                        "materialized": "view"
                    }
                },
                "test.project.test_customer_id": {
                    "resource_type": "test",
                    "name": "test_customer_id"
                }
            }
        }

    def test_init(self, dbt_connector, dbt_config, temp_dbt_project):
        """Test connector initialization."""
        assert str(dbt_connector.project_dir) == dbt_config["project_dir"]
        assert dbt_connector.manifest is None
        expected_manifest_path = temp_dbt_project / "target" / "manifest.json"
        assert Path(dbt_connector.manifest_path) == expected_manifest_path

    @pytest.mark.asyncio
    async def test_test_connection_success(self, dbt_connector, temp_dbt_project):
        """Test successful connection validation."""
        result = await dbt_connector.test_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_no_project_dir(self):
        """Test connection fails when project directory doesn't exist."""
        config = {"project_dir": "/nonexistent/path"}
        connector = DbtConnector(config)

        with pytest.raises(ConnectorConnectionError, match="dbt project directory not found"):
            await connector.test_connection()

    @pytest.mark.asyncio
    async def test_test_connection_no_dbt_project_yml(self, tmp_path):
        """Test connection fails when dbt_project.yml doesn't exist."""
        project_dir = tmp_path / "empty_project"
        project_dir.mkdir()

        config = {"project_dir": str(project_dir)}
        connector = DbtConnector(config)

        with pytest.raises(ConnectorConnectionError, match="dbt_project.yml not found"):
            await connector.test_connection()

    @pytest.mark.asyncio
    async def test_test_connection_with_manifest(self, dbt_connector, temp_dbt_project, sample_manifest):
        """Test connection with existing manifest."""
        manifest_path = temp_dbt_project / "target" / "manifest.json"
        manifest_path.write_text(json.dumps(sample_manifest))

        result = await dbt_connector.test_connection()
        assert result is True
        assert dbt_connector.manifest is not None

    @pytest.mark.asyncio
    async def test_discover_datasets_no_manifest(self, dbt_connector):
        """Test dataset discovery fails without manifest."""
        with pytest.raises(DiscoveryError, match="dbt manifest.json not found"):
            async for dataset in dbt_connector.discover_datasets():
                pass

    @pytest.mark.asyncio
    async def test_discover_datasets_with_models(self, dbt_connector, temp_dbt_project, sample_manifest):
        """Test dataset discovery with dbt models."""
        # Write manifest
        manifest_path = temp_dbt_project / "target" / "manifest.json"
        manifest_path.write_text(json.dumps(sample_manifest))

        datasets = []
        async for dataset in dbt_connector.discover_datasets():
            datasets.append(dataset)

        # Should have 2 models (customers and stg_customers, excluding test)
        assert len(datasets) == 2

        # Check first dataset (customers)
        customers = next(d for d in datasets if d.name == "customers")
        assert customers.name == "customers"
        assert customers.schema_name == "analytics"
        assert customers.type == "table"
        assert customers.fully_qualified_name == "dbt.analytics.customers"
        assert len(customers.columns) == 2
        assert customers.metadata['source_type'] == 'dbt'
        assert customers.metadata['materialized'] == 'table'
        assert customers.metadata['tags'] == ["daily"]

        # Check second dataset (stg_customers)
        stg_customers = next(d for d in datasets if d.name == "stg_customers")
        assert stg_customers.type == "view"
        assert stg_customers.metadata['materialized'] == 'view'

    @pytest.mark.asyncio
    async def test_discover_transformations_no_manifest(self, dbt_connector):
        """Test transformation discovery fails without manifest."""
        with pytest.raises(DiscoveryError, match="dbt manifest.json not found"):
            async for transformation in dbt_connector.discover_transformations():
                pass

    @pytest.mark.asyncio
    async def test_discover_transformations_with_models(self, dbt_connector, temp_dbt_project, sample_manifest):
        """Test transformation discovery with dbt models."""
        # Write manifest
        manifest_path = temp_dbt_project / "target" / "manifest.json"
        manifest_path.write_text(json.dumps(sample_manifest))

        transformations = []
        async for transformation in dbt_connector.discover_transformations():
            transformations.append(transformation)

        # Should have 2 transformations
        assert len(transformations) == 2

        # Check customers transformation
        customers_transform = next(t for t in transformations if "customers" in t.target_fqn and "stg" not in t.target_fqn)
        assert customers_transform.target_fqn == "dbt.analytics.customers"
        assert customers_transform.language == "sql"
        assert customers_transform.dialect == "postgres"
        assert customers_transform.type == "table"
        assert "select * from analytics.stg_customers" in customers_transform.code
        assert "dbt.staging.stg_customers" in customers_transform.source_fqns

        # Check stg_customers transformation
        stg_transform = next(t for t in transformations if "stg_customers" in t.target_fqn)
        assert stg_transform.type == "view"
        assert "raw.customers" in stg_transform.source_fqns

    @pytest.mark.asyncio
    async def test_close(self, dbt_connector):
        """Test closing connector (no-op for dbt)."""
        # Should not raise an error
        await dbt_connector.close()

    def test_load_manifest_file_exists(self, dbt_connector, temp_dbt_project, sample_manifest):
        """Test loading manifest from file."""
        manifest_path = temp_dbt_project / "target" / "manifest.json"
        manifest_path.write_text(json.dumps(sample_manifest))

        dbt_connector._load_manifest()

        assert dbt_connector.manifest is not None
        assert dbt_connector.manifest['metadata']['adapter_type'] == 'postgres'
        assert len(dbt_connector.manifest['nodes']) == 3

    def test_load_manifest_file_not_exists(self, dbt_connector):
        """Test loading manifest when file doesn't exist."""
        dbt_connector._load_manifest()
        assert dbt_connector.manifest is None

    def test_parse_model_node(self, dbt_connector, sample_manifest):
        """Test parsing dbt model node."""
        node = sample_manifest['nodes']['model.project.customers']
        model = dbt_connector._parse_model_node(node)

        assert model.unique_id == "model.project.customers"
        assert model.name == "customers"
        assert model.schema_name == "analytics"
        assert model.database == "prod"
        assert model.materialized == "table"
        assert len(model.columns) == 2
        assert model.columns[0].name == "customer_id"
        assert model.columns[0].data_type == "integer"
        assert model.tags == ["daily"]

    def test_extract_source_tables_model_dependency(self, dbt_connector, sample_manifest):
        """Test extracting source tables with model dependency."""
        dbt_connector.manifest = sample_manifest
        node = sample_manifest['nodes']['model.project.customers']

        sources = dbt_connector._extract_source_tables(node)

        assert len(sources) == 1
        assert "dbt.staging.stg_customers" in sources

    def test_extract_source_tables_source_dependency(self, dbt_connector, sample_manifest):
        """Test extracting source tables with source dependency."""
        dbt_connector.manifest = sample_manifest
        node = sample_manifest['nodes']['model.project.stg_customers']

        sources = dbt_connector._extract_source_tables(node)

        assert len(sources) == 1
        assert "raw.customers" in sources

    def test_get_dataset_type_mapping(self, dbt_connector):
        """Test dataset type mapping from materialization."""
        assert dbt_connector._get_dataset_type('view') == 'view'
        assert dbt_connector._get_dataset_type('table') == 'table'
        assert dbt_connector._get_dataset_type('incremental') == 'table'
        assert dbt_connector._get_dataset_type('ephemeral') == 'view'
        assert dbt_connector._get_dataset_type('materialized_view') == 'materialized_view'
        assert dbt_connector._get_dataset_type('unknown') == 'view'  # default

    def test_get_dialect_from_manifest(self, dbt_connector, sample_manifest):
        """Test getting dialect from manifest."""
        dbt_connector.manifest = sample_manifest
        dialect = dbt_connector._get_dialect()
        assert dialect == 'postgres'

    def test_get_dialect_default(self, dbt_connector):
        """Test getting default dialect without manifest."""
        dialect = dbt_connector._get_dialect()
        assert dialect == 'postgres'


class TestDbtProjectParser:
    """Unit tests for DbtProjectParser."""

    @pytest.fixture
    def temp_dbt_project(self, tmp_path):
        """Create temporary dbt project with models."""
        project_dir = tmp_path / "dbt_project"
        project_dir.mkdir()

        models_dir = project_dir / "models"
        models_dir.mkdir()

        # Create some model files
        (models_dir / "customers.sql").write_text("select * from {{ ref('stg_customers') }}")
        (models_dir / "staging").mkdir()
        (models_dir / "staging" / "stg_customers.sql").write_text(
            "select * from {{ source('raw', 'customers') }}"
        )

        return project_dir

    def test_init(self, temp_dbt_project):
        """Test parser initialization."""
        parser = DbtProjectParser(temp_dbt_project)
        assert parser.project_dir == temp_dbt_project
        assert parser.models_dir == temp_dbt_project / "models"

    def test_discover_models(self, temp_dbt_project):
        """Test discovering model files."""
        parser = DbtProjectParser(temp_dbt_project)
        models = parser.discover_models()

        assert len(models) == 2
        model_names = [m.name for m in models]
        assert "customers.sql" in model_names
        assert "stg_customers.sql" in model_names

    def test_discover_models_no_models_dir(self, tmp_path):
        """Test discovering models when models dir doesn't exist."""
        project_dir = tmp_path / "empty_project"
        project_dir.mkdir()

        parser = DbtProjectParser(project_dir)
        models = parser.discover_models()

        assert len(models) == 0

    def test_parse_model_refs_simple(self):
        """Test parsing ref() macro."""
        sql = "select * from {{ ref('stg_customers') }}"
        parser = DbtProjectParser(Path("/tmp"))

        refs = parser.parse_model_refs(sql)

        assert len(refs) == 1
        assert "stg_customers" in refs

    def test_parse_model_refs_multiple(self):
        """Test parsing multiple ref() macros."""
        sql = """
        select *
        from {{ ref('stg_customers') }} c
        join {{ ref('stg_orders') }} o
          on c.id = o.customer_id
        """
        parser = DbtProjectParser(Path("/tmp"))

        refs = parser.parse_model_refs(sql)

        assert len(refs) == 2
        assert "stg_customers" in refs
        assert "stg_orders" in refs

    def test_parse_model_refs_source(self):
        """Test parsing source() macro."""
        sql = "select * from {{ source('raw', 'customers') }}"
        parser = DbtProjectParser(Path("/tmp"))

        refs = parser.parse_model_refs(sql)

        assert len(refs) == 1
        assert "raw.customers" in refs

    def test_parse_model_refs_mixed(self):
        """Test parsing both ref() and source() macros."""
        sql = """
        with source_data as (
            select * from {{ source('raw', 'customers') }}
        ),
        staging as (
            select * from {{ ref('stg_orders') }}
        )
        select * from source_data join staging
        """
        parser = DbtProjectParser(Path("/tmp"))

        refs = parser.parse_model_refs(sql)

        assert len(refs) == 2
        assert "raw.customers" in refs
        assert "stg_orders" in refs

    def test_parse_model_refs_double_quotes(self):
        """Test parsing with double quotes."""
        sql = 'select * from {{ ref("stg_customers") }}'
        parser = DbtProjectParser(Path("/tmp"))

        refs = parser.parse_model_refs(sql)

        assert len(refs) == 1
        assert "stg_customers" in refs
