import { ReactNode } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import FloatingChat from './FloatingChat';
import NewsTicker from './NewsTicker';

interface AppLayoutProps {
  children: ReactNode;
  title: string;
}

const AppLayout = ({ children, title }: AppLayoutProps) => (
  <div className="min-h-screen bg-background flex flex-col">
    <NewsTicker />
    <div className="flex pt-9">
      <Sidebar />
      <div className="flex-1 ml-[220px] flex flex-col min-h-screen">
        <TopBar title={title} />
        <main className="flex-1">{children}</main>
      </div>
    </div>
    <FloatingChat />
  </div>
);

export default AppLayout;
