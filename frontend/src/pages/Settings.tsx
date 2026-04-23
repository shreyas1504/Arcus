import { useState } from 'react';
import type { ElementType, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Settings2, Shield, Target, BarChart2, EyeOff, Download, Trash2, RotateCcw } from 'lucide-react';
import AppLayout from '@/components/AppLayout';
import { useSettings, DEFAULT_SETTINGS, AppSettings } from '@/hooks/use-settings';

// ── Sub-components ─────────────────────────────────────────────────────────

const Section = ({
  title,
  icon: Icon,
  children,
  delay = 0,
}: {
  title: string;
  icon: ElementType;
  children: ReactNode;
  delay?: number;
}) => (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className="glass rounded-xl p-5 mb-4"
  >
    <div className="flex items-center gap-2 mb-5 pb-3 border-b border-border">
      <Icon size={14} className="text-primary" />
      <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>{title}</span>
    </div>
    <div className="space-y-5">{children}</div>
  </motion.div>
);

const SettingRow = ({
  label,
  description,
  children,
}: {
  label: string;
  description: string;
  children: ReactNode;
}) => (
  <div className="flex items-center justify-between gap-6">
    <div className="min-w-0">
      <div className="font-mono text-xs font-medium text-foreground">{label}</div>
      <div className="font-mono text-[10px] text-muted-foreground mt-0.5 leading-relaxed">{description}</div>
    </div>
    <div className="flex-shrink-0">{children}</div>
  </div>
);

const Toggle = ({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) => (
  <button
    role="switch"
    aria-checked={checked}
    onClick={() => onChange(!checked)}
    className={`relative w-10 h-5 rounded-full transition-colors duration-200 ${
      checked ? 'bg-primary' : 'bg-border'
    }`}
  >
    <span
      className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
        checked ? 'translate-x-5' : 'translate-x-0'
      }`}
    />
  </button>
);

// ── Main Page ──────────────────────────────────────────────────────────────

const Settings = () => {
  const [settings, update] = useSettings();
  const [exported, setExported] = useState(false);

  const handleExport = () => {
    const data = {
      portfolio: JSON.parse(localStorage.getItem('arcus-portfolio') ?? 'null'),
      investorDna: JSON.parse(localStorage.getItem('arcus-investor-dna') ?? 'null'),
      settings: JSON.parse(localStorage.getItem('arcus-settings') ?? 'null'),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'arcus-data.json';
    a.click();
    URL.revokeObjectURL(url);
    setExported(true);
    setTimeout(() => setExported(false), 2500);
  };

  const handleWipe = () => {
    if (!window.confirm('Clear all Arcus data and return to onboarding? This cannot be undone.')) return;
    ['arcus-portfolio', 'arcus-investor-dna', 'arcus-settings', 'arcus-last-analysis', 'arcus-portfolio-draft', 'arcus-onboarding-state'].forEach(
      (k) => localStorage.removeItem(k),
    );
    window.location.href = import.meta.env.BASE_URL || '/';
  };

  return (
    <AppLayout>
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-3 mb-1.5">
            <Settings2 size={20} className="text-primary" />
            <h1 className="font-display font-bold text-xl text-foreground">Command Center</h1>
          </div>
          <p className="font-mono text-[11px] text-muted-foreground">
            Control how Arcus analyzes your portfolio. Changes apply on the next analysis run.
          </p>
        </motion.div>

        {/* Analysis Parameters */}
        <Section title="ANALYSIS PARAMETERS" icon={BarChart2} delay={0.05}>
          <SettingRow
            label="Risk-Free Rate"
            description="US Treasury yield used for Sharpe & Sortino ratio calculations"
          >
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="0"
                max="10"
                step="0.1"
                value={(settings.riskFreeRate * 100).toFixed(1)}
                onChange={(e) => update({ riskFreeRate: parseFloat(e.target.value) / 100 })}
                className="w-28 accent-primary cursor-pointer"
              />
              <span className="font-mono text-sm font-semibold text-foreground w-12 text-right tabular-nums">
                {(settings.riskFreeRate * 100).toFixed(1)}%
              </span>
            </div>
          </SettingRow>

          <SettingRow
            label="Market Benchmark"
            description="Index used for alpha, beta & performance chart comparison"
          >
            <select
              value={settings.benchmark}
              onChange={(e) => update({ benchmark: e.target.value as AppSettings['benchmark'] })}
              className="bg-card border border-border rounded-lg px-3 py-1.5 font-mono text-xs text-foreground focus:outline-none focus:border-primary/50 cursor-pointer"
            >
              <option value="SPY">S&amp;P 500 (SPY)</option>
              <option value="QQQ">Nasdaq 100 (QQQ)</option>
              <option value="VT">Global All-World (VT)</option>
            </select>
          </SettingRow>
        </Section>

        {/* Portfolio Goals */}
        <Section title="PORTFOLIO GOALS" icon={Target} delay={0.1}>
          <SettingRow
            label="Target Annual Return"
            description="Renders a reference line on the Monte Carlo projection chart"
          >
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="1"
                max="30"
                step="1"
                value={Math.round(settings.targetReturn * 100)}
                onChange={(e) => update({ targetReturn: parseFloat(e.target.value) / 100 })}
                className="w-28 accent-primary cursor-pointer"
              />
              <span className="font-mono text-sm font-semibold text-foreground w-12 text-right tabular-nums">
                {(settings.targetReturn * 100).toFixed(0)}%
              </span>
            </div>
          </SettingRow>
        </Section>

        {/* Privacy */}
        <Section title="PRIVACY & DATA" icon={Shield} delay={0.15}>
          <SettingRow
            label="Vault Mode"
            description="Blur all dollar amounts — share your screen without revealing net worth"
          >
            <div className="flex items-center gap-2">
              {settings.vaultMode && (
                <span className="flex items-center gap-1 font-mono text-[10px] text-primary/70">
                  <EyeOff size={10} /> Active
                </span>
              )}
              <Toggle checked={settings.vaultMode} onChange={(v) => update({ vaultMode: v })} />
            </div>
          </SettingRow>

          <SettingRow
            label="Export Data"
            description="Download your portfolio config, investor DNA & settings as JSON"
          >
            <button
              onClick={handleExport}
              className="flex items-center gap-2 font-mono text-xs border border-border hover:border-primary/40 text-muted-foreground hover:text-foreground px-3 py-1.5 rounded-lg transition-colors"
            >
              <Download size={11} />
              {exported ? 'Downloaded!' : 'Export JSON'}
            </button>
          </SettingRow>

          <SettingRow
            label="Wipe All Data"
            description="Clear all saved portfolios and return to the onboarding flow"
          >
            <button
              onClick={handleWipe}
              className="flex items-center gap-2 font-mono text-xs border border-red-500/30 hover:border-red-500/60 text-red-400/70 hover:text-red-400 px-3 py-1.5 rounded-lg transition-colors"
            >
              <Trash2 size={11} />
              Clear Data
            </button>
          </SettingRow>
        </Section>

        {/* Reset to defaults */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="flex justify-end mt-2"
        >
          <button
            onClick={() => update(DEFAULT_SETTINGS)}
            className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground hover:text-foreground transition-colors"
          >
            <RotateCcw size={11} />
            Reset to defaults
          </button>
        </motion.div>
      </div>
    </AppLayout>
  );
};

export default Settings;
