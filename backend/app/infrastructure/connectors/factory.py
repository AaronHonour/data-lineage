"""Connector factory for creating data source connectors."""
from typing import Type

from app.domain.entities.data_source import DataSourceType
from .base import BaseConnector
from .postgres_connector import PostgreSQLConnector
from .mysql_connector import MySQLConnector
from .sqlserver_connector import SQLServerConnector
from .dbt_connector import DbtConnector
from .iceberg_connector import IcebergConnector
from .delta_connector import DeltaLakeConnector


class ConnectorFactory:
    """Factory for creating data source connectors."""

    _connectors: dict[str, Type[BaseConnector]] = {
        DataSourceType.POSTGRES.value: PostgreSQLConnector,
        DataSourceType.MYSQL.value: MySQLConnector,
        DataSourceType.SQLSERVER.value: SQLServerConnector,
        DataSourceType.DBT.value: DbtConnector,
        DataSourceType.ICEBERG.value: IcebergConnector,
        DataSourceType.DELTA.value: DeltaLakeConnector,
    }

    @classmethod
    def create(cls, source_type: str, connection_config: dict[str, any]) -> BaseConnector:
        """
        Create a connector for the given source type.

        Args:
            source_type: Type of data source (postgres, mysql, etc.)
            connection_config: Connection configuration dictionary

        Returns:
            Connector instance

        Raises:
            ValueError: If source type is not supported
        """
        connector_class = cls._connectors.get(source_type)

        if not connector_class:
            raise ValueError(
                f"Unsupported data source type: {source_type}. "
                f"Supported types: {list(cls._connectors.keys())}"
            )

        return connector_class(connection_config)

    @classmethod
    def register_connector(cls, source_type: str, connector_class: Type[BaseConnector]) -> None:
        """
        Register a new connector type.

        Args:
            source_type: Type identifier
            connector_class: Connector class
        """
        cls._connectors[source_type] = connector_class

    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Get list of supported data source types."""
        return list(cls._connectors.keys())
