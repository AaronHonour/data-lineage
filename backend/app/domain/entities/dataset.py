"""Dataset domain entity."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class DatasetType(str, Enum):
    """Dataset types."""
    TABLE = "table"
    VIEW = "view"
    MATERIALIZED_VIEW = "materialized_view"
    ICEBERG_TABLE = "iceberg_table"
    DELTA_TABLE = "delta_table"
    FILE = "file"


@dataclass
class Dataset:
    """Represents a dataset (table, view, file, etc.)."""

    data_source_id: UUID
    fully_qualified_name: str
    name: str
    type: DatasetType
    id: UUID = field(default_factory=uuid4)
    schema_name: Optional[str] = None
    metadata: dict[str, any] = field(default_factory=dict)
    last_synced_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """Check if dataset metadata is stale."""
        if not self.last_synced_at:
            return True

        age = datetime.utcnow() - self.last_synced_at
        return age.total_seconds() > (max_age_hours * 3600)

    def mark_synced(self) -> None:
        """Mark dataset as synced."""
        self.last_synced_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def is_table(self) -> bool:
        """Check if dataset is a physical table."""
        return self.type in [
            DatasetType.TABLE,
            DatasetType.ICEBERG_TABLE,
            DatasetType.DELTA_TABLE
        ]

    def is_view(self) -> bool:
        """Check if dataset is a view."""
        return self.type in [
            DatasetType.VIEW,
            DatasetType.MATERIALIZED_VIEW
        ]
