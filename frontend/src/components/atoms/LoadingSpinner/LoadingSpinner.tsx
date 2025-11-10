/**
 * LoadingSpinner Component (Atom)
 */

import React from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';

interface LoadingSpinnerProps {
  message?: string;
  size?: number;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ message, size = 40 }) => {
  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      minHeight="200px"
      gap={2}
    >
      <CircularProgress size={size} />
      {message && <Typography color="text.secondary">{message}</Typography>}
    </Box>
  );
};

export default LoadingSpinner;
