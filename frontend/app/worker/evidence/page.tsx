"use client";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import EvidenceThumb from "@/components/EvidenceThumb";
import { AdvisoryNote, Button, Notice, SelectField, Spinner, Stamp, TextField } from "@/components/ui";
import { currentPlan, type Plan } from "@/lib/data/assessment";
import { analyzeEvidence, confirmClaims, listEvidence, uploadEvidence, type EvidenceItem } from "@/lib/data/evidence";
import { compressImage, kb } from "@/lib/image";
import { useSession } from "@/lib/useSession";
import { useT, type TKey } from "@/lib/i18n";
import { ApiError } from "@/lib/api";

const DOC_TYPES = ["experience_letter", "certificate", "resume", "id_placeholder", "other"] as const;

export default function EvidencePageWrapper() {
  return <Suspense><EvidencePage /></Suspense>;
}

function EvidencePage() {
  const { t, lang } = useT();
  const s = useSession();
  const wid = s?.user.worker_id ?? "";
  const params = useSearchParams();
  const [plan, setPlan] = useState<Plan | null | undefined>(undefined);
  const [items, setItems] = useState<EvidenceItem[]>([]);
  const [taskCode, setTaskCode] = useState(params.get("task") ?? "");
  const [crit, setCrit] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [compressNote, setCompressNote] = useState<string | null>(null);
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const fail = (e: unknown) => setErr(e instanceof ApiError ? (e.isOffline ? t("err.offline") : e.message) : t("err.generic"));

  useEffect(() => {
    if (!wid) return;
    currentPlan().then((p) => { setPlan(p); if (p && !params.get("task")) setTaskCode(p.tasks[0]?.task_code ?? ""); }).catch((e) => { fail(e); setPlan(null); });
    listEvidence({ worker_id: wid }).then(setItems).catch(fail);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wid]);

  const task = plan?.tasks.find((x) => x.task_code === taskCode);
  const reqs = useMemo(() => task?.evidence_required ?? [], [task]);
  useEffect(() => { setCrit(reqs[0]?.criterion ?? ""); }, [reqs]);

  async function pick(f: File | null) {
    setCompressNote(null);
    if (!f) return setFile(null);
    const c = await compressImage(f);
    if (c !== f) setCompressNote(t("ev.compressed", { from: kb(f.size), to: kb(c.size) }));
    setFile(c);
  }

  async function send() {
    if (!file || !plan) return;
    setBusy("upload"); setErr(null); setOk(null);
    try {
      const ev = await uploadEvidence({ file, worker_id: wid, plan_id: plan.id, task_code: taskCode, criterion_code: crit || undefined, purpose: "assessment", caption, client_op_id: crypto.randomUUID() });
      setItems((x) => [ev, ...x]);
      setFile(null); setCaption(""); setCompressNote(null); setOk(t("ev.uploaded"));
    } catch (e) { fail(e); }
    setBusy(null);
  }

  async function feedback(id: string) {
    setBusy(id); setErr(null);
    try { const ev = await analyzeEvidence(id); setItems((x) => x.map((i) => (i.id === id ? ev : i))); } catch (e) { fail(e); }
    setBusy(null);
  }

  if (plan === undefined) return <Spinner label={t("common.loading")} />;
  const critText = (code: string | null) => plan?.tasks.flatMap((x) => x.criteria).find((c) => c.id === code || c.criterion_code === code);
  const assessmentItems = items.filter((i) => i.purpose === "assessment");
  const canUpload = plan && !["PLAN_CREATED", "SELF_ASSESSED", "READINESS_EVALUATED", "DECIDED", "REPORT_ISSUED"].includes(plan.status);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("ev.title")}</h1>
        <p className="mt-1.5 text-ink-2">{t("ev.lead")}</p>
      </div>
      {err && <Notice tone="bad">{err}</Notice>}
      {ok && <Notice tone="ok">{ok}</Notice>}

      {canUpload ? (
        <section className="sheet flex flex-col gap-4 p-4">
          <SelectField label={t("ev.task")} value={taskCode} onChange={(e) => setTaskCode(e.target.value)}
            options={plan!.tasks.map((x) => ({ value: x.task_code, label: `${x.task_code} · ${lang === "hi" && x.title_hi ? x.title_hi : x.title}` }))} />
          {reqs.length > 0 && (
            <fieldset>
              <legend className="mb-1.5 text-[0.9375rem] font-medium">{t("ev.for")}</legend>
              <div className="flex flex-col gap-1.5">
                {reqs.map((r) => (
                  <label key={r.criterion + r.what} className={`flex min-h-12 cursor-pointer items-start gap-3 rounded-[3px] border px-3 py-2.5 ${crit === r.criterion ? "border-ink bg-accent-wash" : "border-rule-strong bg-sheet"}`}>
                    <input type="radio" name="crit" className="mt-1" checked={crit === r.criterion} onChange={() => setCrit(r.criterion)} />
                    <span><span className="font-medium">{r.what}</span> <span className="text-sm text-ink-3">({r.kind} · {r.criterion})</span>
                      <span className="block text-sm text-ink-3">{critText(r.criterion)?.text}</span></span>
                  </label>
                ))}
              </div>
            </fieldset>
          )}
          <label className="flex min-h-14 cursor-pointer items-center justify-center gap-2 rounded-[3px] border-2 border-dashed border-rule-strong bg-paper px-4 text-center font-semibold hover:border-ink">
            <input type="file" className="sr-only" accept="image/*,video/mp4,video/webm" capture="environment" onChange={(e) => pick(e.target.files?.[0] ?? null)} />
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden><path d="M4 7h3l2-3h6l2 3h3v13H4z" /><circle cx="12" cy="13" r="4" /></svg>
            {file ? `${file.name} · ${kb(file.size)}` : t("ev.take")}
          </label>
          {compressNote && <p className="text-sm text-ink-3">{compressNote}</p>}
          <TextField label={t("ev.caption")} optional value={caption} onChange={(e) => setCaption(e.target.value)} />
          <Button size="lg" block disabled={!file || busy === "upload"} onClick={send}>{busy === "upload" ? t("ev.uploading") : t("ev.upload")}</Button>
        </section>
      ) : plan ? <Notice tone="info">{t("next.QUALIFICATION_CONFIRMED")}</Notice> : <Notice tone="info">{t("task.no_plan")}</Notice>}

      <section>
        <h2 className="label mb-2">{t("ev.mine")}</h2>
        {assessmentItems.length === 0 ? <p className="text-ink-3">{t("ev.none")}</p> : (
          <ul className="flex flex-col gap-2">
            {assessmentItems.map((ev) => {
              const c = critText(ev.criterion_id);
              const o = ev.ai_observation;
              return (
                <li key={ev.id} className="sheet p-3">
                  <div className="flex gap-3">
                    <EvidenceThumb ev={ev} />
                    <div className="min-w-0 flex-1 text-sm">
                      <p className="font-semibold">{c ? `${c.criterion_code} · ${c.text}` : ev.kind}</p>
                      {ev.caption && <p className="text-ink-2">“{ev.caption}”</p>}
                      <p className="text-ink-3 num">{kb(ev.size_bytes)} · {new Date(ev.created_at).toLocaleString()}</p>
                      {ev.data_origin === "synthetic" && <Stamp kind="synthetic" />}
                    </div>
                  </div>
                  {o ? (
                    <div className="ai-panel mt-3 p-3 text-sm">
                      <p className="mb-1 font-semibold">{t("ev.feedback_title")}</p>
                      <AdvisoryNote provider={o.provider} fallback={o.fallback_used} />
                      {o.simulated && <p className="mt-1 text-ink-3">{t("ev.simulated")}</p>}
                      {o.output.analysis_basis === "metadata_only" && <p className="mt-1 text-ink-3">{t("ev.metadata_only")}</p>}
                      <ObsList title={t("ev.observed")} items={o.output.observed} mark="✓" tone="text-ok" />
                      <ObsList title={t("ev.missing")} items={o.output.potentially_missing} mark="!" tone="text-warn" />
                      <ObsList title={t("ev.concerns")} items={o.output.safety_concerns} mark="⚠" tone="text-bad" />
                    </div>
                  ) : (
                    <Button className="mt-3" variant="secondary" block disabled={busy === ev.id} onClick={() => feedback(ev.id)}>
                      {busy === ev.id ? <Spinner label={t("common.loading")} /> : t("ev.feedback")}
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <Documents wid={wid} items={items.filter((i) => i.purpose === "document")} onItems={(f) => setItems(f)} all={items} />
    </div>
  );
}

function ObsList({ title, items, mark, tone }: { title: string; items?: string[]; mark: string; tone: string }) {
  if (!items?.length) return null;
  return (
    <div className="mt-2">
      <p className="label">{title}</p>
      <ul className="mt-1 flex flex-col gap-0.5">{items.map((x) => <li key={x} className="flex gap-2"><span aria-hidden className={`font-bold ${tone}`}>{mark}</span><span>{x}</span></li>)}</ul>
    </div>
  );
}

function Documents({ wid, items, all, onItems }: { wid: string; items: EvidenceItem[]; all: EvidenceItem[]; onItems: (x: EvidenceItem[]) => void }) {
  const { t } = useT();
  const [docType, setDocType] = useState<string>("experience_letter");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [keep, setKeep] = useState<Record<string, Record<number, boolean>>>({});

  async function send() {
    if (!file) return;
    setBusy(true); setErr(null);
    try {
      const up = await uploadEvidence({ file: await compressImage(file), worker_id: wid, purpose: "document", doc_type: docType, client_op_id: crypto.randomUUID() });
      const analysed = await analyzeEvidence(up.id);
      onItems([analysed, ...all]);
      setFile(null);
    } catch (e) { setErr(e instanceof ApiError ? e.message : t("err.generic")); }
    setBusy(false);
  }
  async function confirm(ev: EvidenceItem) {
    const k = keep[ev.id] ?? {};
    const chosen = ev.extracted_claims.filter((_, i) => k[i] !== false);
    const updated = await confirmClaims(ev.id, chosen);
    onItems(all.map((x) => (x.id === ev.id ? updated : x)));
  }

  return (
    <section className="border-t border-rule pt-5">
      <h2 className="text-lg font-semibold">{t("doc.title")}</h2>
      <p className="mt-1 text-sm text-ink-2">{t("doc.lead")}</p>
      <div className="mt-3 flex flex-col gap-3">
        <SelectField label={t("doc.type")} value={docType} onChange={(e) => setDocType(e.target.value)} options={DOC_TYPES.map((d) => ({ value: d, label: t(`doc.t.${d}` as TKey) }))} />
        <input type="file" accept="application/pdf,image/*" aria-label={t("doc.type")} className="text-sm file:mr-3 file:min-h-11 file:rounded-[3px] file:border file:border-rule-strong file:bg-sheet file:px-4 file:font-semibold"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        {err && <Notice tone="bad">{err}</Notice>}
        <Button variant="secondary" disabled={!file || busy} onClick={send}>{busy ? t("common.loading") : t("doc.read")}</Button>
      </div>
      <ul className="mt-4 flex flex-col gap-2">
        {items.map((ev) => (
          <li key={ev.id} className="sheet p-3 text-sm">
            <p className="font-semibold">{t(`doc.t.${ev.doc_type ?? "other"}` as TKey)} · {kb(ev.size_bytes)}</p>
            {ev.extracted_claims.length === 0 ? <p className="mt-1 text-ink-3">{t("doc.no_claims")}</p> : (
              <div className="ai-panel mt-2 p-3">
                <p className="mb-1 font-semibold">{t("doc.claims")}</p>
                <AdvisoryNote provider={ev.ai_observation?.provider} fallback={ev.ai_observation?.fallback_used} />
                <ul className="mt-2 flex flex-col gap-1">
                  {ev.extracted_claims.map((c, i) => (
                    <li key={i}><label className="flex min-h-10 items-center gap-2">
                      <input type="checkbox" disabled={ev.claims_confirmed} checked={keep[ev.id]?.[i] !== false}
                        onChange={(e) => setKeep((k) => ({ ...k, [ev.id]: { ...(k[ev.id] ?? {}), [i]: e.target.checked } }))} />
                      {c.label}</label></li>
                  ))}
                </ul>
                {ev.claims_confirmed ? <p className="mt-2 text-ok">{t("doc.confirmed")}</p> : <Button className="mt-2" onClick={() => confirm(ev)}>{t("doc.confirm")}</Button>}
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
