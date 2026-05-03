import { Bell, User, Menu, Home, Settings, LogOut, UserCircle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import ArcusLogo from './ArcusLogo';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface TopBarProps {
  title: string;
  onMenuClick?: () => void;
  isMobile?: boolean;
}

const TopBar = ({ title, onMenuClick, isMobile }: TopBarProps) => {
  const navigate = useNavigate();

  const handleSignOut = () => {
    localStorage.clear();
    navigate('/');
  };

  return (
    <header className="glass-navbar sticky top-0 z-30 h-[52px] flex items-center px-4 md:px-6 justify-between gap-3">
      <div className="flex items-center gap-2 min-w-0">
        {isMobile && (
          <>
            <button
              onClick={onMenuClick}
              className="text-muted-foreground hover:text-foreground transition-colors flex-shrink-0 p-1"
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
            <Link to="/" className="flex items-center gap-1">
              <ArcusLogo size={22} />
              <span className="font-display font-extrabold text-foreground text-sm mr-1">Arcus</span>
            </Link>
          </>
        )}
        <h2 className="font-display font-bold text-foreground text-sm sm:text-base md:text-lg truncate">{title}</h2>
      </div>

      <div className="flex items-center gap-2 md:gap-3 flex-shrink-0">
        {isMobile && (
          <Link to="/" aria-label="Home" className="text-muted-foreground hover:text-primary transition-colors p-1">
            <Home size={18} />
          </Link>
        )}
        <div className="hidden sm:flex glass-panel rounded-full px-3 py-1 items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-signal-green" />
          <span className="font-mono text-[10px] text-muted-foreground">SPY $512.40</span>
          <span className="font-mono text-[10px] text-signal-green">+1.2%</span>
        </div>

        {/* Notification Bell */}
        <Popover>
          <PopoverTrigger asChild>
            <button className="text-muted-foreground hover:text-foreground transition-colors p-1" aria-label="Notifications">
              <Bell size={16} />
            </button>
          </PopoverTrigger>
          <PopoverContent align="end" className="w-64">
            <div className="flex items-center gap-2 mb-2">
              <Bell size={14} className="text-primary" />
              <span className="font-mono text-xs font-bold text-foreground">Notifications</span>
            </div>
            <p className="text-xs text-muted-foreground">
              No alerts configured yet. Set up alerts in{' '}
              <Link to="/settings" className="text-primary hover:underline">Settings</Link>.
            </p>
          </PopoverContent>
        </Popover>

        {/* Profile Avatar */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="w-7 h-7 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center flex-shrink-0 cursor-pointer hover:bg-primary/30 transition-colors" aria-label="User menu">
              <User size={14} className="text-primary" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={() => navigate('/profile')} className="cursor-pointer">
              <UserCircle size={14} className="mr-2" />
              My Profile
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => navigate('/settings')} className="cursor-pointer">
              <Settings size={14} className="mr-2" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleSignOut} className="cursor-pointer text-signal-red focus:text-signal-red">
              <LogOut size={14} className="mr-2" />
              Sign Out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
};

export default TopBar;
