# Data Lineage Tool - Technical Design Document

## Executive Summary

A production-grade data lineage tracking system that provides **column-level lineage** across heterogeneous data sources including PostgreSQL, MySQL, SQL Server, Apache Iceberg, and Delta Lake. The system automatically discovers metadata via APIs, parses SQL transformations, and visualizes lineage relationships through an interactive graph interface.

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Data Source Layer                      │
│  PostgreSQL │ MySQL │ SQL Server │ Iceberg │ Delta     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Connector Layer (Python)                   │
│  - SQLAlchemy connectors (RDBMS)                       │
│  - PyIceberg (Iceberg tables)                          │
│  - delta-rs (Delta Lake)                               │
│  - Metadata extraction & normalization                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Lineage Processing Engine                       │
│  - sqlglot (SQL parsing & lineage extraction)          │
│  - Graph builder (dependency resolution)               │
│  - Transformation analyzer                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         PostgreSQL Metadata Store                       │
│  - Data sources                                         │
│  - Datasets (tables/files)                             │
│  - Columns                                              │
│  - Column lineage graph                                │
│  - Transformations                                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend                            │
│  - REST API endpoints                                   │
│  - Business logic layer                                │
│  - Background task scheduler                            │
│  - Authentication & authorization                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         React + React Flow Frontend                     │
│  - Interactive lineage visualization                    │
│  - Data source management UI                           │
│  - Search & discovery                                   │
│  - Impact analysis                                      │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Architectural Principles

#### 1.2.1 Clean Architecture (Hexagonal/Ports & Adapters)

```
┌────────────────────────────────────────────┐
│           Presentation Layer               │
│         (FastAPI Controllers)              │
└──────────────────┬─────────────────────────┘
                   │
┌──────────────────▼─────────────────────────┐
│          Application Layer                 │
│  - Use cases (business logic)              │
│  - DTOs (data transfer objects)            │
│  - Service interfaces                      │
└──────────────────┬─────────────────────────┘
                   │
┌──────────────────▼─────────────────────────┐
│            Domain Layer                    │
│  - Entities (Dataset, Column, Lineage)     │
│  - Value Objects                           │
│  - Domain Services                         │
│  - Repository Interfaces                   │
└──────────────────┬─────────────────────────┘
                   │
┌──────────────────▼─────────────────────────┐
│        Infrastructure Layer                │
│  - Repository implementations              │
│  - External service adapters               │
│  - Database access (SQLAlchemy)            │
│  - Connectors (PostgreSQL, Iceberg, etc.)  │
└────────────────────────────────────────────┘
```

**Benefits:**
- **Testability**: Core business logic isolated from infrastructure
- **Flexibility**: Easy to swap implementations (e.g., different databases)
- **Maintainability**: Clear separation of concerns
- **Dependency Rule**: Dependencies point inward (infrastructure depends on domain, not vice versa)

#### 1.2.2 SOLID Principles

- **Single Responsibility**: Each class has one reason to change
- **Open/Closed**: Open for extension, closed for modification (Strategy pattern for connectors)
- **Liskov Substitution**: All connectors implement same interface
- **Interface Segregation**: Specific interfaces for different concerns
- **Dependency Inversion**: Depend on abstractions, not concretions

#### 1.2.3 Design Patterns

- **Repository Pattern**: Data access abstraction
- **Factory Pattern**: Connector instantiation based on source type
- **Strategy Pattern**: Different parsing strategies for SQL dialects
- **Observer Pattern**: Event-driven metadata updates
- **Builder Pattern**: Complex object construction (lineage graphs)

## 2. Data Model

### 2.1 Entity-Relationship Diagram

```
┌─────────────────┐
│  DataSource     │
│─────────────────│
│ id (PK)         │
│ name            │
│ type            │
│ config          │
│ status          │
└────────┬────────┘
         │
         │ 1:N
         │
         ▼
┌─────────────────┐
│  Dataset        │
│─────────────────│
│ id (PK)         │
│ source_id (FK)  │
│ fqn             │
│ name            │
│ schema_name     │
│ type            │
└────────┬────────┘
         │
         │ 1:N
         │
         ▼
┌─────────────────┐         ┌──────────────────┐
│  Column         │    N:M  │ ColumnLineage    │
│─────────────────│◄────────┤──────────────────│
│ id (PK)         │         │ id (PK)          │
│ dataset_id (FK) │         │ source_col_id    │
│ name            │         │ target_col_id    │
│ data_type       │         │ transform_id     │
│ ordinal_pos     │         │ expression       │
└─────────────────┘         │ confidence       │
                            └────────┬─────────┘
                                     │
                                     │ N:1
                                     │
                            ┌────────▼─────────┐
                            │ Transformation   │
                            │──────────────────│
                            │ id (PK)          │
                            │ source_ids[]     │
                            │ target_id        │
                            │ code             │
                            │ language         │
                            │ dialect          │
                            └──────────────────┘
```

