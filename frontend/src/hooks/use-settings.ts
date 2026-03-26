import { useState, useCallback } from 'react';

export interface AppSettings {
  vaultMode: boolean;
  riskFreeRate: number;    // decimal, e.g. 0.042
  benchmark: 'SPY' | 'QQQ' | 'VT';
  targetReturn: number;   // decimal, e.g. 0.10
}

const SETTINGS_KEY = 'arcus-settings';

export const DEFAULT_SETTINGS: AppSettings = {
  vaultMode: false,
  riskFreeRate: 0.042,
  benchmark: 'SPY',
  targetReturn: 0.10,
};

export function loadSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export function useSettings(): [AppSettings, (patch: Partial<AppSettings>) => void] {
  const [settings, setSettings] = useState<AppSettings>(loadSettings);

  const update = useCallback((patch: Partial<AppSettings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  return [settings, update];
}
