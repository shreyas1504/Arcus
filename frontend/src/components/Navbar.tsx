import { Link, useLocation } from 'react-router-dom';
import { Bell, User } from 'lucide-react';
import ArcusLogo from './ArcusLogo';

const navItems = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Sandbox', path: '/dashboard/mock' },
  { label: 'Chat', path: '/chat' },
];

const Navbar = () => {
  const location = useLocation();

  return (
    <nav className="glass-navbar sticky top-0 z-50 h-[52px] flex items-center px-4 justify-between">
      <Link to="/" className="flex items-center gap-2">
        <ArcusLogo size={28} />
        <span className="font-display font-extrabold text-foreground text-lg">Arcus</span>
      </Link>

      <div className="flex items-center gap-1 bg-card/50 rounded-full p-1">
        {navItems.map((item) => {
          const active = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path) && item.path === '/dashboard' && !location.pathname.includes('mock'));
          const isActive = item.path === '/dashboard' 
            ? location.pathname === '/dashboard' || location.pathname === '/dashboard/results'
            : location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-card-elevated'
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </div>

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
    </nav>
  );
};

export default Navbar;
