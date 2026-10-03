"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import EvidenceThumb from "@/components/EvidenceThumb";
import EvidenceViewer from "@/components/EvidenceViewer";
import { StatusBadge } from "@/components/staff";
import { Button, Notice, Spinner, Stamp } from "@/components/ui";
import { getPlan, type Criterion, type Plan, type PlanTask } from "@/lib/data/assessment";
import { scoreTask } from "@/lib/data/assessor";
import { analyzeEvidence, listEvidence, type EvidenceItem } from "@/lib/data/evidence";
import { ApiError } from "@/lib/api";

const SCALE = ["Not demonstrated", "Requires substantial assistance", "Partially demonstrated", "Competent with minor issues", "Competent independently"];
type Draft = Record<string, { score: number | null; note: string }>;

export default function ScoringWorkspace() {
  const { id } = useParams<{ id: string }>();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [tab, setTab] = useState<string>("");
  const [draft, setDraft] = useState<Draft>({});
  const [viewer, setViewer] = useState<{ ev: EvidenceItem; crit?: Criterion; task?: PlanTask } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ tone: "ok" | "bad"; text: string } | null>(null);

  const load = useCallback(async () => {
    const [p, ev] = await Promise.all([getPlan(id), listEvidence({ plan_id: id })]);
    setPlan(p); setEvidence(ev);
    setTab((t) => t || p.tasks[0]?.task_code);
    const d: Draft = {};
    for (const t of p.tasks) for (const c of t.criteria) d[c.criterion_code] = { score: c.score?.final_score ?? null, note: c.score?.assessor_note ?? "" };
    setDraft(d);
  }, [id]);
  useEffect(() => {
    // Initial load runs in a microtask (no synchronous setState in the effect); `live` drops errors after unmount.
    let live = true;
    Promise.resolve().then(() => (live ? load() : undefined)).catch((e) => { if (live) setMsg({ tone: "bad", text: e instanceof ApiError ? e.message : "Could not load assessment." }); });
    return () => { live = false; };
  }, [load]);

  const task = useMemo(() => plan?.tasks.find((t) => t.task_code === tab), [plan, tab]);
  if (!plan) return msg ? <Notice tone="bad">{msg.text}</Notice> : <Spinner label="Loading assessment…" />;
  const locked = ["DECIDED", "REPORT_ISSUED"].includes(plan.status);
  const canScore = !["PLAN_CREATED", "SELF_ASSESSED", "READINESS_EVALUATED"].includes(plan.status) && !locked;
  const evFor = (c: Criterion) => evidence.filter((e) => e.criterion_id === c.id);

  async function analyze(ev: EvidenceItem) {
    setBusy(ev.id);
    try {
      const updated = await analyzeEvidence(ev.id);
      setEvidence((xs) => xs.map((x) => (x.id === ev.id ? updated : x)));
      if (viewer?.ev.id === ev.id) setViewer({ ...viewer, ev: updated });
      setPlan(await getPlan(id));
    } catch (e) { setMsg({ tone: "bad", text: e instanceof ApiError ? e.message : "AI analysis unavailable — continue with manual scoring." }); }
    setBusy(null);
  }

  async function save(t: PlanTask) {
    const scores = t.criteria.filter((c) => draft[c.criterion_code]?.score != null)
      .map((c) => ({ criterion_code: c.criterion_code, final_score: draft[c.criterion_code].score!, assessor_note: draft[c.criterion_code].note.trim() || null }));
    if (!scores.length) return setMsg({ tone: "bad", text: "Select a score for at least one criterion." });
    setBusy("save"); setMsg(null);
    try { setPlan(await scoreTask(plan!.id, t.task_code, scores)); setMsg({ tone: "ok", text: `${t.task_code}: ${scores.length} score(s) recorded.` }); }
    catch (e) { setMsg({ tone: "bad", text: e instanceof ApiError ? e.message : "Could not save scores." }); }
    setBusy(null);
  }

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link href={`/assessor/candidates/${plan.id}`} className="text-sm text-ink-2 underline underline-offset-2">← {plan.worker.full_name}</Link>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Standardised scoring</h1>
          <p className="text-sm text-ink-3">{plan.qualification.title} · {plan.qualification.qualification_code} · NSQF {plan.qualification.nsqf_level}</p>
        </div>
        <div className="flex items-center gap-2"><StatusBadge status={plan.status} />{plan.data_origin === "synthetic" && <Stamp kind="synthetic" />}</div>
      </header>

      <div className="grid gap-2 text-sm md:grid-cols-2">
        <p className="ai-panel px-3 py-2"><Stamp kind="ai" /> <span className="ml-1">Suggestions, observations and confidence. Never counted in results.</span></p>
        <p className="human-panel px-3 py-2"><Stamp kind="human" /> <span className="ml-1">Your 0–4 score against the criterion anchors is the only score used.</span></p>
      </div>

      <nav aria-label="Tasks" className="flex gap-1 overflow-x-auto border-b border-rule">
        {plan.tasks.map((t) => {
          const done = t.criteria.every((c) => c.score?.final_score != null);
          const some = t.criteria.some((c) => c.score?.final_score != null);
          return (
            <button key={t.task_code} onClick={() => setTab(t.task_code)} aria-current={tab === t.task_code ? "page" : undefined}
              className={`-mb-px flex min-h-11 items-center gap-1.5 whitespace-nowrap border-b-2 px-3 text-sm font-semibold ${tab === t.task_code ? "border-ink text-ink" : "border-transparent text-ink-3 hover:text-ink"}`}>
              {t.task_code}<span aria-label={done ? "scored" : some ? "partly scored" : "not scored"} className={`h-2 w-2 rounded-full ${done ? "bg-ok" : some ? "bg-warn" : "border border-ink-3"}`} />
            </button>
          );
        })}
      </nav>

      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}
      {!canScore && !locked && <Notice tone="info">Scoring opens once the candidate starts the practical assessment.</Notice>}
      {locked && <Notice tone="info">Decision recorded — scores are locked.</Notice>}

      {task && (
        <section className="flex flex-col gap-4">
          <div className="sheet p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-lg font-semibold">{task.task_code} · {task.title}</h2>
              <span className="text-xs text-ink-3">LO {task.lo_numbers.join(", ")} · weight {task.weight}</span>
            </div>
            <p className="mt-1 text-ink-2">{task.description}</p>
            <p className="mt-2 text-sm"><span className="label mr-2">Worker submission</span>
              {task.attempt?.status ?? "NOT_STARTED"} · {Object.values(task.attempt?.checklist_state ?? {}).filter(Boolean).length}/{task.steps.length} steps ticked
              {task.attempt?.worker_note && <> · “{task.attempt.worker_note}”</>}</p>
          </div>

          {task.criteria.map((c) => {
            const d = draft[c.criterion_code] ?? { score: null, note: "" };
            const evs = evFor(c);
            const sug = c.score?.ai_suggested_score;
            const latestObs = evs.map((e) => e.ai_observation).find(Boolean);
            const override = sug != null && d.score != null && d.score !== sug;
            return (
              <article key={c.id} className="sheet overflow-hidden" aria-labelledby={`c-${c.id}`}>
                <header className="border-b border-rule px-4 py-3">
                  <p id={`c-${c.id}`} className="font-semibold"><span className="mr-2 font-mono text-sm">{c.criterion_code}</span>{c.text}
                    {c.is_safety_critical && <span className="stamp ml-2 border border-bad bg-bad-wash text-bad">Safety-critical</span>}</p>
                  <p className="mt-0.5 text-xs text-ink-3">{c.qf_criterion_ref} · dimension: {c.qf_dimension} · weight {c.weight}</p>
                </header>
                <div className="grid md:grid-cols-2">
                  <div className="ai-panel m-0 rounded-none border-0 border-l-4 p-4 md:border-r md:border-r-rule">
                    <p className="label mb-2 text-ai">AI assistance</p>
                    {evs.length === 0 ? <p className="text-sm text-ink-3">No evidence linked. A score needs your observation note.</p> : (
                      <ul className="mb-3 flex flex-wrap gap-2">
                        {evs.map((e) => (
                          <li key={e.id}><button onClick={() => setViewer({ ev: e, crit: c, task })} className="block outline-offset-2" aria-label={`Open evidence ${e.caption ?? e.id.slice(0, 8)}`}><EvidenceThumb ev={e} size={64} /></button></li>
                        ))}
                      </ul>
                    )}
                    <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                      <dt className="text-ink-3">Suggested score</dt>
                      <dd className="font-semibold num">{sug != null ? `${sug} — ${SCALE[sug]}` : <span className="font-normal text-ink-3">{latestObs ? "None (evidence not interpretable by rules)" : "—"}</span>}</dd>
                      <dt className="text-ink-3">Confidence</dt><dd className="num">{latestObs?.confidence?.toFixed(2) ?? "—"}</dd>
                    </dl>
                    {latestObs?.output.observed?.slice(0, 3).map((x) => <p key={x} className="mt-1 text-sm"><span aria-hidden className="mr-1 font-bold text-ok">✓</span>{x}</p>)}
                    {latestObs?.output.potentially_missing?.slice(0, 2).map((x) => <p key={x} className="mt-1 text-sm"><span aria-hidden className="mr-1 font-bold text-warn">!</span>{x}</p>)}
                    {latestObs?.output.safety_concerns?.map((x) => <p key={x} className="mt-1 text-sm"><span aria-hidden className="mr-1 font-bold text-bad">⚠</span>{x}</p>)}
                    {evs.some((e) => !e.ai_observation) && canScore && (
                      <Button className="mt-3" variant="secondary" disabled={!!busy} onClick={() => analyze(evs.find((e) => !e.ai_observation)!)}>{busy ? "Analysing…" : "Run AI on evidence"}</Button>
                    )}
                    <p className="mt-3 text-xs font-semibold text-ai">AI assistance only — assessor verification required.</p>
                  </div>
                  <div className="human-panel m-0 rounded-none border-0 border-l-4 p-4">
                    <p className="label mb-2 text-ink">Assessor decision</p>
                    <fieldset disabled={!canScore}>
                      <legend className="sr-only">Score for {c.criterion_code}</legend>
                      <div className="grid grid-cols-5 gap-1">
                        {[0, 1, 2, 3, 4].map((n) => (
                          <label key={n} className={`flex min-h-11 cursor-pointer items-center justify-center rounded-[3px] border text-base font-semibold num ${d.score === n ? "border-ink bg-ink text-sheet" : "border-rule-strong bg-sheet hover:border-ink"} ${sug === n && d.score !== n ? "outline-2 outline-dashed outline-ai -outline-offset-4" : ""}`}
                            title={c.anchors[String(n)]}>
                            <input type="radio" className="sr-only" name={`s-${c.id}`} checked={d.score === n} onChange={() => setDraft((x) => ({ ...x, [c.criterion_code]: { ...d, score: n } }))} />{n}
                          </label>
                        ))}
                      </div>
                      <p className="mt-2 min-h-10 text-sm">{d.score != null ? <><span className="font-semibold">{d.score}: </span>{c.anchors[String(d.score)]}</> : <span className="text-ink-3">Choose a score — anchor text appears here.</span>}</p>
                      {override && <p className="mb-1 text-xs font-semibold text-ink">Override of AI suggestion ({sug} → {d.score}) — recorded in the audit trail.</p>}
                      <label className="mt-1 block text-sm font-medium" htmlFor={`n-${c.id}`}>Observation note {evs.length === 0 && <span className="text-bad">(required — no evidence)</span>}</label>
                      <textarea id={`n-${c.id}`} rows={2} value={d.note} onChange={(e) => setDraft((x) => ({ ...x, [c.criterion_code]: { ...d, note: e.target.value } }))}
                        className="mt-1 w-full rounded-[3px] border border-rule-strong bg-sheet px-3 py-2 text-sm" />
                    </fieldset>
                    {c.score?.confirmed_at && <p className="mt-1 text-xs text-ink-3">Recorded {new Date(c.score.confirmed_at).toLocaleString()}</p>}
                  </div>
                </div>
              </article>
            );
          })}
          {canScore && <div className="sticky bottom-0 -mx-4 border-t border-rule bg-paper px-4 py-3 md:-mx-8 md:px-8"><Button size="lg" disabled={busy === "save"} onClick={() => save(task)}>{busy === "save" ? "Saving…" : `Record scores for ${task.task_code}`}</Button></div>}
        </section>
      )}
      {viewer && <EvidenceViewer ev={viewer.ev} criterion={viewer.crit} task={viewer.task} busy={busy === viewer.ev.id} onAnalyze={() => analyze(viewer.ev)} onClose={() => setViewer(null)} />}
    </div>
  );
}
