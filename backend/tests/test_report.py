"""Phase 14: PDF assessment report (spec §44)."""
from pypdf import PdfReader
import io

from tests.flows import score_all, started_plan, upload_required_evidence


def text_of(pdf: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


def test_report_draft_then_final_and_access(client):
    p, wid, h, ah = started_plan(client)
    upload_required_evidence(client, p, wid, h)
    score_all(client, p, ah, default=3, overrides={"C05.2": 1, "C05.1": 1})
    assert client.post(f"/api/v1/assessments/{p['id']}/recommendation", headers=ah).status_code == 200

    # worker cannot download before the decision
    assert client.get(f"/api/v1/assessments/{p['id']}/report.pdf", headers=h).status_code == 403
    r = client.get(f"/api/v1/assessments/{p['id']}/report.pdf", headers=ah)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF")
    assert "DRAFT" in r.headers["content-disposition"]
    t = text_of(r.content)
    for section in ("1. Candidate and qualification", "2. Mapped competencies", "3. Practical tasks and scores", "4. Evidence summary",
                    "5. Skill gaps", "6. AI assistance summary", "7. Assessor decision", "8. Audit metadata"):
        assert section in t, section
    assert "final decision by authorised human assessor" in t and "DRAFT - no assessor decision" in t
    assert "Testing & Measurement" in t and "[LO8]" in t  # gap with official topic
    assert "DGT/1001" in t and "Not yet recorded" in t

    client.post("/api/v1/assessor/decision", headers=ah, json={"plan_id": p["id"], "decision": "REASSESS",
                                                               "comments": "Repeat measurement task with evidence.", "reassess_task_codes": ["T05"]})
    r = client.get(f"/api/v1/assessments/{p['id']}/report.pdf", headers=h)  # worker, after decision
    assert r.status_code == 200 and "DRAFT" not in r.headers["content-disposition"]
    t = text_of(r.content)
    assert "Reassessment requested" in t and "T05" in t and "Report status final" in t.replace("\n", " ")
    assert client.get(f"/api/v1/assessments/{p['id']}", headers=ah).json()["status"] == "REPORT_ISSUED"


def test_report_text_sanitising():
    from app.services.report import safe
    assert safe("≥ 60% → pass ✓ <b>") == "&gt;= 60% -&gt; pass pass &lt;b&gt;"
    assert "[shown in Hindi in the system]" in safe("मैं 6 साल से काम करता हूँ। wiring")