### 2.2 Database Schema (PostgreSQL)

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Data source configurations
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL CHECK (type IN (
        'postgres', 'mysql', 'sqlserver', 'iceberg', 'delta'
    )),
    connection_config JSONB NOT NULL, -- Encrypted credentials
    sync_schedule VARCHAR(50), -- Cron expression
    last_sync_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN (
        'active', 'error', 'disabled'
    )),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_datasources_type ON data_sources(type);
CREATE INDEX idx_datasources_status ON data_sources(status);

-- Datasets (tables, views, files)
CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    data_source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    fully_qualified_name VARCHAR(500) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    type VARCHAR(50) NOT NULL CHECK (type IN (
        'table', 'view', 'materialized_view', 'iceberg_table', 'delta_table', 'file'
    )),
    metadata JSONB DEFAULT '{}',
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_datasets_source ON datasets(data_source_id);
CREATE INDEX idx_datasets_fqn ON datasets(fully_qualified_name);
CREATE INDEX idx_datasets_name ON datasets(name);
CREATE INDEX idx_datasets_type ON datasets(type);

-- Columns in datasets
CREATE TABLE columns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    data_type VARCHAR(100),
    ordinal_position INTEGER,
    is_nullable BOOLEAN DEFAULT TRUE,
    is_primary_key BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(dataset_id, name)
);

CREATE INDEX idx_columns_dataset ON columns(dataset_id);
CREATE INDEX idx_columns_name ON columns(name);

-- Transformations (SQL queries, Python code)
CREATE TABLE transformations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_dataset_ids UUID[] NOT NULL,
    target_dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    language VARCHAR(50) NOT NULL CHECK (language IN ('sql', 'python')),
    dialect VARCHAR(50), -- 'postgres', 'mysql', 'tsql', 'spark', etc.
    transformation_type VARCHAR(50), -- 'view', 'materialized_view', 'etl'
    extracted_from VARCHAR(100), -- 'pg_views', 'dbt_manifest', etc.
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transformations_target ON transformations(target_dataset_id);
CREATE INDEX idx_transformations_language ON transformations(language);

-- Column-level lineage relationships
CREATE TABLE column_lineage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_column_id UUID NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
    target_column_id UUID NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
    transformation_id UUID REFERENCES transformations(id) ON DELETE SET NULL,
    expression TEXT, -- Specific transformation expression
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_column_id, target_column_id, transformation_id)
);

CREATE INDEX idx_lineage_source ON column_lineage(source_column_id);
CREATE INDEX idx_lineage_target ON column_lineage(target_column_id);
CREATE INDEX idx_lineage_transform ON column_lineage(transformation_id);

-- Sync job tracking
CREATE TABLE sync_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    data_source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (status IN (
        'running', 'completed', 'failed'
    )),
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT,
    stats JSONB DEFAULT '{}', -- {tables_discovered: 10, columns_discovered: 100}
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_syncjobs_source ON sync_jobs(data_source_id);
CREATE INDEX idx_syncjobs_status ON sync_jobs(status);
CREATE INDEX idx_syncjobs_started ON sync_jobs(started_at DESC);

-- Trigger for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_datasources_updated_at BEFORE UPDATE ON data_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_datasets_updated_at BEFORE UPDATE ON datasets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_columns_updated_at BEFORE UPDATE ON columns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transformations_updated_at BEFORE UPDATE ON transformations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## 3. Backend Architecture

