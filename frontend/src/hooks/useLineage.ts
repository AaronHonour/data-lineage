/**
 * Lineage Hooks
 *
 * React Query hooks for lineage queries
 */

import { useQuery } from '@tanstack/react-query';
import { apiService } from '@services/api';

export const LINEAGE_KEY = 'lineage';

/**
 * Fetch table-level lineage for a dataset
 */
export const useTableLineage = (
  datasetId: string,
  direction: 'upstream' | 'downstream' | 'both' = 'both',
  depth: number = 3
) => {
  return useQuery({
    queryKey: [LINEAGE_KEY, 'table', datasetId, direction, depth],
    queryFn: () => apiService.getTableLineage(datasetId, direction, depth),
    enabled: !!datasetId,
    staleTime: 60000, // 1 minute
  });
};

/**
 * Fetch column-level lineage for a column
 */
export const useColumnLineage = (
  columnId: string,
  direction: 'upstream' | 'downstream' | 'both' = 'both',
  depth: number = 5
) => {
  return useQuery({
    queryKey: [LINEAGE_KEY, 'column', columnId, direction, depth],
    queryFn: () => apiService.getColumnLineage(columnId, direction, depth),
    enabled: !!columnId,
    staleTime: 60000, // 1 minute
  });
};
