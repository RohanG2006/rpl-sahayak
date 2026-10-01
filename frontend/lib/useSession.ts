"use client";
import { useEffect, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { getSession, subscribeSession } from "./session";
import type { Role } from "./types";

let cachedRaw: string | null = null;
let cached: ReturnType<typeof getSession> = null;
function snapshot() {
  const raw = typeof window === "undefined" ? null : localStorage.getItem("rpl.session");
  if (raw !== cachedRaw) { cachedRaw = raw; cached = getSession(); }
  return cached;
}

export function useSession() {
  return useSyncExternalStore(subscribeSession, snapshot, () => null);
}

/** Client-side guard: redirect to /login when signed out or wrong role. Server APIs enforce RBAC independently. */
export function useRequireRole(...roles: Role[]) {
  const s = useSession();
  const router = useRouter();
  const ok = !!s && roles.includes(s.user.role);
  useEffect(() => {
    const t = setTimeout(() => {
      const cur = getSession();
      if (!cur) router.replace(`/login?next=${encodeURIComponent(location.pathname)}`);
      else if (!roles.includes(cur.user.role)) router.replace(`/${cur.user.role}/dashboard`);
    }, 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ok]);
  return ok ? s : null;
}
