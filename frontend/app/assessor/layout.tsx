"use client";
import type { ReactNode } from "react";
import StaffShell from "@/components/StaffShell";
import { Spinner } from "@/components/ui";
import { useRequireRole } from "@/lib/useSession";

export default function AssessorLayout({ children }: { children: ReactNode }) {
  const s = useRequireRole("assessor", "admin");
  if (!s) return <div className="grid min-h-dvh place-items-center"><Spinner label="Loading…" /></div>;
  return <StaffShell>{children}</StaffShell>;
}
