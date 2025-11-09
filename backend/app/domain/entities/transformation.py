"""Transformation domain entity."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class TransformationLanguage(str, Enum):
    """Transformation language types."""
    SQL = "sql"
    PYTHON = "python"


class TransformationType(str, Enum):
    """Types of transformations."""
    VIEW = "view"
    MATERIALIZED_VIEW = "materialized_view"
    ETL = "etl"
    STORED_PROCEDURE = "stored_procedure"
    FUNCTION = "function"


@dataclass
class Transformation:
    """Represents a data transformation (SQL, Python, etc.)."""

    code: str
    language: TransformationLanguage
    target_dataset_id: UUID
    id: UUID = field(default_factory=uuid4)
    source_dataset_ids: list[UUID] = field(default_factory=list)
    dialect: Optional[str] = None
    transformation_type: Optional[TransformationType] = None
    extracted_from: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_sql(self) -> bool:
        """Check if transformation is SQL."""
        return self.language == TransformationLanguage.SQL

    def is_python(self) -> bool:
        """Check if transformation is Python."""
        return self.language == TransformationLanguage.PYTHON

    def add_source_dataset(self, dataset_id: UUID) -> None:
        """Add a source dataset to the transformation."""
        if dataset_id not in self.source_dataset_ids:
            self.source_dataset_ids.append(dataset_id)
            self.updated_at = datetime.utcnow()
