"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Kpi } from "@/components/staff";
import { Notice, Spinner } from "@/components/ui";
import { getDashboard, type Dashboard } from "@/lib/data/assessor";
import { getOverview, type Overview } from "@/lib/data/admin";
import { api, ApiError } from "@/lib/api";

type Cons = { available: boolean; label: string; change: Record<string, { before: number; after: number; improved: boolean }> };
const pct = (x: number | null | undefined) => (x == null ? null : `${Math.round(x * 100)}%`);

export default function AdminAnalytics() {
  const [d, setD] = useState<Dashboard | null>(null);
  const [o, setO] = useState<Overview | null>(null);
  const [c, setC] = useState<Cons | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([getDashboard(), getOverview(), api<Cons>("/analytics/consistency")]).then(([a, b, x]) => { setD(a); setO(b); setC(x); })
      .catch((e) => setErr(e instanceof ApiError ? e.message : "Could not load analytics."));
  }, []);
  if (err) return <Notice tone="bad">{err}</Notice>;
  if (!d || !o || !c) return <Spinner label="Loading analytics…" />;
  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-2xl font-semibold tracking-tight">Assessment analytics</h1>
      <section>
        <h2 className="mb-2 text-lg font-semibold">Live assessments (all assessors)</h2>
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-[3px] border border-rule bg-rule md:grid-cols-4">
          <Kpi label="Plans" value={d.assigned} sub={`${d.in_progress} in progress · ${d.pending_review} pending review`} />
          <Kpi label="Decisions" value={d.completed} sub={`${d.approved} approved · ${d.reassessments} reassessment`} />
          <Kpi label="Average score" value={d.average_score == null ? null : `${d.average_score}%`} sub="assessor-confirmed scores" />
          <Kpi label="Evidence coverage" value={pct(d.evidence_coverage)} sub={`${d.evidence_items} items, ${o.evidence.captured_offline} captured offline`} />
          <Kpi label="AI-assisted cases" value={d.ai_assisted_cases} />
          <Kpi label="AI fallback rate" value={pct(o.ai.fallback_rate)} sub="rules used when the LLM failed" />
          <Kpi label="Assessor overrides of AI" value={pct(o.ai.override_rate)} sub={`${o.ai.assessor_overrides} of ${o.ai.scores_with_ai_suggestion}`} />
          <Kpi label="Decisions agreeing with recommendation" value={pct(d.decision_agreement_with_recommendation)} />
        </div>
        <p className="mt-2 text-xs text-ink-3">{d.note}</p>
      </section>
      <section className="sheet p-4">
        <h2 className="font-semibold">Assessor consistency</h2>
        {c.available ? (
          <>
            <p className="mt-1 text-xs font-semibold uppercase text-warn">{c.label}</p>
            <p className="mt-2 text-sm">Mean spread of case scores across 5 assessors: <b className="num">{c.change.mean_case_sd.before.toFixed(1)} → {c.change.mean_case_sd.after.toFixed(1)} pts</b> · Fleiss&apos; κ <b className="num">{c.change.fleiss_kappa.before.toFixed(2)} → {c.change.fleiss_kappa.after.toFixed(2)}</b> · ICC(2,1) <b className="num">{c.change.icc_2_1.before.toFixed(2)} → {c.change.icc_2_1.after.toFixed(2)}</b></p>
            <Link href="/assessor/consistency" className="mt-2 inline-block text-sm font-semibold underline">Open the consistency dashboard →</Link>
          </>
        ) : <p className="text-sm text-ink-3">No multi-rater dataset loaded.</p>}
      </section>
    </div>
  );
}
