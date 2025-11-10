# Runbook 2: Sample Data Deployment

**Purpose**: Register data sources with the lineage system and trigger synchronization to build the lineage graph.

**Estimated Time**: 10-15 minutes (includes sync time)

**Prerequisites**:
- Infrastructure deployment completed (Runbook 1)
- All services healthy and running
- API accessible at http://localhost:8000

---

## Overview

This runbook performs the following operations:

1. **Register Data Sources**
   - PostgreSQL Source (e-commerce operational data)
   - MySQL Source (auxiliary systems)
   - dbt Project (transformation models)
   - Python Jobs (analytics scripts)
   - Delta Lake (analytics output)

2. **Trigger Synchronization**
   - Discover datasets and columns
   - Discover transformations
   - Extract column-level lineage
   - Build lineage graph

3. **Verify Success**
   - Check sync job completion
   - Validate statistics
   - Confirm lineage edges created

---

## Data Flow

The sample deployment creates this data flow:

```
┌─────────────────┐
│ PostgreSQL      │
│ (raw tables)    │──┐
│ - customers     │  │
│ - orders        │  │
│ - products      │  │
└─────────────────┘  │
                     │
┌─────────────────┐  │     ┌─────────────────┐
│ MySQL           │  │     │ dbt             │
│ (auxiliary)     │  ├────▶│ (staging/marts) │──┐
│ - inventory     │  │     │ - stg_customers │  │
│ - deliveries    │  │     │ - dim_customers │  │
└─────────────────┘  │     │ - fct_orders    │  │
                     │     └─────────────────┘  │
                     │                          │
                     │     ┌─────────────────┐  │
                     │     │ Python Jobs     │  │
                     └────▶│ (analytics)     │◀─┘
                           │ - customer_ltv  │
                           │ - daily_metrics │
                           └────────┬────────┘
                                    │
                           ┌────────▼────────┐
                           │ Delta Lake      │
                           │ (output tables) │
                           └─────────────────┘
```

---

## Execution

### Automated Execution

```bash
# From deployment directory
cd deployment
python scripts/cli.py run sample-data
```

### Manual Execution (Advanced)

```bash
# Register each data source manually via API
curl -X POST http://localhost:8000/api/v1/data-sources \
  -H "Content-Type: application/json" \
  -d @config/data-sources.json

# Trigger sync for a specific source
curl -X POST http://localhost:8000/api/v1/data-sources/{source_id}/sync

# Check sync status
curl http://localhost:8000/api/v1/data-sources/{source_id}/sync-jobs
```

---

## Steps Performed

### 1. Prerequisites Check
- Verifies API is accessible
- Checks infrastructure is running
- Validates configuration file exists

### 2. Load Configuration
- Reads `config/data-sources.json`
- Validates JSON structure
- Extracts data source definitions

### 3. Register Data Sources
For each data source:
- Sends POST request to `/api/v1/data-sources`
- Receives source ID in response
- Saves ID to deployment state file
- Handles duplicate registration (idempotent)

### 4. Trigger Synchronization
For each registered source:
- Sends POST request to `/api/v1/data-sources/{id}/sync`
- Receives sync job ID
- Begins polling for completion

### 5. Monitor Sync Progress
- Polls `/api/v1/data-sources/{id}/sync-jobs` every 5 seconds
- Displays progress indicators
- Waits for 'completed' status (max 5 minutes per source)
- Captures and displays statistics

### 6. Display Results
- Shows summary of registered sources
- Lists datasets discovered
- Shows transformations found
- Reports lineage edges created

---

## Expected Results

After successful deployment, you should see:

| Metric | Expected Count |
|--------|----------------|
| Data Sources Registered | 6 |
| Datasets Discovered | 15-20 |
| Transformations Found | 8-12 |
| Lineage Edges Created | 30-50 |

### Data Source Breakdown

1. **PostgreSQL Source**
   - Tables: raw.customers, raw.orders, raw.products, raw.order_items
   - Views: raw.customer_order_summary
   - Columns: ~25

2. **MySQL Source**
   - Tables: auxiliary.inventory, auxiliary.deliveries, auxiliary.warehouses
   - Views: auxiliary.low_stock_alerts, auxiliary.delivery_performance
   - Columns: ~20

3. **dbt Project**
   - Models: stg_customers, stg_orders, stg_products, dim_customers, fct_orders
   - Columns: ~40

4. **Python Jobs**
   - Scripts: customer_lifetime_value.py, daily_order_metrics.py
   - Lineage: SQL reads + Parquet writes

5. **Delta Lake**
   - Tables: customer_ltv, daily_order_metrics (when Python jobs run)

---

## Validation

Verify deployment success:

