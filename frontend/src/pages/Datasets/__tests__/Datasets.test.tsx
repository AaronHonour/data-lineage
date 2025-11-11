/**
 * Datasets Page Tests
 *
 * Tests for the Datasets placeholder page covering:
 * - Page title display
 * - Icon rendering
 * - Informational content
 * - Layout structure
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/tests/test-utils';
import { Datasets } from '../Datasets';

describe('Datasets', () => {
  describe('Page Structure', () => {
    it('displays page title', () => {
      render(<Datasets />);

      expect(screen.getByText('Datasets')).toBeInTheDocument();
    });

    it('displays Dataset Explorer heading', () => {
      render(<Datasets />);

      expect(screen.getByText('Dataset Explorer')).toBeInTheDocument();
    });

    it('displays dataset icon', () => {
      const { container } = render(<Datasets />);

      const icon = container.querySelector('[data-testid="DatasetIcon"]');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Informational Content', () => {
    it('displays information about dataset browser', () => {
      render(<Datasets />);

      expect(
        screen.getByText(/Browse all datasets discovered from your data sources/i)
      ).toBeInTheDocument();
    });

    it('displays information about sample deployment', () => {
      render(<Datasets />);

      expect(
        screen.getByText(/After running the sample deployment/i)
      ).toBeInTheDocument();
    });

    it('mentions supported data sources', () => {
      render(<Datasets />);

      const infoText = screen.getByText(/PostgreSQL, MySQL, dbt models/i);
      expect(infoText).toBeInTheDocument();
    });

    it('displays content in an info alert', () => {
      const { container } = render(<Datasets />);

      const alert = container.querySelector('.MuiAlert-standardInfo');
      expect(alert).toBeInTheDocument();
    });
  });

  describe('Layout', () => {
    it('renders content within a paper component', () => {
      const { container } = render(<Datasets />);

      const paper = container.querySelector('.MuiPaper-root');
      expect(paper).toBeInTheDocument();
    });

    it('renders with centered content', () => {
      const { container } = render(<Datasets />);

      const paper = container.querySelector('.MuiPaper-root');
      expect(paper).toHaveStyle({ textAlign: 'center' });
    });
  });
});
