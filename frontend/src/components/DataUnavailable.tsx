/**
 * Shared empty state for any panel whose data could not be loaded.
 *
 * Arcus must never render a substituted or approximated figure where a measured
 * one belongs — a plausible-looking wrong number is worse than a blank in a
 * financial product. Every chart and metric block on the Results page renders
 * this instead of sample data when the analytics backend is unreachable.
 */
const DataUnavailable = ({
  label,
  detail = 'Could not reach the analytics service. Try again in a few minutes.',
  height = 180,
}: {
  label?: string;
  detail?: string;
  height?: number;
}) => (
  <div
    data-testid="data-unavailable"
    className="flex flex-col items-center justify-center text-center px-4"
    style={{ minHeight: height }}
  >
    <div className="font-mono text-xs text-muted-foreground">
      {label ? `${label} unavailable` : 'Data unavailable'}
    </div>
    <div className="font-mono text-[10px] text-muted-foreground/70 mt-2 max-w-[42ch]">{detail}</div>
  </div>
);

export default DataUnavailable;
