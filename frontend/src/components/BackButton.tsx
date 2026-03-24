import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

interface BackButtonProps {
  to: string;
  label?: string;
}

const BackButton = ({ to, label = 'Back' }: BackButtonProps) => (
  <Link to={to} className="inline-flex items-center gap-1.5 group mb-4">
    <motion.div whileHover={{ x: -2 }} transition={{ type: 'spring', stiffness: 300 }}>
      <ArrowLeft size={16} className="text-primary group-hover:text-foreground transition-colors" />
    </motion.div>
    <span className="font-display font-medium text-[13px] text-muted-foreground group-hover:text-foreground transition-colors">
      {label}
    </span>
  </Link>
);

export default BackButton;
