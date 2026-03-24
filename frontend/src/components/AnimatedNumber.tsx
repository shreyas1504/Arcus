import { useEffect, useRef, useState } from 'react';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';

interface AnimatedNumberProps {
  value: number;
  format?: (n: number) => string;
  duration?: number;
  className?: string;
}

const AnimatedNumber = ({ value, format, duration = 1.2, className = '' }: AnimatedNumberProps) => {
  const motionVal = useMotionValue(0);
  const [display, setDisplay] = useState('0');

  useEffect(() => {
    const controls = animate(motionVal, value, {
      duration,
      ease: [0.25, 0.46, 0.45, 0.94],
      onUpdate: (v) => {
        setDisplay(format ? format(v) : v.toFixed(2));
      },
    });
    return controls.stop;
  }, [value, format, duration]);

  return <span className={className}>{display}</span>;
};

export default AnimatedNumber;
