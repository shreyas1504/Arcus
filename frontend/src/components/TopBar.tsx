import { Bell, User, Menu } from 'lucide-react';

interface TopBarProps {
  title: string;
  onMenuClick?: () => void;
  isMobile?: boolean;
}

const TopBar = ({ title, onMenuClick, isMobile }: TopBarProps) => (
  <header className="glass-navbar sticky top-0 z-30 h-[52px] flex items-center px-4 md:px-6 justify-between gap-3">
    <div className="flex items-center gap-3 min-w-0">
      {/* Hamburger — mobile only */}
      {isMobile && (
        <button
          onClick={onMenuClick}
          className="text-muted-foreground hover:text-foreground transition-colors flex-shrink-0 p-1"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
      )}
      <h2 className="font-display font-bold text-foreground text-base md:text-lg truncate">{title}</h2>
    </div>

    <div className="flex items-center gap-2 md:gap-3 flex-shrink-0">
      {/* Hide ticker on very small screens */}
      <div className="hidden sm:flex glass-panel rounded-full px-3 py-1 items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-signal-green" />
        <span className="font-mono text-[10px] text-muted-foreground">SPY $512.40</span>
        <span className="font-mono text-[10px] text-signal-green">+1.2%</span>
      </div>
      <button className="text-muted-foreground hover:text-foreground transition-colors p-1">
        <Bell size={16} />
      </button>
      <div className="w-7 h-7 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0">
        <User size={14} className="text-primary" />
      </div>
    </div>
  </header>
);

export default TopBar;
