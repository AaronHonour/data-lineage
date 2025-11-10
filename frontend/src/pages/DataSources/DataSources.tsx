/**
 * DataSources Page
 *
 * List and manage data sources
 */

import React from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
} from '@mui/material';
import { Sync as SyncIcon, Visibility as ViewIcon } from '@mui/icons-material';
import { useDataSources, useTriggerSync } from '@hooks/useDataSources';
import { LoadingSpinner } from '@components/atoms/LoadingSpinner/LoadingSpinner';
import { formatSourceType, formatRelativeTime } from '@utils/formatting';

export const DataSources: React.FC = () => {
  const { data: sources, isLoading, error } = useDataSources();
  const triggerSync = useTriggerSync();

  const handleSync = async (sourceId: string) => {
    try {
      await triggerSync.mutateAsync(sourceId);
      alert('Sync triggered successfully!');
    } catch (err) {
      alert('Failed to trigger sync');
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading data sources..." />;
  }

  if (error) {
    return (
      <Box>
        <Typography color="error">Failed to load data sources</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Data Sources</Typography>
      </Box>

      <Grid container spacing={3}>
        {sources && sources.length > 0 ? (
          sources.map((source) => (
            <Grid item xs={12} md={6} lg={4} key={source.id}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                    <Typography variant="h6" component="div">
                      {source.name}
                    </Typography>
                    <Chip
                      label={formatSourceType(source.source_type)}
                      color="primary"
                      size="small"
                    />
                  </Box>

                  {source.description && (
                    <Typography variant="body2" color="text.secondary" paragraph>
                      {source.description}
                    </Typography>
                  )}

                  <Typography variant="caption" color="text.secondary">
                    Created {formatRelativeTime(source.created_at)}
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button
                    size="small"
                    startIcon={<ViewIcon />}
                    onClick={() => alert('View details - TODO')}
                  >
                    View
                  </Button>
                  <Button
                    size="small"
                    startIcon={<SyncIcon />}
                    onClick={() => handleSync(source.id)}
                    disabled={triggerSync.isPending}
                  >
                    Sync
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))
        ) : (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" align="center">
                  No data sources found. Deploy the sample data to see sources here.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default DataSources;
