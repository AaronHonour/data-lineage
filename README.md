# Data Lineage Tool

A production-grade data lineage tracking system that provides **column-level lineage** across heterogeneous data sources including PostgreSQL, MySQL, SQL Server, Apache Iceberg, and Delta Lake.

## Features

- **Column-Level Lineage**: Track how data flows from source columns to target columns through transformations
- **Multi-Source Support**: PostgreSQL, MySQL, SQL Server, Apache Iceberg, Delta Lake
- **Automatic Discovery**: Metadata API integration to automatically discover tables, columns, and transformations
- **SQL Parsing**: Intelligent SQL parsing using sqlglot to extract lineage from views, stored procedures, etc.
- **Interactive Visualization**: React Flow-based interactive lineage graphs
- **REST API**: Comprehensive REST API for programmatic access
- **Impact Analysis**: Understand downstream impact of schema or data changes

## Architecture

The system follows Clean Architecture principles with clear separation of concerns:

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│         (FastAPI REST API)              │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│        Application Layer                │
│     (Use Cases & Services)              │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│          Domain Layer                   │
│    (Entities & Business Logic)          │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Infrastructure Layer               │
│  (Database, Connectors, Parsers)        │
└─────────────────────────────────────────┘
```

See [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) for detailed architecture documentation.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **SQL Parser**: sqlglot
- **Testing**: pytest, pytest-asyncio

### Frontend
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite
- **Visualization**: React Flow
- **State Management**: Zustand
- **HTTP Client**: Axios

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# Backend will be available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

This will start:
- **lineage-db**: PostgreSQL database for lineage metadata (port 5432)
- **sample-db**: Sample PostgreSQL database with test data (port 5433)
- **backend**: FastAPI backend (port 8000)

### Local Development Setup

#### Backend

```bash
cd backend

# Install dependencies
poetry install

# Copy environment file
cp .env.example .env

# Start PostgreSQL (via Docker)
docker-compose up -d lineage-db sample-db

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Usage

### 1. Register a Data Source

```bash
curl -X POST http://localhost:8000/api/v1/data-sources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sample-postgres",
    "type": "postgres",
    "connection_config": {
      "host": "localhost",
      "port": 5433,
      "database": "sample",
      "user": "sample",
      "password": "sample_password"
    }
  }'
```

### 2. Trigger Metadata Sync

```bash
curl -X POST http://localhost:8000/api/v1/data-sources/{source_id}/sync
```

This will:
- Discover all tables and views
- Extract column metadata
- Parse view definitions to extract SQL transformations
- Build column-level lineage graph

### 3. Query Lineage

```bash
# Get column lineage
curl http://localhost:8000/api/v1/lineage/column/{column_id}?direction=both&depth=5

# Get table lineage
curl http://localhost:8000/api/v1/lineage/table/{dataset_id}?direction=upstream
```

### API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
.
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── domain/         # Domain entities and business logic
│   │   ├── application/    # Use cases and services
│   │   ├── infrastructure/ # Database, connectors, parsers
│   │   ├── presentation/   # API endpoints and schemas
│   │   └── core/           # Cross-cutting concerns
│   ├── alembic/            # Database migrations
│   ├── tests/              # Tests
│   └── pyproject.toml      # Dependencies
│
├── frontend/               # React frontend (to be implemented)
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API clients
│   │   └── store/         # State management
│   └── package.json
│
├── sample-data/            # Sample data for testing
│   └── init.sql           # Sample database initialization
│
├── docker-compose.yml      # Docker Compose configuration
├── TECHNICAL_DESIGN.md     # Detailed technical documentation
└── README.md              # This file
```

## Development

### Running Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/unit/test_sql_parser.py
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Code Quality

```bash
# Format code
black app/

# Lint code
ruff check app/

# Type checking
mypy app/
```

## Sample Data

The `sample-data/init.sql` script creates a realistic e-commerce scenario with:

- **Staging Tables**: customers, orders, order_items
- **Analytics Views**:
  - customer_profiles (simple transformation)
  - order_summary (join transformation)
  - customer_lifetime_value (aggregation)
  - product_performance (complex aggregation)
  - customer_product_affinity (multi-level join + aggregation)

This demonstrates various types of lineage:
- Direct column copies
- Column concatenations (`first_name || ' ' || last_name`)
- Aggregations (`SUM`, `COUNT`, `AVG`)
- Multi-table joins
- Complex transformations

## Roadmap

- [x] PostgreSQL connector
- [x] SQL parsing with sqlglot
- [x] Column-level lineage extraction
- [x] REST API endpoints
- [ ] React Flow visualization
- [ ] MySQL connector
- [ ] SQL Server connector
- [ ] Apache Iceberg connector
- [ ] Delta Lake connector
- [ ] dbt integration
- [ ] Python code parsing (Pandas/PySpark)
- [ ] Background job scheduler
- [ ] Real-time lineage updates
- [ ] Data quality integration
- [ ] Search and discovery UI
- [ ] Export capabilities (PNG/SVG/PDF)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/data-lineage/issues)
- Documentation: See [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md)

## Acknowledgments

- [sqlglot](https://github.com/tobymao/sqlglot) - SQL parser and transpiler
- [React Flow](https://reactflow.dev/) - Interactive graph visualization
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
