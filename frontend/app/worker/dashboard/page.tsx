"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Meter, Notice, Spinner, Stamp } from "@/components/ui";
import { getWorker } from "@/lib/data/worker";
import { currentPlan, type Plan } from "@/lib/data/assessment";
import { getGaps } from "@/lib/data/assessor";
import { useSession } from "@/lib/useSession";
import { useOnSynced } from "@/lib/offline/useSynced";
import { useT, type TKey } from "@/lib/i18n";
import { ApiError } from "@/lib/api";
import type { Worker } from "@/lib/types";
import { lifecycleProgress, NCVET_STAGE_HI, STATE_LABEL, type State } from "@/lib/workflow";

const NEXT: Record<string, { href: string; key: TKey }> = {
  REGISTERED: { href: "/worker/profile", key: "next.REGISTERED" },
  PROFILE_COMPLETE: { href: "/worker/experience", key: "next.PROFILE_COMPLETE" },
  EXPERIENCE_DECLARED: { href: "/worker/experience", key: "next.EXPERIENCE_DECLARED" },
  SKILLS_EXTRACTED: { href: "/worker/experience", key: "next.SKILLS_EXTRACTED" },
  SKILLS_CONFIRMED: { href: "/worker/qualification-match", key: "next.SKILLS_CONFIRMED" },
  QUALIFICATION_MATCHED: { href: "/worker/qualification-match", key: "next.QUALIFICATION_MATCHED" },
  QUALIFICATION_CONFIRMED: { href: "/worker/self-assessment", key: "next.QUALIFICATION_CONFIRMED" },
  PLAN_CREATED: { href: "/worker/self-assessment", key: "next.QUALIFICATION_CONFIRMED" },
  SELF_ASSESSED: { href: "/worker/self-assessment", key: "sa.start" },
  READINESS_EVALUATED: { href: "/worker/self-assessment", key: "sa.start" },
  TASKS_IN_PROGRESS: { href: "/worker/assessment", key: "dash.continue" },
  EVIDENCE_SUBMITTED: { href: "/worker/assessment", key: "dash.continue" },
  AI_EVIDENCE_REVIEWED: { href: "/worker/assessment", key: "dash.continue" },
  ASSESSOR_SCORING: { href: "/worker/progress", key: "nav.progress" },
  SCORED: { href: "/worker/progress", key: "nav.progress" },
  RECOMMENDATION_GENERATED: { href: "/worker/progress", key: "nav.progress" },
  UNDER_ASSESSOR_REVIEW: { href: "/worker/progress", key: "nav.progress" },
  DECIDED: { href: "/worker/results", key: "res.title" },
  REPORT_ISSUED: { href: "/worker/results", key: "res.title" },
};

export default function WorkerDashboard() {
  const { t, lang } = useT();
  const s = useSession();
  const [w, setW] = useState<Worker | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [gapCount, setGapCount] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const wid = s?.user.worker_id;
  const [tick, setTick] = useState(0);
  useOnSynced(() => setTick((x) => x + 1));
  useEffect(() => {
    if (!wid) return;
    (async () => {
      const ww = await getWorker(wid);
      setW(ww);
      const p = await currentPlan();
      setPlan(p);
      if (p && ["DECIDED", "REPORT_ISSUED"].includes(p.status)) setGapCount((await getGaps(p.id)).areas.filter((a) => a.status === "gap").length);
    })().catch((e) => setErr(e instanceof ApiError && e.isOffline ? t("err.offline") : t("err.generic")));
  }, [wid, t, tick]);

  if (err) return <Notice tone="bad">{err}</Notice>;
  if (!w) return <Spinner label={t("common.loading")} />;
  const status = (plan?.status ?? w.status) as State;
  const stageEn = plan?.ncvet_stage ?? w.ncvet_stage;
  const stage = lang === "hi" ? NCVET_STAGE_HI[stageEn] ?? stageEn : stageEn;
  const pct = lifecycleProgress(w.status, plan?.status);
  const next = NEXT[status];
  const done = plan?.tasks.filter((x) => ["SUBMITTED", "SCORED"].includes(x.attempt?.status ?? "")).length;

  const tiles: [TKey, string | null][] = [
    ["dash.match", plan ? `${plan.match_snapshot.final_pct}%` : null],
    ["dash.tasks", plan && plan.status !== "PLAN_CREATED" ? `${done} / ${plan.tasks.length}` : null],
    ["dash.evidence", plan ? String(plan.evidence_count) : null],
    ["dash.gaps", gapCount == null ? null : String(gapCount)],
  ];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("dash.welcome", { name: w.full_name.split(" ")[0] })}</h1>
        {w.data_origin === "synthetic" && <p className="mt-2"><Stamp kind="synthetic" /></p>}
      </div>
      <section className="sheet p-4">
        <p className="label">{t("dash.stage")}</p>
        <p className="mt-1 text-lg font-semibold">{stage}</p>
        <p className="text-sm text-ink-3">{STATE_LABEL[status]?.[lang] ?? status}</p>
        <div className="mt-3"><Meter value={pct} label={t("dash.progress")} tone="accent" /></div>
        <p className="mt-1 text-sm text-ink-2 num">{t("dash.progress")}: {pct}%</p>
        {next && (
          <Link href={next.href} className="mt-4 flex min-h-14 items-center justify-between rounded-[3px] bg-ink px-5 font-semibold text-sheet">
            <span><span className="block text-xs font-medium uppercase tracking-wider text-sheet/70">{t("dash.next")}</span>{t(next.key)}</span>
            <span aria-hidden>→</span>
          </Link>
        )}
      </section>
      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-[3px] border border-rule bg-rule">
        {tiles.map(([k, v]) => (
          <div key={k} className="bg-sheet p-3">
            <dt className="label">{t(k)}</dt>
            <dd className="mt-1 text-xl font-semibold num">{v ?? <span className="text-base font-normal text-ink-3">{t("dash.pending")}</span>}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
