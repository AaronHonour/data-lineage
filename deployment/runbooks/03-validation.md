# Runbook 3: Deployment Validation

**Purpose**: Validate that the data lineage system is functioning correctly and the lineage graph was built successfully.

**Estimated Time**: 3-5 minutes

**Prerequisites**:
- Infrastructure deployed (Runbook 1)
- Sample data deployed (Runbook 2)
- All sync jobs completed

---

## Overview

This runbook performs comprehensive validation:

1. **API Health** - Verify API is responding
2. **Data Sources** - Check all sources are registered
3. **Dataset Discovery** - Validate datasets were found
4. **Transformation Discovery** - Confirm transformations exist
5. **Lineage Edges** - Verify column lineage was created
6. **Query Functionality** - Test lineage queries work

---

## Execution

### Automated Execution

```bash
# From deployment directory
cd deployment
python scripts/cli.py run validation
```

### Manual Validation

```bash
# 1. Check API health
curl http://localhost:8000/health

# 2. List data sources
curl http://localhost:8000/api/v1/data-sources | jq 'length'

# 3. Check sync job statistics
for source_id in $(curl -s http://localhost:8000/api/v1/data-sources | jq -r '.[].id'); do
  echo "Source: $source_id"
  curl -s "http://localhost:8000/api/v1/data-sources/$source_id/sync-jobs?limit=1" | jq '.[0].statistics'
done

# 4. Test lineage query (requires dataset_id)
# curl http://localhost:8000/api/v1/lineage/table/{dataset_id}
```

---

## Validation Tests

### Test 1: API Health Check

**Purpose**: Verify the API is running and accessible

**Expected Result**: HTTP 200 with `{"status": "healthy"}`

**Failure Scenarios**:
- Connection refused → API not running
- Timeout → Network/firewall issue
- 500 error → Application error

### Test 2: Data Sources Registration

**Purpose**: Verify all data sources were registered

**Expected Result**: At least 5 data sources

**Minimum Sources**:
- 1x PostgreSQL
- 1x MySQL
- 1x dbt
- 2x Python jobs
- (Optional: Delta Lake)

**Failure Scenarios**:
- Count < 5 → Registration failed
- Empty list → Sample data deployment not run

### Test 3: Dataset Discovery

**Purpose**: Verify datasets were discovered from sources

**Expected Result**: At least 10 datasets total

**Dataset Breakdown**:
- PostgreSQL: ~5 tables/views
- MySQL: ~5 tables/views
- dbt: ~5 models
- Python: ~2 scripts
- Delta Lake: ~2 tables (if Python jobs ran)

**Failure Scenarios**:
- Count < 10 → Connector discovery failed
- Count = 0 → Sync jobs didn't run

### Test 4: Transformation Discovery

**Purpose**: Verify transformations were found

**Expected Result**: At least 5 transformations

**Transformation Types**:
- SQL views (PostgreSQL/MySQL)
- dbt models (SQL)
- Python scripts (DataFrame operations)

**Failure Scenarios**:
- Count < 5 → Transformation extraction failed
- Count = 0 → No code parsed

### Test 5: Lineage Edges Creation

**Purpose**: Verify column-level lineage graph was built

**Expected Result**: At least 10 lineage edges

**Edge Types**:
- View → Base table columns
- dbt model → Source columns
- Python script → Database columns
- Cross-source lineage

**Failure Scenarios**:
- Count < 10 → Lineage extraction failed
- Count = 0 → Parser errors

### Test 6: Table Lineage Query

**Purpose**: Verify lineage query endpoints work

**Expected Result**: Endpoint returns successfully

**Note**: Full testing requires specific dataset IDs

---

## Validation Report

The validation script generates a detailed report:

```
================================================================================
                           Validation Report
================================================================================

Overall: 6/6 tests passed

✓ API Health Check
    API is healthy
✓ Data Sources Registration
    Found 6 registered data sources
✓ Dataset Discovery
    Discovered 18 datasets
✓ Transformation Discovery
    Discovered 10 transformations
✓ Lineage Edges
    Created 42 lineage edges
✓ Table Lineage Query
    Table lineage endpoint is available

================================================================================

🎉 All validation tests passed!

The lineage system is fully operational and ready for use.
```

