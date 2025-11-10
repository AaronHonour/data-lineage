"""
Pytest configuration and global fixtures.

Provides fixtures for API testing, database setup, and authentication.
"""
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models import Base
from app.main import app
from app.infrastructure.database.models import (
    DataSourceModel,
    DatasetModel,
    ColumnModel,
    TransformationModel,
    ColumnLineageModel,
)


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sync_client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """Create a synchronous test client for non-async tests."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_token() -> str:
    """Generate a valid JWT token for testing."""
    from datetime import timedelta
    from app.presentation.api.v1.auth import create_access_token

    access_token = create_access_token(
        data={"sub": "admin"},
        expires_delta=timedelta(minutes=30)
    )
    return access_token


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Create authentication headers with JWT token."""
    return {
        "Authorization": f"Bearer {auth_token}"
    }


@pytest.fixture
async def sample_data_source(db_session: AsyncSession) -> DataSourceModel:
    """Create a sample data source for testing."""
    from uuid import uuid4

    data_source = DataSourceModel(
        id=str(uuid4()),
        name="test_postgres",
        source_type="postgres",
        connection_config={
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "username": "test",
            "password": "test"
        },
        description="Test PostgreSQL source"
    )

    db_session.add(data_source)
    await db_session.commit()
    await db_session.refresh(data_source)

    return data_source


@pytest.fixture
async def sample_dataset(
    db_session: AsyncSession,
    sample_data_source: DataSourceModel
) -> DatasetModel:
    """Create a sample dataset for testing."""
    from uuid import uuid4

    dataset = DatasetModel(
        id=str(uuid4()),
        data_source_id=sample_data_source.id,
        name="customers",
        schema_name="public",
        dataset_type="table",
        description="Customer table"
    )

    db_session.add(dataset)
    await db_session.commit()
    await db_session.refresh(dataset)

    return dataset


@pytest.fixture
async def sample_columns(
    db_session: AsyncSession,
    sample_dataset: DatasetModel
) -> list[ColumnModel]:
    """Create sample columns for testing."""
    from uuid import uuid4

    columns = [
        ColumnModel(
            id=str(uuid4()),
            dataset_id=sample_dataset.id,
            name="customer_id",
            data_type="INTEGER",
            ordinal_position=1,
            is_nullable=False,
            description="Primary key"
        ),
        ColumnModel(
            id=str(uuid4()),
            dataset_id=sample_dataset.id,
            name="email",
            data_type="VARCHAR",
            ordinal_position=2,
            is_nullable=False,
            description="Customer email"
        ),
        ColumnModel(
            id=str(uuid4()),
            dataset_id=sample_dataset.id,
            name="created_at",
            data_type="TIMESTAMP",
            ordinal_position=3,
            is_nullable=True,
            description="Creation timestamp"
        ),
    ]

    for column in columns:
        db_session.add(column)

    await db_session.commit()

    for column in columns:
        await db_session.refresh(column)

    return columns


@pytest.fixture
async def sample_lineage_graph(
    db_session: AsyncSession,
    sample_data_source: DataSourceModel
) -> tuple[list[DatasetModel], list[ColumnLineageModel]]:
    """Create a sample lineage graph for testing.

    Graph structure (table-level):
    raw_events -> stg_events -> fact_orders

    With columns:
    raw_events.event_id -> stg_events.event_id -> fact_orders.order_id
    """
    from uuid import uuid4

    # Create datasets
    raw_events = DatasetModel(
        id=str(uuid4()),
        data_source_id=sample_data_source.id,
        name="raw_events",
        schema_name="raw",
        dataset_type="table"
    )

    stg_events = DatasetModel(
        id=str(uuid4()),
        data_source_id=sample_data_source.id,
        name="stg_events",
        schema_name="staging",
        dataset_type="view"
    )

    fact_orders = DatasetModel(
        id=str(uuid4()),
        data_source_id=sample_data_source.id,
        name="fact_orders",
        schema_name="analytics",
        dataset_type="table"
    )

    datasets = [raw_events, stg_events, fact_orders]
    for dataset in datasets:
        db_session.add(dataset)

    await db_session.commit()

    for dataset in datasets:
        await db_session.refresh(dataset)

    # Create columns for each dataset
    col_raw_event_id = ColumnModel(
        id=str(uuid4()),
        dataset_id=raw_events.id,
        name="event_id",
        data_type="INTEGER",
        ordinal_position=1,
        is_nullable=False
    )

    col_stg_event_id = ColumnModel(
        id=str(uuid4()),
        dataset_id=stg_events.id,
        name="event_id",
        data_type="INTEGER",
        ordinal_position=1,
        is_nullable=False
    )

    col_fact_order_id = ColumnModel(
        id=str(uuid4()),
        dataset_id=fact_orders.id,
        name="order_id",
        data_type="INTEGER",
        ordinal_position=1,
        is_nullable=False
    )

    columns = [col_raw_event_id, col_stg_event_id, col_fact_order_id]
    for column in columns:
        db_session.add(column)

    await db_session.commit()

    for column in columns:
        await db_session.refresh(column)

    # Create column lineage edges
    lineage1 = ColumnLineageModel(
        id=str(uuid4()),
        source_column_id=col_raw_event_id.id,
        target_column_id=col_stg_event_id.id,
        expression="event_id",
        confidence=1.0
    )

    lineage2 = ColumnLineageModel(
        id=str(uuid4()),
        source_column_id=col_stg_event_id.id,
        target_column_id=col_fact_order_id.id,
        expression="event_id",
        confidence=1.0
    )

    lineage_edges = [lineage1, lineage2]
    for edge in lineage_edges:
        db_session.add(edge)

    await db_session.commit()

    for edge in lineage_edges:
        await db_session.refresh(edge)

    return datasets, lineage_edges


@pytest.fixture
def mock_postgres_connector():
    """Create a mock PostgreSQL connector for testing."""
    connector = AsyncMock()
    connector.test_connection.return_value = True
    connector.discover_datasets.return_value = [
        {
            "name": "customers",
            "schema_name": "public",
            "dataset_type": "table",
            "columns": [
                {
                    "name": "id",
                    "data_type": "INTEGER",
                    "ordinal_position": 1,
                    "is_nullable": False
                }
            ]
        }
    ]
    return connector


@pytest.fixture
def mock_lineage_sync_service():
    """Create a mock LineageSyncService for testing."""
    service = AsyncMock()
    service.sync_data_source.return_value = {
        "job_id": "test-job-123",
        "status": "completed",
        "datasets_discovered": 5,
        "transformations_parsed": 10
    }
    return service
