const PANEL = "rounded-2xl border border-line bg-surface-panel p-6 shadow-sm";

/**
 * Shown when the scanning backend is unreachable. This is a deliberate cost
 * decision (the ephemeral compute is torn down between demos), so it reads as an
 * informational state — accent, not alarm — rather than a failure.
 */
export function BackendOffline({ onRetry }: { onRetry: () => void }) {
  return (
    <section aria-label="Backend offline" className={PANEL}>
      <div className="flex items-start gap-4">
        <span
          aria-hidden
          className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-accent-wash text-accent"
        >
          <PowerGlyph />
        </span>
        <div className="min-w-0">
          <p className="font-mono text-xs uppercase tracking-wider text-ink-faint">Backend offline</p>
          <p className="mt-1 text-lg font-semibold tracking-tight text-ink">
            The compliance API is spun down to control cost
          </p>
          <p className="mt-1 max-w-prose text-sm text-ink-dim">
            The dashboard is live, but the scanning backend (ALB + Fargate) is torn down between
            demos to keep it near $0. Findings and the compliance score populate once it's brought
            back up.
          </p>
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 rounded-lg border border-line bg-surface-base px-3 py-1.5 text-sm font-medium text-ink hover:border-line-strong"
          >
            Retry
          </button>
        </div>
      </div>
    </section>
  );
}

function PowerGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 3v9"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M7.5 6.7a7 7 0 1 0 9 0"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
