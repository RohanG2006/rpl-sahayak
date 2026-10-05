"""Assessment report (PDF) — spec §44.

Built with ReportLab's built-in fonts so it renders on any server without font files. Those fonts cannot shape
Devanagari, so non-Latin text is replaced by a marker pointing to the system (known limitation, docs/README).
"""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AIObservation, AssessmentPlan, AssessorDecision, AssessorScore, AuditLog, Evidence, Qualification, Recommendation, User,
    WorkerProfile, WorkerSkill,
)
from app.services.gaps import compute_gaps
from app.services.recommendation import DISCLAIMER
from app.services.results import plan_results, plan_tasks

INK, RULE, AI, OK, BAD, WARN = (colors.HexColor(c) for c in ("#16191d", "#d9d5cb", "#b45309", "#15803d", "#b91c1c", "#a16207"))
_SUBS = {"≥": ">=", "≤": "<=", "→": "->", "✓": "pass", "✕": "fail", "×": "x", "−": "-", "φ": "phi", "ø": "phi", "“": '"', "”": '"', "’": "'", "‘": "'", "…": "..."}
DECISION_LABEL = {"APPROVE": "Approved for certification", "REJECT": "Not yet competent", "REASSESS": "Reassessment requested"}
OUTCOME_LABEL = {"ELIGIBLE": "Eligible - for assessor sign-off", "NOT_YET_READY": "Not yet ready", "REASSESSMENT_SUGGESTED": "Reassessment suggested"}


def safe(text) -> str:
    """Escape for ReportLab markup and keep to characters the built-in fonts can draw."""
    s = "" if text is None else str(text)
    if re.search(r"[ऀ-ॿ]", s):
        s = re.sub(r"[ऀ-ॿ][ऀ-ॿ\s।,.]*", "[shown in Hindi in the system] ", s).strip()
    for a, b in _SUBS.items():
        s = s.replace(a, b)
    s = s.encode("cp1252", "replace").decode("cp1252")
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _styles():
    ss = getSampleStyleSheet()
    base = ParagraphStyle("b", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12, textColor=INK)
    return {
        "base": base,
        "small": ParagraphStyle("s", parent=base, fontSize=7.5, leading=10, textColor=colors.HexColor("#3d434b")),
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=2),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=8, spaceAfter=4),
        "label": ParagraphStyle("l", parent=base, fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=colors.HexColor("#6b727c")),
        "ai": ParagraphStyle("ai", parent=base, textColor=AI, fontName="Helvetica-Bold"),
    }


def _table(rows, widths, header=True, zebra=False):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    st = [("FONT", (0, 0), (-1, -1), "Helvetica", 8), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.5), ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#6b727c")),
               ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK)]
    t.setStyle(TableStyle(st))
    return t


