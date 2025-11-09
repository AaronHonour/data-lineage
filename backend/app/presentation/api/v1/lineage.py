"""Lineage API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import Optional

from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models import (
    ColumnModel,
    ColumnLineageModel,
    DatasetModel,
)
from app.presentation.schemas.lineage import (
    LineageGraphResponse,
    DatasetSchema,
    ColumnSchema,
    LineageEdgeSchema,
)

router = APIRouter(prefix="/lineage")


@router.get(
    "/column/{column_id}",
    response_model=LineageGraphResponse,
    summary="Get column lineage graph"
)
async def get_column_lineage(
    column_id: UUID,
    direction: str = Query("both", regex="^(upstream|downstream|both)$"),
    depth: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db)
):
    """
    Get column-level lineage graph for a specific column.

    - **column_id**: UUID of the column
    - **direction**: 'upstream' (sources), 'downstream' (targets), or 'both'
    - **depth**: How many hops to traverse (1-10)

    Returns a graph with datasets and lineage edges.
    """
    # Verify column exists
    result = await db.execute(
        select(ColumnModel).where(ColumnModel.id == column_id)
    )
    root_column = result.scalar_one_or_none()

    if not root_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column {column_id} not found"
        )

    # Collect all related columns and edges
    visited_columns = set()
    edges_map = {}
    datasets_map = {}

    async def traverse_lineage(col_id: UUID, current_depth: int, is_upstream: bool):
        """Recursively traverse lineage."""
        if current_depth > depth or col_id in visited_columns:
            return

        visited_columns.add(col_id)

        if is_upstream:
            # Get upstream lineage (sources)
            result = await db.execute(
                select(ColumnLineageModel)
                .where(ColumnLineageModel.target_column_id == col_id)
            )
            lineages = result.scalars().all()

            for lineage in lineages:
                edges_map[lineage.id] = lineage
                await traverse_lineage(lineage.source_column_id, current_depth + 1, True)
        else:
            # Get downstream lineage (targets)
            result = await db.execute(
                select(ColumnLineageModel)
                .where(ColumnLineageModel.source_column_id == col_id)
            )
            lineages = result.scalars().all()

            for lineage in lineages:
                edges_map[lineage.id] = lineage
                await traverse_lineage(lineage.target_column_id, current_depth + 1, False)

    # Traverse based on direction
    if direction in ["upstream", "both"]:
        await traverse_lineage(column_id, 1, True)

    if direction in ["downstream", "both"]:
        await traverse_lineage(column_id, 1, False)

    # Add root column
    visited_columns.add(column_id)

    # Fetch all columns with their datasets
    if visited_columns:
        result = await db.execute(
            select(ColumnModel)
            .options(selectinload(ColumnModel.dataset))
            .where(ColumnModel.id.in_(visited_columns))
        )
        columns = result.scalars().all()

        # Group columns by dataset
        for column in columns:
            dataset = column.dataset
            if dataset.id not in datasets_map:
                datasets_map[dataset.id] = {
                    'dataset': dataset,
                    'columns': []
                }
            datasets_map[dataset.id]['columns'].append(column)

    # Build response
    datasets = []
    for dataset_data in datasets_map.values():
        dataset = dataset_data['dataset']
        columns = dataset_data['columns']

        datasets.append(DatasetSchema(
            id=dataset.id,
            name=dataset.name,
            schema_name=dataset.schema_name,
            fully_qualified_name=dataset.fully_qualified_name,
            source_type=dataset.metadata.get('source_type', 'unknown'),
            columns=[
                ColumnSchema(
                    id=col.id,
                    name=col.name,
                    data_type=col.data_type,
                    is_primary_key=col.is_primary_key
                )
                for col in columns
            ]
        ))

    edges = [
        LineageEdgeSchema(
            id=edge.id,
            source_column_id=edge.source_column_id,
            target_column_id=edge.target_column_id,
            expression=edge.expression,
            confidence=edge.confidence
        )
        for edge in edges_map.values()
    ]

    return LineageGraphResponse(
        datasets=datasets,
        edges=edges,
        metadata={
            "root_column_id": str(column_id),
            "direction": direction,
            "depth": depth,
            "total_columns": len(visited_columns),
            "total_edges": len(edges)
        }
    )


@router.get(
    "/table/{dataset_id}",
    response_model=LineageGraphResponse,
    summary="Get table-level lineage"
)
async def get_table_lineage(
    dataset_id: UUID,
    direction: str = Query("both", regex="^(upstream|downstream|both)$"),
    depth: int = Query(3, ge=1, le=5),
    db: AsyncSession = Depends(get_db)
):
    """
    Get table-level lineage (aggregated from column lineage).

    This shows which tables are related, without column-level detail.
    """
    # Verify dataset exists
    result = await db.execute(
        select(DatasetModel).where(DatasetModel.id == dataset_id)
    )
    root_dataset = result.scalar_one_or_none()

    if not root_dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found"
        )

    # TODO: Implement table-level lineage traversal
    # For now, return minimal response
    return LineageGraphResponse(
        datasets=[
            DatasetSchema(
                id=root_dataset.id,
                name=root_dataset.name,
                schema_name=root_dataset.schema_name,
                fully_qualified_name=root_dataset.fully_qualified_name,
                source_type=root_dataset.metadata.get('source_type', 'unknown'),
                columns=[]
            )
        ],
        edges=[],
        metadata={
            "root_dataset_id": str(dataset_id),
            "direction": direction,
            "depth": depth
        }
    )
