/**
 * Dashboard Page Tests
 *
 * Tests for the Dashboard page component covering:
 * - Loading states
 * - Error handling
 * - Statistics display
 * - Recent activity table
 * - Data formatting
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/tests/test-utils';
import { Dashboard } from '../Dashboard';

// Mock the hooks
vi.mock('@hooks/useDashboard', () => ({
  useDashboardStats: vi.fn(),
}));

import { useDashboardStats } from '@hooks/useDashboard';

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading State', () => {
    it('displays loading spinner when data is loading', () => {
      vi.mocked(useDashboardStats).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
        refetch: vi.fn(),
      } as any);

      render(<Dashboard />);

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
      expect(screen.getByText('Loading dashboard...')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('displays error message when data fails to load', () => {
      vi.mocked(useDashboardStats).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Network error'),
        isError: true,
        isSuccess: false,
        refetch: vi.fn(),
      } as any);

      render(<Dashboard />);

      expect(screen.getByText('Failed to load dashboard data')).toBeInTheDocument();
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });
  });

  describe('Statistics Cards', () => {
    it('renders all statistic cards with correct data', () => {
      vi.mocked(useDashboardStats).mockReturnValue({
        data: {
          total_sources: 5,
          total_datasets: 150,
          total_transformations: 75,
          total_lineage_edges: 300,
          recent_syncs: [],
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<Dashboard />);

      // Check all card titles are present
      expect(screen.getByText('Data Sources')).toBeInTheDocument();
      expect(screen.getByText('Lineage Edges')).toBeInTheDocument();

      // Use getAllByText for labels that appear in both cards and table headers
      expect(screen.getAllByText('Datasets').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Transformations').length).toBeGreaterThan(0);

      // Check card values
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('150')).toBeInTheDocument();
      expect(screen.getByText('75')).toBeInTheDocument();
      expect(screen.getByText('300')).toBeInTheDocument();
    });

    it('handles zero values correctly', () => {
      vi.mocked(useDashboardStats).mockReturnValue({
        data: {
          total_sources: 0,
          total_datasets: 0,
          total_transformations: 0,
          total_lineage_edges: 0,
          recent_syncs: [],
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<Dashboard />);

      // Should still render cards with 0 values
      const zeroElements = screen.getAllByText('0');
      expect(zeroElements.length).toBeGreaterThanOrEqual(4);
    });

    it('displays large numbers', () => {
      vi.mocked(useDashboardStats).mockReturnValue({
        data: {
          total_sources: 1000,
          total_datasets: 50000,
          total_transformations: 25000,
          total_lineage_edges: 100000,
          recent_syncs: [],
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<Dashboard />);

      // Component displays raw numbers without formatting
      expect(screen.getByText('1000')).toBeInTheDocument();
      expect(screen.getByText('50000')).toBeInTheDocument();
      expect(screen.getByText('25000')).toBeInTheDocument();
      expect(screen.getByText('100000')).toBeInTheDocument();
    });
  });

  describe('Recent Activity Table', () => {
    it('displays recent sync jobs in table', () => {
      vi.mocked(useDashboardStats).mockReturnValue({
        data: {
          total_sources: 5,
          total_datasets: 150,
          total_transformations: 75,
          total_lineage_edges: 300,
          recent_syncs: [
            {
              id: 'job-1',
              data_source_id: 'source-1',
              status: 'completed',
              created_at: '2025-01-01T10:00:00Z',
              updated_at: '2025-01-01T10:05:00Z',
            },
            {
              id: 'job-2',
              data_source_id: 'source-2',
              status: 'running',
              created_at: '2025-01-01T09:00:00Z',
              updated_at: '2025-01-01T09:05:00Z',
            },
          ],
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<Dashboard />);

      // Check table headers
      expect(screen.getByText('Recent Sync Jobs')).toBeInTheDocument();

      // Check table contains data source IDs (truncated with ...)
      // The component displays data_source_id.substring(0, 8) + "..."
      expect(screen.getByText('source-1...')).toBeInTheDocument();
      expect(screen.getByText('source-2...')).toBeInTheDocument();
    });

    it('displays status badges for sync jobs', () => {
      vi.mocked(useDashboardStats).mockReturnValue({
        data: {
          total_sources: 5,
          total_datasets: 150,
          total_transformations: 75,
          total_lineage_edges: 300,
          recent_syncs: [
            {
              id: 'job-1',
              data_source_id: 'source-1',
              status: 'completed',
              created_at: '2025-01-01T10:00:00Z',
              updated_at: '2025-01-01T10:05:00Z',
            },
            {
              id: 'job-2',
              data_source_id: 'source-2',
              status: 'failed',
              created_at: '2025-01-01T09:00:00Z',
              updated_at: '2025-01-01T09:05:00Z',
            },
            {
              id: 'job-3',
              data_source_id: 'source-3',
              status: 'running',
              created_at: '2025-01-01T08:00:00Z',
              updated_at: '2025-01-01T08:05:00Z',
            },
          ],
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<Dashboard />);

      // All status badges should be present
      expect(screen.getByText('completed')).toBeInTheDocument();
      expect(screen.getByText('failed')).toBeInTheDocument();
      expect(screen.getByText('running')).toBeInTheDocument();
    });

    it('shows empty state when no recent syncs', () => {
      vi.mocked(useDashboardStats).mockReturnValue({
        data: {
          total_sources: 5,
          total_datasets: 0,
          total_transformations: 0,
          total_lineage_edges: 0,
          recent_syncs: [],
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<Dashboard />);

      expect(screen.getByText('Recent Sync Jobs')).toBeInTheDocument();
      // Table should still exist, just with no rows
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
    });
  });

  describe('Card Icons', () => {
    it('displays appropriate icons for each statistic', () => {
      vi.mocked(useDashboardStats).mockReturnValue({
        data: {
          total_sources: 5,
          total_datasets: 150,
          total_transformations: 75,
          total_lineage_edges: 300,
          recent_syncs: [],
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      const { container } = render(<Dashboard />);

      // Check that icon components are rendered (MUI icons render as SVG)
      const icons = container.querySelectorAll('svg');
      expect(icons.length).toBeGreaterThan(0);
    });
  });

  describe('Page Title', () => {
    it('displays dashboard title', () => {
      vi.mocked(useDashboardStats).mockReturnValue({
        data: {
          total_sources: 5,
          total_datasets: 150,
          total_transformations: 75,
          total_lineage_edges: 300,
          recent_syncs: [],
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<Dashboard />);

      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });

  describe('Data Updates', () => {
    it('displays updated data when refetched', () => {
      const { rerender } = render(<Dashboard />);

      // Initial data
      vi.mocked(useDashboardStats).mockReturnValue({
        data: {
          total_sources: 5,
          total_datasets: 150,
          total_transformations: 75,
          total_lineage_edges: 300,
          recent_syncs: [],
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      rerender(<Dashboard />);
      expect(screen.getByText('5')).toBeInTheDocument();

      // Updated data
      vi.mocked(useDashboardStats).mockReturnValue({
        data: {
          total_sources: 10,
          total_datasets: 200,
          total_transformations: 100,
          total_lineage_edges: 400,
          recent_syncs: [],
        },
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      rerender(<Dashboard />);
      expect(screen.getByText('10')).toBeInTheDocument();
      expect(screen.getByText('200')).toBeInTheDocument();
    });
  });
});
