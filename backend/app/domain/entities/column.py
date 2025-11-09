"""Column domain entity."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Column:
    """Represents a column in a dataset."""

    dataset_id: UUID
    name: str
    data_type: str
    id: UUID = field(default_factory=uuid4)
    ordinal_position: Optional[int] = None
    is_nullable: bool = True
    is_primary_key: bool = False
    metadata: dict[str, any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def fully_qualified_name(self) -> str:
        """Get fully qualified column name (requires dataset FQN from join)."""
        # This will be constructed when joined with dataset
        return f"{self.dataset_id}.{self.name}"

    def __eq__(self, other: object) -> bool:
        """Compare columns by ID."""
        if not isinstance(other, Column):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash column by ID."""
        return hash(self.id)
