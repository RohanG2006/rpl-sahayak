"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clearSession } from "@/lib/session";
import ProfileWizard from "@/components/ProfileWizard";
import { Button, Notice, Spinner } from "@/components/ui";
import { getWorker, updateWorker } from "@/lib/data/worker";
import { useSession } from "@/lib/useSession";
import { useT } from "@/lib/i18n";
import { ApiError } from "@/lib/api";
import type { Worker } from "@/lib/types";

export default function WorkerProfilePage() {
  const { t } = useT();
  const s = useSession();
  const router = useRouter();
  const [w, setW] = useState<Worker | null>(null);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const wid = s?.user.worker_id;

  useEffect(() => {
    if (!wid) return;
    getWorker(wid).then(setW).catch((e) => setErr(e instanceof ApiError && e.isOffline ? t("err.offline") : t("err.generic")));
  }, [wid, t]);

  if (err) return <Notice tone="bad">{err}</Notice>;
  if (!w || !wid) return <Spinner label={t("common.loading")} />;
  return (
    <>
      <h1 className="mb-5 text-2xl font-semibold tracking-tight">{t("nav.profile")}</h1>
      {saved && <div className="mb-4"><Notice tone="ok">{t("reg.saved")}</Notice></div>}
      <ProfileWizard key={w.id} mode="edit" initial={w} onSave={async (f) => { setW(await updateWorker(wid, f)); setSaved(true); window.scrollTo(0, 0); }} />
      <div className="mt-10 border-t border-rule pt-5">
        <Button variant="secondary" block onClick={() => { clearSession("logout"); router.replace("/login"); }}>{t("common.signout")}</Button>
      </div>
    </>
  );
}
