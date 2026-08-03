import { useRemediation } from "../hooks/useRemediation";
import type { Finding, Outcome } from "../types";

const BTN =
  "rounded-lg border border-line bg-surface-panel px-3 py-1.5 text-sm font-medium text-ink hover:border-line-strong disabled:opacity-50";
const BTN_PRIMARY =
  "rounded-lg bg-ink px-3 py-1.5 text-sm font-medium text-surface-panel hover:opacity-90 disabled:opacity-50";

const OUTCOME_LABEL: Record<Outcome, string> = {
  PLANNED: "Planned",
  STARTED: "Remediation started",
  REMEDIATED: "Remediated",
  NOTIFIED: "Flagged for manual review",
  SKIPPED: "Skipped",
  FAILED: "Remediation failed",
};

// Style by outcome — a 2xx response is not necessarily a success (the runbook
// can report FAILED/SKIPPED), so don't paint everything green.
const OUTCOME_CLASS: Record<Outcome, string> = {
  PLANNED: "text-ink",
  STARTED: "text-status-compliant",
  REMEDIATED: "text-status-compliant",
  NOTIFIED: "text-ink",
  SKIPPED: "text-ink-dim",
  FAILED: "text-status-error",
};

/**
 * The corrective loop, from the browser. Preview (dry run) → Apply. The preview
 * is always shown before any mutation, mirroring the backend's `apply` gate.
 */
export function RemediationPanel({ finding }: { finding: Finding }) {
  const rem = useRemediation(finding);
  const working = rem.phase === "working";

  return (
    <div className="rounded-lg border border-line bg-surface-panel p-3">
      <p className="font-mono text-xs uppercase tracking-wider text-ink-faint">Remediation</p>

      {rem.phase === "idle" && (
        <div className="mt-2">
          <p className="text-sm text-ink-dim">
            Preview what the gated remediation would do before applying anything.
          </p>
          <button type="button" onClick={rem.preview} className={`mt-2 ${BTN}`}>
            Preview remediation
          </button>
        </div>
      )}

      {working && <p className="mt-2 text-sm text-ink-dim">Working…</p>}

      {rem.phase === "previewed" && rem.result && (
        <div className="mt-2 space-y-2">
          <p className="text-sm text-ink">{rem.result.summary}</p>
          {/* The exact operation the dry run returned — shown before Apply can
              execute anything. Rendered as text (no dangerouslySetInnerHTML). */}
          <pre className="overflow-x-auto rounded-lg border border-line bg-surface-base p-2 font-mono text-xs text-ink-dim">
            {JSON.stringify(rem.result.plan, null, 2)}
          </pre>
          {rem.result.action === "AUTO_REMEDIATE" ? (
            <div className="flex gap-2">
              <button type="button" onClick={rem.apply} disabled={working} className={BTN_PRIMARY}>
                Apply fix
              </button>
              <button type="button" onClick={rem.reset} className={BTN}>
                Cancel
              </button>
            </div>
          ) : (
            <p className="text-sm text-ink-dim">
              This finding can&apos;t be safely auto-fixed — it&apos;s flagged for manual review.
            </p>
          )}
        </div>
      )}

      {rem.phase === "applied" && rem.result && (
        <div className="mt-2 space-y-1">
          <p className={`text-sm font-medium ${OUTCOME_CLASS[rem.result.outcome]}`}>
            {OUTCOME_LABEL[rem.result.outcome]}
          </p>
          <p className="text-sm text-ink-dim">{rem.result.summary}</p>
          {(rem.result.outcome === "STARTED" || rem.result.outcome === "REMEDIATED") && (
            <p className="text-xs text-ink-faint">Re-scan in a moment to confirm the fix.</p>
          )}
        </div>
      )}

      {rem.phase === "error" && (
        <div className="mt-2">
          <p className="text-sm text-status-error">{rem.error}</p>
          <button type="button" onClick={rem.reset} className={`mt-2 ${BTN}`}>
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
