import { API_BASE } from "./config";
import { getToken, clearSession } from "./session";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details: Record<string, unknown> = {}) {
    super(message);
  }
  get isOffline() { return this.code === "offline"; }
}

type Opts = { method?: string; body?: unknown; form?: FormData; auth?: boolean; signal?: AbortSignal };

/** Thin fetch wrapper: JSON in/out, bearer token, typed errors. Never surfaces raw server traces. */
export async function api<T>(path: string, opts: Opts = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = opts.auth === false ? null : getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(opts.body); }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { method: opts.method ?? (body ? "POST" : "GET"), headers, body, signal: opts.signal });
  } catch {
    throw new ApiError(0, "offline", "No connection to the server.");
  }
  if (res.status === 204) return undefined as T;
  let data: unknown = null;
  try { data = await res.json(); } catch { /* non-JSON */ }
  if (!res.ok) {
    const err = (data as { error?: { code: string; message: string; details?: Record<string, unknown> } })?.error;
    if (res.status === 401 && token) clearSession(err?.code === "session_expired" ? "expired" : "invalid");
    throw new ApiError(res.status, err?.code ?? "http_error", err?.message ?? "Request failed.", err?.details ?? {});
  }
  return data as T;
}
