"""Column lineage domain entity."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class ColumnLineage:
    """Represents a lineage relationship between two columns."""

    source_column_id: UUID
    target_column_id: UUID
    id: UUID = field(default_factory=uuid4)
    transformation_id: Optional[UUID] = None
    expression: Optional[str] = None
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

    def is_direct_copy(self) -> bool:
        """Check if this is a direct column copy (no transformation)."""
        return self.expression is None or self.expression.strip() == ""

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if confidence is above threshold."""
        return self.confidence >= threshold

    def __eq__(self, other: object) -> bool:
        """Compare lineage by source and target columns."""
        if not isinstance(other, ColumnLineage):
            return False
        return (
            self.source_column_id == other.source_column_id
            and self.target_column_id == other.target_column_id
        )

    def __hash__(self) -> int:
        """Hash lineage by source and target."""
        return hash((self.source_column_id, self.target_column_id))
