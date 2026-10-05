import type { Metadata } from "next";
import PublicShell from "@/components/PublicShell";

export const metadata: Metadata = { title: "How it works" };

const STAGES: [string, string[]][] = [
  ["Enrolment", ["Registration and profile", "Experience declaration (text or voice, Hindi or English)", "AI skill extraction — suggestions only", "Worker confirms or edits the skills"]],
  ["Orientation", ["Qualification mapping against official learning outcomes", "Worker confirms the qualification", "Self-assessment over the learning outcomes in scope"]],
  ["Assignment of RPL assessor", ["Readiness: > 70 % self-assessed coverage → direct assessment, otherwise upskilling suggested (the assessor can still proceed)", "An assessor is allocated"]],
  ["Assessment (practical skills)", ["Guided practical tasks with steps and safety rules", "Evidence photos/videos linked to rubric criteria — works offline", "AI evidence observations (advisory)", "Assessor scores every criterion 0–4", "Competency profile, skill gaps, explainable recommendation"]],
  ["Certification & Feedback", ["Assessor records the final decision with comments", "Worker sees the decision, profile and what to practise", "PDF assessment report"]],
];

export default function HowItWorks() {
  return (
    <PublicShell>
      <h1 className="text-3xl font-semibold tracking-tight">How it works</h1>
      <p className="mt-2 max-w-3xl text-ink-2">The workflow follows the RPL process in the NCVET Guidelines (Gazette of India, 19 June 2024, Annexure-1, flowchart for NSQF level 4 without formal education). Every step is a recorded state with an audit entry.</p>

      <ol className="mt-8 flex flex-col">
        {STAGES.map(([stage, steps], i) => (
          <li key={stage} className="relative grid gap-2 pb-8 pl-10 last:pb-0">
            <span aria-hidden className="absolute left-0 top-0 grid h-7 w-7 place-items-center rounded-full bg-ink text-sm font-semibold text-sheet num">{i + 1}</span>
            {i < STAGES.length - 1 && <span aria-hidden className="absolute bottom-0 left-[13px] top-8 w-0.5 bg-rule" />}
            <h2 className="text-lg font-semibold">{stage}</h2>
            <ul className="list-disc pl-5 text-sm text-ink-2">{steps.map((s) => <li key={s}>{s}</li>)}</ul>
          </li>
        ))}
      </ol>

      <section className="mt-12 grid gap-4 md:grid-cols-2">
        <div className="sheet min-w-0 p-4">
          <h2 className="font-semibold">Qualification mapping</h2>
          <pre className="mt-2 overflow-x-auto bg-paper p-3 font-mono text-xs leading-relaxed">{`match = 0.40·skill + 0.25·task + 0.15·experience
      + 0.10·occupation + 0.10·eligibility`}</pre>
          <p className="mt-2 text-sm text-ink-2">Skill and task similarity measure how much of each confirmed skill appears in the official learning-outcome text (IDF-weighted term recall). Eligibility checks the qualification&apos;s RPL Category IV rules: age ≥ 21, ≥ 3 years&apos; experience, entry education. Weights are configurable and shown with every result.</p>
        </div>
        <div className="sheet min-w-0 p-4">
          <h2 className="font-semibold">Standardised scoring</h2>
          <pre className="mt-2 overflow-x-auto bg-paper p-3 font-mono text-xs leading-relaxed">{`task %    = Σ(weight × score) / (4 × Σ weight)
LO %      = weighted mean of its tasks
overall % = weighted mean of the tasks`}</pre>
          <p className="mt-2 text-sm text-ink-2">Each criterion has its own anchor text for 0–4, mapped to the official formative-assessment dimensions (safety consciousness, quality of workmanship, …). Only assessor-confirmed scores count; AI suggestions are stored separately.</p>
        </div>
        <div className="sheet min-w-0 p-4">
          <h2 className="font-semibold">Recommendation rules (in order)</h2>
          <ol className="mt-2 list-decimal pl-5 text-sm text-ink-2">
            <li>All criteria scored by the assessor</li>
            <li>Evidence for at least half of the required items, otherwise reassessment</li>
            <li>No safety-critical criterion scored 0 or 1, otherwise not yet ready</li>
            <li>More than 70 % of assessed learning outcomes at ≥ 60 % (NCVET §6.2(c))</li>
            <li>Overall practical score ≥ 60 % (QF DGT/1001 pass mark)</li>
          </ol>
          <p className="mt-2 text-sm text-ink-2">Every rule is shown with its result and source. The outcome is a recommendation for assessor sign-off — never a certification.</p>
        </div>
        <div className="sheet min-w-0 p-4">
          <h2 className="font-semibold">Working offline</h2>
          <p className="mt-2 text-sm text-ink-2">The worker app keeps screens and changes on the phone (IndexedDB). Profile edits, task progress and photos are queued while offline and synchronised later; the server applies each change exactly once, rejects any device change to assessor-owned data, and reports conflicts instead of silently overwriting.</p>
        </div>
      </section>

      <section className="mt-12 sheet p-4">
        <h2 className="font-semibold">Reducing assessor-to-assessor variation</h2>
        <p className="mt-2 text-sm text-ink-2">The consistency dashboard measures agreement when several assessors score the same cases: spread of scores, exact and within-one agreement, weighted Cohen&apos;s κ, Fleiss&apos; κ and ICC(2,1). In this prototype it runs on a clearly labelled simulation dataset, so it demonstrates the measurement, not a proven real-world improvement.</p>
      </section>
    </PublicShell>
  );
}
