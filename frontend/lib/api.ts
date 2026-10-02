import { API_BASE } from "./config";
import { getToken, getUser, clearSession } from "./session";
import { isOnline } from "./offline/network";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details: Record<string, unknown> = {}) {
    super(message);
  }
  get isOffline() { return this.code === "offline"; }
}

type Opts = { method?: string; body?: unknown; form?: FormData; auth?: boolean; signal?: AbortSignal; cache?: boolean };

const cacheKey = (path: string) => `${getUser()?.id ?? "anon"}:${path}`;

async function readCache<T>(path: string): Promise<T | undefined> {
  try {
    const { db } = await import("./offline/db");
    return (await db().cache.get(cacheKey(path)))?.data as T | undefined;
  } catch { return undefined; }
}

export async function writeCache(path: string, data: unknown) {
  try {
    const { db } = await import("./offline/db");
    await db().cache.put({ key: cacheKey(path), data, savedAt: Date.now() });
  } catch { /* IndexedDB unavailable: app still works online */ }
}

/** Patch a cached GET response in place (optimistic offline updates). */
export async function patchCache<T>(path: string, fn: (old: T) => T) {
  const old = await readCache<T>(path);
  if (old !== undefined) await writeCache(path, fn(old));
}

/**
 * Thin fetch wrapper: JSON in/out, bearer token, typed errors, never surfaces raw server traces.
 * GET requests are cached on the device; when offline (real or demo mode) they are served from that cache.
 */
export async function api<T>(path: string, opts: Opts = {}): Promise<T> {
  const method = opts.method ?? (opts.body !== undefined || opts.form ? "POST" : "GET");
  const cacheable = method === "GET" && opts.cache !== false && opts.auth !== false;

  if (!isOnline()) {
    if (cacheable) {
      const hit = await readCache<T>(path);
      if (hit !== undefined) return hit;
    }
    throw new ApiError(0, "offline", "No connection to the server.");
  }

  const headers: Record<string, string> = {};
  const token = opts.auth === false ? null : getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(opts.body); }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { method, headers, body, signal: opts.signal });
  } catch {
    if (cacheable) {
      const hit = await readCache<T>(path);
      if (hit !== undefined) return hit;
    }
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
  if (cacheable) await writeCache(path, data);
  return data as T;
}
