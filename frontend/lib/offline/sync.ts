"use client";
/*
  Offline sync queue.

  Local data ──▶ queue (IndexedDB) ──▶ POST /sync (JSON ops, idempotent on op_id)
                                   └─▶ POST /evidence (files, idempotent on client_op_id)
  Server answers per op: applied | duplicate | conflict | rejected | failed.

  - applied / duplicate / conflict / rejected → removed from the queue (server has decided; conflicts are kept
    server-side for review, rejected ops are never retried).
  - network error → op stays, retried with exponential backoff (2s, 4s, 8s … max 60s), up to MAX_ATTEMPTS, then 🔴 failed.
  - failed ops can be retried manually from the sync panel.
*/
import { API_BASE } from "../config";
import { getToken } from "../session";
import { db, type PendingEvidence, type QueuedOp } from "./db";
import { isOnline, subscribeNetwork } from "./network";

export const MAX_ATTEMPTS = 8;
const CLIENT_KEY = "rpl.clientId";

export type SyncCounts = { applied: number; duplicate: number; conflict: number; rejected: number; failed: number };
export interface SyncResult { at: string; records: SyncCounts; evidenceUploaded: number; evidenceFailed: number; networkError: boolean }
export interface SyncState { pending: number; failed: number; syncing: boolean; last: SyncResult | null; items: QueuedOp[] }

let state: SyncState = { pending: 0, failed: 0, syncing: false, last: null, items: [] };
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());
export const getSyncState = () => state;
export function subscribeSync(fn: () => void) { listeners.add(fn); return () => { listeners.delete(fn); }; }

export function clientId(): string {
  try {
    let id = localStorage.getItem(CLIENT_KEY);
    if (!id) { id = `web-${crypto.randomUUID()}`; localStorage.setItem(CLIENT_KEY, id); }
    return id;
  } catch { return "web-unknown"; }
}

export async function refreshState() {
  try {
    const items = await db().queue.orderBy("seq").toArray();
    state = { ...state, items, pending: items.filter((i) => i.status === "pending").length, failed: items.filter((i) => i.status === "failed").length };
  } catch { /* IndexedDB unavailable */ }
  emit();
}

// Monotonic sequence: microsecond-scaled clock, bumped when two ops land in the same millisecond.
let lastSeq = 0;
function nextSeq() {
  lastSeq = Math.max(lastSeq + 1, Date.now() * 1000);
  return lastSeq;
}

const backoff = (attempts: number) => Math.min(60_000, 2_000 * 2 ** Math.max(0, attempts - 1));

export async function enqueue(op: Omit<QueuedOp, "attempts" | "nextAttemptAt" | "status" | "createdAt" | "client_ts" | "op_id" | "seq"> & { op_id?: string }, file?: Omit<PendingEvidence, "op_id" | "createdAt">) {
  const op_id = op.op_id ?? crypto.randomUUID();
  const row: QueuedOp = { ...op, op_id, client_ts: new Date().toISOString(), attempts: 0, nextAttemptAt: 0, status: "pending", createdAt: Date.now(), seq: nextSeq() };
  await db().transaction("rw", db().queue, db().evidence, async () => {
    await db().queue.put(row);
    if (file) await db().evidence.put({ ...file, op_id, createdAt: row.createdAt });
  });
  await refreshState();
  return row;
}

async function markRetry(ops: QueuedOp[], error: string) {
  for (const o of ops) {
    const attempts = o.attempts + 1;
    await db().queue.update(o.op_id, { attempts, lastError: error, nextAttemptAt: Date.now() + backoff(attempts), status: attempts >= MAX_ATTEMPTS ? "failed" : "pending" });
  }
}

let flushing: Promise<SyncResult | null> | null = null;

/** Send everything that is due. `force` ignores backoff timers (manual "Reconnect & Sync"). */
export function flush(force = false): Promise<SyncResult | null> {
  if (flushing) return flushing;
  flushing = doFlush(force).finally(() => { flushing = null; });
  return flushing;
}

