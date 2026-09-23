import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Line, ComposedChart } from 'recharts';
import { MOCK_PERFORMANCE_DATA } from '@/lib/mock-data';

type TooltipPayload = { color?: string; name?: string; value?: number };

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: TooltipPayload[]; label?: string }) => {
  if (!active || !payload) return null;
  return (
    <div className="glass-panel rounded-lg px-3 py-2 border border-primary/20">
      <p className="font-mono text-[10px] text-muted-foreground mb-1">{label}</p>
      {payload.map((p, i: number) => (
        <p key={i} className="font-mono text-xs" style={{ color: p.color }}>
          {p.name}: ${p.value?.toLocaleString()}
        </p>
      ))}
    </div>
  );
};

const PerformanceChart = ({ data, benchmarkLabel = 'SPY' }: { data?: typeof MOCK_PERFORMANCE_DATA; benchmarkLabel?: string }) => {
  const chartData = data ?? MOCK_PERFORMANCE_DATA;
  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <span className="label-mono">PORTFOLIO PERFORMANCE</span>
        <div className="flex gap-1">
          {['1W', '1M', '3M', '1Y'].map((period, i) => (
            <button key={period} className={`px-2.5 py-1 rounded-full font-mono text-[10px] transition-colors ${i === 3 ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
              {period}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(48,54,61,0.5)" />
          <XAxis dataKey="date" tick={{ fill: '#8B949E', fontSize: 10, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fill: '#8B949E', fontSize: 10, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
          <Tooltip content={<CustomTooltip />} />
          <defs>
            <linearGradient id="tealGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38BDA4" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#38BDA4" stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="portfolio" stroke="#38BDA4" strokeWidth={2} fill="url(#tealGrad)" name="Portfolio" />
          <Line type="monotone" dataKey="benchmark" stroke="#4F9CF0" strokeWidth={1.5} strokeDasharray="5 5" dot={false} name={benchmarkLabel} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PerformanceChart;
