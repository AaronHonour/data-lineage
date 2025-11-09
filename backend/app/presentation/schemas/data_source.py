"""Pydantic schemas for data source API."""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class DataSourceCreate(BaseModel):
    """Schema for creating a data source."""
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., description="Data source type: postgres, mysql, iceberg, delta")
    connection_config: dict = Field(..., description="Connection configuration (encrypted)")
    sync_schedule: Optional[str] = Field(None, description="Cron expression for sync schedule")


class DataSourceUpdate(BaseModel):
    """Schema for updating a data source."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    connection_config: Optional[dict] = None
    sync_schedule: Optional[str] = None
    status: Optional[str] = None


class DataSourceResponse(BaseModel):
    """Schema for data source API responses."""
    id: UUID
    name: str
    type: str
    status: str
    last_sync_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncJobResponse(BaseModel):
    """Schema for sync job responses."""
    id: UUID
    data_source_id: UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    stats: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True
