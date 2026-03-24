import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, SearchX } from 'lucide-react';

interface Stock {
  ticker: string;
  name: string;
  aliases: string[];
  price: number;
  change: string;
  positive: boolean;
}

const STOCK_DB: Stock[] = [
  { ticker: 'AAPL', name: 'Apple Inc.', aliases: ['apple', 'iphone maker'], price: 182.63, change: '+1.24%', positive: true },
  { ticker: 'MSFT', name: 'Microsoft Corporation', aliases: ['microsoft', 'windows', 'azure'], price: 378.91, change: '+0.87%', positive: true },
  { ticker: 'GOOGL', name: 'Alphabet Inc.', aliases: ['google', 'alphabet', 'youtube'], price: 165.22, change: '+1.12%', positive: true },
  { ticker: 'AMZN', name: 'Amazon.com Inc.', aliases: ['amazon', 'aws', 'prime'], price: 178.25, change: '+0.94%', positive: true },
  { ticker: 'NVDA', name: 'NVIDIA Corporation', aliases: ['nvidia', 'jensen huang'], price: 875.40, change: '+2.31%', positive: true },
  { ticker: 'META', name: 'Meta Platforms Inc.', aliases: ['meta', 'facebook', 'instagram', 'zuckerberg'], price: 485.39, change: '+1.56%', positive: true },
  { ticker: 'TSLA', name: 'Tesla Inc.', aliases: ['tesla', 'elon musk', 'electric car'], price: 248.42, change: '-0.73%', positive: false },
  { ticker: 'BRK.B', name: 'Berkshire Hathaway', aliases: ['berkshire', 'warren buffett'], price: 412.30, change: '+0.12%', positive: true },
  { ticker: 'JPM', name: 'JPMorgan Chase', aliases: ['jpmorgan', 'chase bank'], price: 198.45, change: '+0.45%', positive: true },
  { ticker: 'JNJ', name: 'Johnson & Johnson', aliases: ['johnson', 'jnj', 'pharma'], price: 156.78, change: '-0.21%', positive: false },
  { ticker: 'V', name: 'Visa Inc.', aliases: ['visa', 'payments'], price: 278.90, change: '+0.33%', positive: true },
  { ticker: 'UNH', name: 'UnitedHealth Group', aliases: ['unitedhealth', 'insurance'], price: 492.15, change: '-0.42%', positive: false },
  { ticker: 'XOM', name: 'Exxon Mobil', aliases: ['exxon', 'mobil', 'oil'], price: 108.45, change: '+0.67%', positive: true },
  { ticker: 'WMT', name: 'Walmart Inc.', aliases: ['walmart', 'retail'], price: 165.34, change: '+0.56%', positive: true },
  { ticker: 'MA', name: 'Mastercard Inc.', aliases: ['mastercard', 'payments'], price: 458.90, change: '+0.41%', positive: true },
  { ticker: 'PG', name: 'Procter & Gamble', aliases: ['procter', 'gamble', 'consumer'], price: 158.90, change: '+0.18%', positive: true },
  { ticker: 'LLY', name: 'Eli Lilly', aliases: ['lilly', 'ozempic', 'weight loss drug'], price: 782.30, change: '+1.45%', positive: true },
  { ticker: 'HD', name: 'Home Depot', aliases: ['home depot', 'hardware store'], price: 345.67, change: '+0.78%', positive: true },
  { ticker: 'CVX', name: 'Chevron Corporation', aliases: ['chevron', 'oil', 'energy'], price: 155.20, change: '+0.34%', positive: true },
  { ticker: 'MRK', name: 'Merck & Co.', aliases: ['merck', 'pharma'], price: 125.40, change: '-0.15%', positive: false },
  { ticker: 'ABBV', name: 'AbbVie Inc.', aliases: ['abbvie', 'pharma', 'humira'], price: 168.90, change: '+0.52%', positive: true },
  { ticker: 'COST', name: 'Costco Wholesale', aliases: ['costco', 'wholesale'], price: 725.80, change: '+0.34%', positive: true },
  { ticker: 'KO', name: 'Coca-Cola Company', aliases: ['coca cola', 'coke'], price: 60.45, change: '+0.22%', positive: true },
  { ticker: 'PEP', name: 'PepsiCo Inc.', aliases: ['pepsi', 'pepsico', 'frito'], price: 172.30, change: '+0.18%', positive: true },
  { ticker: 'AMD', name: 'Advanced Micro Devices', aliases: ['amd', 'ryzen', 'radeon'], price: 165.23, change: '+1.87%', positive: true },
  { ticker: 'INTC', name: 'Intel Corporation', aliases: ['intel', 'processor'], price: 31.45, change: '-1.23%', positive: false },
  { ticker: 'NFLX', name: 'Netflix Inc.', aliases: ['netflix', 'streaming'], price: 628.90, change: '+0.92%', positive: true },
  { ticker: 'DIS', name: 'Walt Disney Company', aliases: ['disney', 'disney+', 'theme park'], price: 98.45, change: '+1.23%', positive: true },
  { ticker: 'ADBE', name: 'Adobe Inc.', aliases: ['adobe', 'photoshop', 'creative cloud'], price: 478.60, change: '+0.56%', positive: true },
  { ticker: 'CRM', name: 'Salesforce Inc.', aliases: ['salesforce', 'crm'], price: 265.40, change: '+0.64%', positive: true },
  { ticker: 'PYPL', name: 'PayPal Holdings', aliases: ['paypal', 'payments', 'venmo'], price: 62.30, change: '-0.87%', positive: false },
  { ticker: 'UBER', name: 'Uber Technologies', aliases: ['uber', 'rideshare'], price: 72.45, change: '+1.12%', positive: true },
  { ticker: 'SPOT', name: 'Spotify Technology', aliases: ['spotify', 'music streaming'], price: 285.60, change: '+0.78%', positive: true },
  { ticker: 'SHOP', name: 'Shopify Inc.', aliases: ['shopify', 'ecommerce'], price: 78.90, change: '+1.34%', positive: true },
  { ticker: 'SQ', name: 'Block Inc.', aliases: ['block', 'square', 'cash app'], price: 68.20, change: '-0.45%', positive: false },
  { ticker: 'PLTR', name: 'Palantir Technologies', aliases: ['palantir', 'ai data'], price: 22.80, change: '+2.45%', positive: true },
  { ticker: 'SNOW', name: 'Snowflake Inc.', aliases: ['snowflake', 'cloud data'], price: 162.30, change: '-0.67%', positive: false },
  { ticker: 'COIN', name: 'Coinbase Global', aliases: ['coinbase', 'crypto exchange'], price: 225.40, change: '+3.12%', positive: true },
  { ticker: 'SPY', name: 'SPDR S&P 500 ETF', aliases: ['sp500', 's&p 500', 'index fund', 'spy etf'], price: 512.40, change: '+0.38%', positive: true },
  { ticker: 'QQQ', name: 'Invesco QQQ ETF', aliases: ['qqq', 'nasdaq etf', 'tech etf'], price: 438.92, change: '+0.67%', positive: true },
  { ticker: 'VOO', name: 'Vanguard S&P 500 ETF', aliases: ['vanguard', 'voo', 'index'], price: 465.18, change: '+0.42%', positive: true },
  { ticker: 'VTI', name: 'Vanguard Total Stock Market ETF', aliases: ['vti', 'total market'], price: 245.60, change: '+0.35%', positive: true },
  { ticker: 'GLD', name: 'SPDR Gold Trust', aliases: ['gold', 'gld', 'gold etf'], price: 218.90, change: '+0.89%', positive: true },
  { ticker: 'TLT', name: 'iShares 20+ Year Treasury Bond', aliases: ['bonds', 'treasury', 'tlt'], price: 92.30, change: '-0.23%', positive: false },
  { ticker: 'ARKK', name: 'ARK Innovation ETF', aliases: ['ark', 'cathie wood', 'innovation etf'], price: 48.90, change: '+1.67%', positive: true },
  { ticker: 'BTC-USD', name: 'Bitcoin USD', aliases: ['bitcoin', 'btc', 'crypto'], price: 67420.00, change: '+2.34%', positive: true },
  { ticker: 'ETH-USD', name: 'Ethereum USD', aliases: ['ethereum', 'eth', 'crypto'], price: 3520.00, change: '+1.89%', positive: true },
  { ticker: 'BA', name: 'The Boeing Company', aliases: ['boeing'], price: 215.60, change: '-0.56%', positive: false },
  { ticker: 'CAT', name: 'Caterpillar Inc.', aliases: ['caterpillar', 'construction'], price: 328.90, change: '+0.45%', positive: true },
  { ticker: 'GS', name: 'Goldman Sachs', aliases: ['goldman', 'investment bank'], price: 425.60, change: '+0.78%', positive: true },
  { ticker: 'MS', name: 'Morgan Stanley', aliases: ['morgan stanley', 'bank'], price: 92.30, change: '+0.34%', positive: true },
  { ticker: 'IBM', name: 'IBM Corporation', aliases: ['ibm', 'international business machines'], price: 185.40, change: '+0.23%', positive: true },
  { ticker: 'ORCL', name: 'Oracle Corporation', aliases: ['oracle', 'database'], price: 125.60, change: '+0.67%', positive: true },
  { ticker: 'T', name: 'AT&T Inc.', aliases: ['at&t', 'att', 'telecom'], price: 17.20, change: '-0.12%', positive: false },
  { ticker: 'VZ', name: 'Verizon Communications', aliases: ['verizon', 'telecom'], price: 38.90, change: '+0.15%', positive: true },
  { ticker: 'NKE', name: 'Nike Inc.', aliases: ['nike', 'shoes', 'sportswear'], price: 98.45, change: '-0.34%', positive: false },
  { ticker: 'SBUX', name: 'Starbucks Corporation', aliases: ['starbucks', 'coffee'], price: 92.30, change: '+0.45%', positive: true },
  { ticker: 'MCD', name: "McDonald's Corporation", aliases: ['mcdonalds', 'fast food'], price: 285.60, change: '+0.23%', positive: true },
  { ticker: 'PFE', name: 'Pfizer Inc.', aliases: ['pfizer', 'vaccine', 'pharma'], price: 28.90, change: '-0.67%', positive: false },
  { ticker: 'TMO', name: 'Thermo Fisher Scientific', aliases: ['thermo fisher', 'lab equipment'], price: 565.40, change: '+0.45%', positive: true },
];

