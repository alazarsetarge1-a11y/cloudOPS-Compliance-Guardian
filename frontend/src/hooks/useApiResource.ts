import { useCallback, useEffect, useState } from "react";

import { apiGet, isOfflineError, safeErrorMessage } from "../lib/api";

/** The states every data view needs, in one object. `data` is null until
 * loaded; `loading` starts true; `error` holds a message; `offline` marks a
 * backend-unreachable error; `refetch` retries. */
export interface AsyncResource<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  /** True when `error` is a backend-unreachable condition (drives the offline UI). */
  offline: boolean;
  refetch: () => void;
}

/**
 * Fetch a GET resource and track its lifecycle. Keyed by `path` (a stable
 * string), so passing it inline doesn't cause a refetch loop. `refetch` bumps an
 * internal nonce to re-run the effect; a cancel flag prevents a late response
 * from updating an unmounted component.
 */
export function useApiResource<T>(path: string): AsyncResource<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setOffline(false);
    apiGet<T>(path)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(safeErrorMessage(e));
        setOffline(isOfflineError(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [path, nonce]);

  const refetch = useCallback(() => setNonce((n) => n + 1), []);
  return { data, loading, error, offline, refetch };
}
