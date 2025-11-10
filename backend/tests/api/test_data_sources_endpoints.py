"""
Tests for data sources endpoints.

Covers:
- Create data source (success and error cases)
- List data sources
- Get single data source
- Update data source
- Delete data source
- Trigger sync
- Get sync job history
- Error handling and validation
"""
import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch, AsyncMock
from uuid import uuid4


class TestDataSourcesEndpoints:
    """Test data sources CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_data_source_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test successful data source creation."""
        with patch('app.infrastructure.connectors.factory.ConnectorFactory.create') as mock_factory:
            # Mock connector
            mock_connector = AsyncMock()
            mock_connector.test_connection.return_value = True
            mock_connector.close.return_value = None
            mock_factory.return_value = mock_connector

            response = await client.post(
                "/api/v1/data-sources",
                headers=auth_headers,
                json={
                    "name": "test_postgres",
                    "type": "postgres",
                    "connection_config": {
                        "host": "localhost",
                        "port": 5432,
                        "database": "testdb",
                        "username": "test",
                        "password": "test"
                    },
                    "description": "Test database"
                }
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()

            assert "id" in data
            assert data["name"] == "test_postgres"
            assert data["source_type"] == "postgres"
            assert data["status"] == "active"
            assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_data_source_invalid_type(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test creating data source with invalid type."""
        response = await client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "test_invalid",
                "type": "invalid_type",
                "connection_config": {}
            }
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid source type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_data_source_duplicate_name(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_data_source
    ):
        """Test creating data source with duplicate name."""
        with patch('app.infrastructure.connectors.factory.ConnectorFactory.create') as mock_factory:
            mock_connector = AsyncMock()
            mock_connector.test_connection.return_value = True
            mock_connector.close.return_value = None
            mock_factory.return_value = mock_connector

            response = await client.post(
                "/api/v1/data-sources",
                headers=auth_headers,
                json={
                    "name": sample_data_source.name,  # Duplicate name
                    "type": "postgres",
                    "connection_config": {}
                }
            )

            assert response.status_code == status.HTTP_409_CONFLICT
            assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_data_source_connection_failure(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test creating data source with connection test failure."""
        with patch('app.infrastructure.connectors.factory.ConnectorFactory.create') as mock_factory:
            mock_connector = AsyncMock()
            mock_connector.test_connection.side_effect = Exception("Connection refused")
            mock_factory.return_value = mock_connector

            response = await client.post(
                "/api/v1/data-sources",
                headers=auth_headers,
                json={
                    "name": "test_postgres",
                    "type": "postgres",
                    "connection_config": {
                        "host": "invalid_host",
                        "port": 5432
                    }
                }
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Connection test failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_data_source_missing_fields(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test creating data source with missing required fields."""
        response = await client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "test_source"
                # Missing type and connection_config
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_list_data_sources_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test listing data sources when none exist."""
        response = await client.get(
            "/api/v1/data-sources",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_data_sources_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_data_source
    ):
        """Test listing data sources."""
        response = await client.get(
            "/api/v1/data-sources",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == sample_data_source.name

    @pytest.mark.asyncio
    async def test_get_data_source_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_data_source
    ):
        """Test getting a specific data source."""
        response = await client.get(
            f"/api/v1/data-sources/{sample_data_source.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_data_source.id
        assert data["name"] == sample_data_source.name

    @pytest.mark.asyncio
    async def test_get_data_source_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test getting non-existent data source."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/data-sources/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_data_source_invalid_uuid(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test getting data source with invalid UUID format."""
        response = await client.get(
            "/api/v1/data-sources/invalid-uuid",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_data_source_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_data_source
    ):
        """Test updating data source."""
        response = await client.put(
            f"/api/v1/data-sources/{sample_data_source.id}",
            headers=auth_headers,
            json={
                "name": "updated_postgres",
                "description": "Updated description"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "updated_postgres"

    @pytest.mark.asyncio
    async def test_update_data_source_partial(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_data_source
    ):
        """Test partial update of data source."""
        original_name = sample_data_source.name

        response = await client.put(
            f"/api/v1/data-sources/{sample_data_source.id}",
            headers=auth_headers,
            json={
                "status": "inactive"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "inactive"
        assert data["name"] == original_name  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_update_data_source_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test updating non-existent data source."""
        fake_id = str(uuid4())
        response = await client.put(
            f"/api/v1/data-sources/{fake_id}",
            headers=auth_headers,
            json={"name": "new_name"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_data_source_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_data_source
    ):
        """Test deleting data source."""
        response = await client.delete(
            f"/api/v1/data-sources/{sample_data_source.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        get_response = await client.get(
            f"/api/v1/data-sources/{sample_data_source.id}",
            headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_data_source_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test deleting non-existent data source."""
        fake_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/data-sources/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_trigger_sync_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_data_source
    ):
        """Test triggering metadata sync."""
        with patch('app.application.services.lineage_sync_service.LineageSyncService.sync_data_source') as mock_sync:
            mock_sync.return_value = {
                "datasets_discovered": 5,
                "columns_discovered": 25,
                "transformations_discovered": 3,
                "lineage_edges_created": 10
            }

            response = await client.post(
                f"/api/v1/data-sources/{sample_data_source.id}/sync",
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_202_ACCEPTED
            data = response.json()
            assert "message" in data
            assert "stats" in data
            assert data["stats"]["datasets_discovered"] == 5

    @pytest.mark.asyncio
    async def test_trigger_sync_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test triggering sync for non-existent data source."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/data-sources/{fake_id}/sync",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_trigger_sync_failure(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_data_source
    ):
        """Test sync failure handling."""
        with patch('app.application.services.lineage_sync_service.LineageSyncService.sync_data_source') as mock_sync:
            mock_sync.side_effect = Exception("Database connection failed")

            response = await client.post(
                f"/api/v1/data-sources/{sample_data_source.id}/sync",
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Sync failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_sync_jobs_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_data_source
    ):
        """Test getting sync jobs when none exist."""
        response = await client.get(
            f"/api/v1/data-sources/{sample_data_source.id}/sync-jobs",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["source_id"] == sample_data_source.id
        assert data["jobs"] == []

    @pytest.mark.asyncio
    async def test_get_sync_jobs_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str]
    ):
        """Test getting sync jobs for non-existent data source."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/data-sources/{fake_id}/sync-jobs",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_data_source_without_auth(self, client: AsyncClient):
        """Test all endpoints require authentication."""
        endpoints = [
            ("GET", "/api/v1/data-sources"),
            ("POST", "/api/v1/data-sources"),
            ("GET", f"/api/v1/data-sources/{uuid4()}"),
            ("PUT", f"/api/v1/data-sources/{uuid4()}"),
            ("DELETE", f"/api/v1/data-sources/{uuid4()}"),
        ]

        for method, url in endpoints:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, json={})
            elif method == "PUT":
                response = await client.put(url, json={})
            elif method == "DELETE":
                response = await client.delete(url)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED, \
                f"{method} {url} should require authentication"
