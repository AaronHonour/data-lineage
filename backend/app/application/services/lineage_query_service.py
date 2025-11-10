"""Lineage query service for traversing and analyzing lineage graphs."""
from typing import Set, Dict, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models import (
    DatasetModel,
    ColumnModel,
    ColumnLineageModel,
)


class LineageQueryService:
    """
    Service for querying and traversing lineage graphs.

    Provides high-level operations for:
    - Column-level lineage traversal
    - Table-level lineage aggregation
    - Impact analysis
    - Root cause analysis
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    async def get_table_lineage(
        self,
        dataset_id: UUID,
        direction: str = 'both',
        depth: int = 3
    ) -> Dict[str, any]:
        """
        Get table-level lineage by aggregating column lineage.

        Args:
            dataset_id: UUID of the dataset
            direction: 'upstream', 'downstream', or 'both'
            depth: How many hops to traverse

        Returns:
            Dictionary with datasets and table-level edges
        """
        # Verify dataset exists
        result = await self.db.execute(
            select(DatasetModel)
            .options(selectinload(DatasetModel.columns))
            .where(DatasetModel.id == dataset_id)
        )
        root_dataset = result.scalar_one_or_none()

        if not root_dataset:
            return None

        # Collect related datasets through column lineage
        visited_datasets = set()
        dataset_relationships = {}  # (source_dataset_id, target_dataset_id) -> count

        async def traverse_dataset_lineage(ds_id: UUID, current_depth: int, is_upstream: bool):
            """Recursively traverse dataset lineage."""
            if current_depth > depth or ds_id in visited_datasets:
                return

            visited_datasets.add(ds_id)

            # Get all columns for this dataset
            result = await self.db.execute(
                select(ColumnModel.id).where(ColumnModel.dataset_id == ds_id)
            )
            column_ids = [row[0] for row in result.all()]

            if not column_ids:
                return

            if is_upstream:
                # Get upstream lineage (source columns)
                result = await self.db.execute(
                    select(
                        ColumnLineageModel.source_column_id,
                        ColumnModel.dataset_id
                    )
                    .join(
                        ColumnModel,
                        ColumnLineageModel.source_column_id == ColumnModel.id
                    )
                    .where(ColumnLineageModel.target_column_id.in_(column_ids))
                )

                for source_col_id, source_dataset_id in result.all():
                    # Record relationship
                    edge = (source_dataset_id, ds_id)
                    dataset_relationships[edge] = dataset_relationships.get(edge, 0) + 1

                    # Traverse upstream
                    await traverse_dataset_lineage(source_dataset_id, current_depth + 1, True)

            else:
                # Get downstream lineage (target columns)
                result = await self.db.execute(
                    select(
                        ColumnLineageModel.target_column_id,
                        ColumnModel.dataset_id
                    )
                    .join(
                        ColumnModel,
                        ColumnLineageModel.target_column_id == ColumnModel.id
                    )
                    .where(ColumnLineageModel.source_column_id.in_(column_ids))
                )

                for target_col_id, target_dataset_id in result.all():
                    # Record relationship
                    edge = (ds_id, target_dataset_id)
                    dataset_relationships[edge] = dataset_relationships.get(edge, 0) + 1

                    # Traverse downstream
                    await traverse_dataset_lineage(target_dataset_id, current_depth + 1, False)

        # Traverse based on direction
        if direction in ["upstream", "both"]:
            await traverse_dataset_lineage(dataset_id, 1, True)

        if direction in ["downstream", "both"]:
            await traverse_dataset_lineage(dataset_id, 1, False)

        # Add root dataset
        visited_datasets.add(dataset_id)

        # Fetch all datasets
        datasets_data = []
        if visited_datasets:
            result = await self.db.execute(
                select(DatasetModel)
                .where(DatasetModel.id.in_(visited_datasets))
            )
            datasets = result.scalars().all()

            datasets_data = [
                {
                    'id': str(ds.id),
                    'name': ds.name,
                    'schema_name': ds.schema_name,
                    'fully_qualified_name': ds.fully_qualified_name,
                    'type': ds.type,
                    'source_type': ds.extra_metadata.get('source_type', 'unknown')
                }
                for ds in datasets
            ]

        # Build edges with column count
        edges_data = [
            {
                'source_dataset_id': str(source_id),
                'target_dataset_id': str(target_id),
                'column_count': count
            }
            for (source_id, target_id), count in dataset_relationships.items()
        ]

        return {
            'datasets': datasets_data,
            'edges': edges_data,
            'metadata': {
                'root_dataset_id': str(dataset_id),
                'direction': direction,
                'depth': depth,
                'total_datasets': len(visited_datasets),
                'total_edges': len(edges_data)
            }
        }

    async def get_column_impact_analysis(
        self,
        column_id: UUID,
        max_depth: int = 10
    ) -> Dict[str, any]:
        """
        Get impact analysis for a column (all downstream dependencies).

        Args:
            column_id: UUID of the column to analyze
            max_depth: Maximum traversal depth

        Returns:
            Dictionary with impacted columns and datasets
        """
        impacted_columns = set()
        impacted_datasets = set()

        async def traverse_downstream(col_id: UUID, current_depth: int):
            """Recursively find all downstream columns."""
            if current_depth > max_depth or col_id in impacted_columns:
                return

            impacted_columns.add(col_id)

            # Get downstream columns
            result = await self.db.execute(
                select(ColumnLineageModel.target_column_id, ColumnModel.dataset_id)
                .join(
                    ColumnModel,
                    ColumnLineageModel.target_column_id == ColumnModel.id
                )
                .where(ColumnLineageModel.source_column_id == col_id)
            )

            for target_col_id, dataset_id in result.all():
                impacted_datasets.add(dataset_id)
                await traverse_downstream(target_col_id, current_depth + 1)

        # Start traversal
        await traverse_downstream(column_id, 1)

        # Get column details
        columns_data = []
        if impacted_columns:
            result = await self.db.execute(
                select(ColumnModel, DatasetModel)
                .join(DatasetModel)
                .where(ColumnModel.id.in_(impacted_columns))
            )

            for col, dataset in result.all():
                columns_data.append({
                    'column_id': str(col.id),
                    'column_name': col.name,
                    'dataset_id': str(dataset.id),
                    'dataset_name': dataset.fully_qualified_name
                })

        return {
            'root_column_id': str(column_id),
            'impacted_columns': columns_data,
            'total_impacted_columns': len(impacted_columns),
            'total_impacted_datasets': len(impacted_datasets)
        }

    async def get_column_root_cause_analysis(
        self,
        column_id: UUID,
        max_depth: int = 10
    ) -> Dict[str, any]:
        """
        Get root cause analysis for a column (all upstream sources).

        Args:
            column_id: UUID of the column to analyze
            max_depth: Maximum traversal depth

        Returns:
            Dictionary with source columns and datasets
        """
        source_columns = set()
        source_datasets = set()

        async def traverse_upstream(col_id: UUID, current_depth: int):
            """Recursively find all upstream columns."""
            if current_depth > max_depth or col_id in source_columns:
                return

            source_columns.add(col_id)

            # Get upstream columns
            result = await self.db.execute(
                select(ColumnLineageModel.source_column_id, ColumnModel.dataset_id)
                .join(
                    ColumnModel,
                    ColumnLineageModel.source_column_id == ColumnModel.id
                )
                .where(ColumnLineageModel.target_column_id == col_id)
            )

            for source_col_id, dataset_id in result.all():
                source_datasets.add(dataset_id)
                await traverse_upstream(source_col_id, current_depth + 1)

        # Start traversal
        await traverse_upstream(column_id, 1)

        # Get column details
        columns_data = []
        if source_columns:
            result = await self.db.execute(
                select(ColumnModel, DatasetModel)
                .join(DatasetModel)
                .where(ColumnModel.id.in_(source_columns))
            )

            for col, dataset in result.all():
                columns_data.append({
                    'column_id': str(col.id),
                    'column_name': col.name,
                    'dataset_id': str(dataset.id),
                    'dataset_name': dataset.fully_qualified_name
                })

        return {
            'root_column_id': str(column_id),
            'source_columns': columns_data,
            'total_source_columns': len(source_columns),
            'total_source_datasets': len(source_datasets)
        }

    async def get_lineage_statistics(self) -> Dict[str, any]:
        """Get overall lineage graph statistics."""
        # Count datasets
        result = await self.db.execute(select(DatasetModel.id))
        total_datasets = len(result.all())

        # Count columns
        result = await self.db.execute(select(ColumnModel.id))
        total_columns = len(result.all())

        # Count lineage edges
        result = await self.db.execute(select(ColumnLineageModel.id))
        total_edges = len(result.all())

        # Count by source type
        result = await self.db.execute(
            select(DatasetModel.extra_metadata)
        )
        source_types = {}
        for row in result.all():
            metadata = row[0] or {}
            source_type = metadata.get('source_type', 'unknown')
            source_types[source_type] = source_types.get(source_type, 0) + 1

        return {
            'total_datasets': total_datasets,
            'total_columns': total_columns,
            'total_lineage_edges': total_edges,
            'datasets_by_source_type': source_types,
            'average_edges_per_column': round(total_edges / total_columns, 2) if total_columns > 0 else 0
        }
