import { motion } from 'framer-motion';
import { LucideIcon, MessageSquare } from 'lucide-react';
import AnimatedNumber from './AnimatedNumber';
import Sparkline from './Sparkline';

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { openArcusChat } from '@/lib/chat-launcher';

interface MetricCardProps {
  icon: LucideIcon;
  label: string;
  value: number;
  format?: (n: number) => string;
  change?: number;
  changeLabel?: string;
  sparklineData?: number[];
  delay?: number;
  chatQuestion?: string;
}

const MetricCard = ({ icon: Icon, label, value, format, change, changeLabel, sparklineData, delay = 0, chatQuestion }: MetricCardProps) => {
  const isPositive = change !== undefined ? change >= 0 : true;

  const handleClick = () => {
    if (chatQuestion) {
      openArcusChat(chatQuestion);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      whileHover={{ y: -2, boxShadow: '0 0 0 1px rgba(56,189,148,0.3), 0 8px 32px rgba(0,0,0,0.3)' }}
      onClick={handleClick}
      className={`glass rounded-xl p-4 relative overflow-hidden ${chatQuestion ? 'cursor-pointer' : 'cursor-default'}`}
    >
      <div className="flex items-center gap-1.5 mb-2">
        <Icon size={16} className="text-primary" />
        <span className="label-mono">{label}</span>
        {chatQuestion && (
          <Tooltip>
            <TooltipTrigger asChild>
              <MessageSquare size={12} className="text-primary/60 hover:text-primary ml-auto transition-colors" />
            </TooltipTrigger>
            <TooltipContent side="top" className="text-xs">Click to explain in AI chat</TooltipContent>
          </Tooltip>
        )}
      </div>
      <div className="value-large">
        <AnimatedNumber value={value} format={format} />
      </div>
      <div className="flex items-center justify-between mt-2">
        {change !== undefined && (
          <span className={`font-mono text-[11px] px-2 py-0.5 rounded-full ${isPositive ? 'bg-signal-green/10 text-signal-green' : 'bg-signal-red/10 text-signal-red'}`}>
            {isPositive ? '▲' : '▼'} {changeLabel || (isPositive ? '+' : '') + change.toFixed(2)}
          </span>
        )}
        {sparklineData && (
          <div className="ml-auto">
            <Sparkline data={sparklineData} color={isPositive ? '#3FB68B' : '#F0514F'} />
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default MetricCard;
