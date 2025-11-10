"""Lineage synchronization service."""
from typing import Optional, Dict, Set, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.domain.entities.data_source import DataSource, DataSourceType
from app.infrastructure.connectors.factory import ConnectorFactory
from app.infrastructure.connectors.base import (
    DatasetMetadata,
    TransformationMetadata,
    ColumnMetadata as ConnectorColumnMetadata,
)
from app.infrastructure.parsers.sql_parser import SQLLineageExtractor, ColumnLineageResult
from app.infrastructure.parsers.pandas_extractor import PandasLineageExtractor
from app.infrastructure.parsers.polars_extractor import PolarsLineageExtractor
from app.infrastructure.parsers.pyspark_extractor import PySparkLineageExtractor
from app.infrastructure.database.models import (
    DataSourceModel,
    DatasetModel,
    ColumnModel,
    TransformationModel,
    ColumnLineageModel,
    SyncJobModel,
)
from app.domain.entities import Dataset, Column, Transformation, ColumnLineage
from app.domain.entities.dataset import DatasetType as DomainDatasetType
from app.domain.entities.transformation import TransformationType, TransformationLanguage


class LineageSyncService:
    """
    Service for synchronizing data source metadata and building lineage graph.

    This is the orchestration layer that:
    1. Discovers datasets and columns from data sources
    2. Discovers transformations (SQL views, dbt models, Python scripts)
    3. Parses transformation code to extract column-level lineage
    4. Resolves column references (FQN → column ID)
    5. Builds the global lineage graph in the database
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
        self.sql_parser = SQLLineageExtractor()

    async def sync_data_source(self, source_id: UUID) -> Dict[str, any]:
        """
        Synchronize a data source: discover metadata and build lineage.

        Args:
            source_id: UUID of the data source to sync

        Returns:
            Dictionary with sync statistics

        Raises:
            ValueError: If data source not found
            Exception: If sync fails
        """
        # Start sync job
        sync_job = await self._start_sync_job(source_id)

        try:
            # Get data source
            data_source = await self._get_data_source(source_id)

            if not data_source:
                raise ValueError(f"Data source {source_id} not found")

            # Create connector
            connector = ConnectorFactory.create(
                data_source.type.value,
                data_source.connection_config
            )

            stats = {
                'datasets_discovered': 0,
                'columns_discovered': 0,
                'transformations_discovered': 0,
                'lineage_edges_created': 0,
                'errors': []
            }

            try:
                # Step 1: Discover and save datasets
                datasets_map = await self._discover_and_save_datasets(
                    connector, source_id, stats
                )

                # Step 2: Discover and save transformations
                transformations = await self._discover_and_save_transformations(
                    connector, source_id, datasets_map, stats
                )

                # Step 3: Extract and save column lineage
                await self._extract_and_save_lineage(
                    transformations, datasets_map, stats
                )

                # Step 4: Update data source sync time
                await self._mark_source_synced(source_id)

                # Commit transaction
                await self.db.commit()

                # Complete sync job
                await self._complete_sync_job(sync_job.id, stats)

            finally:
                await connector.close()

            return stats

        except Exception as e:
            # Rollback transaction
            await self.db.rollback()

            # Mark sync job as failed
            await self._fail_sync_job(sync_job.id, str(e))

            raise

    async def _discover_and_save_datasets(
        self,
        connector,
        source_id: UUID,
        stats: Dict[str, any]
    ) -> Dict[str, UUID]:
        """
        Discover datasets from connector and save to database.

        Returns:
            Dictionary mapping FQN → dataset_id
        """
        datasets_map = {}

        async for dataset_meta in connector.discover_datasets():
            try:
                # Check if dataset already exists
                result = await self.db.execute(
                    select(DatasetModel).where(
                        DatasetModel.fully_qualified_name == dataset_meta.fully_qualified_name
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing dataset
                    dataset_model = existing
                    dataset_model.name = dataset_meta.name
                    dataset_model.schema_name = dataset_meta.schema_name
                    dataset_model.type = dataset_meta.type
                    dataset_model.extra_metadata = dataset_meta.metadata
                    dataset_model.last_synced_at = datetime.utcnow()
                    dataset_model.updated_at = datetime.utcnow()
                else:
                    # Create new dataset
                    dataset_entity = Dataset(
                        data_source_id=source_id,
                        fully_qualified_name=dataset_meta.fully_qualified_name,
                        name=dataset_meta.name,
                        schema_name=dataset_meta.schema_name,
                        type=DomainDatasetType(dataset_meta.type),
                        metadata=dataset_meta.metadata,
                        last_synced_at=datetime.utcnow()
                    )
                    dataset_model = DatasetModel.from_entity(dataset_entity)
                    self.db.add(dataset_model)

                # Flush to get dataset ID
                await self.db.flush()
                await self.db.refresh(dataset_model)

                datasets_map[dataset_meta.fully_qualified_name] = dataset_model.id

                # Save columns
                await self._save_columns(dataset_model.id, dataset_meta.columns, stats)

                stats['datasets_discovered'] += 1

            except Exception as e:
                stats['errors'].append(f"Error saving dataset {dataset_meta.fully_qualified_name}: {e}")

        return datasets_map

    async def _save_columns(
        self,
        dataset_id: UUID,
        columns: List[ConnectorColumnMetadata],
        stats: Dict[str, any]
    ) -> None:
        """Save columns for a dataset."""
        # Get existing columns
        result = await self.db.execute(
            select(ColumnModel).where(ColumnModel.dataset_id == dataset_id)
        )
        existing_columns = {col.name: col for col in result.scalars().all()}

        for col_meta in columns:
            try:
                if col_meta.name in existing_columns:
                    # Update existing column
                    col_model = existing_columns[col_meta.name]
                    col_model.data_type = col_meta.data_type
                    col_model.ordinal_position = col_meta.ordinal_position
                    col_model.is_nullable = col_meta.is_nullable
                    col_model.is_primary_key = col_meta.is_primary_key
                    col_model.updated_at = datetime.utcnow()
                else:
                    # Create new column
                    col_entity = Column(
                        dataset_id=dataset_id,
                        name=col_meta.name,
                        data_type=col_meta.data_type,
                        ordinal_position=col_meta.ordinal_position,
                        is_nullable=col_meta.is_nullable,
                        is_primary_key=col_meta.is_primary_key
                    )
                    col_model = ColumnModel.from_entity(col_entity)
                    self.db.add(col_model)

                stats['columns_discovered'] += 1

            except Exception as e:
                stats['errors'].append(f"Error saving column {col_meta.name}: {e}")

    async def _discover_and_save_transformations(
        self,
        connector,
        source_id: UUID,
        datasets_map: Dict[str, UUID],
        stats: Dict[str, any]
    ) -> List[Tuple[TransformationModel, TransformationMetadata]]:
        """
        Discover transformations and save to database.

        Returns:
            List of (transformation_model, transformation_metadata) tuples
        """
        transformations = []

        async for trans_meta in connector.discover_transformations():
            try:
                # Resolve target dataset ID
                target_dataset_id = datasets_map.get(trans_meta.target_fqn)

                if not target_dataset_id:
                    stats['errors'].append(f"Target dataset not found: {trans_meta.target_fqn}")
                    continue

                # Resolve source dataset IDs
                source_dataset_ids = []
                for source_fqn in trans_meta.source_fqns:
                    source_id = datasets_map.get(source_fqn)
                    if source_id:
                        source_dataset_ids.append(source_id)
                    else:
                        # Source might be from different data source - try to find it
                        result = await self.db.execute(
                            select(DatasetModel.id).where(
                                DatasetModel.fully_qualified_name == source_fqn
                            )
                        )
                        found_id = result.scalar_one_or_none()
                        if found_id:
                            source_dataset_ids.append(found_id)

                # Check if transformation already exists
                result = await self.db.execute(
                    select(TransformationModel).where(
                        TransformationModel.target_dataset_id == target_dataset_id
                    ).where(
                        TransformationModel.code == trans_meta.code
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing transformation
                    trans_model = existing
                    trans_model.source_dataset_ids = source_dataset_ids
                    trans_model.dialect = trans_meta.dialect
                    trans_model.updated_at = datetime.utcnow()
                else:
                    # Create new transformation
                    trans_entity = Transformation(
                        source_dataset_ids=source_dataset_ids,
                        target_dataset_id=target_dataset_id,
                        code=trans_meta.code,
                        language=TransformationLanguage(trans_meta.language),
                        dialect=trans_meta.dialect,
                        transformation_type=self._infer_transformation_type(trans_meta.type),
                        extracted_from=f"{trans_meta.type}_discovery"
                    )
                    trans_model = TransformationModel.from_entity(trans_entity)
                    self.db.add(trans_model)

                await self.db.flush()
                await self.db.refresh(trans_model)

                transformations.append((trans_model, trans_meta))
                stats['transformations_discovered'] += 1

            except Exception as e:
                stats['errors'].append(f"Error saving transformation for {trans_meta.target_fqn}: {e}")

        return transformations

    async def _extract_and_save_lineage(
        self,
        transformations: List[Tuple[TransformationModel, TransformationMetadata]],
        datasets_map: Dict[str, UUID],
        stats: Dict[str, any]
    ) -> None:
        """Extract column lineage from transformations and save to database."""
        for trans_model, trans_meta in transformations:
            try:
                # Parse transformation code based on language
                lineage_results = []

                if trans_meta.language == 'sql':
                    # Parse SQL
                    parser = SQLLineageExtractor(dialect=trans_meta.dialect)

                    # Build schema for parser (optional but improves accuracy)
                    schema = await self._build_schema_for_parser(
                        trans_model.source_dataset_ids
                    )

                    lineage_results = parser.extract_lineage(
                        trans_meta.code,
                        trans_meta.target_fqn,
                        schema=schema
                    )

                elif trans_meta.language == 'python':
                    # Detect Python library and use appropriate parser
                    parser = self._get_python_parser(trans_meta.code)
                    if parser:
                        lineage_results = parser.extract_lineage(
                            trans_meta.code,
                            trans_meta.target_fqn
                        )

                # Resolve column lineage to column IDs and save
                await self._save_column_lineage(
                    lineage_results,
                    trans_model.id,
                    stats
                )

            except Exception as e:
                stats['errors'].append(f"Error extracting lineage from transformation {trans_model.id}: {e}")

    async def _save_column_lineage(
        self,
        lineage_results: List[ColumnLineageResult],
        transformation_id: UUID,
        stats: Dict[str, any]
    ) -> None:
        """Resolve FQNs to column IDs and save lineage edges."""
        for result in lineage_results:
            try:
                # Resolve target column ID
                target_col_id = await self._resolve_column_fqn(result.target_column)

                if not target_col_id:
                    stats['errors'].append(f"Target column not found: {result.target_column}")
                    continue

                # Resolve each source column ID
                for source_fqn in result.source_columns:
                    source_col_id = await self._resolve_column_fqn(source_fqn)

                    if not source_col_id:
                        stats['errors'].append(f"Source column not found: {source_fqn}")
                        continue

                    # Check if lineage edge already exists
                    result_check = await self.db.execute(
                        select(ColumnLineageModel).where(
                            ColumnLineageModel.source_column_id == source_col_id
                        ).where(
                            ColumnLineageModel.target_column_id == target_col_id
                        ).where(
                            ColumnLineageModel.transformation_id == transformation_id
                        )
                    )
                    existing = result_check.scalar_one_or_none()

                    if not existing:
                        # Create new lineage edge
                        lineage_entity = ColumnLineage(
                            source_column_id=source_col_id,
                            target_column_id=target_col_id,
                            transformation_id=transformation_id,
                            expression=result.expression
                        )
                        lineage_model = ColumnLineageModel.from_entity(lineage_entity)
                        self.db.add(lineage_model)

                        stats['lineage_edges_created'] += 1

            except Exception as e:
                stats['errors'].append(f"Error saving lineage edge: {e}")

    async def _resolve_column_fqn(self, fqn: str) -> Optional[UUID]:
        """
        Resolve a column FQN to its database ID.

        FQN format: dataset_fqn.column_name
        Example: postgres.public.customers.customer_id
        """
        # Split FQN into dataset and column parts
        parts = fqn.rsplit('.', 1)
        if len(parts) != 2:
            return None

        dataset_fqn, column_name = parts

        # Find column by dataset FQN and column name
        result = await self.db.execute(
            select(ColumnModel.id)
            .join(DatasetModel)
            .where(DatasetModel.fully_qualified_name == dataset_fqn)
            .where(ColumnModel.name == column_name)
        )

        return result.scalar_one_or_none()

    async def _build_schema_for_parser(
        self,
        dataset_ids: List[UUID]
    ) -> Dict[str, Dict[str, str]]:
        """Build schema dictionary for SQL parser."""
        schema = {}

        for dataset_id in dataset_ids:
            # Get dataset and columns
            result = await self.db.execute(
                select(DatasetModel)
                .options(selectinload(DatasetModel.columns))
                .where(DatasetModel.id == dataset_id)
            )
            dataset = result.scalar_one_or_none()

            if dataset:
                # Add table schema
                table_name = dataset.name
                schema[table_name] = {
                    col.name: col.data_type
                    for col in dataset.columns
                }

        return schema

    def _get_python_parser(self, code: str):
        """Detect Python library from code and return appropriate parser."""
        if 'pandas' in code or 'pd.' in code:
            return PandasLineageExtractor()
        elif 'polars' in code or 'pl.' in code:
            return PolarsLineageExtractor()
        elif 'pyspark' in code or 'spark.' in code:
            return PySparkLineageExtractor()
        return None

    def _infer_transformation_type(self, type_str: str) -> Optional[TransformationType]:
        """Infer transformation type from string."""
        type_map = {
            'view': TransformationType.VIEW,
            'materialized_view': TransformationType.MATERIALIZED_VIEW,
            'table': TransformationType.TABLE,
        }
        return type_map.get(type_str)

    async def _get_data_source(self, source_id: UUID) -> Optional[DataSource]:
        """Get data source entity from database."""
        result = await self.db.execute(
            select(DataSourceModel).where(DataSourceModel.id == source_id)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def _mark_source_synced(self, source_id: UUID) -> None:
        """Mark data source as synced."""
        result = await self.db.execute(
            select(DataSourceModel).where(DataSourceModel.id == source_id)
        )
        model = result.scalar_one_or_none()

        if model:
            model.last_sync_at = datetime.utcnow()
            model.status = 'active'
            model.updated_at = datetime.utcnow()

    async def _start_sync_job(self, source_id: UUID) -> SyncJobModel:
        """Create and start a sync job."""
        sync_job = SyncJobModel(
            data_source_id=source_id,
            status='running',
            started_at=datetime.utcnow()
        )
        self.db.add(sync_job)
        await self.db.flush()
        await self.db.refresh(sync_job)
        return sync_job

    async def _complete_sync_job(self, job_id: UUID, stats: Dict[str, any]) -> None:
        """Mark sync job as completed."""
        result = await self.db.execute(
            select(SyncJobModel).where(SyncJobModel.id == job_id)
        )
        job = result.scalar_one_or_none()

        if job:
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.stats = stats
            await self.db.commit()

    async def _fail_sync_job(self, job_id: UUID, error: str) -> None:
        """Mark sync job as failed."""
        result = await self.db.execute(
            select(SyncJobModel).where(SyncJobModel.id == job_id)
        )
        job = result.scalar_one_or_none()

        if job:
            job.status = 'failed'
            job.completed_at = datetime.utcnow()
            job.error_message = error
            await self.db.commit()
