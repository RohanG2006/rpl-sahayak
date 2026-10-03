"use client";
import { useEffect, useMemo, useState } from "react";
import { Notice, Spinner } from "@/components/ui";
import { api, ApiError } from "@/lib/api";

type ModeStats = {
  mean_case_sd: number; mean_case_variance: number; mean_case_range: number; max_case_range: number; exact_agreement: number;
  adjacent_agreement: number; fleiss_kappa: number; mean_pairwise_weighted_kappa: number; pairwise_weighted_kappa: Record<string, number>;
  icc_2_1: number; assessor_mean: Record<string, number>; assessor_sd: Record<string, number>; score_distribution: Record<string, number[]>;
  n_items: number; n_cases: number; n_assessors: number;
};
type CaseMode = { overall: Record<string, number>; spread: { mean: number; sd: number; variance: number; range: number }; tasks: Record<string, Record<string, number>> };
type Change = { before: number; after: number; change: number; relative_pct: number | null; improved: boolean };
type Data = {
  label: string; available: boolean; parameters: { parameters: Record<string, number | string | string[]>; assessor_severity_drawn: Record<string, number>; generated_by: string };
  modes: { baseline: ModeStats; standardised: ModeStats }; cases: Record<string, { baseline: CaseMode; standardised: CaseMode }>;
  change: Record<string, Change>; featured_case: { case_id: string; rule: string }; assessors: string[]; case_ids: string[];
};

const METRICS: { key: string; label: string; fmt: (x: number) => string; better: "lower" | "higher"; what: string }[] = [
  { key: "mean_case_sd", label: "Mean SD of case score across assessors", fmt: (x) => `${x.toFixed(1)} pts`, better: "lower", what: "Spread of the 5 assessors' overall % for the same case, averaged over 20 cases" },
  { key: "mean_case_variance", label: "Mean variance of case score", fmt: (x) => x.toFixed(1), better: "lower", what: "Sample variance (pts²) of overall % per case, averaged" },
  { key: "mean_case_range", label: "Mean range (max − min)", fmt: (x) => `${x.toFixed(1)} pts`, better: "lower", what: "Gap between most lenient and strictest assessor per case" },
  { key: "exact_agreement", label: "Exact agreement (criterion level)", fmt: (x) => `${(x * 100).toFixed(1)}%`, better: "higher", what: "Share of assessor pairs giving the identical 0–4 score" },
  { key: "adjacent_agreement", label: "Agreement within ±1", fmt: (x) => `${(x * 100).toFixed(1)}%`, better: "higher", what: "Share of assessor pairs within one rubric point" },
  { key: "mean_pairwise_weighted_kappa", label: "Mean quadratic-weighted Cohen's κ", fmt: (x) => x.toFixed(3), better: "higher", what: "Average over the 10 assessor pairs; ordinal 0–4 scale" },
  { key: "fleiss_kappa", label: "Fleiss' κ (5 raters)", fmt: (x) => x.toFixed(3), better: "higher", what: "Multi-rater chance-corrected agreement; treats 0–4 as nominal (conservative)" },
  { key: "icc_2_1", label: "ICC(2,1) on overall %", fmt: (x) => x.toFixed(3), better: "higher", what: "Two-way random, absolute agreement, single rater (Shrout & Fleiss 1979)" },
];

const X = (v: number) => `${Math.max(0, Math.min(100, v))}%`;

