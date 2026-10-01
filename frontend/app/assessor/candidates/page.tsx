"use client";
import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { OUTCOME, StatusBadge, DECISION } from "@/components/staff";
import { Button, Notice, Spinner, Stamp } from "@/components/ui";
import { getCandidates, type CandidateRow } from "@/lib/data/assessor";
import { ApiError } from "@/lib/api";

const FILTERS = [
  { key: "", label: "All" }, { key: "pending", label: "Pending review" }, { key: "in_progress", label: "In progress" }, { key: "completed", label: "Completed" },
];

export default function CandidatesWrapper() { return <Suspense><Candidates /></Suspense>; }

function Candidates() {
  const params = useSearchParams();
  const router = useRouter();
  const status = params.get("status") ?? "";
  const page = Number(params.get("page") ?? 1);
  const [q, setQ] = useState(params.get("q") ?? "");
  const [data, setData] = useState<{ total: number; rows: CandidateRow[]; page_size: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    getCandidates({ status, q: params.get("q") ?? "", page, page_size: 20 }).then(setData).catch((e) => setErr(e instanceof ApiError ? e.message : "Could not load candidates."));
  }, [status, page, params]);

  const go = (patch: Record<string, string>) => {
    const p = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) v ? p.set(k, v) : p.delete(k);
    router.replace(`/assessor/candidates?${p}`);
  };
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="flex flex-col gap-5">
      <h1 className="text-2xl font-semibold tracking-tight">Candidates</h1>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div role="tablist" aria-label="Status filter" className="flex flex-wrap gap-1">
          {FILTERS.map((f) => (
            <button key={f.key} role="tab" aria-selected={status === f.key} onClick={() => go({ status: f.key, page: "" })}
              className={`min-h-10 rounded-[3px] border px-3 text-sm font-medium ${status === f.key ? "border-ink bg-ink text-sheet" : "border-rule-strong bg-sheet hover:border-ink"}`}>{f.label}</button>
          ))}
        </div>
        <form className="flex w-full gap-2 sm:w-auto" onSubmit={(e) => { e.preventDefault(); go({ q, page: "" }); }}>
          <input aria-label="Search by name" placeholder="Search name" value={q} onChange={(e) => setQ(e.target.value)} className="min-h-10 min-w-0 flex-1 rounded-[3px] border border-rule-strong bg-sheet px-3 text-sm sm:w-48 sm:flex-none" />
          <Button type="submit" variant="secondary">Search</Button>
        </form>
      </div>
      {err && <Notice tone="bad">{err}</Notice>}
      {!data ? <Spinner label="Loading…" /> : (
        <div className="overflow-x-auto rounded-[3px] border border-rule bg-sheet">
          <table className="w-full min-w-[880px] text-sm">
            <thead>
              <tr className="border-b border-rule-strong text-left">
                {["Candidate", "Trade", "Qualification", "Experience", "AI match", "Assessment score", "Status", "Last updated"].map((h) => (
                  <th key={h} scope="col" className={`px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-ink-3 ${["Experience", "AI match", "Assessment score"].includes(h) ? "text-right" : ""}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.length === 0 && <tr><td colSpan={8} className="px-3 py-6 text-center text-ink-3">No candidates match.</td></tr>}
              {data.rows.map((r) => (
                <tr key={r.plan_id} className="border-b border-rule last:border-0 hover:bg-paper">
                  <td className="px-3 py-2.5">
                    <Link href={`/assessor/candidates/${r.plan_id}`} className="font-semibold underline-offset-2 hover:underline">{r.candidate}</Link>
                    {r.data_origin === "synthetic" && <span className="ml-1.5"><Stamp kind="synthetic">Synthetic</Stamp></span>}
                  </td>
                  <td className="px-3 py-2.5">{r.trade}</td>
                  <td className="px-3 py-2.5"><span className="font-mono text-xs">{r.qualification_code}</span></td>
                  <td className="px-3 py-2.5 text-right num">{r.experience_years ?? "—"} yrs</td>
                  <td className="px-3 py-2.5 text-right num">{r.ai_match_pct != null ? `${r.ai_match_pct}%` : "—"}</td>
                  <td className="px-3 py-2.5 text-right num">{r.assessment_score != null ? `${r.assessment_score.toFixed(1)}%` : <span className="text-ink-3">{r.scored}</span>}</td>
                  <td className="px-3 py-2.5">
                    <div className="flex flex-col items-start gap-1">
                      {r.decision ? <span className={`stamp border ${DECISION[r.decision as keyof typeof DECISION].tone}`}>{DECISION[r.decision as keyof typeof DECISION].label}</span> : <StatusBadge status={r.status} />}
                      {r.recommendation && !r.decision && <span className="text-xs text-ink-3">AI rec: {OUTCOME[r.recommendation as keyof typeof OUTCOME].label}</span>}
                    </div>
                  </td>
                  <td className="px-3 py-2.5 text-ink-3 num">{new Date(r.updated_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && pages > 1 && (
        <nav aria-label="Pagination" className="flex items-center gap-2 text-sm">
          <Button variant="secondary" disabled={page <= 1} onClick={() => go({ page: String(page - 1) })}>Previous</Button>
          <span className="num">Page {page} of {pages} · {data.total} candidates</span>
          <Button variant="secondary" disabled={page >= pages} onClick={() => go({ page: String(page + 1) })}>Next</Button>
        </nav>
      )}
    </div>
  );
}