### 3.1 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   │
│   ├── domain/                 # Domain layer (business entities)
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── data_source.py
│   │   │   ├── dataset.py
│   │   │   ├── column.py
│   │   │   ├── lineage.py
│   │   │   └── transformation.py
│   │   ├── value_objects/
│   │   │   ├── __init__.py
│   │   │   ├── connection_config.py
│   │   │   └── lineage_graph.py
│   │   └── repositories/       # Repository interfaces
│   │       ├── __init__.py
│   │       ├── data_source_repository.py
│   │       ├── dataset_repository.py
│   │       └── lineage_repository.py
│   │
│   ├── application/            # Application layer (use cases)
│   │   ├── __init__.py
│   │   ├── use_cases/
│   │   │   ├── __init__.py
│   │   │   ├── register_data_source.py
│   │   │   ├── sync_metadata.py
│   │   │   ├── extract_lineage.py
│   │   │   └── query_lineage.py
│   │   ├── dtos/              # Data transfer objects
│   │   │   ├── __init__.py
│   │   │   ├── data_source_dto.py
│   │   │   └── lineage_dto.py
│   │   └── services/
│   │       ├── __init__.py
│   │       └── lineage_service.py
│   │
│   ├── infrastructure/         # Infrastructure layer
│   │   ├── __init__.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   ├── models.py      # SQLAlchemy models
│   │   │   └── repositories/  # Repository implementations
│   │   │       ├── __init__.py
│   │   │       ├── sqlalchemy_data_source_repo.py
│   │   │       └── sqlalchemy_lineage_repo.py
│   │   ├── connectors/        # Data source connectors
│   │   │   ├── __init__.py
│   │   │   ├── base.py        # Base connector interface
│   │   │   ├── factory.py     # Connector factory
│   │   │   ├── postgres_connector.py
│   │   │   ├── mysql_connector.py
│   │   │   ├── sqlserver_connector.py
│   │   │   ├── iceberg_connector.py
│   │   │   └── delta_connector.py
│   │   └── parsers/           # SQL/code parsers
│   │       ├── __init__.py
│   │       ├── sql_parser.py  # sqlglot wrapper
│   │       └── lineage_extractor.py
│   │
│   ├── presentation/          # Presentation layer (API)
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── data_sources.py
│   │   │       ├── datasets.py
│   │   │       ├── lineage.py
│   │   │       └── sync.py
│   │   └── schemas/           # Pydantic schemas
│   │       ├── __init__.py
│   │       ├── data_source.py
│   │       ├── dataset.py
│   │       └── lineage.py
│   │
│   └── core/                  # Cross-cutting concerns
│       ├── __init__.py
│       ├── exceptions.py
│       ├── logging.py
│       └── security.py
│
├── alembic/                   # Database migrations
│   ├── versions/
│   └── env.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── alembic.ini
├── pyproject.toml             # Poetry dependencies
├── Dockerfile
└── README.md
```

### 3.2 Core Components

#### 3.2.1 Domain Entities

**Dataset Entity:**
```python
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Optional

@dataclass
class Dataset:
    """Core domain entity representing a data asset."""

    id: UUID
    data_source_id: UUID
    fully_qualified_name: str
    name: str
    schema_name: Optional[str]
    type: str  # 'table', 'view', etc.
    metadata: dict
    last_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """Check if metadata needs refresh."""
        if not self.last_synced_at:
            return True
        age = datetime.utcnow() - self.last_synced_at
        return age.total_seconds() > (max_age_hours * 3600)
```

#### 3.2.2 Repository Pattern

**Interface:**
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from app.domain.entities.dataset import Dataset

class DatasetRepository(ABC):
    """Repository interface for dataset persistence."""

    @abstractmethod
    async def create(self, dataset: Dataset) -> Dataset:
        pass

    @abstractmethod
    async def get_by_id(self, dataset_id: UUID) -> Optional[Dataset]:
        pass

    @abstractmethod
    async def get_by_fqn(self, fqn: str) -> Optional[Dataset]:
        pass

    @abstractmethod
    async def find_by_source(self, source_id: UUID) -> List[Dataset]:
        pass

    @abstractmethod
    async def update(self, dataset: Dataset) -> Dataset:
        pass

    @abstractmethod
    async def delete(self, dataset_id: UUID) -> None:
        pass
```

**Implementation:**
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database.models import DatasetModel

class SQLAlchemyDatasetRepository(DatasetRepository):
    """SQLAlchemy implementation of dataset repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, dataset: Dataset) -> Dataset:
        model = DatasetModel.from_entity(dataset)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model.to_entity()

    async def get_by_id(self, dataset_id: UUID) -> Optional[Dataset]:
        result = await self.session.execute(
            select(DatasetModel).where(DatasetModel.id == dataset_id)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None
```

#### 3.2.3 Connector Strategy Pattern

**Base Connector:**
```python
from abc import ABC, abstractmethod
from typing import List, AsyncIterator
from dataclasses import dataclass

@dataclass
class ColumnMetadata:
    name: str
    data_type: str
    ordinal_position: int
    is_nullable: bool
    is_primary_key: bool = False

@dataclass
class DatasetMetadata:
    fully_qualified_name: str
    name: str
    schema_name: str
    type: str
    columns: List[ColumnMetadata]
    metadata: dict

@dataclass
class TransformationMetadata:
    source_fqns: List[str]
    target_fqn: str
    code: str
    language: str
    dialect: str
    type: str

class BaseConnector(ABC):
    """Base interface for all data source connectors."""

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if connection is valid."""
        pass

    @abstractmethod
    async def discover_datasets(self) -> AsyncIterator[DatasetMetadata]:
        """Discover all datasets (tables, views) in the source."""
        pass

    @abstractmethod
    async def discover_transformations(self) -> AsyncIterator[TransformationMetadata]:
        """Discover transformation logic (views, stored procedures)."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection and cleanup resources."""
        pass
