import { describe, it, expect } from 'vitest';
import { resolveApiBase, DEFAULT_BACKEND_URL, LOCAL_BACKEND_URL } from '@/lib/api';

describe('resolveApiBase', () => {
  it('prefers VITE_API_URL over everything else', () => {
    expect(resolveApiBase('https://arcus.example.com', 'arcus-insights.com')).toBe('https://arcus.example.com');
  });

  it('lets VITE_API_URL override the localhost default too', () => {
    // So a developer can point a local dev server at a staging backend.
    expect(resolveApiBase('https://staging.example.com', 'localhost')).toBe('https://staging.example.com');
  });

  it('strips trailing slashes so paths do not double up', () => {
    expect(resolveApiBase('https://arcus.example.com/', 'arcus-insights.com')).toBe('https://arcus.example.com');
    expect(resolveApiBase('https://arcus.example.com///', 'arcus-insights.com')).toBe('https://arcus.example.com');
  });

  it('ignores an unset, empty or whitespace-only value', () => {
    expect(resolveApiBase(undefined, 'arcus-insights.com')).toBe(DEFAULT_BACKEND_URL);
    expect(resolveApiBase('', 'arcus-insights.com')).toBe(DEFAULT_BACKEND_URL);
    expect(resolveApiBase('   ', 'arcus-insights.com')).toBe(DEFAULT_BACKEND_URL);
  });

  it('uses the local backend when developing', () => {
    expect(resolveApiBase(undefined, 'localhost')).toBe(LOCAL_BACKEND_URL);
    expect(resolveApiBase(undefined, '127.0.0.1')).toBe(LOCAL_BACKEND_URL);
  });

  it('falls back to the deployed backend for every other host', () => {
    expect(resolveApiBase(undefined, 'arcus-insights.com')).toBe(DEFAULT_BACKEND_URL);
    expect(resolveApiBase(undefined, 'www.arcus-insights.com')).toBe(DEFAULT_BACKEND_URL);
    expect(resolveApiBase(undefined, 'shreyas1504.github.io')).toBe(DEFAULT_BACKEND_URL);
  });
});
