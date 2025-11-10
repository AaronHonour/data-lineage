"""Data sources API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List

from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models import DataSourceModel
from app.presentation.schemas.data_source import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
)
from app.domain.entities.data_source import DataSource, DataSourceType, DataSourceStatus
from app.infrastructure.connectors.factory import ConnectorFactory
from app.application.services.lineage_sync_service import LineageSyncService

router = APIRouter(prefix="/data-sources")


@router.post(
    "",
    response_model=DataSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new data source"
)
async def create_data_source(
    data: DataSourceCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new data source for lineage tracking.

    - **name**: Unique name for the data source
    - **type**: Type of data source (postgres, mysql, iceberg, delta)
    - **connection_config**: Connection configuration dictionary
    - **sync_schedule**: Optional cron expression for scheduled syncs
    """
    # Validate source type
    if data.type not in [t.value for t in DataSourceType]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source type. Must be one of: {[t.value for t in DataSourceType]}"
        )

    # Check if name already exists
    result = await db.execute(
        select(DataSourceModel).where(DataSourceModel.name == data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Data source with name '{data.name}' already exists"
        )

    # Test connection
    try:
        connector = ConnectorFactory.create(data.type, data.connection_config)
        await connector.test_connection()
        await connector.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection test failed: {str(e)}"
        )

    # Create entity
    entity = DataSource(
        name=data.name,
        type=DataSourceType(data.type),
        connection_config=data.connection_config,
        sync_schedule=data.sync_schedule
    )

    # Save to database
    model = DataSourceModel.from_entity(entity)
    db.add(model)
    await db.commit()
    await db.refresh(model)

    return DataSourceResponse.model_validate(model)


@router.get(
    "",
    response_model=List[DataSourceResponse],
    summary="List all data sources"
)
async def list_data_sources(
    db: AsyncSession = Depends(get_db)
):
    """Get list of all registered data sources."""
    result = await db.execute(select(DataSourceModel).order_by(DataSourceModel.created_at.desc()))
    models = result.scalars().all()
    return [DataSourceResponse.model_validate(m) for m in models]


@router.get(
    "/{source_id}",
    response_model=DataSourceResponse,
    summary="Get data source by ID"
)
async def get_data_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get details of a specific data source."""
    result = await db.execute(
        select(DataSourceModel).where(DataSourceModel.id == source_id)
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found"
        )

    return DataSourceResponse.model_validate(model)


@router.put(
    "/{source_id}",
    response_model=DataSourceResponse,
    summary="Update data source"
)
async def update_data_source(
    source_id: UUID,
    data: DataSourceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update data source configuration."""
    result = await db.execute(
        select(DataSourceModel).where(DataSourceModel.id == source_id)
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found"
        )

    # Update fields
    if data.name is not None:
        model.name = data.name
    if data.connection_config is not None:
        model.connection_config = data.connection_config
    if data.sync_schedule is not None:
        model.sync_schedule = data.sync_schedule
    if data.status is not None:
        model.status = data.status

    await db.commit()
    await db.refresh(model)

    return DataSourceResponse.model_validate(model)


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete data source"
)
async def delete_data_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a data source and all associated metadata."""
    result = await db.execute(
        select(DataSourceModel).where(DataSourceModel.id == source_id)
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found"
        )

    await db.delete(model)
    await db.commit()


@router.post(
    "/{source_id}/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger metadata sync"
)
async def trigger_sync(
    source_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger metadata synchronization for a data source.

    This will:
    - Discover tables, views, and columns from the data source
    - Discover transformations (SQL views, dbt models, etc.)
    - Parse transformation code to extract column-level lineage
    - Build the global lineage graph in the database

    The sync runs in the background and may take several minutes for large sources.
    """
    result = await db.execute(
        select(DataSourceModel).where(DataSourceModel.id == source_id)
    )
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found"
        )

    # Create sync service
    sync_service = LineageSyncService(db)

    # Run sync (for now run synchronously; in production use Celery/RQ)
    try:
        stats = await sync_service.sync_data_source(source_id)

        return {
            "message": "Sync completed successfully",
            "source_id": str(source_id),
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )

@router.get(
    "/{source_id}/sync-jobs",
    summary="Get sync job history"
)
async def get_sync_jobs(
    source_id: UUID,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get sync job history for a data source.

    Returns the most recent sync jobs with their status and statistics.
    """
    from app.infrastructure.database.models import SyncJobModel

    result = await db.execute(
        select(DataSourceModel).where(DataSourceModel.id == source_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found"
        )

    # Get sync jobs
    result = await db.execute(
        select(SyncJobModel)
        .where(SyncJobModel.data_source_id == source_id)
        .order_by(SyncJobModel.created_at.desc())
        .limit(limit)
    )
    jobs = result.scalars().all()

    return {
        "source_id": str(source_id),
        "jobs": [
            {
                "id": str(job.id),
                "status": job.status,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
                "stats": job.stats
            }
            for job in jobs
        ]
    }
