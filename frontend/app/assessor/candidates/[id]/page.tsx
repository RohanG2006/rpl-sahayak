"use client";
import Link from "next/link";
import { Fragment, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import EvidenceThumb from "@/components/EvidenceThumb";
import { CompetencyBars, DECISION, OUTCOME, StatusBadge } from "@/components/staff";
import { Button, Notice, Spinner, Stamp } from "@/components/ui";
import { getPlan, type Plan, type Readiness } from "@/lib/data/assessment";
import {
  getDecision, getGaps, getRecommendation, getResults, getWorkerFull, makeRecommendation, recordDecision,
  type Decision, type Gaps, type Recommendation, type Results,
} from "@/lib/data/assessor";
import { listEvidence, type EvidenceItem } from "@/lib/data/evidence";
import { ApiError } from "@/lib/api";
import type { Worker } from "@/lib/types";

const DIM_LABEL: Record<string, string> = {
  safety: "Safety consciousness", hygiene: "Workplace hygiene", manuals: "Following manuals/instructions", knowledge: "Application of knowledge",
  tools: "Handling tools/instruments", materials: "Economical use of materials", strategy: "Working strategy", quality: "Quality of workmanship", viva: "Viva",
};

export default function CandidateDetail() {
  const { id } = useParams<{ id: string }>();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [worker, setWorker] = useState<Worker | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [results, setResults] = useState<Results | null>(null);
  const [gaps, setGaps] = useState<Gaps | null>(null);
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    const p = await getPlan(id);
    setPlan(p);
    const [w, ev, r, g, re, d] = await Promise.all([getWorkerFull(p.worker.id), listEvidence({ plan_id: id }), getResults(id), getGaps(id), getRecommendation(id), getDecision(id)]);
    setWorker(w); setEvidence(ev); setResults(r); setGaps(g); setRec(re); setDecision(d);
  }, [id]);
  useEffect(() => {
    // Initial load runs in a microtask (no synchronous setState in the effect); `live` drops errors after unmount.
    let live = true;
    Promise.resolve().then(() => (live ? load() : undefined)).catch((e) => { if (live) setErr(e instanceof ApiError ? e.message : "Could not load candidate."); });
    return () => { live = false; };
  }, [load]);

  if (err) return <Notice tone="bad">{err}</Notice>;
  if (!plan || !worker || !results || !gaps) return <Spinner label="Loading candidate…" />;
  const m = plan.match_snapshot;
  const rd = plan.readiness as Readiness;
  const latestExp = worker.experiences.at(-1);

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/assessor/candidates" className="text-sm text-ink-2 underline underline-offset-2">← Candidates</Link>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{worker.full_name} {worker.data_origin === "synthetic" && <Stamp kind="synthetic" />}</h1>
          <p className="text-sm text-ink-3">{plan.qualification.title} · {plan.qualification.qualification_code} · NSQF {plan.qualification.nsqf_level} · NCVET stage: {plan.ncvet_stage}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <StatusBadge status={plan.status} />
          <Link href={`/assessor/assessment/${plan.id}`} className="inline-flex min-h-11 items-center rounded-[3px] bg-ink px-4 text-sm font-semibold text-sheet">Open scoring workspace →</Link>
        </div>
      </header>

      {/* Profile + declaration + match */}
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="sheet p-4">
          <h2 className="label mb-2">Profile</h2>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            {[["Age", worker.age], ["Location", [worker.district, worker.state].filter(Boolean).join(", ")], ["Occupation", worker.occupation],
              ["Experience", worker.years_experience != null ? `${worker.years_experience} years` : null], ["Employer", worker.current_employer],
              ["Learned via", worker.informal_training], ["Education", worker.education_level], ["Certificates", worker.existing_certificates.join(", ")]]
              .map(([k, v]) => <Fragment key={k as string}><dt className="text-ink-3">{k}</dt><dd className="break-words">{(v as string) || "—"}</dd></Fragment>)}
          </dl>
        </section>
        <section className="sheet p-4 lg:col-span-2">
          <h2 className="label mb-2">Experience declaration {latestExp && `(v${latestExp.version}, ${latestExp.input_mode}, ${latestExp.language})`}</h2>
          {latestExp ? <blockquote className="border-l-2 border-rule-strong pl-3 text-ink-2">{latestExp.raw_text}</blockquote> : <p className="text-ink-3">—</p>}
          <h3 className="label mb-1.5 mt-4">Confirmed skills ({worker.skills.length})</h3>
          <ul className="flex flex-wrap gap-1.5">{worker.skills.filter((s) => s.kind !== "task").map((s) => (
            <li key={s.id} className="rounded-[3px] border border-rule-strong px-2 py-1 text-xs">{s.label}<span className="ml-1 text-ink-3">· {s.kind}{s.source !== "ai" ? `, added by ${s.source}` : ", AI-extracted"}</span></li>))}
          </ul>
        </section>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="sheet p-4">
          <h2 className="label mb-2">Qualification match <span className="ml-1 normal-case tracking-normal text-ink-3">(rule-based mapping engine)</span></h2>
          <p className="text-3xl font-semibold num">{m.final_pct}%</p>
          <p className="text-sm text-ink-3">{m.lo_coverage.matched} matched + {m.lo_coverage.partial} partial of {m.lo_coverage.total} official LOs evidenced by declaration</p>
          <ul className="mt-2 text-sm">{m.matched_skills.slice(0, 5).map((s) => <li key={s.label}><span className="font-bold text-ok">✓</span> {s.label} → LO{s.lo_number}</li>)}</ul>
          <ul className="mt-2 text-xs text-ink-2">{m.eligibility.map((c) => <li key={c.key}>{c.result === "pass" ? "✓" : c.result === "fail" ? "✕" : "?"} {c.label}: {c.detail}</li>)}</ul>
        </section>
        <section className="sheet p-4">
          <h2 className="label mb-2">Self-assessment & readiness</h2>
          {rd && "pathway" in rd ? <>
            <p className="font-semibold">{rd.pathway === "DIRECT_ASSESSMENT" ? "Direct assessment" : "Upskilling suggested"} · {Math.round(rd.weighted_coverage * 100)}% self-assessed coverage</p>
            <p className="text-xs text-ink-3">{rd.threshold_source}</p>
            {rd.probe_los.length > 0 && <p className="mt-2 text-sm"><span className="font-bold text-warn">!</span> Probe in viva: claimed regularly but not in declaration — LO {rd.probe_los.join(", ")}</p>}
            <table className="mt-2 w-full text-xs"><tbody>{rd.rows.map((r) => <tr key={r.lo_number} className="border-b border-rule last:border-0"><td className="py-1">LO {r.lo_number}</td><td>{r.claim}</td><td className="text-ink-3">declaration: {r.declaration_evidence.replace("_", " ")}</td></tr>)}</tbody></table>
          </> : <p className="text-ink-3">Not completed yet.</p>}
        </section>
      </div>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Evidence ({evidence.length})</h2>
        {evidence.length === 0 ? <p className="text-ink-3">No evidence uploaded.</p> : (
          <ul className="flex flex-wrap gap-2">{evidence.map((e) => (
            <li key={e.id} className="w-36 text-xs"><Link href={`/assessor/assessment/${plan.id}`}><EvidenceThumb ev={e} size={144} /></Link>
              <p className="mt-1 truncate">{plan.tasks.flatMap((t) => t.criteria).find((c) => c.id === e.criterion_id)?.criterion_code ?? "—"} · {e.caption}</p>
              {e.ai_observation && <p className="text-ai">AI note ✓</p>}</li>))}
          </ul>
        )}
        {results.evidence_missing.length > 0 && <p className="mt-2 text-sm text-warn">Required evidence missing for: {results.evidence_missing.join(", ")}</p>}
      </section>

      {/* Competency profile */}
      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-semibold">Competency profile</h2>
          <p className="text-sm text-ink-3 num">{results.scored_criteria}/{results.total_criteria} criteria scored · overall {results.overall_pct != null ? `${results.overall_pct.toFixed(1)}%` : "—"}</p>
        </div>
        {results.scored_criteria === 0 ? <p className="text-ink-3">No assessor scores yet.</p> : (
          <div className="grid gap-4 lg:grid-cols-2">
            <CompetencyBars title="By competency area" threshold={gaps.required_pct}
              rows={Object.entries(results.competencies).map(([k, v]) => ({ key: k, label: results.competency_labels[k] ?? k, value: v }))} />
            <CompetencyBars title="By official formative dimension (QF §24)" threshold={gaps.required_pct}
              rows={Object.entries(results.dimensions).map(([k, v]) => ({ key: k, label: DIM_LABEL[k] ?? k, value: v }))} />
          </div>
        )}
        {results.summary && <p className="text-sm text-ink-2"><span className="label mr-2">Summary</span>{results.summary.text}{results.summary.provider === "rules" && <span className="text-ink-3"> (generated from computed scores by template)</span>}</p>}
        {results.safety_flags.length > 0 && <Notice tone="bad">Safety-critical criteria scored 0–1: {results.safety_flags.join(", ")}</Notice>}
      </section>

      {/* Gaps */}
      {results.scored_criteria > 0 && (
        <section>
          <h2 className="mb-1 text-lg font-semibold">Skill gaps</h2>
          <p className="mb-3 text-xs text-ink-3">{gaps.required_source}. {gaps.note}</p>
          <div className="grid gap-3 md:grid-cols-2">
            {gaps.areas.filter((a) => a.status === "gap").map((a) => (
              <div key={a.competency_key} className="sheet p-3">
                <p className="font-semibold">{a.label} <span className="ml-1 text-sm font-normal num">required {a.required}% · demonstrated {a.demonstrated?.toFixed(1)}% · <span className="font-semibold text-warn">gap {a.gap}</span></span></p>
                <ul className="mt-1.5 text-sm">{a.learning_topics.map((t, i) => (
                  <li key={i} className="flex gap-2"><span className={`stamp shrink-0 ${t.source === "official" ? "stamp-official" : "border border-rule-strong text-ink-3"}`}>{t.source === "official" ? `LO${t.lo_number}` : "Suggested"}</span><span>{t.topic} <span className="text-ink-3">({t.because})</span></span></li>))}
                </ul>
              </div>
            ))}
            {gaps.areas.every((a) => a.status !== "gap") && <p className="text-ink-3">No gaps against the threshold in the assessed scope.</p>}
          </div>
          <details className="mt-3 text-sm"><summary className="cursor-pointer text-ink-2">{gaps.not_assessed_in_prototype.length} learning outcomes not assessed in this prototype (not assumed competent)</summary>
            <ul className="mt-1 columns-1 text-xs text-ink-3 md:columns-2">{gaps.not_assessed_in_prototype.map((l) => <li key={l.lo_number}>LO{l.lo_number}: {l.title}</li>)}</ul></details>
        </section>
      )}

      {/* AI recommendation vs Assessor decision */}
      <section aria-label="Recommendation and decision" className="grid gap-4 lg:grid-cols-2">
        <RecommendationPanel plan={plan} rec={rec} onRec={setRec} onPlan={load} />
        <DecisionPanel plan={plan} rec={rec} decision={decision} onDone={async (d) => { setDecision(d); await load(); }} />
      </section>
    </div>
  );
}

