"use client";
import type { ReactNode } from "react";
import WorkerShell from "@/components/WorkerShell";
import { Spinner } from "@/components/ui";
import { useRequireRole } from "@/lib/useSession";
import { useT } from "@/lib/i18n";

export default function WorkerLayout({ children }: { children: ReactNode }) {
  const s = useRequireRole("worker");
  const { t } = useT();
  if (!s) return <div className="grid min-h-dvh place-items-center"><Spinner label={t("common.loading")} /></div>;
  return <WorkerShell>{children}</WorkerShell>;
}
