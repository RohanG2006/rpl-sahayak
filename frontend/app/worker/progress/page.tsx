"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Meter, Notice, Spinner } from "@/components/ui";
import { currentPlan, type Plan } from "@/lib/data/assessment";
import { getWorker } from "@/lib/data/worker";
import { useSession } from "@/lib/useSession";
import { useT } from "@/lib/i18n";
import { LIFECYCLE, NCVET_STAGE_HI, STATE_LABEL, lifecycleProgress, type State } from "@/lib/workflow";
import type { Worker } from "@/lib/types";

// NCVET Annexure-1 Flowchart 3 stage for each lifecycle state (mirrors backend workflow.NCVET_STAGE)
const STAGE: Record<State, string> = {
  REGISTERED: "Enrolment", PROFILE_COMPLETE: "Enrolment", EXPERIENCE_DECLARED: "Enrolment", SKILLS_EXTRACTED: "Enrolment", SKILLS_CONFIRMED: "Enrolment",
  QUALIFICATION_MATCHED: "Orientation", QUALIFICATION_CONFIRMED: "Orientation", PLAN_CREATED: "Orientation", SELF_ASSESSED: "Orientation",
  READINESS_EVALUATED: "Assignment of RPL assessor", TASKS_IN_PROGRESS: "Assessment (practical skills)", EVIDENCE_SUBMITTED: "Assessment (practical skills)",
  AI_EVIDENCE_REVIEWED: "Assessment (practical skills)", ASSESSOR_SCORING: "Assessment (practical skills)", SCORED: "Assessment (practical skills)",
  RECOMMENDATION_GENERATED: "Assessment (practical skills)", UNDER_ASSESSOR_REVIEW: "Assessment (practical skills)", DECIDED: "Certification & Feedback", REPORT_ISSUED: "Certification & Feedback",
};

export default function ProgressPage() {
  const { t, lang } = useT();
  const s = useSession();
  const [w, setW] = useState<Worker | null>(null);
  const [plan, setPlan] = useState<Plan | null | undefined>(undefined);
  const [err, setErr] = useState(false);
  useEffect(() => {
    if (!s?.user.worker_id) return;
    Promise.all([getWorker(s.user.worker_id), currentPlan()]).then(([ww, pp]) => { setW(ww); setPlan(pp); }).catch(() => setErr(true));
  }, [s?.user.worker_id]);
  if (err) return <Notice tone="bad">{t("err.generic")}</Notice>;
  if (!w || plan === undefined) return <Spinner label={t("common.loading")} />;

  const cur = (plan?.status ?? w.status) as State;
  const idx = LIFECYCLE.indexOf(cur);
  const stages = [...new Set(LIFECYCLE.map((x) => STAGE[x]))];
  const done = plan?.tasks.filter((x) => ["SUBMITTED", "SCORED"].includes(x.attempt?.status ?? "")).length ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t("prog.title")}</h1>
      <div>
        <Meter value={lifecycleProgress(w.status, plan?.status)} tone="accent" label={t("dash.progress")} />
        <p className="mt-1 text-sm num">{t("dash.progress")}: {lifecycleProgress(w.status, plan?.status)}%</p>
      </div>
      {plan && <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-[3px] border border-rule bg-rule">
        <div className="bg-sheet p-3"><dt className="label">{t("prog.tasks")}</dt><dd className="text-xl font-semibold num">{done} / {plan.tasks.length}</dd></div>
        <div className="bg-sheet p-3"><dt className="label">{t("prog.evidence")}</dt><dd className="text-xl font-semibold num">{plan.evidence_count}</dd></div>
      </dl>}
      <ol className="flex flex-col">
        {stages.map((st) => {
          const states = LIFECYCLE.filter((x) => STAGE[x] === st);
          const first = LIFECYCLE.indexOf(states[0]);
          const last = LIFECYCLE.indexOf(states[states.length - 1]);
          const status = idx > last ? "done" : idx >= first ? "current" : "todo";
          return (
            <li key={st} className="relative flex gap-3 pb-5 last:pb-0">
              <span aria-hidden className={`z-10 mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full border-2 text-xs font-bold ${status === "done" ? "border-ok bg-ok text-white" : status === "current" ? "border-ink bg-ink text-sheet" : "border-rule-strong bg-sheet"}`}>{status === "done" ? "✓" : ""}</span>
              <span aria-hidden className="absolute left-[11px] top-6 h-full w-0.5 bg-rule" />
              <div>
                <p className="label">{t("prog.stage")}</p>
                <p className="font-semibold">{lang === "hi" ? NCVET_STAGE_HI[st] : st} {status === "current" && <span className="stamp ml-1 border border-ink">{t("prog.current")}</span>}</p>
                <ul className="mt-1 text-sm text-ink-2">{states.map((x) => {
                  const skipped = (x === "EVIDENCE_SUBMITTED" || x === "AI_EVIDENCE_REVIEWED") && plan?.evidence_count === 0 && LIFECYCLE.indexOf(x) < idx;
                  return <li key={x} className={LIFECYCLE.indexOf(x) <= idx && !skipped ? "" : "text-ink-3"}>
                    {skipped ? "– " : LIFECYCLE.indexOf(x) < idx ? "✓ " : LIFECYCLE.indexOf(x) === idx ? "→ " : "· "}{STATE_LABEL[x][lang]}{skipped && ` (${t("prog.skipped")})`}</li>;
                })}
                </ul>
              </div>
            </li>
          );
        })}
      </ol>
      {plan && ["DECIDED", "REPORT_ISSUED"].includes(plan.status) && <Link href="/worker/results" className="inline-flex min-h-14 items-center justify-center rounded-[3px] bg-ink px-5 font-semibold text-sheet">{t("res.title")} →</Link>}
    </div>
  );
}
