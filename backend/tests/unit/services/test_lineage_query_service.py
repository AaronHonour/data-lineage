"""
Tests for LineageQueryService.

Covers:
- Table-level lineage aggregation
- Impact analysis (downstream traversal)
- Root cause analysis (upstream traversal)
- Lineage statistics
- Direction and depth parameters
- Edge cases and error handling
"""
import pytest
from uuid import uuid4

from app.application.services.lineage_query_service import LineageQueryService
from app.domain.models.column_lineage import ColumnLineageModel


class TestLineageQueryService:
    """Test LineageQueryService methods."""

    @pytest.mark.asyncio
    async def test_get_table_lineage_not_found(self, db_session):
        """Test getting table lineage for non-existent dataset."""
        service = LineageQueryService(db_session)
        fake_id = uuid4()

        result = await service.get_table_lineage(fake_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_table_lineage_exists_no_edges(
        self,
        db_session,
        sample_dataset
    ):
        """Test getting table lineage for dataset with no lineage edges."""
        service = LineageQueryService(db_session)

        result = await service.get_table_lineage(sample_dataset.id)

        assert result is not None
        assert "datasets" in result
        assert "edges" in result
        assert "metadata" in result
        assert result["metadata"]["root_dataset_id"] == str(sample_dataset.id)
        assert result["metadata"]["total_datasets"] == 1
        assert result["metadata"]["total_edges"] == 0

    @pytest.mark.asyncio
    async def test_get_table_lineage_with_graph(
        self,
        db_session,
        sample_lineage_graph
    ):
        """Test getting table lineage for connected datasets."""
        service = LineageQueryService(db_session)
        datasets, edges = sample_lineage_graph

        # Query from first dataset (raw_events)
        result = await service.get_table_lineage(datasets[0].id)

        assert result is not None
        assert len(result["datasets"]) >= 1
        assert result["metadata"]["root_dataset_id"] == str(datasets[0].id)

    @pytest.mark.asyncio
    async def test_get_table_lineage_direction_upstream(
        self,
        db_session,
        sample_lineage_graph
    ):
        """Test table lineage with upstream direction."""
        service = LineageQueryService(db_session)
        datasets, edges = sample_lineage_graph

        # Query from middle dataset (stg_events) with upstream
        result = await service.get_table_lineage(
            datasets[1].id,
            direction="upstream"
        )

        assert result is not None
        assert result["metadata"]["direction"] == "upstream"
        # Should include raw_events (upstream) and stg_events itself
        assert len(result["datasets"]) >= 1

    @pytest.mark.asyncio
    async def test_get_table_lineage_direction_downstream(
        self,
        db_session,
        sample_lineage_graph
    ):
        """Test table lineage with downstream direction."""
        service = LineageQueryService(db_session)
        datasets, edges = sample_lineage_graph

        # Query from first dataset (raw_events) with downstream
        result = await service.get_table_lineage(
            datasets[0].id,
            direction="downstream"
        )

        assert result is not None
        assert result["metadata"]["direction"] == "downstream"
        # Should include downstream datasets
        assert len(result["datasets"]) >= 1

    @pytest.mark.asyncio
    async def test_get_table_lineage_direction_both(
        self,
        db_session,
        sample_lineage_graph
    ):
        """Test table lineage with both directions."""
        service = LineageQueryService(db_session)
        datasets, edges = sample_lineage_graph

        # Query from middle dataset with both directions
        result = await service.get_table_lineage(
            datasets[1].id,
            direction="both"
        )

        assert result is not None
        assert result["metadata"]["direction"] == "both"
        # Should include both upstream and downstream
        assert len(result["datasets"]) >= 2

    @pytest.mark.asyncio
    async def test_get_table_lineage_depth_limit(
        self,
        db_session,
        sample_lineage_graph
    ):
        """Test table lineage respects depth limit."""
        service = LineageQueryService(db_session)
        datasets, edges = sample_lineage_graph

        # Depth 1 - only immediate neighbors
        result_depth1 = await service.get_table_lineage(
            datasets[0].id,
            direction="downstream",
            depth=1
        )

        # Depth 3 - more hops
        result_depth3 = await service.get_table_lineage(
            datasets[0].id,
            direction="downstream",
            depth=3
        )

        assert result_depth1 is not None
        assert result_depth3 is not None

        # Higher depth should have equal or more datasets
        assert len(result_depth3["datasets"]) >= len(result_depth1["datasets"])

    @pytest.mark.asyncio
    async def test_get_table_lineage_edge_count(
        self,
        db_session,
        sample_lineage_graph
    ):
        """Test that table lineage edges include column count."""
        service = LineageQueryService(db_session)
        datasets, edges = sample_lineage_graph

        result = await service.get_table_lineage(datasets[0].id)

        if len(result["edges"]) > 0:
            edge = result["edges"][0]
            assert "source_dataset_id" in edge
            assert "target_dataset_id" in edge
            assert "column_count" in edge
            assert edge["column_count"] >= 0

    @pytest.mark.asyncio
    async def test_get_column_impact_analysis_no_downstream(
        self,
        db_session,
        sample_columns
    ):
        """Test impact analysis for column with no downstream dependencies."""
        service = LineageQueryService(db_session)
        column = sample_columns[0]

        result = await service.get_column_impact_analysis(column.id)

        assert result is not None
        assert result["root_column_id"] == str(column.id)
        assert result["total_impacted_columns"] >= 1  # At least includes itself
        assert result["total_impacted_datasets"] >= 0

    @pytest.mark.asyncio
    async def test_get_column_impact_analysis_with_depth(
        self,
        db_session,
        sample_columns
    ):
        """Test impact analysis with custom depth."""
        service = LineageQueryService(db_session)
        column = sample_columns[0]

        result = await service.get_column_impact_analysis(column.id, max_depth=5)

        assert result is not None
        assert "impacted_columns" in result
        assert isinstance(result["impacted_columns"], list)

    @pytest.mark.asyncio
    async def test_get_column_root_cause_analysis_no_upstream(
        self,
        db_session,
        sample_columns
    ):
        """Test root cause analysis for column with no upstream sources."""
        service = LineageQueryService(db_session)
        column = sample_columns[0]

        result = await service.get_column_root_cause_analysis(column.id)

        assert result is not None
        assert result["root_column_id"] == str(column.id)
        assert result["total_source_columns"] >= 1  # At least includes itself
        assert result["total_source_datasets"] >= 0

    @pytest.mark.asyncio
    async def test_get_column_root_cause_analysis_with_depth(
        self,
        db_session,
        sample_columns
    ):
        """Test root cause analysis with custom depth."""
        service = LineageQueryService(db_session)
        column = sample_columns[0]

        result = await service.get_column_root_cause_analysis(column.id, max_depth=5)

        assert result is not None
        assert "source_columns" in result
        assert isinstance(result["source_columns"], list)

    @pytest.mark.asyncio
    async def test_get_lineage_statistics_empty_database(self, db_session):
        """Test getting statistics from empty database."""
        service = LineageQueryService(db_session)

        result = await service.get_lineage_statistics()

        assert result is not None
        assert "total_datasets" in result
        assert "total_columns" in result
        assert "total_lineage_edges" in result
        assert "datasets_by_source_type" in result
        assert result["total_datasets"] == 0
        assert result["total_columns"] == 0
        assert result["total_lineage_edges"] == 0

    @pytest.mark.asyncio
    async def test_get_lineage_statistics_with_data(
        self,
        db_session,
        sample_dataset,
        sample_columns
    ):
        """Test getting statistics with data."""
        service = LineageQueryService(db_session)

        result = await service.get_lineage_statistics()

        assert result is not None
        assert result["total_datasets"] >= 1
        assert result["total_columns"] >= len(sample_columns)
        assert "average_edges_per_column" in result
        assert isinstance(result["average_edges_per_column"], (int, float))

    @pytest.mark.asyncio
    async def test_get_lineage_statistics_source_types(
        self,
        db_session,
        sample_lineage_graph
    ):
        """Test statistics includes source type breakdown."""
        service = LineageQueryService(db_session)

        result = await service.get_lineage_statistics()

        assert result is not None
        assert "datasets_by_source_type" in result
        assert isinstance(result["datasets_by_source_type"], dict)

    @pytest.mark.asyncio
    async def test_table_lineage_response_structure(
        self,
        db_session,
        sample_dataset
    ):
        """Test table lineage response has correct structure."""
        service = LineageQueryService(db_session)

        result = await service.get_table_lineage(sample_dataset.id)

        assert result is not None

        # Check datasets structure
        assert "datasets" in result
        assert isinstance(result["datasets"], list)
        if len(result["datasets"]) > 0:
            dataset = result["datasets"][0]
            assert "id" in dataset
            assert "name" in dataset
            assert "fully_qualified_name" in dataset

        # Check edges structure
        assert "edges" in result
        assert isinstance(result["edges"], list)

        # Check metadata
        assert "metadata" in result
        assert "root_dataset_id" in result["metadata"]
        assert "direction" in result["metadata"]
        assert "depth" in result["metadata"]
        assert "total_datasets" in result["metadata"]
        assert "total_edges" in result["metadata"]

    @pytest.mark.asyncio
    async def test_impact_analysis_response_structure(
        self,
        db_session,
        sample_columns
    ):
        """Test impact analysis response has correct structure."""
        service = LineageQueryService(db_session)
        column = sample_columns[0]

        result = await service.get_column_impact_analysis(column.id)

        assert result is not None
        assert "root_column_id" in result
        assert "impacted_columns" in result
        assert "total_impacted_columns" in result
        assert "total_impacted_datasets" in result

        # Check impacted columns structure
        assert isinstance(result["impacted_columns"], list)
        if len(result["impacted_columns"]) > 0:
            col_data = result["impacted_columns"][0]
            assert "column_id" in col_data
            assert "column_name" in col_data
            assert "dataset_id" in col_data
            assert "dataset_name" in col_data

    @pytest.mark.asyncio
    async def test_root_cause_analysis_response_structure(
        self,
        db_session,
        sample_columns
    ):
        """Test root cause analysis response has correct structure."""
        service = LineageQueryService(db_session)
        column = sample_columns[0]

        result = await service.get_column_root_cause_analysis(column.id)

        assert result is not None
        assert "root_column_id" in result
        assert "source_columns" in result
        assert "total_source_columns" in result
        assert "total_source_datasets" in result

        # Check source columns structure
        assert isinstance(result["source_columns"], list)
        if len(result["source_columns"]) > 0:
            col_data = result["source_columns"][0]
            assert "column_id" in col_data
            assert "column_name" in col_data
            assert "dataset_id" in col_data
            assert "dataset_name" in col_data