```

**PostgreSQL Connector:**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import text

class PostgreSQLConnector(BaseConnector):
    """PostgreSQL metadata connector."""

    def __init__(self, connection_config: dict):
        self.config = connection_config
        self.engine: Optional[AsyncEngine] = None

    async def test_connection(self) -> bool:
        try:
            engine = await self._get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def discover_datasets(self) -> AsyncIterator[DatasetMetadata]:
        """Discover tables and views from information_schema."""
        engine = await self._get_engine()

        query = text("""
            SELECT
                table_schema,
                table_name,
                table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """)

        async with engine.connect() as conn:
            result = await conn.execute(query)

            for row in result:
                columns = await self._get_columns(
                    conn, row.table_schema, row.table_name
                )

                yield DatasetMetadata(
                    fully_qualified_name=f"postgres.{row.table_schema}.{row.table_name}",
                    name=row.table_name,
                    schema_name=row.table_schema,
                    type='view' if row.table_type == 'VIEW' else 'table',
                    columns=columns,
                    metadata={}
                )

    async def discover_transformations(self) -> AsyncIterator[TransformationMetadata]:
        """Extract SQL from views."""
        engine = await self._get_engine()

        query = text("""
            SELECT
                schemaname,
                viewname,
                definition
            FROM pg_views
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        """)

        async with engine.connect() as conn:
            result = await conn.execute(query)

            for row in result:
                yield TransformationMetadata(
                    source_fqns=[],  # Will be parsed from SQL
                    target_fqn=f"postgres.{row.schemaname}.{row.viewname}",
                    code=row.definition,
                    language='sql',
                    dialect='postgres',
                    type='view'
                )

    async def _get_columns(
        self, conn, schema: str, table: str
    ) -> List[ColumnMetadata]:
        """Get column metadata for a table."""
        query = text("""
            SELECT
                column_name,
                data_type,
                ordinal_position,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            ORDER BY ordinal_position
        """)

        result = await conn.execute(
            query, {"schema": schema, "table": table}
        )

        return [
            ColumnMetadata(
                name=row.column_name,
                data_type=row.data_type,
                ordinal_position=row.ordinal_position,
                is_nullable=(row.is_nullable == 'YES')
            )
            for row in result
        ]

    async def _get_engine(self) -> AsyncEngine:
        if not self.engine:
            connection_string = (
                f"postgresql+asyncpg://{self.config['user']}:"
                f"{self.config['password']}@{self.config['host']}:"
                f"{self.config['port']}/{self.config['database']}"
            )
            self.engine = create_async_engine(connection_string)
        return self.engine

    async def close(self) -> None:
        if self.engine:
            await self.engine.dispose()
```

#### 3.2.4 SQL Parser with sqlglot

```python
import sqlglot
from sqlglot.lineage import lineage as sqlglot_lineage
from typing import Dict, List, Set
from dataclasses import dataclass

@dataclass
class ColumnLineage:
    target_column: str
    source_columns: List[str]  # FQNs like "schema.table.column"
    expression: str

class SQLLineageExtractor:
    """Extract column-level lineage from SQL using sqlglot."""

    def __init__(self, dialect: str = 'postgres'):
        self.dialect = dialect

    def extract_lineage(
        self,
        sql: str,
        target_table: str
    ) -> List[ColumnLineage]:
        """Extract column lineage from SQL."""
        try:
            # Parse SQL
            parsed = sqlglot.parse_one(sql, dialect=self.dialect)

            # Get all columns in SELECT clause
            select_columns = self._get_select_columns(parsed)

            lineages = []
            for col_name, col_expr in select_columns.items():
                # Use sqlglot lineage analysis
                try:
                    node = sqlglot_lineage(
                        col_name,
                        sql,
                        dialect=self.dialect,
                        schema={}  # Can provide schema for better accuracy
                    )

                    # Extract source columns
                    source_columns = self._extract_source_columns(node)

                    lineages.append(ColumnLineage(
                        target_column=f"{target_table}.{col_name}",
                        source_columns=source_columns,
                        expression=str(col_expr)
                    ))
                except Exception as e:
                    # If lineage extraction fails, at least capture the column
                    lineages.append(ColumnLineage(
                        target_column=f"{target_table}.{col_name}",
                        source_columns=[],
                        expression=str(col_expr)
                    ))

            return lineages

        except Exception as e:
            raise LineageExtractionError(f"Failed to parse SQL: {e}")

    def _get_select_columns(self, parsed) -> Dict[str, str]:
        """Extract column names and expressions from SELECT."""
        columns = {}

        if hasattr(parsed, 'expressions'):
            for expr in parsed.expressions:
                if hasattr(expr, 'alias'):
                    col_name = expr.alias or str(expr)
                else:
                    col_name = str(expr)
                columns[col_name] = expr

        return columns

    def _extract_source_columns(self, lineage_node) -> List[str]:
        """Extract source column FQNs from lineage node."""
        sources = []

        def traverse(node):
            if hasattr(node, 'downstream'):
                for child in node.downstream:
                    traverse(child)
            if hasattr(node, 'name'):
                # Build FQN: schema.table.column
                parts = []
                if hasattr(node, 'table'):
                    if hasattr(node.table, 'schema'):
                        parts.append(str(node.table.schema))
                    parts.append(str(node.table.name))
                parts.append(str(node.name))
                sources.append('.'.join(parts))

        traverse(lineage_node)
        return sources

class LineageExtractionError(Exception):
    pass
```

