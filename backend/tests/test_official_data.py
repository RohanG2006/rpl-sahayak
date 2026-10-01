"""Phase 2: official qualification data integrity and provenance."""
import hashlib
import json
import re

from app.core.config import DATA_DIR, REPO_ROOT


def test_requires_auth(client):
    assert client.get("/api/v1/qualifications").status_code == 401


def test_list_contains_official_electrician_and_wireman(client, assessor_headers):
    rows = {q["qualification_code"]: q for q in client.get("/api/v1/qualifications", headers=assessor_headers).json()}
    assert set(rows) == {"DGT/1001", "DGT/1009"}
    e = rows["DGT/1001"]
    assert e["title"] == "ELECTRICIAN" and e["nsqf_level"] == 4 and e["ncvet_code"] == "2022/POW/DGT/06309"
    assert e["is_assessable"] is True and rows["DGT/1009"]["is_assessable"] is False
    assert all(q["data_origin"] == "official" for q in rows.values())
    assert e["source_url"].startswith("https://www.nqr.gov.in/")


def test_detail_by_official_code_with_slash(client, assessor_headers):
    d = client.get("/api/v1/qualifications/DGT/1001", headers=assessor_headers).json()
    trade = [c for c in d["competencies"] if c["category"] == "trade"]
    emp = [c for c in d["competencies"] if c["category"] == "employability"]
    assert len(trade) == 30 and len(emp) == 12
    assert [c["lo_number"] for c in trade] == list(range(1, 31))
    assert all(c["assessment_criteria"] for c in d["competencies"])
    assert d["rpl_eligibility"]["category_iv_other_candidates"]["min_age"] == 21
    assert sum(x["weight_pct"] for x in d["formative_dimensions"]) == 100
    lo7 = trade[6]
    assert lo7["nos_codes_summary"] == ["PSS/N9403"] and lo7["nos_codes_lo_table"] == ["N/A"] and lo7["nos_mismatch"]


def test_unknown_qualification_is_typed_error(client, assessor_headers):
    r = client.get("/api/v1/qualifications/NOPE-1", headers=assessor_headers)
    assert r.status_code == 404 and r.json()["error"]["code"] == "qualification_unavailable"


def test_source_files_match_recorded_hashes():
    meta = json.loads((DATA_DIR / "qualifications" / "source_metadata.json").read_text(encoding="utf-8"))
    for s in meta["official_sources"]:
        digest = hashlib.sha256((REPO_ROOT / s["local_file"]).read_bytes()).hexdigest()
        assert digest == s["sha256"], s["local_file"]


def test_task_bank_references_are_verbatim_official_criteria(client, assessor_headers):
    d = client.get("/api/v1/qualifications/DGT/1001", headers=assessor_headers).json()
    crit = {c["lo_number"]: c["assessment_criteria"] for c in d["competencies"] if c["category"] == "trade"}
    tasks = client.get("/api/v1/qualifications/DGT/1001/tasks", headers=assessor_headers).json()
    assert len(tasks) == 8
    n = 0
    for t in tasks:
        assert set(t["lo_numbers"]) <= set(crit)
        assert set(t["scoring_scale"]) == {"0", "1", "2", "3", "4"}
        for c in t["criteria"]:
            n += 1
            assert set(c["anchors"]) == {"0", "1", "2", "3", "4"}
            m = re.match(r"LO(\d+): (.*)", c["qf_criterion_ref"])
            if m:
                assert m.group(2) in crit[int(m.group(1))], c["criterion_code"]
            else:
                assert c["qf_criterion_ref"].startswith("QF §24")
    assert n == 28
    assert any(c["is_safety_critical"] for t in tasks for c in t["criteria"])


def test_project_authored_files_are_labelled():
    for rel in ("assessment/electrician_tasks.json", "assessment/rubric.json", "qualifications/electrician_lexicon.json"):
        assert json.loads((DATA_DIR / rel).read_text(encoding="utf-8"))["_label"].startswith("PROJECT-AUTHORED")
    for rel in ("qualifications/electrician_qualification.json", "qualifications/wireman_qualification.json"):
        assert json.loads((DATA_DIR / rel).read_text(encoding="utf-8"))["_label"].startswith("OFFICIAL SOURCE DATA")
