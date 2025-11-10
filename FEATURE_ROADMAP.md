# Data Lineage Tool - Feature Development Roadmap

## Executive Summary

**Current State**: Production-ready backend with comprehensive connectors, functional React frontend with basic lineage visualization, but **critical testing gaps** (25% vs 90% target).

**Recommendation**: Complete Phase 1 testing (Backend API + Services) before major feature development to prevent regressions.

**Timeline**: 12-16 weeks for complete implementation.

---

## Phase 0: Testing Foundation (CRITICAL PREREQUISITE) 🔴

**Duration**: 3-4 weeks
**Priority**: CRITICAL
**Status**: Not Started

### Why This Matters
Without comprehensive tests, adding new features will:
- Introduce regressions without detection
- Make debugging significantly harder
- Increase technical debt exponentially
- Risk breaking existing functionality

### Deliverables
1. **Backend API Tests** (~50 tests)
   - All endpoint coverage (auth, data sources, sync, lineage)
   - Error handling and validation
   - Authentication flow
   - Coverage: 90%+

2. **Backend Service Tests** (~30 tests)
   - LineageSyncService orchestration
   - LineageQueryService graph queries
   - FQN resolution
   - Transaction management
   - Coverage: 90%+

3. **Backend Connector Tests** (~60 tests, 10 per connector)
   - PostgreSQL, MySQL, SQL Server
   - dbt, Python (pandas, polars, pyspark)
   - Iceberg, Delta Lake
   - Coverage: 80%+

4. **Frontend Component Tests** (~40 tests)
   - All atoms, molecules, organisms
   - User interactions
   - Accessibility
   - Coverage: 90%+

5. **Frontend Page Tests** (~50 tests)
   - All pages with loading/error states
   - Navigation and routing
   - Coverage: 85%+

6. **E2E Tests** (~20 tests)
   - Critical user flows
   - Cross-browser compatibility
   - Coverage: 70%+

### Dependencies
- None (can start immediately)

### Risk if Skipped
**HIGH RISK**: Feature development without tests will make the codebase fragile and regression-prone.

**See**: TESTING_ROADMAP.md for detailed implementation plan.

---

## Phase 1: Column-Level Lineage Enhancement (Weeks 5-8) 🟡

**Duration**: 4 weeks
**Priority**: HIGH
**Dependencies**: Phase 0 complete

### 1.1 Enhanced Column Lineage Visualization
**Effort**: 2 weeks

**Backend Changes**:
```python
# New endpoint
GET /api/v1/lineage/column/{column_id}
  ?direction=both
  &depth=3
  &include_transformations=true

Response:
{
  "columns": [
    {
      "id": "uuid",
      "name": "customer_id",
      "dataset_name": "customers",
      "data_type": "INTEGER",
      "description": "...",
      "source_type": "postgres"
    }
  ],
  "edges": [
    {
      "source_column_id": "uuid",
      "target_column_id": "uuid",
      "transformation": "SELECT customer_id FROM...",
      "expression": "CAST(customer_id AS INT)"
    }
  ],
  "transformations": [
    {
      "id": "uuid",
      "sql": "SELECT c.customer_id...",
      "type": "dbt_model",
      "file_path": "models/staging/stg_customers.sql"
    }
  ]
}
```

**Frontend Changes**:
- New `ColumnLineageGraph` component (extend current LineageGraph)
- Column-level nodes with data type badges
- Transformation expression tooltips
- Click to expand/collapse column details
- Filter by data type

**Test Requirements**:
- Backend: 15 tests (endpoint, query logic, edge cases)
- Frontend: 20 tests (component, interactions, rendering)

### 1.2 Transformation Detail View
**Effort**: 1 week

**Features**:
- Side panel showing full SQL/Python code
- Syntax highlighting
- Link to source file (if available)
- Execution statistics (if available)

**Components**:
- `TransformationPanel` organism
- `CodeViewer` molecule (syntax highlighting)

**Test Requirements**:
- 10 tests (component rendering, syntax highlighting, user interactions)

