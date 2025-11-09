"""Pydantic schemas for lineage API."""
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional


class ColumnSchema(BaseModel):
    """Column schema for API responses."""
    id: UUID
    name: str
    data_type: Optional[str] = None
    is_primary_key: bool = False

    class Config:
        from_attributes = True


class DatasetSchema(BaseModel):
    """Dataset schema for API responses."""
    id: UUID
    name: str
    schema_name: Optional[str] = None
    fully_qualified_name: str
    source_type: str
    columns: list[ColumnSchema] = []

    class Config:
        from_attributes = True


class LineageEdgeSchema(BaseModel):
    """Lineage edge schema."""
    id: UUID
    source_column_id: UUID
    target_column_id: UUID
    expression: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class LineageGraphResponse(BaseModel):
    """Lineage graph API response."""
    datasets: list[DatasetSchema]
    edges: list[LineageEdgeSchema]
    metadata: dict = Field(default_factory=dict)
