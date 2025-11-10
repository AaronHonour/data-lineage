/**
 * LineageViewer Page
 *
 * Interactive lineage visualization for a specific dataset
 */

import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Button,
  Alert,
  Breadcrumbs,
  Link,
} from '@mui/material';
import { Refresh as RefreshIcon, Home as HomeIcon } from '@mui/icons-material';
import { useTableLineage } from '@hooks/useLineage';
import { LoadingSpinner } from '@components/atoms/LoadingSpinner/LoadingSpinner';
import { LineageGraph } from '@components/organisms/LineageGraph/LineageGraph';

export const LineageViewer: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();

  const [direction, setDirection] = useState<'upstream' | 'downstream' | 'both'>('both');
  const [depth, setDepth] = useState(3);

  const { data: lineageData, isLoading, error, refetch } = useTableLineage(
    datasetId || '',
    direction,
    depth
  );

  const handleRefresh = () => {
    refetch();
  };

  const handleNodeClick = (clickedDatasetId: string) => {
    navigate(`/lineage/${clickedDatasetId}`);
  };

  if (!datasetId) {
    return (
      <Box>
        <Alert severity="error">No dataset ID provided</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link
          underline="hover"
          sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}
          color="inherit"
          onClick={() => navigate('/')}
        >
          <HomeIcon sx={{ mr: 0.5 }} fontSize="inherit" />
          Home
        </Link>
        <Typography color="text.primary">Lineage</Typography>
        {lineageData && lineageData.datasets.length > 0 && (
          <Typography color="text.primary">
            {lineageData.datasets[0].name}
          </Typography>
        )}
      </Breadcrumbs>

      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Data Lineage Visualization</Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={isLoading}
        >
          Refresh
        </Button>
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Lineage Controls
        </Typography>

        <Box display="flex" gap={3} alignItems="flex-start" flexWrap="wrap">
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Direction</InputLabel>
            <Select
              value={direction}
              label="Direction"
              onChange={(e) => setDirection(e.target.value as typeof direction)}
            >
              <MenuItem value="upstream">Upstream (Sources)</MenuItem>
              <MenuItem value="downstream">Downstream (Targets)</MenuItem>
              <MenuItem value="both">Both</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ minWidth: 250 }}>
            <Typography gutterBottom>Depth: {depth}</Typography>
            <Slider
              value={depth}
              onChange={(_, value) => setDepth(value as number)}
              min={1}
              max={5}
              marks
              valueLabelDisplay="auto"
            />
          </Box>
        </Box>

        {lineageData && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Showing {lineageData.datasets.length} dataset(s) and {lineageData.edges.length}{' '}
              connection(s)
            </Typography>
          </Box>
        )}
      </Paper>

      {isLoading && <LoadingSpinner message="Loading lineage graph..." />}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load lineage data. Please ensure the dataset exists and sync has completed.
        </Alert>
      )}

      {lineageData && !isLoading && (
        <Paper sx={{ p: 2 }}>
          <LineageGraph data={lineageData} onNodeClick={handleNodeClick} />
        </Paper>
      )}
    </Box>
  );
};

export default LineageViewer;
