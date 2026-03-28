import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, Lock } from 'lucide-react';
import { toast } from 'sonner';
import AppLayout from '@/components/AppLayout';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';

const Pricing = () => {
  const navigate = useNavigate();
  const [isAnnual, setIsAnnual] = useState(false);
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const [email, setEmail] = useState('');

  const handleWaitlistSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !email.includes('@')) {
      toast.error('Please enter a valid email address.');
      return;
    }

    try {
      const existingRaw = localStorage.getItem('arcus-waitlist');
      const existing = existingRaw ? JSON.parse(existingRaw) : [];
      existing.push({ email, joinedAt: new Date().toISOString() });
      localStorage.setItem('arcus-waitlist', JSON.stringify(existing));
      toast.success("You're on the list! We'll email you at launch.");
      setWaitlistOpen(false);
      setEmail('');
    } catch {
      toast.error('Failed to join waitlist. Try again.');
    }
  };

  return (
    <AppLayout title="Pricing">
      <div className="max-w-4xl mx-auto px-6 py-16 text-zinc-100">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-extrabold mb-4 font-display">Unlock Your Full Portfolio Edge</h1>
          <p className="text-xl text-zinc-400">Professional-grade analytics. Free to start.</p>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12">
          {/* FREE Card */}
          <div className="rounded-2xl border border-zinc-700 bg-zinc-900 p-6 flex flex-col">
            <div className="mb-6">
              <span className="inline-block px-3 py-1 bg-zinc-800 text-zinc-300 rounded-full text-sm font-semibold mb-4">Free</span>
              <div className="text-4xl font-bold mb-2">$0 <span className="text-lg font-normal text-zinc-500">/ forever</span></div>
            </div>

            <div className="flex-1 space-y-4 mb-8">
              <ul className="space-y-3">
                {[
                  'Up to 5 holdings',
                  'Health Score & risk metrics',
                  'Monte Carlo simulation (300 paths)',
                  '4 historical stress tests',
                  'Basic PDF export',
                  '10 AI messages per day',
                ].map((feature, i) => (
                  <li key={i} className="flex items-start gap-3 text-zinc-300 text-sm">
                    <Check size={16} className="text-zinc-500 mt-0.5 shrink-0" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <div className="pt-4 border-t border-zinc-800">
                <ul className="space-y-3">
                  {[
                    'Unlimited holdings',
                    'Efficient Frontier optimization',
                    'Tax-loss harvesting analyzer',
                    'Robinhood sync',
                    'Portfolio alerts',
                    'Analysis history'
                  ].map((feature, i) => (
                    <li key={i} className="flex items-start gap-3 text-zinc-600 text-sm">
                      <Lock size={16} className="mt-0.5 shrink-0" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <button
              onClick={() => navigate('/dashboard')}
              className="w-full py-3 rounded-xl border border-zinc-600 text-white hover:border-zinc-400 hover:bg-zinc-800 transition-colors font-semibold"
            >
              Get Started Free
            </button>
          </div>

          {/* PREMIUM Card */}
          <div className="rounded-2xl border-2 border-green-500 bg-zinc-900 p-6 flex flex-col relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-green-500 text-black text-xs font-bold px-3 py-1 rounded-full whitespace-nowrap">
              Most Popular
            </div>

            <div className="mb-6">
              <div className="text-green-500 font-bold mb-4 tracking-wide">Premium ✦</div>
              <div className="flex items-center gap-4 mb-4">
                <span className={`text-sm ${!isAnnual ? 'text-white' : 'text-zinc-500'}`}>Monthly</span>
                <Switch
                  checked={isAnnual}
                  onCheckedChange={setIsAnnual}
                />
                <span className={`text-sm ${isAnnual ? 'text-white' : 'text-zinc-500'}`}>Annual</span>
              </div>
              <div className="min-h-[64px]">
                {isAnnual ? (
                  <>
                    <div className="text-4xl font-bold mb-1">$7.99 <span className="text-lg font-normal text-zinc-500">/month</span></div>
                    <div className="text-sm text-green-400 font-medium">Billed annually (save 20%)</div>
                  </>
                ) : (
                  <div className="text-4xl font-bold mb-1">$9.99 <span className="text-lg font-normal text-zinc-500">/month</span></div>
                )}
              </div>
            </div>

            <div className="flex-1 space-y-4 mb-8">
              <div className="text-sm font-semibold text-zinc-200">Everything in Free, plus:</div>
              <ul className="space-y-3">
                {[
                  'Unlimited holdings',
                  'Efficient Frontier optimization',
                  'Tax-loss harvesting analyzer',
                  'Robinhood sync',
                  'Portfolio alerts',
                  'Analysis history'
                ].map((feature, i) => (
                  <li key={i} className="flex items-start gap-3 text-zinc-200 text-sm">
                    <Check size={16} className="text-green-400 mt-0.5 shrink-0" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>

            <button
              onClick={() => setWaitlistOpen(true)}
              className="w-full py-3 rounded-xl bg-green-500 hover:bg-green-400 text-black font-bold transition-colors"
            >
              Upgrade to Premium
            </button>
            <div className="text-center text-xs text-zinc-500 mt-4">
              Cancel anytime · No hidden fees · Billed via Stripe
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-16 text-center text-zinc-600 text-xs">
          Arcus is an analytics platform, not a licensed investment advisor.
        </div>
      </div>

      {/* Waitlist Dialog */}
      <Dialog open={waitlistOpen} onOpenChange={setWaitlistOpen}>
        <DialogContent className="sm:max-w-md bg-zinc-950 border border-zinc-800 text-zinc-100">
          <DialogHeader>
            <DialogTitle className="text-xl font-display font-bold">🚀 Premium Launching Soon</DialogTitle>
            <DialogDescription className="text-zinc-400">
              Join the waitlist and get 3 months free Premium at launch.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleWaitlistSubmit} className="space-y-4 mt-4">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-green-500 focus:ring-1 focus:ring-green-500 transition-colors"
              required
            />
            <button
              type="submit"
              className="w-full bg-green-500 hover:bg-green-400 text-black font-bold py-3 rounded-lg transition-colors"
            >
              Join Waitlist
            </button>
          </form>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
};

export default Pricing;
