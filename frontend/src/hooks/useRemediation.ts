import { useState } from "react";

import { ApiError, apiPost } from "../lib/api";
import type { Finding, RemediationResult } from "../types";

export type RemediationPhase = "idle" | "working" | "previewed" | "applied" | "error";

/**
 * Drives the gated remediation of one finding: `preview` does a dry run
 * (apply=false → the plan), `apply` executes it. Two steps on purpose — the
 * preview shows exactly what will happen before anything mutates AWS.
 */
export function useRemediation(finding: Finding) {
  const [phase, setPhase] = useState<RemediationPhase>("idle");
  const [result, setResult] = useState<RemediationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(apply: boolean) {
    setPhase("working");
    setError(null);
    try {
      const r = await apiPost<RemediationResult>("/remediations", {
        check_id: finding.check_id,
        resource_id: finding.resource_id,
        apply,
      });
      setResult(r);
      setPhase(apply ? "applied" : "previewed");
    } catch (e: unknown) {
      setError(e instanceof ApiError ? `${e.status} — ${e.message}` : String(e));
      setPhase("error");
    }
  }

  return {
    phase,
    result,
    error,
    preview: () => run(false),
    apply: () => run(true),
    reset: () => {
      setPhase("idle");
      setResult(null);
      setError(null);
    },
  };
}
