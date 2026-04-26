import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, ShieldCheck, Activity, TrendingUp, Zap, ChevronRight, ArrowLeft } from 'lucide-react';
import { useNavigate, Link } from 'react-router-dom';
import NewsTicker from '@/components/NewsTicker';

const steps = ['Expected Return', 'Risk Tolerance', 'Sectors'];

const riskProfiles = [
  { icon: Shield, label: 'Conservative', desc: 'Capital preservation first. Minimal drawdowns.' },
  { icon: ShieldCheck, label: 'Moderate', desc: 'Balanced growth with safety nets.' },
  { icon: Activity, label: 'Balanced', desc: 'Equal risk and reward exposure.' },
  { icon: TrendingUp, label: 'Growth', desc: 'Higher returns, more volatility.' },
  { icon: Zap, label: 'Aggressive', desc: 'Maximum growth potential.' },
];

const sectors = ['Technology', 'Healthcare', 'Energy', 'Financials', 'Consumer', 'Real Estate', 'Utilities'];

const STORAGE_KEY = 'arcus-onboarding-state';

const loadState = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return JSON.parse(saved);
  } catch {}
  return null;
};

const Onboarding = () => {
  const saved = loadState();
  const [step, setStep] = useState(saved?.step || 0);
  const [targetReturn, setTargetReturn] = useState(saved?.target_return_idx ?? 1);
  const [riskProfile, setRiskProfile] = useState(saved?.risk_tolerance || '');
  const [selectedSectors, setSelectedSectors] = useState<string[]>(saved?.sectors || []);
  const navigate = useNavigate();

  const returnValues = ['5%', '10%', '15%', '20%+'];

  // Persist state
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      step,
      target_return_idx: targetReturn,
      target_return: [0.05, 0.10, 0.15, 0.20][targetReturn],
      risk_tolerance: riskProfile,
      sectors: selectedSectors,
    }));
  }, [step, targetReturn, riskProfile, selectedSectors]);

  const next = () => {
    if (step < 2) {
      setStep(step + 1);
    } else {
      // Save final state to a permanent key for Dashboard/Results to read
      localStorage.setItem('arcus-investor-dna', JSON.stringify({
        target_return_idx: targetReturn,
        target_return: [0.05, 0.10, 0.15, 0.20][targetReturn],
        risk_tolerance: riskProfile,
        sectors: selectedSectors,
      }));
      localStorage.removeItem(STORAGE_KEY);
      // Clear any stale portfolio draft so Dashboard starts blank
      localStorage.removeItem('arcus-portfolio-draft');
      localStorage.removeItem('arcus-portfolio');
      navigate('/dashboard');
    }
  };

  const prev = () => {
    if (step === 0) navigate('/');
    else setStep(step - 1);
  };

  const toggleSector = (s: string) => {
    setSelectedSectors(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <NewsTicker />
      {/* Progress bar */}
      <div className="h-1 bg-border relative">
        <motion.div
          className="h-full bg-primary"
          animate={{ width: `${((step + 1) / steps.length) * 100}%` }}
          transition={{ type: 'spring', stiffness: 100, damping: 20 }}
        />
      </div>
      <div className="flex justify-center gap-8 py-4 border-b border-border">
        {steps.map((s, i) => (
          <span key={s} className={`font-mono text-[10px] uppercase tracking-widest ${i === step ? 'text-primary' : i < step ? 'text-foreground' : 'text-muted-foreground/40'}`}>{s}</span>
        ))}
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.35 }}
            className="max-w-2xl w-full"
          >
            {step === 0 && (
              <div className="text-center">
                <h2 className="font-display font-bold text-2xl text-foreground">WHAT'S YOUR TARGET RETURN?</h2>
                <p className="text-muted-foreground text-sm mt-2">We'll flag when your portfolio doesn't match your goals.</p>
                <div className="mt-12 relative max-w-md mx-auto">
                  <div className="flex justify-between mb-4">
                    {returnValues.map((v, i) => (
                      <button key={v} onClick={() => setTargetReturn(i)} className={`font-mono text-sm font-medium transition-all ${i === targetReturn ? 'text-primary scale-110' : 'text-muted-foreground'}`}>
                        {v}
                      </button>
                    ))}
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="3"
                    step="1"
                    value={targetReturn}
                    onChange={(e) => setTargetReturn(Number(e.target.value))}
                    className="w-full h-1.5 appearance-none bg-border rounded-full cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:border-4 [&::-webkit-slider-thumb]:border-background [&::-webkit-slider-thumb]:cursor-grab [&::-webkit-slider-thumb]:active:cursor-grabbing [&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:h-5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-primary [&::-moz-range-thumb]:border-4 [&::-moz-range-thumb]:border-background [&::-moz-range-thumb]:cursor-grab"
                  />
                </div>
                <div className="font-mono text-4xl font-bold text-primary mt-8">{returnValues[targetReturn]}<span className="text-lg text-muted-foreground"> / yr</span></div>
              </div>
            )}

            {step === 1 && (
              <div className="text-center">
                <h2 className="font-display font-bold text-2xl text-foreground">HOW DO YOU HANDLE RISK?</h2>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-8">
                  {riskProfiles.map((p) => (
                    <motion.button
                      key={p.label}
                      whileHover={{ y: -2 }}
                      whileTap={{ scale: 0.96 }}
                      onClick={() => setRiskProfile(p.label)}
                      className={`glass rounded-xl p-4 text-center transition-all ${riskProfile === p.label ? 'border-primary/80 bg-primary/8' : ''}`}
                      style={riskProfile === p.label ? { boxShadow: '0 0 0 1.5px hsl(var(--primary))' } : {}}
                    >
                      <p.icon size={24} className="text-primary mx-auto" />
                      <span className="font-display font-bold text-sm text-foreground block mt-2">{p.label}</span>
                      <span className="text-[11px] text-muted-foreground">{p.desc}</span>
                    </motion.button>
                  ))}
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="text-center">
                <h2 className="font-display font-bold text-2xl text-foreground">WHICH SECTORS DO YOU BELIEVE IN?</h2>
                <div className="flex flex-wrap gap-3 justify-center mt-8">
                  {sectors.map((s) => (
                    <motion.button
                      key={s}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.96 }}
                      onClick={() => toggleSector(s)}
                      className={`px-4 py-2 rounded-full font-mono text-xs transition-all ${selectedSectors.includes(s) ? 'bg-primary text-primary-foreground' : 'glass text-muted-foreground hover:text-foreground'}`}
                    >
                      {s}
                    </motion.button>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="flex justify-between px-6 py-6 border-t border-border">
        <button onClick={prev} className="px-6 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-foreground flex items-center gap-1.5">
          <ArrowLeft size={16} className="text-primary" /> Back
        </button>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.96 }}
          onClick={next}
          disabled={step === 1 && !riskProfile}
          className="px-6 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {step === 2 ? 'Finish Setup' : 'Continue'} <ChevronRight size={14} className="inline ml-1" />
        </motion.button>
      </div>
    </div>
  );
};

export default Onboarding;
