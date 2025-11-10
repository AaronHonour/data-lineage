/**
 * Main App Component
 *
 * Sets up routing, authentication, and global providers
 */

import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { AuthProvider } from '@/contexts/AuthContext';
import { ProtectedRoute } from '@components/auth/ProtectedRoute';
import { MainLayout } from '@components/templates/MainLayout/MainLayout';
import { Login } from '@pages/Login/Login';
import { Dashboard } from '@pages/Dashboard/Dashboard';
import { DataSources } from '@pages/DataSources/DataSources';
import { Lineage } from '@pages/Lineage/Lineage';
import { LineageViewer } from '@pages/Lineage/LineageViewer';
import { Datasets } from '@pages/Datasets/Datasets';
import { theme } from './theme';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30 seconds
    },
  },
});

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <MainLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="sources" element={<DataSources />} />
              <Route path="datasets" element={<Datasets />} />
              <Route path="lineage" element={<Lineage />} />
              <Route path="lineage/:datasetId" element={<LineageViewer />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
};

export default App;
