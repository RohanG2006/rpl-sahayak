"use client";
import { Fragment, useEffect, useState } from "react";
import { Button, Notice, Spinner } from "@/components/ui";
import { getAudit, type AuditRow } from "@/lib/data/admin";
import { ApiError } from "@/lib/api";

type Filters = { action: string; actor_role: string; via: string; q: string; page: number };

export default function AuditLogPage() {
  const [f, setF] = useState<Filters>({ action: "", actor_role: "", via: "", q: "", page: 1 });
  const [data, setData] = useState<{ total: number; page_size: number; actions: string[]; rows: AuditRow[] } | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [q, setQ] = useState("");
  useEffect(() => {
    getAudit({ ...f, page_size: 50 }).then(setData).catch((e) => setErr(e instanceof ApiError ? e.message : "Could not load audit log."));
  }, [f]);
  const set = (patch: Partial<Filters>) => setF((x) => ({ ...x, ...patch, page: patch.page ?? 1 }));
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const sel = "min-h-10 rounded-[3px] border border-rule-strong bg-sheet px-2 text-sm";

  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Audit log</h1>
        <p className="mt-1 text-sm text-ink-2">Append-only record of every assessment event. Personal fields (names, mobile numbers, locality) are redacted before storage.</p>
      </header>
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-sm">Event<select className={`${sel} ml-1`} value={f.action} onChange={(e) => set({ action: e.target.value })}><option value="">All events</option>{data?.actions.map((a) => <option key={a}>{a}</option>)}</select></label>
        <label className="text-sm">Actor<select className={`${sel} ml-1`} value={f.actor_role} onChange={(e) => set({ actor_role: e.target.value })}><option value="">Anyone</option><option>worker</option><option>assessor</option><option>admin</option><option>system</option></select></label>
        <label className="text-sm">Channel<select className={`${sel} ml-1`} value={f.via} onChange={(e) => set({ via: e.target.value })}><option value="">Any</option><option>online</option><option>sync</option><option>demo</option></select></label>
        <form className="flex gap-1" onSubmit={(e) => { e.preventDefault(); set({ q }); }}>
          <input aria-label="Search summaries" placeholder="Search summary" className={sel} value={q} onChange={(e) => setQ(e.target.value)} /><Button type="submit" variant="secondary">Search</Button>
        </form>
      </div>
      {err && <Notice tone="bad">{err}</Notice>}
      {!data ? <Spinner label="Loading…" /> : (
        <>
          <p className="text-sm text-ink-3 num">{data.total} events</p>
          <div className="overflow-x-auto rounded-[3px] border border-rule bg-sheet">
            <table className="w-full min-w-[820px] text-sm">
              <thead><tr className="border-b border-rule-strong text-left text-xs uppercase tracking-wider text-ink-3"><th className="px-3 py-2">Time</th><th className="px-3 py-2">Event</th><th className="px-3 py-2">Actor</th><th className="px-3 py-2">Channel</th><th className="px-3 py-2">Summary</th></tr></thead>
              <tbody>{data.rows.map((r) => (
                <Fragment key={r.id}>
                  <tr className="cursor-pointer border-b border-rule hover:bg-paper" onClick={() => setOpen(open === r.id ? null : r.id)} aria-expanded={open === r.id}>
                    <td className="whitespace-nowrap px-3 py-1.5 text-xs num">{new Date(r.at).toLocaleString()}</td>
                    <td className="px-3 py-1.5 font-mono text-xs">{r.action}</td>
                    <td className="px-3 py-1.5">{r.actor} <span className="text-xs text-ink-3">{r.actor_role}</span></td>
                    <td className="px-3 py-1.5 text-xs">{r.via}</td>
                    <td className="px-3 py-1.5">{r.summary}</td>
                  </tr>
                  {open === r.id && (
                    <tr className="border-b border-rule bg-paper"><td colSpan={5} className="px-3 py-2">
                      <p className="text-xs text-ink-3">{r.entity} {r.entity_id}</p>
                      {(r.before != null || r.after != null) && <div className="mt-1 grid gap-2 md:grid-cols-2">
                        <pre className="overflow-x-auto rounded-[3px] border border-rule bg-sheet p-2 text-xs">before {JSON.stringify(r.before, null, 2)}</pre>
                        <pre className="overflow-x-auto rounded-[3px] border border-rule bg-sheet p-2 text-xs">after {JSON.stringify(r.after, null, 2)}</pre>
                      </div>}
                    </td></tr>
                  )}
                </Fragment>))}
              </tbody>
            </table>
          </div>
          {pages > 1 && <nav aria-label="Pagination" className="flex items-center gap-2 text-sm">
            <Button variant="secondary" disabled={f.page <= 1} onClick={() => set({ page: f.page - 1 })}>Previous</Button>
            <span className="num">Page {f.page} of {pages}</span>
            <Button variant="secondary" disabled={f.page >= pages} onClick={() => set({ page: f.page + 1 })}>Next</Button></nav>}
        </>
      )}
    </div>
  );
}
