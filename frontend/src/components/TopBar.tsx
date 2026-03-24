import { Bell, User } from 'lucide-react';

interface TopBarProps {
  title: string;
}

const TopBar = ({ title }: TopBarProps) => (
  <header className="glass-navbar sticky top-0 z-30 h-[52px] flex items-center px-6 justify-between">
    <h2 className="font-display font-bold text-foreground text-lg">{title}</h2>
    <div className="flex items-center gap-3">
      <div className="glass-panel rounded-full px-3 py-1 flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-signal-green" />
        <span className="font-mono text-[10px] text-muted-foreground">SPY $512.40</span>
        <span className="font-mono text-[10px] text-signal-green">+1.2%</span>
      </div>
      <button className="text-muted-foreground hover:text-foreground transition-colors">
        <Bell size={16} />
      </button>
      <div className="w-7 h-7 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
        <User size={14} className="text-primary" />
      </div>
    </div>
  </header>
);

export default TopBar;
