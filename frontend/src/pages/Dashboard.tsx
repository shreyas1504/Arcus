import { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Upload, ChevronRight, Calendar, Trash2, Plus, CheckCircle2, RefreshCw } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import AppLayout from '@/components/AppLayout';
import BackButton from '@/components/BackButton';
import StockSearch from '@/components/StockSearch';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { MOCK_STOCK_PRICES, TICKER_RISK_DB } from '@/lib/mock-data';
import { getStockPrice } from '@/lib/api';

const STORAGE_KEY = 'arcus-portfolio-draft';
const SAVED_KEY = 'arcus-portfolio';

interface Holding {
  ticker: string;
  shares: string;
  cost: string;
}

const SECTOR_TICKERS: Record<string, string[]> = {
  'Technology': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'CRM', 'ADBE'],
  'Healthcare': ['UNH', 'JNJ', 'PFE', 'ABBV', 'TMO', 'MRK'],
  'Energy':     ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC'],
  'Financials': ['JPM', 'V', 'MA', 'BAC', 'GS', 'BLK'],
  'Consumer':   ['AMZN', 'TSLA', 'HD', 'NKE', 'SBUX', 'MCD'],
  'Real Estate':['AMT', 'PLD', 'CCI', 'SPG', 'O', 'WELL'],
  'Utilities':  ['NEE', 'DUK', 'SO', 'D', 'AEP', 'SRE'],
};

const DEFAULT_PRESETS: Record<string, string[]> = {
  'FAANG':      ['META', 'AAPL', 'AMZN', 'NFLX', 'GOOGL'],
  'Tech Heavy': ['NVDA', 'MSFT', 'CRM', 'ADBE', 'AMD'],
  'Balanced':   ['AAPL', 'JNJ', 'JPM', 'XOM', 'VOO'],
  'S&P 500':   ['VOO', 'SPY', 'VTI', 'QQQ'],
};

interface PresetConfig { key: string; label: string; tickers: string[] }


const getPresets = (): PresetConfig[] => {
  const dna = (() => { try { return JSON.parse(localStorage.getItem('arcus-investor-dna') || 'null'); } catch { return null; } })();
  const userSectors: string[] = dna?.sectors || [];
  const riskTolerance: string = dna?.risk_tolerance || 'Moderate';

  if (userSectors.length > 0) {
    const presets: PresetConfig[] = [];

    // Sort sectors' tickers by risk profile
    const isConservative = ['Conservative', 'Moderate'].includes(riskTolerance);

    const sortedSectorTickers = (tickers: string[]): string[] => {
      return [...tickers].sort((a, b) => {
        const aRisk = TICKER_RISK_DB[a];
        const bRisk = TICKER_RISK_DB[b];
        if (!aRisk || !bRisk) return 0;
        // Conservative: low beta first; Aggressive: high beta first
        return isConservative ? aRisk.beta - bRisk.beta : bRisk.beta - aRisk.beta;
      });
    };

    // "All Picks" — take 3 per sector (up from 2), max 15 so no sector gets cut
    const allTickers: string[] = [];
    const perSector = Math.max(2, Math.ceil(12 / userSectors.length));
    for (const sec of userSectors) {
      const sorted = sortedSectorTickers(SECTOR_TICKERS[sec] || []);
      allTickers.push(...sorted.slice(0, perSector));
    }
    const sectorTag = userSectors.length <= 2 ? userSectors.join(' & ') : `${userSectors.length} Sectors`;
    presets.push({ key: '__all__', label: `All Picks · ${sectorTag}`, tickers: allTickers });

    // Individual sector presets — show ALL 6 stocks (not just 4)
    for (const sec of userSectors) {
      const sorted = sortedSectorTickers(SECTOR_TICKERS[sec] || []);
      presets.push({ key: sec, label: sec, tickers: sorted });
    }
    return presets;
  }
  return Object.entries(DEFAULT_PRESETS).map(([name, tickers]) => ({ key: name, label: name, tickers }));
};

const SAMPLE_CSV = `Symbol,Quantity,Average Cost
AAPL,15,148.20
MSFT,8,320.00
NVDA,5,620.00
GOOGL,12,132.50
VOO,40,388.00
`;

