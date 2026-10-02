"use client";
/*
  Network mode = real connectivity AND NOT the demo "Offline" switch.
  The demo switch lets the offline workflow be shown on stage without unplugging anything: while it is on,
  every API call is treated exactly like a lost connection (reads come from the device cache, writes are queued).
*/
const KEY = "rpl.demoOffline";
const listeners = new Set<() => void>();

export function demoOffline(): boolean {
  try { return localStorage.getItem(KEY) === "1"; } catch { return false; }
}

export function setDemoOffline(on: boolean) {
  try {
    if (on) localStorage.setItem(KEY, "1");
    else localStorage.removeItem(KEY);
  } catch { /* storage blocked */ }
  listeners.forEach((l) => l());
}

export function isOnline(): boolean {
  if (typeof navigator === "undefined") return true;
  return navigator.onLine && !demoOffline();
}

export function subscribeNetwork(fn: () => void) {
  listeners.add(fn);
  if (typeof window !== "undefined") {
    window.addEventListener("online", fn);
    window.addEventListener("offline", fn);
  }
  return () => {
    listeners.delete(fn);
    if (typeof window !== "undefined") {
      window.removeEventListener("online", fn);
      window.removeEventListener("offline", fn);
    }
  };
}
