import { useState } from 'react';
import { ReactNode } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import FloatingChat from './FloatingChat';
import NewsTicker from './NewsTicker';

interface AppLayoutProps {
  children: ReactNode;
  title: string;
}

const AppLayout = ({ children, title }: AppLayoutProps) => {
  const [collapsed, setCollapsed] = useState(true);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <NewsTicker />
      <div className="flex pt-9">
        <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
        <div
          className="flex-1 flex flex-col min-h-screen transition-all duration-300"
          style={{ marginLeft: collapsed ? 64 : 220 }}
        >
          <TopBar title={title} />
          <main className="flex-1">{children}</main>
        </div>
      </div>
      <FloatingChat />
    </div>
  );
};

export default AppLayout;
