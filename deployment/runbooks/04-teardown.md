# Runbook 4: Teardown

**Purpose**: Stop all services and optionally clean up data to prepare for redeployment or remove the deployment entirely.

**Estimated Time**: 2-3 minutes

**Prerequisites**: None (can be run at any time)

---

## Overview

This runbook provides multiple levels of teardown:

### Level 1: Stop Services (Preserve Data)
- Stops all Docker containers
- Preserves Docker volumes (data persists)
- Preserves deployment state
- Quick restart possible

### Level 2: Clean Volumes (Delete Data)
- Stops all Docker containers
- **Removes Docker volumes** (⚠️ all data deleted)
- Preserves deployment state
- Fresh start required

### Level 3: Complete Cleanup
- Stops all containers
- Removes all volumes
- Removes deployment state
- Removes generated files
- Clean slate

---

## Execution

### Basic Teardown (Preserve Data)

```bash
# From deployment directory
cd deployment
python scripts/cli.py run teardown
```

### Complete Teardown (Delete All Data)

```bash
python scripts/cli.py run teardown --clean-volumes --clean-state --clean-data
```

### With Confirmation Skip

```bash
# Skip confirmation prompts (use with caution!)
python scripts/cli.py run teardown --clean-volumes --yes
```

---

## Command Options

| Option | Description | Impact |
|--------|-------------|--------|
| (none) | Stop services only | Data preserved, fast restart |
| `--clean-volumes` | Remove Docker volumes | ⚠️ All database data deleted |
| `--clean-state` | Remove state file | Source registrations forgotten |
| `--clean-data` | Remove generated files | Delta Lake files deleted |
| `--yes` / `-y` | Skip confirmations | Auto-accept warnings |

---

## Steps Performed

### 1. Confirmation (if needed)

For destructive operations, you'll be prompted:

```
⚠️  This will delete all database data. Continue? [y/N]:
```

- `--clean-volumes` requires confirmation
- Use `--yes` to skip (automation)

### 2. Stop Docker Services

```bash
docker compose -f docker-compose.sample.yml down
```

This stops and removes:
- All containers
- Docker networks
- Anonymous volumes (not named volumes)

### 3. Remove Volumes (Optional)

```bash
docker compose -f docker-compose.sample.yml down -v
```

⚠️ **Warning**: This deletes:
- `lineage-db-data` → All lineage metadata
- `postgres-source-data` → Sample e-commerce data
- `mysql-source-data` → Sample auxiliary data

### 4. Clean State File (Optional)

Removes `config/deployment-state.json`

This contains:
- Registered data source IDs
- Source type mappings

Effect: Next deployment will register new sources

### 5. Clean Generated Data (Optional)

Removes files from `sample-data/delta-lake/`

This includes:
- `*.parquet` files from Python jobs
- Subdirectories

Effect: Python job outputs deleted

### 6. Verification

Checks that no services are still running:

```bash
docker compose -f docker-compose.sample.yml ps
```

Expected: Empty list

---

## Teardown Scenarios

### Scenario 1: Quick Restart

**Use Case**: Testing configuration changes

```bash
# Stop services
python scripts/cli.py run teardown

# Make configuration changes
vim docker-compose.sample.yml

# Restart
python scripts/cli.py run infrastructure
```

**Data State**: All data preserved, no re-sync needed

---

### Scenario 2: Fresh Data

**Use Case**: Testing with clean database

```bash
# Complete teardown
python scripts/cli.py run teardown --clean-volumes

# Redeploy everything
python scripts/cli.py deploy  # or run runbooks individually
```

**Data State**: All data deleted, full re-sync required

---

### Scenario 3: Reset Registration

**Use Case**: Re-register data sources with different config

```bash
# Stop and clean state
python scripts/cli.py run teardown --clean-state

# Update configuration
vim config/data-sources.json

# Redeploy sample data only
python scripts/cli.py run sample-data
```

**Data State**: Database data preserved, new source registrations

---

### Scenario 4: Complete Removal

**Use Case**: Removing deployment entirely

```bash
# Nuclear option - remove everything
python scripts/cli.py run teardown --clean-volumes --clean-state --clean-data --yes
```

**Data State**: Everything deleted, like deployment never existed

---

## Validation

After teardown, verify:

```bash
# Check no services running
docker compose -f docker-compose.sample.yml ps
# Expected: Empty

# Check no containers exist
docker ps -a | grep lineage
# Expected: No results

# Check volumes (should be empty if cleaned)
docker volume ls | grep lineage
# With --clean-volumes: No results
# Without: lineage-db-data, postgres-source-data, mysql-source-data

# Check API not accessible
curl http://localhost:8000/health
# Expected: Connection refused
```

---

## Troubleshooting

### Problem: Containers won't stop

**Symptoms**:
```
Error: Container lineage-api cannot be stopped
```

**Resolution**:
```bash
# Force stop containers
docker compose -f docker-compose.sample.yml down --timeout 5

# If still stuck, force kill
docker ps -a | grep lineage | awk '{print $1}' | xargs docker kill

# Remove containers
docker ps -a | grep lineage | awk '{print $1}' | xargs docker rm -f
```

### Problem: Volumes won't delete

**Symptoms**:
```
Error: volume is in use
```

**Resolution**:
```bash
# Ensure all containers using volume are stopped
docker ps -a

# Remove containers first
docker compose down

# Then remove volumes
docker volume rm lineage-db-data postgres-source-data mysql-source-data

# Or force remove
docker volume rm -f lineage-db-data
```

### Problem: Port still in use after teardown

**Symptoms**:
```
Error: port 8000 is already in use
```

