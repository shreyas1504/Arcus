import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { MOCK_MONTE_CARLO } from '@/lib/mock-data';

interface MonteCarloChartProps {
  data?: typeof MOCK_MONTE_CARLO;
  targetReturn?: number;  // decimal e.g. 0.10
  initialValue?: number;  // e.g. 100000
  vaultMode?: boolean;
}

const MonteCarloChart = ({ data, targetReturn, initialValue = 100000, vaultMode = false }: MonteCarloChartProps) => {
  const chartData = data ?? MOCK_MONTE_CARLO;
  const targetValue = targetReturn !== undefined ? initialValue * (1 + targetReturn) : undefined;

  return (
    <div className="glass rounded-xl p-5">
      <span className="label-mono">MONTE CARLO SIMULATION — 1,000 PATHS</span>
      <ResponsiveContainer width="100%" height={240} className="mt-4">
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(48,54,61,0.5)" />
          <XAxis dataKey="month" tick={{ fill: '#8B949E', fontSize: 10, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
          <YAxis
            tick={{ fill: '#8B949E', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => vaultMode ? '***' : `$${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            contentStyle={{ background: '#161B22', border: '1px solid rgba(56,189,148,0.2)', borderRadius: 8, fontFamily: 'JetBrains Mono', fontSize: 11 }}
            formatter={(value: number) => vaultMode ? ['$***', ''] : [`$${value.toLocaleString()}`, '']}
          />
          <defs>
            <linearGradient id="mcGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38BDA4" stopOpacity={0.1} />
              <stop offset="100%" stopColor="#38BDA4" stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="p90" stackId="1" stroke="none" fill="rgba(56,189,148,0.05)" name="90th %ile" />
          <Area type="monotone" dataKey="p75" stackId="2" stroke="none" fill="rgba(56,189,148,0.08)" name="75th %ile" />
          <Area type="monotone" dataKey="p50" stroke="#38BDA4" strokeWidth={2} fill="url(#mcGrad)" name="Median" />
          <Area type="monotone" dataKey="p25" stackId="3" stroke="none" fill="rgba(78,204,163,0.06)" name="25th %ile" />
          <Area type="monotone" dataKey="p10" stackId="4" stroke="none" fill="rgba(240,81,79,0.05)" name="10th %ile" />
          {targetValue !== undefined && (
            <ReferenceLine
              y={targetValue}
              stroke="#F0A44F"
              strokeDasharray="4 3"
              strokeWidth={1.5}
              label={{
                value: `Target ${((targetReturn ?? 0) * 100).toFixed(0)}%`,
                fill: '#F0A44F',
                fontSize: 9,
                fontFamily: 'JetBrains Mono',
                position: 'insideTopRight',
              }}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default MonteCarloChart;
