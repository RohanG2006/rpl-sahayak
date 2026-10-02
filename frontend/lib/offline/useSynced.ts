"use client";
import { useEffect, useRef } from "react";

/** Run `fn` after every completed sync (so screens drop optimistic 'pending' items for server truth). */
export function useOnSynced(fn: () => void) {
  const ref = useRef(fn);
  useEffect(() => { ref.current = fn; });
  useEffect(() => {
    const h = () => ref.current();
    window.addEventListener("rpl:synced", h);
    return () => window.removeEventListener("rpl:synced", h);
  }, []);
}
