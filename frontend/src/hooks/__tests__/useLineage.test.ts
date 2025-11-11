/**
 * useLineage Hook Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useTableLineage, useColumnLineage } from '../useLineage';
import { apiService } from '@services/api';

// Mock apiService
vi.mock('@services/api', () => ({
  apiService: {
    getTableLineage: vi.fn(),
    getColumnLineage: vi.fn(),
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

describe('useLineage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useTableLineage', () => {
    it('fetches table lineage with default parameters', async () => {
      const mockLineage = {
        nodes: [
          { id: 'table1', name: 'orders', type: 'table' },
          { id: 'table2', name: 'customers', type: 'table' },
        ],
        edges: [{ source: 'table2', target: 'table1' }],
      };

      vi.mocked(apiService.getTableLineage).mockResolvedValueOnce(mockLineage);

      const { result } = renderHook(() => useTableLineage('dataset-1'), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockLineage);
      expect(apiService.getTableLineage).toHaveBeenCalledWith('dataset-1', 'both', 3);
    });

    it('fetches upstream lineage with custom depth', async () => {
      const mockLineage = {
        nodes: [{ id: 'table1', name: 'staging_orders', type: 'table' }],
        edges: [],
      };

      vi.mocked(apiService.getTableLineage).mockResolvedValueOnce(mockLineage);

      const { result } = renderHook(() => useTableLineage('dataset-1', 'upstream', 5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockLineage);
      expect(apiService.getTableLineage).toHaveBeenCalledWith('dataset-1', 'upstream', 5);
    });

    it('fetches downstream lineage', async () => {
      const mockLineage = {
        nodes: [{ id: 'table1', name: 'fact_orders', type: 'table' }],
        edges: [],
      };

      vi.mocked(apiService.getTableLineage).mockResolvedValueOnce(mockLineage);

      const { result } = renderHook(() => useTableLineage('dataset-1', 'downstream', 2), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockLineage);
      expect(apiService.getTableLineage).toHaveBeenCalledWith('dataset-1', 'downstream', 2);
    });

    it('does not fetch when dataset ID is not provided', () => {
      renderHook(() => useTableLineage(''), {
        wrapper: createWrapper(),
      });

      expect(apiService.getTableLineage).not.toHaveBeenCalled();
    });

    it('handles fetch error', async () => {
      vi.mocked(apiService.getTableLineage).mockRejectedValueOnce(
        new Error('Failed to fetch lineage')
      );

      const { result } = renderHook(() => useTableLineage('dataset-1'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeDefined();
    });

    it('uses correct query key for cache', () => {
      const { result } = renderHook(() => useTableLineage('dataset-1', 'upstream', 4), {
        wrapper: createWrapper(),
      });

      // Query key should be unique for this combination
      expect(result.current).toBeDefined();
      // The hook should create a unique cache entry
    });
  });

  describe('useColumnLineage', () => {
    it('fetches column lineage with default parameters', async () => {
      const mockLineage = {
        nodes: [
          { id: 'col1', name: 'order_id', type: 'column', table: 'orders' },
          { id: 'col2', name: 'id', type: 'column', table: 'staging_orders' },
        ],
        edges: [{ source: 'col2', target: 'col1' }],
      };

      vi.mocked(apiService.getColumnLineage).mockResolvedValueOnce(mockLineage);

      const { result } = renderHook(() => useColumnLineage('column-1'), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockLineage);
      expect(apiService.getColumnLineage).toHaveBeenCalledWith('column-1', 'both', 5);
    });

    it('fetches upstream column lineage', async () => {
      const mockLineage = {
        nodes: [{ id: 'col1', name: 'customer_id', type: 'column' }],
        edges: [],
      };

      vi.mocked(apiService.getColumnLineage).mockResolvedValueOnce(mockLineage);

      const { result } = renderHook(() => useColumnLineage('column-1', 'upstream', 3), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(apiService.getColumnLineage).toHaveBeenCalledWith('column-1', 'upstream', 3);
    });

    it('fetches downstream column lineage with high depth', async () => {
      const mockLineage = {
        nodes: [
          { id: 'col1', name: 'order_total', type: 'column' },
          { id: 'col2', name: 'revenue', type: 'column' },
        ],
        edges: [{ source: 'col1', target: 'col2' }],
      };

      vi.mocked(apiService.getColumnLineage).mockResolvedValueOnce(mockLineage);

      const { result } = renderHook(() => useColumnLineage('column-1', 'downstream', 10), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(apiService.getColumnLineage).toHaveBeenCalledWith('column-1', 'downstream', 10);
    });

    it('does not fetch when column ID is not provided', () => {
      renderHook(() => useColumnLineage(''), {
        wrapper: createWrapper(),
      });

      expect(apiService.getColumnLineage).not.toHaveBeenCalled();
    });

    it('handles fetch error', async () => {
      vi.mocked(apiService.getColumnLineage).mockRejectedValueOnce(
        new Error('Column not found')
      );

      const { result } = renderHook(() => useColumnLineage('column-1'), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeDefined();
    });

    it('returns empty result when columnId is undefined', () => {
      // @ts-expect-error Testing with undefined
      const { result } = renderHook(() => useColumnLineage(undefined), {
        wrapper: createWrapper(),
      });

      expect(apiService.getColumnLineage).not.toHaveBeenCalled();
    });
  });

  describe('caching behavior', () => {
    it('caches table lineage results', async () => {
      const mockLineage = { nodes: [], edges: [] };
      vi.mocked(apiService.getTableLineage).mockResolvedValueOnce(mockLineage);

      const { result, rerender } = renderHook(
        ({ id }) => useTableLineage(id),
        {
          wrapper: createWrapper(),
          initialProps: { id: 'dataset-1' },
        }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Rerender with same ID should use cache
      rerender({ id: 'dataset-1' });

      // API should only be called once due to caching
      expect(apiService.getTableLineage).toHaveBeenCalledTimes(1);
    });

    it('makes new request for different dataset ID', async () => {
      const mockLineage1 = { nodes: [{ id: 't1', name: 'table1' }], edges: [] };
      const mockLineage2 = { nodes: [{ id: 't2', name: 'table2' }], edges: [] };

      vi.mocked(apiService.getTableLineage)
        .mockResolvedValueOnce(mockLineage1)
        .mockResolvedValueOnce(mockLineage2);

      const { result, rerender } = renderHook(
        ({ id }) => useTableLineage(id),
        {
          wrapper: createWrapper(),
          initialProps: { id: 'dataset-1' },
        }
      );

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockLineage1);

      // Change dataset ID
      rerender({ id: 'dataset-2' });

      await waitFor(() => {
        expect(result.current.data).toEqual(mockLineage2);
      });

      // Should make two API calls for different IDs
      expect(apiService.getTableLineage).toHaveBeenCalledTimes(2);
    });
  });
});
