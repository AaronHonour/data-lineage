/**
 * Lineage Page
 *
 * Visualize data lineage graph
 */

import React from 'react';
import { Box, Typography, Paper, Alert } from '@mui/material';
import { AccountTree as LineageIcon } from '@mui/icons-material';

export const Lineage: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Data Lineage Visualization
      </Typography>

      <Paper sx={{ p: 4, textAlign: 'center', minHeight: 400 }}>
        <LineageIcon sx={{ fontSize: 80, color: 'action.disabled', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          Lineage Graph Visualization
        </Typography>
        <Alert severity="info" sx={{ mt: 3, maxWidth: 600, mx: 'auto' }}>
          <Typography variant="body2">
            Select a dataset from the Data Sources or Datasets page to visualize its lineage.
            <br />
            <br />
            The lineage graph will show upstream sources and downstream dependencies with
            interactive controls for direction and depth.
          </Typography>
        </Alert>
      </Paper>
    </Box>
  );
};

export default Lineage;
