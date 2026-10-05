import type { Metadata } from "next";
import Link from "next/link";
import PublicShell from "@/components/PublicShell";

export const metadata: Metadata = { title: "About" };

const SOURCES = [
  ["Electrician qualification file (DGT/1001, NCVET 2022/POW/DGT/06309, NSQF 4)", "https://www.nqr.gov.in/sites/default/files/QF_Electrician_CTS2.0_NSQF-4.pdf"],
  ["Wireman qualification file (DGT/1009, NCVET 2022/POW/DGT/06310, NSQF 4)", "https://www.nqr.gov.in/sites/default/files/QF_Wireman_CTS2.0_NSQF-4.pdf"],
  ["NCVET Guidelines for Recognition of Prior Learning (Gazette of India, 19 June 2024)", "https://ncvet.gov.in/wp-content/uploads/2024/09/RPL.pdf"],
  ["NCVET draft RPL guidelines (January 2023)", "https://ncvet.gov.in/wp-content/uploads/2023/01/RPL-guidelines-for-PC-30.01.23.pdf"],
];

export default function About() {
  return (
    <PublicShell>
      <h1 className="text-3xl font-semibold tracking-tight">About RPL-Sahayak AI</h1>
      <div className="mt-6 grid gap-8 md:grid-cols-[1.4fr_1fr]">
        <div className="flex flex-col gap-4 text-ink-2">
          <p>A large share of India&apos;s workforce learned their trade on the job — from a relative, an ustad or a contractor — rather than through certified training. Recognition of Prior Learning lets them be certified against NSQF qualifications without repeating training they have effectively completed.</p>
          <p>Today, RPL assessment depends heavily on manual practical evaluation: it is slow to scale, can vary between assessors and locations, and is hard to schedule for workers who cannot take time off — often in places with weak connectivity.</p>
          <p>RPL-Sahayak AI is a working prototype for Smart India Hackathon 2026, problem statement <b>SIH26242</b>. It supports the whole journey for one trade, Electrician, built so that more trades can be added as data: a qualification pack, its learning outcomes, a task bank, a rubric and evidence requirements.</p>
          <p>It is <b>not</b> an NCVET or DGT system, it is not integrated with any government platform, and it issues no certificates. The assessor&apos;s decision recorded here is a prototype record.</p>
        </div>
        <aside className="sheet p-4 text-sm">
          <h2 className="font-semibold">Principles</h2>
          <ul className="mt-2 list-disc pl-5 text-ink-2">
            <li>The human assessor is the final authority</li>
            <li>Official data is used as published, with provenance — never invented</li>
            <li>Synthetic and simulated data is labelled wherever it appears</li>
            <li>Every AI output is advisory and stored separately</li>
            <li>Works in Hindi and English, on a phone, offline</li>
          </ul>
        </aside>
      </div>

      <section className="mt-10">
        <h2 className="text-xl font-semibold">Official sources</h2>
        <p className="mt-1 text-sm text-ink-3">Downloaded on 1 October 2026; each file&apos;s SHA-256 fingerprint is recorded and checked by the test suite.</p>
        <ul className="mt-3 divide-y divide-rule border-y border-rule text-sm">
          {SOURCES.map(([name, url]) => (
            <li key={url} className="py-2.5"><span className="font-medium">{name}</span><a className="block break-all text-accent underline" href={url} target="_blank" rel="noreferrer">{url}</a></li>
          ))}
        </ul>
      </section>

      <p className="mt-8 text-sm"><Link className="font-semibold text-accent underline" href="/how-it-works">How it works →</Link></p>
    </PublicShell>
  );
}
