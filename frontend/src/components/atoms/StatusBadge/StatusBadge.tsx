/**
 * StatusBadge Component (Atom)
 *
 * Displays a colored badge for status indicators
 */

import React from 'react';
import { Chip, ChipProps } from '@mui/material';

export type StatusType = 'success' | 'error' | 'warning' | 'info' | 'pending' | 'running';

interface StatusBadgeProps extends Omit<ChipProps, 'color'> {
  status: StatusType;
}

const statusColorMap: Record<StatusType, ChipProps['color']> = {
  success: 'success',
  error: 'error',
  warning: 'warning',
  info: 'info',
  pending: 'default',
  running: 'primary',
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, ...props }) => {
  const displayLabel = label || status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <Chip
      label={displayLabel}
      color={statusColorMap[status]}
      size="small"
      {...props}
    />
  );
};

export default StatusBadge;
