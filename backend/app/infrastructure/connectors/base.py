"""Base connector interface for data sources."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional


@dataclass
class ColumnMetadata:
    """Metadata about a column."""
    name: str
    data_type: str
    ordinal_position: int
    is_nullable: bool
    is_primary_key: bool = False


@dataclass
class DatasetMetadata:
    """Metadata about a dataset (table, view, file)."""
    fully_qualified_name: str
    name: str
    schema_name: Optional[str]
    type: str  # 'table', 'view', etc.
    columns: list[ColumnMetadata]
    metadata: dict[str, any]


@dataclass
class TransformationMetadata:
    """Metadata about a transformation (SQL query, script)."""
    source_fqns: list[str]
    target_fqn: str
    code: str
    language: str
    dialect: str
    type: str


class BaseConnector(ABC):
    """Base interface for all data source connectors."""

    def __init__(self, connection_config: dict[str, any]):
        """
        Initialize connector with connection configuration.

        Args:
            connection_config: Connection configuration dictionary
        """
        self.config = connection_config

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        Test if connection is valid.

        Returns:
            True if connection is successful
        """
        pass

    @abstractmethod
    async def discover_datasets(self) -> AsyncIterator[DatasetMetadata]:
        """
        Discover all datasets (tables, views) in the source.

        Yields:
            DatasetMetadata for each discovered dataset
        """
        pass

    @abstractmethod
    async def discover_transformations(self) -> AsyncIterator[TransformationMetadata]:
        """
        Discover transformation logic (views, stored procedures).

        Yields:
            TransformationMetadata for each discovered transformation
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection and cleanup resources."""
        pass


class ConnectorError(Exception):
    """Base exception for connector errors."""
    pass


class ConnectionError(ConnectorError):
    """Exception raised when connection fails."""
    pass


class DiscoveryError(ConnectorError):
    """Exception raised during metadata discovery."""
    pass
