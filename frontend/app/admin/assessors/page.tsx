"use client";
import { useEffect, useState } from "react";
import { Button, Notice, SelectField, Spinner, Stamp, TextField } from "@/components/ui";
import { createUser, getUsers, patchUser, type AdminUser } from "@/lib/data/admin";
import { ApiError } from "@/lib/api";
import { useSession } from "@/lib/useSession";

export default function AdminUsers() {
  const s = useSession();
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [role, setRole] = useState<"assessor" | "admin">("assessor");
  const [form, setForm] = useState({ login: "", full_name: "", assessor_code: "" });
  const [created, setCreated] = useState<AdminUser | null>(null);
  const [msg, setMsg] = useState<{ tone: "ok" | "bad"; text: string } | null>(null);
  const [filter, setFilter] = useState("staff");
  const err = (e: unknown) => setMsg({ tone: "bad", text: e instanceof ApiError ? e.message : "Request failed." });

  const load = () => getUsers().then(setUsers).catch(err);
  useEffect(() => {
    getUsers().then(setUsers).catch((e) => setMsg({ tone: "bad", text: e instanceof ApiError ? e.message : "Request failed." }));
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault(); setMsg(null); setCreated(null);
    try {
      const u = await createUser({ login: form.login, full_name: form.full_name, role, assessor_code: role === "assessor" ? form.assessor_code : undefined });
      setCreated(u); setForm({ login: "", full_name: "", assessor_code: "" }); await load();
    } catch (x) { err(x); }
  }
  async function toggle(u: AdminUser) {
    setMsg(null);
    try { await patchUser(u.id, { is_active: !u.is_active }); await load(); setMsg({ tone: "ok", text: `${u.assessor_code ?? u.login} ${u.is_active ? "deactivated" : "activated"}.` }); } catch (x) { err(x); }
  }

  if (!users) return <Spinner label="Loading users…" />;
  const shown = users.filter((u) => filter === "all" || (filter === "staff" ? u.role !== "worker" : u.role === filter));

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
      {msg && <Notice tone={msg.tone}>{msg.text}</Notice>}

      <form onSubmit={create} className="sheet grid gap-3 p-4 md:grid-cols-5 md:items-end">
        <SelectField label="Role" value={role} onChange={(e) => setRole(e.target.value as "assessor" | "admin")} options={[{ value: "assessor", label: "Assessor" }, { value: "admin", label: "Administrator" }]} />
        <TextField label="Login (email)" value={form.login} onChange={(e) => setForm({ ...form, login: e.target.value })} required />
        <TextField label="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
        {role === "assessor" ? <TextField label="Assessor code" placeholder="A06" value={form.assessor_code} onChange={(e) => setForm({ ...form, assessor_code: e.target.value.toUpperCase() })} required /> : <span />}
        <Button type="submit">Create account</Button>
      </form>
      {created?.temporary_password && (
        <Notice tone="warn">Account <b>{created.login}</b> created. Temporary password (shown once, not stored in readable form): <span className="font-mono">{created.temporary_password}</span></Notice>
      )}

      <div className="flex gap-1" role="tablist">{[["staff", "Staff"], ["assessor", "Assessors"], ["worker", "Workers"], ["all", "All"]].map(([k, l]) => (
        <button key={k} role="tab" aria-selected={filter === k} onClick={() => setFilter(k)} className={`min-h-10 rounded-[3px] border px-3 text-sm font-medium ${filter === k ? "border-ink bg-ink text-sheet" : "border-rule-strong bg-sheet"}`}>{l}</button>))}
      </div>
      <div className="overflow-x-auto rounded-[3px] border border-rule bg-sheet">
        <table className="w-full min-w-[720px] text-sm">
          <thead><tr className="border-b border-rule-strong text-left text-xs uppercase tracking-wider text-ink-3">
            <th className="px-3 py-2">Name</th><th className="px-3 py-2">Login</th><th className="px-3 py-2">Role</th><th className="px-3 py-2 text-right">Open plans</th><th className="px-3 py-2 text-right">Decisions</th><th className="px-3 py-2">Status</th><th className="px-3 py-2" /></tr></thead>
          <tbody>{shown.map((u) => (
            <tr key={u.id} className="border-b border-rule last:border-0">
              <td className="px-3 py-2 font-medium">{u.full_name} {u.data_origin === "synthetic" && <Stamp kind="synthetic">Synthetic</Stamp>}</td>
              <td className="px-3 py-2 font-mono text-xs">{u.role === "worker" ? "XXXXXX" + u.login.slice(-4) : u.login}</td>
              <td className="px-3 py-2">{u.role}{u.assessor_code ? ` · ${u.assessor_code}` : ""}</td>
              <td className="px-3 py-2 text-right num">{u.open_plans ?? "—"}</td><td className="px-3 py-2 text-right num">{u.decisions ?? "—"}</td>
              <td className={`px-3 py-2 font-semibold ${u.is_active ? "text-ok" : "text-bad"}`}>{u.is_active ? "✓ active" : "✕ inactive"}</td>
              <td className="px-3 py-2 text-right">{u.id !== s?.user.id && u.role !== "worker" && <Button variant="secondary" onClick={() => toggle(u)}>{u.is_active ? "Deactivate" : "Activate"}</Button>}</td>
            </tr>))}</tbody>
        </table>
      </div>
    </div>
  );
}
