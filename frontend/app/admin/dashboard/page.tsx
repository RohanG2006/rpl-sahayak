"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Kpi, StatusBadge } from "@/components/staff";
import { Notice, Spinner, Stamp } from "@/components/ui";
import { getOverview, getSyncLog, type Overview, type SyncRow } from "@/lib/data/admin";
import { ApiError } from "@/lib/api";
import { PLAN_STATES } from "@/lib/workflow";

const pct = (x: number | null) => (x == null ? null : `${Math.round(x * 100)}%`);
const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);

export default function AdminDashboard() {
  const [o, setO] = useState<Overview | null>(null);
  const [sync, setSync] = useState<SyncRow[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([getOverview(), getSyncLog()]).then(([a, b]) => { setO(a); setSync(b); })
      .catch((e) => setErr(e instanceof ApiError ? e.message : "Could not load overview."));
  }, []);
  if (err) return <Notice tone="bad">{err}</Notice>;
  if (!o) return <Spinner label="Loading overview…" />;
  const plans = sum(o.plans_by_status);
  const maxPlan = Math.max(1, ...Object.values(o.plans_by_status));

  return (
    <div className="flex flex-col gap-8">
      <header><p className="label">Administration</p><h1 className="mt-1 text-2xl font-semibold tracking-tight">System overview</h1></header>

      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-[3px] border border-rule bg-rule md:grid-cols-4">
        <Kpi label="Workers" value={o.users_by_role.worker ?? 0} emphasis sub={Object.entries(o.workers_by_origin).map(([k, v]) => `${v} ${k}`).join(" · ")} />
        <Kpi label="Assessors" value={o.users_by_role.assessor ?? 0} emphasis sub={<Link className="underline" href="/admin/assessors">Manage users →</Link>} />
        <Kpi label="Assessment plans" value={plans} emphasis sub={Object.entries(o.decisions).map(([k, v]) => `${v} ${k.toLowerCase()}`).join(" · ") || "no decisions yet"} />
        <Kpi label="Audit events today" value={o.audit_events_today} emphasis sub={<Link className="underline" href="/admin/audit">Audit log →</Link>} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="sheet p-4">
          <h2 className="font-semibold">Plans by workflow state</h2>
          {plans === 0 ? <p className="mt-2 text-sm text-ink-3">No plans yet.</p> : (
            <ul className="mt-3 flex flex-col gap-1.5">
              {PLAN_STATES.filter((s) => o.plans_by_status[s]).map((s) => (
                <li key={s} className="grid grid-cols-[minmax(0,13rem)_1fr_2.5rem] items-center gap-2 text-sm">
                  <StatusBadge status={s} />
                  <span className="h-3 bg-rule/40"><span className="block h-full rounded-r-[4px] bg-[var(--seq-4)]" style={{ width: `${(o.plans_by_status[s] / maxPlan) * 100}%` }} /></span>
                  <span className="text-right font-semibold num">{o.plans_by_status[s]}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="ai-panel p-4">
          <div className="flex items-center justify-between"><h2 className="font-semibold">AI governance</h2><Stamp kind="ai" /></div>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <div><dt className="label">AI outputs logged</dt><dd className="text-xl font-semibold num">{o.ai.observations}</dd>
              <dd className="text-xs text-ink-3">{Object.entries(o.ai.by_provider).map(([k, v]) => `${v} ${k}`).join(" · ")}</dd></div>
            <div><dt className="label">Fallback to rules</dt><dd className="text-xl font-semibold num">{pct(o.ai.fallback_rate) ?? "—"}</dd>
              <dd className="text-xs text-ink-3">LLM output invalid twice or provider down</dd></div>
            <div><dt className="label">Scores with an AI suggestion</dt><dd className="text-xl font-semibold num">{o.ai.scores_with_ai_suggestion}</dd></div>
            <div><dt className="label">Assessor overrides of AI</dt><dd className="text-xl font-semibold num">{o.ai.assessor_overrides} {o.ai.override_rate != null && <span className="text-sm font-normal text-ink-3">({pct(o.ai.override_rate)})</span>}</dd></div>
          </dl>
          <p className="mt-3 text-xs text-ink-3">AI suggestions never enter scores; only assessor-confirmed scores count. A high override rate signals the AI is not helping and should be reviewed.</p>
        </section>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="sheet p-4">
          <h2 className="font-semibold">Evidence</h2>
          <p className="mt-2 text-sm"><span className="text-2xl font-semibold num">{o.evidence.total}</span> items · {o.evidence.captured_offline} captured offline · {Object.entries(o.evidence.by_kind).map(([k, v]) => `${v} ${k}`).join(" · ") || "—"}</p>
        </section>
        <section className="sheet p-4">
          <h2 className="font-semibold">Qualification sources <Stamp kind="official" /></h2>
          <ul className="mt-2 flex flex-col gap-2 text-sm">{o.qualifications.map((q) => (
            <li key={q.code}><Link href="/admin/qualifications" className="font-medium underline-offset-2 hover:underline">{q.title} · {q.code}</Link> · {q.los} LOs · {q.assessable ? "assessable" : "matching only"}
              <span className="block break-all font-mono text-[0.6875rem] text-ink-3">sha256 {q.sha256.slice(0, 16)}… · retrieved {q.retrieved_at.slice(0, 10)}</span></li>))}
          </ul>
        </section>
      </div>

      <section>
        <div className="mb-2 flex items-baseline justify-between"><h2 className="text-lg font-semibold">Offline sync</h2>
          <p className="text-sm text-ink-3">{Object.entries(o.sync.by_status).map(([k, v]) => `${v} ${k}`).join(" · ") || "no syncs yet"}{o.sync.last_received && ` · last ${new Date(o.sync.last_received).toLocaleString()}`}</p></div>
        {sync.length > 0 && (
          <div className="overflow-x-auto rounded-[3px] border border-rule bg-sheet">
            <table className="w-full min-w-[640px] text-sm">
              <thead><tr className="border-b border-rule-strong text-left text-xs uppercase tracking-wider text-ink-3"><th className="px-3 py-2">Received</th><th className="px-3 py-2">Device</th><th className="px-3 py-2">Operation</th><th className="px-3 py-2">Result</th></tr></thead>
              <tbody>{sync.slice(0, 12).map((r) => (
                <tr key={r.client_op_id} className="border-b border-rule last:border-0">
                  <td className="px-3 py-1.5 num">{new Date(r.received_at).toLocaleString()}</td><td className="px-3 py-1.5 font-mono text-xs">{r.client_id.slice(0, 14)}</td>
                  <td className="px-3 py-1.5">{r.entity}.{r.op}</td>
                  <td className={`px-3 py-1.5 font-semibold ${r.status === "applied" ? "text-ok" : r.status === "conflict" ? "text-warn" : r.status === "rejected" || r.status === "failed" ? "text-bad" : ""}`}>{r.status}{r.detail ? <span className="font-normal text-ink-3"> · {r.detail}</span> : null}</td>
                </tr>))}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
