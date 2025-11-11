/**
 * DataSources Page Tests
 *
 * Comprehensive tests for the DataSources page component covering:
 * - Loading states
 * - Error handling
 * - Data sources display
 * - Sync functionality
 * - Empty state
 * - Card formatting
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/tests/test-utils';
import userEvent from '@testing-library/user-event';
import { DataSources } from '../DataSources';

// Mock the hooks
const mockTriggerSync = {
  mutateAsync: vi.fn(),
  isPending: false,
};

vi.mock('@hooks/useDataSources', () => ({
  useDataSources: vi.fn(),
  useTriggerSync: () => mockTriggerSync,
}));

import { useDataSources } from '@hooks/useDataSources';

// Mock window.alert
const mockAlert = vi.fn();
global.alert = mockAlert;

describe('DataSources', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTriggerSync.isPending = false;
  });

  describe('Loading State', () => {
    it('displays loading spinner when data is loading', () => {
      vi.mocked(useDataSources).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        isError: false,
        isSuccess: false,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
      expect(screen.getByText('Loading data sources...')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('displays error message when data fails to load', () => {
      vi.mocked(useDataSources).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Network error'),
        isError: true,
        isSuccess: false,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      expect(screen.getByText('Failed to load data sources')).toBeInTheDocument();
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('displays empty state message when no data sources exist', () => {
      vi.mocked(useDataSources).mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      expect(screen.getByText('Data Sources')).toBeInTheDocument();
      expect(
        screen.getByText('No data sources found. Deploy the sample data to see sources here.')
      ).toBeInTheDocument();
    });
  });

  describe('Data Sources Display', () => {
    const mockDataSources = [
      {
        id: 'source-1',
        name: 'PostgreSQL Database',
        source_type: 'postgres',
        description: 'Main production database',
        created_at: '2025-01-01T10:00:00Z',
        updated_at: '2025-01-01T10:00:00Z',
        connection_info: { host: 'localhost' },
      },
      {
        id: 'source-2',
        name: 'MySQL Database',
        source_type: 'mysql',
        description: 'Analytics database',
        created_at: '2025-01-02T10:00:00Z',
        updated_at: '2025-01-02T10:00:00Z',
        connection_info: { host: 'localhost' },
      },
    ];

    it('displays all data sources in cards', () => {
      vi.mocked(useDataSources).mockReturnValue({
        data: mockDataSources,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      expect(screen.getByText('PostgreSQL Database')).toBeInTheDocument();
      expect(screen.getByText('MySQL Database')).toBeInTheDocument();
    });

    it('displays data source descriptions', () => {
      vi.mocked(useDataSources).mockReturnValue({
        data: mockDataSources,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      expect(screen.getByText('Main production database')).toBeInTheDocument();
      expect(screen.getByText('Analytics database')).toBeInTheDocument();
    });

    it('displays formatted source types', () => {
      vi.mocked(useDataSources).mockReturnValue({
        data: mockDataSources,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      // formatSourceType should convert 'postgres' to 'PostgreSQL' and 'mysql' to 'MySQL'
      expect(screen.getByText('PostgreSQL')).toBeInTheDocument();
      expect(screen.getByText('MySQL')).toBeInTheDocument();
    });

    it('displays relative time for creation date', () => {
      vi.mocked(useDataSources).mockReturnValue({
        data: mockDataSources,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      const { container } = render(<DataSources />);

      // formatRelativeTime should display something like "Created X ago"
      const captions = container.querySelectorAll('.MuiTypography-caption');
      expect(captions.length).toBeGreaterThan(0);
    });

    it('displays View and Sync buttons for each source', () => {
      vi.mocked(useDataSources).mockReturnValue({
        data: mockDataSources,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      const viewButtons = screen.getAllByRole('button', { name: /view/i });
      const syncButtons = screen.getAllByRole('button', { name: /sync/i });

      expect(viewButtons).toHaveLength(2);
      expect(syncButtons).toHaveLength(2);
    });

    it('handles data sources without descriptions', () => {
      const sourcesWithoutDescription = [
        {
          id: 'source-3',
          name: 'BigQuery Dataset',
          source_type: 'bigquery',
          created_at: '2025-01-03T10:00:00Z',
          updated_at: '2025-01-03T10:00:00Z',
          connection_info: {},
        },
      ];

      vi.mocked(useDataSources).mockReturnValue({
        data: sourcesWithoutDescription,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      expect(screen.getByText('BigQuery Dataset')).toBeInTheDocument();
      // Description should not be rendered
      expect(screen.queryByText('Main production database')).not.toBeInTheDocument();
    });
  });

  describe('Sync Functionality', () => {
    const mockDataSources = [
      {
        id: 'source-1',
        name: 'PostgreSQL Database',
        source_type: 'postgres',
        description: 'Main production database',
        created_at: '2025-01-01T10:00:00Z',
        updated_at: '2025-01-01T10:00:00Z',
        connection_info: { host: 'localhost' },
      },
    ];

    it('calls triggerSync when sync button is clicked', async () => {
      const user = userEvent.setup();
      mockTriggerSync.mutateAsync.mockResolvedValue({});

      vi.mocked(useDataSources).mockReturnValue({
        data: mockDataSources,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      const syncButton = screen.getByRole('button', { name: /sync/i });
      await user.click(syncButton);

      await waitFor(() => {
        expect(mockTriggerSync.mutateAsync).toHaveBeenCalledWith('source-1');
      });
    });

    it('displays success alert when sync is triggered successfully', async () => {
      const user = userEvent.setup();
      mockTriggerSync.mutateAsync.mockResolvedValue({});

      vi.mocked(useDataSources).mockReturnValue({
        data: mockDataSources,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      const syncButton = screen.getByRole('button', { name: /sync/i });
      await user.click(syncButton);

      await waitFor(() => {
        expect(mockAlert).toHaveBeenCalledWith('Sync triggered successfully!');
      });
    });

    it('displays error alert when sync fails', async () => {
      const user = userEvent.setup();
      mockTriggerSync.mutateAsync.mockRejectedValue(new Error('Sync failed'));

      vi.mocked(useDataSources).mockReturnValue({
        data: mockDataSources,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      const syncButton = screen.getByRole('button', { name: /sync/i });
      await user.click(syncButton);

      await waitFor(() => {
        expect(mockAlert).toHaveBeenCalledWith('Failed to trigger sync');
      });
    });

    it('disables sync button when sync is pending', () => {
      mockTriggerSync.isPending = true;

      vi.mocked(useDataSources).mockReturnValue({
        data: mockDataSources,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      const syncButton = screen.getByRole('button', { name: /sync/i });
      expect(syncButton).toBeDisabled();
    });
  });

  describe('View Functionality', () => {
    it('shows alert when view button is clicked', async () => {
      const user = userEvent.setup();
      const mockDataSources = [
        {
          id: 'source-1',
          name: 'PostgreSQL Database',
          source_type: 'postgres',
          description: 'Main production database',
          created_at: '2025-01-01T10:00:00Z',
          updated_at: '2025-01-01T10:00:00Z',
          connection_info: { host: 'localhost' },
        },
      ];

      vi.mocked(useDataSources).mockReturnValue({
        data: mockDataSources,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      const viewButton = screen.getByRole('button', { name: /view/i });
      await user.click(viewButton);

      expect(mockAlert).toHaveBeenCalledWith('View details - TODO');
    });
  });

  describe('Page Structure', () => {
    it('displays page title', () => {
      vi.mocked(useDataSources).mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      render(<DataSources />);

      expect(screen.getByText('Data Sources')).toBeInTheDocument();
    });

    it('renders data sources in a grid layout', () => {
      const mockDataSources = [
        {
          id: 'source-1',
          name: 'PostgreSQL Database',
          source_type: 'postgres',
          created_at: '2025-01-01T10:00:00Z',
          updated_at: '2025-01-01T10:00:00Z',
          connection_info: {},
        },
        {
          id: 'source-2',
          name: 'MySQL Database',
          source_type: 'mysql',
          created_at: '2025-01-02T10:00:00Z',
          updated_at: '2025-01-02T10:00:00Z',
          connection_info: {},
        },
      ];

      vi.mocked(useDataSources).mockReturnValue({
        data: mockDataSources,
        isLoading: false,
        error: null,
        isError: false,
        isSuccess: true,
        refetch: vi.fn(),
      } as any);

      const { container } = render(<DataSources />);

      // Check for MUI Grid container
      const gridContainer = container.querySelector('.MuiGrid-container');
      expect(gridContainer).toBeInTheDocument();
    });
  });
});
