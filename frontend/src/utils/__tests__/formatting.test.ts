/**
 * Formatting Utilities Tests
 */

import { describe, it, expect } from 'vitest';
import {
  formatNumber,
  formatBytes,
  formatDuration,
  truncate,
  getInitials,
  capitalize,
  formatSourceType,
} from '../formatting';

describe('formatNumber', () => {
  it('formats numbers with thousand separators', () => {
    expect(formatNumber(1000)).toBe('1,000');
    expect(formatNumber(1000000)).toBe('1,000,000');
    expect(formatNumber(42)).toBe('42');
  });
});

describe('formatBytes', () => {
  it('formats bytes correctly', () => {
    expect(formatBytes(0)).toBe('0 Bytes');
    expect(formatBytes(1024)).toBe('1 KB');
    expect(formatBytes(1048576)).toBe('1 MB');
  });
});

describe('formatDuration', () => {
  it('formats durations correctly', () => {
    expect(formatDuration(30)).toBe('30s');
    expect(formatDuration(90)).toBe('1m 30s');
    expect(formatDuration(3600)).toBe('1h');
    expect(formatDuration(3660)).toBe('1h 1m');
  });
});

describe('truncate', () => {
  it('truncates long strings', () => {
    expect(truncate('Hello World', 5)).toBe('Hello...');
    expect(truncate('Short', 10)).toBe('Short');
  });
});

describe('getInitials', () => {
  it('gets initials from names', () => {
    expect(getInitials('John Doe')).toBe('JD');
    expect(getInitials('Jane')).toBe('JA');
    expect(getInitials('Alice Bob Charlie')).toBe('AB');
  });
});

describe('capitalize', () => {
  it('capitalizes first letter', () => {
    expect(capitalize('hello')).toBe('Hello');
    expect(capitalize('WORLD')).toBe('World');
  });
});

describe('formatSourceType', () => {
  it('formats source types correctly', () => {
    expect(formatSourceType('postgres')).toBe('PostgreSQL');
    expect(formatSourceType('mysql')).toBe('MySQL');
    expect(formatSourceType('dbt')).toBe('dbt');
    expect(formatSourceType('unknown')).toBe('Unknown');
  });
});
