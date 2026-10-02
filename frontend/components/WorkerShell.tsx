"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import Brand from "./Brand";
import LangToggle from "./LangToggle";
import SyncStatus, { OfflineBanner } from "./SyncStatus";
import { useT, type TKey } from "@/lib/i18n";

const I = {
  home: <path d="M3 10.5L12 3l9 7.5V21h-6v-6H9v6H3z" />,
  profile: <><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7" /></>,
  work: <><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z" /></>,
  match: <><rect x="3" y="4" width="18" height="16" /><path d="M7 9h10M7 13h6M7 17h4" /></>,
  tasks: <><path d="M9 6h12M9 12h12M9 18h12" /><path d="M3 6l1.5 1.5L7 5M3 12l1.5 1.5L7 11M3 18l1.5 1.5L7 17" /></>,
  progress: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
};

const NAV: { href: string; key: TKey; icon: keyof typeof I }[] = [
  { href: "/worker/dashboard", key: "nav.home", icon: "home" },
  { href: "/worker/experience", key: "nav.experience", icon: "work" },
  { href: "/worker/qualification-match", key: "nav.match", icon: "match" },
  { href: "/worker/assessment", key: "nav.assessment", icon: "tasks" },
  { href: "/worker/progress", key: "nav.progress", icon: "progress" },
];

export function Icon({ name, size = 22 }: { name: keyof typeof I; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" aria-hidden>{I[name]}</svg>;
}

export default function WorkerShell({ children, status }: { children: ReactNode; status?: ReactNode }) {
  const { t } = useT();
  const path = usePathname();
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 border-b border-rule bg-paper/95 backdrop-blur-sm">
        <div className="mx-auto flex h-14 w-full max-w-xl min-w-0 items-center justify-between gap-2 px-4">
          <Brand href="/worker/dashboard" collapse />
          <div className="flex min-w-0 items-center gap-2">
            {status ?? <SyncStatus />}
            <LangToggle />
            <Link href="/worker/profile" className="grid min-h-10 min-w-10 place-items-center rounded-[3px] border border-rule-strong hover:border-ink" aria-label={t("nav.profile")}>
              <Icon name="profile" size={18} />
            </Link>
          </div>
        </div>
        <OfflineBanner />
      </header>
      <main className="mx-auto w-full max-w-xl flex-1 px-4 pb-28 pt-5">{children}</main>
      <nav aria-label="Worker" className="fixed inset-x-0 bottom-0 z-20 border-t border-rule bg-sheet">
        <ul className="mx-auto grid max-w-xl grid-cols-5">
          {NAV.map((n) => {
            const on = path.startsWith(n.href);
            return (
              <li key={n.href}>
                <Link href={n.href} aria-current={on ? "page" : undefined}
                  className={`flex min-h-16 flex-col items-center justify-center gap-1 text-[0.75rem] font-medium ${on ? "text-ink [box-shadow:inset_0_3px_0_var(--accent)]" : "text-ink-3 hover:text-ink"}`}>
                  <Icon name={n.icon} />
                  {t(n.key)}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
