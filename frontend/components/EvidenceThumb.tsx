"use client";
import { useEffect, useState } from "react";
import { evidenceBlobUrl, type EvidenceItem } from "@/lib/data/evidence";

/** Authenticated, lazily-loaded thumbnail. Falls back to a labelled tile for video/PDF/audio. */
export default function EvidenceThumb({ ev, size = 72 }: { ev: EvidenceItem; size?: number }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (ev.kind !== "image") return;
    let u: string | null = null;
    let live = true;
    evidenceBlobUrl(ev.id).then((x) => { u = x; if (live) setUrl(x); }).catch(() => {});
    return () => { live = false; if (u) URL.revokeObjectURL(u); };
  }, [ev.id, ev.kind]);
  const box = { width: size, height: size };
  if (ev.kind === "image" && url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={url} alt={ev.caption ?? "Evidence photo"} style={box} className="shrink-0 border border-rule object-cover" loading="lazy" />;
  }
  return <span style={box} className="grid shrink-0 place-items-center border border-rule bg-paper text-xs font-semibold uppercase text-ink-3">{ev.kind}</span>;
}