### 1.3 Column Metadata Enhancement
**Effort**: 1 week

**Backend Changes**:
- Add `description`, `tags`, `quality_score` to ColumnModel
- Migration for new fields
- Update all connectors to extract descriptions (if available)

**Frontend Changes**:
- Column metadata display in graph nodes
- Searchable/filterable by tags

**Test Requirements**:
- Backend: 10 tests (migration, connector updates)
- Frontend: 8 tests (rendering, filtering)

---

## Phase 2: Impact & Root Cause Analysis (Weeks 9-10) 🟡

**Duration**: 2 weeks
**Priority**: HIGH
**Dependencies**: Phase 1 complete

### 2.1 Impact Analysis Feature
**Effort**: 1 week

**Backend**:
```python
POST /api/v1/lineage/impact-analysis
{
  "column_id": "uuid",
  "change_type": "deletion | modification | type_change"
}

Response:
{
  "impacted_datasets": [
    {
      "dataset_id": "uuid",
      "dataset_name": "customer_reports",
      "impact_severity": "high | medium | low",
      "affected_columns": ["revenue", "customer_count"],
      "path_length": 3,
      "transformation_chain": [...]
    }
  ],
  "total_impacted": 15,
  "max_depth_reached": 5
}
```

**Frontend**:
- "Analyze Impact" button on dataset/column pages
- Modal showing impact tree view
- Color-coded severity (red/yellow/green)
- Export impact report

**Test Requirements**:
- Backend: 12 tests (traversal algorithm, edge cases)
- Frontend: 10 tests (UI interactions, report generation)

### 2.2 Root Cause Analysis
**Effort**: 1 week

**Backend**:
```python
POST /api/v1/lineage/root-cause-analysis
{
  "column_id": "uuid",
  "max_depth": 10
}

Response:
{
  "source_columns": [
    {
      "column_id": "uuid",
      "column_name": "raw_customer_id",
      "dataset_name": "raw_events",
      "source_type": "postgres",
      "is_root_source": true,
      "path_length": 4
    }
  ],
  "transformation_chain": [...]
}
```

**Frontend**:
- "Find Root Causes" button
- Tree visualization showing all source paths
- Highlight root sources (no upstream)

**Test Requirements**:
- Backend: 12 tests
- Frontend: 10 tests

---

## Phase 3: Search & Discovery (Weeks 11-12) 🟢

**Duration**: 2 weeks
**Priority**: MEDIUM
**Dependencies**: Phase 1 complete

### 3.1 Full-Text Search
**Effort**: 1.5 weeks

**Backend**:
```python
# Add PostgreSQL full-text search indexes
CREATE INDEX idx_dataset_search ON datasets
  USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));

CREATE INDEX idx_column_search ON columns
  USING gin(to_tsvector('english', name || ' ' || COALESCE(description, '')));

GET /api/v1/search?q=customer&type=dataset|column|all&limit=50
```

**Frontend**:
- Global search bar in header
- Search results page with faceted filters
- Highlight matching terms
- Recent searches

**Test Requirements**:
- Backend: 15 tests (search accuracy, ranking, performance)
- Frontend: 12 tests (UI, filtering, navigation)

### 3.2 Advanced Filters
**Effort**: 0.5 weeks

**Features**:
- Filter by source type
- Filter by data type
- Filter by date range (created/modified)
- Filter by tags (when implemented)
- Save filter presets

**Test Requirements**:
- 8 tests (filter logic, combinations)

---

## Phase 4: Export & Sharing (Weeks 13-14) 🟢

**Duration**: 2 weeks
**Priority**: MEDIUM
**Dependencies**: Phase 1 complete

### 4.1 Export Functionality
**Effort**: 1 week

**Features**:
- **PNG Export**: Screenshot of current graph view
- **SVG Export**: Vector format for high-quality printing
- **JSON Export**: Complete lineage data for external tools
- **CSV Export**: Tabular format (datasets + edges)

