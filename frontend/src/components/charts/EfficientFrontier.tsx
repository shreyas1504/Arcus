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

  const getPointStyle = (type: string) => {
    if (type === 'current') {
      return { fill: '#FFAD4D', stroke: '#FFF1D8', strokeWidth: 2.5, radius: 9 };
    }
    if (type === 'optimal') {
      return { fill: '#40D9BD', stroke: '#D7FFF5', strokeWidth: 2.5, radius: 9 };
    }
    return { fill: '#7F8A98', stroke: '#B8C1CC', strokeWidth: 0.9, radius: 3.5 };
  };

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
            {scatterData.map((entry, i) => {
              const point = getPointStyle(entry.type);
              return (
                <Cell
                  key={i}
                  fill={point.fill}
                  stroke={point.stroke}
                  strokeWidth={point.strokeWidth}
                  r={point.radius}
                />
              );
            })}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap gap-x-4 gap-y-2 mt-2 justify-center">
        <div className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#7F8A98] ring-1 ring-[#B8C1CC]/70" /><span className="font-mono text-[10px] text-muted-foreground">Frontier Points</span></div>
        <div className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#FFAD4D] ring-1 ring-[#FFF1D8]/90" /><span className="font-mono text-[10px] text-muted-foreground">Your Portfolio</span></div>
        <div className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-[#40D9BD] ring-1 ring-[#D7FFF5]/90" /><span className="font-mono text-[10px] text-muted-foreground">Optimal</span></div>
      </div>
    </div>
  );
};

export default EfficientFrontier;
