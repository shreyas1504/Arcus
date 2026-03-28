import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { MOCK_SECTORS } from '@/lib/mock-data';

const SectorDonut = ({ data }: { data?: typeof MOCK_SECTORS }) => {
  const chartData = data ?? MOCK_SECTORS;
  return (
    <div className="glass rounded-xl p-5 flex flex-col h-full">
      <span className="label-mono">SECTOR CONCENTRATION</span>
      <div className="flex-1 relative flex items-center justify-center min-h-[200px] mt-4">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={80}
              dataKey="value"
              paddingAngle={3}
              strokeWidth={0}
            >
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: '#161B22',
                border: '1px solid rgba(56,189,148,0.2)',
                borderRadius: 8,
                fontFamily: 'JetBrains Mono',
                fontSize: 11,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <span className="font-mono text-2xl font-bold text-foreground">{chartData.length}</span>
            <p className="font-mono text-[9px] text-muted-foreground">sectors</p>
          </div>
        </div>
      </div>
      <div className="flex flex-wrap gap-3 mt-3 justify-center">
        {chartData.map((s) => (
          <div key={s.name} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: s.color }} />
            <span className="font-mono text-[10px] text-muted-foreground">{s.name} {s.value}%</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SectorDonut;
