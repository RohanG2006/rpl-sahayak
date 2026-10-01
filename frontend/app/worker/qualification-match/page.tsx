"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Notice, Spinner, Stamp } from "@/components/ui";
import { createPlan, runMatch, type Component, type MatchResponse, type MatchResult } from "@/lib/data/assessment";
import { getWorker } from "@/lib/data/worker";
import { useSession } from "@/lib/useSession";
import { useT, type TKey } from "@/lib/i18n";
import { ApiError } from "@/lib/api";

const COMPONENTS: Component[] = ["skill", "task", "experience", "occupation", "eligibility"];
// Categorical slots in fixed order (validated); identity also carried by the value table = legend.
const SLOT = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)", "var(--series-5)"];

export default function QualificationMatchPage() {
  const { t } = useT();
  const s = useSession();
  const router = useRouter();
  const wid = s?.user.worker_id ?? "";
  const [data, setData] = useState<MatchResponse | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const fail = (e: unknown) => setErr(e instanceof ApiError ? (e.isOffline ? t("err.offline") : e.message) : t("err.generic"));

  useEffect(() => {
    if (!wid) return;
    getWorker(wid).then((w) => {
      setStatus(w.status);
      if (["SKILLS_CONFIRMED", "QUALIFICATION_MATCHED", "QUALIFICATION_CONFIRMED"].includes(w.status)) run();
    }).catch(fail);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wid]);

  async function run() {
    setBusy(true); setErr(null);
    try { setData(await runMatch(wid)); } catch (e) { fail(e); }
    setBusy(false);
  }

  async function choose(r: MatchResult) {
    setBusy(true); setErr(null);
    try {
      await createPlan(wid, r.qualification_id);
      router.push("/worker/self-assessment");
    } catch (e) { fail(e); setBusy(false); }
  }

  if (status && !["SKILLS_CONFIRMED", "QUALIFICATION_MATCHED", "QUALIFICATION_CONFIRMED"].includes(status)) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">{t("match.title")}</h1>
        <Notice tone="info">{t("next.PROFILE_COMPLETE")} → {t("exp.confirm")}</Notice>
        <Button size="lg" onClick={() => router.push("/worker/experience")}>{t("exp.title")}</Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("match.title")}</h1>
        <p className="mt-1.5 text-ink-2">{t("match.lead")}</p>
        <p className="mt-2 text-sm text-ink-3">{t("match.rule_label")}</p>
      </div>
      {err && <Notice tone="bad">{err}</Notice>}
      {!data && (busy ? <Spinner label={t("match.running")} /> : <Button size="lg" onClick={run}>{t("match.run")}</Button>)}
      {data?.results.map((r, i) => <MatchCard key={r.qualification_id} r={r} open={i === 0} busy={busy} onChoose={() => choose(r)} />)}
    </div>
  );
}

