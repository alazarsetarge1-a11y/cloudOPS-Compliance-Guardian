import type { ComplianceScore, Severity } from "../types";
import { SEVERITY_ORDER } from "../types";

interface PostureHeaderProps {
  score: ComplianceScore | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

// Severity is paired with a label + a shape marker — never color alone (≈1 in 12
// men has a color-vision deficiency; red/green coding is the failure case).
const SEV_META: Record<Severity, { label: string; dot: string }> = {
  CRITICAL: { label: "Critical", dot: "bg-severity-critical" },
  HIGH: { label: "High", dot: "bg-severity-high" },
  MEDIUM: { label: "Medium", dot: "bg-severity-medium" },
  LOW: { label: "Low", dot: "bg-severity-low" },
};

const PANEL = "rounded-2xl border border-line bg-surface-panel p-6 shadow-sm";

export function PostureHeader({ score, loading, error, onRetry }: PostureHeaderProps) {
  if (loading) return <PostureSkeleton />;
  if (error) return <PostureError message={error} onRetry={onRetry} />;
  if (!score || score.total_findings === 0) return <PostureEmpty />;

  const sev = score.non_compliant_by_severity;
  const onFire = sev.CRITICAL + sev.HIGH;
  const nonCompliant = score.by_status.NON_COMPLIANT;
  const compliant = score.by_status.COMPLIANT;
  const evaluable = compliant + nonCompliant;

  return (
    <section aria-label="Compliance posture" className={PANEL}>
      <div className="flex flex-wrap items-start justify-between gap-8">
        {/* The dominant question: is anything on fire? */}
        <div className="min-w-[16rem]">
          {onFire > 0 ? (
            <>
              <p className="font-mono text-xs uppercase tracking-wider text-severity-critical">
                Action needed
              </p>
              <p className="mt-1 text-4xl font-semibold tracking-tight text-ink">
                {onFire} <span className="text-xl font-normal text-ink-dim">critical + high</span>
              </p>
              <p className="mt-1 text-sm text-ink-dim">exposed right now — remediate these first</p>
            </>
          ) : (
            <>
              <p className="font-mono text-xs uppercase tracking-wider text-status-compliant">
                All clear
              </p>
              <p className="mt-1 text-4xl font-semibold tracking-tight text-ink">
                No critical or high findings
              </p>
              <p className="mt-1 text-sm text-ink-dim">nothing exposed on sensitive controls</p>
            </>
          )}
        </div>

        {/* Secondary: the headline score */}
        <div className="text-right">
          <p className="font-mono text-xs uppercase tracking-wider text-ink-faint">Compliance score</p>
          <p className="mt-1 text-5xl font-semibold tabular-nums text-ink">
            {score.compliance_score_pct ?? "—"}
            <span className="text-2xl text-ink-dim">%</span>
          </p>
          <p className="mt-1 text-sm text-ink-dim">
            {compliant} of {evaluable} resources compliant
          </p>
        </div>
      </div>

      {/* Severity breakdown of the outstanding findings */}
      <div className="mt-6 flex flex-wrap gap-2 border-t border-line pt-4">
        {SEVERITY_ORDER.map((s) => (
          <span
            key={s}
            className="inline-flex items-center gap-2 rounded-lg border border-line bg-surface-base px-3 py-1.5 text-sm"
          >
            <span aria-hidden className={`h-2.5 w-2.5 rounded-full ${SEV_META[s].dot}`} />
            <span className="text-ink-dim">{SEV_META[s].label}</span>
            <span className="font-mono font-semibold tabular-nums text-ink">{sev[s]}</span>
          </span>
        ))}
      </div>
    </section>
  );
}

function PostureSkeleton() {
  return (
    <section aria-busy="true" aria-label="Loading compliance posture" className={PANEL}>
      <div className="flex flex-wrap justify-between gap-8">
        <div className="space-y-3">
          <div className="h-3 w-24 rounded bg-surface-base motion-safe:animate-pulse" />
          <div className="h-9 w-64 rounded bg-surface-base motion-safe:animate-pulse" />
        </div>
        <div className="space-y-3">
          <div className="h-3 w-24 rounded bg-surface-base motion-safe:animate-pulse" />
          <div className="h-12 w-28 rounded bg-surface-base motion-safe:animate-pulse" />
        </div>
      </div>
      <div className="mt-6 flex gap-2 border-t border-line pt-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-8 w-24 rounded-lg bg-surface-base motion-safe:animate-pulse" />
        ))}
      </div>
    </section>
  );
}

function PostureError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <section aria-label="Compliance posture unavailable" className={PANEL}>
      <p className="font-mono text-xs uppercase tracking-wider text-status-error">
        Couldn&apos;t load posture
      </p>
      <p className="mt-1 text-ink">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="mt-4 rounded-lg border border-line bg-surface-base px-3 py-1.5 text-sm font-medium text-ink hover:border-line-strong"
      >
        Retry
      </button>
    </section>
  );
}

function PostureEmpty() {
  return (
    <section aria-label="No compliance findings" className={PANEL}>
      <p className="font-mono text-xs uppercase tracking-wider text-ink-faint">No data yet</p>
      <p className="mt-1 text-ink">No resources have been evaluated.</p>
      <p className="mt-1 text-sm text-ink-dim">
        Findings appear here after the first detective scan of the account.
      </p>
    </section>
  );
}