### 3.3 FastAPI Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List

from app.presentation.schemas.lineage import (
    LineageGraphResponse, ColumnLineageNode, ColumnLineageEdge
)
from app.application.use_cases.query_lineage import QueryLineageUseCase
from app.presentation.api.dependencies import get_query_lineage_use_case

router = APIRouter(prefix="/api/v1/lineage", tags=["lineage"])

@router.get(
    "/column/{column_id}",
    response_model=LineageGraphResponse,
    summary="Get column lineage graph"
)
async def get_column_lineage(
    column_id: UUID,
    direction: str = "both",  # 'upstream', 'downstream', 'both'
    depth: int = 5,
    use_case: QueryLineageUseCase = Depends(get_query_lineage_use_case)
):
    """
    Get column-level lineage graph for a specific column.

    - **column_id**: UUID of the column
    - **direction**: 'upstream' (sources), 'downstream' (targets), or 'both'
    - **depth**: How many hops to traverse
    """
    try:
        lineage_graph = await use_case.execute(
            column_id=column_id,
            direction=direction,
            depth=depth
        )
        return lineage_graph
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get(
    "/table/{dataset_id}",
    response_model=LineageGraphResponse,
    summary="Get table-level lineage"
)
async def get_table_lineage(
    dataset_id: UUID,
    direction: str = "both",
    depth: int = 3,
    use_case: QueryLineageUseCase = Depends(get_query_lineage_use_case)
):
    """Get table-level lineage (aggregated from column lineage)."""
    # Implementation similar to column lineage
    pass

@router.get(
    "/impact/{column_id}",
    response_model=List[UUID],
    summary="Get downstream impact analysis"
)
async def get_impact_analysis(
    column_id: UUID,
    use_case: QueryLineageUseCase = Depends(get_query_lineage_use_case)
):
    """
    Get all downstream columns affected by this column.
    Useful for impact analysis before making changes.
    """
    pass
```

## 4. Frontend Architecture

### 4.1 Project Structure

```
frontend/
├── public/
├── src/
│   ├── main.tsx              # Application entry point
│   ├── App.tsx
│   │
│   ├── components/
│   │   ├── common/           # Reusable components
│   │   │   ├── Button/
│   │   │   ├── Input/
│   │   │   └── Modal/
│   │   │
│   │   ├── lineage/          # Lineage visualization
│   │   │   ├── LineageFlow/
│   │   │   │   ├── LineageFlow.tsx
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useLineageLayout.ts
│   │   │   │   └── utils/
│   │   │   │       └── layoutAlgorithm.ts
│   │   │   ├── nodes/
│   │   │   │   ├── ColumnTableNode/
│   │   │   │   │   ├── ColumnTableNode.tsx
│   │   │   │   │   └── ColumnTableNode.module.css
│   │   │   │   └── index.ts
│   │   │   ├── edges/
│   │   │   │   ├── TransformationEdge/
│   │   │   │   │   ├── TransformationEdge.tsx
│   │   │   │   │   └── TransformationEdge.module.css
│   │   │   │   └── index.ts
│   │   │   └── controls/
│   │   │       ├── LineageControls.tsx
│   │   │       └── SearchPanel.tsx
│   │   │
│   │   └── sources/          # Data source management
│   │       ├── SourceList/
│   │       ├── SourceForm/
│   │       └── SyncStatus/
│   │
│   ├── pages/
│   │   ├── Dashboard/
│   │   ├── DataSources/
│   │   ├── LineageExplorer/
│   │   └── Search/
│   │
│   ├── services/             # API clients
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── lineageApi.ts
│   │   │   └── sourceApi.ts
│   │   └── auth/
│   │
│   ├── store/                # State management (Zustand)
│   │   ├── lineageStore.ts
│   │   └── sourceStore.ts
│   │
│   ├── types/                # TypeScript types
│   │   ├── lineage.ts
│   │   └── dataSource.ts
│   │
│   └── utils/
│       └── graphTransform.ts
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

