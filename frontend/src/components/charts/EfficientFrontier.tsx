import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { MOCK_EFFICIENT_FRONTIER } from '@/lib/mock-data';

interface FrontierData {
  frontier_points?: Array<{ volatility: number; return: number; type: string }>;
  current_portfolio?: { volatility: number; return: number; type: string };
  optimal_portfolio?: { volatility: number; return: number; type: string };
}

const EfficientFrontier = ({ data }: { data?: FrontierData }) => {
  // Build scatter data from API response or use mock
  let scatterData = MOCK_EFFICIENT_FRONTIER;
  if (data?.frontier_points) {
    scatterData = [
      ...data.frontier_points,
      ...(data.current_portfolio ? [data.current_portfolio] : []),
      ...(data.optimal_portfolio ? [data.optimal_portfolio] : []),
    ];
  }

  return (
    <div className="glass rounded-xl p-5">
      <span className="label-mono">EFFICIENT FRONTIER</span>
      <ResponsiveContainer width="100%" height={240} className="mt-4">
        <ScatterChart>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(48,54,61,0.5)" />
          <XAxis type="number" dataKey="volatility" name="Volatility" unit="%" tick={{ fill: '#8B949E', fontSize: 10, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
          <YAxis type="number" dataKey="return" name="Return" unit="%" tick={{ fill: '#8B949E', fontSize: 10, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={{ background: '#161B22', border: '1px solid rgba(56,189,148,0.2)', borderRadius: 8, fontFamily: 'JetBrains Mono', fontSize: 11 }} />
          <Scatter data={scatterData}>
            {scatterData.map((entry, i) => (
              <Cell
                key={i}
                fill={entry.type === 'current' ? '#F0A44F' : entry.type === 'optimal' ? '#38BDA4' : 'rgba(139,148,158,0.3)'}
                r={entry.type === 'random' ? 3 : 8}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-2 justify-center">
        <div className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-signal-amber" /><span className="font-mono text-[10px] text-muted-foreground">Your Portfolio</span></div>
        <div className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-primary" /><span className="font-mono text-[10px] text-muted-foreground">Optimal</span></div>
      </div>
    </div>
  );
};

export default EfficientFrontier;
