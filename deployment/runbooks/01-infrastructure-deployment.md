# Runbook 1: Infrastructure Deployment

**Purpose**: Deploy all Docker services required for the data lineage system.

**Estimated Time**: 5-10 minutes

**Prerequisites**:
- Docker installed and running
- Docker Compose V2 installed
- At least 4GB free RAM
- At least 5GB free disk space

---

## Overview

This runbook deploys the following services:

1. **lineage-db** (PostgreSQL 15)
   - Purpose: Stores lineage metadata
   - Port: 5432
   - Credentials: lineage_user / lineage_pass

2. **postgres-source** (PostgreSQL 15)
   - Purpose: Sample operational database (e-commerce data)
   - Port: 5433 (mapped from 5432)
   - Credentials: source_user / source_pass

3. **mysql-source** (MySQL 8.0)
   - Purpose: Sample auxiliary database (inventory, shipping)
   - Port: 3306
   - Credentials: mysql_user / mysql_pass

4. **lineage-api** (FastAPI)
   - Purpose: REST API for lineage system
   - Port: 8000
   - Health check: http://localhost:8000/health

5. **dbt** (dbt-postgres)
   - Purpose: Transformation service
   - Not exposed externally

---

## Execution

### Automated Execution

```bash
# From deployment directory
cd deployment
python scripts/cli.py run infrastructure
```

### Manual Execution

```bash
# Start services
docker compose -f docker-compose.sample.yml up -d

# Wait for services to be healthy
docker compose -f docker-compose.sample.yml ps

# Check API health
curl http://localhost:8000/health
```

---

## Steps Performed

### 1. Prerequisites Check
- Verifies Docker is installed and running
- Checks docker-compose.sample.yml exists
- Validates system resources

### 2. Service Startup
- Pulls required Docker images (if not cached)
- Creates Docker network: lineage-network
- Creates Docker volumes for data persistence
- Starts all containers in detached mode

### 3. Health Checks
- Waits for lineage-db to accept connections (max 120s)
- Waits for postgres-source to accept connections (max 120s)
- Waits for mysql-source to accept connections (max 120s)
- Waits for lineage-api to respond to /health (max 180s)

### 4. Verification
- Lists all running services
- Verifies API health endpoint returns 200
- Tests database connectivity via API

### 5. Success Output
Prints service endpoints and next steps

---

## Validation

After successful deployment, verify:

```bash
# Check all services are running
docker compose -f docker-compose.sample.yml ps

# Expected output: All services should show "Up" status

# Test API connectivity
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# Test API docs
curl http://localhost:8000/docs
# Expected: HTML response (Swagger UI)

# Test data sources endpoint
curl http://localhost:8000/api/v1/data-sources
# Expected: Empty array [] (no sources registered yet)
```

---

## Troubleshooting

### Problem: Docker not found
**Symptom**: "Docker is not available"

**Solution**:
```bash
# Check Docker installation
docker --version

# Start Docker service (Linux)
sudo systemctl start docker

# Start Docker Desktop (Mac/Windows)
# Launch Docker Desktop application
```

### Problem: Port already in use
**Symptom**: "port is already allocated"

**Solution**:
```bash
# Check what's using the port
# Linux/Mac:
sudo lsof -i :5432
sudo lsof -i :8000

# Windows:
netstat -ano | findstr :5432
netstat -ano | findstr :8000

# Stop conflicting service or change port in docker-compose.sample.yml
```

### Problem: Service unhealthy
**Symptom**: Container exits or health check fails

**Solution**:
```bash
# View logs for specific service
docker compose -f docker-compose.sample.yml logs lineage-api
docker compose -f docker-compose.sample.yml logs lineage-db

# Restart specific service
docker compose -f docker-compose.sample.yml restart lineage-api

# Full restart
docker compose -f docker-compose.sample.yml down
docker compose -f docker-compose.sample.yml up -d
```

### Problem: Insufficient resources
**Symptom**: Services start but crash repeatedly

**Solution**:
- Increase Docker resource limits (Docker Desktop Settings)
- Close other applications to free RAM
- Check disk space: `df -h` (Linux/Mac) or `dir` (Windows)

---

## Rollback

If deployment fails, the script automatically rolls back:

```bash
# Manual rollback
docker compose -f docker-compose.sample.yml down

# This stops all services but preserves volumes
# To also remove volumes (delete all data):
docker compose -f docker-compose.sample.yml down -v
```

---

## Next Steps

After successful infrastructure deployment:

1. **Register Data Sources**
   ```bash
   python scripts/cli.py run sample-data
   ```

2. **Validate Deployment**
   ```bash
   python scripts/cli.py run validation
   ```

---

## Service Endpoints

| Service | Endpoint | Credentials |
|---------|----------|-------------|
| API | http://localhost:8000 | N/A |
| API Docs | http://localhost:8000/docs | N/A |
| Lineage DB | localhost:5432 | lineage_user / lineage_pass |
| PostgreSQL Source | localhost:5433 | source_user / source_pass |
| MySQL Source | localhost:3306 | mysql_user / mysql_pass |

---

## Data Persistence

The following Docker volumes are created for data persistence:

- `lineage-db-data`: Lineage metadata
- `postgres-source-data`: Sample e-commerce data
- `mysql-source-data`: Sample auxiliary data

Data persists across container restarts unless volumes are explicitly removed.

---

## Security Considerations

⚠️ **WARNING**: This is a sample deployment for development/testing only.

**DO NOT use in production without:**
- Changing default passwords
- Implementing proper network security
- Enabling SSL/TLS
- Configuring authentication/authorization
- Setting up proper backups
- Following security best practices

---

## Additional Resources

- Docker Compose documentation: https://docs.docker.com/compose/
- FastAPI documentation: https://fastapi.tiangolo.com/
- PostgreSQL documentation: https://www.postgresql.org/docs/
- MySQL documentation: https://dev.mysql.com/doc/