def build_report(db: Session, plan: AssessmentPlan) -> tuple[bytes, dict]:
    S = _styles()
    P = lambda t, s="base": Paragraph(safe(t), S[s])  # noqa: E731
    w = db.get(WorkerProfile, plan.worker_id)
    q = db.get(Qualification, plan.qualification_id)
    assessor = db.get(User, plan.assessor_id) if plan.assessor_id else None
    res = plan_results(db, plan)
    gaps = compute_gaps(db, plan, res)
    rec = db.scalar(select(Recommendation).where(Recommendation.plan_id == plan.id).order_by(Recommendation.created_at.desc()))
    dec = db.scalar(select(AssessorDecision).where(AssessorDecision.plan_id == plan.id).order_by(AssessorDecision.created_at.desc()))
    decided = dec is not None
    now = datetime.now(timezone.utc)
    synthetic = plan.data_origin == "synthetic"

    story = []
    story.append(Paragraph("RPL-Sahayak AI - Assessment report", S["h1"]))
    story.append(P(f"Recognition of Prior Learning - {q.title} ({q.qualification_code}, NSQF Level {q.nsqf_level:g}) - prototype report, not a certificate", "small"))
    if synthetic:
        story.append(Paragraph("<b>SYNTHETIC / DEMONSTRATION DATA - NOT A REAL CANDIDATE</b>", ParagraphStyle("syn", parent=S["base"], textColor=WARN)))
    if not decided:
        story.append(Paragraph("<b>DRAFT - no assessor decision has been recorded yet</b>", ParagraphStyle("dr", parent=S["base"], textColor=BAD)))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>IMPORTANT:</b> {safe(DISCLAIMER)} AI-generated assistance in this report is advisory and does not replace "
                           "authorised assessor judgement.", ParagraphStyle("disc", parent=S["base"], textColor=AI, borderColor=AI,
                                                                            borderWidth=0.8, borderPadding=5, spaceBefore=4, spaceAfter=8)))

    # 1 Candidate & qualification
    skills = [s.label for s in db.scalars(select(WorkerSkill).where(WorkerSkill.worker_id == w.id, WorkerSkill.kind == "skill"))]
    story.append(Paragraph("1. Candidate and qualification", S["h2"]))
    story.append(_table([
        [P("Candidate", "label"), P(w.full_name), P("Qualification", "label"), P(f"{q.title} - {q.qualification_code} (NCVET {q.ncvet_code})")],
        [P("Location", "label"), P(", ".join(x for x in (w.district, w.state) if x) or "-"), P("Awarding body", "label"), P(q.awarding_body)],
        [P("Occupation", "label"), P(w.occupation), P("Assessor", "label"), P(f"{assessor.full_name}" if assessor else "unassigned")],
        [P("Experience", "label"), P(f"{w.years_experience:g} years" if w.years_experience is not None else "not stated"),
         P("Pathway", "label"), P((plan.pathway or "-").replace("_", " ").title())],
        [P("Learned via", "label"), P(w.informal_training or "-"), P("Qualification match", "label"),
         P(f"{(plan.match_snapshot or {}).get('final_pct', '-')}% (rule-based mapping engine)")],
    ], [28 * mm, 57 * mm, 32 * mm, 57 * mm], header=False))
    story.append(Spacer(1, 3))
    story.append(P("Confirmed skills: " + (", ".join(skills) or "-"), "small"))

    # 2 Competencies
    story.append(Paragraph("2. Mapped competencies (assessor-confirmed scores only)", S["h2"]))
    rows = [["Competency area", "Score", "Required", "Status"]]
    for a in sorted(gaps["areas"], key=lambda a: a["label"]):
        v = a["demonstrated"]
        rows.append([P(a["label"]), f"{v:.1f}%" if v is not None else "-", f"{a['required']:.0f}%",
                     "not assessed" if v is None else ("met" if v >= a["required"] else f"gap {a['gap']:.1f}")])
    rows.append([Paragraph("<b>Overall practical score</b>", S["base"]), f"{res['overall_pct']:.1f}%" if res["overall_pct"] is not None else "-", f"{gaps['required_pct']:.0f}%", ""])
    story.append(_table(rows, [80 * mm, 30 * mm, 30 * mm, 34 * mm]))
    story.append(P(f"Scope: {len(res['learning_outcomes'])} of {sum(c.category == 'trade' for c in q.competencies)} official learning outcomes "
                   f"were assessed in this prototype; the others are not assessed and are not assumed competent.", "small"))

    # 3 Tasks & scores
    story.append(Paragraph("3. Practical tasks and scores", S["h2"]))
    rows = [["Task", "LOs", "Criteria scored", "Task score"]]
    for t in plan_tasks(db, plan):
        tr = res["tasks"][t.task_code]
        rows.append([P(f"{t.task_code} - {t.title}"), ", ".join(map(str, t.lo_numbers)), f"{tr['scored']}/{tr['total']}",
                     f"{tr['task_pct']:.1f}%" if tr["task_pct"] is not None else "-"])
    story.append(_table(rows, [100 * mm, 22 * mm, 26 * mm, 26 * mm]))
    if res["safety_flags"]:
        story.append(Paragraph(f"<b>Safety-critical criteria scored 0-1:</b> {safe(', '.join(res['safety_flags']))}", ParagraphStyle("sf", parent=S["base"], textColor=BAD)))

    # 4 Evidence
    ev = list(db.scalars(select(Evidence).where(Evidence.plan_id == plan.id)))
    story.append(Paragraph("4. Evidence summary", S["h2"]))
    story.append(P(f"{len(ev)} evidence items ({sum(e.kind == 'image' for e in ev)} images, {sum(e.kind == 'video' for e in ev)} videos, "
                   f"{sum(e.kind == 'document' for e in ev)} documents); {sum(e.captured_offline for e in ev)} captured offline. "
                   f"Required evidence coverage: {res['evidence_coverage'] * 100:.0f}%"
                   + (f"; missing for {', '.join(res['evidence_missing'])}." if res["evidence_missing"] else ".")))

    # 5 Gaps
    story.append(Paragraph("5. Skill gaps and learning topics", S["h2"]))
    gap_areas = [a for a in gaps["areas"] if a["status"] == "gap"]
    if not gap_areas:
        story.append(P("No gaps against the 60% threshold in the assessed scope."))
    for a in gap_areas:
        lines = [f"<b>{safe(a['label'])}</b>: {a['demonstrated']:.1f}% (required {a['required']:.0f}%, gap {a['gap']:.1f})"]
        for x in a["learning_topics"][:4]:
            tag = f"[LO{x['lo_number']}]" if x["source"] == "official" else "[suggested]"
            lines.append(f"&nbsp;&nbsp;- {tag} {safe(x['topic'].rstrip('.'))}")
        story.append(Paragraph("<br/>".join(lines), ParagraphStyle("gap", parent=S["base"], spaceAfter=4)))
    story.append(P("[LO n] topics quote the official qualification's assessment criteria; [suggested] topics are prototype guidance, not official requirements.", "small"))

    # 6 AI assistance summary
    obs = list(db.scalars(select(AIObservation).where(AIObservation.plan_id == plan.id)))
    with_ai = list(db.scalars(select(AssessorScore).where(AssessorScore.plan_id == plan.id, AssessorScore.ai_suggested_score.is_not(None))))
    providers = sorted({o.provider for o in obs})
    story.append(Paragraph("6. AI assistance summary (advisory)", S["h2"]))
    story.append(P(f"{len(obs)} AI outputs recorded ({', '.join(providers) or 'none'}). {len(with_ai)} criteria had an AI-suggested score; "
                   f"the assessor overrode {sum(s.overrode_ai for s in with_ai)} of them. AI suggestions are stored separately and are never "
                   "used in score calculations."))
    if "demo-prepared" in providers:
        story.append(P("Evidence observations on synthetic placeholder images are prepared demo outputs, not live AI calls.", "small"))
    if rec:
        story.append(Spacer(1, 3))
        story.append(Paragraph(f"AI-assisted recommendation: {safe(OUTCOME_LABEL[rec.outcome])} "
                               f"(competency coverage {rec.competency_coverage * 100:.0f}%, evidence coverage {rec.evidence_coverage * 100:.0f}%)", S["ai"]))
        rows = [["Rule", "Result", "Detail", "Source"]] + [[r["rule"], "pass" if r["passed"] else "FAIL", P(r["detail"], "small"), P(r["source"], "small")] for r in rec.rule_trace]
        story.append(_table(rows, [12 * mm, 14 * mm, 84 * mm, 64 * mm]))

    # 7 Decision
    story.append(KeepTogether([
        Paragraph("7. Assessor decision (final, human)", S["h2"]),
        _table([[P("Decision", "label"), Paragraph(f"<b>{safe(DECISION_LABEL[dec.decision])}</b>", S["base"]) if dec else P("Not yet recorded")],
                [P("Assessor comments", "label"), P(dec.comments if dec else "-")],
                [P("Tasks to reassess", "label"), P(", ".join(dec.reassess_task_codes) if dec and dec.reassess_task_codes else "-")],
                [P("Decided by", "label"), P(f"{db.get(User, dec.assessor_id).full_name} on {dec.created_at:%d %b %Y %H:%M} UTC" if dec else "-")],
                [P("Agreement with AI", "label"), P("-" if not dec or dec.agrees_with_recommendation is None else ("agrees" if dec.agrees_with_recommendation else "differs - assessor judgement prevails"))]],
               [40 * mm, 134 * mm], header=False),
    ]))

    # 8 Audit metadata
    n_audit = db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.entity_id == plan.id)) or 0
    story.append(Paragraph("8. Audit metadata", S["h2"]))
    story.append(_table([
        [P("Assessment id", "label"), P(plan.id), P("Generated", "label"), P(f"{now:%d %b %Y %H:%M} UTC")],
        [P("Plan created", "label"), P(f"{plan.created_at:%d %b %Y}"), P("Audit events (plan)", "label"), P(str(n_audit))],
        [P("Official source", "label"), P(q.source.url), P("Source SHA-256", "label"), P(f"{(q.source.sha256 or '')[:24]}...")],
        [P("Data origin", "label"), P(plan.data_origin), P("Report status", "label"), P("final" if decided else "DRAFT")],
    ], [30 * mm, 57 * mm, 32 * mm, 55 * mm], header=False))
    story.append(Spacer(1, 6))
    story.append(P("Prototype (SIH26242). Not an NCVET/DGT certificate and not a legally valid assessment outcome. Official qualification data: "
                   "National Qualification Register (DGT/NCVET).", "small"))

    buf = io.BytesIO()

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#6b727c"))
        canvas.drawString(18 * mm, 10 * mm, f"RPL-Sahayak AI - {q.qualification_code} - {plan.id[:8]}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        if not decided or synthetic:
            canvas.setFont("Helvetica-Bold", 54)
            canvas.setFillColor(colors.Color(0.7, 0.1, 0.1, alpha=0.08))
            canvas.translate(A4[0] / 2, A4[1] / 2)
            canvas.rotate(35)
            canvas.drawCentredString(0, 0, "DRAFT" if not decided else "SYNTHETIC")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"RPL assessment report - {w.full_name}", author="RPL-Sahayak AI (prototype)")
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buf.getvalue(), {"decided": decided, "synthetic": synthetic}
