/**
 * Data Sources Hooks
 *
 * React Query hooks for managing data sources
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '@services/api';
import type { DataSource } from '@types/api';

export const DATA_SOURCES_KEY = 'dataSources';

/**
 * Fetch all data sources
 */
export const useDataSources = () => {
  return useQuery({
    queryKey: [DATA_SOURCES_KEY],
    queryFn: () => apiService.getDataSources(),
    staleTime: 30000, // 30 seconds
  });
};

/**
 * Fetch a single data source by ID
 */
export const useDataSource = (id: string) => {
  return useQuery({
    queryKey: [DATA_SOURCES_KEY, id],
    queryFn: () => apiService.getDataSource(id),
    enabled: !!id,
  });
};

/**
 * Create a new data source
 */
export const useCreateDataSource = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<DataSource>) => apiService.createDataSource(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [DATA_SOURCES_KEY] });
    },
  });
};

/**
 * Update an existing data source
 */
export const useUpdateDataSource = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<DataSource> }) =>
      apiService.updateDataSource(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [DATA_SOURCES_KEY] });
      queryClient.invalidateQueries({ queryKey: [DATA_SOURCES_KEY, variables.id] });
    },
  });
};

/**
 * Delete a data source
 */
export const useDeleteDataSource = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => apiService.deleteDataSource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [DATA_SOURCES_KEY] });
    },
  });
};

/**
 * Trigger sync for a data source
 */
export const useTriggerSync = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sourceId: string) => apiService.triggerSync(sourceId),
    onSuccess: (_, sourceId) => {
      // Invalidate sync jobs to show the new job
      queryClient.invalidateQueries({ queryKey: ['syncJobs', sourceId] });
    },
  });
};

/**
 * Fetch sync jobs for a data source
 */
export const useSyncJobs = (sourceId: string, limit: number = 10) => {
  return useQuery({
    queryKey: ['syncJobs', sourceId, limit],
    queryFn: () => apiService.getSyncJobs(sourceId, limit),
    enabled: !!sourceId,
    refetchInterval: (query) => {
      // If there's a running job, poll every 5 seconds
      const jobs = query.state.data;
      const hasRunningJob = jobs?.some((job) => job.status === 'running' || job.status === 'pending');
      return hasRunningJob ? 5000 : false;
    },
  });
};
