import { beforeEach, describe, expect, it, vi } from "vitest";

// Controlled network + session for the sync engine
let online = false;
vi.mock("@/lib/offline/network", () => ({ isOnline: () => online, subscribeNetwork: () => () => {}, demoOffline: () => !online }));
vi.mock("@/lib/session", () => ({ getToken: () => "test-token" }));

import { db } from "@/lib/offline/db";
import { enqueue, flush, getSyncState, MAX_ATTEMPTS } from "@/lib/offline/sync";

const ok = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

beforeEach(async () => {
  online = false;
  await db().queue.clear();
  await db().evidence.clear();
  vi.restoreAllMocks();
});

const jsonOp = (label: string) => ({ kind: "json" as const, entity: "worker_profile", op: "update", payload: { locality: label }, label });

describe("offline sync queue", () => {
  it("queues while offline and does not send", async () => {
    const f = vi.spyOn(globalThis, "fetch");
    await enqueue(jsonOp("a"));
    await enqueue(jsonOp("b"));
    expect(getSyncState().pending).toBe(2);
    expect(await flush(true)).toBeNull();
    expect(f).not.toHaveBeenCalled();
  });

  it("sends a batch in order when back online and clears applied/duplicate ops", async () => {
    const a = await enqueue(jsonOp("a"));
    const b = await enqueue(jsonOp("b"));
    online = true;
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(ok({ results: [{ op_id: a.op_id, status: "applied", detail: null }, { op_id: b.op_id, status: "duplicate", detail: "already applied" }] }));
    const r = await flush(true);
    const sent = JSON.parse(String(f.mock.calls[0][1]!.body));
    expect(sent.ops.map((o: { op_id: string }) => o.op_id)).toEqual([a.op_id, b.op_id]);
    expect(r!.records.applied).toBe(1);
    expect(r!.records.duplicate).toBe(1);
    expect(await db().queue.count()).toBe(0);
    expect(getSyncState().pending).toBe(0);
  });

  it("keeps ops on network error with backoff, then marks failed after max attempts", async () => {
    const a = await enqueue(jsonOp("a"));
    online = true;
    const f = vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    const r = await flush(true);
    expect(r!.networkError).toBe(true);
    let row = await db().queue.get(a.op_id);
    expect(row!.attempts).toBe(1);
    expect(row!.nextAttemptAt).toBeGreaterThan(Date.now());
    await flush(false); // not due yet → no new request
    expect(f).toHaveBeenCalledTimes(1);
    for (let i = 1; i < MAX_ATTEMPTS; i++) await flush(true);
    row = await db().queue.get(a.op_id);
    expect(row!.status).toBe("failed");
    expect(getSyncState().failed).toBe(1);
  });

  it("marks server-rejected validation failures as failed (not retried)", async () => {
    const a = await enqueue(jsonOp("bad"));
    online = true;
    vi.spyOn(globalThis, "fetch").mockResolvedValue(ok({ results: [{ op_id: a.op_id, status: "failed", detail: "Input should be greater than or equal to 14" }] }));
    const r = await flush(true);
    expect(r!.records.failed).toBe(1);
    expect((await db().queue.get(a.op_id))!.status).toBe("failed");
  });

  it("uploads offline evidence with its op id; invalid files fail without retry", async () => {
    const good = await enqueue({ kind: "evidence", entity: "evidence", op: "upload", payload: {}, label: "photo" },
      { blob: new Blob(["x"], { type: "image/png" }), name: "p.png", mime: "image/png", fields: { worker_id: "w1", plan_id: "p1", purpose: "assessment" } });
    const bad = await enqueue({ kind: "evidence", entity: "evidence", op: "upload", payload: {}, label: "bad" },
      { blob: new Blob(["MZ"], { type: "image/jpeg" }), name: "x.jpg", mime: "image/jpeg", fields: { worker_id: "w1", purpose: "assessment" } });
    online = true;
    const f = vi.spyOn(globalThis, "fetch").mockImplementation(async (_url, init) => {
      const fd = init!.body as FormData;
      return fd.get("client_op_id") === good.op_id ? ok({ id: "e1" }, 201) : ok({ error: { code: "invalid_evidence", message: "Unsupported file." } }, 415);
    });
    const r = await flush(true);
    expect(r!.evidenceUploaded).toBe(1);
    expect(r!.evidenceFailed).toBe(1);
    const sentGood = f.mock.calls.map((c) => c[1]!.body as FormData).find((fd) => fd.get("client_op_id") === good.op_id)!;
    expect(sentGood.get("captured_offline")).toBe("true");
    expect(await db().evidence.get(good.op_id)).toBeUndefined();
    expect((await db().queue.get(bad.op_id))!.status).toBe("failed");
  });

  it("keeps creation order for ops queued in the same millisecond (regression)", async () => {
    const made = [];
    for (let i = 0; i < 25; i++) made.push((await enqueue(jsonOp(`op${i}`))).op_id);
    online = true;
    const f = vi.spyOn(globalThis, "fetch").mockImplementation(async (_u, init) => {
      const ops = JSON.parse(String(init!.body)).ops as { op_id: string }[];
      return ok({ results: ops.map((o) => ({ op_id: o.op_id, status: "applied", detail: null })) });
    });
    await flush(true);
    const sent = JSON.parse(String(f.mock.calls[0][1]!.body)).ops.map((o: { op_id: string }) => o.op_id);
    expect(sent).toEqual(made);
  });
});
