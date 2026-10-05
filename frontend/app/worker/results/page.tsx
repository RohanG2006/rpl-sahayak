"use client";
import { useEffect, useState } from "react";
import { CompetencyBars } from "@/components/staff";
import { Button, Notice, Spinner, Stamp } from "@/components/ui";
import { currentPlan, type Plan } from "@/lib/data/assessment";
import { downloadReport, getDecision, getGaps, getResults, type Decision, type Gaps, type Results } from "@/lib/data/assessor";
import { useT, type TKey } from "@/lib/i18n";
import { ApiError } from "@/lib/api";

export default function WorkerResults() {
  const { t, lang } = useT();
  const [plan, setPlan] = useState<Plan | null | undefined>(undefined);
  const [d, setD] = useState<Decision | null>(null);
  const [r, setR] = useState<Results | null>(null);
  const [g, setG] = useState<Gaps | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const p = await currentPlan();
      setPlan(p);
      if (p && ["DECIDED", "REPORT_ISSUED"].includes(p.status)) {
        const [dd, rr, gg] = await Promise.all([getDecision(p.id), getResults(p.id), getGaps(p.id)]);
        setD(dd); setR(rr); setG(gg);
      }
    })().catch((e) => { setErr(e instanceof ApiError && e.isOffline ? t("err.offline") : t("err.generic")); setPlan(null); });
  }, [t]);

  if (plan === undefined) return <Spinner label={t("common.loading")} />;
  if (err) return <Notice tone="bad">{err}</Notice>;
  if (!plan) return <Notice tone="info">{t("task.no_plan")}</Notice>;
  if (!d || !r || !g) return <div className="flex flex-col gap-4"><h1 className="text-2xl font-semibold tracking-tight">{t("res.title")}</h1><Notice tone="info">{t("res.wait")}</Notice></div>;

  const tone = { APPROVE: "border-l-ok", REJECT: "border-l-bad", REASSESS: "border-l-warn" }[d.decision];
  const label = (k: string) => (lang === "hi" ? r.competency_labels_hi[k] : r.competency_labels[k]) ?? k;
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t("res.title")}</h1>
      <section className={`human-panel border-l-4 p-4 ${tone}`}>
        <div className="flex items-center justify-between"><p className="label">{t("res.decision")}</p><Stamp kind="human" /></div>
        <p className="mt-1 text-xl font-semibold">{t(`res.dec.${d.decision}` as TKey)}</p>
        <p className="mt-2 text-ink-2">“{d.comments}”</p>
        {d.reassess_task_codes.length > 0 && <p className="mt-2 text-sm"><span className="font-semibold">{t("res.reassess")}:</span> {d.reassess_task_codes.join(", ")}</p>}
        <p className="mt-2 text-xs text-ink-3">{t("res.by", { name: d.assessor?.name ?? "" })} · {new Date(d.decided_at).toLocaleDateString()}</p>
      </section>

      <p className="text-sm"><span className="label mr-2">{t("res.overall")}</span><span className="text-2xl font-semibold num">{r.overall_pct?.toFixed(0)}%</span></p>
      <CompetencyBars title={t("res.profile")} threshold={g.required_pct}
        rows={Object.entries(r.competencies).map(([k, v]) => ({ key: k, label: label(k), value: v }))} />

      <section>
        <h2 className="mb-2 text-lg font-semibold">{t("res.gaps")}</h2>
        {g.areas.every((a) => a.status !== "gap") ? <p className="text-ink-2">{t("res.no_gaps")}</p> : (
          <ul className="flex flex-col gap-2">{g.areas.filter((a) => a.status === "gap").map((a) => (
            <li key={a.competency_key} className="sheet p-3">
              <p className="font-semibold">{lang === "hi" ? a.label_hi : a.label} <span className="text-sm font-normal num">{a.demonstrated?.toFixed(0)}% / {a.required}%</span></p>
              <ul className="mt-1.5 flex flex-col gap-1 text-sm">{a.learning_topics.map((x, i) => (
                <li key={i} className="flex gap-2"><span className={`stamp shrink-0 ${x.source === "official" ? "stamp-official" : "border border-rule-strong text-ink-3"}`}>{x.source === "official" ? `LO${x.lo_number}` : t("res.suggested")}</span>{x.topic}</li>))}
              </ul>
            </li>))}
          </ul>
        )}
      </section>
      <p className="text-sm text-ink-3">{t("res.scope", { n: Object.keys(r.learning_outcomes).length, total: plan.lo_total })} {t("res.note")}</p>
      <Button size="lg" variant="secondary" disabled={busy} onClick={async () => { setBusy(true); try { await downloadReport(plan.id); } catch (e) { setErr(e instanceof Error ? e.message : t("err.generic")); } setBusy(false); }}>
        {busy ? t("res.report_busy") : t("res.report")}
      </Button>
    </div>
  );
}
