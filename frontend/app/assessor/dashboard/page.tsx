"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Kpi, OUTCOME, StatusBadge } from "@/components/staff";
import { Notice, Spinner, Stamp } from "@/components/ui";
import { getCandidates, getDashboard, type CandidateRow, type Dashboard } from "@/lib/data/assessor";
import { useSession } from "@/lib/useSession";
import { ApiError } from "@/lib/api";

const pct = (x: number | null | undefined) => (x == null ? null : `${Math.round(x * 100)}%`);

export default function AssessorDashboard() {
  const s = useSession();
  const [k, setK] = useState<Dashboard | null>(null);
  const [rows, setRows] = useState<CandidateRow[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([getDashboard(), getCandidates({ status: "pending", page_size: 8 })])
      .then(([d, c]) => { setK(d); setRows(c.rows); })
      .catch((e) => setErr(e instanceof ApiError ? e.message : "Could not load dashboard."));
  }, []);
  if (err) return <Notice tone="bad">{err}</Notice>;
  if (!k) return <Spinner label="Loading dashboard…" />;

  return (
    <div className="flex flex-col gap-8">
      <header>
        <p className="label">{s?.user.role === "admin" ? "All assessors" : `Assessor ${s?.user.assessor_code ?? ""}`}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Caseload</h1>
      </header>

      <section aria-label="Caseload">
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-[3px] border border-rule bg-rule md:grid-cols-4">
          <Kpi label="Candidates assigned" value={k.assigned} emphasis />
          <Kpi label="Pending review" value={k.pending_review} emphasis sub="Evidence in, awaiting scoring or decision" />
          <Kpi label="Completed" value={k.completed} emphasis sub={`${k.approved} approved`} />
          <Kpi label="Reassessments" value={k.reassessments} emphasis />
        </div>
        <div className="mt-px grid grid-cols-2 gap-px overflow-hidden rounded-[3px] border border-rule bg-rule md:grid-cols-4">
          <Kpi label="Average assessment score" value={k.average_score == null ? null : `${k.average_score}%`} sub="Assessor-confirmed scores only" />
          <Kpi label="Evidence coverage" value={pct(k.evidence_coverage)} sub={`${k.evidence_items} evidence items`} />
          <Kpi label="AI-assisted cases" value={k.ai_assisted_cases} sub="Cases with AI evidence observations" />
          <Kpi label="Decisions agreeing with recommendation" value={pct(k.decision_agreement_with_recommendation)} sub={<Link className="underline" href="/assessor/consistency">Assessor consistency →</Link>} />
        </div>
      </section>

      <section>
        <div className="mb-2 flex items-end justify-between">
          <h2 className="text-lg font-semibold">Needs your attention</h2>
          <Link href="/assessor/candidates?status=pending" className="text-sm font-medium underline underline-offset-2">All pending →</Link>
        </div>
        {rows.length === 0 ? <p className="text-ink-3">Nothing waiting for review.</p> : (
          <ul className="divide-y divide-rule rounded-[3px] border border-rule bg-sheet">
            {rows.map((r) => (
              <li key={r.plan_id}>
                <Link href={`/assessor/candidates/${r.plan_id}`} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 hover:bg-paper">
                  <span className="min-w-40 flex-1 font-semibold">{r.candidate} {r.data_origin === "synthetic" && <Stamp kind="synthetic" />}</span>
                  <span className="text-sm text-ink-3 num">{r.scored} criteria scored · {r.evidence_items} evidence</span>
                  {r.recommendation && <span className={`stamp border ${OUTCOME[r.recommendation as keyof typeof OUTCOME].tone}`}>{OUTCOME[r.recommendation as keyof typeof OUTCOME].label}</span>}
                  <StatusBadge status={r.status} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
      <p className="text-xs text-ink-3">{k.note}</p>
    </div>
  );
}
