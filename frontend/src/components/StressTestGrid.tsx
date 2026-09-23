import { motion } from 'framer-motion';
import DataUnavailable from '@/components/DataUnavailable';

export type StressTest = { name: string; loss: number; recoveryDays: number };
import AnimatedNumber from './AnimatedNumber';

const StressTestGrid = ({ data }: { data?: StressTest[] }) => {
  if (!data?.length) {
    return (
      <div>
        <span className="label-mono mb-4 block">STRESS TESTING</span>
        <div className="glass rounded-xl p-5">
          <DataUnavailable label="Stress tests" height={140} />
        </div>
      </div>
    );
  }
  const tests = data;
  return (
    <div>
      <span className="label-mono mb-4 block">STRESS TESTING</span>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {tests.map((test, i) => (
          <motion.div
            key={test.name}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="glass rounded-xl p-4 card-hover-glow"
          >
            <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{test.name}</span>
            <div className="font-mono text-[28px] font-bold text-signal-red mt-1">
              <AnimatedNumber value={test.loss} format={(n) => `${n.toFixed(1)}%`} />
            </div>
            <div className="flex items-center gap-1 mt-1">
              <span className="font-mono text-[11px] text-signal-amber">
                Recovery: <AnimatedNumber value={test.recoveryDays} format={(n) => `${Math.round(n)} days`} />
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default StressTestGrid;
