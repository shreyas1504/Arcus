import { motion } from 'framer-motion';
import { MOCK_STRESS_TESTS } from '@/lib/mock-data';
import AnimatedNumber from './AnimatedNumber';

const StressTestGrid = ({ data }: { data?: typeof MOCK_STRESS_TESTS }) => {
  const tests = data ?? MOCK_STRESS_TESTS;
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
