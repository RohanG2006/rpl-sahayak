"use client";
import { useEffect, useState } from "react";
import { Button, Notice, Spinner } from "@/components/ui";
import { getAdminTasks, patchCriterion, patchTask, type AdminCriterion, type AdminTask } from "@/lib/data/admin";
import { ApiError } from "@/lib/api";

export default function AdminTasks() {
  const [tasks, setTasks] = useState<AdminTask[] | null>(null);
  const [open, setOpen] = useState<string | null>("T01");
  const [msg, setMsg] = useState<{ tone: "ok" | "bad"; text: string } | null>(null);
  const load = () => getAdminTasks().then(setTasks).catch((e) => setMsg({ tone: "bad", text: e instanceof ApiError ? e.message : "Could not load." }));
  useEffect(() => { load(); }, []);
  if (!tasks) return <Spinner label="Loading task bank…" />;

  async function run(p: Promise<unknown>, ok: string) {
    setMsg(null);
    try { await p; setMsg({ tone: "ok", text: ok }); await load(); }
    catch (e) { setMsg({ tone: "bad", text: e instanceof ApiError ? e.message : "Save failed." }); }
  }

  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Tasks & rubrics</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink-2">Project-authored task bank derived from the official Electrician learning outcomes. Wording, anchors and Hindi titles can be edited at any time.
          <b> Weights, the safety-critical flag and activation lock once scores exist</b>, because results are computed live and changing them would silently rewrite past assessments. Every edit is audited.</p>
      </header>
      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}
      <ul className="flex flex-col gap-2">
        {tasks.map((t) => {
          const locked = t.scores_recorded > 0;
          return (
            <li key={t.task_code} className="sheet">
              <button className="flex min-h-14 w-full items-center gap-3 px-4 text-left" aria-expanded={open === t.task_code} onClick={() => setOpen(open === t.task_code ? null : t.task_code)}>
                <span className="font-mono font-semibold">{t.task_code}</span>
                <span className="flex-1 font-medium">{t.title}</span>
                <span className="text-xs text-ink-3 num">LO {t.lo_numbers.join(", ")} · weight {t.weight} · {t.criteria.length} criteria</span>
                {locked && <span className="stamp border border-ink">🔒 {t.scores_recorded} scores</span>}
                {!t.is_active && <span className="stamp border border-bad text-bad">inactive</span>}
              </button>
              {open === t.task_code && <TaskEditor t={t} locked={locked} onSaveTask={(b) => run(patchTask(t.task_code, b), `${t.task_code} saved.`)}
                onSaveCrit={(code, b) => run(patchCriterion(code, b), `${code} saved.`)} />}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function TaskEditor({ t, locked, onSaveTask, onSaveCrit }: { t: AdminTask; locked: boolean; onSaveTask: (b: Partial<AdminTask>) => void; onSaveCrit: (code: string, b: Partial<AdminCriterion>) => void }) {
  const [title, setTitle] = useState(t.title);
  const [titleHi, setTitleHi] = useState(t.title_hi ?? "");
  const [weight, setWeight] = useState(String(t.weight));
  return (
    <div className="flex flex-col gap-4 border-t border-rule p-4">
      <div className="grid gap-3 md:grid-cols-[2fr_2fr_7rem_auto] md:items-end">
        <label className="text-sm font-medium">Title<input className="mt-1 block min-h-10 w-full rounded-[3px] border border-rule-strong bg-sheet px-2" value={title} onChange={(e) => setTitle(e.target.value)} /></label>
        <label className="text-sm font-medium">Title (Hindi)<input className="mt-1 block min-h-10 w-full rounded-[3px] border border-rule-strong bg-sheet px-2" value={titleHi} onChange={(e) => setTitleHi(e.target.value)} /></label>
        <label className="text-sm font-medium">Weight<input type="number" step="0.25" min="0.25" max="5" disabled={locked} className="mt-1 block min-h-10 w-full rounded-[3px] border border-rule-strong bg-sheet px-2 disabled:bg-paper disabled:text-ink-3" value={weight} onChange={(e) => setWeight(e.target.value)} /></label>
        <Button onClick={() => onSaveTask({ title, title_hi: titleHi, ...(locked ? {} : { weight: Number(weight) }) })}>Save task</Button>
      </div>
      {t.criteria.map((c) => <CriterionEditor key={c.criterion_code} c={c} onSave={(b) => onSaveCrit(c.criterion_code, b)} />)}
    </div>
  );
}

function CriterionEditor({ c, onSave }: { c: AdminCriterion; onSave: (b: Partial<AdminCriterion>) => void }) {
  const locked = c.scores_recorded > 0;
  const [text, setText] = useState(c.text);
  const [anchors, setAnchors] = useState<Record<string, string>>(c.anchors);
  const [weight, setWeight] = useState(String(c.weight));
  const [safety, setSafety] = useState(c.is_safety_critical);
  return (
    <fieldset className="rounded-[3px] border border-rule p-3">
      <legend className="px-1 text-sm font-semibold"><span className="font-mono">{c.criterion_code}</span> · {c.qf_dimension}{locked && <span className="ml-2 text-xs font-normal text-ink-3">🔒 weight & safety flag locked ({c.scores_recorded} scores)</span>}</legend>
      <p className="mb-2 text-xs text-ink-3">{c.qf_criterion_ref}</p>
      <div className="grid gap-2 md:grid-cols-[1fr_6rem_auto]">
        <label className="text-sm">Criterion text<textarea rows={2} className="mt-1 block w-full rounded-[3px] border border-rule-strong bg-sheet px-2 py-1" value={text} onChange={(e) => setText(e.target.value)} /></label>
        <label className="text-sm">Weight<input type="number" step="0.25" min="0.25" max="5" disabled={locked} className="mt-1 block min-h-10 w-full rounded-[3px] border border-rule-strong bg-sheet px-2 disabled:bg-paper" value={weight} onChange={(e) => setWeight(e.target.value)} /></label>
        <label className="flex items-center gap-2 self-end pb-2 text-sm"><input type="checkbox" disabled={locked} checked={safety} onChange={(e) => setSafety(e.target.checked)} /> Safety-critical</label>
      </div>
      <div className="mt-2 grid gap-1.5 md:grid-cols-5">{["0", "1", "2", "3", "4"].map((k) => (
        <label key={k} className="text-xs">Anchor {k}<textarea rows={3} className="mt-0.5 block w-full rounded-[3px] border border-rule-strong bg-sheet px-2 py-1 text-xs" value={anchors[k] ?? ""} onChange={(e) => setAnchors({ ...anchors, [k]: e.target.value })} /></label>))}
      </div>
      <Button className="mt-2" variant="secondary" onClick={() => onSave({ text, anchors, ...(locked ? {} : { weight: Number(weight), is_safety_critical: safety }) })}>Save {c.criterion_code}</Button>
    </fieldset>
  );
}
