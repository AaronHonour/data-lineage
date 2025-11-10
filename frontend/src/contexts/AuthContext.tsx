/**
 * Authentication Context
 *
 * Provides authentication state and functions throughout the app
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { jwtDecode } from 'jwt-decode';
import type { User, LoginRequest } from '@types/api';
import { apiService } from '@services/api';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

interface JWTPayload {
  sub: string;
  exp: number;
  [key: string]: unknown;
}

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check if token is valid
  const isTokenValid = (token: string): boolean => {
    try {
      const decoded = jwtDecode<JWTPayload>(token);
      const currentTime = Date.now() / 1000;
      return decoded.exp > currentTime;
    } catch {
      return false;
    }
  };

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = () => {
      const token = localStorage.getItem('auth_token');
      const storedUser = localStorage.getItem('user');

      if (token && storedUser && isTokenValid(token)) {
        try {
          setUser(JSON.parse(storedUser));
        } catch {
          // Invalid stored user data
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user');
        }
      } else {
        // Token expired or invalid
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user');
      }

      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (credentials: LoginRequest) => {
    try {
      setError(null);
      setIsLoading(true);

      const response = await apiService.login(credentials);

      // Store token and user
      localStorage.setItem('auth_token', response.access_token);
      localStorage.setItem('user', JSON.stringify(response.user));

      setUser(response.user);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
    setUser(null);
    setError(null);
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    error,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
