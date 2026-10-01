"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import VoiceInput from "@/components/VoiceInput";
import { AdvisoryNote, Button, Notice, Spinner, Stamp, TextArea, TextField } from "@/components/ui";
import { confirmSkills, declareExperience, extractSkills, getWorker } from "@/lib/data/worker";
import { useSession } from "@/lib/useSession";
import { useT, type TKey } from "@/lib/i18n";
import { ApiError } from "@/lib/api";
import type { ExtractedItem, ExtractionResponse, SkillKind, Worker } from "@/lib/types";

type Row = { kind: SkillKind; label: string; source: "ai" | "worker"; confidence: number | null; source_text?: string | null; keep: boolean };

const GROUPS: { key: keyof ExtractionResponse["extraction"]; kind: SkillKind; title: TKey; addable: boolean }[] = [
  { key: "skills", kind: "skill", title: "exp.skills", addable: true },
  { key: "tools", kind: "tool", title: "exp.tools", addable: true },
  { key: "equipment", kind: "equipment", title: "exp.equipment", addable: false },
  { key: "safety_practices", kind: "safety", title: "exp.safety", addable: true },
  { key: "learning_mode", kind: "learning_mode", title: "exp.learning", addable: false },
  { key: "tasks", kind: "task", title: "exp.tasks", addable: false },
];

export default function ExperiencePage() {
  const { t, lang } = useT();
  const s = useSession();
  const wid = s?.user.worker_id ?? "";
  const [worker, setWorker] = useState<Worker | null>(null);
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"text" | "voice">("text");
  const [phase, setPhase] = useState<"write" | "analysing" | "review" | "done">("write");
  const [ext, setExt] = useState<ExtractionResponse | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [occupation, setOccupation] = useState("");
  const [years, setYears] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!wid) return;
    getWorker(wid).then((w) => {
      setWorker(w);
      const latest = w.experiences.at(-1);
      if (latest) setText(latest.raw_text);
      if (["SKILLS_CONFIRMED", "QUALIFICATION_MATCHED", "QUALIFICATION_CONFIRMED"].includes(w.status)) setPhase("done");
    }).catch(fail);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wid]);

  function fail(e: unknown) {
    setErr(e instanceof ApiError ? (e.isOffline ? t("err.offline") : e.message) : t("err.generic"));
    setBusy(false);
  }

  async function analyse() {
    setErr(null);
    setBusy(true);
    setPhase("analysing");
    try {
      const exp = await declareExperience(wid, text.trim(), mode, lang);
      const r = await extractSkills(wid, exp.id);
      setExt(r);
      const rs: Row[] = [];
      for (const g of GROUPS) for (const i of r.extraction[g.key] as ExtractedItem[]) rs.push({ kind: g.kind, label: i.label, source: "ai", confidence: i.confidence, source_text: i.source_text, keep: true });
      setRows(rs);
      setOccupation(r.extraction.occupation ?? worker?.occupation ?? "");
      setYears(String(r.extraction.experience_years ?? worker?.years_experience ?? ""));
      setPhase("review");
    } catch (e) { fail(e); setPhase("write"); }
    setBusy(false);
  }

  async function confirm() {
    setBusy(true);
    setErr(null);
    try {
      const w = await confirmSkills(wid, {
        skills: rows.filter((r) => r.keep).map((r) => ({ kind: r.kind, label: r.label, source: r.source, confidence: r.confidence })),
        occupation: occupation || null, years_experience: years === "" ? null : Number(years), ai_observation_id: ext?.observation_id,
      });
      setWorker(w);
      setPhase("done");
      window.scrollTo(0, 0);
    } catch (e) { fail(e); }
    setBusy(false);
  }

  const confirmed = useMemo(() => worker?.skills ?? [], [worker]);

  if (!worker) return err ? <Notice tone="bad">{err}</Notice> : <Spinner label={t("common.loading")} />;

  if (phase === "done") {
    return (
      <div className="flex flex-col gap-5">
        <h1 className="text-2xl font-semibold tracking-tight">{t("exp.confirmed")}</h1>
        <Notice tone="ok">{t("exp.confirmed")} · {confirmed.length}</Notice>
        {GROUPS.map((g) => {
          const items = confirmed.filter((c) => c.kind === g.kind);
          if (!items.length) return null;
          return (
            <section key={g.kind}>
              <h2 className="label mb-2">{t(g.title)}</h2>
              <ul className="flex flex-wrap gap-2">{items.map((i) => (
                <li key={i.id} className="rounded-[3px] border border-rule-strong bg-sheet px-2.5 py-1.5 text-sm">
                  {i.label} {i.source !== "ai" && <span className="ml-1 text-xs text-ink-3">({i.source})</span>}
                </li>))}
              </ul>
            </section>
          );
        })}
        <div className="flex flex-col gap-2">
          <Link href="/worker/qualification-match" className="inline-flex min-h-14 items-center justify-center rounded-[3px] bg-ink px-5 font-semibold text-sheet">{t("next.SKILLS_CONFIRMED")}</Link>
          <Button variant="secondary" onClick={() => setPhase("write")}>{t("common.edit")}</Button>
        </div>
      </div>
    );
  }

  if (phase === "write" || phase === "analysing") {
    return (
      <div className="flex flex-col gap-5">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t("exp.title")}</h1>
          <p className="mt-1.5 text-ink-2">{t("exp.lead")}</p>
        </div>
        <TextArea label={t("exp.title")} rows={8} value={text} placeholder={t("exp.placeholder")} onChange={(e) => { setText(e.target.value); setMode("text"); }} />
        <VoiceInput onText={(v) => { setText((p) => (p ? p + " " : "") + v); setMode("voice"); }} />
        {worker.experiences.length > 0 && <p className="text-sm text-ink-3">v{worker.experiences.at(-1)!.version} · {t("exp.history")}</p>}
        {err && <Notice tone="bad">{err}</Notice>}
        <Button size="lg" block disabled={busy || text.trim().length < 10} onClick={analyse}>
          {phase === "analysing" ? <Spinner label={t("exp.analysing")} /> : t("exp.submit")}
        </Button>
      </div>
    );
  }

  // review
  const x = ext!;
  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("exp.review_title")}</h1>
        <p className="mt-1.5 text-ink-2">{t("exp.review_lead")}</p>
      </div>
      <div className="ai-panel p-3"><AdvisoryNote provider={x.provider} fallback={x.fallback_used} /></div>

      <div className="grid grid-cols-2 gap-3">
        <TextField label={t("exp.occupation")} value={occupation} onChange={(e) => setOccupation(e.target.value)} />
        <TextField label={t("exp.years")} inputMode="decimal" value={years} onChange={(e) => setYears(e.target.value.replace(/[^\d.]/g, ""))} />
      </div>

      {GROUPS.map((g) => <Group key={g.kind} title={t(g.title)} kind={g.kind} addable={g.addable} rows={rows} setRows={setRows} />)}

      {x.extraction.missing_information.length > 0 && (
        <section className="border-l-4 border-warn bg-warn-wash px-3 py-2.5">
          <h2 className="text-sm font-semibold text-warn">{t("exp.missing")}</h2>
          <ul className="mt-1 list-disc pl-5 text-[0.9375rem] text-ink-2">{x.extraction.missing_information.map((m) => <li key={m}>{m}</li>)}</ul>
        </section>
      )}

      {err && <Notice tone="bad">{err}</Notice>}
      <div className="sticky bottom-16 z-10 -mx-4 flex gap-2 border-t border-rule bg-paper px-4 py-3">
        <Button variant="secondary" size="lg" onClick={() => setPhase("write")}>{t("common.back")}</Button>
        <Button size="lg" block disabled={busy || !rows.some((r) => r.keep && r.kind === "skill")} onClick={confirm}>{busy ? t("common.saving") : t("exp.confirm")}</Button>
      </div>
    </div>
  );
}

