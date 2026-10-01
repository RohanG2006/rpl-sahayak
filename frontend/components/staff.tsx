"use client";
import { useState, type ReactNode } from "react";
import { STATE_LABEL, type State } from "@/lib/workflow";

export function Kpi({ label, value, sub, emphasis }: { label: string; value: ReactNode; sub?: ReactNode; emphasis?: boolean }) {
  return (
    <div className="bg-sheet p-4">
      <p className="label">{label}</p>
      <p className={`mt-1 font-semibold leading-none num ${emphasis ? "text-4xl" : "text-2xl"}`}>{value ?? <span className="text-base font-normal text-ink-3">—</span>}</p>
      {sub && <p className="mt-1.5 text-xs text-ink-3">{sub}</p>}
    </div>
  );
}

const STATUS_TONE: Partial<Record<State, string>> = {
  TASKS_IN_PROGRESS: "border-accent text-accent-ink bg-accent-wash",
  EVIDENCE_SUBMITTED: "border-warn text-warn bg-warn-wash", AI_EVIDENCE_REVIEWED: "border-warn text-warn bg-warn-wash",
  ASSESSOR_SCORING: "border-warn text-warn bg-warn-wash", SCORED: "border-warn text-warn bg-warn-wash",
  RECOMMENDATION_GENERATED: "border-warn text-warn bg-warn-wash", UNDER_ASSESSOR_REVIEW: "border-warn text-warn bg-warn-wash",
  DECIDED: "border-ok text-ok bg-ok-wash", REPORT_ISSUED: "border-ok text-ok bg-ok-wash",
};
export function StatusBadge({ status }: { status: string }) {
  const tone = STATUS_TONE[status as State] ?? "border-rule-strong text-ink-2 bg-sheet";
  return <span className={`stamp border ${tone}`}>{STATE_LABEL[status as State]?.en ?? status}</span>;
}

export const OUTCOME = {
  ELIGIBLE: { label: "Eligible — for assessor sign-off", tone: "border-ok text-ok bg-ok-wash", icon: "✓" },
  NOT_YET_READY: { label: "Not yet ready", tone: "border-bad text-bad bg-bad-wash", icon: "✕" },
  REASSESSMENT_SUGGESTED: { label: "Reassessment suggested", tone: "border-warn text-warn bg-warn-wash", icon: "↻" },
} as const;
export const DECISION = {
  APPROVE: { label: "Approved for certification", tone: "border-ok text-ok bg-ok-wash" },
  REJECT: { label: "Not yet competent", tone: "border-bad text-bad bg-bad-wash" },
  REASSESS: { label: "Reassessment requested", tone: "border-warn text-warn bg-warn-wash" },
} as const;

/**
 * Competency magnitude bars: one hue (sequential slot), solid hairline threshold, value at the bar tip.
 * Below-threshold rows use the reserved warning status colour + "!" icon + "Gap" label (never colour alone).
 * Table view toggle for accessibility.
 */
export function CompetencyBars({ rows, threshold, title }: { rows: { key: string; label: string; value: number | null }[]; threshold: number; title: string }) {
  const [table, setTable] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  return (
    <figure className="sheet p-4">
      <figcaption className="flex items-center justify-between gap-2">
        <span className="font-semibold">{title}</span>
        <button className="min-h-9 rounded-[3px] border border-rule-strong px-2.5 text-xs font-medium hover:border-ink" aria-pressed={table} onClick={() => setTable(!table)}>{table ? "Chart view" : "Table view"}</button>
      </figcaption>
      {table ? (
        <table className="mt-3 w-full text-sm">
          <thead><tr className="border-b border-rule text-left text-ink-3"><th className="py-1.5 font-medium">Area</th><th className="py-1.5 text-right font-medium">Score</th><th className="py-1.5 text-right font-medium">Required</th><th className="py-1.5 text-right font-medium">Status</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.key} className="border-b border-rule last:border-0"><td className="py-1.5">{r.label}</td>
              <td className="py-1.5 text-right num">{r.value == null ? "—" : `${r.value.toFixed(1)}%`}</td><td className="py-1.5 text-right num">{threshold}%</td>
              <td className="py-1.5 text-right">{r.value == null ? "Not assessed" : r.value >= threshold ? "Met" : "Gap"}</td></tr>))}
          </tbody>
        </table>
      ) : (
        <div className="relative mt-4">
          {/* threshold reference: solid hairline + label */}
          <div aria-hidden className="pointer-events-none absolute bottom-0 top-0 z-10 border-l border-ink" style={{ left: `calc(10.5rem + (100% - 10.5rem - 3.25rem) * ${threshold / 100})` }}>
            <span className="absolute -top-4 -translate-x-1/2 whitespace-nowrap text-[0.6875rem] font-semibold text-ink">Required {threshold}%</span>
          </div>
          <ul className="flex flex-col gap-2.5 pt-2">
            {rows.map((r) => {
              const below = r.value != null && r.value < threshold;
              return (
                <li key={r.key} className="grid grid-cols-[10.5rem_1fr_3.25rem] items-center gap-0 text-sm" tabIndex={0}
                  onMouseEnter={() => setHover(r.key)} onMouseLeave={() => setHover(null)} onFocus={() => setHover(r.key)} onBlur={() => setHover(null)}
                  aria-label={`${r.label}: ${r.value == null ? "not assessed" : `${r.value.toFixed(1)} percent${below ? ", below required" : ""}`}`}>
                  <span className={`truncate pr-3 ${hover === r.key ? "font-semibold" : ""}`}>{below && <span aria-hidden className="mr-1 font-bold text-warn">!</span>}{r.label}</span>
                  <span className="relative h-5 bg-rule/40">
                    {r.value != null && <span className="absolute inset-y-0 left-0 rounded-r-[4px]" style={{ width: `${r.value}%`, background: below ? "var(--warn)" : "var(--seq-4)", opacity: hover && hover !== r.key ? 0.45 : 1 }} />}
                    {hover === r.key && r.value != null && (
                      <span role="tooltip" className="absolute -top-8 z-20 whitespace-nowrap rounded-[3px] bg-ink px-2 py-1 text-xs text-sheet" style={{ left: `min(${r.value}%, 70%)` }}>
                        {r.label}: {r.value.toFixed(1)}% · {below ? `gap ${(threshold - r.value).toFixed(1)}` : "meets threshold"}
                      </span>
                    )}
                  </span>
                  <span className="pl-2 text-right font-semibold num">{r.value == null ? "—" : `${Math.round(r.value)}%`}{below && <span className="block text-[0.625rem] font-semibold uppercase text-warn">Gap</span>}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </figure>
  );
}
