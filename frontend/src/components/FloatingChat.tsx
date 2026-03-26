import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, X, SendHorizontal, Zap, User } from 'lucide-react';
import { sendChatMessage } from '@/lib/api';

const quickPrompts = ['PORTFOLIO RISK', 'EXPLAIN SHARPE', 'STRESS TEST'];

// Global event to open chat with a pre-filled message
export const openChatWithMessage = new EventTarget();

const FloatingChat = ({ initialMessage }: { initialMessage?: string }) => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<{ role: 'ai' | 'user'; content: string }[]>([
    { role: 'ai', content: "Hi! I'm Arcus AI. I have context on your portfolio. Ask me anything about your risk, performance, or strategy." },
  ]);
  const [input, setInput] = useState(initialMessage || '');
  const [typing, setTyping] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Listen for external open events
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      setOpen(true);
      if (detail?.message) {
        setInput(detail.message);
        setTimeout(() => {
          doSendMessage(detail.message);
        }, 300);
      }
    };
    openChatWithMessage.addEventListener('open', handler);
    return () => openChatWithMessage.removeEventListener('open', handler);
  }, []);

  const doSendMessage = async (text: string) => {
    if (!text.trim()) return;
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
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
    <>
      {/* Floating button — bottom RIGHT */}
      <AnimatePresence>
        {!open && (
          <motion.button
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            whileHover={{ scale: 1.08 }}
            onClick={() => setOpen(true)}
            className="fixed bottom-6 right-6 z-50 w-[52px] h-[52px] rounded-full bg-primary text-primary-foreground flex items-center justify-center shadow-lg"
            title="Arcus AI"
          >
            <MessageSquare size={22} />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat panel — bottom RIGHT */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            className="fixed bottom-6 right-4 z-50 w-[calc(100vw-2rem)] sm:w-[360px] h-[480px] glass rounded-2xl border border-border flex flex-col overflow-hidden shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <div className="flex items-center gap-2">
                <Zap size={16} className="text-primary" />
                <span className="font-display font-bold text-sm text-foreground">Arcus AI</span>
              </div>
              <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X size={16} />
              </button>
            </div>

            {/* Quick prompts */}
            <div className="flex gap-1.5 px-3 py-2 border-b border-border overflow-x-auto">
              {quickPrompts.map((p) => (
                <button
                  key={p}
                  onClick={() => doSendMessage(p.toLowerCase())}
                  className="font-mono text-[9px] uppercase tracking-wider px-2 py-1 rounded-full glass text-muted-foreground hover:text-primary whitespace-nowrap flex-shrink-0"
                >
                  {p}
                </button>
              ))}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[280px] rounded-lg px-3 py-2 ${msg.role === 'user' ? 'bg-primary/20' : 'glass-elevated'}`}>
                    <div className="flex items-center gap-1.5 mb-1">
                      {msg.role === 'ai' ? <Zap size={10} className="text-primary" /> : <User size={10} className="text-muted-foreground" />}
                      <span className="font-mono text-[8px] uppercase text-muted-foreground">{msg.role === 'ai' ? 'ARCUS AI' : 'YOU'}</span>
                    </div>
                    <p className="text-xs leading-relaxed text-foreground">
                      {msg.content.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
                        part.startsWith('**') && part.endsWith('**')
                          ? <span key={j} className="font-mono font-bold text-primary">{part.slice(2, -2)}</span>
                          : part
                      )}
                    </p>
                  </div>
                </div>
              ))}
              {typing && (
                <div className="flex justify-start">
                  <div className="glass-elevated rounded-lg px-3 py-2 flex items-center gap-1">
                    {[0, 1, 2].map((i) => (
                      <motion.span key={i} className="w-1.5 h-1.5 rounded-full bg-primary" animate={{ scale: [0, 1, 0] }} transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }} />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Input */}
            <div className="p-3 border-t border-border">
              <div className="glass-elevated rounded-lg flex items-center px-3 py-1.5">
                <input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && doSendMessage(input)}
                  placeholder="Ask about your portfolio..."
                  className="flex-1 bg-transparent text-xs text-foreground placeholder:text-muted-foreground/50 outline-none"
                />
                <button onClick={() => doSendMessage(input)} className="text-primary hover:text-accent-bright ml-2">
                  <SendHorizontal size={14} />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default FloatingChat;