export default function ConsistencyPage() {
  const [d, setD] = useState<Data | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [tip, setTip] = useState<{ text: string; x: number; y: number } | null>(null);
  useEffect(() => { api<Data>("/analytics/consistency").then((x) => { setD(x); setSel(x.featured_case?.case_id ?? null); }).catch((e) => setErr(e instanceof ApiError ? e.message : "Could not load analytics.")); }, []);

  const caseOrder = useMemo(() => d ? [...d.case_ids].sort((a, b) => d.cases[b].baseline.spread.range - d.cases[a].baseline.spread.range) : [], [d]);
  if (err) return <Notice tone="bad">{err}</Notice>;
  if (!d) return <Spinner label="Computing agreement statistics…" />;
  if (!d.available) return <Notice tone="info">No multi-rater dataset loaded. Run scripts/generate_consistency.py and seed.</Notice>;
  const B = d.modes.baseline, S = d.modes.standardised;
  const fc = d.cases[d.featured_case.case_id];
  const p = d.parameters.parameters;
  const show = (e: React.MouseEvent, text: string) => setTip({ text, x: e.clientX, y: e.clientY });

  return (
    <div className="flex flex-col gap-8" onMouseLeave={() => setTip(null)}>
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Assessor consistency</h1>
        <div role="note" className="mt-3 border-2 border-dashed border-warn bg-warn-wash px-4 py-3 text-sm">
          <p className="font-bold uppercase tracking-wide text-warn">{d.label}</p>
          <p className="mt-1 text-ink">The same {B.n_cases} synthetic cases were rated on all {B.n_items / B.n_cases} rubric criteria by {B.n_assessors} synthetic assessors, once in a <b>baseline</b> (unassisted) mode and once in the <b>standardised</b> workflow.
            Ratings come from a seeded simulation whose assumptions (smaller leniency bias and noise when anchors + evidence checklists are used) are listed below. <b>The size of any change is a consequence of those assumptions.</b> What this page demonstrates is the measurement pipeline — the same statistics run unchanged on real multi-assessor ratings.</p>
        </div>
      </header>

      {/* Featured case: spec block */}
      <section className="grid gap-4 md:grid-cols-2">
        {(["baseline", "standardised"] as const).map((m) => (
          <div key={m} className={`sheet p-4 ${m === "standardised" ? "border-ink" : ""}`}>
            <p className="label">{m === "baseline" ? "Before standardisation" : "After standardised workflow"} · case {d.featured_case.case_id}</p>
            <table className="mt-2 w-full text-sm"><tbody>
              {d.assessors.map((a) => <tr key={a} className="border-b border-rule last:border-0"><td className="py-1">Assessor {a}</td><td className="py-1 text-right font-semibold num">{fc[m].overall[a].toFixed(1)}%</td></tr>)}
            </tbody></table>
            <p className="mt-2 text-sm num">Variance <b>{fc[m].spread.variance.toFixed(1)}</b> · SD {fc[m].spread.sd.toFixed(1)} · range {fc[m].spread.range.toFixed(1)} pts</p>
          </div>
        ))}
        <p className="text-xs text-ink-3 md:col-span-2">Change in variance for this case (computed): {(fc.standardised.spread.variance - fc.baseline.spread.variance).toFixed(1)} ({((fc.standardised.spread.variance / fc.baseline.spread.variance - 1) * 100).toFixed(0)}%). Case chosen by rule: {d.featured_case.rule}.</p>
      </section>

      {/* Metric table */}
      <section>
        <h2 className="mb-2 text-lg font-semibold">All cases — computed statistics</h2>
        <div className="overflow-x-auto rounded-[3px] border border-rule bg-sheet">
          <table className="w-full min-w-[720px] text-sm">
            <thead><tr className="border-b border-rule-strong text-left text-xs uppercase tracking-wider text-ink-3">
              <th className="px-3 py-2 font-semibold">Measure</th><th className="px-3 py-2 text-right font-semibold">Baseline</th><th className="px-3 py-2 text-right font-semibold">Standardised</th><th className="px-3 py-2 text-right font-semibold">Change</th></tr></thead>
            <tbody>{METRICS.map((m) => {
              const c = d.change[m.key];
              return (
                <tr key={m.key} className="border-b border-rule last:border-0">
                  <td className="px-3 py-2"><span className="font-medium">{m.label}</span><span className="block text-xs text-ink-3">{m.what} · {m.better} is better</span></td>
                  <td className="px-3 py-2 text-right num">{m.fmt(c.before)}</td>
                  <td className="px-3 py-2 text-right font-semibold num">{m.fmt(c.after)}</td>
                  <td className="px-3 py-2 text-right num"><span className={c.improved ? "text-ok" : "text-bad"}>{c.improved ? "▲ better" : "▼ worse"}</span> {c.relative_pct != null ? `${c.relative_pct > 0 ? "+" : ""}${c.relative_pct.toFixed(0)}%` : ""}</td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>
      </section>

      {/* Dumbbell: assessor leniency */}
      <section>
        <h2 className="text-lg font-semibold">Assessor leniency — mean case score</h2>
        <p className="mb-3 text-sm text-ink-3">Each row is one synthetic assessor&apos;s average overall % across the 20 cases. Converging dots = assessors scoring the same candidates more alike.</p>
        <figure className="sheet p-4">
          <div className="mb-3 flex gap-4 text-xs"><span><span aria-hidden className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full border-2 border-[var(--seq-3)] bg-sheet align-middle" />Baseline</span><span><span aria-hidden className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full bg-[var(--seq-5)] align-middle" />Standardised</span></div>
          <ul className="flex flex-col gap-3">{d.assessors.map((a) => {
            const b = B.assessor_mean[a], s = S.assessor_mean[a];
            return (
              <li key={a} className="grid grid-cols-[3rem_1fr_7rem] items-center gap-2 text-sm">
                <span className="font-mono">{a}</span>
                <span className="relative h-6">
                  <span aria-hidden className="absolute top-1/2 h-px w-full bg-rule" />
                  <span aria-hidden className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-[var(--seq-3)]" style={{ left: X(Math.min(b, s)), width: `${Math.abs(b - s)}%` }} />
                  <span className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--seq-3)] bg-sheet" style={{ left: X(b) }} onMouseMove={(e) => show(e, `${a} baseline mean ${b.toFixed(1)}%`)} />
                  <span className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--seq-5)] ring-2 ring-sheet" style={{ left: X(s) }} onMouseMove={(e) => show(e, `${a} standardised mean ${s.toFixed(1)}%`)} />
                </span>
                <span className="text-right text-xs num">{b.toFixed(1)} → <b>{s.toFixed(1)}</b></span>
              </li>
            );
          })}</ul>
          <div aria-hidden className="ml-[3.5rem] mr-[7.5rem] mt-2 flex justify-between text-[0.6875rem] text-ink-3 num"><span>0%</span><span>50%</span><span>100%</span></div>
          <figcaption className="sr-only">Assessor means: {d.assessors.map((a) => `${a} ${B.assessor_mean[a].toFixed(1)} to ${S.assessor_mean[a].toFixed(1)}`).join("; ")}</figcaption>
        </figure>
      </section>

      {/* Strip plots: per-case spread */}
      <section>
        <h2 className="text-lg font-semibold">Per-case spread of the 5 assessors</h2>
        <p className="mb-3 text-sm text-ink-3">Each row is one case; dots are the five assessors&apos; overall %, the bar spans lowest to highest. Sorted by baseline range. Select a case to see task-level scores.</p>
        <div className="grid gap-4 lg:grid-cols-2">
          {(["baseline", "standardised"] as const).map((m) => (
            <figure key={m} className="sheet p-3">
              <figcaption className="mb-2 text-sm font-semibold">{m === "baseline" ? "Baseline" : "Standardised"} <span className="font-normal text-ink-3">· mean range {d.modes[m].mean_case_range.toFixed(1)} pts</span></figcaption>
              <ul>{caseOrder.map((c) => {
                const cm = d.cases[c][m];
                const vals = Object.values(cm.overall);
                const lo = Math.min(...vals), hi = Math.max(...vals);
                return (
                  <li key={c}>
                    <button onClick={() => setSel(c)} aria-pressed={sel === c} aria-label={`Case ${c}, range ${(hi - lo).toFixed(1)} points`}
                      className={`grid min-h-7 w-full grid-cols-[3rem_1fr] items-center gap-2 px-1 text-left text-xs ${sel === c ? "bg-accent-wash" : "hover:bg-paper"}`}>
                      <span className="font-mono">{c}</span>
                      <span className="relative h-4">
                        <span aria-hidden className="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-[var(--seq-2)]" style={{ left: X(lo), width: `${hi - lo}%` }} />
                        {Object.entries(cm.overall).map(([a, v]) => (
                          <span key={a} className="absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--seq-5)] ring-1 ring-sheet" style={{ left: X(v) }} onMouseMove={(e) => show(e, `${c} · ${a}: ${v.toFixed(1)}%`)} />
                        ))}
                      </span>
                    </button>
                  </li>
                );
              })}</ul>
              <div aria-hidden className="ml-[3.5rem] mt-1 flex justify-between text-[0.6875rem] text-ink-3 num"><span>0%</span><span>50%</span><span>100%</span></div>
            </figure>
          ))}
        </div>
      </section>

      {sel && (
        <section aria-live="polite">
          <h2 className="mb-2 text-lg font-semibold">Case {sel} — task scores by assessor</h2>
          <div className="overflow-x-auto rounded-[3px] border border-rule bg-sheet">
            <table className="w-full min-w-[760px] text-xs num">
              <thead><tr className="border-b border-rule-strong"><th className="px-2 py-2 text-left">Mode</th><th className="px-2 py-2 text-left">Assessor</th>
                {Object.keys(d.cases[sel].baseline.tasks[d.assessors[0]]).map((t) => <th key={t} className="px-2 py-2 text-right">{t}</th>)}<th className="px-2 py-2 text-right">Overall</th></tr></thead>
              <tbody>{(["baseline", "standardised"] as const).flatMap((m) => d.assessors.map((a, i) => (
                <tr key={m + a} className={`border-b border-rule ${i === d.assessors.length - 1 ? "border-b-rule-strong" : ""}`}>
                  <td className="px-2 py-1.5">{i === 0 ? m : ""}</td><td className="px-2 py-1.5 font-mono">{a}</td>
                  {Object.values(d.cases[sel][m].tasks[a]).map((v, j) => <td key={j} className="px-2 py-1.5 text-right">{v.toFixed(0)}</td>)}
                  <td className="px-2 py-1.5 text-right font-semibold">{d.cases[sel][m].overall[a].toFixed(1)}</td>
                </tr>)))}</tbody>
            </table>
          </div>
        </section>
      )}

      {/* Score distributions: sequential-shaded grid */}
      <section>
        <h2 className="mb-2 text-lg font-semibold">Rubric score distribution by assessor</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {(["baseline", "standardised"] as const).map((m) => (
            <table key={m} className="sheet w-full text-xs num">
              <caption className="p-2 text-left text-sm font-semibold">{m === "baseline" ? "Baseline" : "Standardised"} <span className="font-normal text-ink-3">(share of each assessor&apos;s {B.n_items} ratings)</span></caption>
              <thead><tr><th className="px-2 py-1 text-left">Assessor</th>{[0, 1, 2, 3, 4].map((s) => <th key={s} className="px-2 py-1">{s}</th>)}</tr></thead>
              <tbody>{d.assessors.map((a) => {
                const row = d.modes[m].score_distribution[a]; const tot = row.reduce((x, y) => x + y, 0);
                return <tr key={a}><td className="px-2 py-1 font-mono">{a}</td>{row.map((n, s) => {
                  const share = n / tot; const step = share > 0.4 ? 5 : share > 0.25 ? 4 : share > 0.15 ? 3 : share > 0.05 ? 2 : 1;
                  return <td key={s} className={`border border-sheet px-2 py-1.5 text-center ${step >= 4 ? "text-white" : "text-ink"}`} style={{ background: `var(--seq-${step})` }} title={`${a} gave ${s}: ${n} (${(share * 100).toFixed(0)}%)`}>{(share * 100).toFixed(0)}%</td>;
                })}</tr>;
              })}</tbody>
            </table>
          ))}
        </div>
      </section>

      <section className="sheet p-4 text-sm">
        <h2 className="font-semibold">Simulation parameters & method</h2>
        <dl className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 md:grid-cols-4">
          {Object.entries(p).filter(([k]) => k !== "assessors").map(([k, v]) => <div key={k}><dt className="text-xs text-ink-3">{k}</dt><dd className="font-mono">{String(v)}</dd></div>)}
        </dl>
        <p className="mt-3 text-ink-2">Drawn assessor severity (leniency +, strictness −): {Object.entries(d.parameters.assessor_severity_drawn).map(([a, v]) => `${a} ${v > 0 ? "+" : ""}${v}`).join(", ")}.</p>
        <p className="mt-2 text-ink-2">Baseline rating = round(clip(true level + severity + noise σ={String(p.base_noise_sd)})). Standardised = round(clip(true level + {String(p.k_severity)}×severity + noise σ={String(p.std_noise_sd)})). Case overall % uses the same weighted rubric formula as live assessments. Generated by <span className="font-mono">{d.parameters.generated_by}</span>; dataset <span className="font-mono">data/demo/consistency_test_set.csv</span>.</p>
        <p className="mt-2 text-ink-2">To validate for real: have several assessors score the same recorded evidence with and without the rubric, load their ratings into this table, and the same statistics apply.</p>
      </section>
      {tip && <div role="tooltip" className="pointer-events-none fixed z-50 rounded-[3px] bg-ink px-2 py-1 text-xs text-sheet" style={{ left: tip.x + 12, top: tip.y - 28 }}>{tip.text}</div>}
    </div>
  );
}
