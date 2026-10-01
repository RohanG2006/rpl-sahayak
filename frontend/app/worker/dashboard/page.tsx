"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Meter, Notice, Spinner, Stamp } from "@/components/ui";
import { getWorker } from "@/lib/data/worker";
import { useSession } from "@/lib/useSession";
import { useT, type TKey } from "@/lib/i18n";
import { ApiError } from "@/lib/api";
import type { Worker } from "@/lib/types";
import { lifecycleProgress, NCVET_STAGE_HI, STATE_LABEL, type State } from "@/lib/workflow";

const NEXT_HREF: Record<string, string> = {
  REGISTERED: "/worker/profile", PROFILE_COMPLETE: "/worker/experience", EXPERIENCE_DECLARED: "/worker/experience",
  SKILLS_EXTRACTED: "/worker/experience", SKILLS_CONFIRMED: "/worker/qualification-match",
  QUALIFICATION_MATCHED: "/worker/qualification-match", QUALIFICATION_CONFIRMED: "/worker/self-assessment",
};

export default function WorkerDashboard() {
  const { t, lang } = useT();
  const s = useSession();
  const [w, setW] = useState<Worker | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const wid = s?.user.worker_id;
  useEffect(() => {
    if (wid) getWorker(wid).then(setW).catch((e) => setErr(e instanceof ApiError && e.isOffline ? t("err.offline") : t("err.generic")));
  }, [wid, t]);

  if (err) return <Notice tone="bad">{err}</Notice>;
  if (!w) return <Spinner label={t("common.loading")} />;
  const pct = lifecycleProgress(w.status);
  const stage = lang === "hi" ? NCVET_STAGE_HI[w.ncvet_stage] ?? w.ncvet_stage : w.ncvet_stage;
  const statusLabel = STATE_LABEL[w.status as State]?.[lang] ?? w.status;
  const nextKey = `next.${w.status}` as TKey;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("dash.welcome", { name: w.full_name.split(" ")[0] })}</h1>
        {w.data_origin === "synthetic" && <p className="mt-2"><Stamp kind="synthetic" /></p>}
      </div>

      <section className="sheet p-4">
        <p className="label">{t("dash.stage")}</p>
        <p className="mt-1 text-lg font-semibold">{stage}</p>
        <p className="text-sm text-ink-3">{statusLabel}</p>
        <div className="mt-3"><Meter value={pct} label={t("dash.progress")} tone="accent" /></div>
        <p className="mt-1 text-sm text-ink-2 num">{t("dash.progress")}: {pct}%</p>
        {NEXT_HREF[w.status] && (
          <Link href={NEXT_HREF[w.status]} className="mt-4 flex min-h-14 items-center justify-between rounded-[3px] bg-ink px-5 font-semibold text-sheet">
            <span><span className="block text-xs font-medium uppercase tracking-wider text-sheet/70">{t("dash.next")}</span>{t(nextKey)}</span>
            <span aria-hidden>→</span>
          </Link>
        )}
      </section>

      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-[3px] border border-rule bg-rule">
        {([["dash.match", null], ["dash.tasks", null], ["dash.evidence", null], ["dash.gaps", null]] as [TKey, string | null][]).map(([k, v]) => (
          <div key={k} className="bg-sheet p-3">
            <dt className="label">{t(k)}</dt>
            <dd className="mt-1 text-xl font-semibold num">{v ?? <span className="text-base font-normal text-ink-3">{t("dash.pending")}</span>}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