**Implementation**:
```typescript
// Frontend utilities
export const exportGraphAsPNG = (reactFlowInstance: ReactFlowInstance) => {
  // Use html-to-image library
};

export const exportGraphAsSVG = (reactFlowInstance: ReactFlowInstance) => {
  // Convert React Flow to SVG
};

export const exportLineageAsJSON = (data: LineageGraph) => {
  // Download JSON file
};
```

**Backend**:
```python
GET /api/v1/lineage/export/{dataset_id}
  ?format=json|csv
  ?direction=both
  ?depth=3
```

**Test Requirements**:
- Backend: 8 tests (export formats, data integrity)
- Frontend: 10 tests (export functions, file downloads)

### 4.2 Saved Views & Bookmarks
**Effort**: 1 week

**Backend**:
```python
# New models
class SavedView(Base):
    id: UUID
    user_id: UUID
    name: str
    description: str
    dataset_id: UUID
    direction: str
    depth: int
    filters: JSON
    created_at: datetime

POST /api/v1/saved-views
GET /api/v1/saved-views
DELETE /api/v1/saved-views/{id}
```

**Frontend**:
- "Save Current View" button
- "My Saved Views" page
- Quick access from dropdown

**Test Requirements**:
- Backend: 12 tests (CRUD operations)
- Frontend: 10 tests (UI, persistence)

---

## Phase 5: Real-Time Updates (Weeks 15-16) 🟢

**Duration**: 2 weeks
**Priority**: MEDIUM
**Dependencies**: Phase 0 complete

### 5.1 WebSocket Integration
**Effort**: 1.5 weeks

**Backend**:
```python
# Add WebSocket support to FastAPI
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Broadcast sync status updates
    while True:
        if job_status_changed:
            await websocket.send_json({
                "event": "sync_status",
                "job_id": "uuid",
                "status": "running|completed|failed",
                "progress": 65
            })
```

**Frontend**:
```typescript
// WebSocket hook
export const useWebSocket = () => {
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Update React Query cache
      queryClient.invalidateQueries(['syncJobs']);
    };
  }, []);
};
```

**Features**:
- Live sync job progress
- Real-time notifications
- Auto-refresh lineage graph when sync completes

**Test Requirements**:
- Backend: 10 tests (WebSocket connection, message broadcasting)
- Frontend: 8 tests (connection handling, UI updates)

### 5.2 Notifications System
**Effort**: 0.5 weeks

**Features**:
- Toast notifications for sync completion
- Error notifications
- Browser notifications (optional)

**Test Requirements**:
- 5 tests

---

## Phase 6: Data Quality Integration (Weeks 17-18) 🔵

**Duration**: 2 weeks
**Priority**: LOW
**Dependencies**: Phase 0 complete

### 6.1 Quality Metrics Schema
**Effort**: 1 week

**Backend**:
```python
class DataQualityMetric(Base):
    id: UUID
    column_id: UUID
    metric_type: str  # completeness, uniqueness, validity, etc.
    value: float
    threshold: float
    status: str  # pass, warning, fail
    measured_at: datetime

GET /api/v1/quality/column/{column_id}
POST /api/v1/quality/metrics
```

**Test Requirements**:
- 15 tests (CRUD, validation, queries)

### 6.2 Quality Visualization
**Effort**: 1 week

**Frontend**:
- Quality badges on graph nodes
- Quality score trend charts
- Filter by quality status

**Test Requirements**:
- 10 tests

---

## Phase 7: User Management & Permissions (Weeks 19-20) 🔵

**Duration**: 2 weeks
**Priority**: LOW
**Dependencies**: Phase 0 complete

### 7.1 User Registration & Management
**Effort**: 1 week

**Backend**:
```python
class User(Base):
    id: UUID
    username: str
    email: str
    password_hash: str  # bcrypt
    role: str  # admin, editor, viewer
    created_at: datetime

POST /api/v1/users/register
POST /api/v1/users/reset-password
GET /api/v1/users
PUT /api/v1/users/{id}
DELETE /api/v1/users/{id}
```

**Security**:
- Replace demo users with database users
- Password hashing with bcrypt
- Email verification
- Password reset flow

