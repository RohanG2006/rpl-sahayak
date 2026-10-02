"use client";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Button } from "./ui";
import { useT } from "@/lib/i18n";
import { demoOffline, isOnline, setDemoOffline, subscribeNetwork } from "@/lib/offline/network";
import { flush, getSyncState, retryFailed, startSyncLoop, subscribeSync, type SyncResult } from "@/lib/offline/sync";

function useNetwork() {
  // "on" | "demo" (demo switch set to Offline) | "off" (device has no connection)
  return useSyncExternalStore(subscribeNetwork, () => (isOnline() ? "on" : demoOffline() ? "demo" : "off"), () => "on");
}
const useSync = () => useSyncExternalStore(subscribeSync, getSyncState, getSyncState);

/** Status chip (🟢 / 🟡 / 🔴 with icon + text, never colour alone) that opens the sync panel. */
export default function SyncStatus() {
  const { t } = useT();
  const net = useNetwork();
  const s = useSync();
  const [open, setOpen] = useState(false);
  useEffect(() => { startSyncLoop(); }, []);
  const online = net === "on";
  const [dot, label, tone] = !online
    ? ["●", t("sync.offline", { n: s.pending }), "border-warn bg-warn-wash text-warn"]
    : s.syncing ? ["↻", t("sync.syncing"), "border-accent bg-accent-wash text-accent-ink"]
    : s.failed ? ["✕", t("sync.failed", { n: s.failed }), "border-bad bg-bad-wash text-bad"]
    : s.pending ? ["●", t("sync.pending", { n: s.pending }), "border-warn bg-warn-wash text-warn"]
    : ["✓", t("sync.synced"), "border-ok bg-ok-wash text-ok"];
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} aria-haspopup="dialog"
        className={`inline-flex min-h-10 max-w-36 items-center gap-1.5 truncate rounded-[3px] border px-2 text-xs font-semibold ${tone}`}>
        <span aria-hidden>{dot}</span><span className="truncate">{label}</span>
      </button>
      {open && <SyncPanel onClose={() => setOpen(false)} />}
    </>
  );
}

export function OfflineBanner() {
  const { t } = useT();
  const net = useNetwork();
  if (net === "on") return null;
  return <div role="status" className="border-b border-warn bg-warn-wash px-4 py-2 text-center text-sm font-medium text-warn">{t("sync.banner")}</div>;
}

function SyncPanel({ onClose }: { onClose: () => void }) {
  const { t } = useT();
  const net = useNetwork();
  const s = useSync();
  const ref = useRef<HTMLDialogElement>(null);
  const [result, setResult] = useState<SyncResult | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { ref.current?.showModal(); }, []);
  const offlineMode = net === "demo";

  async function reconnect() {
    setBusy(true);
    setDemoOffline(false);
    setResult(await flush(true) ?? { at: new Date().toISOString(), records: { applied: 0, duplicate: 0, conflict: 0, rejected: 0, failed: 0 }, evidenceUploaded: 0, evidenceFailed: 0, networkError: !isOnline() });
    setBusy(false);
  }
  const r = result ?? s.last;

  return (
    <dialog ref={ref} onClose={onClose} aria-label={t("sync.title")} className="m-auto w-[min(440px,94vw)] rounded-[3px] border border-ink bg-sheet p-0 text-ink backdrop:bg-ink/50">
      <div className="flex items-center justify-between border-b border-rule px-4 py-3">
        <h2 className="font-semibold">{t("sync.title")}</h2>
        <Button variant="ghost" onClick={() => ref.current?.close()} aria-label={t("sync.close")}>✕</Button>
      </div>
      <div className="flex flex-col gap-4 p-4">
        <fieldset className="border-2 border-dashed border-rule-strong p-3">
          <legend className="label px-1">{t("sync.demo")}</legend>
          <div className="grid grid-cols-2 gap-1" role="radiogroup" aria-label={t("sync.demo")}>
            {[false, true].map((off) => (
              <button key={String(off)} role="radio" aria-checked={offlineMode === off} onClick={() => setDemoOffline(off)}
                className={`min-h-11 rounded-[3px] border text-sm font-semibold ${offlineMode === off ? "border-ink bg-ink text-sheet" : "border-rule-strong bg-sheet"}`}>
                {off ? `● ${t("sync.offline_btn")}` : `✓ ${t("sync.online")}`}
              </button>
            ))}
          </div>
          <p className="mt-2 text-xs text-ink-3">{t("sync.demo_hint")}</p>
        </fieldset>

        <section>
          <h3 className="label mb-1.5">{t("sync.queue")} ({s.items.length})</h3>
          {s.items.length === 0 ? <p className="text-sm text-ink-3">{t("sync.empty")}</p> : (
            <ul className="max-h-48 divide-y divide-rule overflow-y-auto border border-rule text-sm">
              {s.items.map((i) => (
                <li key={i.op_id} className="flex items-start justify-between gap-2 px-2.5 py-2">
                  <span className="min-w-0"><span className="block truncate">{i.label}</span>
                    <span className="text-xs text-ink-3 num">{new Date(i.createdAt).toLocaleTimeString()}{i.attempts ? ` · ${i.attempts} ${t("sync.attempts")}` : ""}{i.lastError ? ` · ${i.lastError}` : ""}</span></span>
                  <span className={`stamp shrink-0 border ${i.status === "failed" ? "border-bad text-bad" : "border-warn text-warn"}`}>{i.status === "failed" ? "✕" : "●"} {i.status}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {r && (
          <div role="status" className={`border-l-4 px-3 py-2 text-sm ${r.networkError ? "border-bad bg-bad-wash" : "border-ok bg-ok-wash"}`}>
            {r.networkError ? t("sync.network_error") : (
              <>
                <p className="font-semibold">{t("sync.result", { records: r.records.applied + r.records.duplicate, evidence: r.evidenceUploaded, conflicts: r.records.conflict })}</p>
                {(r.records.rejected + r.records.failed + r.evidenceFailed) > 0 && <p>{t("sync.result_rejected", { n: r.records.rejected + r.records.failed + r.evidenceFailed })}</p>}
              </>
            )}
            <p className="text-xs text-ink-3">{t("sync.last")}: {new Date(r.at).toLocaleTimeString()}</p>
          </div>
        )}

        <div className="flex flex-col gap-2">
          <Button size="lg" disabled={busy} onClick={reconnect}>{busy ? t("sync.syncing") : t("sync.reconnect")}</Button>
          {s.failed > 0 && <Button variant="secondary" disabled={busy} onClick={async () => { setBusy(true); setResult(await retryFailed()); setBusy(false); }}>{t("sync.retry")}</Button>}
        </div>
      </div>
    </dialog>
  );
}
