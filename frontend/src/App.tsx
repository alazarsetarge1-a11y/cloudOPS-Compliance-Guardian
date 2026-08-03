import { FindingsList } from "./components/FindingsList";
import { PostureHeader } from "./components/PostureHeader";
import { useComplianceScore } from "./hooks/useComplianceScore";
import { useFindings } from "./hooks/useFindings";

/**
 * App shell + composition root: wires the data hooks and hands their state to
 * presentational views. The views themselves never fetch.
 */
export function App() {
  const score = useComplianceScore();
  const findings = useFindings();
  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-line bg-surface-panel">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-3">
            <span
              aria-hidden
              className="grid h-9 w-9 place-items-center rounded-lg bg-accent-wash text-accent"
            >
              <ShieldGlyph />
            </span>
            <div>
              <h1 className="text-sm font-semibold tracking-tight text-ink">
                Cloud Compliance Guardian
              </h1>
              <p className="font-mono text-xs text-ink-faint">
                preventive · detective · corrective
              </p>
            </div>
          </div>
          <span className="rounded-full border border-line px-3 py-1 font-mono text-xs text-ink-dim">
            member account · us-east-1
          </span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 space-y-6 px-6 py-8">
        <PostureHeader
          score={score.data}
          loading={score.loading}
          error={score.error}
          onRetry={score.refetch}
        />
        <FindingsList
          findings={findings.data}
          loading={findings.loading}
          error={findings.error}
          onRetry={findings.refetch}
        />
      </main>
    </div>
  );
}

function ShieldGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 2.5 5 5.2v5.6c0 4.4 3 8.5 7 10.7 4-2.2 7-6.3 7-10.7V5.2L12 2.5Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="m9 12 2 2 4-4.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
