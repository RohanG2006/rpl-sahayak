"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Brand from "@/components/Brand";
import { Button, Notice, Spinner, Stamp } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { API_BASE } from "@/lib/config";
import { setSession } from "@/lib/session";
import { setDemoOffline } from "@/lib/offline/network";
import type { SessionUser } from "@/lib/types";

type Sess = { access_token: string; expires_at: string; user: SessionUser };
type Reset = { checkpoint: string; plan_id: string | null; status: string; worker_session: Sess; assessor_session: Sess };
type Status = { synthetic_workers: number; synthetic_assessments: number; raj: { worker_status: string; plan_status: string | null } | null;
  evidence_pack: { upload_name: string; criterion_code: string; caption: string; url: string }[] };

const RAJ_TEXT = "I have worked as an electrician for six years. I install wiring, switches, fans, MCBs and troubleshoot electrical faults. I learned most of this work while working with my uncle. I always switch off the main and check with tester before touching wires. I use a multimeter and crimping tool.";

const STEPS: { id: string; title: string; covers: string; checkpoint: Reset["checkpoint"] | null; as: "worker" | "assessor" | "admin"; go: (r: Reset | null) => string; note?: string }[] = [
  { id: "worker", title: "1 · Worker journey — Raj Kumar", covers: "Declaration → AI skill extraction → qualification match → self-assessment → practical task → evidence upload",
    checkpoint: "fresh", as: "worker", go: () => "/worker/experience", note: "Paste the declaration below, then follow the screens. For evidence, download a file from the evidence pack and upload it: its prepared AI observation appears instantly." },
  { id: "offline", title: "2 · Offline field workflow", covers: "Demo network mode → work offline → Reconnect & Sync with server counts",
    checkpoint: "practical", as: "worker", go: () => "/worker/assessment", note: "Tap the ✓ Synced chip → Offline. Finish tasks and add photos, then Reconnect & Sync." },
  { id: "scoring", title: "3 · Assessor scoring with AI assistance", covers: "Evidence with AI observations and suggested scores → standardised 0–4 rubric → overrides",
    checkpoint: "evidence_ready", as: "assessor", go: (r) => `/assessor/assessment/${r?.plan_id}` },
  { id: "decision", title: "4 · Recommendation & human decision", covers: "Competency profile → skill gaps → explainable recommendation → assessor's final decision",
    checkpoint: "awaiting_decision", as: "assessor", go: (r) => `/assessor/candidates/${r?.plan_id}` },
  { id: "consistency", title: "5 · Assessor consistency analytics", covers: "Before/after standardisation on the labelled simulation dataset",
    checkpoint: null, as: "assessor", go: () => "/assessor/consistency" },
  { id: "admin", title: "6 · Admin & audit", covers: "AI governance, official qualification provenance, rubric governance, audit trail",
    checkpoint: null, as: "admin", go: () => "/admin/dashboard" },
];

export default function DemoPage() {
  const router = useRouter();
  const [st, setSt] = useState<Status | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => { api<Status>("/demo/status", { auth: false, cache: false }).then(setSt).catch((e) => setErr(e instanceof ApiError && e.status === 404 ? "Demo mode is disabled on this server (DEMO_MODE_ENABLED=false)." : "Cannot reach the API.")); }, []);

  async function run(step: (typeof STEPS)[number]) {
    setBusy(step.id); setErr(null);
    try {
      setDemoOffline(false);
      let r: Reset | null = null;
      let sess: Sess;
      if (step.checkpoint) {
        r = await api<Reset>("/demo/raj", { body: { checkpoint: step.checkpoint }, auth: false });
        sess = step.as === "worker" ? r.worker_session : r.assessor_session;
      } else {
        const login = step.as === "admin" ? "admin@demo.rpl" : "assessor1@demo.rpl";
        sess = await api<Sess>("/auth/login", { body: { login, password: "demo1234" }, auth: false });
      }
      setSession(sess.access_token, sess.user, sess.expires_at);
      router.push(step.go(r));
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Could not prepare this step.");
      setBusy(null);
    }
  }

  return (
    <div className="min-h-dvh">
      <header className="border-b border-rule bg-sheet"><div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4"><Brand /><span className="stamp border-2 border-dashed border-warn bg-warn-wash text-warn">Demo mode</span></div></header>
      <main className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Five-minute demonstration</h1>
          <p className="mt-2 max-w-3xl text-ink-2">Raj Kumar has six years of informal electrician experience and no formal credential. Each step below resets his <b>synthetic</b> record to the right point, signs in as the right person and opens the right screen, so nothing waits on live AI calls.</p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm"><Stamp kind="synthetic" /> <span className="text-ink-3">All people, scores and evidence images here are synthetic demonstration data. AI evidence notes on these images are prepared outputs, labelled as such.</span></div>
        </div>
        {err && <Notice tone="bad">{err}</Notice>}
        {!st && !err && <Spinner label="Checking demo data…" />}
        {st && <p className="text-sm text-ink-3 num">{st.synthetic_workers} synthetic workers · {st.synthetic_assessments} synthetic assessments · Raj: {st.raj?.plan_status ?? st.raj?.worker_status ?? "not seeded"}</p>}

        <ol className="grid gap-3 md:grid-cols-2">
          {STEPS.map((s) => (
            <li key={s.id} className="sheet flex flex-col gap-2 p-4">
              <h2 className="text-lg font-semibold">{s.title}</h2>
              <p className="text-sm text-ink-2">{s.covers}</p>
              {s.note && <p className="text-xs text-ink-3">{s.note}</p>}
              <p className="text-xs text-ink-3">Signs in as {s.as === "worker" ? "Raj Kumar (worker)" : s.as === "assessor" ? "Meera Iyer, assessor A01" : "Demo Administrator"}{s.checkpoint ? ` · resets Raj to “${s.checkpoint.replace("_", " ")}”` : ""}</p>
              <Button className="mt-auto" disabled={!st || !!busy} onClick={() => run(s)}>{busy === s.id ? "Preparing…" : "Open this step"}</Button>
            </li>
          ))}
        </ol>

        <section className="sheet p-4">
          <h2 className="font-semibold">Raj&apos;s declaration (for step 1)</h2>
          <p className="mt-2 border-l-2 border-rule-strong pl-3 text-ink-2">{RAJ_TEXT}</p>
          <Button className="mt-2" variant="secondary" onClick={() => { navigator.clipboard?.writeText(RAJ_TEXT).then(() => setCopied(true)).catch(() => {}); }}>{copied ? "Copied" : "Copy text"}</Button>
        </section>

        {st && st.evidence_pack.length > 0 && (
          <section>
            <h2 className="mb-1 font-semibold">Evidence pack (synthetic placeholders)</h2>
            <p className="mb-3 text-sm text-ink-3">Download and upload during step 1 under the matching criterion. Keep the file names: they identify the prepared AI observation.</p>
            <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {st.evidence_pack.map((e) => (
                <li key={e.upload_name} className="sheet p-2 text-xs">
                  {/* eslint-disable-next-line @next/next/no-img-element -- small API-served placeholder */}
                  <img src={`${API_BASE}${e.url}`} alt={`Synthetic placeholder for ${e.criterion_code}`} className="aspect-[4/3] w-full border border-rule object-cover" loading="lazy" />
                  <p className="mt-1 font-semibold">{e.criterion_code}</p>
                  <p className="truncate text-ink-3">{e.caption}</p>
                  <a className="text-accent underline" href={`${API_BASE}${e.url}`} download={e.upload_name}>Download</a>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}