function Group({ title, kind, addable, rows, setRows }: { title: string; kind: SkillKind; addable: boolean; rows: Row[]; setRows: (f: (r: Row[]) => Row[]) => void }) {
  const { t } = useT();
  const [draft, setDraft] = useState("");
  const mine = rows.map((r, i) => ({ r, i })).filter(({ r }) => r.kind === kind);
  if (!mine.length && !addable) return null;
  return (
    <section>
      <h2 className="label mb-2">{title}</h2>
      <ul className="sheet divide-y divide-rule">
        {mine.map(({ r, i }) => (
          <li key={i} className={`flex items-start gap-3 px-3 py-2.5 ${r.keep ? "" : "opacity-50"}`}>
            <div className="min-w-0 flex-1">
              <p className={`font-medium ${r.keep ? "" : "line-through"}`}>{r.label}
                {r.source === "ai" ? <span className="ml-2 align-middle"><Stamp kind="ai" /></span> : <span className="ml-2 text-xs text-ink-3">({t("exp.you_added")})</span>}
              </p>
              {r.source_text && kind !== "task" && <p className="mt-0.5 text-sm text-ink-3"><span className="sr-only">{t("exp.your_words")}: </span>“…{r.source_text}…”</p>}
              {r.confidence != null && <p className="mt-1 text-xs text-ink-3 num">{t("exp.confidence")} {Math.round(r.confidence * 100)}%</p>}
            </div>
            <button type="button" className="min-h-10 shrink-0 rounded-[3px] border border-rule-strong px-3 text-sm hover:border-ink"
              aria-pressed={!r.keep} onClick={() => setRows((rs) => rs.map((x, j) => (j === i ? { ...x, keep: !x.keep } : x)))}>
              {r.keep ? t("common.remove") : t("common.add")}
            </button>
          </li>
        ))}
        {addable && (
          <li className="flex gap-2 px-3 py-2.5">
            <input className="min-h-11 flex-1 rounded-[3px] border border-rule-strong bg-sheet px-3" value={draft} placeholder={t("exp.add_skill")} aria-label={`${t("common.add")}: ${title}`}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && draft.trim()) { setRows((rs) => [...rs, { kind, label: draft.trim(), source: "worker", confidence: null, keep: true }]); setDraft(""); } }} />
            <Button variant="secondary" disabled={!draft.trim()} onClick={() => { setRows((rs) => [...rs, { kind, label: draft.trim(), source: "worker", confidence: null, keep: true }]); setDraft(""); }}>{t("common.add")}</Button>
          </li>
        )}
      </ul>
    </section>
  );
}
