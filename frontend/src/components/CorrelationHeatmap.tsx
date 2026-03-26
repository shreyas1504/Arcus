import { motion } from 'framer-motion';
import { MOCK_CORRELATION } from '@/lib/mock-data';

const getColor = (val: number) => {
  if (val >= 0.85) return { bg: 'rgba(240,81,79,0.18)', text: '#F0514F' };
  if (val >= 0.7)  return { bg: 'rgba(240,164,79,0.18)', text: '#F0A44F' };
  if (val >= 0.5)  return { bg: 'rgba(56,189,164,0.18)', text: '#38BDA4' };
  if (val <= -0.3) return { bg: 'rgba(79,156,240,0.18)', text: '#4F9CF0' };
  return { bg: 'rgba(72,79,88,0.18)', text: '#8B949E' };
};

const CorrelationHeatmap = ({ data }: { data?: typeof MOCK_CORRELATION }) => {
  const { tickers, matrix } = data ?? MOCK_CORRELATION;
  const n = tickers.length;

  return (
    <div className="glass rounded-xl p-4 sm:p-5">
      <span className="label-mono" style={{ color: 'hsl(214 10% 57%)' }}>CORRELATION MATRIX</span>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-3 mb-4 flex-wrap">
        {[
          { color: '#F0514F', label: '≥0.85 High' },
          { color: '#F0A44F', label: '≥0.70 Mod' },
          { color: '#38BDA4', label: '≥0.50 Low' },
          { color: '#8B949E', label: 'Weak' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1">
            <div className="w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
            <span className="font-mono text-[9px] text-muted-foreground">{label}</span>
          </div>
        ))}
      </div>

      {/* Full-width grid — label column is fixed, data columns share remaining space equally */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `40px repeat(${n}, 1fr)`,
          gap: '3px',
        }}
      >
        {/* Top-left empty corner */}
        <div />
        {/* Column headers */}
        {tickers.map((t) => (
          <div
            key={t}
            className="font-mono text-[9px] text-muted-foreground flex items-center justify-center truncate"
            style={{ aspectRatio: '1' }}
          >
            {t}
          </div>
        ))}

        {/* Rows */}
        {matrix.map((row, i) => (
          <>
            {/* Row label */}
            <div
              key={`label-${i}`}
              className="font-mono text-[9px] text-muted-foreground flex items-center justify-end pr-1.5 truncate"
              style={{ aspectRatio: '1' }}
            >
              {tickers[i]}
            </div>

            {/* Cells */}
            {row.map((val, j) => {
              const { bg, text } = getColor(val);
              return (
                <motion.div
                  key={j}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: (i * n + j) * 0.012, duration: 0.25 }}
                  className="flex items-center justify-center rounded font-mono font-semibold cursor-default select-none"
                  style={{
                    aspectRatio: '1',
                    fontSize: n > 6 ? 8 : 10,
                    backgroundColor: bg,
                    color: text,
                    border: i === j ? `1px solid ${text}40` : 'none',
                  }}
                  title={`${tickers[i]} ↔ ${tickers[j]}: ${val.toFixed(2)}`}
                >
                  {val.toFixed(2)}
                </motion.div>
              );
            })}
          </>
        ))}
      </div>
    </div>
  );
};

export default CorrelationHeatmap;