interface StockSearchProps {
  value: string;
  onChange: (ticker: string) => void;
  placeholder?: string;
}

const StockSearch = ({ value, onChange, placeholder = 'Search stocks (e.g. Apple, NVDA)...' }: StockSearchProps) => {
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  const results = query.length > 0
    ? STOCK_DB.filter((s) => {
        const q = query.toLowerCase();
        return s.ticker.toLowerCase().includes(q) || s.name.toLowerCase().includes(q) || s.aliases.some((a) => a.includes(q));
      }).slice(0, 6)
    : [];

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const select = (ticker: string) => {
    setQuery(ticker);
    onChange(ticker);
    setOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx((i) => Math.min(i + 1, results.length - 1)); }
    if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIdx((i) => Math.max(i - 1, 0)); }
    if (e.key === 'Enter' && results[selectedIdx]) { select(results[selectedIdx].ticker); }
    if (e.key === 'Escape') setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-primary" />
        <input
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); setSelectedIdx(0); }}
          onFocus={() => query.length > 0 && setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full bg-card-elevated border border-border rounded-lg pl-10 pr-4 py-3 font-mono text-sm text-foreground placeholder:text-muted-foreground/50 focus:border-primary focus:outline-none transition-colors"
        />
      </div>
      <AnimatePresence>
        {open && query.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="absolute top-full mt-1 w-full rounded-[10px] border z-50 overflow-hidden"
            style={{ background: '#161B22', borderColor: 'rgba(56,189,148,0.25)', boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}
          >
            {results.length === 0 ? (
              <div className="flex items-center gap-2 px-4 py-3 text-muted-foreground">
                <SearchX size={16} className="text-primary" />
                <span className="text-sm">No results for '{query}'</span>
              </div>
            ) : (
              results.map((stock, i) => (
                <button
                  key={stock.ticker}
                  onClick={() => select(stock.ticker)}
                  className="w-full flex items-center justify-between h-11 px-3 transition-colors"
                  style={{
                    background: i === selectedIdx ? 'rgba(56,189,148,0.12)' : 'transparent',
                    borderLeft: i === selectedIdx ? '2px solid hsl(var(--primary))' : '2px solid transparent',
                  }}
                  onMouseEnter={() => setSelectedIdx(i)}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-[11px] text-primary px-2 py-0.5 rounded" style={{ background: 'rgba(56,189,148,0.15)' }}>{stock.ticker}</span>
                    <span className="text-[13px] text-foreground">{stock.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-secondary">${stock.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    <span className={`font-mono text-[11px] ${stock.positive ? 'text-signal-green' : 'text-signal-red'}`}>{stock.change}</span>
                  </div>
                </button>
              ))
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default StockSearch;
