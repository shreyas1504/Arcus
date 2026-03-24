import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { MOCK_RISK_ATTRIBUTION } from '@/lib/mock-data';

const RiskAttribution = ({ data }: { data?: typeof MOCK_RISK_ATTRIBUTION }) => {
  const chartData = data ?? MOCK_RISK_ATTRIBUTION;
  return (
    <div className="glass rounded-xl p-5">
      <span className="label-mono">RISK CONTRIBUTION</span>
      <ResponsiveContainer width="100%" height={200} className="mt-4">
        <BarChart data={chartData} layout="vertical">
          <XAxis type="number" tick={{ fill: '#8B949E', fontSize: 10, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} />
          <YAxis type="category" dataKey="ticker" tick={{ fill: '#E6EDF3', fontSize: 11, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} width={50} />
          <Tooltip contentStyle={{ background: '#161B22', border: '1px solid rgba(56,189,148,0.2)', borderRadius: 8, fontFamily: 'JetBrains Mono', fontSize: 11 }} formatter={(v: any) => [`${v}%`, 'Risk Share']} />
          <Bar dataKey="contribution" radius={[0, 4, 4, 0]} barSize={16}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default RiskAttribution;
