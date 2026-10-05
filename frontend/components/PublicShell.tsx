import Link from "next/link";
import type { ReactNode } from "react";
import Brand from "./Brand";

const NAV = [
  { href: "/how-it-works", label: "How it works" },
  { href: "/about", label: "About" },
  { href: "/demo", label: "Demo" },
];

export default function PublicShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-rule bg-sheet">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between gap-3 px-4">
          <Brand />
          <nav aria-label="Site" className="flex items-center gap-1 overflow-x-auto text-sm">
            {NAV.map((n) => <Link key={n.href} href={n.href} className="whitespace-nowrap rounded-[3px] px-2.5 py-2 font-medium text-ink-2 hover:bg-black/5">{n.label}</Link>)}
            <Link href="/login" className="ml-1 whitespace-nowrap rounded-[3px] bg-ink px-3 py-2 font-semibold text-sheet">Sign in</Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">{children}</main>
      <footer className="border-t border-rule bg-sheet">
        <div className="mx-auto flex max-w-5xl flex-col gap-1 px-4 py-5 text-xs text-ink-3">
          <p>RPL-Sahayak AI — SIH 2026 prototype for problem statement SIH26242. Not an NCVET/DGT system; no certificates are issued.</p>
          <p>Official qualification data: National Qualification Register (DGT/NCVET), Electrician DGT/1001 and Wireman DGT/1009. All demo people and scores are synthetic.</p>
        </div>
      </footer>
    </div>
  );
}
