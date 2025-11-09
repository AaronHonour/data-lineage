"""SQLAlchemy database models."""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column as SQLColumn,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from app.domain.entities import (
    Column,
    ColumnLineage,
    DataSource,
    Dataset,
    Transformation,
)

Base = declarative_base()


class DataSourceModel(Base):
    """SQLAlchemy model for data sources."""

    __tablename__ = "data_sources"

    id = SQLColumn(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = SQLColumn(String(255), nullable=False, unique=True)
    type = SQLColumn(
        String(50),
        CheckConstraint("type IN ('postgres', 'mysql', 'sqlserver', 'iceberg', 'delta')"),
        nullable=False
    )
    connection_config = SQLColumn(JSONB, nullable=False)
    sync_schedule = SQLColumn(String(50), nullable=True)
    last_sync_at = SQLColumn(DateTime, nullable=True)
    status = SQLColumn(
        String(20),
        CheckConstraint("status IN ('active', 'error', 'disabled')"),
        nullable=False,
        default='active'
    )
    created_at = SQLColumn(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = SQLColumn(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    datasets = relationship("DatasetModel", back_populates="data_source", cascade="all, delete-orphan")

    def to_entity(self) -> DataSource:
        """Convert SQLAlchemy model to domain entity."""
        return DataSource(
            id=self.id,
            name=self.name,
            type=self.type,
            connection_config=self.connection_config,
            sync_schedule=self.sync_schedule,
            last_sync_at=self.last_sync_at,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @staticmethod
    def from_entity(entity: DataSource) -> "DataSourceModel":
        """Create SQLAlchemy model from domain entity."""
        return DataSourceModel(
            id=entity.id,
            name=entity.name,
            type=entity.type.value,
            connection_config=entity.connection_config,
            sync_schedule=entity.sync_schedule,
            last_sync_at=entity.last_sync_at,
            status=entity.status.value,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )


class DatasetModel(Base):
    """SQLAlchemy model for datasets."""

    __tablename__ = "datasets"

    id = SQLColumn(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    data_source_id = SQLColumn(PGUUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False)
    fully_qualified_name = SQLColumn(String(500), nullable=False, unique=True)
    name = SQLColumn(String(255), nullable=False)
    schema_name = SQLColumn(String(255), nullable=True)
    type = SQLColumn(
        String(50),
        CheckConstraint("type IN ('table', 'view', 'materialized_view', 'iceberg_table', 'delta_table', 'file')"),
        nullable=False
    )
    extra_metadata = SQLColumn('metadata', JSONB, default={}, nullable=False)
    last_synced_at = SQLColumn(DateTime, nullable=True)
    created_at = SQLColumn(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = SQLColumn(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    data_source = relationship("DataSourceModel", back_populates="datasets")
    columns = relationship("ColumnModel", back_populates="dataset", cascade="all, delete-orphan")

    def to_entity(self) -> Dataset:
        """Convert SQLAlchemy model to domain entity."""
        return Dataset(
            id=self.id,
            data_source_id=self.data_source_id,
            fully_qualified_name=self.fully_qualified_name,
            name=self.name,
            schema_name=self.schema_name,
            type=self.type,
            metadata=self.extra_metadata,
            last_synced_at=self.last_synced_at,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @staticmethod
    def from_entity(entity: Dataset) -> "DatasetModel":
        """Create SQLAlchemy model from domain entity."""
        return DatasetModel(
            id=entity.id,
            data_source_id=entity.data_source_id,
            fully_qualified_name=entity.fully_qualified_name,
            name=entity.name,
            schema_name=entity.schema_name,
            type=entity.type.value,
            extra_metadata=entity.metadata,
            last_synced_at=entity.last_synced_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )


class ColumnModel(Base):
    """SQLAlchemy model for columns."""

    __tablename__ = "columns"

    id = SQLColumn(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id = SQLColumn(PGUUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    name = SQLColumn(String(255), nullable=False)
    data_type = SQLColumn(String(100), nullable=True)
    ordinal_position = SQLColumn(Integer, nullable=True)
    is_nullable = SQLColumn(Boolean, default=True, nullable=False)
    is_primary_key = SQLColumn(Boolean, default=False, nullable=False)
    extra_metadata = SQLColumn('metadata', JSONB, default={}, nullable=False)
    created_at = SQLColumn(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = SQLColumn(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('dataset_id', 'name', name='uq_dataset_column'),
    )

    # Relationships
    dataset = relationship("DatasetModel", back_populates="columns")

    def to_entity(self) -> Column:
        """Convert SQLAlchemy model to domain entity."""
        return Column(
            id=self.id,
            dataset_id=self.dataset_id,
            name=self.name,
            data_type=self.data_type,
            ordinal_position=self.ordinal_position,
            is_nullable=self.is_nullable,
            is_primary_key=self.is_primary_key,
            metadata=self.extra_metadata,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @staticmethod
    def from_entity(entity: Column) -> "ColumnModel":
        """Create SQLAlchemy model from domain entity."""
        return ColumnModel(
            id=entity.id,
            dataset_id=entity.dataset_id,
            name=entity.name,
            data_type=entity.data_type,
            ordinal_position=entity.ordinal_position,
            is_nullable=entity.is_nullable,
            is_primary_key=entity.is_primary_key,
            extra_metadata=entity.metadata,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )


class TransformationModel(Base):
    """SQLAlchemy model for transformations."""

    __tablename__ = "transformations"

    id = SQLColumn(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_dataset_ids = SQLColumn(ARRAY(PGUUID(as_uuid=True)), nullable=False)
    target_dataset_id = SQLColumn(PGUUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    code = SQLColumn(Text, nullable=False)
    language = SQLColumn(
        String(50),
        CheckConstraint("language IN ('sql', 'python')"),
        nullable=False
    )
    dialect = SQLColumn(String(50), nullable=True)
    transformation_type = SQLColumn(String(50), nullable=True)
    extracted_from = SQLColumn(String(100), nullable=True)
    created_at = SQLColumn(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = SQLColumn(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_entity(self) -> Transformation:
        """Convert SQLAlchemy model to domain entity."""
        return Transformation(
            id=self.id,
            source_dataset_ids=list(self.source_dataset_ids) if self.source_dataset_ids else [],
            target_dataset_id=self.target_dataset_id,
            code=self.code,
            language=self.language,
            dialect=self.dialect,
            transformation_type=self.transformation_type,
            extracted_from=self.extracted_from,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @staticmethod
    def from_entity(entity: Transformation) -> "TransformationModel":
        """Create SQLAlchemy model from domain entity."""
        return TransformationModel(
            id=entity.id,
            source_dataset_ids=entity.source_dataset_ids,
            target_dataset_id=entity.target_dataset_id,
            code=entity.code,
            language=entity.language.value,
            dialect=entity.dialect,
            transformation_type=entity.transformation_type.value if entity.transformation_type else None,
            extracted_from=entity.extracted_from,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )


class ColumnLineageModel(Base):
    """SQLAlchemy model for column lineage relationships."""

    __tablename__ = "column_lineage"

    id = SQLColumn(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_column_id = SQLColumn(PGUUID(as_uuid=True), ForeignKey("columns.id", ondelete="CASCADE"), nullable=False)
    target_column_id = SQLColumn(PGUUID(as_uuid=True), ForeignKey("columns.id", ondelete="CASCADE"), nullable=False)
    transformation_id = SQLColumn(PGUUID(as_uuid=True), ForeignKey("transformations.id", ondelete="SET NULL"), nullable=True)
    expression = SQLColumn(Text, nullable=True)
    confidence = SQLColumn(Float, CheckConstraint("confidence >= 0 AND confidence <= 1"), default=1.0, nullable=False)
    created_at = SQLColumn(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('source_column_id', 'target_column_id', 'transformation_id', name='uq_column_lineage'),
    )

    def to_entity(self) -> ColumnLineage:
        """Convert SQLAlchemy model to domain entity."""
        return ColumnLineage(
            id=self.id,
            source_column_id=self.source_column_id,
            target_column_id=self.target_column_id,
            transformation_id=self.transformation_id,
            expression=self.expression,
            confidence=self.confidence,
            created_at=self.created_at
        )

    @staticmethod
    def from_entity(entity: ColumnLineage) -> "ColumnLineageModel":
        """Create SQLAlchemy model from domain entity."""
        return ColumnLineageModel(
            id=entity.id,
            source_column_id=entity.source_column_id,
            target_column_id=entity.target_column_id,
            transformation_id=entity.transformation_id,
            expression=entity.expression,
            confidence=entity.confidence,
            created_at=entity.created_at
        )


class SyncJobModel(Base):
    """SQLAlchemy model for sync job tracking."""

    __tablename__ = "sync_jobs"

    id = SQLColumn(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    data_source_id = SQLColumn(PGUUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False)
    status = SQLColumn(
        String(20),
        CheckConstraint("status IN ('running', 'completed', 'failed')"),
        nullable=False,
        default='running'
    )
    started_at = SQLColumn(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = SQLColumn(DateTime, nullable=True)
    error_message = SQLColumn(Text, nullable=True)
    stats = SQLColumn(JSONB, default={}, nullable=False)
    created_at = SQLColumn(DateTime, default=datetime.utcnow, nullable=False)
