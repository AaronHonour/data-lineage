/**
 * API Type Definitions
 *
 * These types match the backend API schemas
 */

export interface DataSource {
  id: string;
  name: string;
  source_type: 'postgres' | 'mysql' | 'sqlserver' | 'dbt' | 'python' | 'iceberg' | 'delta';
  connection_config: Record<string, unknown>;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface Dataset {
  id: string;
  name: string;
  schema_name?: string;
  fully_qualified_name: string;
  source_type: string;
  columns: Column[];
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface Column {
  id: string;
  name: string;
  data_type?: string;
  is_primary_key: boolean;
  description?: string;
}

export interface LineageEdge {
  id?: string;
  source_column_id?: string;
  target_column_id?: string;
  source_dataset_id?: string;
  target_dataset_id?: string;
  expression?: string;
  confidence: number;
}

export interface LineageGraph {
  datasets: Dataset[];
  edges: LineageEdge[];
  metadata: {
    root_dataset_id?: string;
    root_column_id?: string;
    direction: 'upstream' | 'downstream' | 'both';
    depth: number;
    total_datasets?: number;
    total_columns?: number;
    total_edges?: number;
  };
}

export interface SyncJob {
  id: string;
  data_source_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  statistics?: {
    datasets_discovered?: number;
    transformations_discovered?: number;
    lineage_edges_created?: number;
    duration_seconds?: number;
  };
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface SyncResponse {
  message: string;
  source_id: string;
  stats: {
    datasets_discovered: number;
    transformations_discovered: number;
    lineage_edges_created: number;
  };
}

export interface DashboardStats {
  total_sources: number;
  total_datasets: number;
  total_transformations: number;
  total_lineage_edges: number;
  recent_syncs: SyncJob[];
}

// Auth types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface User {
  id: string;
  username: string;
  email?: string;
  full_name?: string;
}

// API Error
export interface APIError {
  detail: string | Array<{
    loc: (string | number)[];
    msg: string;
    type: string;
  }>;
}

// Pagination
export interface PaginationParams {
  skip?: number;
  limit?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}
