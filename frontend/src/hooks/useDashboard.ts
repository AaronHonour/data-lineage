/**
 * Dashboard Hook
 *
 * React Query hook for dashboard statistics
 */

import { useQuery } from '@tanstack/react-query';
import { apiService } from '@services/api';

export const DASHBOARD_KEY = 'dashboard';

/**
 * Fetch dashboard statistics
 */
export const useDashboardStats = () => {
  return useQuery({
    queryKey: [DASHBOARD_KEY, 'stats'],
    queryFn: () => apiService.getDashboardStats(),
    staleTime: 60000, // 1 minute
    refetchInterval: 300000, // Refetch every 5 minutes
  });
};
