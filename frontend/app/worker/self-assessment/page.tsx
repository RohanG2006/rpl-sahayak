"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Meter, Notice, Spinner, Stamp } from "@/components/ui";
import { currentPlan, selfAssess, startPlan, type Plan, type Readiness } from "@/lib/data/assessment";
import { useT, type TKey } from "@/lib/i18n";
import { ApiError } from "@/lib/api";

type Claim = "regularly" | "sometimes" | "never";
const CLAIMS: Claim[] = ["regularly", "sometimes", "never"];

export default function SelfAssessmentPage() {
  const { t } = useT();
  const router = useRouter();
  const [plan, setPlan] = useState<Plan | null | undefined>(undefined);
  const [answers, setAnswers] = useState<Record<number, Claim>>({});
  const [result, setResult] = useState<Readiness | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fail = (e: unknown) => setErr(e instanceof ApiError ? (e.isOffline ? t("err.offline") : e.message) : t("err.generic"));

  useEffect(() => {
    currentPlan().then((p) => {
      setPlan(p);
      if (p?.self_assessment) setAnswers(Object.fromEntries(Object.entries(p.self_assessment).map(([k, v]) => [Number(k), v as Claim])));
      if (p && "pathway" in (p.readiness ?? {})) setResult(p.readiness as Readiness);
    }).catch((e) => { fail(e); setPlan(null); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (plan === undefined) return <Spinner label={t("common.loading")} />;
  if (!plan) return <div className="flex flex-col gap-4">{err && <Notice tone="bad">{err}</Notice>}<Notice tone="info">{t("task.no_plan")}</Notice>
    <Button size="lg" onClick={() => router.push("/worker/qualification-match")}>{t("match.title")}</Button></div>;

  const locked = !["PLAN_CREATED", "SELF_ASSESSED", "READINESS_EVALUATED"].includes(plan.status);
  const complete = plan.scope_los.every((lo) => answers[lo.lo_number]);

  async function submit() {
    setBusy(true); setErr(null);
    try { setResult((await selfAssess(plan!.id, answers)).readiness); window.scrollTo(0, 0); } catch (e) { fail(e); }
    setBusy(false);
  }
  async function start() {
    setBusy(true); setErr(null);
    try { await startPlan(plan!.id); router.push("/worker/assessment"); } catch (e) { fail(e); setBusy(false); }
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="label">{plan.qualification.title} · {plan.qualification.qualification_code}</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">{t("sa.title")}</h1>
        <p className="mt-1.5 text-ink-2">{t("sa.lead")}</p>
      </div>

      {result && (
        <section className={`sheet p-4 ${result.pathway === "DIRECT_ASSESSMENT" ? "border-l-4 border-l-ok" : "border-l-4 border-l-warn"}`} aria-live="polite">
          <p className="label">{t("sa.result")}</p>
          <p className="mt-1 text-xl font-semibold">{result.pathway === "DIRECT_ASSESSMENT" ? t("sa.direct") : t("sa.upskill")}</p>
          <div className="mt-3"><Meter value={result.weighted_coverage * 100} tone={result.pathway === "DIRECT_ASSESSMENT" ? "ok" : "warn"} label={t("sa.coverage")} /></div>
          <p className="mt-1 text-sm num">{t("sa.coverage")}: {Math.round(result.weighted_coverage * 100)}% (&gt; {Math.round(result.threshold * 100)}%)</p>
          <ul className="mt-3 list-disc pl-5 text-sm text-ink-2">{result.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          {result.pathway !== "DIRECT_ASSESSMENT" && <p className="mt-2 text-sm">{t("sa.upskill_note")}</p>}
          <Button className="mt-4" size="lg" block disabled={busy} onClick={start}>{t("sa.start")}</Button>
        </section>
      )}

      <ol className="flex flex-col gap-3">
        {plan.scope_los.map((lo) => (
          <li key={lo.lo_number} className="sheet p-3">
            <fieldset disabled={locked}>
              <legend className="w-full">
                <span className="label">LO {lo.lo_number} {lo.nos[0] ? `· ${lo.nos.join(", ")}` : ""}</span>
                <span className="mt-1 block font-semibold leading-snug">{lo.title}</span>
              </legend>
              <details className="mt-1 text-sm text-ink-3"><summary className="cursor-pointer py-1">{t("sa.official")} <Stamp kind="official" /></summary>
                <ul className="list-disc pl-5">{lo.criteria.map((c) => <li key={c}>{c}</li>)}</ul></details>
              <div className="mt-2 grid grid-cols-1 gap-1.5">
                {CLAIMS.map((c) => {
                  const on = answers[lo.lo_number] === c;
                  return (
                    <label key={c} className={`flex min-h-12 cursor-pointer items-center gap-3 rounded-[3px] border px-3 ${on ? "border-ink bg-ink text-sheet" : "border-rule-strong bg-sheet hover:border-ink"}`}>
                      <input type="radio" className="sr-only" name={`lo-${lo.lo_number}`} checked={on} onChange={() => setAnswers((a) => ({ ...a, [lo.lo_number]: c }))} />
                      <span aria-hidden className={`h-4 w-4 shrink-0 rounded-full border-2 ${on ? "border-sheet bg-sheet [box-shadow:inset_0_0_0_3px_var(--ink)]" : "border-ink-3"}`} />
                      {t(`sa.${c}` as TKey)}
                    </label>
                  );
                })}
              </div>
            </fieldset>
          </li>
        ))}
      </ol>
      {err && <Notice tone="bad">{err}</Notice>}
      {!locked && (
        <div className="sticky bottom-16 z-10 -mx-4 border-t border-rule bg-paper px-4 py-3">
          <Button size="lg" block disabled={busy || !complete} onClick={submit}>{t("sa.submit")}</Button>
        </div>
      )}
    </div>
  );
}
