/**
 * Formatting Utilities
 *
 * Helper functions for formatting dates, numbers, etc.
 */

import { format, formatDistanceToNow, parseISO } from 'date-fns';

/**
 * Format a date string to a readable format
 */
export const formatDate = (dateString: string, formatString: string = 'PPp'): string => {
  try {
    const date = parseISO(dateString);
    return format(date, formatString);
  } catch {
    return 'Invalid date';
  }
};

/**
 * Format a date string to relative time (e.g., "2 hours ago")
 */
export const formatRelativeTime = (dateString: string): string => {
  try {
    const date = parseISO(dateString);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return 'Invalid date';
  }
};

/**
 * Format a number with thousand separators
 */
export const formatNumber = (num: number): string => {
  return new Intl.NumberFormat('en-US').format(num);
};

/**
 * Format bytes to human-readable size
 */
export const formatBytes = (bytes: number, decimals: number = 2): string => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Format duration in seconds to human-readable string
 */
export const formatDuration = (seconds: number): string => {
  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
};

/**
 * Truncate text to specified length
 */
export const truncate = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

/**
 * Get initials from a name
 */
export const getInitials = (name: string): string => {
  const parts = name.split(' ').filter(part => part.length > 0);

  // If single name, take first 2 letters
  if (parts.length === 1) {
    return parts[0].substring(0, 2).toUpperCase();
  }

  // For multiple names, take first letter of first 2 words
  return parts
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
};

/**
 * Capitalize first letter
 */
export const capitalize = (text: string): string => {
  return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
};

/**
 * Format data source type to display name
 */
export const formatSourceType = (type: string): string => {
  const typeMap: Record<string, string> = {
    postgres: 'PostgreSQL',
    mysql: 'MySQL',
    sqlserver: 'SQL Server',
    dbt: 'dbt',
    python: 'Python',
    iceberg: 'Apache Iceberg',
    delta: 'Delta Lake',
  };

  return typeMap[type] || capitalize(type);
};
