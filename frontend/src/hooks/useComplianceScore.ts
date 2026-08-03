import type { ComplianceScore } from "../types";
import { useApiResource } from "./useApiResource";

/** The account's rolled-up posture (score + counts). Wraps GET /compliance-score. */
export function useComplianceScore() {
  return useApiResource<ComplianceScore>("/compliance-score");
}
