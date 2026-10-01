"""Phase 9: agreement statistics verified against published worked examples, and the consistency endpoint."""
import pytest

from app.seed.consistency import load_consistency
from app.services import stats

# Shrout & Fleiss (1979), Table 2: 6 targets × 4 judges. Published ICC(2,1) = 0.29.
SHROUT_FLEISS = [[9, 2, 5, 8], [6, 1, 3, 2], [8, 4, 6, 8], [7, 1, 2, 6], [10, 5, 6, 9], [6, 2, 4, 7]]

# Standard Fleiss' kappa worked example (10 subjects, 14 raters, 5 categories). Published κ = 0.210.
FLEISS_EXAMPLE = [
    [0, 0, 0, 0, 14], [0, 2, 6, 4, 2], [0, 0, 3, 5, 6], [0, 3, 9, 2, 0], [2, 2, 8, 1, 1],
    [7, 7, 0, 0, 0], [3, 2, 6, 3, 0], [2, 5, 3, 2, 2], [6, 5, 2, 1, 0], [0, 2, 2, 3, 7],
]


def test_icc_matches_shrout_fleiss():
    assert stats.icc_2_1(SHROUT_FLEISS) == pytest.approx(0.29, abs=0.005)


def test_fleiss_kappa_matches_published_example():
    assert stats.fleiss_kappa(FLEISS_EXAMPLE) == pytest.approx(0.210, abs=0.001)


def test_cohen_kappa_unweighted_hand_example():
    # Two raters, yes/no: 20 both yes, 15 both no, 5 / 10 disagreements → κ = 0.4
    a = [1] * 20 + [1] * 5 + [0] * 10 + [0] * 15
    b = [1] * 20 + [0] * 5 + [1] * 10 + [0] * 15
    assert stats.cohen_kappa(a, b, [0, 1], "none") == pytest.approx(0.4)


def test_quadratic_kappa_properties():
    x = [0, 1, 2, 3, 4, 2, 3]
    assert stats.cohen_kappa(x, x, [0, 1, 2, 3, 4]) == pytest.approx(1.0)
    near = stats.cohen_kappa([0, 1, 2, 3, 4], [1, 1, 2, 3, 3], [0, 1, 2, 3, 4])
    far = stats.cohen_kappa([0, 1, 2, 3, 4], [4, 3, 2, 1, 0], [0, 1, 2, 3, 4])
    assert near > 0.8 and far == pytest.approx(-1.0)  # full reversal is perfect disagreement under quadratic weights


def test_pairwise_agreement():
    exact, adj = stats.pairwise_agreement([[2, 2, 3], [0, 4, 4]])
    # pairs: (2,2)=exact,(2,3)=adj,(2,3)=adj ; (0,4),(0,4)=neither,(4,4)=exact
    assert exact == pytest.approx(2 / 6) and adj == pytest.approx(4 / 6)


def test_consistency_endpoint_computes_from_dataset(client, db, assessor_headers, worker_like=None):
    assert load_consistency(db) == 5600
    db.commit()
    r = client.get("/api/v1/analytics/consistency", headers=assessor_headers)
    assert r.status_code == 200
    j = r.json()
    assert j["available"] and j["label"].startswith("Prototype / Test Dataset Demonstration")
    b, s = j["modes"]["baseline"], j["modes"]["standardised"]
    assert b["n_cases"] == 20 and b["n_assessors"] == 5 and b["n_items"] == 20 * 28
    for k in ("fleiss_kappa", "icc_2_1", "mean_pairwise_weighted_kappa", "exact_agreement"):
        assert -1 <= b[k] <= 1 and -1 <= s[k] <= 1
    ch = j["change"]["mean_case_sd"]
    assert ch["change"] == pytest.approx(ch["after"] - ch["before"])
    assert j["featured_case"]["rule"].startswith("Case with the median")
    assert j["parameters"]["parameters"]["seed"] == 2026
    fc = j["cases"][j["featured_case"]["case_id"]]
    assert set(fc["baseline"]["overall"]) == {"A01", "A02", "A03", "A04", "A05"}


def test_consistency_requires_staff(client):
    from tests.conftest import make_worker
    _, h = make_worker(client, skills=["House wiring installation"])
    assert client.get("/api/v1/analytics/consistency", headers=h).status_code == 403
