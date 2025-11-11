/**
 * Lineage Page Tests
 *
 * Tests for the Lineage placeholder page covering:
 * - Page title display
 * - Icon rendering
 * - Informational content
 * - Layout structure
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/tests/test-utils';
import { Lineage } from '../Lineage';

describe('Lineage', () => {
  describe('Page Structure', () => {
    it('displays page title', () => {
      render(<Lineage />);

      expect(screen.getByText('Data Lineage Visualization')).toBeInTheDocument();
    });

    it('displays Lineage Graph Visualization heading', () => {
      render(<Lineage />);

      expect(screen.getByText('Lineage Graph Visualization')).toBeInTheDocument();
    });

    it('displays lineage icon', () => {
      const { container } = render(<Lineage />);

      const icon = container.querySelector('[data-testid="AccountTreeIcon"]');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('Informational Content', () => {
    it('displays instructions for selecting a dataset', () => {
      render(<Lineage />);

      expect(
        screen.getByText(/Select a dataset from the Data Sources or Datasets page/i)
      ).toBeInTheDocument();
    });

    it('displays information about lineage graph features', () => {
      render(<Lineage />);

      expect(
        screen.getByText(/The lineage graph will show upstream sources and downstream dependencies/i)
      ).toBeInTheDocument();
    });

    it('mentions interactive controls', () => {
      render(<Lineage />);

      expect(
        screen.getByText(/interactive controls for direction and depth/i)
      ).toBeInTheDocument();
    });

    it('displays content in an info alert', () => {
      const { container } = render(<Lineage />);

      const alert = container.querySelector('.MuiAlert-standardInfo');
      expect(alert).toBeInTheDocument();
    });
  });

  describe('Layout', () => {
    it('renders content within a paper component', () => {
      const { container } = render(<Lineage />);

      const paper = container.querySelector('.MuiPaper-root');
      expect(paper).toBeInTheDocument();
    });

    it('renders with centered content', () => {
      const { container } = render(<Lineage />);

      const paper = container.querySelector('.MuiPaper-root');
      expect(paper).toHaveStyle({ textAlign: 'center' });
    });
  });
});