function RecommendationPanel({ plan, rec, onRec, onPlan }: { plan: Plan; rec: Recommendation | null; onRec: (r: Recommendation) => void; onPlan: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const scored = ["SCORED", "RECOMMENDATION_GENERATED", "UNDER_ASSESSOR_REVIEW"].includes(plan.status);
  async function gen() {
    setBusy(true); setErr(null);
    try { onRec(await makeRecommendation(plan.id)); await onPlan(); } catch (e) { setErr(e instanceof ApiError ? e.message : "Could not generate."); }
    setBusy(false);
  }
  return (
    <div className="ai-panel p-4">
      <div className="flex items-center justify-between"><h2 className="font-semibold">AI assistance — recommendation</h2><Stamp kind="ai" /></div>
      {!rec ? (
        <div className="mt-3 text-sm">
          <p className="text-ink-2">Generated from assessor-confirmed scores, evidence coverage and safety rules once every criterion is scored.</p>
          {err && <div className="mt-2"><Notice tone="bad">{err}</Notice></div>}
          <Button className="mt-3" disabled={!scored || busy} onClick={gen}>{busy ? "Generating…" : "Generate recommendation"}</Button>
        </div>
      ) : (
        <div className="mt-3 flex flex-col gap-3 text-sm">
          <p className="label">RPL assessment summary · {rec.status_label}</p>
          <span className={`stamp self-start border text-sm ${OUTCOME[rec.outcome].tone}`}>{OUTCOME[rec.outcome].icon} AI recommendation: {OUTCOME[rec.outcome].label}</span>
          <dl className="grid grid-cols-3 gap-px bg-rule text-center">
            {[["Competency coverage", `${Math.round(rec.competency_coverage * 100)}%`], ["Evidence coverage", `${Math.round(rec.evidence_coverage * 100)}%`], ["Overall", rec.overall_pct != null ? `${rec.overall_pct.toFixed(1)}%` : "—"]].map(([k, v]) => (
              <div key={k} className="bg-sheet p-2"><dt className="text-[0.6875rem] text-ink-3">{k}</dt><dd className="text-lg font-semibold num">{v}</dd></div>))}
          </dl>
          <table className="w-full text-xs">
            <caption className="label mb-1 text-left">Why — every rule evaluated</caption>
            <tbody>{rec.rule_trace.map((r) => (
              <tr key={r.rule} className="border-b border-rule align-top last:border-0">
                <td className="py-1.5 pr-2 font-mono">{r.rule}</td>
                <td className={`py-1.5 pr-2 font-bold ${r.passed ? "text-ok" : "text-bad"}`}>{r.passed ? "✓ pass" : "✕ fail"}</td>
                <td className="py-1.5"><span className="font-medium">{r.label}</span><br /><span className="text-ink-2">{r.detail}</span><br /><span className="text-ink-3">{r.source}</span></td>
              </tr>))}
            </tbody>
          </table>
          {rec.flags.length > 0 && <ul className="text-xs">{rec.flags.map((f) => <li key={f}><span className="font-bold text-warn">!</span> {f}</li>)}</ul>}
          {rec.narrative && <p className="text-ink-2">{rec.narrative}</p>}
          <p className="border-t border-rule pt-2 text-xs font-semibold text-ai">IMPORTANT: {rec.disclaimer}</p>
        </div>
      )}
    </div>
  );
}

function DecisionPanel({ plan, rec, decision, onDone }: { plan: Plan; rec: Recommendation | null; decision: Decision | null; onDone: (d: Decision) => Promise<void> }) {
  const [choice, setChoice] = useState<Decision["decision"] | null>(null);
  const [comments, setComments] = useState("");
  const [tasks, setTasks] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const ready = plan.status === "UNDER_ASSESSOR_REVIEW";
  async function submit() {
    if (!choice) return;
    setBusy(true); setErr(null);
    try { const r = await recordDecision({ plan_id: plan.id, decision: choice, comments, reassess_task_codes: choice === "REASSESS" ? tasks : [] }); await onDone(r.decision); }
    catch (e) { setErr(e instanceof ApiError ? (e.details as { fields?: { msg: string }[] })?.fields?.[0]?.msg ?? e.message : "Could not record decision."); }
    setBusy(false);
  }
  return (
    <div className="human-panel p-4">
      <div className="flex items-center justify-between"><h2 className="font-semibold">Assessor decision</h2><Stamp kind="human" /></div>
      {decision ? (
        <div className="mt-3 flex flex-col gap-2 text-sm">
          <span className={`stamp self-start border text-sm ${DECISION[decision.decision].tone}`}>{DECISION[decision.decision].label}</span>
          <p>{decision.comments}</p>
          {decision.reassess_task_codes.length > 0 && <p>Reassess: {decision.reassess_task_codes.join(", ")}</p>}
          <p className="text-xs text-ink-3">Recorded by {decision.assessor?.name} on {new Date(decision.decided_at).toLocaleString()} ·
            {decision.agrees_with_recommendation == null ? " no recommendation" : decision.agrees_with_recommendation ? " agrees with AI recommendation" : " differs from AI recommendation"}</p>
        </div>
      ) : !ready ? <p className="mt-3 text-sm text-ink-2">Available after all criteria are scored and the recommendation is generated. The decision is yours; the recommendation is advisory.</p> : (
        <div className="mt-3 flex flex-col gap-3">
          <fieldset className="flex flex-col gap-1.5">
            <legend className="mb-1 text-sm font-medium">Final decision</legend>
            {(Object.keys(DECISION) as Decision["decision"][]).map((k) => (
              <label key={k} className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-[3px] border px-3 text-sm ${choice === k ? "border-ink bg-ink text-sheet" : "border-rule-strong bg-sheet"}`}>
                <input type="radio" name="decision" className="sr-only" checked={choice === k} onChange={() => setChoice(k)} />{DECISION[k].label}
                {rec && ({ APPROVE: "ELIGIBLE", REJECT: "NOT_YET_READY", REASSESS: "REASSESSMENT_SUGGESTED" } as const)[k] === rec.outcome && <span className="ml-auto text-xs opacity-70">matches AI recommendation</span>}
              </label>))}
          </fieldset>
          {choice === "REASSESS" && (
            <fieldset><legend className="mb-1 text-sm font-medium">Tasks to reassess</legend>
              <div className="flex flex-wrap gap-1.5">{plan.tasks.map((t) => (
                <label key={t.task_code} className="flex min-h-9 items-center gap-1.5 rounded-[3px] border border-rule-strong px-2 text-sm">
                  <input type="checkbox" checked={tasks.includes(t.task_code)} onChange={(e) => setTasks((x) => e.target.checked ? [...x, t.task_code] : x.filter((y) => y !== t.task_code))} />{t.task_code}</label>))}
              </div></fieldset>
          )}
          <label className="text-sm font-medium" htmlFor="dec-comments">Assessor comments (min 10 characters)</label>
          <textarea id="dec-comments" rows={4} value={comments} onChange={(e) => setComments(e.target.value)} className="rounded-[3px] border border-rule-strong bg-sheet px-3 py-2 text-sm" />
          {err && <Notice tone="bad">{err}</Notice>}
          <Button size="lg" disabled={!choice || comments.trim().length < 10 || busy} onClick={submit}>{busy ? "Recording…" : "Record final decision"}</Button>
          <p className="text-xs text-ink-3">Recorded under your name and assessor code in the audit trail. Cannot be changed afterwards.</p>
        </div>
      )}
    </div>
  );
}
