import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, errorMessage, tokens, unwrap } from "../lib/api";
import type { MonitorSummary, UserOut } from "../types";

const STATUS_STYLES: Record<MonitorSummary["current_status"], { dot: string; text: string }> = {
  UP: { dot: "bg-green-500", text: "text-green-700" },
  DOWN: { dot: "bg-red-500", text: "text-red-700" },
  PAUSED: { dot: "bg-amber-400", text: "text-amber-700" },
  PENDING: { dot: "bg-slate-300", text: "text-slate-500" },
};

export default function Dashboard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", url: "", interval_min: 5, keyword: "" });

  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => unwrap<{ user: UserOut }>(api.get("/auth/me")),
  });

  const monitors = useQuery({
    queryKey: ["monitors"],
    queryFn: () => unwrap<MonitorSummary[]>(api.get("/monitors")),
    refetchInterval: 30_000,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["monitors"] });

  const addMonitor = useMutation({
    mutationFn: () =>
      unwrap(
        api.post("/monitors", {
          name: form.name,
          url: form.url,
          interval_min: Number(form.interval_min),
          keyword: form.keyword || null,
        })
      ),
    onSuccess: () => {
      setForm({ name: "", url: "", interval_min: 5, keyword: "" });
      setShowForm(false);
      setFormError(null);
      invalidate();
    },
    onError: (err) => setFormError(errorMessage(err)),
  });

  const pauseResume = useMutation({
    mutationFn: (m: MonitorSummary) =>
      unwrap(api.post(`/monitors/${m.id}/${m.is_paused ? "resume" : "pause"}`)),
    onSuccess: invalidate,
  });

  const removeMonitor = useMutation({
    mutationFn: (m: MonitorSummary) => unwrap(api.delete(`/monitors/${m.id}`)),
    onSuccess: invalidate,
    onError: (err) => alert(errorMessage(err)),
  });

  function logout() {
    api.post("/auth/logout").catch(() => undefined).finally(() => {
      tokens.clear();
      navigate("/login");
    });
  }

  const rows = monitors.data ?? [];
  const up = rows.filter((m) => m.current_status === "UP").length;
  const down = rows.filter((m) => m.current_status === "DOWN").length;
  const paused = rows.filter((m) => m.current_status === "PAUSED").length;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      {/* Header */}
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            PulseTrack <span className="text-indigo-600">AI</span>
          </h1>
          <p className="text-sm text-slate-500">
            {me.data?.user.email ?? "…"} · {me.data?.user.role ?? ""} · team {me.data?.user.name}
          </p>
        </div>
        <button
          onClick={logout}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-white"
        >
          Log out
        </button>
      </header>

      {/* Stat cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Monitors" value={rows.length} />
        <StatCard label="Up" value={up} accent="text-green-600" />
        <StatCard label="Down" value={down} accent="text-red-600" />
        <StatCard label="Paused" value={paused} accent="text-amber-600" />
      </div>

      {/* Toolbar */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Monitors</h2>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
        >
          {showForm ? "Close" : "+ Add monitor"}
        </button>
      </div>

      {/* Add monitor form */}
      {showForm && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addMonitor.mutate();
          }}
          className="mb-6 grid gap-3 rounded-xl bg-white p-5 shadow md:grid-cols-5"
        >
          <label className="md:col-span-1">
            <span className="mb-1 block text-xs font-medium text-slate-600">Name</span>
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Checkout API"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="md:col-span-2">
            <span className="mb-1 block text-xs font-medium text-slate-600">URL</span>
            <input
              required
              type="url"
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
              placeholder="https://example.com"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <label>
            <span className="mb-1 block text-xs font-medium text-slate-600">Every (min)</span>
            <select
              value={form.interval_min}
              onChange={(e) => setForm({ ...form, interval_min: Number(e.target.value) })}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              <option value={1}>1</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={30}>30</option>
            </select>
          </label>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={addMonitor.isPending}
              className="w-full rounded-lg bg-green-600 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
            >
              {addMonitor.isPending ? "Adding…" : "Create"}
            </button>
          </div>
          {formError && <p className="md:col-span-5 text-sm text-red-600">{formError}</p>}
          <p className="md:col-span-5 text-xs text-slate-400">
            Free plan limit: 10 monitors. Checks actually start running in Phase 3 (worker).
          </p>
        </form>
      )}

      {/* Monitors table */}
      <div className="overflow-hidden rounded-xl bg-white shadow">
        {monitors.isLoading ? (
          <p className="p-6 text-sm text-slate-400">Loading monitors…</p>
        ) : rows.length === 0 ? (
          <p className="p-6 text-sm text-slate-400">
            No monitors yet. Click <b>+ Add monitor</b> to watch your first website.
          </p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-300">
              <tr>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">URL</th>
                <th className="px-4 py-3">Interval</th>
                <th className="px-4 py-3">Last latency</th>
                <th className="px-4 py-3">Last check</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((m) => {
                const style = STATUS_STYLES[m.current_status];
                return (
                  <tr key={m.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-2">
                        <span className={`h-2.5 w-2.5 rounded-full ${style.dot}`} />
                        <span className={`font-medium ${style.text}`}>{m.current_status}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900">{m.name}</td>
                    <td className="max-w-[220px] truncate px-4 py-3 text-slate-500">{m.url}</td>
                    <td className="px-4 py-3">{m.interval_min} min</td>
                    <td className="px-4 py-3">
                      {m.last_latency_ms != null ? `${m.last_latency_ms} ms` : "—"}
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {m.last_checked_at ? new Date(m.last_checked_at).toLocaleTimeString() : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => pauseResume.mutate(m)}
                        className="mr-2 rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50"
                      >
                        {m.is_paused ? "Resume" : "Pause"}
                      </button>
                      {me.data?.user.role === "owner" && (
                        <button
                          onClick={() => {
                            if (confirm(`Delete monitor "${m.name}"?`)) removeMonitor.mutate(m);
                          }}
                          className="rounded-md border border-red-200 px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <p className="mt-4 text-center text-xs text-slate-400">
        Auto-refreshes every 30 s · Real-time updates + charts arrive in later phases
      </p>
    </div>
  );
}

function StatCard({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accent ?? "text-slate-900"}`}>{value}</p>
    </div>
  );
}
