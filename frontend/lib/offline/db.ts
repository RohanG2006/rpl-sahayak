import Dexie, { type Table } from "dexie";

/** Cached GET response (per signed-in user) so screens render without network. */
export interface CacheRow { key: string; data: unknown; savedAt: number }

/** One queued JSON operation for POST /sync (mirrors backend app/api/routes/sync.py). */
export interface QueuedOp {
  op_id: string; entity: string; op: string; payload: Record<string, unknown>; client_ts: string;
  kind: "json" | "evidence"; attempts: number; nextAttemptAt: number; status: "pending" | "failed"; lastError?: string; createdAt: number;
  label: string; // human-readable, shown in the sync panel
}

/** Evidence captured offline: the file itself waits here until upload. */
export interface PendingEvidence {
  op_id: string; blob: Blob; name: string; mime: string;
  fields: Record<string, string>; // worker_id, plan_id, task_code, criterion_code, purpose, doc_type, caption
  createdAt: number;
}

class OfflineDB extends Dexie {
  cache!: Table<CacheRow, string>;
  queue!: Table<QueuedOp, string>;
  evidence!: Table<PendingEvidence, string>;
  constructor() {
    super("rpl-sahayak");
    this.version(1).stores({ cache: "key", queue: "op_id, status, createdAt", evidence: "op_id" });
  }
}

let _db: OfflineDB | null = null;
export function db(): OfflineDB {
  if (!_db) _db = new OfflineDB();
  return _db;
}
