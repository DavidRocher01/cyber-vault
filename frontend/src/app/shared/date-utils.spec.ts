import { describe, expect, it } from 'vitest';

import { formatFrDate } from './date-utils';

describe('formatFrDate', () => {
  const iso = '2026-07-25T14:30:00';

  it('formats date-only (default preset)', () => {
    expect(formatFrDate(iso)).toBe('25 juil. 2026');
  });

  it('formats date + time', () => {
    expect(formatFrDate(iso, 'datetime')).toBe('25 juil. 2026, 14:30');
  });

  it('formats long month', () => {
    expect(formatFrDate(iso, 'long')).toBe('25 juillet 2026');
  });

  it('returns em dash for null / undefined / empty', () => {
    expect(formatFrDate(null)).toBe('—');
    expect(formatFrDate(undefined)).toBe('—');
    expect(formatFrDate('')).toBe('—');
  });

  it('returns em dash for an invalid date string', () => {
    expect(formatFrDate('not-a-date')).toBe('—');
  });

  it('accepts a Date instance', () => {
    expect(formatFrDate(new Date(iso), 'date')).toBe('25 juil. 2026');
  });
});
