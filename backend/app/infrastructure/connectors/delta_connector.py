"""Delta Lake connector for lineage extraction."""
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


class DeltaLakeConnector(BaseConnector):
    """
    Delta Lake connector.

    Extracts lineage from Delta tables by:
    1. Reading Delta transaction logs (_delta_log/)
    2. Extracting schema and partition information
    3. Tracking table versions via commit history
    4. Extracting transformation metadata from commit info

    Note: Requires delta-spark or deltalake library for production use.
    This implementation provides the connector interface and basic metadata reading.
    """

    def __init__(self, connection_config: dict[str, any]):
        """
        Initialize Delta Lake connector.

        Args:
            connection_config: Should contain:
                - storage_path: Path or URI to Delta Lake storage (S3, ADLS, GCS, local)
                - catalog_type: Optional ('unity_catalog', 'hive_metastore', 'file')
                - catalog_config: Optional catalog configuration
        """
        super().__init__(connection_config)
        self.storage_path = connection_config.get('storage_path')
        self.catalog_type = connection_config.get('catalog_type', 'file')
        self.catalog_config = connection_config.get('catalog_config', {})

    async def test_connection(self) -> bool:
        """
        Test if Delta Lake storage is accessible.

        Returns:
            True if storage is accessible
        """
        try:
            if not self.storage_path:
                raise ConnectorConnectionError("Delta Lake storage path is required")

            # Check if storage path exists (for file-based storage)
            if self.storage_path.startswith('/') or self.storage_path.startswith('file://'):
                storage_path = Path(self.storage_path.replace('file://', ''))
                if not storage_path.exists():
                    raise ConnectorConnectionError(
                        f"Delta Lake storage not found: {self.storage_path}"
                    )

            return True

        except Exception as e:
            raise ConnectorConnectionError(f"Delta Lake connection test failed: {e}") from e

    async def discover_datasets(self) -> AsyncIterator[DatasetMetadata]:
        """
        Discover Delta tables.

        Yields:
            DatasetMetadata for each Delta table
        """
        try:
            # Discover Delta tables
            tables = self._discover_delta_tables()

            for table_path, namespace, table_name in tables:
                # Load Delta table metadata
                table_info = self._load_delta_metadata(table_path)

                if not table_info:
                    continue

                # Extract schema from latest commit
                columns = self._parse_delta_schema(table_info.get('schema'))

                # Get partition columns
                partition_cols = table_info.get('partitionColumns', [])

                yield DatasetMetadata(
                    fully_qualified_name=f"delta.{namespace}.{table_name}",
                    name=table_name,
                    schema_name=namespace,
                    type='table',
                    columns=columns,
                    metadata={
                        'source_type': 'delta',
                        'table_version': table_info.get('version'),
                        'partition_columns': partition_cols,
                        'table_path': table_path,
                        'created_time': table_info.get('createdTime'),
                        'last_modified': table_info.get('lastModified'),
                    }
                )

        except Exception as e:
            raise DiscoveryError(f"Failed to discover Delta tables: {e}") from e

    async def discover_transformations(self) -> AsyncIterator[TransformationMetadata]:
        """
        Extract transformation metadata from Delta tables.

        For Delta Lake, transformations can be found in:
        - Commit metadata (operationParameters)
        - Table properties
        - History/audit log

        Yields:
            TransformationMetadata for tables with transformation info
        """
        try:
            tables = self._discover_delta_tables()

            for table_path, namespace, table_name in tables:
                # Load commit history
                commits = self._load_commit_history(table_path)

                for commit in commits:
                    # Check if commit contains transformation info
                    operation_params = commit.get('operationParameters', {})

                    if 'sql' in operation_params or 'predicate' in operation_params:
                        sql = operation_params.get('sql', operation_params.get('predicate', ''))

                        # Extract source tables from operation metadata
                        source_tables = []
                        if 'sourceTable' in operation_params:
                            source_tables.append(operation_params['sourceTable'])

                        yield TransformationMetadata(
                            source_fqns=source_tables,
                            target_fqn=f"delta.{namespace}.{table_name}",
                            code=sql,
                            language='sql',
                            dialect='spark',
                            type='table'
                        )

                        # Only return the most recent transformation
                        break

        except Exception as e:
            raise DiscoveryError(f"Failed to discover Delta transformations: {e}") from e

    async def close(self) -> None:
        """Close connection and cleanup resources."""
        pass

    def _discover_delta_tables(self) -> list[tuple[str, str, str]]:
        """
        Discover Delta tables in storage.

        Returns:
            List of (table_path, namespace, table_name) tuples
        """
        tables = []

        if self.storage_path.startswith('/') or self.storage_path.startswith('file://'):
            # File-based discovery
            storage_path = Path(self.storage_path.replace('file://', ''))

            if not storage_path.exists():
                return tables

            # Look for _delta_log directories (indicates Delta table)
            for path in storage_path.rglob('_delta_log'):
                table_path = str(path.parent)
                table_name = path.parent.name

                # Try to determine namespace from parent directory
                parent_parts = path.parent.parent.parts
                namespace = parent_parts[-1] if len(parent_parts) > 0 else 'default'

                tables.append((table_path, namespace, table_name))

        return tables

    def _load_delta_metadata(self, table_path: str) -> Optional[dict]:
        """
        Load Delta table metadata from _delta_log.

        Args:
            table_path: Path to Delta table

        Returns:
            Metadata dictionary or None
        """
        delta_log_path = Path(table_path) / "_delta_log"

        if not delta_log_path.exists():
            return None

        # Find the latest checkpoint or commit file
        latest_version = self._get_latest_version(delta_log_path)

        if latest_version is None:
            return None

        # Read the commit file
        commit_file = delta_log_path / f"{latest_version:020d}.json"

        if not commit_file.exists():
            return None

        metadata = {
            'version': latest_version,
            'schema': None,
            'partitionColumns': [],
            'createdTime': None,
            'lastModified': None,
        }

        # Parse Delta log JSON lines
        with open(commit_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    action = json.loads(line)

                    # Extract metadata action
                    if 'metaData' in action:
                        meta = action['metaData']
                        metadata['schema'] = meta.get('schemaString')
                        metadata['partitionColumns'] = meta.get('partitionColumns', [])
                        metadata['createdTime'] = meta.get('createdTime')

                    # Extract protocol version
                    if 'protocol' in action:
                        metadata['protocol'] = action['protocol']

                except json.JSONDecodeError:
                    continue

        # Get last modified time from file
        metadata['lastModified'] = commit_file.stat().st_mtime

        return metadata

    def _get_latest_version(self, delta_log_path: Path) -> Optional[int]:
        """Get the latest version number from Delta log."""
        # Find all JSON commit files
        commit_files = list(delta_log_path.glob("*.json"))

        if not commit_files:
            return None

        # Extract version numbers (format: 00000000000000000000.json)
        versions = []
        for cf in commit_files:
            try:
                # Skip _last_checkpoint file
                if cf.name.startswith('_'):
                    continue

                version = int(cf.stem)
                versions.append(version)
            except ValueError:
                continue

        return max(versions) if versions else None

    def _parse_delta_schema(self, schema_string: Optional[str]) -> list[ColumnMetadata]:
        """
        Parse Delta schema JSON string to extract columns.

        Args:
            schema_string: JSON string containing schema

        Returns:
            List of ColumnMetadata
        """
        columns = []

        if not schema_string:
            return columns

        try:
            schema = json.loads(schema_string)
            fields = schema.get('fields', [])

            for idx, field in enumerate(fields):
                # Delta schema format: {"name": str, "type": str, "nullable": bool, "metadata": {}}
                columns.append(ColumnMetadata(
                    name=field.get('name', ''),
                    data_type=self._format_delta_type(field.get('type')),
                    ordinal_position=idx + 1,
                    is_nullable=field.get('nullable', True),
                    is_primary_key=False
                ))

        except json.JSONDecodeError:
            pass

        return columns

    def _format_delta_type(self, type_info: any) -> str:
        """Format Delta type to string."""
        if isinstance(type_info, str):
            return type_info
        elif isinstance(type_info, dict):
            # Complex types like struct, array, map
            return type_info.get('type', 'unknown')
        return str(type_info)

    def _load_commit_history(self, table_path: str, limit: int = 10) -> list[dict]:
        """
        Load commit history from Delta log.

        Args:
            table_path: Path to Delta table
            limit: Maximum number of commits to load

        Returns:
            List of commit dictionaries
        """
        commits = []
        delta_log_path = Path(table_path) / "_delta_log"

        if not delta_log_path.exists():
            return commits

        # Get list of commit files in reverse order (newest first)
        commit_files = sorted(delta_log_path.glob("*.json"), reverse=True)

        for commit_file in commit_files[:limit]:
            if commit_file.name.startswith('_'):
                continue

            try:
                version = int(commit_file.stem)
            except ValueError:
                continue

            commit_info = {'version': version, 'operations': []}

            # Parse commit file
            with open(commit_file, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        action = json.loads(line)

                        # Extract commitInfo action
                        if 'commitInfo' in action:
                            commit_info.update(action['commitInfo'])

                    except json.JSONDecodeError:
                        continue

            if commit_info.get('operation'):
                commits.append(commit_info)

        return commits
