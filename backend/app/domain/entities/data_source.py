"""Data source domain entity."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class DataSourceType(str, Enum):
    """Supported data source types."""
    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    DBT = "dbt"
    ICEBERG = "iceberg"
    DELTA = "delta"


class DataSourceStatus(str, Enum):
    """Data source status."""
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class DataSource:
    """Represents a data source connection configuration."""

    name: str
    type: DataSourceType
    connection_config: dict[str, any]
    id: UUID = field(default_factory=uuid4)
    sync_schedule: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    status: DataSourceStatus = DataSourceStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_active(self) -> bool:
        """Check if data source is active."""
        return self.status == DataSourceStatus.ACTIVE

    def needs_sync(self, max_age_seconds: int = 3600) -> bool:
        """Check if data source needs metadata sync."""
        if not self.last_sync_at:
            return True

        age = (datetime.utcnow() - self.last_sync_at).total_seconds()
        return age > max_age_seconds

    def mark_synced(self) -> None:
        """Mark data source as synced."""
        self.last_sync_at = datetime.utcnow()
        self.status = DataSourceStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def mark_error(self) -> None:
        """Mark data source as having an error."""
        self.status = DataSourceStatus.ERROR
        self.updated_at = datetime.utcnow()

    def disable(self) -> None:
        """Disable data source."""
        self.status = DataSourceStatus.DISABLED
        self.updated_at = datetime.utcnow()
