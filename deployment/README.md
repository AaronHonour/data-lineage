# Data Lineage Sample Deployment

Complete cross-platform deployment system for the data lineage application, featuring automated infrastructure setup, sample data loading, comprehensive validation, and graceful teardown.

---

## 🚀 Quick Start

```bash
# Navigate to deployment directory
cd deployment

# Install Python dependencies (if needed)
pip install requests

# Run full deployment
python scripts/cli.py deploy

# Or step-by-step:
python scripts/cli.py run infrastructure
python scripts/cli.py run sample-data
python scripts/cli.py run validation
```

**That's it!** Your data lineage system is now running with a complete sample data flow from source databases through transformations to analytics outputs.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Runbooks](#runbooks)
- [Sample Data](#sample-data)
- [API Endpoints](#api-endpoints)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Overview

This deployment system provides:

- **✅ Cross-platform**: Works on Windows, macOS, and Linux
- **✅ Automated**: Single command deployment
- **✅ Validated**: Comprehensive test suite
- **✅ Documented**: Detailed runbooks for each operation
- **✅ Reversible**: Clean teardown and redeployment
- **✅ Production-like**: Real data flow patterns

### What Gets Deployed

1. **Infrastructure** (Docker services)
   - PostgreSQL (lineage metadata DB)
   - PostgreSQL (source e-commerce DB)
   - MySQL (source auxiliary DB)
   - FastAPI backend
   - dbt service

2. **Sample Data** (Realistic e-commerce flow)
   - Raw operational data (customers, orders, products)
   - Auxiliary systems (inventory, shipping)
   - dbt transformation models (staging + marts)
   - Python analytics jobs (pandas, polars)
   - Delta Lake analytics output

3. **Lineage Graph** (Column-level)
   - 15-20 datasets discovered
   - 8-12 transformations tracked
   - 30-50 column lineage edges
   - Cross-source lineage (PostgreSQL → dbt → Python → Delta Lake)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Flow                                 │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│ PostgreSQL   │──┐
│ (raw data)   │  │
└──────────────┘  │
                  │
┌──────────────┐  │     ┌──────────────┐     ┌──────────────┐
│ MySQL        │  │     │ dbt          │     │ Python Jobs  │
│ (auxiliary)  │  ├────▶│ (staging +   │────▶│ (analytics)  │
└──────────────┘  │     │  marts)      │     └──────┬───────┘
                  │     └──────────────┘            │
                  │                                 │
                  │                        ┌────────▼────────┐
                  └───────────────────────▶│ Delta Lake      │
                                           │ (output)        │
                                           └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Lineage Tracking                              │
└─────────────────────────────────────────────────────────────────┘

                      ┌──────────────┐
                      │ Lineage DB   │
                      │ (metadata)   │
                      └──────┬───────┘
                             │
                    ┌────────▼─────────┐
                    │  FastAPI Backend │
                    │  - Connectors    │
                    │  - Parsers       │
                    │  - Sync Service  │
                    └──────┬───────────┘
                           │
                  ┌────────▼────────┐
                  │  REST API       │
                  │  :8000/api/v1   │
                  └─────────────────┘
```

---

## Requirements

### Software Requirements

- **Docker**: Version 20.10+
- **Docker Compose**: V2 (bundled with Docker Desktop)
- **Python**: 3.8+ (for deployment scripts)
- **pip**: For installing Python dependencies

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 4 GB | 8 GB |
| Disk Space | 5 GB | 10 GB |
| CPU Cores | 2 | 4 |

### Operating Systems

- ✅ **Linux**: Ubuntu 20.04+, Debian 10+, CentOS 8+
- ✅ **macOS**: 10.15+ (Catalina or later)
- ✅ **Windows**: 10/11 with WSL2

---

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd data-lineage/deployment
```

### 2. Install Python Dependencies

```bash
# Using pip
pip install requests

# Or using requirements.txt (if provided)
pip install -r requirements.txt
```

### 3. Verify Docker

```bash
# Check Docker is installed
docker --version

# Check Docker Compose
docker compose version

# Verify Docker is running
docker ps
```

### 4. (Optional) Configure

Most configurations work out-of-the-box. To customize:

- **Services**: Edit `docker-compose.sample.yml`
- **Data Sources**: Edit `config/data-sources.json`
- **Sample Data**: Modify SQL files in `sample-data/`

---

## Usage

### Interactive Mode

```bash
python scripts/cli.py
```

You'll be presented with a menu:

```
Select an operation:

1. Run full deployment (infrastructure + data + validation)
2. Run individual runbook
3. List available runbooks
4. Exit

Enter your choice (1-4):
```

### Command Line Mode

```bash
# List available runbooks
python scripts/cli.py list

# Run specific runbook
python scripts/cli.py run infrastructure
python scripts/cli.py run sample-data
python scripts/cli.py run validation
python scripts/cli.py run teardown

# Run with options
python scripts/cli.py run teardown --clean-volumes

# Full deployment shortcut
python scripts/cli.py deploy
```

### Direct Python Execution

```bash
# Run runbook scripts directly
python scripts/deploy_infrastructure.py
python scripts/deploy_sample_data.py
python scripts/validate_deployment.py
python scripts/teardown.py --help
```

---

## Runbooks

Detailed runbooks are available for each operation:

### 1. [Infrastructure Deployment](runbooks/01-infrastructure-deployment.md)
- Deploy Docker services
- Initialize databases
- Start API service
- **Time**: 5-10 minutes

### 2. [Sample Data Deployment](runbooks/02-sample-data-deployment.md)
- Register data sources
- Trigger synchronization
- Build lineage graph
- **Time**: 10-15 minutes

### 3. [Validation](runbooks/03-validation.md)
- Verify deployment health
- Test lineage queries
- Generate validation report
- **Time**: 3-5 minutes

### 4. [Teardown](runbooks/04-teardown.md)
- Stop services
- Clean up data (optional)
- Remove deployment state (optional)
- **Time**: 2-3 minutes

---

## Sample Data

### E-commerce Data Flow

The deployment includes a realistic e-commerce data pipeline:

#### Source Layer (PostgreSQL + MySQL)

**PostgreSQL: `raw` schema**
- `customers`: 10 sample customers
- `orders`: 10 sample orders
- `products`: 10 sample products
- `order_items`: Line items for orders
- `customer_order_summary`: Aggregation view

**MySQL: `auxiliary` database**
- `inventory`: Product stock levels
- `deliveries`: Shipping information
- `warehouses`: Distribution centers
- `low_stock_alerts`: Monitoring view
- `delivery_performance`: Analytics view

#### Transformation Layer (dbt)

**Staging Models** (`staging` schema)
- `stg_customers`: Cleaned customer data
- `stg_orders`: Enriched order data
- `stg_products`: Standardized product data

**Marts Models** (`marts` schema)
- `dim_customers`: Customer dimension with lifetime metrics
- `fct_orders`: Order fact table with denormalization

#### Analytics Layer (Python + Delta Lake)

**Python Jobs**
- `customer_lifetime_value.py`: LTV analysis using pandas
- `daily_order_metrics.py`: Daily aggregations using polars

**Delta Lake Output**
- `customer_ltv`: Customer value segments
- `daily_order_metrics`: Time-series metrics

### Lineage Coverage

The sample data creates lineage across:

- **Database → Database**: View dependencies
- **Database → dbt**: Source to model lineage
- **dbt → dbt**: Model dependencies
- **dbt → Python**: DataFrame reads from database
- **Python → Delta Lake**: Analytics outputs
- **Cross-source**: Multi-database transformations

---

## API Endpoints

Once deployed, these endpoints are available:

### Health Check

```bash
GET http://localhost:8000/health
```

### API Documentation

```bash
# Interactive Swagger UI
http://localhost:8000/docs

# ReDoc alternative
http://localhost:8000/redoc
```

### Data Sources

```bash
# List all data sources
GET http://localhost:8000/api/v1/data-sources

# Get specific source
GET http://localhost:8000/api/v1/data-sources/{source_id}

# Trigger sync
POST http://localhost:8000/api/v1/data-sources/{source_id}/sync

# View sync jobs
GET http://localhost:8000/api/v1/data-sources/{source_id}/sync-jobs
```

### Lineage Queries

```bash
# Table-level lineage
GET http://localhost:8000/api/v1/lineage/table/{dataset_id}?direction=both&depth=3

# Column-level lineage
GET http://localhost:8000/api/v1/lineage/column/{column_id}?direction=both&depth=5
```

See [API Documentation](http://localhost:8000/docs) for complete endpoint reference.

---

## Troubleshooting

### Common Issues

#### 1. Docker Not Running

**Error**: `Docker is not available`

**Solution**:
```bash
# Linux
sudo systemctl start docker

# Mac/Windows
# Start Docker Desktop application
```

#### 2. Port Already in Use

**Error**: `port is already allocated`

**Solution**:
```bash
# Find what's using the port (example: 8000)
# Linux/Mac
sudo lsof -i :8000

# Windows
netstat -ano | findstr :8000

# Stop the conflicting service
# Or change port in docker-compose.sample.yml
```

#### 3. Insufficient Memory

**Error**: Services crash or become unresponsive

**Solution**:
- Increase Docker memory limit (Docker Desktop → Settings → Resources)
- Close other applications
- Recommended: 8GB RAM allocated to Docker

#### 4. Sync Jobs Fail

**Error**: `Sync failed: Connection refused`

**Solution**:
```bash
# Check source databases are running
docker compose -f docker-compose.sample.yml ps

# View detailed logs
docker compose -f docker-compose.sample.yml logs postgres-source
docker compose -f docker-compose.sample.yml logs mysql-source

# Restart failed service
docker compose -f docker-compose.sample.yml restart postgres-source
```

#### 5. Validation Fails

**Error**: `Expected at least 10 datasets, found 0`

**Solution**:
```bash
# Re-run sync
python scripts/cli.py run sample-data

# Check sync job status via API
curl http://localhost:8000/api/v1/data-sources | jq

# View sync job details
curl "http://localhost:8000/api/v1/data-sources/{source_id}/sync-jobs" | jq
```

### Getting Help

1. **Check Logs**
   ```bash
   docker compose -f docker-compose.sample.yml logs -f
   ```

2. **Review Runbooks**
   - Each runbook has a detailed troubleshooting section

3. **Validation Report**
   ```bash
   python scripts/cli.py run validation
   ```

4. **Clean Restart**
   ```bash
   python scripts/cli.py run teardown --clean-volumes
   python scripts/cli.py deploy
   ```

---

## Development

### Modifying Sample Data

1. **Edit SQL Files**
   ```bash
   vim sample-data/postgres-source/init.sql
   vim sample-data/mysql-source/init.sql
   ```

2. **Rebuild Databases**
   ```bash
   python scripts/cli.py run teardown --clean-volumes
   python scripts/cli.py run infrastructure
   ```

### Adding New Data Sources

1. **Update Configuration**
   ```bash
   vim config/data-sources.json
   ```

2. **Add Connection Details**
   ```json
   {
     "name": "New Source",
     "source_type": "postgres",
     "connection_config": {
       "host": "hostname",
       "port": 5432,
       "database": "dbname"
     }
   }
   ```

3. **Redeploy**
   ```bash
   python scripts/cli.py run sample-data
   ```

### Testing Changes

```bash
# Test infrastructure
python scripts/cli.py run infrastructure
python scripts/cli.py run validation

# Test sample data
python scripts/cli.py run sample-data
python scripts/cli.py run validation

# Full integration test
python scripts/cli.py run teardown --clean-volumes
python scripts/cli.py deploy
```

---

## Production Considerations

⚠️ **WARNING**: This is a **sample/development deployment**.

**DO NOT** use in production without:

### Security Hardening
- Change all default passwords
- Enable SSL/TLS
- Configure authentication/authorization
- Set up network security (firewalls, VPCs)
- Implement secrets management
- Enable audit logging

### Scalability
- Use managed database services (RDS, Cloud SQL)
- Implement connection pooling
- Add load balancing
- Configure auto-scaling
- Optimize database indexes

### Reliability
- Set up monitoring and alerting
- Configure automated backups
- Implement disaster recovery
- Use health checks and liveness probes
- Set up log aggregation

### Compliance
- Implement data encryption (at rest and in transit)
- Configure data retention policies
- Enable compliance logging
- Implement access controls
- Conduct security audits

---

## File Structure

```
deployment/
├── README.md                           # This file
├── docker-compose.sample.yml           # Docker services configuration
├── scripts/
│   ├── cli.py                          # Main CLI interface
│   ├── utils.py                        # Shared utilities
│   ├── deploy_infrastructure.py        # Runbook 1 implementation
│   ├── deploy_sample_data.py           # Runbook 2 implementation
│   ├── validate_deployment.py          # Runbook 3 implementation
│   └── teardown.py                     # Runbook 4 implementation
├── runbooks/
│   ├── 01-infrastructure-deployment.md # Infrastructure runbook
│   ├── 02-sample-data-deployment.md    # Sample data runbook
│   ├── 03-validation.md                # Validation runbook
│   └── 04-teardown.md                  # Teardown runbook
├── config/
│   ├── data-sources.json               # Data source definitions
│   └── deployment-state.json           # Generated state file
├── sample-data/
│   ├── postgres-source/
│   │   └── init.sql                    # PostgreSQL sample data
│   ├── mysql-source/
│   │   └── init.sql                    # MySQL sample data
│   ├── dbt-project/
│   │   ├── dbt_project.yml             # dbt configuration
│   │   ├── profiles.yml                # dbt profiles
│   │   └── models/                     # dbt models
│   │       ├── staging/                # Staging layer
│   │       └── marts/                  # Marts layer
│   ├── python-jobs/
│   │   ├── customer_lifetime_value.py  # Pandas analytics
│   │   └── daily_order_metrics.py      # Polars analytics
│   └── delta-lake/                     # Output directory
```

---

## FAQ

### Q: How long does deployment take?
**A**: Full deployment takes 15-25 minutes (infrastructure 5-10 min, data 10-15 min).

### Q: Can I run this on Windows?
**A**: Yes! All scripts are cross-platform Python. Requires Docker Desktop with WSL2.

### Q: Do I need to install dbt separately?
**A**: No, dbt runs in a Docker container. No local installation needed.

### Q: How much data is created?
**A**: Sample data is small (~100 rows total). Minimal disk space (~500MB including Docker images).

### Q: Can I connect my own databases?
**A**: Yes! Edit `config/data-sources.json` with your connection details.

### Q: Is this production-ready?
**A**: No. This is for development/testing. See [Production Considerations](#production-considerations).

### Q: Can I deploy without Docker?
**A**: Not with this system. Docker provides isolation and consistency.

### Q: How do I see the lineage graph visually?
**A**: The backend API provides data. Frontend UI development is the next phase.

---

## Next Steps

After successful deployment:

1. **Explore the API**
   - Visit http://localhost:8000/docs
   - Try different lineage queries
   - Experiment with query parameters

2. **Understand the Data Flow**
   - Review sample data SQL files
   - Examine dbt models
   - Study Python transformation scripts

3. **Test Lineage Queries**
   - Query table-level lineage
   - Explore column-level lineage
   - Test impact analysis

4. **Begin UI Development**
   - Backend API is ready
   - Lineage data is available
   - Build visualization layer

---

## Contributing

Improvements welcome!

### Report Issues
- Use GitHub Issues
- Include error messages
- Describe steps to reproduce

### Submit Pull Requests
- Follow existing code style
- Update documentation
- Test changes end-to-end

### Improve Documentation
- Fix typos
- Add examples
- Clarify instructions

---

## License

See main repository LICENSE file.

---

## Support

- **Documentation**: See `runbooks/` directory
- **Issues**: GitHub Issues
- **API Docs**: http://localhost:8000/docs (when running)

---

**Built with ❤️ for data engineers who care about lineage**
