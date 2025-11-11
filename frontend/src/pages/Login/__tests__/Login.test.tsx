/**
 * Login Page Tests
 *
 * Comprehensive tests for the Login page component covering:
 * - Form rendering
 * - User input handling
 * - Form validation
 * - Login success/failure
 * - Loading states
 * - Navigation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/tests/test-utils';
import userEvent from '@testing-library/user-event';
import { Login } from '../Login';

// Mock react-router-dom
const mockNavigate = vi.fn();
const mockLocation = { state: null };

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
  };
});

// Mock AuthContext
const mockLogin = vi.fn();
const mockAuthError = null;

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    login: mockLogin,
    error: mockAuthError,
    user: null,
    isAuthenticated: false,
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocation.state = null;
  });

  describe('Form Rendering', () => {
    it('renders login form with all elements', () => {
      render(<Login />);

      expect(screen.getByRole('heading', { name: /Data Lineage/i })).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /Sign In/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('displays demo credentials info', () => {
      render(<Login />);

      expect(screen.getByText(/Demo credentials:/i)).toBeInTheDocument();
      // "admin" appears twice - for username and password
      const adminElements = screen.getAllByText('admin', { selector: 'code' });
      expect(adminElements.length).toBe(2);
    });

    it('displays app icon', () => {
      const { container } = render(<Login />);

      const icon = container.querySelector('[data-testid="AccountTreeIcon"]');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('User Input', () => {
    it('updates username field when user types', async () => {
      const user = userEvent.setup();
      render(<Login />);

      const usernameInput = screen.getByLabelText(/username/i) as HTMLInputElement;

      await user.type(usernameInput, 'testuser');

      expect(usernameInput.value).toBe('testuser');
    });

    it('updates password field when user types', async () => {
      const user = userEvent.setup();
      render(<Login />);

      const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;

      await user.type(passwordInput, 'password123');

      expect(passwordInput.value).toBe('password123');
    });

    it('password field is type="password"', () => {
      render(<Login />);

      const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement;

      expect(passwordInput.type).toBe('password');
    });
  });

  describe('Form Validation', () => {
    it('submit button is disabled when fields are empty', () => {
      render(<Login />);

      const submitButton = screen.getByRole('button', { name: /sign in/i });

      expect(submitButton).toBeDisabled();
    });

    it('submit button is disabled when only username is filled', async () => {
      const user = userEvent.setup();
      render(<Login />);

      const usernameInput = screen.getByLabelText(/username/i);
      await user.type(usernameInput, 'testuser');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      expect(submitButton).toBeDisabled();
    });

    it('submit button is disabled when only password is filled', async () => {
      const user = userEvent.setup();
      render(<Login />);

      const passwordInput = screen.getByLabelText(/password/i);
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      expect(submitButton).toBeDisabled();
    });

    it('submit button is enabled when both fields are filled', async () => {
      const user = userEvent.setup();
      render(<Login />);

      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);

      await user.type(usernameInput, 'testuser');
      await user.type(passwordInput, 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      expect(submitButton).not.toBeDisabled();
    });
  });

  describe('Login Success', () => {
    it('calls login with correct credentials on submit', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue(undefined);

      render(<Login />);

      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(usernameInput, 'admin');
      await user.type(passwordInput, 'admin');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          username: 'admin',
          password: 'admin',
        });
      });
    });

    it('navigates to home page after successful login', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue(undefined);

      render(<Login />);

      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(usernameInput, 'admin');
      await user.type(passwordInput, 'admin');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
      });
    });

    it('navigates to original location after successful login', async () => {
      const user = userEvent.setup();
      mockLogin.mockResolvedValue(undefined);
      mockLocation.state = { from: { pathname: '/data-sources' } };

      render(<Login />);

      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(usernameInput, 'admin');
      await user.type(passwordInput, 'admin');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/data-sources', { replace: true });
      });
    });
  });

  describe('Login Failure', () => {
    it('displays error message when login fails', async () => {
      const user = userEvent.setup();
      mockLogin.mockRejectedValue(new Error('Invalid credentials'));

      render(<Login />);

      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(usernameInput, 'wrong');
      await user.type(passwordInput, 'wrong');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Login failed/i)).toBeInTheDocument();
      });
    });

    it('does not navigate when login fails', async () => {
      const user = userEvent.setup();
      mockLogin.mockRejectedValue(new Error('Invalid credentials'));

      render(<Login />);

      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(usernameInput, 'wrong');
      await user.type(passwordInput, 'wrong');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Login failed/i)).toBeInTheDocument();
      });

      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  describe('Loading State', () => {
    it('shows loading spinner during login', async () => {
      const user = userEvent.setup();
      mockLogin.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(<Login />);

      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(usernameInput, 'admin');
      await user.type(passwordInput, 'admin');
      await user.click(submitButton);

      // During loading
      expect(screen.getByRole('progressbar')).toBeInTheDocument();

      // After loading completes
      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
      });
    });

    it('disables form fields during login', async () => {
      const user = userEvent.setup();
      mockLogin.mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      render(<Login />);

      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      await user.type(usernameInput, 'admin');
      await user.type(passwordInput, 'admin');
      await user.click(submitButton);

      // During loading - fields should be disabled
      expect(usernameInput).toBeDisabled();
      expect(passwordInput).toBeDisabled();
      expect(submitButton).toBeDisabled();

      // After loading completes
      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('clears previous error when retrying login', async () => {
      const user = userEvent.setup();
      mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'));
      mockLogin.mockResolvedValueOnce(undefined);

      render(<Login />);

      const usernameInput = screen.getByLabelText(/username/i);
      const passwordInput = screen.getByLabelText(/password/i);
      const submitButton = screen.getByRole('button', { name: /sign in/i });

      // First attempt - fail
      await user.type(usernameInput, 'wrong');
      await user.type(passwordInput, 'wrong');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Login failed/i)).toBeInTheDocument();
      });

      // Clear and retry
      await user.clear(usernameInput);
      await user.clear(passwordInput);
      await user.type(usernameInput, 'admin');
      await user.type(passwordInput, 'admin');
      await user.click(submitButton);

      // Error should be cleared during second attempt
      await waitFor(() => {
        expect(screen.queryByText(/Login failed/i)).not.toBeInTheDocument();
      });
    });
  });
});
