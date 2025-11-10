/**
 * StatusBadge Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/tests/test-utils';
import { StatusBadge } from './StatusBadge';

describe('StatusBadge', () => {
  it('renders with success status', () => {
    render(<StatusBadge status="success" />);
    expect(screen.getByText(/Success/i)).toBeInTheDocument();
  });

  it('renders with error status', () => {
    render(<StatusBadge status="error" />);
    expect(screen.getByText(/Error/i)).toBeInTheDocument();
  });

  it('renders with custom label', () => {
    render(<StatusBadge status="success" label="Completed" />);
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });

  it('renders with pending status', () => {
    render(<StatusBadge status="pending" />);
    expect(screen.getByText(/Pending/i)).toBeInTheDocument();
  });
});
