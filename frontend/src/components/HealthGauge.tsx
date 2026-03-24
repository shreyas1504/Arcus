import { motion } from 'framer-motion';
import AnimatedNumber from './AnimatedNumber';

const HealthGauge = ({ score }: { score: number }) => {
  const radius = 80;
  const stroke = 8;
  const circumference = Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = score > 70 ? '#38BDA4' : score > 40 ? '#F0A44F' : '#F0514F';

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <svg width="200" height="120" viewBox="0 0 200 120">
          <defs>
            <filter id="teal-glow-filter">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <path
            d={`M 20 100 A ${radius} ${radius} 0 0 1 180 100`}
            fill="none"
            stroke="rgba(48,54,61,0.5)"
            strokeWidth={stroke}
            strokeLinecap="round"
          />
          <motion.path
            d={`M 20 100 A ${radius} ${radius} 0 0 1 180 100`}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            filter="url(#teal-glow-filter)"
            initial={{ strokeDasharray: `0 ${circumference}` }}
            animate={{ strokeDasharray: `${progress} ${circumference}` }}
            transition={{ duration: 1.5, ease: [0.25, 0.46, 0.45, 0.94] }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center pt-4">
          <span className="font-mono text-[48px] font-extrabold text-foreground">
            <AnimatedNumber value={score} format={(n) => Math.round(n).toString()} duration={1.5} />
          </span>
        </div>
      </div>
      <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-primary mt-2">HEALTH SCORE</span>
    </div>
  );
};

export default HealthGauge;