### 4.2 React Flow Implementation

**Custom Column Table Node:**

```tsx
// src/components/lineage/nodes/ColumnTableNode/ColumnTableNode.tsx
import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import styles from './ColumnTableNode.module.css';

export interface ColumnData {
  id: string;
  name: string;
  dataType: string;
  isPrimaryKey?: boolean;
}

export interface ColumnTableNodeData {
  tableName: string;
  schemaName: string;
  sourceType: string;
  columns: ColumnData[];
  onColumnClick?: (columnId: string) => void;
}

const ColumnTableNode: React.FC<NodeProps<ColumnTableNodeData>> = ({
  data,
  selected
}) => {
  return (
    <div className={`${styles.node} ${selected ? styles.selected : ''}`}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.tableName}>{data.tableName}</div>
        <div className={styles.metadata}>
          <span className={styles.schema}>{data.schemaName}</span>
          <span className={styles.sourceType}>{data.sourceType}</span>
        </div>
      </div>

      {/* Columns */}
      <div className={styles.columnsList}>
        {data.columns.map((column, index) => (
          <div
            key={column.id}
            className={styles.columnRow}
            onClick={() => data.onColumnClick?.(column.id)}
          >
            {/* Input handle */}
            <Handle
              type="target"
              position={Position.Left}
              id={`${column.id}-target`}
              className={styles.handle}
              style={{ top: `${index * 32 + 16}px` }}
            />

            {/* Column info */}
            <div className={styles.columnInfo}>
              <span className={styles.columnIcon}>
                {column.isPrimaryKey ? '🔑' : '○'}
              </span>
              <span className={styles.columnName}>{column.name}</span>
              <span className={styles.columnType}>{column.dataType}</span>
            </div>

            {/* Output handle */}
            <Handle
              type="source"
              position={Position.Right}
              id={`${column.id}-source`}
              className={styles.handle}
              style={{ top: `${index * 32 + 16}px` }}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default ColumnTableNode;
```

**Lineage Flow Component:**

```tsx
// src/components/lineage/LineageFlow/LineageFlow.tsx
import React, { useCallback, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';

import ColumnTableNode from '../nodes/ColumnTableNode/ColumnTableNode';
import TransformationEdge from '../edges/TransformationEdge/TransformationEdge';
import { LineageGraphData } from '../../../types/lineage';
import { convertToFlowFormat } from '../../../utils/graphTransform';
import { getLayoutedElements } from './utils/layoutAlgorithm';

const nodeTypes = {
  columnTable: ColumnTableNode,
};

const edgeTypes = {
  transformation: TransformationEdge,
};

interface LineageFlowProps {
  data: LineageGraphData;
  onColumnClick?: (columnId: string) => void;
  onEdgeClick?: (edgeId: string) => void;
}

const LineageFlow: React.FC<LineageFlowProps> = ({
  data,
  onColumnClick,
  onEdgeClick,
}) => {
  const [selectedColumn, setSelectedColumn] = useState<string | null>(null);

  // Convert backend data to React Flow format
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    const { nodes, edges } = convertToFlowFormat(data);
    return getLayoutedElements(nodes, edges, 'LR');
  }, [data]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    console.log('Node clicked:', node);
  }, []);

  const handleEdgeClick = useCallback((event: React.MouseEvent, edge: Edge) => {
    onEdgeClick?.(edge.id);
  }, [onEdgeClick]);

  const handleColumnClick = useCallback((columnId: string) => {
    setSelectedColumn(columnId);
    onColumnClick?.(columnId);

    // Highlight related edges
    setEdges((eds) =>
      eds.map((edge) => ({
        ...edge,
        animated:
          edge.sourceHandle?.includes(columnId) ||
          edge.targetHandle?.includes(columnId),
      }))
    );
  }, [onColumnClick, setEdges]);

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        attributionPosition="bottom-right"
        defaultEdgeOptions={{
          type: 'transformation',
          markerEnd: { type: MarkerType.ArrowClosed },
        }}
      >
        <Background />
        <Controls />
        <MiniMap
          nodeColor={(node) => {
            switch (node.data.sourceType) {
              case 'postgres': return '#336791';
              case 'mysql': return '#4479A1';
              case 'iceberg': return '#00C7D9';
              default: return '#888';
            }
          }}
        />

        <Panel position="top-left">
          <div style={{ background: 'white', padding: '10px', borderRadius: '5px' }}>
            <h3>Lineage Explorer</h3>
            {selectedColumn && <p>Selected: {selectedColumn}</p>}
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
};

export default LineageFlow;
```

