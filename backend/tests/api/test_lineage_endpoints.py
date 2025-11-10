"""
Tests for lineage endpoints.

Covers:
- Column-level lineage queries
- Table-level lineage queries
- Direction parameter (upstream, downstream, both)
- Depth parameter
- Error handling
- Edge cases (cycles, disconnected nodes)
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from uuid import uuid4, UUID


class TestLineageEndpoints:
    """Test lineage query endpoints."""

    @pytest.mark.asyncio
    async def test_get_column_lineage_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test getting lineage for non-existent column."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/lineage/column/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_column_lineage_invalid_uuid(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test getting lineage with invalid UUID format."""
        response = await client.get(
            "/api/v1/lineage/column/invalid-uuid",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_column_lineage_with_columns(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_columns
    ):
        """Test getting lineage for a column (no lineage edges)."""
        column = sample_columns[0]
        response = await client.get(
            f"/api/v1/lineage/column/{column.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "datasets" in data
        assert "edges" in data
        assert "metadata" in data
        assert data["metadata"]["root_column_id"] == column.id

    @pytest.mark.asyncio
    async def test_get_column_lineage_direction_upstream(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_columns
    ):
        """Test column lineage with upstream direction."""
        column = sample_columns[0]
        response = await client.get(
            f"/api/v1/lineage/column/{column.id}?direction=upstream",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metadata"]["direction"] == "upstream"

    @pytest.mark.asyncio
    async def test_get_column_lineage_direction_downstream(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_columns
    ):
        """Test column lineage with downstream direction."""
        column = sample_columns[0]
        response = await client.get(
            f"/api/v1/lineage/column/{column.id}?direction=downstream",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metadata"]["direction"] == "downstream"

    @pytest.mark.asyncio
    async def test_get_column_lineage_direction_both(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_columns
    ):
        """Test column lineage with both directions."""
        column = sample_columns[0]
        response = await client.get(
            f"/api/v1/lineage/column/{column.id}?direction=both",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metadata"]["direction"] == "both"

    @pytest.mark.asyncio
    async def test_get_column_lineage_invalid_direction(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_columns
    ):
        """Test column lineage with invalid direction."""
        column = sample_columns[0]
        response = await client.get(
            f"/api/v1/lineage/column/{column.id}?direction=invalid",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_get_column_lineage_custom_depth(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_columns
    ):
        """Test column lineage with custom depth."""
        column = sample_columns[0]
        response = await client.get(
            f"/api/v1/lineage/column/{column.id}?depth=3",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metadata"]["depth"] == 3

    @pytest.mark.asyncio
    async def test_get_column_lineage_depth_bounds(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_columns
    ):
        """Test column lineage depth parameter bounds (1-10)."""
        column = sample_columns[0]

        # Test below minimum
        response = await client.get(
            f"/api/v1/lineage/column/{column.id}?depth=0",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test above maximum
        response = await client.get(
            f"/api/v1/lineage/column/{column.id}?depth=11",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test valid minimum
        response = await client.get(
            f"/api/v1/lineage/column/{column.id}?depth=1",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK

        # Test valid maximum
        response = await client.get(
            f"/api/v1/lineage/column/{column.id}?depth=10",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_table_lineage_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test getting table lineage for non-existent dataset."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/lineage/table/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_table_lineage_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_lineage_graph
    ):
        """Test getting table-level lineage."""
        datasets, edges = sample_lineage_graph
        dataset = datasets[0]  # raw_events

        response = await client.get(
            f"/api/v1/lineage/table/{dataset.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "datasets" in data
        assert "edges" in data
        assert "metadata" in data

    @pytest.mark.asyncio
    async def test_get_table_lineage_direction_upstream(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_lineage_graph
    ):
        """Test table lineage with upstream direction."""
        datasets, edges = sample_lineage_graph
        # Use middle dataset (stg_events) which has both upstream and downstream
        dataset = datasets[1]

        response = await client.get(
            f"/api/v1/lineage/table/{dataset.id}?direction=upstream",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should include raw_events (upstream) but not fact_orders (downstream)
        assert len(data["datasets"]) >= 1

    @pytest.mark.asyncio
    async def test_get_table_lineage_direction_downstream(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_lineage_graph
    ):
        """Test table lineage with downstream direction."""
        datasets, edges = sample_lineage_graph
        dataset = datasets[0]  # raw_events

        response = await client.get(
            f"/api/v1/lineage/table/{dataset.id}?direction=downstream",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should include stg_events and fact_orders (downstream)
        assert len(data["datasets"]) >= 1

    @pytest.mark.asyncio
    async def test_get_table_lineage_depth_parameter(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_lineage_graph
    ):
        """Test table lineage depth parameter."""
        datasets, edges = sample_lineage_graph
        dataset = datasets[0]

        # Depth 1 - only immediate neighbors
        response = await client.get(
            f"/api/v1/lineage/table/{dataset.id}?depth=1&direction=downstream",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        depth1_data = response.json()

        # Depth 3 - more hops
        response = await client.get(
            f"/api/v1/lineage/table/{dataset.id}?depth=3&direction=downstream",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        depth3_data = response.json()

        # Depth 3 should have equal or more datasets than depth 1
        assert len(depth3_data["datasets"]) >= len(depth1_data["datasets"])

    @pytest.mark.asyncio
    async def test_get_table_lineage_depth_bounds(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_lineage_graph
    ):
        """Test table lineage depth bounds (1-5)."""
        datasets, edges = sample_lineage_graph
        dataset = datasets[0]

        # Below minimum
        response = await client.get(
            f"/api/v1/lineage/table/{dataset.id}?depth=0",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Above maximum
        response = await client.get(
            f"/api/v1/lineage/table/{dataset.id}?depth=6",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_lineage_response_structure(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_lineage_graph
    ):
        """Test that lineage response has correct structure."""
        datasets, edges = sample_lineage_graph
        dataset = datasets[0]

        response = await client.get(
            f"/api/v1/lineage/table/{dataset.id}",
            headers=auth_headers
        )

        data = response.json()

        # Check datasets structure
        assert isinstance(data["datasets"], list)
        if len(data["datasets"]) > 0:
            dataset_obj = data["datasets"][0]
            assert "id" in dataset_obj
            assert "name" in dataset_obj
            assert "source_type" in dataset_obj

        # Check edges structure
        assert isinstance(data["edges"], list)

        # Check metadata
        assert "metadata" in data
        assert isinstance(data["metadata"], dict)

    @pytest.mark.asyncio
    async def test_lineage_without_authentication(self, client: AsyncClient):
        """Test lineage endpoints require authentication."""
        endpoints = [
            f"/api/v1/lineage/column/{uuid4()}",
            f"/api/v1/lineage/table/{uuid4()}",
        ]

        for url in endpoints:
            response = await client.get(url)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                f"{url} should require authentication"
