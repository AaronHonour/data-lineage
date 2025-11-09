# SQL Lineage Parsing - Testing Framework

## Overview

This is a comprehensive testing and regression framework for SQL lineage parsing. It provides:

- **JSON-based test case definitions** with schema validation
- **Version-controlled snapshots** for regression testing
- **Performance testing** with time thresholds
- **SQL feature coverage tracking** across 67+ SQL features
- **Integration testing** with real SQL parsing
- **Automated reporting** and CI/CD integration

## Quick Start

### Running Tests

```bash
# Run all Phase 1 tests
pytest tests/integration/test_lineage_parsing_integration.py::TestLineageParsingIntegration::test_phase1_basic_queries -v -s

# Run schema validation only
pytest tests/integration/test_lineage_parsing_integration.py::TestLineageParsingIntegration::test_load_test_cases_schema_validation -v

# Run performance benchmarks
pytest tests/integration/test_lineage_parsing_integration.py::TestLineageParsingIntegration::test_performance_benchmark -v -s -m slow

# Run snapshot management tests
pytest tests/integration/test_lineage_parsing_integration.py::TestLineageParsingIntegration::test_snapshot_management -v
```

### Creating New Test Cases

1. **Use the JSON schema**:
   ```json
   {
     "test_id": "join-001",
     "name": "Simple INNER JOIN",
     "description": "Test basic INNER JOIN lineage tracking",
     "difficulty": "intermediate",
     "phase": 2,
     "tags": ["inner_join", "joins"],
     "dialect": "postgres",
     "sql": "SELECT c.id, o.total FROM customers c JOIN orders o ON c.id = o.customer_id",
     "source_tables": [
       {
         "name": "customers",
         "columns": [{"name": "id", "type": "INTEGER"}]
       },
       {
         "name": "orders",
         "columns": [{"name": "customer_id", "type": "INTEGER"}, {"name": "total", "type": "DECIMAL"}]
       }
     ],
     "expected_lineage": [
       {
         "target": "result.id",
         "sources": ["customers.id"],
         "transformation_type": "projection"
       },
       {
         "target": "result.total",
         "sources": ["orders.total"],
         "transformation_type": "projection"
       }
     ],
     "min_confidence": 0.9,
     "max_parse_time_ms": 3000
   }
   ```

2. **Validate the test case**:
   ```python
   from tests.utils.test_case_loader import TestCaseLoader

   loader = TestCaseLoader()
   test_case = loader.load_test_case(Path("my_test.json"))
   ```

3. **Add to appropriate phase directory**:
   - `phase1_basic/` - Simple SELECT, projections, basic transformations
   - `phase2_joins/` - JOIN queries
   - `phase3_aggregations/` - GROUP BY, aggregate functions
   - `phase4_subqueries/` - Subqueries and CTEs
   - `phase5_advanced/` - Window functions, UNION, advanced features
   - `phase6_edge_cases/` - Edge cases and complex scenarios

## Directory Structure

```
tests/
├── fixtures/
│   ├── golden/                    # Version-controlled snapshots
│   │   ├── basic-001.snapshot.json
│   │   └── _metadata/
│   │       └── basic-001.meta.json
│   └── schemas/
│       └── test_case_schema.json  # JSON schema for test cases
│
├── test_cases/
│   ├── phase1_basic/
│   │   ├── 01_simple_projections.json  # 10 test cases
│   │   └── 02_simple_transformations.json  # 10 test cases
│   ├── phase2_joins/
│   ├── phase3_aggregations/
│   ├── phase4_subqueries/
│   ├── phase5_advanced/
│   └── phase6_edge_cases/
│
├── utils/
│   ├── test_case_loader.py        # Load and validate test cases
│   ├── regression_framework.py    # Snapshot management
│   ├── performance_testing.py     # Performance benchmarking
│   └── coverage_tracker.py        # SQL feature coverage tracking
│
├── integration/
│   └── test_lineage_parsing_integration.py  # Main integration tests
│
├── unit/
│   └── lineage_parser/            # Unit tests for parser components
│
├── performance/                   # Performance-specific tests
│
└── README.md                      # This file
```

## Test Case Schema

### Required Fields

- `test_id` (string): Unique identifier (e.g., "basic-001")
- `name` (string): Human-readable test name
- `difficulty` (enum): "basic", "intermediate", "advanced", "expert", "edge_case"
- `sql` (string): SQL query to test
- `expected_lineage` (array): Expected lineage relationships

### Optional Fields

- `description` (string): Detailed description
- `phase` (integer 1-6): Development phase
- `tags` (array): Feature tags for coverage tracking
- `dialect` (string): SQL dialect (default: "postgres")
- `source_tables` (array): Table schema definitions
- `min_confidence` (float 0.0-1.0): Minimum acceptable confidence (default: 0.8)
- `max_parse_time_ms` (integer): Max allowed parse time (default: 5000)
- `skip` (boolean): Skip this test
- `skip_reason` (string): Reason for skipping

## Regression Testing

### How It Works

