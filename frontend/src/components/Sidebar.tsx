import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutDashboard, FlaskConical, MessageSquare, FileText, Settings, User, ChevronLeft, ChevronRight } from 'lucide-react';
import ArcusLogo from './ArcusLogo';

const navItems = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
  { icon: FlaskConical, label: 'Sandbox', path: '/dashboard/mock' },
  { icon: MessageSquare, label: 'AI Chat', path: '/chat' },
  { icon: FileText, label: 'Reports', path: '/dashboard/results' },
];

const bottomItems = [
  { icon: Settings, label: 'Settings', path: '#' },
  { icon: User, label: 'Profile / DNA', path: '/onboarding' },
];

const Sidebar = () => {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/dashboard') return location.pathname === '/dashboard';
    if (path === '/dashboard/results') return location.pathname === '/dashboard/results';
    return location.pathname === path;
  };

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 220 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="fixed left-0 top-9 h-[calc(100%-36px)] z-40 flex flex-col bg-card border-r border-border"
      style={{ backdropFilter: 'blur(20px)' }}
    >
      {/* Logo */}
      <Link to="/" className="flex items-center gap-2 px-4 h-[52px] border-b border-border flex-shrink-0">
        <ArcusLogo size={26} />
        <AnimatePresence>
          {!collapsed && (
            <motion.span
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              className="font-display font-extrabold text-foreground text-lg overflow-hidden whitespace-nowrap"
            >
              Arcus
            </motion.span>
          )}
        </AnimatePresence>
      </Link>

      {/* Nav items */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {navItems.map((item) => {
          const active = isActive(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all relative ${
                active
                  ? 'bg-accent/8 text-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent/5'
              }`}
            >
              {active && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 bg-primary rounded-r-full"
                />
              )}
              <item.icon size={18} className="text-primary flex-shrink-0" />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="font-display font-medium text-[13px] overflow-hidden whitespace-nowrap"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          );
        })}
      </nav>

      {/* Bottom items */}
      <div className="px-2 py-2 space-y-1 border-t border-border">
        {bottomItems.map((item) => (
          <Link
            key={item.label}
            to={item.path}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/5 transition-all"
          >
            <item.icon size={18} className="text-primary flex-shrink-0" />
            <AnimatePresence>
              {!collapsed && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  className="font-display font-medium text-[13px] overflow-hidden whitespace-nowrap"
                >
                  {item.label}
                </motion.span>
              )}
            </AnimatePresence>
          </Link>
        ))}

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/5 transition-all w-full"
        >
          {collapsed ? <ChevronRight size={18} className="text-primary flex-shrink-0" /> : <ChevronLeft size={18} className="text-primary flex-shrink-0" />}
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="font-display font-medium text-[13px] overflow-hidden whitespace-nowrap"
              >
                Collapse
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  );
};

export default Sidebar;
