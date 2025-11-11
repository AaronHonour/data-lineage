/**
 * useDataSources Hook Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import {
  useDataSources,
  useDataSource,
  useCreateDataSource,
  useUpdateDataSource,
  useDeleteDataSource,
  useTriggerSync,
  useSyncJobs,
} from '../useDataSources';
import { apiService } from '@services/api';
import type { DataSource } from '@types/api';

// Mock apiService
vi.mock('@services/api', () => ({
  apiService: {
    getDataSources: vi.fn(),
    getDataSource: vi.fn(),
    createDataSource: vi.fn(),
    updateDataSource: vi.fn(),
    deleteDataSource: vi.fn(),
    triggerSync: vi.fn(),
    getSyncJobs: vi.fn(),
  },
}));

// Helper to create wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe('useDataSources', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useDataSources', () => {
    it('fetches all data sources successfully', async () => {
      const mockDataSources: DataSource[] = [
        {
          id: '1',
          name: 'Postgres DB',
          type: 'postgres',
          status: 'active',
          connection_config: {},
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ];

      vi.mocked(apiService.getDataSources).mockResolvedValueOnce(mockDataSources);

      const { result } = renderHook(() => useDataSources(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockDataSources);
      expect(apiService.getDataSources).toHaveBeenCalledTimes(1);
    });

    it('handles fetch error', async () => {
      vi.mocked(apiService.getDataSources).mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useDataSources(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeDefined();
    });
  });

  describe('useDataSource', () => {
    it('fetches single data source by ID', async () => {
      const mockDataSource: DataSource = {
        id: '1',
        name: 'Postgres DB',
        type: 'postgres',
        status: 'active',
        connection_config: {},
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      vi.mocked(apiService.getDataSource).mockResolvedValueOnce(mockDataSource);

      const { result } = renderHook(() => useDataSource('1'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockDataSource);
      expect(apiService.getDataSource).toHaveBeenCalledWith('1');
    });

    it('does not fetch when ID is not provided', () => {
      renderHook(() => useDataSource(''), {
        wrapper: createWrapper(),
      });

      expect(apiService.getDataSource).not.toHaveBeenCalled();
    });
  });

  describe('useCreateDataSource', () => {
    it('creates a data source successfully', async () => {
      const newDataSource: Partial<DataSource> = {
        name: 'New Postgres',
        type: 'postgres',
        connection_config: { host: 'localhost' },
      };

      const createdDataSource: DataSource = {
        id: '2',
        ...newDataSource,
        status: 'active',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      } as DataSource;

      vi.mocked(apiService.createDataSource).mockResolvedValueOnce(createdDataSource);

      const { result } = renderHook(() => useCreateDataSource(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(newDataSource);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(createdDataSource);
      expect(apiService.createDataSource).toHaveBeenCalledWith(newDataSource);
    });

    it('handles creation error', async () => {
      vi.mocked(apiService.createDataSource).mockRejectedValueOnce(new Error('Creation failed'));

      const { result } = renderHook(() => useCreateDataSource(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ name: 'Test' });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeDefined();
    });
  });

  describe('useUpdateDataSource', () => {
    it('updates a data source successfully', async () => {
      const updateData: Partial<DataSource> = {
        name: 'Updated Name',
      };

      const updatedDataSource: DataSource = {
        id: '1',
        name: 'Updated Name',
        type: 'postgres',
        status: 'active',
        connection_config: {},
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      vi.mocked(apiService.updateDataSource).mockResolvedValueOnce(updatedDataSource);

      const { result } = renderHook(() => useUpdateDataSource(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ id: '1', data: updateData });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(updatedDataSource);
      expect(apiService.updateDataSource).toHaveBeenCalledWith('1', updateData);
    });
  });

  describe('useDeleteDataSource', () => {
    it('deletes a data source successfully', async () => {
      vi.mocked(apiService.deleteDataSource).mockResolvedValueOnce(undefined);

      const { result } = renderHook(() => useDeleteDataSource(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('1');

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(apiService.deleteDataSource).toHaveBeenCalledWith('1');
    });
  });

  describe('useTriggerSync', () => {
    it('triggers sync successfully', async () => {
      const syncJob = {
        id: 'job-1',
        source_id: '1',
        status: 'pending',
        started_at: '2024-01-01T00:00:00Z',
      };

      vi.mocked(apiService.triggerSync).mockResolvedValueOnce(syncJob);

      const { result } = renderHook(() => useTriggerSync(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('1');

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(syncJob);
      expect(apiService.triggerSync).toHaveBeenCalledWith('1');
    });
  });

  describe('useSyncJobs', () => {
    it('fetches sync jobs for a data source', async () => {
      const mockJobs = [
        {
          id: 'job-1',
          source_id: '1',
          status: 'completed',
          started_at: '2024-01-01T00:00:00Z',
          completed_at: '2024-01-01T00:01:00Z',
        },
      ];

      vi.mocked(apiService.getSyncJobs).mockResolvedValueOnce(mockJobs);

      const { result } = renderHook(() => useSyncJobs('1', 10), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockJobs);
      expect(apiService.getSyncJobs).toHaveBeenCalledWith('1', 10);
    });

    it('does not fetch when source ID is not provided', () => {
      renderHook(() => useSyncJobs(''), {
        wrapper: createWrapper(),
      });

      expect(apiService.getSyncJobs).not.toHaveBeenCalled();
    });
  });
});