**Layout Algorithm (Dagre):**

```typescript
// src/components/lineage/LineageFlow/utils/layoutAlgorithm.ts
import dagre from 'dagre';
import { Node, Edge, Position } from 'reactflow';

const NODE_WIDTH = 320;
const NODE_HEIGHT_BASE = 80;
const COLUMN_HEIGHT = 32;

export function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'LR'
) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 100,
    ranksep: 150,
  });

  // Add nodes with dynamic heights based on column count
  nodes.forEach((node) => {
    const columnCount = node.data.columns?.length || 0;
    const nodeHeight = NODE_HEIGHT_BASE + (columnCount * COLUMN_HEIGHT);

    dagreGraph.setNode(node.id, {
      width: NODE_WIDTH,
      height: nodeHeight,
    });
  });

  // Add edges
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Calculate layout
  dagre.layout(dagreGraph);

  // Update node positions
  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);

    return {
      ...node,
      targetPosition: isHorizontal ? Position.Left : Position.Top,
      sourcePosition: isHorizontal ? Position.Right : Position.Bottom,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - nodeWithPosition.height / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}
```

### 4.3 State Management (Zustand)

```typescript
// src/store/lineageStore.ts
import { create } from 'zustand';
import { LineageGraphData, Column } from '../types/lineage';
import { lineageApi } from '../services/api/lineageApi';

interface LineageState {
  // State
  currentGraph: LineageGraphData | null;
  selectedColumn: Column | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchLineage: (columnId: string, direction?: string, depth?: number) => Promise<void>;
  selectColumn: (column: Column | null) => void;
  clearGraph: () => void;
}

export const useLineageStore = create<LineageState>((set, get) => ({
  currentGraph: null,
  selectedColumn: null,
  loading: false,
  error: null,

  fetchLineage: async (columnId, direction = 'both', depth = 5) => {
    set({ loading: true, error: null });

    try {
      const graph = await lineageApi.getColumnLineage(columnId, direction, depth);
      set({ currentGraph: graph, loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch lineage',
        loading: false
      });
    }
  },

  selectColumn: (column) => {
    set({ selectedColumn: column });
  },

  clearGraph: () => {
    set({ currentGraph: null, selectedColumn: null, error: null });
  },
}));
```

## 5. Testing Strategy

### 5.1 Backend Testing

**Unit Tests:**
```python
# tests/unit/test_sql_lineage_extractor.py
import pytest
from app.infrastructure.parsers.sql_parser import SQLLineageExtractor

class TestSQLLineageExtractor:
    @pytest.fixture
    def extractor(self):
        return SQLLineageExtractor(dialect='postgres')

    def test_simple_select(self, extractor):
        sql = """
        SELECT
            customer_id,
            first_name,
            last_name
        FROM customers
        """

        lineages = extractor.extract_lineage(sql, 'result')

        assert len(lineages) == 3
        assert any(l.target_column == 'result.customer_id' for l in lineages)

    def test_column_transformation(self, extractor):
        sql = """
        SELECT
            first_name || ' ' || last_name as full_name
        FROM customers
        """

        lineages = extractor.extract_lineage(sql, 'result')

        full_name_lineage = next(
            l for l in lineages if 'full_name' in l.target_column
        )

        assert 'first_name' in str(full_name_lineage.source_columns)
        assert 'last_name' in str(full_name_lineage.source_columns)
```

**Integration Tests:**
```python
# tests/integration/test_postgres_connector.py
import pytest
from app.infrastructure.connectors.postgres_connector import PostgreSQLConnector

@pytest.mark.asyncio
class TestPostgreSQLConnector:
    @pytest.fixture
    async def connector(self, test_postgres_config):
        conn = PostgreSQLConnector(test_postgres_config)
        yield conn
        await conn.close()

    async def test_discover_tables(self, connector):
        datasets = []
        async for dataset in connector.discover_datasets():
            datasets.append(dataset)

        assert len(datasets) > 0
        assert all(hasattr(d, 'columns') for d in datasets)

    async def test_discover_views(self, connector):
        transformations = []
        async for transform in connector.discover_transformations():
            transformations.append(transform)

        assert all(t.language == 'sql' for t in transformations)
```

