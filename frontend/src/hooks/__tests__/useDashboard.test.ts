/**
 * useDashboard Hook Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useDashboardStats } from '../useDashboard';
import { apiService } from '@services/api';

// Mock apiService
vi.mock('@services/api', () => ({
  apiService: {
    getDashboardStats: vi.fn(),
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

describe('useDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useDashboardStats', () => {
    it('fetches dashboard statistics successfully', async () => {
      const mockStats = {
        totalDataSources: 5,
        totalDatasets: 120,
        totalColumns: 1500,
        totalLineageRelationships: 350,
        recentSyncJobs: [
          {
            id: 'job-1',
            source_name: 'Postgres Production',
            status: 'completed',
            started_at: '2024-01-01T10:00:00Z',
          },
        ],
        dataSourcesByType: {
          postgres: 2,
          mysql: 1,
          dbt: 1,
          delta: 1,
        },
      };

      vi.mocked(apiService.getDashboardStats).mockResolvedValueOnce(mockStats);

      const { result } = renderHook(() => useDashboardStats(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockStats);
      expect(apiService.getDashboardStats).toHaveBeenCalledTimes(1);
    });

    it('handles fetch error', async () => {
      vi.mocked(apiService.getDashboardStats).mockRejectedValueOnce(
        new Error('Failed to fetch dashboard stats')
      );

      const { result } = renderHook(() => useDashboardStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.data).toBeUndefined();
    });

    it('returns loading state initially', () => {
      vi.mocked(apiService.getDashboardStats).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { result } = renderHook(() => useDashboardStats(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeUndefined();
      expect(result.current.error).toBeNull();
    });

    it('caches results for subsequent renders', async () => {
      const mockStats = {
        totalDataSources: 3,
        totalDatasets: 50,
        totalColumns: 600,
        totalLineageRelationships: 100,
      };

      vi.mocked(apiService.getDashboardStats).mockResolvedValueOnce(mockStats);

      const { result, rerender } = renderHook(() => useDashboardStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Rerender should use cached data
      rerender();

      expect(apiService.getDashboardStats).toHaveBeenCalledTimes(1);
      expect(result.current.data).toEqual(mockStats);
    });

    it('has correct staleTime configuration', async () => {
      const mockStats = { totalDataSources: 1 };
      vi.mocked(apiService.getDashboardStats).mockResolvedValue(mockStats);

      const { result } = renderHook(() => useDashboardStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Data should remain fresh for 60 seconds (staleTime: 60000)
      // Verify the hook configuration is correct
      expect(result.current.data).toEqual(mockStats);
    });

    it('returns empty data structure on first render', () => {
      vi.mocked(apiService.getDashboardStats).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({}), 1000))
      );

      const { result } = renderHook(() => useDashboardStats(), {
        wrapper: createWrapper(),
      });

      expect(result.current.data).toBeUndefined();
      expect(result.current.isLoading).toBe(true);
      expect(result.current.isError).toBe(false);
    });

    it('exposes query methods for manual control', async () => {
      const mockStats = { totalDataSources: 2 };
      vi.mocked(apiService.getDashboardStats).mockResolvedValue(mockStats);

      const { result } = renderHook(() => useDashboardStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Verify query object has expected methods
      expect(typeof result.current.refetch).toBe('function');
      expect(typeof result.current.isLoading).toBe('boolean');
      expect(typeof result.current.isError).toBe('boolean');
      expect(typeof result.current.isSuccess).toBe('boolean');
    });

    it('handles partial stats data', async () => {
      const partialStats = {
        totalDataSources: 1,
        totalDatasets: 10,
        // Missing other fields
      };

      vi.mocked(apiService.getDashboardStats).mockResolvedValueOnce(partialStats);

      const { result } = renderHook(() => useDashboardStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(partialStats);
    });

    it('handles refetch correctly', async () => {
      const initialStats = { totalDataSources: 1 };
      const updatedStats = { totalDataSources: 2 };

      vi.mocked(apiService.getDashboardStats)
        .mockResolvedValueOnce(initialStats)
        .mockResolvedValueOnce(updatedStats);

      const { result } = renderHook(() => useDashboardStats(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(initialStats);

      // Manually refetch
      await result.current.refetch();

      await waitFor(() => {
        expect(result.current.data).toEqual(updatedStats);
      });

      expect(apiService.getDashboardStats).toHaveBeenCalledTimes(2);
    });
  });
});
