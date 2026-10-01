"""Shared end-to-end helpers: Worker → Profile → Match → Plan → Self-assessment → Tasks → Evidence → Scores."""
import io

from PIL import Image

from tests.conftest import login, make_worker

DOMESTIC = ["House wiring installation", "Switch and socket installation", "Fan installation and repair",
            "MCB / circuit breaker installation", "Electrical fault diagnosis", "Measurement with multimeter"]
EMAIL = {f"A0{i}": f"assessor{i}@demo.rpl" for i in range(1, 6)}


def png() -> bytes:
    img = Image.new("RGB", (640, 480), (200, 200, 200))
    for x in range(0, 640, 16):
        for y in range(480):
            img.putpixel((x, y), (30, 30, 30))
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()


def started_plan(client):
    wid, h = make_worker(client, skills=DOMESTIC)
    res = client.post("/api/v1/qualifications/match", headers=h, json={"worker_id": wid}).json()["results"]
    q = next(r for r in res if r["qualification_code"] == "DGT/1001")
    p = client.post("/api/v1/assessments", headers=h, json={"worker_id": wid, "qualification_id": q["qualification_id"]}).json()
    scope = sorted({lo for t in p["tasks"] for lo in t["lo_numbers"]})
    client.post(f"/api/v1/assessments/{p['id']}/self-assessment", headers=h, json={"responses": {str(lo): "regularly" for lo in scope}})
    p = client.post(f"/api/v1/assessments/{p['id']}/start", headers=h).json()
    return p, wid, h, login(client, EMAIL[p["assessor"]["code"]])


def upload_required_evidence(client, p, wid, h):
    for t in p["tasks"]:
        for r in t["evidence_required"]:
            r2 = client.post("/api/v1/evidence", headers=h, data={"worker_id": wid, "plan_id": p["id"], "criterion_code": r["criterion"],
                                                                 "purpose": "assessment", "caption": r["what"]},
                             files={"file": ("e.png", png(), "image/png")})
            assert r2.status_code == 201, r2.text


def score_all(client, p, ah, default=3, overrides: dict | None = None):
    overrides = overrides or {}
    r = None
    for t in p["tasks"]:
        scores = [{"criterion_code": c["criterion_code"], "final_score": overrides.get(c["criterion_code"], default),
                   "assessor_note": "Observed during practical"} for c in t["criteria"]]
        r = client.post(f"/api/v1/assessments/{p['id']}/tasks/{t['task_code']}/score", headers=ah, json={"scores": scores})
        assert r.status_code == 200, r.text
    return r.json()
