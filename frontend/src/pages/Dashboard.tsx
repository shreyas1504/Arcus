import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Upload, ChevronRight, Calendar, Trash2, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '@/components/AppLayout';
import BackButton from '@/components/BackButton';
import StockSearch from '@/components/StockSearch';
import { MOCK_STOCK_PRICES } from '@/lib/mock-data';

const STORAGE_KEY = 'arcus-portfolio-draft';
const SAVED_KEY = 'arcus-portfolio';

interface Holding {
  ticker: string;
  shares: string;
  cost: string;
}

// Sector → representative tickers mapping (all must exist in StockSearch STOCK_DB)
const SECTOR_TICKERS: Record<string, string[]> = {
  'Technology': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'CRM', 'ADBE'],
  'Healthcare': ['UNH', 'JNJ', 'PFE', 'ABBV', 'TMO', 'MRK'],
  'Energy':     ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC'],
  'Financials': ['JPM', 'V', 'MA', 'BAC', 'GS', 'BLK'],
  'Consumer':   ['AMZN', 'TSLA', 'HD', 'NKE', 'SBUX', 'MCD'],
  'Real Estate':['AMT', 'PLD', 'CCI', 'SPG', 'O', 'WELL'],
  'Utilities':  ['NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE'],
};

// Default presets shown when no sectors selected in onboarding
const DEFAULT_PRESETS: Record<string, string[]> = {
  'FAANG':      ['META', 'AAPL', 'AMZN', 'NFLX', 'GOOGL'],
  'Tech Heavy': ['NVDA', 'MSFT', 'CRM', 'ADBE', 'AMD'],
  'Balanced':   ['AAPL', 'JNJ', 'JPM', 'XOM', 'VOO'],
  'S&P 500':   ['VOO', 'SPY', 'VTI', 'QQQ'],
};

interface PresetConfig {
  key: string;
  label: string;
  tickers: string[];
}

// When sectors were chosen: one button per sector + an "All Picks" button.
// When no sectors chosen: show the classic FAANG / Tech Heavy / Balanced / S&P 500 buttons.
const getPresets = (): PresetConfig[] => {
  const dna = (() => { try { return JSON.parse(localStorage.getItem('arcus-investor-dna') || 'null'); } catch { return null; } })();
  const userSectors: string[] = dna?.sectors || [];

  if (userSectors.length > 0) {
    const presets: PresetConfig[] = [];

    // "All Picks" — top 2 stocks from every chosen sector
    const allTickers: string[] = [];
    for (const sec of userSectors) {
      allTickers.push(...(SECTOR_TICKERS[sec] || []).slice(0, 2));
    }
    const sectorTag = userSectors.length <= 2
      ? userSectors.join(' & ')
      : `${userSectors.length} Sectors`;
    presets.push({
      key: '__all__',
      label: `All Picks · ${sectorTag}`,
      tickers: allTickers.slice(0, 8),
    });

    // One button per sector — top 4 tickers for that sector
    for (const sec of userSectors) {
      presets.push({
        key: sec,
        label: sec,
        tickers: (SECTOR_TICKERS[sec] || []).slice(0, 4),
      });
    }

    return presets;
  }

  // No sector context — show generic presets
  return Object.entries(DEFAULT_PRESETS).map(([name, tickers]) => ({
    key: name,
    label: name,
    tickers,
  }));
};

const loadDraft = (): { holdings: Holding[]; startDate: string; endDate: string } => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved);
  } catch {}
  return { holdings: [{ ticker: '', shares: '', cost: '' }], startDate: '2023-01-01', endDate: '2024-12-31' };
};