const parseCSV = (text: string): Holding[] => {
  const lines = text.trim().split('\n').filter(l => l.trim() && !l.startsWith('---'));
  if (lines.length < 2) return [];
  const sep = lines[0].includes('\t') ? '\t' : ',';
  const headers = lines[0].split(sep).map(h => h.replace(/"/g, '').trim().toLowerCase());
  const colIdx = (keys: string[]) => headers.findIndex(h => keys.some(k => h.includes(k)));
  const tickerIdx = colIdx(['symbol', 'ticker', 'instrument', 'stock', 'security']);
  const sharesIdx = colIdx(['quantity', 'shares', 'qty', 'units']);
  const costIdx   = colIdx(['average cost', 'avg cost', 'cost basis', 'cost per share', 'unit cost', 'purchase price', 'avg price', 'average price']);
  if (tickerIdx === -1) return [];
  const results: Holding[] = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(sep).map(c => c.replace(/"/g, '').trim());
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
  } catch { /* empty */ }
  return { holdings: [{ ticker: '', shares: '', cost: '' }], startDate: '2023-01-01', endDate: '2024-12-31' };
};

// ── Price display for individual holdings ────────────────────────────────
const HoldingPrice = ({ ticker, shares, onPriceFetched }: { ticker: string; shares: string; onPriceFetched?: (t: string, p: number) => void }) => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['price', ticker],
    queryFn: () => getStockPrice(ticker),
    enabled: !!ticker && ticker.length >= 1,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const price = data?.price || MOCK_STOCK_PRICES[ticker.toUpperCase()] || 0;
  const changePct = data?.changePercent || 0;
  const qty = parseFloat(shares) || 0;
  const total = qty * price;

  useEffect(() => {
    if (price > 0 && onPriceFetched) {
      onPriceFetched(ticker.toUpperCase(), price);
    }
  }, [price, ticker, onPriceFetched]);

  if (!ticker) return null;

  return (
    <div className="flex flex-col gap-0.5 mt-0.5">
      <div className="flex items-center gap-2">
        {isLoading ? (
          <Skeleton className="h-4 w-16" />
        ) : (
          <>
            <span className="font-mono text-[10px] text-foreground">${price.toFixed(2)}</span>
            {(changePct !== 0 || data) && (
              <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${changePct >= 0 ? 'bg-signal-green/10 text-signal-green' : 'bg-signal-red/10 text-signal-red'}`}>
                {changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%
              </span>
            )}
          </>
        )}
      </div>
      {qty > 0 && price > 0 && (
        <span className="font-mono text-[10px] text-muted-foreground/60">
          {qty} shares × ${price.toFixed(2)} = ${total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      )}
    </div>
  );
};

// ── Dashboard ────────────────────────────────────────────────────────────
const Dashboard = () => {
  const draft = loadDraft();
  const [holdings, setHoldings] = useState<Holding[]>(draft.holdings);
  const [startDate, setStartDate] = useState(draft.startDate);
  const [endDate, setEndDate] = useState(draft.endDate);
  const [selectedPreset, setSelectedPreset] = useState('');
  const [csvImported, setCsvImported] = useState(false);
  const [csvError, setCsvError] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);
  const [livePrices, setLivePrices] = useState<Record<string, number>>({});
  const handlePriceFetched = useCallback((t: string, p: number) => {
    setLivePrices(prev => prev[t] === p ? prev : { ...prev, [t]: p });
  }, []);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  // Pre-populate holdings if navigated from Apply Strategy in Sandbox
  useEffect(() => {
    const state = location.state as { weights?: Record<string, number>; tickers?: string[] } | null;
    if (state?.weights && state.tickers?.length) {
      // Load tickers only — leave shares & cost for the user to fill in
      setHoldings(state.tickers.map(t => ({
        ticker: t,
        shares: '',
        cost: '',
      })));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const savedPortfolio = localStorage.getItem(SAVED_KEY);
  const hasSaved = !!savedPortfolio;

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
    // Load tickers only — leave shares & cost blank for the user to fill in
    const newHoldings = preset.tickers.map(t => ({
      ticker: t.toUpperCase(),
      shares: '',
      cost: '',
    }));
    setHoldings(newHoldings);
  };

  const updateHolding = (idx: number, field: keyof Holding, value: string) => {
    if (field === 'shares' && value === '0') {
      toast.error('Minimum 1 needed', {
        className: 'border-signal-red bg-card-elevated text-signal-red font-mono',
        duration: 3000,
      });
      value = '1';
    }

    const updated = [...holdings];
    updated[idx] = { ...updated[idx], [field]: value };
    setHoldings(updated);
  };

  const filledTickers = holdings.filter(h => h.ticker).map(h => h.ticker);
  const activeHoldings = holdings.filter((holding) => holding.ticker.trim());
  const holdingsMissingShares = activeHoldings.filter((holding) => {
    const shares = parseFloat(holding.shares);
    return !Number.isFinite(shares) || shares <= 0;
  });
  const hasInvalidDateRange = !!startDate && !!endDate && startDate > endDate;
  const canAnalyzePortfolio = activeHoldings.length > 0 && holdingsMissingShares.length === 0 && !hasInvalidDateRange;
  const analysisRequirementText = hasInvalidDateRange
    ? 'Choose a valid date range.'
    : activeHoldings.length === 0
      ? 'Add at least one holding to run analysis.'
      : holdingsMissingShares.length > 0
        ? 'Enter shares greater than 0 for every selected holding.'
        : '';

  // Compute total portfolio value
  const portfolioTotal = holdings
    .filter(h => h.ticker && h.shares)
    .reduce((sum, h) => {
      const upperTicker = h.ticker.toUpperCase();
      const price = livePrices[upperTicker] || MOCK_STOCK_PRICES[upperTicker] || 0;
      return sum + (parseFloat(h.shares) || 0) * price;
    }, 0);

  const totalCostBasis = holdings
    .filter(h => h.ticker && h.shares && h.cost)
    .reduce((sum, h) => sum + (parseFloat(h.shares) || 0) * (parseFloat(h.cost) || 0), 0);

  const totalPnL = portfolioTotal - totalCostBasis;
  const totalPnLPct = totalCostBasis > 0 ? (totalPnL / totalCostBasis) * 100 : 0;
  const pnlPositive = totalPnL >= 0;

  const refreshPrices = () => {
    queryClient.invalidateQueries({ queryKey: ['price'] });
  };

  const analyse = () => {
    if (!canAnalyzePortfolio) {
      toast.error(analysisRequirementText || 'Complete all required holdings before analysis.', {
        className: 'border-signal-red bg-card-elevated text-signal-red font-mono',
        duration: 3000,
      });
      return;
    }

    localStorage.setItem(SAVED_KEY, JSON.stringify({ holdings, startDate, endDate, livePrices }));
    navigate('/dashboard/results');
  };

  return (
    <AppLayout title="Portfolio Builder">
      <div className="w-full max-w-[780px] mx-auto px-4 sm:px-6 py-6 sm:py-8 overflow-x-hidden">
        <BackButton to="/" />

        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display font-extrabold text-2xl sm:text-3xl text-foreground">Portfolio Builder</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {hasSaved ? 'Your portfolio is saved. Update it or run analysis.' : "Welcome. Now let's add your portfolio."}
          </p>
        </motion.div>

        {/* Saved portfolio summary */}
        {hasSaved && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-xl p-4 mt-6">
            <span className="label-mono mb-2 block">SAVED PORTFOLIO</span>
            <div className="flex flex-wrap gap-2">
              {filledTickers.length > 0
                ? filledTickers.map(t => (
                    <span key={t} className="font-mono text-xs bg-primary/10 text-primary px-3 py-1 rounded-full">{t}</span>
                  ))
                : <span className="text-muted-foreground text-sm">No tickers yet</span>
              }
            </div>
            <div className="flex gap-3 mt-4">
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.96 }} onClick={() => window.scrollTo({ top: 300, behavior: 'smooth' })} className="px-4 py-2 rounded-lg border border-border text-sm text-foreground hover:bg-card-elevated transition-colors">
                Update Portfolio
              </motion.button>
              <motion.button
                whileHover={canAnalyzePortfolio ? { scale: 1.02 } : undefined}
                whileTap={canAnalyzePortfolio ? { scale: 0.96 } : undefined}
                onClick={analyse}
                disabled={!canAnalyzePortfolio}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                  canAnalyzePortfolio
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-primary/30 text-primary-foreground/60 cursor-not-allowed'
                }`}
              >
                Analyse Portfolio <ChevronRight size={14} className="inline ml-1" />
              </motion.button>
            </div>
            {!canAnalyzePortfolio && (
              <p className="mt-3 font-mono text-[10px] text-signal-amber">{analysisRequirementText}</p>
            )}
          </motion.div>
        )}

        {/* Quick Load — above holdings so user picks sector first */}
        <div className="space-y-5 mt-8">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <label className="label-mono mb-3 block">QUICK LOAD</label>
            <p className="text-muted-foreground text-xs mb-3">Select a sector to load its stocks, then fill in your quantities and cost.</p>
            <div className="flex flex-wrap gap-2">
              {presets.map(p => (
                <button key={p.key} onClick={() => applyPreset(p)} className={`px-4 py-2 rounded-full font-mono text-xs transition-all ${selectedPreset === p.key ? 'bg-primary text-primary-foreground' : 'glass text-muted-foreground hover:text-foreground'}`}>
                  {p.label}
                </button>
              ))}
            </div>
          </motion.div>

          {/* Holdings form */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="glass rounded-xl p-5 overflow-visible relative z-20">
            <label className="label-mono mb-1 block">ADD HOLDINGS</label>
            <p className="text-muted-foreground text-[11px] mb-4">Enter the price you paid per share as <span className="text-primary">Buy Price</span>.</p>
            {/* Column headers */}
            <div className="flex flex-row items-center gap-1.5 mb-2">
              <span className="flex-1 min-w-0 font-mono text-[10px] text-muted-foreground/70 uppercase tracking-wider pl-10">Stock</span>
              <span className="w-14 sm:w-20 font-mono text-[10px] text-muted-foreground/70 uppercase tracking-wider text-center">Shares</span>
              <span className="w-16 sm:w-24 font-mono text-[10px] text-muted-foreground/70 uppercase tracking-wider text-center">Buy Price</span>
              <span className="w-[13px] flex-shrink-0"></span>
            </div>
            <div className="space-y-3">
              {holdings.map((h, i) => (
                <div key={i}>
                  <div className="flex flex-row items-center gap-1.5">
                    <div className="flex-1 min-w-0">
                      <StockSearch value={h.ticker} onChange={t => updateHolding(i, 'ticker', t)} placeholder="Ticker / Name..." />
                    </div>
                    <input
                      type="number"
                      min="1"
                      placeholder="0"
                      value={h.shares}
                      onChange={e => updateHolding(i, 'shares', e.target.value)}
                      className="w-14 sm:w-20 bg-card-elevated border border-border rounded-lg px-2 py-2.5 font-mono text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
                    />
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                      value={h.cost}
                      onChange={e => updateHolding(i, 'cost', e.target.value)}
                      className="w-16 sm:w-24 bg-card-elevated border border-border rounded-lg px-2 py-2.5 font-mono text-xs text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none"
                    />
                    {holdings.length > 1 && (
                      <button onClick={() => setHoldings(holdings.filter((_, j) => j !== i))} className="text-muted-foreground hover:text-signal-red flex-shrink-0">
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                  {/* Live price + position value */}
                  {h.ticker && (
                    <div className="ml-0 sm:ml-2 mt-1">
                      <HoldingPrice 
                        ticker={h.ticker} 
                        shares={h.shares} 
                        onPriceFetched={handlePriceFetched}
                      />
                    </div>
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

          {/* Total Portfolio Value */}
          {filledTickers.length > 0 && portfolioTotal > 0 && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }} className="glass rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="label-mono">PORTFOLIO VALUE</span>
                <button onClick={refreshPrices} className="text-muted-foreground hover:text-primary transition-colors p-1" title="Refresh prices">
                  <RefreshCw size={13} />
                </button>
              </div>
              <div className="flex flex-wrap items-end gap-4">
                <div>
                  <div className="font-mono text-2xl font-bold text-foreground">${portfolioTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                  <span className="font-mono text-[10px] text-muted-foreground">Current Market Value</span>
                </div>
                {totalCostBasis > 0 && (
                  <div>
                    <div className={`font-mono text-lg font-bold ${pnlPositive ? 'text-signal-green' : 'text-signal-red'}`}>
                      {pnlPositive ? '+' : ''}${totalPnL.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      <span className="text-sm ml-2">({pnlPositive ? '+' : ''}{totalPnLPct.toFixed(1)}%)</span>
                    </div>
                    <span className="font-mono text-[10px] text-muted-foreground">Total P&L</span>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.22 }} className="glass rounded-xl p-5 relative z-10 overflow-hidden">
            <label className="label-mono mb-3 block">DATE RANGE</label>
            <div className="flex flex-col gap-2.5">
              <div>
                <span className="font-mono text-[10px] text-muted-foreground mb-1 block">START DATE</span>
                <div className="relative w-full">
                  <Calendar size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-primary pointer-events-none z-10" />
                  <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-full max-w-full appearance-none bg-card-elevated border border-border rounded-lg pl-8 pr-3 py-2.5 font-mono text-xs text-foreground focus:border-primary focus:outline-none box-border" />
                </div>
              </div>
              <div>
                <span className="font-mono text-[10px] text-muted-foreground mb-1 block">END DATE</span>
                <div className="relative w-full">
                  <Calendar size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-primary pointer-events-none z-10" />
                  <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-full max-w-full appearance-none bg-card-elevated border border-border rounded-lg pl-8 pr-3 py-2.5 font-mono text-xs text-foreground focus:border-primary focus:outline-none box-border" />
                </div>
              </div>
            </div>
          </motion.div>

          {/* CSV import zone */}
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }} className={`glass rounded-xl border-2 border-dashed transition-colors ${isDragOver ? 'border-primary bg-primary/5' : 'border-border'}`} onDragOver={e => { e.preventDefault(); setIsDragOver(true); }} onDragLeave={() => setIsDragOver(false)} onDrop={handleDrop}>
            <input ref={fileInputRef} id="csv-file-input" type="file" accept=".csv,.txt" className="sr-only" onChange={handleFileChange} />
            <button type="button" className="block w-full p-6 text-center cursor-pointer hover:bg-primary/5 rounded-xl transition-colors" onClick={() => { setCsvError(''); setCsvImported(false); setTimeout(() => fileInputRef.current?.click(), 50); }}>
              {csvImported ? <CheckCircle2 size={32} className="text-signal-green mx-auto mb-4" /> : <Upload size={32} className="text-primary mx-auto mb-4" />}
              <p className="font-display font-bold text-foreground">{csvImported ? 'CSV Imported! Tap to change' : 'Tap to upload CSV file'}</p>
              <p className="text-muted-foreground text-sm mt-2">{csvImported ? 'Holdings loaded from your file.' : 'Or drag & drop your broker export'}</p>
              {csvError && <p className="font-mono text-[11px] text-signal-red mt-2">{csvError}</p>}
              <p className="font-mono text-[10px] text-muted-foreground mt-3">Robinhood · Fidelity · Schwab · Webull</p>
            </button>
            <div className="px-6 pb-5 text-center">
              <button type="button" className="px-4 py-2 rounded-lg font-mono text-xs text-primary border border-primary/30 hover:bg-primary/10 transition-colors" onClick={loadSampleFile}>
                Load sample data instead
              </button>
            </div>
          </motion.div>

          <motion.button
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            whileHover={canAnalyzePortfolio ? { scale: 1.01 } : undefined}
            whileTap={canAnalyzePortfolio ? { scale: 0.98 } : undefined}
            onClick={analyse}
            disabled={!canAnalyzePortfolio}
            className={`w-full py-4 rounded-xl font-semibold text-sm transition-colors ${
              canAnalyzePortfolio
                ? 'bg-primary text-primary-foreground'
                : 'bg-primary/30 text-primary-foreground/60 cursor-not-allowed'
            }`}
          >
            Analyse Portfolio <ChevronRight size={14} className="inline ml-1" />
          </motion.button>
          {!canAnalyzePortfolio && (
            <p className="text-center font-mono text-[10px] text-signal-amber -mt-1">{analysisRequirementText}</p>
          )}
        </div>

        {/* Preview */}
        {filledTickers.length > 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass rounded-xl p-4 mt-6">
            <span className="label-mono">PREVIEW</span>
            <div className="flex flex-wrap gap-2 mt-3">
              {filledTickers.map(t => (
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