**Test Requirements**:
- 20 tests (registration, authentication, authorization)

### 7.2 Role-Based Access Control
**Effort**: 1 week

**Roles**:
- **Admin**: Full access, user management
- **Editor**: Create/edit data sources, trigger syncs
- **Viewer**: Read-only access

**Implementation**:
```python
@require_role("editor")
async def create_data_source(...):
    pass
```

**Test Requirements**:
- 15 tests (permission checks, edge cases)

---

## Phase 8: Performance Optimization (Weeks 21-22) 🔵

**Duration**: 2 weeks
**Priority**: LOW
**Dependencies**: All features implemented

### 8.1 Backend Performance
**Effort**: 1 week

**Optimizations**:
- Database query optimization (EXPLAIN ANALYZE)
- Add database indexes for common queries
- Implement caching layer (Redis)
- Pagination for large result sets
- Connection pooling tuning

**Caching Strategy**:
```python
from aiocache import cached

@cached(ttl=300)  # 5 minutes
async def get_table_lineage(dataset_id: str, direction: str, depth: int):
    # Cache expensive graph queries
    pass
```

**Test Requirements**:
- 15 performance benchmarks
- Load testing scenarios

### 8.2 Frontend Performance
**Effort**: 1 week

**Optimizations**:
- Code splitting by route
- Lazy loading for large graphs
- Virtual scrolling for long lists
- Image optimization
- Bundle size reduction

**Implementation**:
```typescript
// Lazy load heavy components
const LineageGraph = lazy(() => import('@components/organisms/LineageGraph'));

// Virtual scrolling for datasets
import { useVirtualizer } from '@tanstack/react-virtual';
```

**Targets**:
- Bundle size < 500KB
- First Contentful Paint < 1.5s
- Time to Interactive < 3s
- Lighthouse score > 90

**Test Requirements**:
- 10 performance tests
- Lighthouse CI integration

---

## Implementation Timeline

```
Week 1-4:   Phase 0 - Testing Foundation (CRITICAL)
Week 5-8:   Phase 1 - Column-Level Lineage
Week 9-10:  Phase 2 - Impact & Root Cause Analysis
Week 11-12: Phase 3 - Search & Discovery
Week 13-14: Phase 4 - Export & Sharing
Week 15-16: Phase 5 - Real-Time Updates
Week 17-18: Phase 6 - Data Quality Integration (Optional)
Week 19-20: Phase 7 - User Management (Optional)
Week 21-22: Phase 8 - Performance Optimization (Optional)
```

**Total Duration**: 12-16 weeks (depending on optional phases)

---

## Effort Estimation

| Phase | Backend | Frontend | Tests | Total Hours |
|-------|---------|----------|-------|-------------|
| Phase 0 (Testing) | 40h | 40h | 35h | 115h |
| Phase 1 (Column Lineage) | 60h | 50h | 30h | 140h |
| Phase 2 (Impact Analysis) | 30h | 25h | 15h | 70h |
| Phase 3 (Search) | 30h | 20h | 12h | 62h |
| Phase 4 (Export) | 20h | 25h | 10h | 55h |
| Phase 5 (Real-Time) | 25h | 20h | 8h | 53h |
| Phase 6 (Quality) | 30h | 20h | 12h | 62h |
| Phase 7 (Users) | 35h | 25h | 15h | 75h |
| Phase 8 (Performance) | 30h | 25h | 15h | 70h |
| **Total** | **300h** | **250h** | **152h** | **702h** |

**Notes**:
- Assumes 1 full-time developer
- Includes design, implementation, testing, and documentation
- Phase 0 is non-negotiable for quality assurance
- Phases 6-8 are optional based on requirements

---

## Success Metrics

### Phase 0 Completion Criteria
- ✅ Backend test coverage > 85%
- ✅ Frontend test coverage > 85%
- ✅ All CI/CD pipelines passing
- ✅ No critical bugs in existing features

