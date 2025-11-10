/**
 * API Service Layer
 *
 * Centralized API client using Axios with interceptors for auth and error handling
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import type {
  DataSource,
  LineageGraph,
  SyncJob,
  SyncResponse,
  LoginRequest,
  LoginResponse,
  APIError,
} from '@types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class APIService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor - add auth token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('auth_token');
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor - handle errors
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<APIError>) => {
        if (error.response?.status === 401) {
          // Unauthorized - clear token and redirect to login
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // ==================== Authentication ====================

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await this.client.post<LoginResponse>('/api/v1/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.client.get('/api/v1/auth/me');
    return response.data;
  }

  // ==================== Health ====================

  async checkHealth(): Promise<{ status: string }> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // ==================== Data Sources ====================

  async getDataSources(): Promise<DataSource[]> {
    const response = await this.client.get<DataSource[]>('/api/v1/data-sources');
    return response.data;
  }

  async getDataSource(id: string): Promise<DataSource> {
    const response = await this.client.get<DataSource>(`/api/v1/data-sources/${id}`);
    return response.data;
  }

  async createDataSource(data: Partial<DataSource>): Promise<DataSource> {
    const response = await this.client.post<DataSource>('/api/v1/data-sources', data);
    return response.data;
  }

  async updateDataSource(id: string, data: Partial<DataSource>): Promise<DataSource> {
    const response = await this.client.put<DataSource>(`/api/v1/data-sources/${id}`, data);
    return response.data;
  }

  async deleteDataSource(id: string): Promise<void> {
    await this.client.delete(`/api/v1/data-sources/${id}`);
  }

  // ==================== Sync Operations ====================

  async triggerSync(sourceId: string): Promise<SyncResponse> {
    const response = await this.client.post<SyncResponse>(
      `/api/v1/data-sources/${sourceId}/sync`
    );
    return response.data;
  }

  async getSyncJobs(sourceId: string, limit: number = 10): Promise<SyncJob[]> {
    const response = await this.client.get<SyncJob[]>(
      `/api/v1/data-sources/${sourceId}/sync-jobs`,
      {
        params: { limit },
      }
    );
    return response.data;
  }

  // ==================== Lineage ====================

  async getTableLineage(
    datasetId: string,
    direction: 'upstream' | 'downstream' | 'both' = 'both',
    depth: number = 3
  ): Promise<LineageGraph> {
    const response = await this.client.get<LineageGraph>(
      `/api/v1/lineage/table/${datasetId}`,
      {
        params: { direction, depth },
      }
    );
    return response.data;
  }

  async getColumnLineage(
    columnId: string,
    direction: 'upstream' | 'downstream' | 'both' = 'both',
    depth: number = 5
  ): Promise<LineageGraph> {
    const response = await this.client.get<LineageGraph>(
      `/api/v1/lineage/column/${columnId}`,
      {
        params: { direction, depth },
      }
    );
    return response.data;
  }

  // ==================== Dashboard ====================

  async getDashboardStats() {
    // This would be a dedicated endpoint, for now we'll aggregate
    const sources = await this.getDataSources();

    let totalDatasets = 0;
    let totalTransformations = 0;
    let totalEdges = 0;
    const recentSyncs: SyncJob[] = [];

    // Collect sync jobs from first few sources
    for (const source of sources.slice(0, 5)) {
      try {
        const jobs = await this.getSyncJobs(source.id, 1);
        if (jobs.length > 0) {
          const job = jobs[0];
          recentSyncs.push(job);
          if (job.statistics) {
            totalDatasets += job.statistics.datasets_discovered || 0;
            totalTransformations += job.statistics.transformations_discovered || 0;
            totalEdges += job.statistics.lineage_edges_created || 0;
          }
        }
      } catch (error) {
        console.error(`Failed to fetch sync jobs for source ${source.id}`, error);
      }
    }

    return {
      total_sources: sources.length,
      total_datasets: totalDatasets,
      total_transformations: totalTransformations,
      total_lineage_edges: totalEdges,
      recent_syncs: recentSyncs.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ),
    };
  }
}

// Export singleton instance
export const apiService = new APIService();
export default apiService;