---

## Success Criteria

| Metric | Minimum | Ideal | Status |
|--------|---------|-------|--------|
| Data Sources | 5 | 6 | ✓ |
| Datasets | 10 | 15-20 | ✓ |
| Transformations | 5 | 8-12 | ✓ |
| Lineage Edges | 10 | 30-50 | ✓ |

All minimum thresholds must pass for validation to succeed.

---

## Troubleshooting

### Problem: API health check fails

**Symptoms**:
```
✗ API Health Check
    API not responding
```

**Root Causes**:
1. API service not running
2. Port 8000 blocked
3. Container crashed

**Resolution**:
```bash
# Check API status
docker compose -f docker-compose.sample.yml ps lineage-api

# View logs
docker compose logs -f lineage-api

# Restart if needed
docker compose restart lineage-api

# Wait and retry validation
python scripts/cli.py run validation
```

### Problem: No data sources found

**Symptoms**:
```
✗ Data Sources Registration
    Expected at least 5 sources, found 0
```

**Root Cause**: Sample data deployment not run or failed

**Resolution**:
```bash
# Run sample data deployment
python scripts/cli.py run sample-data

# Then retry validation
python scripts/cli.py run validation
```

### Problem: Zero datasets discovered

**Symptoms**:
```
✗ Dataset Discovery
    Expected at least 10 datasets, found 0
```

**Root Causes**:
1. Sync jobs didn't complete
2. Connector configuration error
3. Source databases empty

**Resolution**:
```bash
# Check sync job status
curl http://localhost:8000/api/v1/data-sources | jq -r '.[].id' | while read id; do
  echo "=== Source: $id ==="
  curl -s "http://localhost:8000/api/v1/data-sources/$id/sync-jobs?limit=1" | jq '.[0] | {status, error_message, statistics}'
done

# Look for:
# - status: "failed" → Check error_message
# - status: "running" → Wait for completion
# - statistics.datasets_discovered: 0 → Configuration issue

# Verify source databases have data
docker exec postgres-source psql -U source_user -d ecommerce -c "\dt raw.*"
docker exec mysql-source mysql -u mysql_user -pmysql_pass auxiliary -e "SHOW TABLES;"

# Re-trigger sync if needed
curl -X POST http://localhost:8000/api/v1/data-sources/{source_id}/sync
```

### Problem: No lineage edges

**Symptoms**:
```
✗ Lineage Edges
    Expected at least 10 edges, found 0
```

**Root Causes**:
1. Transformations not found
2. Parser errors
3. FQN resolution failures

**Resolution**:
```bash
# Check parser logs
docker compose logs lineage-api | grep -i "lineage\|parser\|error"

# Verify transformations exist
curl http://localhost:8000/api/v1/data-sources | jq -r '.[].id' | while read id; do
  curl -s "http://localhost:8000/api/v1/data-sources/$id/sync-jobs?limit=1" | jq '.[0].statistics.transformations_discovered'
done

# Check for parser errors in sync jobs
curl -s "http://localhost:8000/api/v1/data-sources/{source_id}/sync-jobs?limit=1" | jq '.[0].error_message'

# Common issues:
# - SQL syntax errors in views
# - Python parsing errors
# - Missing source dataset references

# Fix and re-sync
curl -X POST http://localhost:8000/api/v1/data-sources/{source_id}/sync
```

### Problem: Validation timeout

**Symptoms**: Validation hangs or takes very long

**Root Cause**: Sync jobs still running

**Resolution**:
```bash
# Check if syncs are still in progress
curl http://localhost:8000/api/v1/data-sources | jq -r '.[].id' | while read id; do
  status=$(curl -s "http://localhost:8000/api/v1/data-sources/$id/sync-jobs?limit=1" | jq -r '.[0].status')
  echo "Source $id: $status"
done

# Wait for all syncs to complete, then retry validation
```

---

## Deep Dive Validation

For more detailed validation, use the API directly:

### Check Specific Dataset

