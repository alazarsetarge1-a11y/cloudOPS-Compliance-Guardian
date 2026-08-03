import type { Finding } from "../types";
import { useApiResource } from "./useApiResource";

/**
 * All current findings. We fetch the full set once and filter/sort in the
 * browser — each /findings call triggers a full multi-region AWS scan (slow), so
 * re-fetching per filter change would be a poor trade. Client-side filtering is
 * the right call while the result set is small.
 */
export function useFindings() {
  return useApiResource<Finding[]>("/findings");
}
