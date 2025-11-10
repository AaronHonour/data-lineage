/**
 * Datasets Page
 *
 * Browse and search datasets
 */

import React from 'react';
import { Box, Typography, Paper, Alert } from '@mui/material';
import { Dataset as DatasetIcon } from '@mui/icons-material';

export const Datasets: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Datasets
      </Typography>

      <Paper sx={{ p: 4, textAlign: 'center', minHeight: 400 }}>
        <DatasetIcon sx={{ fontSize: 80, color: 'action.disabled', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          Dataset Explorer
        </Typography>
        <Alert severity="info" sx={{ mt: 3, maxWidth: 600, mx: 'auto' }}>
          <Typography variant="body2">
            Browse all datasets discovered from your data sources.
            <br />
            <br />
            After running the sample deployment, datasets from PostgreSQL, MySQL, dbt models,
            and Python jobs will appear here.
          </Typography>
        </Alert>
      </Paper>
    </Box>
  );
};

export default Datasets;
