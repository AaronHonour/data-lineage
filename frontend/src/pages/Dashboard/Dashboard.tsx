/**
 * Dashboard Page
 *
 * Overview of system statistics and recent activity
 */

import React from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  Storage as StorageIcon,
  Dataset as DatasetIcon,
  Transform as TransformIcon,
  AccountTree as LineageIcon,
} from '@mui/icons-material';
import { useDashboardStats } from '@hooks/useDashboard';
import { LoadingSpinner } from '@components/atoms/LoadingSpinner/LoadingSpinner';
import { StatusBadge } from '@components/atoms/StatusBadge/StatusBadge';
import { formatRelativeTime } from '@utils/formatting';

export const Dashboard: React.FC = () => {
  const { data: stats, isLoading, error } = useDashboardStats();

  if (isLoading) {
    return <LoadingSpinner message="Loading dashboard..." />;
  }

  if (error) {
    return (
      <Box>
        <Typography color="error">Failed to load dashboard data</Typography>
      </Box>
    );
  }

  const statCards = [
    {
      title: 'Data Sources',
      value: stats?.total_sources || 0,
      icon: <StorageIcon sx={{ fontSize: 40 }} />,
      color: '#1976d2',
    },
    {
      title: 'Datasets',
      value: stats?.total_datasets || 0,
      icon: <DatasetIcon sx={{ fontSize: 40 }} />,
      color: '#2e7d32',
    },
    {
      title: 'Transformations',
      value: stats?.total_transformations || 0,
      icon: <TransformIcon sx={{ fontSize: 40 }} />,
      color: '#ed6c02',
    },
    {
      title: 'Lineage Edges',
      value: stats?.total_lineage_edges || 0,
      icon: <LineageIcon sx={{ fontSize: 40 }} />,
      color: '#9c27b0',
    },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {statCards.map((card) => (
          <Grid item xs={12} sm={6} md={3} key={card.title}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                  <Box>
                    <Typography color="textSecondary" gutterBottom variant="body2">
                      {card.title}
                    </Typography>
                    <Typography variant="h4">{card.value}</Typography>
                  </Box>
                  <Box sx={{ color: card.color }}>{card.icon}</Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Recent Sync Jobs
      </Typography>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Status</TableCell>
              <TableCell>Data Source</TableCell>
              <TableCell align="right">Datasets</TableCell>
              <TableCell align="right">Transformations</TableCell>
              <TableCell align="right">Edges</TableCell>
              <TableCell>Time</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {stats?.recent_syncs && stats.recent_syncs.length > 0 ? (
              stats.recent_syncs.map((job) => (
                <TableRow key={job.id}>
                  <TableCell>
                    <StatusBadge
                      status={
                        job.status === 'completed'
                          ? 'success'
                          : job.status === 'failed'
                          ? 'error'
                          : job.status === 'running'
                          ? 'running'
                          : 'pending'
                      }
                      label={job.status}
                    />
                  </TableCell>
                  <TableCell>{job.data_source_id.substring(0, 8)}...</TableCell>
                  <TableCell align="right">{job.statistics?.datasets_discovered || 0}</TableCell>
                  <TableCell align="right">
                    {job.statistics?.transformations_discovered || 0}
                  </TableCell>
                  <TableCell align="right">
                    {job.statistics?.lineage_edges_created || 0}
                  </TableCell>
                  <TableCell>{formatRelativeTime(job.created_at)}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography color="textSecondary">No recent sync jobs</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default Dashboard;
