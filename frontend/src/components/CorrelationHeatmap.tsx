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
  const size = 48;

  return (
    <div className="glass rounded-xl p-5">
      <span className="label-mono">CORRELATION MATRIX</span>
      <div className="mt-4 overflow-x-auto">
        <div className="inline-block">
          <div className="flex">
            <div style={{ width: size }} />
            {tickers.map((t) => (
              <div key={t} className="font-mono text-[10px] text-muted-foreground text-center" style={{ width: size }}>{t}</div>
            ))}
          </div>
          {matrix.map((row, i) => (
            <div key={i} className="flex">
              <div className="font-mono text-[10px] text-muted-foreground flex items-center" style={{ width: size }}>{tickers[i]}</div>
              {row.map((val, j) => (
                <motion.div
                  key={j}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: (i * tickers.length + j) * 0.015, duration: 0.3 }}
                  className="flex items-center justify-center rounded-md m-0.5 font-mono text-[10px] font-medium cursor-default"
                  style={{
                    width: size - 4,
                    height: size - 4,
                    backgroundColor: `${getColor(val)}20`,
                    color: getColor(val),
                  }}
                  title={`${tickers[i]} ↔ ${tickers[j]}: ${val.toFixed(2)}`}
                >
                  {val.toFixed(2)}
                </motion.div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default CorrelationHeatmap;
