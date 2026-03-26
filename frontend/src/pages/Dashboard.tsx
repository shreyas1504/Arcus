import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Upload, ChevronRight, Calendar, Trash2, Plus, CheckCircle2 } from 'lucide-react';
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

const SAMPLE_CSV = `Symbol,Quantity,Average Cost
AAPL,15,148.20
MSFT,8,320.00
NVDA,5,620.00
GOOGL,12,132.50
VOO,40,388.00
`;

const parseCSV = (text: string): Holding[] => {
  const lines = text.trim().split('\n').filter((l) => l.trim() && !l.startsWith('---'));
  if (lines.length < 2) return [];
  const sep = lines[0].includes('\t') ? '\t' : ',';
  const headers = lines[0].split(sep).map((h) => h.replace(/"/g, '').trim().toLowerCase());

  const colIdx = (keys: string[]) =>
    headers.findIndex((h) => keys.some((k) => h.includes(k)));

  const tickerIdx = colIdx(['symbol', 'ticker', 'instrument', 'stock', 'security']);
  const sharesIdx = colIdx(['quantity', 'shares', 'qty', 'units']);
  const costIdx   = colIdx(['average cost', 'avg cost', 'cost basis', 'cost per share', 'unit cost', 'purchase price', 'avg price', 'average price']);

  if (tickerIdx === -1) return [];

  const results: Holding[] = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(sep).map((c) => c.replace(/"/g, '').trim());
    const ticker = cols[tickerIdx]?.toUpperCase().replace(/[^A-Z.]/g, '');
    if (!ticker || ['TOTAL', 'CASH', 'PENDING'].includes(ticker)) continue;
    if (!/^[A-Z.]{1,6}$/.test(ticker)) continue;
    const shares = sharesIdx !== -1 ? (cols[sharesIdx] ?? '') : '';
    const cost   = costIdx   !== -1 ? (cols[costIdx]?.replace(/[$,\s]/g, '') ?? '') : '';
    results.push({ ticker, shares, cost });
  }
  return results;
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
  const [csvImported, setCsvImported] = useState(false);
  const [csvError, setCsvError] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const savedPortfolio = localStorage.getItem(SAVED_KEY);
  const hasSaved = !!savedPortfolio;

  // Persist draft
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ holdings, startDate, endDate }));
  }, [holdings, startDate, endDate]);

  const applyParsedHoldings = (text: string) => {
    setCsvError('');
    const parsed = parseCSV(text);
    if (parsed.length === 0) {
      setCsvError('Could not parse CSV. Check format: Symbol, Quantity, Average Cost columns required.');
      return;
    }
    setHoldings(parsed);
    setSelectedPreset('');
    setCsvImported(true);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => applyParsedHoldings(ev.target?.result as string);
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => applyParsedHoldings(ev.target?.result as string);
    reader.readAsText(file);
  };

  const loadSampleFile = () => applyParsedHoldings(SAMPLE_CSV);

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
      <div className="w-full max-w-[780px] mx-auto px-4 sm:px-6 py-6 sm:py-8 overflow-x-hidden">
        <BackButton to="/" />

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display font-extrabold text-2xl sm:text-3xl text-foreground">Portfolio Builder</h1>
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
                <div key={i} className="flex flex-row items-center gap-1.5">
                  <div className="flex-1 min-w-0">
                    <StockSearch value={h.ticker} onChange={(t) => updateHolding(i, 'ticker', t)} placeholder="Ticker / Name..." />
                  </div>
                  <input
                    placeholder="Qty"
                    value={h.shares}
                    onChange={(e) => updateHolding(i, 'shares', e.target.value)}
                    className="w-14 sm:w-20 bg-card-elevated border border-border rounded-lg px-2 py-2.5 font-mono text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
                  />
                  <input
                    placeholder="Cost $"
                    value={h.cost}
                    onChange={(e) => updateHolding(i, 'cost', e.target.value)}
                    className="w-16 sm:w-24 bg-card-elevated border border-border rounded-lg px-2 py-2.5 font-mono text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
                  />
                  {holdings.length > 1 && (
                    <button onClick={() => setHoldings(holdings.filter((_, j) => j !== i))} className="text-muted-foreground hover:text-signal-red flex-shrink-0">
                      <Trash2 size={13} />
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

          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="glass rounded-xl p-5 relative z-10 overflow-hidden">
            <label className="label-mono mb-3 block">DATE RANGE</label>
            <div className="flex flex-col gap-2.5">
              <div>
                <span className="font-mono text-[10px] text-muted-foreground mb-1 block">START DATE</span>
                <div className="relative w-full">
                  <Calendar size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-primary pointer-events-none z-10" />
                  <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-full max-w-full appearance-none bg-card-elevated border border-border rounded-lg pl-8 pr-3 py-2.5 font-mono text-xs text-foreground focus:border-primary focus:outline-none box-border" />
                </div>
              </div>
              <div>
                <span className="font-mono text-[10px] text-muted-foreground mb-1 block">END DATE</span>
                <div className="relative w-full">
                  <Calendar size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-primary pointer-events-none z-10" />
                  <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-full max-w-full appearance-none bg-card-elevated border border-border rounded-lg pl-8 pr-3 py-2.5 font-mono text-xs text-foreground focus:border-primary focus:outline-none box-border" />
                </div>
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
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className={`glass rounded-xl border-2 border-dashed transition-colors ${isDragOver ? 'border-primary bg-primary/5' : 'border-border'}`}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
          >
            {/* Hidden real file input */}
            <input
              ref={fileInputRef}
              id="csv-file-input"
              type="file"
              accept=".csv,.txt"
              className="sr-only"
              onChange={handleFileChange}
            />

            {/* Label covers the whole zone — triggers file picker natively on all browsers */}
            <label
              htmlFor="csv-file-input"
              className="block p-6 text-center cursor-pointer hover:bg-primary/5 rounded-xl transition-colors"
            >
              {csvImported
                ? <CheckCircle2 size={32} className="text-signal-green mx-auto mb-4" />
                : <Upload size={32} className="text-primary mx-auto mb-4" />}
              <p className="font-display font-bold text-foreground">
                {csvImported ? 'CSV Imported!' : 'Tap to upload CSV file'}
              </p>
              <p className="text-muted-foreground text-sm mt-2">
                {csvImported ? 'Holdings loaded. Tap to upload a different file.' : 'Or drag & drop your broker export'}
              </p>
              {csvError && <p className="font-mono text-[11px] text-signal-red mt-2">{csvError}</p>}
              <p className="font-mono text-[10px] text-muted-foreground mt-3">Robinhood · Fidelity · Schwab · Webull</p>
            </label>

            {/* Sample file button — outside the label so it doesn't re-trigger file picker */}
            <div className="px-6 pb-5 text-center">
              <button
                type="button"
                className="px-4 py-2 rounded-lg font-mono text-xs text-primary border border-primary/30 hover:bg-primary/10 transition-colors"
                onClick={loadSampleFile}
              >
                Load sample data instead
              </button>
            </div>
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