```bash
# List all data sources and their datasets
curl http://localhost:8000/api/v1/data-sources | jq -r '.[].id' | while read source_id; do
  echo "=== Source: $source_id ==="
  curl -s "http://localhost:8000/api/v1/data-sources/$source_id/sync-jobs?limit=1" | \
    jq '{
      source: $source_id,
      datasets: .statistics.datasets_discovered,
      transformations: .statistics.transformations_discovered,
      edges: .statistics.lineage_edges_created
    }'
done
```

### Verify Column Lineage

```bash
# Get a sample dataset ID (e.g., dim_customers from dbt)
# Then query its lineage
curl "http://localhost:8000/api/v1/lineage/table/{dataset_id}?direction=both&depth=3" | jq
```

### Check Lineage Statistics

```bash
# Get overall lineage graph statistics
# (If this endpoint exists in your API)
curl http://localhost:8000/api/v1/lineage/statistics | jq
```

---

## Post-Validation Actions

### If Validation Passes ✓

**Congratulations!** Your data lineage system is ready.

Next steps:
1. Explore the API documentation: http://localhost:8000/docs
2. Query lineage for specific tables
3. Test impact analysis
4. Begin UI development (if planned)

### If Validation Fails ✗

**Don't panic!** Follow these steps:

1. **Read the error messages** - They usually indicate the issue
2. **Check logs** - Docker logs contain detailed error information
3. **Verify prerequisites** - Ensure infrastructure is healthy
4. **Re-run specific steps** - You can re-run individual runbooks
5. **Consult troubleshooting** - Review the troubleshooting section above
6. **Clean restart** - If all else fails, teardown and redeploy:
   ```bash
   python scripts/cli.py run teardown --clean-volumes
   python scripts/cli.py deploy  # Full deployment
   ```

---

## Expected Output Example

```
================================================================================
                       Deployment Validation - Runbook 3
================================================================================

================================================================================
                           Checking Prerequisites
================================================================================

ℹ Validating API health...
✓ API health check passed

================================================================================
                      Validating Data Sources
================================================================================

ℹ Validating data sources...
✓ Found 6 registered data sources
  - PostgreSQL Source - E-commerce (postgres)
  - MySQL Source - Auxiliary Systems (mysql)
  - dbt Project - Analytics (dbt)
  - Python Jobs - Customer Analytics (python)
  - Python Jobs - Daily Metrics (python)
  - Delta Lake - Analytics Output (delta)

================================================================================
                      Validating Dataset Discovery
================================================================================

ℹ Validating dataset discovery...
✓ Discovered 18 datasets

...
```

---

## Continuous Validation

For ongoing validation:

```bash
# Create a validation cron job (Linux/Mac)
# Every hour
0 * * * * cd /path/to/deployment && python scripts/cli.py run validation

# Or use a monitoring tool to check API health
curl http://localhost:8000/health
```

---

## Next Steps

After successful validation:

1. **Explore the System**
   - API docs: http://localhost:8000/docs
   - Query lineage endpoints
   - Test different query parameters

2. **Run Python Jobs** (if not done)
   ```bash
   docker exec lineage-api python /python-jobs/customer_lifetime_value.py
   docker exec lineage-api python /python-jobs/daily_order_metrics.py
   ```

3. **Experiment with Lineage Queries**
   - Get column-level lineage
   - Query table-level lineage
   - Test impact analysis
   - Try root cause analysis

4. **Begin UI Development**
   - You now have a validated backend
   - API is ready for frontend integration
   - Lineage graph data is available

---

## Validation Metrics Reference

| Metric | Source | API Endpoint |
|--------|--------|--------------|
| Data Sources | API | GET /api/v1/data-sources |
| Datasets | Sync Jobs | GET /api/v1/data-sources/{id}/sync-jobs |
| Transformations | Sync Jobs | GET /api/v1/data-sources/{id}/sync-jobs |
| Lineage Edges | Sync Jobs | GET /api/v1/data-sources/{id}/sync-jobs |
| Table Lineage | Lineage API | GET /api/v1/lineage/table/{id} |
| Column Lineage | Lineage API | GET /api/v1/lineage/column/{id} |
