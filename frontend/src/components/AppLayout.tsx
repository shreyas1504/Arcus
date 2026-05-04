import { useState } from 'react';
import { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import FloatingChat from './FloatingChat';
import NewsTicker from './NewsTicker';
import { useIsMobile } from '@/hooks/use-mobile';

interface AppLayoutProps {
  children: ReactNode;
  title: string;
}

const AppLayout = ({ children, title }: AppLayoutProps) => {
  const [collapsed, setCollapsed] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const isMobile = useIsMobile();
  const location = useLocation();
  const showFloatingChat = location.pathname !== '/chat';

  return (
    <div className="min-h-screen bg-background flex flex-col overflow-x-hidden">
      <NewsTicker />
      <div className="flex pt-9 relative overflow-x-hidden">
        {/* Mobile backdrop */}
        {isMobile && mobileOpen && (
          <div
            className="fixed inset-0 bg-black/60 z-30 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
        )}

        <Sidebar
          collapsed={isMobile ? false : collapsed}
          setCollapsed={setCollapsed}
          mobileOpen={mobileOpen}
          setMobileOpen={setMobileOpen}
          isMobile={isMobile}
        />

        <div
          className="flex-1 flex flex-col min-h-screen transition-all duration-300"
          style={{ marginLeft: isMobile ? 0 : (collapsed ? 64 : 220) }}
        >
          <TopBar
            title={title}
            onMenuClick={() => setMobileOpen(true)}
            isMobile={isMobile}
          />
          <main className="flex-1">{children}</main>
        </div>
      </div>
      {showFloatingChat && <FloatingChat />}
    </div>
  );
};

export default AppLayout;
