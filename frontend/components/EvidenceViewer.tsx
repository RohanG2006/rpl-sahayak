"use client";
import { useEffect, useRef, useState } from "react";
import { evidenceBlobUrl, type EvidenceItem } from "@/lib/data/evidence";
import type { Criterion, PlanTask } from "@/lib/data/assessment";
import { Button, Stamp } from "./ui";

/** Modal: Score → Criterion → Evidence → Worker submission (traceability chain). */
export default function EvidenceViewer({ ev, criterion, task, onClose, onAnalyze, busy }: {
  ev: EvidenceItem; criterion?: Criterion; task?: PlanTask; onClose: () => void; onAnalyze: () => void; busy: boolean;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { ref.current?.showModal(); }, []);
  useEffect(() => {
    let u: string | null = null;
    evidenceBlobUrl(ev.id).then((x) => { u = x; setUrl(x); }).catch(() => {});
    return () => { if (u) URL.revokeObjectURL(u); };
  }, [ev.id]);
  const o = ev.ai_observation;
  return (
    <dialog ref={ref} onClose={onClose} className="m-auto w-[min(960px,94vw)] max-h-[92vh] rounded-[3px] border border-ink bg-sheet p-0 text-ink backdrop:bg-ink/60" aria-label="Evidence viewer">
      <div className="flex items-center justify-between border-b border-rule px-4 py-3">
        <ol className="flex flex-wrap items-center gap-1.5 text-sm" aria-label="Traceability">
          {criterion?.score?.final_score != null && <><li className="font-semibold">Score {criterion.score.final_score}/4</li><li aria-hidden>→</li></>}
          {criterion && <><li><span className="font-mono">{criterion.criterion_code}</span></li><li aria-hidden>→</li></>}
          <li>Evidence <span className="font-mono text-xs">{ev.id.slice(0, 8)}</span></li><li aria-hidden>→</li>
          <li>{task ? `Worker submission ${task.task_code}` : "Worker upload"}</li>
        </ol>
        <Button variant="ghost" onClick={() => ref.current?.close()} aria-label="Close">✕</Button>
      </div>
      <div className="grid max-h-[calc(92vh-56px)] gap-0 overflow-y-auto md:grid-cols-[1.4fr_1fr]">
        <div className="grid min-h-64 place-items-center bg-ink/95 p-2">
          {ev.kind === "image" && url && (
            // Authenticated blob: URL — next/image cannot optimise it, so a plain <img> is correct here.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={url} alt={ev.caption ?? "Evidence"} className="max-h-[70vh] w-auto object-contain" />
          )}
          {ev.kind === "video" && url && <video src={url} controls className="max-h-[70vh] w-full" />}
          {ev.kind === "document" && url && <a href={url} target="_blank" rel="noreferrer" className="text-sheet underline">Open PDF</a>}
          {!url && <span className="text-sheet/70">Loading…</span>}
        </div>
        <div className="flex flex-col gap-4 p-4 text-sm">
          {criterion && <div><p className="label">Criterion</p><p className="mt-1 font-medium">{criterion.criterion_code} · {criterion.text}</p><p className="mt-1 text-xs text-ink-3">{criterion.qf_criterion_ref}</p></div>}
          <div>
            <p className="label">Worker submission</p>
            {ev.caption && <p className="mt-1">“{ev.caption}”</p>}
            <p className="mt-1 text-xs text-ink-3 num">{ev.mime} · {Math.round(ev.size_bytes / 1024)} KB · {new Date(ev.created_at).toLocaleString()}{ev.captured_offline ? " · captured offline" : ""}</p>
            <p className="mt-0.5 break-all font-mono text-[0.6875rem] text-ink-3">sha256 {ev.sha256}</p>
            {task?.attempt && <p className="mt-1 text-xs">Checklist: {Object.values(task.attempt.checklist_state).filter(Boolean).length}/{task.steps.length} steps ticked{task.attempt.worker_note ? ` · note: “${task.attempt.worker_note}”` : ""}</p>}
            {ev.data_origin === "synthetic" && <p className="mt-1"><Stamp kind="synthetic" /></p>}
          </div>
          <div className="ai-panel p-3">
            <div className="flex items-center justify-between"><Stamp kind="ai" />{o && <span className="text-xs text-ink-3 num">confidence {o.confidence?.toFixed(2) ?? "—"}</span>}</div>
            {!o ? <Button className="mt-2" variant="secondary" disabled={busy} onClick={onAnalyze}>{busy ? "Analysing…" : "Run AI evidence assistance"}</Button> : (
              <div className="mt-2 flex flex-col gap-2">
                <p className="text-xs text-ink-3">{o.simulated ? "Prepared demo output (synthetic evidence) — not a live AI call" : o.provider === "rules" ? "Rule-based: file quality & completeness only — image content not interpreted" : `${o.provider}${o.model ? ` · ${o.model}` : ""}`}</p>
                {[["Observed", o.output.observed, "✓", "text-ok"], ["Potentially missing", o.output.potentially_missing, "!", "text-warn"], ["Safety concerns", o.output.safety_concerns, "⚠", "text-bad"], ["Competency indicators", o.output.competency_indicators, "•", "text-ink-2"]].map(([t, items, m, tone]) =>
                  (items as string[] | undefined)?.length ? <div key={t as string}><p className="label">{t as string}</p><ul>{(items as string[]).map((x) => <li key={x} className="flex gap-2"><span aria-hidden className={`font-bold ${tone}`}>{m as string}</span>{x}</li>)}</ul></div> : null)}
                <p className="text-xs"><span className="font-semibold">Suggested score:</span> {o.output.suggested_score ?? "none"}{o.output.suggested_score_reason ? ` — ${o.output.suggested_score_reason}` : ""}</p>
                <p className="text-xs font-semibold text-ai">{o.advisory}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </dialog>
  );
}
