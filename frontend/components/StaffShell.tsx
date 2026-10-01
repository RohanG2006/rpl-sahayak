"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import Brand from "./Brand";
import { clearSession } from "@/lib/session";
import { useSession } from "@/lib/useSession";

type NavItem = { href: string; label: string };
const ASSESSOR: NavItem[] = [
  { href: "/assessor/dashboard", label: "Dashboard" },
  { href: "/assessor/candidates", label: "Candidates" },
  { href: "/assessor/consistency", label: "Consistency" },
];
const ADMIN: NavItem[] = [
  { href: "/admin/dashboard", label: "Dashboard" },
  { href: "/admin/qualifications", label: "Qualifications" },
  { href: "/admin/tasks", label: "Tasks & rubrics" },
  { href: "/admin/assessors", label: "Users" },
  { href: "/admin/analytics", label: "Analytics" },
  { href: "/admin/audit", label: "Audit log" },
  { href: "/assessor/candidates", label: "All candidates" },
  { href: "/assessor/consistency", label: "Consistency" },
];

/** Assessor/admin workspace: data-dense, desktop-first, collapses to a top bar on small screens. */
export default function StaffShell({ children, status }: { children: ReactNode; status?: ReactNode }) {
  const s = useSession();
  const path = usePathname();
  const router = useRouter();
  const nav = s?.user.role === "admin" ? ADMIN : ASSESSOR;
  return (
    <div className="flex min-h-dvh flex-col md:flex-row">
      <aside className="border-b border-rule bg-sheet md:sticky md:top-0 md:h-dvh md:w-56 md:shrink-0 md:border-b-0 md:border-r">
        <div className="flex h-14 items-center justify-between px-4 md:h-16"><Brand href={`/${s?.user.role ?? "assessor"}/dashboard`} /></div>
        <nav aria-label="Workspace" className="overflow-x-auto px-2 pb-2 md:pb-0">
          <ul className="flex gap-1 md:flex-col">
            {nav.map((n) => {
              const on = path === n.href || (n.href !== "/assessor/dashboard" && n.href !== "/admin/dashboard" && path.startsWith(n.href));
              return (
                <li key={n.href}>
                  <Link href={n.href} aria-current={on ? "page" : undefined}
                    className={`flex min-h-10 items-center whitespace-nowrap rounded-[3px] px-3 text-sm font-medium ${on ? "bg-ink text-sheet" : "text-ink-2 hover:bg-black/5"}`}>{n.label}</Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="hidden px-4 pt-6 md:block">
          <p className="label">Signed in</p>
          <p className="mt-1 text-sm font-medium">{s?.user.full_name}</p>
          <p className="text-xs text-ink-3">{s?.user.role}{s?.user.assessor_code ? ` · ${s.user.assessor_code}` : ""}</p>
          <button className="mt-3 text-sm text-ink-2 underline underline-offset-2" onClick={() => { clearSession("logout"); router.replace("/login"); }}>Sign out</button>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        {status && <div className="border-b border-rule bg-sheet px-6 py-2">{status}</div>}
        <main className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}
