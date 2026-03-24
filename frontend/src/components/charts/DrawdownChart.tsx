import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { MOCK_DRAWDOWN } from '@/lib/mock-data';

const DrawdownChart = ({ data }: { data?: typeof MOCK_DRAWDOWN }) => {
  const chartData = data ?? MOCK_DRAWDOWN;
  return (
    <div className="glass rounded-xl p-5">
      <span className="label-mono">DRAWDOWN</span>
      <ResponsiveContainer width="100%" height={200} className="mt-4">
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(48,54,61,0.5)" />
          <XAxis dataKey="date" tick={{ fill: '#8B949E', fontSize: 10, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fill: '#8B949E', fontSize: 10, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
          <Tooltip formatter={(v: any) => [`${(Number(v) * 100).toFixed(1)}%`, 'Drawdown']} contentStyle={{ background: '#161B22', border: '1px solid rgba(56,189,148,0.2)', borderRadius: 8, fontFamily: 'JetBrains Mono', fontSize: 11 }} />
          <ReferenceLine y={0} stroke="rgba(48,54,61,0.8)" />
          <defs>
            <linearGradient id="redGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#F0514F" stopOpacity={0.2} />
              <stop offset="100%" stopColor="#F0514F" stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="drawdown" stroke="#F0514F" strokeWidth={2} fill="url(#redGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DrawdownChart;
