/**
 * LoadingSpinner Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/tests/test-utils';
import { LoadingSpinner } from './LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders loading spinner', () => {
    render(<LoadingSpinner />);
    // CircularProgress is rendered
    const spinner = screen.getByRole('progressbar');
    expect(spinner).toBeInTheDocument();
  });

  it('renders with custom message', () => {
    render(<LoadingSpinner message="Loading data..." />);
    expect(screen.getByText('Loading data...')).toBeInTheDocument();
  });

  it('does not render message when not provided', () => {
    render(<LoadingSpinner />);
    const container = screen.getByRole('progressbar').closest('div');
    expect(container).toBeInTheDocument();
    // Only CircularProgress should be present, no Typography
    expect(screen.queryByText(/./)).not.toBeInTheDocument();
  });

  it('renders with custom size', () => {
    render(<LoadingSpinner size={60} />);
    const spinner = screen.getByRole('progressbar');
    expect(spinner).toBeInTheDocument();
    // Size is applied as a CSS property
    expect(spinner).toHaveStyle({ width: '60px', height: '60px' });
  });

  it('renders with default size when not specified', () => {
    render(<LoadingSpinner />);
    const spinner = screen.getByRole('progressbar');
    expect(spinner).toHaveStyle({ width: '40px', height: '40px' });
  });
});
