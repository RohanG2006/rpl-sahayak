import Dexie, { type Table } from "dexie";

/** Cached GET response (per signed-in user) so screens render without network. */
export interface CacheRow { key: string; data: unknown; savedAt: number }

/** One queued JSON operation for POST /sync (mirrors backend app/api/routes/sync.py). */
export interface QueuedOp {
  op_id: string; entity: string; op: string; payload: Record<string, unknown>; client_ts: string;
  kind: "json" | "evidence"; attempts: number; nextAttemptAt: number; status: "pending" | "failed"; lastError?: string; createdAt: number;
  seq: number; // strictly increasing; ops created in the same millisecond still sync in creation order
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
    // v2: order by a monotonic sequence instead of createdAt (same-millisecond ops were ordered by random op_id)
    this.version(2).stores({ queue: "op_id, status, seq, createdAt" }).upgrade((tx) =>
      tx.table("queue").toCollection().modify((op: QueuedOp) => { op.seq = op.createdAt * 1000; }));
  }
}

let _db: OfflineDB | null = null;
export function db(): OfflineDB {
  if (!_db) _db = new OfflineDB();
  return _db;
}
