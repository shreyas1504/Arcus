import { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { SendHorizontal, Zap, User, Trash2, AlertTriangle, RefreshCw } from 'lucide-react';
import AppLayout from '@/components/AppLayout';
import BackButton from '@/components/BackButton';
import Disclaimer from '@/components/legal/Disclaimer';
import { sendChatMessage, ChatMessage } from '@/lib/api';
import { ARCUS_CHAT_EVENT, consumePendingArcusChatMessage } from '@/lib/chat-launcher';
import { buildChatPortfolioContext } from '@/lib/portfolio-context';

const Chat = () => {
  const [messages, setMessages] = useState<{ role: 'ai' | 'user'; content: string }[]>([
    { role: 'ai', content: "Welcome to Arcus AI. I have access to your portfolio data. How can I help you today?" },
  ]);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [show503, setShow503] = useState(false);
  const [pendingRetry, setPendingRetry] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const ctx = buildChatPortfolioContext();
  const healthScore = ctx?.metrics.healthScore ?? 0;
  const sharpe = ctx?.metrics.sharpe ?? 0;
  const var95 = ctx?.metrics.var95 ?? 0;
  const riskTolerance = ctx?.investorProfile?.riskTolerance ?? 'Moderate';
  const targetReturn = ctx?.investorProfile?.targetReturn ?? 0.10;

  const quickPrompts = useMemo(() => [
    {
      label: 'PORTFOLIO RISK',
      prompt: `My Health Score is ${healthScore}, Sharpe ${sharpe.toFixed(2)}, VaR ${(var95 * 100).toFixed(1)}%. What are my top 3 risk concerns?`,
    },
    {
      label: 'SHARPE ANALYSIS',
      prompt: `My Sharpe is ${sharpe.toFixed(2)}. Good for a ${riskTolerance} investor targeting ${(targetReturn * 100).toFixed(0)}%? How to improve it?`,
    },
    {
      label: 'STRESS TEST',
      prompt: 'How would my portfolio perform in a 2008-style crash?',
    },
    {
      label: 'SECTOR EXPOSURE',
      prompt: 'Analyze my sector concentration. Am I too heavily weighted in any sector?',
    },
    {
      label: 'REBALANCING',
      prompt: 'What specific trades should I make to rebalance?',
    },
    {
      label: 'MARKET MOOD',
      prompt: 'Given current market conditions, what should I watch for in my portfolio?',
    },
  ], [healthScore, sharpe, var95, riskTolerance, targetReturn]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typing]);

  const doSendMessage = async (text: string) => {
    if (!text.trim()) return;
    const userMsg = { role: 'user' as const, content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setTyping(true);
    setShow503(false);

    const newHistory: ChatMessage[] = [...history, { role: 'user', content: text }];

    try {
      const latestCtx = buildChatPortfolioContext();
      const data = await sendChatMessage(text, latestCtx, newHistory);

      if (data.status503) {
        setShow503(true);
        setPendingRetry(text);
        setMessages(prev => [...prev, {
          role: 'ai',
          content: '⏳ AI backend is starting up. This usually takes ~30 seconds on first use. Click Retry below.',
        }]);
      } else {
        const reply = data.reply || 'No response received.';
        setMessages(prev => [...prev, { role: 'ai', content: reply }]);
        setHistory([...newHistory, { role: 'assistant', content: reply }]);
        setShow503(false);
        setPendingRetry(null);
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages(prev => [...prev, { role: 'ai', content: 'Sorry, I had trouble connecting. Please try again.' }]);
    } finally {
      setTyping(false);
    }
  };

  const handleRetry = () => {
    if (pendingRetry) {
      setShow503(false);
      setTimeout(() => doSendMessage(pendingRetry), 5000);
    }
  };

  const clearChat = () => {
    setMessages([{ role: 'ai', content: "Chat cleared. How can I help you?" }]);
    setHistory([]);
    setShow503(false);
    setPendingRetry(null);
  };

  useEffect(() => {
    const pending = consumePendingArcusChatMessage();
    if (!pending) return;
    setInput(pending);
    window.setTimeout(() => {
      doSendMessage(pending);
    }, 150);
  }, []);

  useEffect(() => {
    const handleOpen = (event: Event) => {
      const detail = (event as CustomEvent<{ message?: string }>).detail;
      const pending = detail?.message || consumePendingArcusChatMessage();
      if (!pending) return;
      setInput(pending);
      window.setTimeout(() => {
        doSendMessage(pending);
      }, 150);
    };

    window.addEventListener(ARCUS_CHAT_EVENT, handleOpen);
    return () => window.removeEventListener(ARCUS_CHAT_EVENT, handleOpen);
  }, [history]);

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
            <span className="font-mono text-[10px] text-primary block mt-1">
              {riskTolerance.toUpperCase()} investor, {(targetReturn * 100).toFixed(0)}% target
            </span>
          </div>
          <div className="mt-4">
            <span className="label-mono mb-2 block" style={{ color: 'hsl(214 10% 57%)' }}>QUICK PROMPTS</span>
            <div className="flex flex-wrap gap-1.5">
              {quickPrompts.map(p => (
                <button
                  key={p.label}
                  onClick={() => doSendMessage(p.prompt)}
                  className="font-mono text-[9px] uppercase tracking-wider px-2.5 py-1.5 rounded-full glass text-muted-foreground hover:text-primary hover:border-primary/30 transition-colors"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-auto">
            <button
              onClick={clearChat}
              className="flex items-center gap-2 text-muted-foreground hover:text-signal-red transition-colors font-mono text-[10px]"
            >
              <Trash2 size={12} /> Clear Chat
            </button>
          </div>
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col">
          <div className="px-6 pt-4 flex items-center justify-between">
            <BackButton to="/dashboard/results" />
            <button
              onClick={clearChat}
              className="lg:hidden flex items-center gap-1 text-muted-foreground hover:text-signal-red transition-colors font-mono text-[10px]"
            >
              <Trash2 size={12} /> Clear
            </button>
          </div>

          {/* 503 Banner */}
          <AnimatePresence>
            {show503 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mx-6 mt-2"
              >
                <div className="bg-signal-amber/10 border border-signal-amber/30 rounded-lg px-4 py-3 flex items-center gap-3">
                  <AlertTriangle size={16} className="text-signal-amber flex-shrink-0" />
                  <span className="text-xs text-signal-amber flex-1">AI is waking up (~30 sec on first use)</span>
                  <button
                    onClick={handleRetry}
                    className="flex items-center gap-1 px-3 py-1 rounded-full bg-signal-amber/20 text-signal-amber font-mono text-[10px] hover:bg-signal-amber/30 transition-colors"
                  >
                    <RefreshCw size={10} /> Retry
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

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
                <div className="glass rounded-xl px-4 py-3 flex items-center gap-1.5">
                  {[0, 1, 2].map(i => (
                    <motion.span
                      key={i}
                      className="w-2 h-2 rounded-full bg-primary"
                      animate={{ y: [0, -4, 0] }}
                      transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                    />
                  ))}
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Mobile quick prompts */}
          <div className="lg:hidden flex gap-1.5 px-4 py-2 overflow-x-auto border-t border-border">
            {quickPrompts.slice(0, 4).map(p => (
              <button
                key={p.label}
                onClick={() => doSendMessage(p.prompt)}
                className="font-mono text-[9px] uppercase tracking-wider px-2.5 py-1.5 rounded-full glass text-muted-foreground hover:text-primary whitespace-nowrap flex-shrink-0"
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="p-4 border-t border-border">
            <div className="glass rounded-xl flex items-center px-4 py-2 focus-within:border-primary transition-colors">
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && doSendMessage(input)}
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

      {/* Legal disclaimer */}
      <div className="px-6 py-2 border-t border-border">
        <Disclaimer variant="compact" />
      </div>
    </AppLayout>
  );
};

export default Chat;
