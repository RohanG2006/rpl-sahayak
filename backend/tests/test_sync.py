"""Phase 10 (server side): offline sync idempotency, conflict rules, server-owned rejection, partial failure."""
import uuid
from datetime import datetime, timedelta, timezone

from tests.flows import started_plan

uid = lambda: str(uuid.uuid4())


def test_sync_applies_once_and_replays_as_duplicate(client):
    p, wid, h, _ = started_plan(client)
    ops = [
        {"op_id": uid(), "entity": "worker_profile", "op": "update", "payload": {"locality": "Danapur"}, "client_ts": datetime.now(timezone.utc).isoformat()},
        {"op_id": uid(), "entity": "worker_experience", "op": "create", "payload": {"raw_text": "Offline note: I also do earthing work.", "language": "en"}},
        {"op_id": uid(), "entity": "task_progress", "op": "update", "payload": {"plan_id": p["id"], "task_code": "T03", "checklist_state": {"0": True}, "status": "SUBMITTED"}},
    ]
    r = client.post("/api/v1/sync", headers=h, json={"client_id": "device-1", "ops": ops}).json()
    assert r["counts"]["applied"] == 3
    again = client.post("/api/v1/sync", headers=h, json={"client_id": "device-1", "ops": ops}).json()
    assert again["counts"] == {"applied": 0, "duplicate": 3, "conflict": 0, "rejected": 0, "failed": 0}
    w = client.get(f"/api/v1/workers/{wid}", headers=h).json()
    assert w["locality"] == "Danapur" and len(w["experiences"]) == 2  # applied exactly once
    t3 = next(t for t in client.get(f"/api/v1/assessments/{p['id']}", headers=h).json()["tasks"] if t["task_code"] == "T03")
    assert t3["attempt"]["status"] == "SUBMITTED"
    st = client.get("/api/v1/sync/status", headers=h).json()
    assert st["by_status"]["applied"] == 3 and st["last_sync_at"]


def test_assessor_owned_ops_rejected_and_stale_edit_is_conflict(client):
    p, wid, h, _ = started_plan(client)
    old = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    ops = [
        {"op_id": uid(), "entity": "assessor_score", "op": "update", "payload": {"criterion_code": "C02.2", "final_score": 4}},
        {"op_id": uid(), "entity": "worker_profile", "op": "update", "payload": {"district": "Gaya"}, "client_ts": old},
        {"op_id": uid(), "entity": "worker_profile", "op": "update", "payload": {"age": 7}},  # invalid → failed, batch continues
        {"op_id": uid(), "entity": "worker_profile", "op": "update", "payload": {"locality": "Ok"}},
    ]
    r = client.post("/api/v1/sync", headers=h, json={"client_id": "device-2", "ops": ops}).json()
    assert [x["status"] for x in r["results"]] == ["rejected", "conflict", "failed", "applied"]
    assert client.get(f"/api/v1/workers/{wid}", headers=h).json()["district"] == "Patna"


def test_staff_cannot_use_worker_sync(client, assessor_headers):
    r = client.post("/api/v1/sync", headers=assessor_headers, json={"client_id": "x-device", "ops": []})
    assert r.status_code == 403