### 5.2 Frontend Testing

**Component Tests (Vitest + React Testing Library):**
```tsx
// src/components/lineage/nodes/ColumnTableNode/ColumnTableNode.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ColumnTableNode from './ColumnTableNode';

describe('ColumnTableNode', () => {
  const mockData = {
    tableName: 'users',
    schemaName: 'public',
    sourceType: 'postgres',
    columns: [
      { id: 'col1', name: 'id', dataType: 'INTEGER', isPrimaryKey: true },
      { id: 'col2', name: 'name', dataType: 'VARCHAR' },
    ],
  };

  it('renders table name and columns', () => {
    render(<ColumnTableNode id="1" data={mockData} />);

    expect(screen.getByText('users')).toBeInTheDocument();
    expect(screen.getByText('id')).toBeInTheDocument();
    expect(screen.getByText('name')).toBeInTheDocument();
  });

  it('calls onColumnClick when column is clicked', () => {
    const onColumnClick = vi.fn();
    const dataWithCallback = { ...mockData, onColumnClick };

    render(<ColumnTableNode id="1" data={dataWithCallback} />);

    fireEvent.click(screen.getByText('id'));
    expect(onColumnClick).toHaveBeenCalledWith('col1');
  });
});
```

## 6. Technology Stack

### 6.1 Backend
- **Framework**: FastAPI 0.104+
- **Language**: Python 3.11+
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0+ (async)
- **Migrations**: Alembic
- **SQL Parser**: sqlglot
- **Connectors**:
  - PyIceberg (Apache Iceberg)
  - delta-rs (Delta Lake)
  - asyncpg (PostgreSQL)
  - aiomysql (MySQL)
- **Background Jobs**: Celery + Redis (or APScheduler for simplicity)
- **Testing**: pytest, pytest-asyncio
- **Package Management**: Poetry

### 6.2 Frontend
- **Framework**: React 18+
- **Language**: TypeScript 5+
- **Build Tool**: Vite
- **Visualization**: React Flow 11+
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Styling**: CSS Modules + Tailwind CSS
- **Layout**: Dagre
- **Testing**: Vitest + React Testing Library
- **Package Management**: npm/pnpm

### 6.3 Infrastructure
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana (optional)

## 7. Security Considerations

### 7.1 Connection String Encryption
- Use Fernet encryption for storing connection configs
- Store encryption key in environment variable or secrets manager

### 7.2 API Security
- JWT authentication
- Rate limiting
- CORS configuration
- Input validation with Pydantic

### 7.3 SQL Injection Prevention
- Parameterized queries only
- No string concatenation for SQL
- sqlglot parsing prevents injection in lineage analysis

## 8. Performance Optimizations

### 8.1 Database
- Indexes on foreign keys
- Partial indexes for status fields
- Connection pooling
- Query result caching (Redis)

### 8.2 API
- Pagination for large result sets
- Async endpoints
- Background tasks for heavy operations
- Response compression

### 8.3 Frontend
- Code splitting
- Lazy loading of routes
- Virtual scrolling for large lists
- Debounced search
- React Flow virtualization for large graphs

## 9. Deployment

### 9.1 Docker Compose Setup
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: lineage
      POSTGRES_USER: lineage
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql+asyncpg://lineage:${DB_PASSWORD}@postgres:5432/lineage
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    depends_on:
      - backend
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:8000

volumes:
  postgres_data:
```

## 10. Future Enhancements

1. **dbt Integration** - Parse dbt manifest.json for comprehensive lineage
2. **Python Code Parsing** - AST analysis for Pandas/PySpark
3. **Real-time Updates** - WebSocket for live lineage updates
4. **Data Quality Integration** - Link to test results and data quality metrics
5. **Column-level Statistics** - Show data profiling alongside lineage
6. **Version Control** - Track lineage changes over time
7. **Export Capabilities** - Export graphs as PNG/SVG/PDF
8. **Collaboration Features** - Comments, annotations on lineage
9. **ML Model Lineage** - Track feature dependencies for ML models
10. **Cost Analysis** - Estimate query costs based on lineage

## Conclusion

This technical design provides a robust, scalable foundation for a production-grade data lineage tool. The architecture emphasizes:

- **Clean separation of concerns** through layered architecture
- **Extensibility** via strategy patterns for connectors
- **Performance** through async operations and efficient graph algorithms
- **Maintainability** through comprehensive testing and type safety
- **User experience** through interactive visualization and intuitive UI

The implementation can start with core features (PostgreSQL connector, SQL parsing, basic visualization) and incrementally add support for additional data sources and advanced features.