```bash
# List all registered data sources
curl http://localhost:8000/api/v1/data-sources | jq

# Check specific source details
curl http://localhost:8000/api/v1/data-sources/{source_id} | jq

# View sync job history
curl http://localhost:8000/api/v1/data-sources/{source_id}/sync-jobs | jq

# Expected output structure:
# [{
#   "id": "...",
#   "status": "completed",
#   "statistics": {
#     "datasets_discovered": 5,
#     "transformations_discovered": 2,
#     "lineage_edges_created": 15
#   }
# }]
```

---

## Troubleshooting

### Problem: API not accessible
**Symptom**: "API is not available"

**Solution**:
```bash
# Check API service status
docker compose -f docker-compose.sample.yml ps lineage-api

# View API logs
docker compose -f docker-compose.sample.yml logs -f lineage-api

# Restart API service
docker compose -f docker-compose.sample.yml restart lineage-api

# Wait for health check
curl http://localhost:8000/health
```

### Problem: Sync job fails
**Symptom**: Sync status shows 'failed'

**Solution**:
```bash
# Check error message in sync job
curl http://localhost:8000/api/v1/data-sources/{source_id}/sync-jobs | jq '.[0].error_message'

# Common issues:
# 1. Connection refused → Check source database is running
# 2. Authentication failed → Verify credentials in config
# 3. Schema not found → Check database/schema names
# 4. Timeout → Increase timeout or check network

# View detailed logs
docker compose logs -f lineage-api
```

### Problem: Sync timeout
**Symptom**: "Sync timeout after 300 seconds"

**Solution**:
- Large datasets may take longer
- Check if sync is still running in background
- Monitor database CPU/memory usage
- Consider increasing timeout in script

### Problem: Zero datasets discovered
**Symptom**: "datasets_discovered: 0"

**Solution**:
```bash
# Verify source database has data
docker exec postgres-source psql -U source_user -d ecommerce -c "SELECT * FROM raw.customers LIMIT 1;"

# Check connector configuration
curl http://localhost:8000/api/v1/data-sources/{source_id} | jq '.connection_config'

# Verify schemas are correct
# PostgreSQL: Should include ["raw"]
# MySQL: Should connect to "auxiliary" database
```

### Problem: Duplicate registration
**Symptom**: "Data source already exists"

**Solution**:
- This is expected behavior (idempotent)
- Existing source ID will be reused
- Check `config/deployment-state.json` for source mappings
- Delete state file to force re-registration:
  ```bash
  rm config/deployment-state.json
  ```

---

## Sync Job States

| State | Description | Action |
|-------|-------------|--------|
| pending | Job queued, not started | Wait |
| running | Sync in progress | Monitor progress |
| completed | Sync finished successfully | Proceed to validation |
| failed | Error occurred | Check error_message, retry |

---

## Deployment State File

The script maintains a state file at `config/deployment-state.json`:

```json
{
  "data_sources": {
    "PostgreSQL Source - E-commerce": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "postgres"
    },
    ...
  }
}
```

This enables:
- Idempotent operations
- Source ID tracking
- Quick re-deployment

**To reset**: Delete this file before re-running

---

## Re-running Sync

To re-sync an existing source:

```bash
# Get source ID from state file
cat config/deployment-state.json | jq '.data_sources'

# Trigger new sync
curl -X POST http://localhost:8000/api/v1/data-sources/{source_id}/sync

# Or re-run entire deployment
python scripts/cli.py run sample-data
```

---

## Next Steps

After successful sample data deployment:

1. **Run Validation**
   ```bash
   python scripts/cli.py run validation
   ```

2. **Explore Lineage**
   ```bash
   # View API documentation
   open http://localhost:8000/docs

   # Query table lineage
   # (Get dataset_id from API first)
   curl http://localhost:8000/api/v1/lineage/table/{dataset_id}
   ```

3. **Run Python Jobs** (Optional)
   ```bash
   # Execute analytics jobs to create Delta Lake tables
   docker exec lineage-api python /python-jobs/customer_lifetime_value.py
   docker exec lineage-api python /python-jobs/daily_order_metrics.py

   # Then re-sync to discover Delta Lake tables
   curl -X POST http://localhost:8000/api/v1/data-sources/{delta_source_id}/sync
   ```

---

## Performance Considerations

- First sync takes longer (schema discovery + metadata caching)
- Subsequent syncs are faster (incremental updates)
- Large datasets (1M+ rows) may require timeout adjustments
- Python parsing is CPU-intensive for large scripts
- Consider running syncs sequentially for resource-constrained systems

---

## Data Privacy

⚠️ **Sample Data Notice**

The sample data includes fictional:
- Customer names and emails
- Order information
- Product catalogs

**Do NOT** use this deployment with real customer data without proper:
- Data anonymization
- Access controls
- Compliance verification (GDPR, CCPA, etc.)
- Security hardening
