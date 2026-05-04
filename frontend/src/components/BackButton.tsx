import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

interface BackButtonProps {
  to: string;
  label?: string;
}

const BackButton = ({ to, label = 'Back' }: BackButtonProps) => (
  <Link to={to} className="inline-flex max-w-full items-center gap-1.5 group mb-4 -ml-1 rounded-lg px-1 py-1">
    <motion.div className="flex h-4 w-4 flex-shrink-0 items-center justify-center" whileHover={{ x: -2 }} transition={{ type: 'spring', stiffness: 300 }}>
      <ArrowLeft size={16} className="block text-primary group-hover:text-foreground transition-colors" />
    </motion.div>
    <span className="min-w-0 truncate font-display font-medium text-[13px] text-muted-foreground group-hover:text-foreground transition-colors">
      {label}
    </span>
  </Link>
);

export default BackButton;
