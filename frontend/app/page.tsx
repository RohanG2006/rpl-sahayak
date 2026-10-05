import Link from "next/link";
import PublicShell from "@/components/PublicShell";

const ROLES = [
  { who: "Worker", what: "Describe your work in your own words, in Hindi or English. See which official qualification it matches, do the practical tasks, add photos — even with no network.", href: "/register", cta: "Register" },
  { who: "Assessor", what: "Score every criterion on one anchored 0–4 rubric, with evidence and AI observations beside it. The recommendation explains itself; the decision is yours.", href: "/login", cta: "Sign in" },
  { who: "Administrator", what: "Official qualification data with provenance, rubric governance, assessor consistency and a full audit trail.", href: "/login", cta: "Sign in" },
];

const STATUS = [
  ["Implemented", "Worker self-declaration, skill extraction, qualification mapping (Electrician, Wireman), self-assessment and readiness, guided practical tasks, evidence upload and analysis, standardised scoring, competency profile, skill gaps, explainable recommendation, assessor decision, offline queue and sync, PDF report, audit log, Hindi worker flow"],
  ["Simulated", "Demo workers and assessors, demo evidence images and their prepared AI notes, the assessor-consistency rating dataset"],
  ["Future scope", "Identity verification, Skill India Digital / NCVET integration, task banks for more trades, real multi-assessor validation study, video frame analysis at scale"],
];

export default function Home() {
  return (
    <PublicShell>
      <section className="grid gap-8 md:grid-cols-[1.3fr_1fr] md:items-end">
        <div>
          <p className="label">SIH26242 · Recognition of Prior Learning</p>
          <h1 className="mt-2 text-4xl font-semibold leading-tight tracking-tight">Years of informal work, turned into evidence an assessor can trust.</h1>
          <p className="mt-4 max-w-xl text-lg text-ink-2">RPL-Sahayak AI helps convert informal work experience into a structured, evidence-backed competency profile aligned to the official qualification — while the certification decision stays with the human assessor.</p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link href="/demo" className="inline-flex min-h-12 items-center rounded-[3px] bg-ink px-5 font-semibold text-sheet">See the five-minute demo</Link>
            <Link href="/how-it-works" className="inline-flex min-h-12 items-center rounded-[3px] border border-rule-strong bg-sheet px-5 font-semibold hover:border-ink">How it works</Link>
          </div>
        </div>
        <figure className="sheet p-4 text-sm">
          <figcaption className="label">Example · Raj Kumar (synthetic)</figcaption>
          <blockquote className="mt-2 border-l-2 border-rule-strong pl-3 text-ink-2">“I have worked as an electrician for six years… I learned most of this work while working with my uncle.”</blockquote>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            <dt className="text-ink-3">Matched to</dt><dd className="font-medium">Electrician · DGT/1001 · NSQF 4</dd>
            <dt className="text-ink-3">Evidence</dt><dd>16 items linked to rubric criteria</dd>
            <dt className="text-ink-3">AI recommendation</dt><dd><span className="stamp stamp-ai">Advisory</span> eligible for sign-off</dd>
            <dt className="text-ink-3">Decision</dt><dd><span className="stamp stamp-human">Assessor</span> recorded by a person</dd>
          </dl>
        </figure>
      </section>

      <section className="mt-14 grid gap-px overflow-hidden rounded-[3px] border border-rule bg-rule md:grid-cols-3">
        {ROLES.map((r) => (
          <div key={r.who} className="flex flex-col gap-2 bg-sheet p-5">
            <h2 className="text-lg font-semibold">{r.who}</h2>
            <p className="flex-1 text-sm text-ink-2">{r.what}</p>
            <Link href={r.href} className="text-sm font-semibold text-accent underline underline-offset-2">{r.cta} →</Link>
          </div>
        ))}
      </section>

      <section className="mt-14">
        <h2 className="text-xl font-semibold">Where the AI is — and where it stops</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="ai-panel p-4 text-sm">
            <p className="font-semibold">AI assists</p>
            <ul className="mt-2 list-disc pl-5 text-ink-2">
              <li>Reads the worker&apos;s own description and suggests skills (the worker confirms or edits)</li>
              <li>Describes what evidence photos show and what may be missing</li>
              <li>Suggests a rubric score per criterion, stored separately</li>
              <li>Explains the computed results in plain language</li>
            </ul>
          </div>
          <div className="human-panel p-4 text-sm">
            <p className="font-semibold">People decide</p>
            <ul className="mt-2 list-disc pl-5 text-ink-2">
              <li>Only the assessor&apos;s 0–4 scores enter any calculation</li>
              <li>Matching, scores, gaps and the recommendation are transparent rules, not a model</li>
              <li>The final decision can only be recorded by the assigned assessor, with comments</li>
              <li>Every override of an AI suggestion is kept in the audit trail</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="mt-14">
        <h2 className="text-xl font-semibold">What is real, what is simulated</h2>
        <dl className="mt-4 divide-y divide-rule border-y border-rule">
          {STATUS.map(([k, v]) => (
            <div key={k} className="grid gap-1 py-3 md:grid-cols-[10rem_1fr]">
              <dt className="font-semibold">{k}</dt><dd className="text-sm text-ink-2">{v}</dd>
            </div>
          ))}
        </dl>
      </section>
    </PublicShell>
  );
}
