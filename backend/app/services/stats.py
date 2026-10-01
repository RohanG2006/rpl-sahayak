"""Inter-rater agreement statistics (pure Python, no dependencies). Verified against published examples in
tests/test_consistency.py (Shrout & Fleiss 1979 for ICC; Fleiss 1971 / standard worked example for Fleiss' kappa)."""
from __future__ import annotations

from itertools import combinations
from statistics import mean, pstdev, stdev, variance


def cohen_kappa(a: list[int], b: list[int], categories: list[int], weights: str = "quadratic") -> float | None:
    """Cohen's kappa for two raters; weights: 'none' | 'linear' | 'quadratic'."""
    if len(a) != len(b) or not a:
        raise ValueError("ratings must be equal-length and non-empty")
    k = len(categories)
    idx = {c: i for i, c in enumerate(categories)}
    n = len(a)
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[idx[x]][idx[y]] += 1 / n
    pa = [sum(obs[i][j] for j in range(k)) for i in range(k)]
    pb = [sum(obs[i][j] for i in range(k)) for j in range(k)]

    def w(i: int, j: int) -> float:
        if weights == "none":
            return 0.0 if i == j else 1.0
        d = abs(i - j) / (k - 1)
        return d if weights == "linear" else d * d

    do = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k))
    de = sum(w(i, j) * pa[i] * pb[j] for i in range(k) for j in range(k))
    return None if de == 0 else 1 - do / de


def fleiss_kappa(counts: list[list[int]]) -> float | None:
    """counts[subject][category] = number of raters assigning that category (same rater count per subject)."""
    n_sub = len(counts)
    n = sum(counts[0])
    if n_sub == 0 or n < 2:
        return None
    k = len(counts[0])
    p_j = [sum(row[j] for row in counts) / (n_sub * n) for j in range(k)]
    p_i = [(sum(c * c for c in row) - n) / (n * (n - 1)) for row in counts]
    p_bar, p_e = mean(p_i), sum(p * p for p in p_j)
    return None if p_e == 1 else (p_bar - p_e) / (1 - p_e)


def icc_2_1(matrix: list[list[float]]) -> float | None:
    """ICC(2,1): two-way random effects, absolute agreement, single rater (Shrout & Fleiss 1979).
    matrix[target][rater]."""
    n, k = len(matrix), len(matrix[0])
    if n < 2 or k < 2:
        return None
    grand = mean(x for row in matrix for x in row)
    row_m = [mean(r) for r in matrix]
    col_m = [mean(matrix[i][j] for i in range(n)) for j in range(k)]
    ss_r = k * sum((m - grand) ** 2 for m in row_m)
    ss_c = n * sum((m - grand) ** 2 for m in col_m)
    ss_t = sum((x - grand) ** 2 for row in matrix for x in row)
    ss_e = ss_t - ss_r - ss_c
    msr, msc, mse = ss_r / (n - 1), ss_c / (k - 1), ss_e / ((n - 1) * (k - 1))
    den = msr + (k - 1) * mse + k * (msc - mse) / n
    return None if den == 0 else (msr - mse) / den


def pairwise_agreement(items: list[list[int]]) -> tuple[float, float]:
    """items[item][rater] → (exact agreement share, within-±1 share) over all rater pairs."""
    exact = adj = total = 0
    for row in items:
        for x, y in combinations(row, 2):
            total += 1
            exact += x == y
            adj += abs(x - y) <= 1
    return (exact / total, adj / total) if total else (0.0, 0.0)


def spread(values: list[float]) -> dict:
    return {"mean": mean(values), "sd": stdev(values) if len(values) > 1 else 0.0,
            "variance": variance(values) if len(values) > 1 else 0.0, "range": max(values) - min(values),
            "population_sd": pstdev(values)}
