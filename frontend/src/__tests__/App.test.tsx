/**
 * App Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@/tests/test-utils';
import App from '../App';

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />);
    expect(screen.getByText(/Data Lineage/i)).toBeInTheDocument();
  });

  it('shows login page when not authenticated', () => {
    render(<App />);
    expect(screen.getByText(/Sign In/i)).toBeInTheDocument();
  });
});
