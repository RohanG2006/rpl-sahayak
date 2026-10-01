"use client";
import type { SessionUser } from "./types";

/*
  Session storage. Prototype choice: token kept in localStorage so the worker PWA keeps working offline
  after a reload. Production would use an httpOnly refresh cookie + short-lived in-memory access token.
*/
const KEY = "rpl.session";
const listeners = new Set<() => void>();

type Stored = { token: string; user: SessionUser; expiresAt: string };

function read(): Stored | null {
  if (typeof window === "undefined") return null;
  try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch { return null; }
}

export function getSession(): Stored | null { return read(); }
export function getToken(): string | null { return read()?.token ?? null; }
export function getUser(): SessionUser | null { return read()?.user ?? null; }

export function setSession(token: string, user: SessionUser, expiresAt: string) {
  try { localStorage.setItem(KEY, JSON.stringify({ token, user, expiresAt })); } catch { /* storage blocked */ }
  listeners.forEach((l) => l());
}

export function updateUser(patch: Partial<SessionUser>) {
  const s = read();
  if (s) setSession(s.token, { ...s.user, ...patch }, s.expiresAt);
}

export function clearSession(reason?: "expired" | "invalid" | "logout") {
  try {
    localStorage.removeItem(KEY);
    if (reason && reason !== "logout") sessionStorage.setItem("rpl.signout_reason", reason);
  } catch { /* ignore */ }
  listeners.forEach((l) => l());
}

export function subscribeSession(fn: () => void) { listeners.add(fn); return () => { listeners.delete(fn); }; }
