# Sources

## Official sources used

| # | Document | Publisher | URL | Local copy | SHA-256 | Retrieved |
|---|---|---|---|---|---|---|
| 1 | NSQF Qualification File — **Electrician** (DGT/1001, NCVET 2022/POW/DGT/06309, NSQF 4); "Approved in 22th NSQC Meeting-NCVET-25th August 2022" | DGT, MSDE (via National Qualification Register) | https://www.nqr.gov.in/sites/default/files/QF_Electrician_CTS2.0_NSQF-4.pdf | `data/sources/QF_Electrician_CTS2.0_NSQF-4.pdf` | `7ac84a9b967b710c42da0184afdc7c193fe050064a6648d7e0623b9634fd6db3` | 2026-10-01 |
| 2 | NSQF Qualification File — **Wireman** (DGT/1009, NCVET 2022/POW/DGT/06310, NSQF 4) | DGT, MSDE (via NQR) | https://www.nqr.gov.in/sites/default/files/QF_Wireman_CTS2.0_NSQF-4.pdf | `data/sources/QF_Wireman_CTS2.0_NSQF-4.pdf` | `70676fc558844158dad55d2a5deac1f83b11daca18d68f7abecb7446f6a79844` | 2026-10-01 |
| 3 | **Guidelines for Recognition of Prior Learning**, F.No. 22003/05/2023/NCVET (11 Aug 2023), Gazette of India Extraordinary Part III Sec 4, No. 420, 19 June 2024 | NCVET | https://ncvet.gov.in/wp-content/uploads/2024/09/RPL.pdf | `data/sources/NCVET_RPL_2024-09.pdf` | `35af675aa73c1c4830bc0a306081c264376f63f0e1de35769d28508f0e55abc0` | 2026-10-01 |
| 4 | Draft Guidelines for RPL, 27 Jan 2023, Version 10.2 | NCVET | https://ncvet.gov.in/wp-content/uploads/2023/01/RPL-guidelines-for-PC-30.01.23.pdf | `data/sources/NCVET_RPL_guidelines_2023-01-30.pdf` | `52039f4f97cf1938dc58ab1504d3c6a5106095c0551c940ad732ee546ea77562` | 2026-10-01 |
| — | National Qualification Register (index) | NCVET | https://www.nqr.gov.in/ | — | — | — |

The hashes are re-checked by `backend/tests/test_official_data.py::test_source_files_match_recorded_hashes`.

## What each source is used for

| Used for | Source & location |
|---|---|
| Qualification record: title, codes, NSQF level, NCO, job description, awarding body, notional hours, entry requirement, progression, RPL availability | (1) items 1–19 |
| 30 trade learning outcomes with NOS codes and skill/knowledge hours; 12 employability LOs | (1) §20, LO tables pp. 11–20 |
| Every task-bank criterion reference (verbatim, tested) | (1) LO assessment criteria |
| RPL eligibility Category IV: age ≥ 21, ≥ 3 years' experience, entry qualification | (1) §22 |
| 60 % competency threshold | (1) §23 minimum pass for Trade Practical / formative |
| Official formative dimensions and weightages (safety consciousness 15 %, …) | (1) §24 |
| "No scope for error … could cause fatal accidents" (rationale for the safety gate) | (1) §25 |
| Comparison qualification for ranking | (2) |
| > 70 % of declared learning outcomes for direct RPL assessment | (3) §6.2(c); Annexure-1 Flowchart 1 |
| Workflow stages: Enrolment → Orientation → Assignment of RPL assessor → Assessment → Certification & Feedback; "not suitable" → skill-gap training | (3) Annexure-1 Flowchart 3 (NSQF 4 without formal education) |
| Assessor role statements | (3) §6.2 |
| Background | (4) |

## Known discrepancy in a source (kept as published)

The Electrician QF gives different NOS codes for some LOs in its summary table (§20) and in its LO / assessment
criteria table (e.g. LO 7: `PSS/N9403` vs `N/A`; LOs 12, 13, 29, 30 list no NOS in the LO table). Both values are
stored (`nos_codes_summary`, `nos_codes_lo_table`, `nos_mismatch = true`) and the admin view flags them. Nothing was
"corrected".

## Fields not present in the sources

Not invented; stored as empty with a `not_in_source` note: NOS titles/descriptions, international comparability,
an RPL-specific duration.

## Method references

- Shrout, P. E., & Fleiss, J. L. (1979). Intraclass correlations: uses in assessing rater reliability.
  *Psychological Bulletin*, 86(2), 420–428 — ICC(2,1) definition and Table 2 test fixture.
- Fleiss, J. L. (1971). Measuring nominal scale agreement among many raters. *Psychological Bulletin*, 76(5), 378–382
  — Fleiss' κ.
- Cohen, J. (1968). Weighted kappa. *Psychological Bulletin*, 70(4), 213–220 — weighted Cohen's κ.

## Attribution in the product

Official records carry `data_origin = official` and a link to their source; the admin qualification page shows the
source URL, SHA-256 and retrieval date; the qualification match screen links the source PDF; the PDF report's audit
section names the source and its fingerprint; the public About page lists all sources.
