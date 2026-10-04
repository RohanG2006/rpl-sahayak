import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-10">
      <p className="label">SIH26242 · Prototype</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">RPL-Sahayak AI</h1>
      <p className="mt-1 text-ink-2">AI-Assisted Prior Learning Assessment &amp; Assessor Support Platform</p>
      <hr className="my-6 border-rule" />
      <p className="text-ink-2">Foundation build (Phase 1). Workflow screens are added in later phases.</p>
      <p className="mt-4"><span className="stamp stamp-ai">AI assist</span> <span className="stamp stamp-human">Assessor</span> <span className="stamp stamp-official">Official source</span> <span className="stamp stamp-synthetic">Synthetic</span></p>
      <p className="mt-6 flex gap-4"><Link className="font-semibold text-accent underline" href="/demo">Five-minute demo</Link><Link className="text-accent underline" href="/login">Sign in</Link></p>
    </main>
  );
}
