"use client";
import { Fragment, useEffect, useState } from "react";
import { Notice, Spinner, Stamp } from "@/components/ui";
import { api, ApiError } from "@/lib/api";

interface Comp { category: string; lo_number: number; year: number | null; title: string; assessment_criteria: string[]; nos_codes_summary: string[]; nos_codes_lo_table: string[]; nos_mismatch: boolean; skill_hours: number | null; knowledge_hours: number | null }
interface Q {
  id: string; title: string; qualification_code: string; ncvet_code: string | null; nsqf_level: number; occupations: string[]; is_assessable: boolean;
  nco_codes: { code: string; title: string }[]; awarding_body: string | null; entry_requirements: string | null; approval_note: string | null; review_note: string | null;
  rpl_notes: string | null; not_in_source: string[]; source: { source_name: string; url: string; sha256: string | null; retrieved_at: string | null };
  competencies: Comp[]; nos: { nos_code: string; lo_numbers: number[] }[];
}

export default function AdminQualifications() {
  const [qs, setQs] = useState<Q[]>([]);
  const [sel, setSel] = useState<string>("DGT/1001");
  const [open, setOpen] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    Promise.all(["DGT/1001", "DGT/1009"].map((c) => api<Q>(`/qualifications/${c}`))).then(setQs).catch((e) => setErr(e instanceof ApiError ? e.message : "Could not load."));
  }, []);
  if (err) return <Notice tone="bad">{err}</Notice>;
  if (!qs.length) return <Spinner label="Loading qualifications…" />;
  const q = qs.find((x) => x.qualification_code === sel)!;
  const trade = q.competencies.filter((c) => c.category === "trade");
  const mismatches = trade.filter((c) => c.nos_mismatch).length;

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Qualification packs</h1>
        <p className="mt-1 text-sm text-ink-2">Official data, read-only. To change it, re-run <span className="font-mono">scripts/ingest_official_qualifications.py</span> against a new source file. It is never edited by hand.</p>
      </header>
      <div role="tablist" className="flex gap-1">{qs.map((x) => (
        <button key={x.id} role="tab" aria-selected={sel === x.qualification_code} onClick={() => { setSel(x.qualification_code); setOpen(null); }}
          className={`min-h-10 rounded-[3px] border px-3 text-sm font-semibold ${sel === x.qualification_code ? "border-ink bg-ink text-sheet" : "border-rule-strong bg-sheet"}`}>{x.title} · {x.qualification_code}</button>))}
      </div>

      <section className="sheet grid gap-4 p-4 md:grid-cols-2">
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          {([["Title", q.title], ["Qualification code", q.qualification_code], ["NCVET code", q.ncvet_code], ["NSQF level", q.nsqf_level],
            ["NCO", q.nco_codes.map((n) => `${n.code} ${n.title}`).join("; ")], ["Awarding body", q.awarding_body], ["Entry", q.entry_requirements],
            ["Approval", q.approval_note], ["Review", q.review_note], ["RPL", q.rpl_notes], ["Use in prototype", q.is_assessable ? "Matching + practical assessment" : "Matching only (no task bank)"]] as [string, unknown][])
            .map(([k, v]) => <Fragment key={k}><dt className="text-ink-3">{k}</dt><dd>{v == null || v === "" ? "—" : String(v)}</dd></Fragment>)}
        </dl>
        <div className="text-sm">
          <p className="label mb-1">Provenance <Stamp kind="official" /></p>
          <p>{q.source.source_name}</p>
          <a className="break-all text-accent underline" href={q.source.url} target="_blank" rel="noreferrer">{q.source.url}</a>
          <p className="mt-1 break-all font-mono text-xs text-ink-3">sha256 {q.source.sha256}</p>
          <p className="text-xs text-ink-3">Retrieved {q.source.retrieved_at?.slice(0, 10)}</p>
          <p className="label mb-1 mt-3">Not in source (left empty, not invented)</p>
          <ul className="list-disc pl-5 text-ink-2">{q.not_in_source.map((x) => <li key={x}>{x}</li>)}</ul>
        </div>
      </section>

      <section>
        <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-lg font-semibold">Learning outcomes ({trade.length})</h2>
          {mismatches > 0 && <p className="text-sm text-warn"><span className="font-bold">!</span> {mismatches} LOs list different NOS codes in the QF summary table (§20) and the LO table. Both are kept as published.</p>}
        </div>
        <div className="overflow-x-auto rounded-[3px] border border-rule bg-sheet">
          <table className="w-full min-w-[760px] text-sm">
            <thead><tr className="border-b border-rule-strong text-left text-xs uppercase tracking-wider text-ink-3">
              <th className="px-3 py-2">LO</th><th className="px-3 py-2">Yr</th><th className="px-3 py-2">Title</th><th className="px-3 py-2">NOS (§20 / LO table)</th><th className="px-3 py-2 text-right">Hours S+K</th><th className="px-3 py-2 text-right">Criteria</th></tr></thead>
            <tbody>{trade.map((c) => (
              <Fragment key={c.lo_number}>
                <tr className="cursor-pointer border-b border-rule hover:bg-paper" onClick={() => setOpen(open === c.lo_number ? null : c.lo_number)} aria-expanded={open === c.lo_number}>
                  <td className="px-3 py-1.5 font-semibold num">{c.lo_number}</td><td className="px-3 py-1.5 num">{c.year ?? "—"}</td>
                  <td className="px-3 py-1.5">{c.title}</td>
                  <td className="px-3 py-1.5 font-mono text-xs">{c.nos_codes_summary.join(", ") || "—"}{c.nos_mismatch && <span className="ml-1 text-warn">/ {c.nos_codes_lo_table.join(", ") || "none"} !</span>}</td>
                  <td className="px-3 py-1.5 text-right num">{c.skill_hours ?? "—"}+{c.knowledge_hours ?? "—"}</td>
                  <td className="px-3 py-1.5 text-right num">{c.assessment_criteria.length}</td>
                </tr>
                {open === c.lo_number && <tr className="border-b border-rule bg-paper"><td colSpan={6} className="px-6 py-2"><ul className="list-disc pl-4 text-ink-2">{c.assessment_criteria.map((a) => <li key={a}>{a}</li>)}</ul></td></tr>}
              </Fragment>))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