async function doFlush(force: boolean): Promise<SyncResult | null> {
  if (!isOnline() || !getToken()) return null;
  const now = Date.now();
  const due = (await db().queue.orderBy("seq").toArray()).filter((o) => o.status === "pending" && (force || o.nextAttemptAt <= now));
  if (!due.length) return null;
  state = { ...state, syncing: true }; emit();
  const records: SyncCounts = { applied: 0, duplicate: 0, conflict: 0, rejected: 0, failed: 0 };
  let evidenceUploaded = 0, evidenceFailed = 0, networkError = false;
  const auth = { Authorization: `Bearer ${getToken()}` };

  // 1) JSON operations, one batch, in creation order
  const json = due.filter((o) => o.kind === "json");
  if (json.length) {
    try {
      const res = await fetch(`${API_BASE}/sync`, {
        method: "POST", headers: { ...auth, "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId(), ops: json.map(({ op_id, entity, op, payload, client_ts }) => ({ op_id, entity, op, payload, client_ts })) }),
      });
      if (!res.ok) throw new Error(`sync ${res.status}`);
      const out: { results: { op_id: string; status: keyof SyncCounts; detail: string | null }[] } = await res.json();
      for (const r of out.results) {
        records[r.status] += 1;
        if (r.status === "failed") await db().queue.update(r.op_id, { status: "failed", lastError: r.detail ?? "rejected by server validation" });
        else await db().queue.delete(r.op_id);
      }
    } catch (e) {
      networkError = true;
      await markRetry(json, e instanceof Error ? e.message : "network");
    }
  }

  // 2) Evidence files (after their JSON context exists on the server)
  for (const o of due.filter((x) => x.kind === "evidence")) {
    const f = await db().evidence.get(o.op_id);
    if (!f) { await db().queue.delete(o.op_id); continue; }
    const form = new FormData();
    form.append("file", new File([f.blob], f.name, { type: f.mime }));
    for (const [k, v] of Object.entries(f.fields)) if (v) form.append(k, v);
    form.append("client_op_id", o.op_id);
    form.append("captured_offline", "true");
    try {
      const res = await fetch(`${API_BASE}/evidence`, { method: "POST", headers: auth, body: form });
      if (res.ok) {
        evidenceUploaded += 1;
        await db().transaction("rw", db().queue, db().evidence, async () => { await db().queue.delete(o.op_id); await db().evidence.delete(o.op_id); });
      } else if (res.status >= 400 && res.status < 500 && res.status !== 401 && res.status !== 429) {
        evidenceFailed += 1; // invalid file / unknown criterion: retrying cannot help
        const j = await res.json().catch(() => null);
        await db().queue.update(o.op_id, { status: "failed", lastError: j?.error?.message ?? `upload rejected (${res.status})` });
      } else {
        await markRetry([o], `upload ${res.status}`);
      }
    } catch {
      networkError = true;
      await markRetry([o], "network");
    }
  }

  const last: SyncResult = { at: new Date().toISOString(), records, evidenceUploaded, evidenceFailed, networkError };
  state = { ...state, syncing: false, last };
  await refreshState();
  if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent("rpl:synced", { detail: last }));
  return last;
}

export async function retryFailed() {
  const failed = await db().queue.where("status").equals("failed").toArray();
  for (const f of failed) await db().queue.update(f.op_id, { status: "pending", attempts: 0, nextAttemptAt: 0 });
  await refreshState();
  return flush(true);
}

/** Start background syncing: on reconnect, on demo-mode switch back to online, and every 15 s while ops are due. */
let started = false;
export function startSyncLoop() {
  if (started || typeof window === "undefined") return;
  started = true;
  refreshState();
  subscribeNetwork(() => { if (isOnline()) flush(); });
  setInterval(() => { if (isOnline() && state.pending > 0) flush(); }, 15_000);
}
