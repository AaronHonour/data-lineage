/**
 * API Service Tests
 *
 * Comprehensive tests for the API service layer
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import type { DataSource, SyncJob, LineageGraph, LoginResponse } from '@types/api';

// Mock axios
vi.mock('axios');

describe('APIService', () => {
  let apiService: any;

  beforeEach(async () => {
    // Clear all mocks
    vi.clearAllMocks();

    // Create mock axios instance
    const mockAxiosInstance = {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    };

    // Configure axios.create mock
    vi.mocked(axios.create).mockReturnValue(mockAxiosInstance as any);

    // Dynamically import to ensure fresh instance
    vi.resetModules();
    const module = await import('../api');
    apiService = module.apiService;
  });

  describe('Authentication Methods', () => {
    it('login() sends credentials as form data', async () => {
      const mockResponse: LoginResponse = {
        access_token: 'token-123',
        token_type: 'bearer',
        user: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
        },
      };

      // Get the axios instance and mock its post method
      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.post.mockResolvedValue({ data: mockResponse });

      const credentials = {
        username: 'testuser',
        password: 'password123',
      };

      const result = await apiService.login(credentials);

      expect(axiosInstance.post).toHaveBeenCalledWith(
        '/api/v1/auth/login',
        expect.any(URLSearchParams),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );

      // Verify form data
      const formData = axiosInstance.post.mock.calls[0][1];
      expect(formData.get('username')).toBe('testuser');
      expect(formData.get('password')).toBe('password123');

      expect(result).toEqual(mockResponse);
    });

    it('getCurrentUser() fetches current user', async () => {
      const mockUser = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
      };

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.get.mockResolvedValue({ data: mockUser });

      const result = await apiService.getCurrentUser();

      expect(axiosInstance.get).toHaveBeenCalledWith('/api/v1/auth/me');
      expect(result).toEqual(mockUser);
    });
  });

  describe('Health Check', () => {
    it('checkHealth() returns health status', async () => {
      const mockHealth = { status: 'ok' };
      
      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.get.mockResolvedValue({ data: mockHealth });

      const result = await apiService.checkHealth();

      expect(axiosInstance.get).toHaveBeenCalledWith('/health');
      expect(result).toEqual(mockHealth);
    });
  });

  describe('Data Sources CRUD', () => {
    it('getDataSources() fetches all data sources', async () => {
      const mockSources: DataSource[] = [
        {
          id: '1',
          name: 'Source 1',
          type: 'postgres',
          connection_details: {},
          status: 'active',
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
        },
      ];

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.get.mockResolvedValue({ data: mockSources });

      const result = await apiService.getDataSources();

      expect(axiosInstance.get).toHaveBeenCalledWith('/api/v1/data-sources');
      expect(result).toEqual(mockSources);
    });

    it('getDataSource() fetches single data source by ID', async () => {
      const mockSource: DataSource = {
        id: '1',
        name: 'Source 1',
        type: 'postgres',
        connection_details: {},
        status: 'active',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      };

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.get.mockResolvedValue({ data: mockSource });

      const result = await apiService.getDataSource('1');

      expect(axiosInstance.get).toHaveBeenCalledWith('/api/v1/data-sources/1');
      expect(result).toEqual(mockSource);
    });

    it('createDataSource() creates new data source', async () => {
      const newSource = {
        name: 'New Source',
        type: 'mysql',
        connection_details: { host: 'localhost' },
      };

      const createdSource: DataSource = {
        id: '2',
        ...newSource,
        status: 'active',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      };

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.post.mockResolvedValue({ data: createdSource });

      const result = await apiService.createDataSource(newSource);

      expect(axiosInstance.post).toHaveBeenCalledWith(
        '/api/v1/data-sources',
        newSource
      );
      expect(result).toEqual(createdSource);
    });

    it('updateDataSource() updates existing data source', async () => {
      const updates = {
        name: 'Updated Source',
      };

      const updatedSource: DataSource = {
        id: '1',
        name: 'Updated Source',
        type: 'postgres',
        connection_details: {},
        status: 'active',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-02T00:00:00Z',
      };

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.put.mockResolvedValue({ data: updatedSource });

      const result = await apiService.updateDataSource('1', updates);

      expect(axiosInstance.put).toHaveBeenCalledWith(
        '/api/v1/data-sources/1',
        updates
      );
      expect(result).toEqual(updatedSource);
    });

    it('deleteDataSource() deletes data source', async () => {
      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.delete.mockResolvedValue({ data: null });

      await apiService.deleteDataSource('1');

      expect(axiosInstance.delete).toHaveBeenCalledWith('/api/v1/data-sources/1');
    });
  });

  describe('Sync Operations', () => {
    it('triggerSync() triggers sync for data source', async () => {
      const mockResponse = {
        message: 'Sync started',
        job_id: 'job-123',
      };

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.post.mockResolvedValue({ data: mockResponse });

      const result = await apiService.triggerSync('source-1');

      expect(axiosInstance.post).toHaveBeenCalledWith(
        '/api/v1/data-sources/source-1/sync'
      );
      expect(result).toEqual(mockResponse);
    });

    it('getSyncJobs() fetches sync jobs with default limit', async () => {
      const mockJobs: SyncJob[] = [
        {
          id: 'job-1',
          data_source_id: 'source-1',
          status: 'completed',
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
        },
      ];

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.get.mockResolvedValue({ data: mockJobs });

      const result = await apiService.getSyncJobs('source-1');

      expect(axiosInstance.get).toHaveBeenCalledWith(
        '/api/v1/data-sources/source-1/sync-jobs',
        {
          params: { limit: 10 },
        }
      );
      expect(result).toEqual(mockJobs);
    });

    it('getSyncJobs() fetches sync jobs with custom limit', async () => {
      const mockJobs: SyncJob[] = [];
      
      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.get.mockResolvedValue({ data: mockJobs });

      await apiService.getSyncJobs('source-1', 20);

      expect(axiosInstance.get).toHaveBeenCalledWith(
        '/api/v1/data-sources/source-1/sync-jobs',
        {
          params: { limit: 20 },
        }
      );
    });
  });

  describe('Lineage Queries', () => {
    it('getTableLineage() fetches table lineage with default parameters', async () => {
      const mockLineage: LineageGraph = {
        nodes: [],
        edges: [],
      };

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.get.mockResolvedValue({ data: mockLineage });

      const result = await apiService.getTableLineage('dataset-1');

      expect(axiosInstance.get).toHaveBeenCalledWith(
        '/api/v1/lineage/table/dataset-1',
        {
          params: { direction: 'both', depth: 3 },
        }
      );
      expect(result).toEqual(mockLineage);
    });

    it('getTableLineage() fetches upstream lineage with custom depth', async () => {
      const mockLineage: LineageGraph = {
        nodes: [],
        edges: [],
      };

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.get.mockResolvedValue({ data: mockLineage });

      await apiService.getTableLineage('dataset-1', 'upstream', 5);

      expect(axiosInstance.get).toHaveBeenCalledWith(
        '/api/v1/lineage/table/dataset-1',
        {
          params: { direction: 'upstream', depth: 5 },
        }
      );
    });

    it('getColumnLineage() fetches column lineage with default parameters', async () => {
      const mockLineage: LineageGraph = {
        nodes: [],
        edges: [],
      };

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.get.mockResolvedValue({ data: mockLineage });

      const result = await apiService.getColumnLineage('column-1');

      expect(axiosInstance.get).toHaveBeenCalledWith(
        '/api/v1/lineage/column/column-1',
        {
          params: { direction: 'both', depth: 5 },
        }
      );
      expect(result).toEqual(mockLineage);
    });

    it('getColumnLineage() fetches downstream lineage with custom depth', async () => {
      const mockLineage: LineageGraph = {
        nodes: [],
        edges: [],
      };

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      axiosInstance.get.mockResolvedValue({ data: mockLineage });

      await apiService.getColumnLineage('column-1', 'downstream', 10);

      expect(axiosInstance.get).toHaveBeenCalledWith(
        '/api/v1/lineage/column/column-1',
        {
          params: { direction: 'downstream', depth: 10 },
        }
      );
    });
  });

  describe('Dashboard Stats', () => {
    it('getDashboardStats() aggregates stats from multiple sources', async () => {
      const mockSources: DataSource[] = [
        {
          id: 'source-1',
          name: 'Source 1',
          type: 'postgres',
          connection_details: {},
          status: 'active',
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
        },
        {
          id: 'source-2',
          name: 'Source 2',
          type: 'mysql',
          connection_details: {},
          status: 'active',
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
        },
      ];

      const mockJobs: SyncJob[] = [
        {
          id: 'job-1',
          data_source_id: 'source-1',
          status: 'completed',
          created_at: '2025-01-01T10:00:00Z',
          updated_at: '2025-01-01T10:05:00Z',
          statistics: {
            datasets_discovered: 10,
            transformations_discovered: 5,
            lineage_edges_created: 15,
          },
        },
      ];

      const axiosInstance = vi.mocked(axios.create).mock.results[0].value;
      // Mock getDataSources call
      axiosInstance.get
        .mockResolvedValueOnce({ data: mockSources })
        // Mock getSyncJobs calls
        .mockResolvedValueOnce({ data: mockJobs })
        .mockResolvedValueOnce({ data: [] });

      const result = await apiService.getDashboardStats();

      expect(result).toEqual({
        total_sources: 2,
        total_datasets: 10,
        total_transformations: 5,
        total_lineage_edges: 15,
        recent_syncs: mockJobs,
      });
    });
  });
});