### Feature Completion Criteria
- ✅ All acceptance criteria met
- ✅ Unit tests passing (coverage > 80%)
- ✅ Integration tests passing
- ✅ Code review approved
- ✅ Documentation updated
- ✅ No performance regressions

### Quality Gates
**Before Merge**:
- All tests passing
- Code coverage maintained
- No linting/type errors
- Security scan passing

**Before Release**:
- E2E tests passing
- Performance benchmarks met
- No critical/high vulnerabilities
- Deployment smoke tests passing

---

## Risk Assessment

### High Risks
1. **Starting features without Phase 0**: Will accumulate technical debt and cause regressions
2. **Underestimating complexity**: Column-level lineage visualization is complex
3. **Performance at scale**: Large graphs (1000+ nodes) may require optimization sooner

### Medium Risks
1. **WebSocket scalability**: May need message queue (Redis Pub/Sub) for multiple users
2. **Search performance**: Full-text search may need Elasticsearch for large datasets
3. **Browser compatibility**: React Flow may have issues in older browsers

### Low Risks
1. **Export functionality**: Well-established libraries available
2. **User management**: Standard implementation patterns

---

## Dependencies & Prerequisites

### External Libraries (New)
**Backend**:
- `redis` - Caching layer
- `python-socketio` - WebSocket support (alternative to FastAPI WebSocket)
- `elasticsearch-py` - If implementing advanced search

**Frontend**:
- `html-to-image` - PNG export
- `@tanstack/react-virtual` - Virtual scrolling
- `recharts` or `visx` - Quality metric charts

### Infrastructure
- Redis instance (for caching and WebSocket)
- Elasticsearch (optional, for advanced search)

---

## Rollout Strategy

### Phase 0 (Testing)
**Goal**: Establish quality baseline before feature development

**Approach**: Parallel development tracks
- Track 1: Backend tests (API + Services)
- Track 2: Frontend tests (Components + Pages)
- Track 3: E2E tests

**Delivery**: All tracks complete before Phase 1 starts

### Phases 1-5 (Core Features)
**Goal**: Deliver high-value features incrementally

**Approach**: Feature-by-feature deployment
- Each phase deploys independently
- Feature flags for gradual rollout
- User feedback loops

### Phases 6-8 (Advanced Features)
**Goal**: Enhance and optimize

**Approach**: Priority-based selection
- Assess user needs after Phase 5
- Implement most-requested features first
- Continuous performance monitoring

---

## Monitoring & Maintenance

### Continuous Monitoring
- Test coverage trends (target: maintain 85%+)
- Performance metrics (API response times, bundle size)
- Error rates and user feedback
- Feature usage analytics

### Maintenance Schedule
- **Weekly**: Review failed tests and bugs
- **Monthly**: Performance review and optimization
- **Quarterly**: Security audit and dependency updates
- **Yearly**: Architecture review and tech debt assessment

---

## Conclusion

**Current State**: Production-ready backend and functional frontend, but critical testing gaps create high risk for feature development.

**Critical Path**: Phase 0 (Testing Foundation) is non-negotiable. Without comprehensive tests, feature development will:
- Introduce regressions
- Increase debugging time exponentially
- Create unsustainable technical debt

**Recommendation**:
1. **Weeks 1-4**: Complete Phase 0 (Testing Foundation)
2. **Weeks 5-8**: Implement Phase 1 (Column-Level Lineage) - highest business value
3. **Weeks 9-10**: Implement Phase 2 (Impact Analysis) - critical for data governance
4. **Weeks 11+**: Evaluate remaining phases based on user feedback and business priorities

**Expected Outcome**: A robust, well-tested system with advanced lineage capabilities that scales confidently to production workloads.

---

## Next Steps

1. **Approve this roadmap** and confirm Phase 0 as the starting point
2. **Begin Phase 0 implementation** following TESTING_ROADMAP.md
3. **Set up progress tracking** (GitHub Projects, Jira, etc.)
4. **Schedule regular reviews** (bi-weekly sprint reviews)
5. **Establish quality gates** in CI/CD pipeline

**Ready to proceed?** The next action is to begin Phase 0: Testing Foundation.
