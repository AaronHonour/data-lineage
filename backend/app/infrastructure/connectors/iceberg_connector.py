"""Apache Iceberg connector for lineage extraction."""
from pathlib import Path
from typing import AsyncIterator, Optional
import json

from .base import (
    BaseConnector,
    ColumnMetadata,
    DatasetMetadata,
    TransformationMetadata,
    ConnectionError as ConnectorConnectionError,
    DiscoveryError,
)


class IcebergConnector(BaseConnector):
    """
    Apache Iceberg connector.

    Extracts lineage from Iceberg tables by:
    1. Reading Iceberg table metadata files
    2. Extracting schema and partition information
    3. Tracking table versions via snapshots
    4. Extracting transformation metadata from table properties

    Note: Requires pyiceberg library for production use.
    This implementation provides the connector interface and basic metadata reading.
    """

    def __init__(self, connection_config: dict[str, any]):
        """
        Initialize Iceberg connector.

        Args:
            connection_config: Should contain:
                - catalog_type: 'rest', 'hive', 'glue', 'hadoop', etc.
                - warehouse: Path or URI to Iceberg warehouse
                - catalog_properties: Dict of catalog-specific properties
        """
        super().__init__(connection_config)
        self.catalog_type = connection_config.get('catalog_type', 'hadoop')
        self.warehouse = connection_config.get('warehouse')
        self.catalog_properties = connection_config.get('catalog_properties', {})
        self.catalog = None

    async def test_connection(self) -> bool:
        """
        Test if Iceberg catalog is accessible.

        Returns:
            True if catalog is accessible
        """
        try:
            if not self.warehouse:
                raise ConnectorConnectionError("Iceberg warehouse path is required")

            # Check if warehouse directory exists (for file-based catalogs)
            if self.catalog_type in ['hadoop', 'local']:
                warehouse_path = Path(self.warehouse)
                if not warehouse_path.exists():
                    raise ConnectorConnectionError(
                        f"Iceberg warehouse not found: {self.warehouse}"
                    )

            # Try to initialize catalog
            self._initialize_catalog()

            return True

        except Exception as e:
            raise ConnectorConnectionError(f"Iceberg connection test failed: {e}") from e

    async def discover_datasets(self) -> AsyncIterator[DatasetMetadata]:
        """
        Discover Iceberg tables.

        Yields:
            DatasetMetadata for each Iceberg table
        """
        try:
            self._initialize_catalog()

            # List all namespaces and tables
            tables = self._list_tables()

            for namespace, table_name in tables:
                # Load table metadata
                table_metadata = self._load_table_metadata(namespace, table_name)

                if not table_metadata:
                    continue

                # Extract schema
                columns = self._parse_schema(table_metadata.get('current-schema-id'),
                                             table_metadata.get('schemas', []))

                # Get partition spec
                partition_spec = self._get_partition_spec(table_metadata)

                yield DatasetMetadata(
                    fully_qualified_name=f"iceberg.{namespace}.{table_name}",
                    name=table_name,
                    schema_name=namespace,
                    type='table',
                    columns=columns,
                    metadata={
                        'source_type': 'iceberg',
                        'format_version': table_metadata.get('format-version'),
                        'current_snapshot_id': table_metadata.get('current-snapshot-id'),
                        'partition_spec': partition_spec,
                        'location': table_metadata.get('location'),
                    }
                )

        except Exception as e:
            raise DiscoveryError(f"Failed to discover Iceberg tables: {e}") from e

    async def discover_transformations(self) -> AsyncIterator[TransformationMetadata]:
        """
        Extract transformation metadata from Iceberg tables.

        For Iceberg, transformations are typically stored in:
        - Table properties (SQL statements, dbt references)
        - Commit metadata
        - Lineage information in table properties

        Yields:
            TransformationMetadata for tables with transformation info
        """
        try:
            self._initialize_catalog()

            tables = self._list_tables()

            for namespace, table_name in tables:
                table_metadata = self._load_table_metadata(namespace, table_name)

                if not table_metadata:
                    continue

                # Check table properties for transformation metadata
                properties = table_metadata.get('properties', {})

                # Look for lineage/transformation metadata in properties
                if 'lineage.sql' in properties or 'transformation.sql' in properties:
                    sql = properties.get('lineage.sql') or properties.get('transformation.sql')
                    source_tables = properties.get('lineage.sources', '').split(',')

                    yield TransformationMetadata(
                        source_fqns=[s.strip() for s in source_tables if s.strip()],
                        target_fqn=f"iceberg.{namespace}.{table_name}",
                        code=sql,
                        language='sql',
                        dialect=properties.get('lineage.dialect', 'spark'),
                        type='table'
                    )

        except Exception as e:
            raise DiscoveryError(f"Failed to discover Iceberg transformations: {e}") from e

    async def close(self) -> None:
        """Close connection and cleanup resources."""
        self.catalog = None

    def _initialize_catalog(self) -> None:
        """Initialize Iceberg catalog."""
        if self.catalog:
            return

        # In production, this would use pyiceberg:
        # from pyiceberg.catalog import load_catalog
        # self.catalog = load_catalog(
        #     self.catalog_type,
        #     **self.catalog_properties
        # )

        # For now, use file-based discovery for hadoop/local catalogs
        if self.catalog_type in ['hadoop', 'local']:
            self.catalog = {'type': 'file', 'warehouse': self.warehouse}
        else:
            # Placeholder for other catalog types (REST, Hive, Glue)
            self.catalog = {
                'type': self.catalog_type,
                'properties': self.catalog_properties
            }

    def _list_tables(self) -> list[tuple[str, str]]:
        """
        List all tables in the catalog.

        Returns:
            List of (namespace, table_name) tuples
        """
        tables = []

        if self.catalog_type in ['hadoop', 'local']:
            # File-based discovery
            warehouse_path = Path(self.warehouse)
            if warehouse_path.exists():
                # Iceberg tables are typically: warehouse/namespace.db/table_name/metadata/
                for namespace_dir in warehouse_path.iterdir():
                    if namespace_dir.is_dir() and namespace_dir.name.endswith('.db'):
                        namespace = namespace_dir.name[:-3]  # Remove .db suffix
                        for table_dir in namespace_dir.iterdir():
                            if table_dir.is_dir():
                                tables.append((namespace, table_dir.name))

        return tables

    def _load_table_metadata(self, namespace: str, table_name: str) -> Optional[dict]:
        """
        Load Iceberg table metadata.

        Args:
            namespace: Table namespace
            table_name: Table name

        Returns:
            Metadata dictionary or None
        """
        if self.catalog_type in ['hadoop', 'local']:
            # Try to find metadata JSON file
            metadata_dir = Path(self.warehouse) / f"{namespace}.db" / table_name / "metadata"

            if not metadata_dir.exists():
                return None

            # Find the latest metadata file (v*.metadata.json)
            metadata_files = sorted(metadata_dir.glob("v*.metadata.json"), reverse=True)

            if not metadata_files:
                return None

            with open(metadata_files[0], 'r') as f:
                return json.load(f)

        return None

    def _parse_schema(self, schema_id: int, schemas: list[dict]) -> list[ColumnMetadata]:
        """
        Parse Iceberg schema to extract columns.

        Args:
            schema_id: Current schema ID
            schemas: List of schema definitions

        Returns:
            List of ColumnMetadata
        """
        columns = []

        # Find current schema
        current_schema = None
        for schema in schemas:
            if schema.get('schema-id') == schema_id:
                current_schema = schema
                break

        if not current_schema:
            return columns

        # Extract fields
        fields = current_schema.get('fields', [])

        for idx, field in enumerate(fields):
            columns.append(ColumnMetadata(
                name=field.get('name', ''),
                data_type=self._format_type(field.get('type')),
                ordinal_position=idx + 1,
                is_nullable=not field.get('required', False),
                is_primary_key=False  # Iceberg doesn't have explicit PKs
            ))

        return columns

    def _format_type(self, type_info: any) -> str:
        """Format Iceberg type to string."""
        if isinstance(type_info, str):
            return type_info
        elif isinstance(type_info, dict):
            return type_info.get('type', 'unknown')
        return str(type_info)

    def _get_partition_spec(self, table_metadata: dict) -> list[str]:
        """Extract partition columns from table metadata."""
        partition_specs = table_metadata.get('partition-specs', [])

        if not partition_specs:
            return []

        # Get current partition spec
        current_spec_id = table_metadata.get('default-spec-id', 0)
        current_spec = None

        for spec in partition_specs:
            if spec.get('spec-id') == current_spec_id:
                current_spec = spec
                break

        if not current_spec:
            return []

        # Extract field names
        partition_fields = []
        for field in current_spec.get('fields', []):
            name = field.get('name', '')
            if name:
                partition_fields.append(name)

        return partition_fields