**Resolution**:
```bash
# Check what's using the port
# Linux/Mac:
sudo lsof -i :8000

# Windows:
netstat -ano | findstr :8000

# If it's a zombie Docker container:
docker ps -a | grep 8000
docker rm -f <container_id>

# If it's another process, stop that process
```

### Problem: State file locked

**Symptoms**: Permission denied when deleting state file

**Resolution**:
```bash
# Linux/Mac:
sudo rm config/deployment-state.json

# Windows:
# Run PowerShell as Administrator
Remove-Item config\deployment-state.json -Force
```

---

## Data Recovery

### If You Accidentally Deleted Volumes

**Bad News**: Docker volumes are **permanently deleted** when removed.

**Prevention**: Always backup important data before using `--clean-volumes`

**Options**:
1. Redeploy from scratch (sample data is reproducible)
2. Restore from backup (if you have one)
3. Re-run sync jobs (if lineage metadata was deleted but sources intact)

### Backup Before Teardown

```bash
# Backup lineage database
docker exec lineage-db pg_dump -U lineage_user lineage > backup-lineage-$(date +%Y%m%d).sql

# Backup deployment state
cp config/deployment-state.json config/deployment-state.backup.json

# Then safely teardown
python scripts/cli.py run teardown --clean-volumes
```

### Restore After Teardown

```bash
# Redeploy infrastructure
python scripts/cli.py run infrastructure

# Restore database
cat backup-lineage-20240125.sql | docker exec -i lineage-db psql -U lineage_user lineage

# Restore state
cp config/deployment-state.backup.json config/deployment-state.json

# Verify
python scripts/cli.py run validation
```

---

## Manual Teardown

If the script fails, use manual commands:

```bash
# Stop services
docker compose -f docker-compose.sample.yml down

# Remove volumes
docker compose -f docker-compose.sample.yml down -v

# Or remove specific volumes
docker volume rm lineage-db-data
docker volume rm postgres-source-data
docker volume rm mysql-source-data

# Remove networks
docker network rm lineage-network

# Clean state
rm -f config/deployment-state.json

# Clean generated data
rm -rf sample-data/delta-lake/*.parquet
```

---

## Post-Teardown State

### After Basic Teardown

```
Docker Containers: ❌ Stopped
Docker Volumes:    ✓ Preserved
State File:        ✓ Preserved
Generated Data:    ✓ Preserved
```

**Quick Restart**: `python scripts/cli.py run infrastructure`

### After Complete Teardown

```
Docker Containers: ❌ Stopped
Docker Volumes:    ❌ Deleted
State File:        ❌ Deleted
Generated Data:    ❌ Deleted
```

**Full Redeploy Required**: `python scripts/cli.py deploy`

---

## Redeployment After Teardown

### After Basic Teardown (Data Preserved)

```bash
# Start infrastructure
python scripts/cli.py run infrastructure

# No need to re-register or re-sync!
# Data is still in volumes

# Verify
python scripts/cli.py run validation
```

### After Complete Teardown (Data Deleted)

```bash
# Full deployment sequence
python scripts/cli.py run infrastructure
python scripts/cli.py run sample-data
python scripts/cli.py run validation

# Or use shortcut
python scripts/cli.py deploy
```

---

## Automation

### Nightly Cleanup (Development)

```bash
# Cron job for nightly reset (Linux/Mac)
0 2 * * * cd /path/to/deployment && python scripts/cli.py run teardown --clean-volumes --yes && python scripts/cli.py deploy

# Windows Task Scheduler
# Action: python
# Arguments: scripts/cli.py run teardown --clean-volumes --yes
# Follow with deployment task
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Teardown Deployment
  run: |
    cd deployment
    python scripts/cli.py run teardown --clean-volumes --yes

- name: Redeploy
  run: |
    cd deployment
    python scripts/cli.py deploy
```

---

## Safety Checklist

Before running teardown with `--clean-volumes`:

- [ ] Backup any important data
- [ ] Verify you're in correct environment (not production!)
- [ ] Check no critical jobs are running
- [ ] Notify team members if shared environment
- [ ] Save any unsaved work
- [ ] Double-check the command
- [ ] Understand data will be **permanently deleted**

---

## Next Steps

### After Basic Teardown
→ Ready to restart: `python scripts/cli.py run infrastructure`

### After Complete Teardown
→ Ready to redeploy: `python scripts/cli.py deploy`

### If Done with Testing
→ All cleaned up! Infrastructure removed.

---

## Comparison: Teardown vs Reset

| Operation | Teardown | Reset (Redeploy) |
|-----------|----------|------------------|
| Stops services | ✓ | ✓ then restart |
| Deletes data | Optional | Optional |
| Cleans state | Optional | No |
| Re-registers sources | - | ✓ |
| Re-syncs lineage | - | ✓ |
| **Use when** | Done/changing config | Testing/refreshing |

---

## Resources

- Docker Compose Down: https://docs.docker.com/compose/reference/down/
- Docker Volume Management: https://docs.docker.com/storage/volumes/
- Container Lifecycle: https://docs.docker.com/engine/reference/run/

---

## Warning Labels

⚠️ **Destructive Operations**

These flags **permanently delete data**:
- `--clean-volumes`: Deletes all database data
- `--clean-state`: Loses source registration tracking
- `--clean-data`: Deletes Python job outputs

**Always** have backups before using destructive flags in any environment that contains valuable data!

🔒 **Production Warning**

This deployment is **not** production-ready. Do not use teardown scripts on production systems without proper:
- Change management procedures
- Backup verification
- Stakeholder approval
- Rollback plans
