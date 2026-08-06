/**
 * Tiny typed API client. One place adds the base URL + the X-API-Key header and
 * normalizes errors, so hooks/components never touch fetch directly.
 */

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
// Only the local dev build reads the key; in a production build this branch is
// dead code (import.meta.env.DEV is statically false) and is tree-shaken out, so
// the browser bundle can never carry a secret. In production CloudFront injects
// X-API-Key server-side.
const KEY = import.meta.env.DEV ? (import.meta.env.VITE_API_KEY ?? "") : "";

/** Carries the HTTP status so the UI can distinguish 401 (auth) from 503 (down). */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  // Sent only by the local dev build; in production the header is absent and
  // CloudFront adds it, so no secret ships to the browser.
  if (KEY) headers["X-API-Key"] = KEY;

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    // Surface the API's `detail` message when present; fall back to the status.
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* error body wasn't JSON — keep the status text */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const apiGet = <T>(path: string) => request<T>(path);

export const apiPost = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

/**
 * A safe, user-facing message for an error. Never surfaces the raw backend
 * `detail` in the UI — boto3/AWS messages can carry account ids, ARNs, or
 * resource names, so we map by status instead of echoing server text.
 */
export function safeErrorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 401 || e.status === 403) return "Not authorized.";
    if (e.status === 404) return "That item is no longer available.";
    if (e.status === 422) return "The request was invalid.";
    if (e.status === 503) return "The service is temporarily unavailable.";
    if (e.status >= 500) return "The server encountered an error.";
    return "The request failed.";
  }
  return "Couldn't reach the API.";
}

/**
 * Is this "the backend is unreachable" (spun down, gateway error, or a network
 * failure) rather than a real application error? Drives the graceful "backend
 * offline" UI instead of a scary generic error.
 */
export function isOfflineError(e: unknown): boolean {
  if (e instanceof ApiError) return e.status === 502 || e.status === 503 || e.status === 504;
  return true; // non-ApiError = fetch/network failure = couldn't reach the backend
}
