const Disclaimer = ({ variant }: { variant: 'compact' | 'full' }) => {
  if (variant === 'compact') {
    return (
      <div className="flex items-start gap-2 rounded-md bg-amber-950/40 border border-amber-800/50 px-3 py-2 text-xs text-amber-300/80 my-2">
        <span className="shrink-0">⚠️</span>
        <span>For educational purposes only. Not investment advice. Projections are hypothetical and do not guarantee future results.</span>
      </div>
    );
  }
  return (
    <div className="mt-8 mb-4 px-2 border-t border-border pt-6">
      <p className="font-mono text-[10px] text-zinc-500 font-medium uppercase tracking-wider mb-2">Important Disclosures</p>
      <p className="font-mono text-[10px] text-zinc-600 leading-relaxed">
        Arcus is an educational analytics tool. It is not a registered investment advisor with the SEC or FINRA. All analysis — Health Scores, Sharpe ratios, Monte Carlo simulations, VaR estimates, and AI responses — is hypothetical and for educational purposes only. Nothing on this platform constitutes a recommendation to buy, sell, or hold any security. Always consult a qualified financial advisor before making investment decisions. Market data sourced from Yahoo Finance and may be delayed.
      </p>
    </div>
  );
};

export default Disclaimer;
