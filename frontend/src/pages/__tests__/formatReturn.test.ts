import { describe, expect, it } from 'vitest';
import { formatReturn } from '../ScenarioLab';

describe('formatReturn', () => {
  it('never shows −0.0% for tiny negatives that round to zero', () => {
    expect(formatReturn(-0.0004)).toBe('0.0%');
    expect(formatReturn(-0.00049)).toBe('0.0%');
    expect(formatReturn(0)).toBe('0.0%');
    expect(formatReturn(0.0004)).toBe('0.0%');
  });

  it('keeps a signed one-decimal percent for non-flat moves', () => {
    expect(formatReturn(-0.074)).toBe('−7.4%');
    expect(formatReturn(0.163)).toBe('+16.3%');
  });

  it('uses an em dash for missing values', () => {
    expect(formatReturn(null)).toBe('—');
    expect(formatReturn(undefined)).toBe('—');
    expect(formatReturn(Number.NaN)).toBe('—');
  });
});
