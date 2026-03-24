import { useState } from 'react';
import { motion } from 'framer-motion';
import { SendHorizontal, Zap, User } from 'lucide-react';
import AppLayout from '@/components/AppLayout';
import BackButton from '@/components/BackButton';
import { sendChatMessage } from '@/lib/api';

const quickPrompts = ['PORTFOLIO RISK', 'SHARPE ANALYSIS', 'STRESS TEST', 'SECTOR EXPOSURE', 'REBALANCING', 'MARKET MOOD'];

const initialMessages: { role: 'ai' | 'user'; content: string }[] = [
  {
    role: 'ai',
    content: "Welcome to Arcus AI. I have access to your portfolio data. How can I help you today?",
  },
];

const Chat = () => {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);

  const doSendMessage = async (text: string) => {
    if (!text.trim()) return;
    const userMsg = { role: 'user' as const, content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setTyping(true);

    const portfolioContext = {
      portfolio: (() => { try { return JSON.parse(localStorage.getItem('arcus-portfolio') || 'null'); } catch { return null; } })(),
      metrics: (() => { try { return JSON.parse(localStorage.getItem('arcus-last-analysis') || 'null')?.metrics; } catch { return null; } })(),
      investor_dna: (() => { try { return JSON.parse(localStorage.getItem('arcus-onboarding-state') || 'null'); } catch { return null; } })(),
    };

    try {
      const data = await sendChatMessage(text, portfolioContext);
      setMessages((prev) => [...prev, { role: 'ai', content: data.reply || data.response || data.content || 'No response received.' }]);
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) => [...prev, { role: 'ai', content: 'Sorry, I had trouble connecting. Please try again.' }]);
    } finally {
      setTyping(false);
    }
  };

  return (
    <AppLayout title="AI Chat">
      <div className="flex flex-1 overflow-hidden h-[calc(100vh-52px)]">
        {/* Sidebar */}
        <div className="w-64 glass-panel p-4 hidden lg:flex flex-col gap-4 border-r border-border">
          <div className="flex items-center gap-2">
            <Zap size={16} className="text-primary" />
            <span className="font-display font-bold text-sm text-foreground">ARCUS AI</span>
          </div>
          <div className="glass rounded-lg p-3 mt-2">
            <span className="font-mono text-[10px] text-muted-foreground">Your profile:</span>
            <span className="font-mono text-[10px] text-primary block mt-1">GROWTH investor, 15% target</span>
          </div>
          <div className="mt-4">
            <span className="label-mono mb-2 block" style={{ color: 'hsl(214 10% 57%)' }}>QUICK PROMPTS</span>
            <div className="flex flex-wrap gap-1.5">
              {quickPrompts.map((p) => (
                <button
                  key={p}
                  onClick={() => doSendMessage(p.toLowerCase())}
                  className="font-mono text-[9px] uppercase tracking-wider px-2.5 py-1.5 rounded-full glass text-muted-foreground hover:text-primary hover:border-primary/30 transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col">
          <div className="px-6 pt-4">
            <BackButton to="/dashboard/results" />
          </div>
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((msg, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-xl rounded-xl px-4 py-3 ${msg.role === 'user' ? 'bg-primary/20 text-foreground' : 'glass'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    {msg.role === 'ai' ? <Zap size={12} className="text-primary" /> : <User size={12} className="text-primary" />}
                    <span className="font-mono text-[9px] uppercase text-muted-foreground">{msg.role === 'ai' ? 'ARCUS AI' : 'YOU'}</span>
                  </div>
                  <p className="text-sm leading-relaxed whitespace-pre-line">
                    {msg.content.split(/(\*\*[^*]+\*\*)/g).map((part, j) => {
                      if (part.startsWith('**') && part.endsWith('**')) {
                        return <span key={j} className="font-mono font-bold text-primary">{part.slice(2, -2)}</span>;
                      }
                      return part;
                    })}
                  </p>
                </div>
              </motion.div>
            ))}
            {typing && (
              <div className="flex justify-start">
                <div className="glass rounded-xl px-4 py-3 flex items-center gap-1">
                  {[0, 1, 2].map((i) => (
                    <motion.span key={i} className="w-1.5 h-1.5 rounded-full bg-primary" animate={{ scale: [0, 1, 0] }} transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-4 border-t border-border">
            <div className="glass rounded-xl flex items-center px-4 py-2 focus-within:border-primary transition-colors">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && doSendMessage(input)}
                placeholder="Ask about your portfolio risk, allocation, strategy..."
                className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 outline-none"
              />
              <button onClick={() => doSendMessage(input)} className="text-primary hover:text-accent-bright transition-colors ml-2">
                <SendHorizontal size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};

export default Chat;
