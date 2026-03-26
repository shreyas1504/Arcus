import { motion } from 'framer-motion';
import { MOCK_CORRELATION } from '@/lib/mock-data';

const getColor = (val: number) => {
  if (val >= 0.85) return '#F0514F';
  if (val >= 0.75) return '#F0A44F';
  if (val >= 0.6) return '#38BDA4';
  return '#484F58';
};

const CorrelationHeatmap = ({ data }: { data?: typeof MOCK_CORRELATION }) => {
  const { tickers, matrix } = data ?? MOCK_CORRELATION;
  const n = tickers.length;

  return (
    <div className="glass rounded-xl p-5">
      <span className="label-mono">CORRELATION MATRIX</span>
      <div className="mt-4 w-full overflow-x-auto">
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `min-content repeat(${n}, 1fr)`,
            gap: '2px',
            minWidth: `${n * 40 + 44}px`,
          }}
        >
          {/* Top-left empty corner */}
          <div />
          {/* Column headers */}
          {tickers.map((t) => (
            <div
              key={t}
              className="font-mono text-[10px] text-muted-foreground flex items-center justify-center py-1"
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
                className="font-mono text-[10px] text-muted-foreground flex items-center pr-2 whitespace-nowrap"
              >
                {tickers[i]}
              </div>

              {/* Cells */}
              {row.map((val, j) => (
                <motion.div
                  key={j}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: (i * n + j) * 0.015, duration: 0.3 }}
                  className="aspect-square flex items-center justify-center rounded-md font-mono text-[9px] sm:text-[10px] font-medium cursor-default"
                  style={{
                    backgroundColor: `${getColor(val)}20`,
                    color: getColor(val),
                  }}
                  title={`${tickers[i]} ↔ ${tickers[j]}: ${val.toFixed(2)}`}
                >
                  {val.toFixed(2)}
                </motion.div>
              ))}
            </>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CorrelationHeatmap;