const Dashboard = () => {
  const draft = loadDraft();
  const [holdings, setHoldings] = useState<Holding[]>(draft.holdings);
  const [startDate, setStartDate] = useState(draft.startDate);
  const [endDate, setEndDate] = useState(draft.endDate);
  const [selectedPreset, setSelectedPreset] = useState('');
  const navigate = useNavigate();

  const savedPortfolio = localStorage.getItem(SAVED_KEY);
  const hasSaved = !!savedPortfolio;

  // Persist draft
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ holdings, startDate, endDate }));
  }, [holdings, startDate, endDate]);

  const presets = getPresets();

  const applyPreset = (preset: PresetConfig) => {
    setSelectedPreset(preset.key);
    setHoldings(preset.tickers.map((t) => {
      const price = MOCK_STOCK_PRICES[t];
      const estimatedCost = price ? (price * 0.82).toFixed(2) : '';
      return { ticker: t, shares: '10', cost: estimatedCost };
    }));
  };

  const analyse = () => {
    localStorage.setItem(SAVED_KEY, JSON.stringify({ holdings, startDate, endDate }));
    navigate('/dashboard/results');
  };

  const updateHolding = (idx: number, field: keyof Holding, value: string) => {
    const updated = [...holdings];
    updated[idx] = { ...updated[idx], [field]: value };
    setHoldings(updated);
  };

  const filledTickers = holdings.filter((h) => h.ticker).map((h) => h.ticker);

  return (
    <AppLayout title="Portfolio Builder">
      <div className="max-w-[780px] mx-auto px-6 py-8">
        <BackButton to="/" />

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display font-extrabold text-3xl text-foreground">Portfolio Builder</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {hasSaved ? 'Your portfolio is saved. Update it or run analysis.' : 'Welcome. Now let\'s add your portfolio.'}
          </p>
        </motion.div>

        {/* Saved portfolio summary */}
        {hasSaved && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-xl p-4 mt-6">
            <span className="label-mono mb-2 block">SAVED PORTFOLIO</span>
            <div className="flex flex-wrap gap-2">
              {filledTickers.length > 0
                ? filledTickers.map((t) => (
                    <span key={t} className="font-mono text-xs bg-primary/10 text-primary px-3 py-1 rounded-full">{t}</span>
                  ))
                : <span className="text-muted-foreground text-sm">No tickers yet</span>
              }
            </div>
            <div className="flex gap-3 mt-4">
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.96 }} className="px-4 py-2 rounded-lg border border-border text-sm text-foreground hover:bg-card-elevated transition-colors">
                Update Portfolio
              </motion.button>
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.96 }} onClick={analyse} className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold">
                Analyse Portfolio <ChevronRight size={14} className="inline ml-1" />
              </motion.button>
            </div>
          </motion.div>
        )}

        {/* Holdings form */}
        <div className="space-y-5 mt-8">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass rounded-xl p-5 overflow-visible relative z-20">
            <label className="label-mono mb-3 block">ADD HOLDINGS</label>
            <div className="space-y-3">
              {holdings.map((h, i) => (
                <div key={i} className="flex gap-3 items-start">
                  <div className="flex-1">
                    <StockSearch value={h.ticker} onChange={(t) => updateHolding(i, 'ticker', t)} placeholder="Search stocks (e.g. Apple, NVDA)..." />
                  </div>
                  <input
                    placeholder="Shares"
                    value={h.shares}
                    onChange={(e) => updateHolding(i, 'shares', e.target.value)}
                    className="w-24 bg-card-elevated border border-border rounded-lg px-3 py-3 font-mono text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
                  />
                  <input
                    placeholder="Cost $"
                    value={h.cost}
                    onChange={(e) => updateHolding(i, 'cost', e.target.value)}
                    className="w-28 bg-card-elevated border border-border rounded-lg px-3 py-3 font-mono text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
                  />
                  {holdings.length > 1 && (
                    <button onClick={() => setHoldings(holdings.filter((_, j) => j !== i))} className="text-muted-foreground hover:text-signal-red mt-3">
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              ))}
              <button
                onClick={() => setHoldings([...holdings, { ticker: '', shares: '', cost: '' }])}
                className="glass rounded-lg p-2.5 w-full text-center text-muted-foreground hover:text-primary font-mono text-xs transition-colors"
              >
                <Plus size={14} className="inline mr-1" /> Add Position
              </button>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="glass rounded-xl p-5 relative z-10">
            <label className="label-mono mb-3 block">DATE RANGE</label>
            <div className="grid grid-cols-2 gap-3">
              <div className="relative">
                <Calendar size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-primary" />
                <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-full bg-card-elevated border border-border rounded-lg pl-9 pr-3 py-2.5 font-mono text-xs text-foreground focus:border-primary focus:outline-none" />
              </div>
              <div className="relative">
                <Calendar size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-primary" />
                <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-full bg-card-elevated border border-border rounded-lg pl-9 pr-3 py-2.5 font-mono text-xs text-foreground focus:border-primary focus:outline-none" />
              </div>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <label className="label-mono mb-3 block">QUICK LOAD</label>
            <div className="flex flex-wrap gap-2">
              {presets.map((p) => (
                <button key={p.key} onClick={() => applyPreset(p)} className={`px-4 py-2 rounded-full font-mono text-xs transition-all ${selectedPreset === p.key ? 'bg-primary text-primary-foreground' : 'glass text-muted-foreground hover:text-foreground'}`}>
                  {p.label}
                </button>
              ))}
            </div>
          </motion.div>

          {/* CSV import zone */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }} className="glass rounded-xl p-6 border-2 border-dashed border-border hover:border-primary/30 transition-colors text-center">
            <Upload size={32} className="text-primary mx-auto mb-4" />
            <h3 className="font-display font-bold text-foreground">Import from CSV</h3>
            <p className="text-muted-foreground text-sm mt-2">Drag and drop your broker CSV file</p>
            <p className="font-mono text-[10px] text-muted-foreground mt-3">Robinhood · Fidelity · Schwab · Webull</p>
            <button className="mt-4 px-4 py-2 rounded-lg font-mono text-xs text-primary border border-primary/30 hover:bg-primary/10 transition-colors">
              Use sample file
            </button>
          </motion.div>

          <motion.button
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            onClick={analyse}
            className="w-full py-4 rounded-xl bg-primary text-primary-foreground font-semibold text-sm"
          >
            Analyse Portfolio <ChevronRight size={14} className="inline ml-1" />
          </motion.button>
        </div>

        {/* Preview */}
        {filledTickers.length > 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass rounded-xl p-4 mt-6">
            <span className="label-mono">PREVIEW</span>
            <div className="flex flex-wrap gap-2 mt-3">
              {filledTickers.map((t) => (
                <span key={t} className="font-mono text-xs bg-primary/10 text-primary px-3 py-1 rounded-full">{t}</span>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </AppLayout>
  );
};

export default Dashboard;