function MatchCard({ r, open, busy, onChoose }: { r: MatchResult; open: boolean; busy: boolean; onChoose: () => void }) {
  const { t } = useT();
  const total = Object.values(r.weights).reduce((a, b) => a + b, 0);
  return (
    <article className={`sheet ${open ? "border-ink" : ""}`} aria-labelledby={`q-${r.qualification_id}`}>
      <header className="flex items-start justify-between gap-3 border-b border-rule p-4">
        <div className="min-w-0">
          <p className="label">#{r.rank} · {r.qualification_code} · {t("match.level")} {r.nsqf_level}</p>
          <h2 id={`q-${r.qualification_id}`} className="mt-1 text-xl font-semibold">{r.title}</h2>
          <p className="mt-1.5"><Stamp kind="official" /></p>
        </div>
        <div className="text-right">
          <p className="text-4xl font-semibold leading-none num">{r.final_pct}<span className="text-xl text-ink-3">%</span></p>
          <p className="mt-1 text-xs text-ink-3">{t("match.score")}</p>
        </div>
      </header>

      <details open={open} className="group">
        <summary className="flex min-h-12 cursor-pointer items-center justify-between px-4 text-[0.9375rem] font-medium">
          {t("match.breakdown")} <span aria-hidden className="text-ink-3 group-open:rotate-180">▾</span>
        </summary>
        <div className="flex flex-col gap-5 px-4 pb-4">
          {/* stacked contribution bar */}
          <div>
            <div className="flex h-3 w-full gap-[2px] bg-sheet" role="img" aria-label={`${t("match.score")} ${r.final_pct}%`}>
              {COMPONENTS.filter((c) => r.contributions[c] > 0).map((c) => (
                <div key={c} className="first:rounded-l-[4px]" style={{ width: `${r.contributions[c] * 100}%`, background: SLOT[COMPONENTS.indexOf(c)] }}
                  title={`${t(`match.c.${c}` as TKey)}: ${(r.contributions[c] * 100).toFixed(1)}`} />
              ))}
              <div className="flex-1 rounded-r-[4px] bg-rule/50" title={`${100 - r.final_pct}`} />
            </div>
            <table className="mt-3 w-full text-sm">
              <tbody>
                {COMPONENTS.map((c, i) => (
                  <tr key={c} className="border-b border-rule last:border-0">
                    <td className="py-1.5"><span aria-hidden className="mr-2 inline-block h-2.5 w-2.5 align-middle" style={{ background: SLOT[i] }} />{t(`match.c.${c}` as TKey)}</td>
                    <td className="py-1.5 text-right text-ink-3 num">{Math.round(r.components[c] * 100)}% × {(r.weights[c] / total).toFixed(2)}</td>
                    <td className="py-1.5 pl-3 text-right font-semibold num">{(r.contributions[c] * 100).toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <section>
            <h3 className="label mb-2">{t("match.coverage")}</h3>
            <ol className="grid grid-cols-10 gap-1" aria-label={t("match.coverage")}>
              {r.learning_outcomes.map((lo) => (
                <li key={lo.lo_number} title={`LO${lo.lo_number}: ${lo.title}${lo.matched_by ? ` — ${lo.matched_by}` : ""}`}
                  className={`grid h-7 place-items-center text-[0.6875rem] font-semibold num ${lo.status === "matched" ? "bg-ink text-sheet" : lo.status === "partial" ? "bg-accent-wash text-accent-ink border border-accent" : "border border-rule text-ink-3"}`}>
                  {lo.lo_number}
                </li>
              ))}
            </ol>
            <p className="mt-2 text-sm text-ink-2">{t("match.coverage_note", { m: r.lo_coverage.matched, p: r.lo_coverage.partial, t: r.lo_coverage.total })}</p>
          </section>

          {r.matched_skills.length > 0 && (
            <section>
              <h3 className="label mb-2">{t("match.matched")}</h3>
              <ul className="flex flex-col gap-1.5">
                {r.matched_skills.map((m) => (
                  <li key={m.label} className="flex gap-2 text-[0.9375rem]">
                    <span aria-hidden className="font-bold text-ok">✓</span>
                    <span className="min-w-0"><span className="font-medium">{m.label}</span>
                      <span className="block text-sm text-ink-3">{t("match.lo")} {m.lo_number}: {m.lo_title} {m.nos[0] && m.nos[0] !== "N/A" ? `(${m.nos.join(", ")})` : ""}</span></span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {r.unclear_skills.length > 0 && (
            <section>
              <h3 className="label mb-2">{t("match.unclear")}</h3>
              <ul className="flex flex-col gap-1.5">{r.unclear_skills.map((m) => <li key={m.label} className="flex gap-2 text-[0.9375rem]"><span aria-hidden className="font-bold text-warn">!</span>{m.label}</li>)}</ul>
            </section>
          )}

          {r.areas_not_evidenced.length > 0 && (
            <section>
              <h3 className="label mb-2">{t("match.not_evidenced")}</h3>
              <ul className="flex flex-col gap-1 text-sm text-ink-2">{r.areas_not_evidenced.slice(0, 5).map((a) => <li key={a.lo_number}>{t("match.lo")} {a.lo_number}: {a.title}</li>)}</ul>
            </section>
          )}

          <section>
            <h3 className="label mb-2">{t("match.eligibility")}</h3>
            <ul className="divide-y divide-rule border-y border-rule">
              {r.eligibility.map((c) => (
                <li key={c.key} className="flex items-start justify-between gap-3 py-2 text-sm">
                  <span className="min-w-0"><span className="font-medium">{c.label}</span><span className="block text-ink-3">{c.detail}</span><span className="block text-xs text-ink-3">{c.source}</span></span>
                  <span className={`stamp shrink-0 ${c.result === "pass" ? "text-ok border-ok bg-ok-wash border" : c.result === "fail" ? "text-bad border-bad bg-bad-wash border" : "text-warn border-warn bg-warn-wash border"}`}>{t(`match.check.${c.result}` as TKey)}</span>
                </li>
              ))}
            </ul>
          </section>

          {r.supporting_evidence.length > 0 && <p className="text-sm text-ink-3">{t("match.supporting")}: {r.supporting_evidence.map((x) => x.label).join(", ")}</p>}

          <p className="text-xs text-ink-3">{t("match.source")}: <a className="underline break-all" href={r.source_url} target="_blank" rel="noreferrer">{r.source_url.replace("https://", "")}</a></p>

          {r.is_assessable
            ? <Button size="lg" block disabled={busy} onClick={onChoose}>{t("match.confirm")}</Button>
            : <Notice tone="info">{t("match.not_assessable")}</Notice>}
        </div>
      </details>
    </article>
  );
}