1. **First Run**: Creates baseline snapshot
   ```
   tests/fixtures/golden/
   ├── basic-001.snapshot.json
   └── _metadata/
       └── basic-001.meta.json
   ```

2. **Subsequent Runs**: Compares against snapshot
   - ✓ Pass if results match
   - ✗ Fail if results differ (shows diff)

3. **Baseline Management**:
   ```python
   # Approve new baseline
   regression_tester.approve_baseline(test_id, new_data, notes="Updated for bug fix")

   # Update existing baseline
   regression_tester.update_baseline(test_id, new_data, notes="Intentional change")

   # Delete snapshot
   snapshot_manager.delete_snapshot(test_id)
   ```

### Version Control

- Snapshots are stored in `tests/fixtures/golden/`
- **Commit snapshots to git** for version control
- Changes to snapshots should be reviewed in PRs
- Metadata tracks when baselines were created/updated

## Performance Testing

### Parse Time Thresholds

Each test case can specify `max_parse_time_ms`:

```json
{
  "test_id": "perf-001",
  "max_parse_time_ms": 1000,
  ...
}
```

### Benchmarking

```python
from tests.utils.performance_testing import PerformanceTester

tester = PerformanceTester(max_parse_time_ms=5000)

# Run single test
metrics = tester.measure_parse_time(
    test_id="test-001",
    parse_func=parser.extract_lineage,
    sql="SELECT * FROM users"
)

# Run benchmark (multiple iterations)
benchmark = tester.benchmark(
    test_id="test-001",
    parse_func=parser.extract_lineage,
    sql="SELECT * FROM users",
    iterations=10
)

print(f"Avg: {benchmark.avg_time_ms:.2f}ms")
print(f"Min: {benchmark.min_time_ms:.2f}ms")
print(f"Max: {benchmark.max_time_ms:.2f}ms")
```

### Large File Testing

```python
from tests.utils.performance_testing import LargeFileTester

# Generate large SQL file
filepath = LargeFileTester.create_large_sql_file(
    Path("large_test.sql"),
    num_queries=100,
    tables_per_query=10
)

# Test parsing performance
result = LargeFileTester.test_large_file(
    filepath,
    parse_func=parser.extract_lineage,
    max_time_ms=30000
)
```

## Coverage Tracking

### SQL Features Tracked

67+ SQL features across 9 categories:
- **basic** (7 features): SELECT, WHERE, DISTINCT, etc.
- **transformations** (9 features): CONCAT, CAST, CASE, etc.
- **joins** (8 features): INNER, LEFT, RIGHT, FULL, CROSS, etc.
- **aggregations** (9 features): SUM, COUNT, AVG, GROUP BY, etc.
- **subqueries** (7 features): Scalar, IN, EXISTS, correlated, etc.
- **advanced** (12 features): CTE, window functions, UNION, etc.
- **dml** (4 features): INSERT...SELECT, UPDATE, DELETE, MERGE
- **ddl** (3 features): CREATE VIEW, materialized views, etc.
- **edge_cases** (8 features): LATERAL, PIVOT, JSONB, arrays, etc.

### Usage

```python
from tests.utils.coverage_tracker import SQLFeatureCoverage

tracker = SQLFeatureCoverage()

# Mark features from test tags
tracker.mark_features_from_tags(["inner_join", "concat"], passed=True)

# Get coverage report
report = tracker.get_full_coverage_report()

# Print formatted report
tracker.print_coverage_report()

# Save to JSON
tracker.save_coverage_report(Path("coverage.json"))
```

## Configuration Parameters

### Test Case Defaults

```json
{
  "min_confidence": 0.8,        // Accept 80%+ confidence for complex queries
  "max_parse_time_ms": 5000,    // 5 second timeout per query
  "dialect": "postgres"          // Default SQL dialect
}
```

### Regression Framework

```python
regression_tester = RegressionTester(
    snapshot_manager,
    auto_approve=True,   # Auto-approve new baselines (dev mode)
    verbose=True         # Print detailed output
)
```

**Production/CI Settings**:
```python
regression_tester = RegressionTester(
    snapshot_manager,
    auto_approve=False,  # Require manual approval
    verbose=False
)
```

## CI/CD Integration

### GitHub Actions Workflow

See `.github/workflows/nightly-regression-tests.yml`

**Features**:
- Runs nightly at 2 AM UTC
- Runs on push to main/develop
- Manual trigger available
- Uploads test results and coverage reports
- Comments on PRs with results
- Fails on regression failures

### Manual Trigger

```bash
# Via GitHub UI: Actions → Nightly Regression Tests → Run workflow

# Via gh CLI:
gh workflow run nightly-regression-tests.yml
```

## Development Workflow

### Phase 1: Basic SQL (Current)

**Focus**: Simple SELECT, projections, basic transformations
**Status**: 20 test cases created
**Coverage**: Basic features

```bash
pytest tests/integration/test_lineage_parsing_integration.py::TestLineageParsingIntegration::test_phase1_basic_queries -v -s
```

### Phase 2: Joins (Next)

**TODO**:
1. Create test cases for INNER, LEFT, RIGHT, FULL JOIN
2. Test multi-table joins
3. Test complex join conditions
4. Target: 25+ test cases

