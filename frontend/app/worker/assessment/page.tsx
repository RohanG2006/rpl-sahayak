"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Meter, Notice, Spinner, TextArea } from "@/components/ui";
import { currentPlan, saveTaskProgress, type Plan, type PlanTask } from "@/lib/data/assessment";
import { useOnSynced } from "@/lib/offline/useSynced";
import { useT, type TKey } from "@/lib/i18n";
import { ApiError } from "@/lib/api";

const STATUS_TONE: Record<string, string> = {
  NOT_STARTED: "border-rule-strong text-ink-3", IN_PROGRESS: "border-accent text-accent-ink bg-accent-wash",
  SUBMITTED: "border-ink text-ink", SCORED: "border-ok text-ok bg-ok-wash",
};

export default function WorkerAssessmentPage() {
  const { t, lang } = useT();
  const router = useRouter();
  const [plan, setPlan] = useState<Plan | null | undefined>(undefined);
  const [open, setOpen] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const fail = (e: unknown) => setErr(e instanceof ApiError ? (e.isOffline ? t("err.offline") : e.message) : t("err.generic"));

  useEffect(() => {
    currentPlan().then(setPlan).catch((e) => { fail(e); setPlan(null); });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load once on mount
  }, []);

  useOnSynced(() => { currentPlan().then((p) => p && setPlan(p)).catch(() => {}); });

  if (plan === undefined) return <Spinner label={t("common.loading")} />;
  if (!plan) return <Notice tone="info">{t("task.no_plan")}</Notice>;
  if (["PLAN_CREATED", "SELF_ASSESSED", "READINESS_EVALUATED"].includes(plan.status)) {
    return <div className="flex flex-col gap-4"><h1 className="text-2xl font-semibold tracking-tight">{t("task.title")}</h1>
      <Notice tone="info">{t("next.QUALIFICATION_CONFIRMED")}</Notice>
      <Button size="lg" onClick={() => router.push("/worker/self-assessment")}>{t("sa.title")}</Button></div>;
  }

  const done = plan.tasks.filter((x) => ["SUBMITTED", "SCORED"].includes(x.attempt?.status ?? "")).length;
  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="label">{plan.qualification.title} · {plan.qualification.qualification_code}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">{t("task.title")}</h1>
        <p className="mt-1.5 text-ink-2">{t("task.lead")}</p>
        <div className="mt-3"><Meter value={done} max={plan.tasks.length} tone="accent" label={t("task.done_count", { n: done, total: plan.tasks.length })} /></div>
        <p className="mt-1 text-sm num">{t("task.done_count", { n: done, total: plan.tasks.length })}</p>
      </div>
      {err && <Notice tone="bad">{err}</Notice>}
      <ol className="flex flex-col gap-2">
        {plan.tasks.map((task) => {
          const st = task.attempt?.status ?? "NOT_STARTED";
          const isOpen = open === task.task_code;
          return (
            <li key={task.task_code} className="sheet">
              <button type="button" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? null : task.task_code)}
                className="flex min-h-16 w-full items-center gap-3 px-3 py-2 text-left">
                <span className="grid h-9 w-9 shrink-0 place-items-center border border-ink text-sm font-semibold num">{task.task_code}</span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold leading-snug">{lang === "hi" && task.title_hi ? task.title_hi : task.title}</span>
                  <span className={`stamp mt-1 border ${STATUS_TONE[st]}`}>{t(`task.status.${st}` as TKey)}</span>
                </span>
                <span aria-hidden className={`text-ink-3 ${isOpen ? "rotate-180" : ""}`}>▾</span>
              </button>
              {isOpen && <TaskBody plan={plan} task={task} onPlan={setPlan} onErr={fail} />}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function TaskBody({ plan, task, onPlan, onErr }: { plan: Plan; task: PlanTask; onPlan: (p: Plan) => void; onErr: (e: unknown) => void }) {
  const { t, lang } = useT();
  const [ticks, setTicks] = useState<Record<string, boolean>>(task.attempt?.checklist_state ?? {});
  const [note, setNote] = useState(task.attempt?.worker_note ?? "");
  const [busy, setBusy] = useState(false);
  const locked = task.attempt?.status === "SCORED";

  async function save(status: "IN_PROGRESS" | "SUBMITTED") {
    setBusy(true);
    try { onPlan(await saveTaskProgress(plan.id, task.task_code, { checklist_state: ticks, worker_note: note || null, status })); } catch (e) { onErr(e); }
    setBusy(false);
  }

  return (
    <div className="flex flex-col gap-4 border-t border-rule px-3 py-4">
      <p className="text-ink-2">{lang === "hi" && task.description_hi ? task.description_hi : task.description}</p>
      {task.safety_requirements.length > 0 && (
        <div className="border-l-4 border-bad bg-bad-wash px-3 py-2">
          <p className="text-sm font-semibold text-bad">{t("task.safety")}</p>
          <ul className="list-disc pl-5 text-sm">{task.safety_requirements.map((s) => <li key={s}>{s}</li>)}</ul>
        </div>
      )}
      <fieldset disabled={locked}>
        <legend className="label mb-2">{t("task.steps")}</legend>
        <ol className="flex flex-col gap-1.5">
          {task.steps.map((s, i) => (
            <li key={i}>
              <label className="flex min-h-12 cursor-pointer items-start gap-3 rounded-[3px] border border-rule-strong bg-sheet px-3 py-3">
                <input type="checkbox" className="mt-0.5 h-5 w-5 shrink-0 accent-[var(--ink)]" checked={!!ticks[i]} onChange={(e) => setTicks((x) => ({ ...x, [i]: e.target.checked }))} />
                <span className={ticks[i] ? "text-ink-3 line-through" : ""}><span className="mr-1 font-semibold num">{i + 1}.</span>{lang === "hi" ? s.hi : s.en}</span>
              </label>
            </li>
          ))}
        </ol>
      </fieldset>
      <div>
        <p className="label mb-1.5">{t("task.evidence")}</p>
        <ul className="list-disc pl-5 text-sm text-ink-2">{task.evidence_required.map((e) => <li key={e.what}>{e.what} <span className="text-ink-3">({e.kind})</span></li>)}</ul>
        <Link href={`/worker/evidence?task=${task.task_code}`} className="mt-2 inline-flex min-h-11 items-center rounded-[3px] border border-rule-strong px-4 text-sm font-semibold hover:border-ink">{t("task.add_evidence")}</Link>
      </div>
      {!locked && <>
        <TextArea label={t("task.note")} optional rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
        <div className="flex gap-2">
          <Button variant="secondary" disabled={busy} onClick={() => save("IN_PROGRESS")}>{t("task.save")}</Button>
          <Button block disabled={busy} onClick={() => save("SUBMITTED")}>{t("task.submit")}</Button>
        </div>
      </>}
    </div>
  );
}
