const ArcusLogo = ({ size = 28 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
    <circle cx="16" cy="16" r="14" stroke="hsl(var(--primary))" strokeWidth="1.5" opacity="0.3" />
    <ellipse cx="16" cy="16" rx="14" ry="8" stroke="hsl(var(--primary))" strokeWidth="1.5" opacity="0.4" transform="rotate(-20 16 16)" />
    <ellipse cx="16" cy="16" rx="14" ry="6" stroke="hsl(var(--primary))" strokeWidth="1.5" opacity="0.5" transform="rotate(35 16 16)" />
    <path d="M16 2 A14 14 0 0 1 30 16" stroke="hsl(var(--accent-bright))" strokeWidth="2" fill="none" strokeLinecap="round" />
    <circle cx="30" cy="16" r="2.5" fill="hsl(var(--accent-bright))">
      <animate attributeName="opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite" />
    </circle>
  </svg>
);

export default ArcusLogo;