### Phase 3: Aggregations

**TODO**:
1. GROUP BY with single/multiple columns
2. Aggregate functions (SUM, COUNT, AVG, MIN, MAX)
3. HAVING clauses
4. COUNT(DISTINCT)
5. Target: 20+ test cases

### Phase 4: Subqueries

**TODO**:
1. Scalar subqueries
2. IN/EXISTS subqueries
3. Correlated subqueries
4. Subqueries in FROM/WHERE
5. Target: 15+ test cases

### Phase 5: Advanced

**TODO**:
1. CTEs (WITH clauses)
2. Recursive CTEs
3. Window functions (ROW_NUMBER, RANK, LAG, LEAD)
4. UNION/INTERSECT/EXCEPT
5. Target: 25+ test cases

### Phase 6: Edge Cases

**TODO**:
1. LATERAL joins
2. PIVOT/UNPIVOT
3. JSONB operations
4. Array operations
5. Recursive hierarchical queries
6. Target: 15+ test cases

## Known Issues

### Issue #1: Empty Source Columns

**Status**: Identified via testing framework ✓

**Problem**: sqlglot returns empty `source_columns` list

**Root Cause**: Not providing schema to sqlglot

**Solution**: Need to integrate table schema into SQL parser:
```python
# Current (broken)
lineage = sqlglot_lineage(col_name, sql, dialect=self.dialect, schema={})

# Fixed (TODO)
lineage = sqlglot_lineage(col_name, sql, dialect=self.dialect, schema=table_schemas)
```

**Test Results**:
- ✓ Framework detects the issue
- ✓ All 20 tests show consistent "empty sources" error
- ✓ Performance is good (avg 4.13ms)
- ✓ Schema validation passes

## Metrics & Benchmarks

### Current Performance (Phase 1, 20 tests)

```
Total Tests:           20
Successful:            20
Failed:                0
Avg Parse Time:        4.13ms
Min Parse Time:        1.06ms
Max Parse Time:        19.05ms
Median Parse Time:     1.77ms
Within Threshold:      20/20 (100%)
```

### Success Criteria

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Parse time (simple) | < 5ms | 1.77ms | ✅ |
| Parse time (complex) | < 50ms | - | ⏳ |
| Large file (1000 lines) | < 30s | - | ⏳ |
| Accuracy (basic) | > 95% | 0% | ⚠️  (parser bug) |
| Accuracy (joins) | > 90% | - | ⏳ |
| Accuracy (aggregations) | > 90% | - | ⏳ |
| Coverage | > 80% | 0% | ⏳ |

## Best Practices

### Writing Test Cases

1. **One concept per test**: Each test should validate one SQL feature
2. **Clear naming**: Use descriptive test IDs and names
3. **Add tags**: Helps with coverage tracking
4. **Set realistic thresholds**: `min_confidence` and `max_parse_time_ms`
5. **Document edge cases**: Use `description` field
6. **Start simple**: Phase 1 → Phase 6 progression

### Regression Testing

1. **Review snapshot diffs**: Don't blindly approve changes
2. **Commit snapshots**: Version control is critical
3. **Document changes**: Use `notes` when updating baselines
4. **Validate manually**: Test complex changes before approving

### Performance Testing

1. **Set realistic limits**: Don't make tests flaky
2. **Test at scale**: Include large file tests
3. **Profile slow queries**: Use `PerformanceProfiler`
4. **Monitor trends**: Track performance over time

## Troubleshooting

### Tests Failing Unexpectedly

```bash
# Check if test case JSON is valid
pytest tests/integration/test_lineage_parsing_integration.py::TestLineageParsingIntegration::test_load_test_cases_schema_validation -v

# Run single test in verbose mode
pytest tests/integration/test_lineage_parsing_integration.py -v -s -k "basic-001"

# Check snapshot integrity
python -c "
from tests.utils.regression_framework import LineageSnapshot
from pathlib import Path
sm = LineageSnapshot(Path('tests/fixtures/golden'))
print(sm.list_snapshots())
"
```

### Performance Issues

```bash
# Profile a specific query
python -c "
from tests.utils.performance_testing import PerformanceProfiler
from app.infrastructure.parsers.sql_parser import SQLLineageExtractor

parser = SQLLineageExtractor()
sql = 'SELECT * FROM users WHERE id > 100'

PerformanceProfiler.profile_parse(
    lambda s: parser.extract_lineage(s, 'result'),
    sql,
    Path('profile_output.txt')
)
"
```

## Contributing

1. **Add test cases**: Focus on uncovered features
2. **Report bugs**: Use test framework to reproduce
3. **Improve performance**: Profile and optimize
4. **Document findings**: Update this README

## References

- [JSON Schema Specification](http://json-schema.org/)
- [sqlglot Documentation](https://github.com/tobymao/sqlglot)
- [pytest Documentation](https://docs.pytest.org/)
- [DeepDiff Documentation](https://zepworks.com/deepdiff/)

## License

MIT License - See root LICENSE file
