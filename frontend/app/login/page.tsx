"use client";
import Link from "next/link";
import { useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import Brand from "@/components/Brand";
import LangToggle from "@/components/LangToggle";
import { Button, Notice, Stamp, TextField } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { setSession } from "@/lib/session";
import { useT } from "@/lib/i18n";
import type { SessionUser } from "@/lib/types";

const DEMO = [
  { label: "Assessor A01", login: "assessor1@demo.rpl" },
  { label: "Admin", login: "admin@demo.rpl" },
];

const noopSubscribe = () => () => {};
function wasExpired() {
  try { return sessionStorage.getItem("rpl.signout_reason") === "expired"; } catch { return false; }
}

export default function LoginPage() {
  const { t } = useT();
  const router = useRouter();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const expired = useSyncExternalStore(noopSubscribe, wasExpired, () => false);

  async function submit(e: React.FormEvent, override?: { login: string; password: string }) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const body = override ?? { login, password };
      const r = await api<{ access_token: string; expires_at: string; user: SessionUser }>("/auth/login", { body, auth: false });
      setSession(r.access_token, r.user, r.expires_at);
      try { sessionStorage.removeItem("rpl.signout_reason"); } catch { /* ignore */ }
      const next = new URLSearchParams(location.search).get("next");
      router.replace(next && next.startsWith(`/${r.user.role}`) ? next : `/${r.user.role}/dashboard`);
    } catch (e) {
      setErr(e instanceof ApiError ? (e.isOffline ? t("err.offline") : e.message) : t("err.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="mx-auto flex h-14 w-full max-w-md items-center justify-between px-4">
        <Brand /> <LangToggle />
      </header>
      <main className="mx-auto w-full max-w-md flex-1 px-4 py-8">
        <h1 className="text-2xl font-semibold tracking-tight">{t("login.title")}</h1>
        <form className="mt-6 flex flex-col gap-4" onSubmit={submit}>
          {expired && <Notice tone="warn">{t("login.expired")}</Notice>}
          <TextField label={t("login.mobile")} autoComplete="username" value={login} onChange={(e) => setLogin(e.target.value)} required />
          <TextField label={t("login.pin")} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {err && <Notice tone="bad">{err}</Notice>}
          <Button type="submit" size="lg" block disabled={busy}>{busy ? t("common.loading") : t("login.submit")}</Button>
        </form>
        <p className="mt-6 text-[0.9375rem]">
          {t("login.new")} <Link href="/register" className="font-semibold text-accent underline underline-offset-2">{t("login.register")}</Link>
        </p>

        <section className="mt-10 border-t border-rule pt-5">
          <div className="flex items-center gap-2"><h2 className="label">{t("login.demo")}</h2><Stamp kind="synthetic" /></div>
          <p className="mt-2 text-sm"><Link href="/demo" className="font-semibold text-accent underline underline-offset-2">Open the five-minute demo →</Link></p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {DEMO.map((d) => (
              <li key={d.login}>
                <Button variant="secondary" disabled={busy} onClick={(e) => submit(e as unknown as React.FormEvent, { login: d.login, password: "demo1234" })}>{d.label}</Button>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}
