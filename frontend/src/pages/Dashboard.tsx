import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useToast } from "../components/Toast";
import { useLiveMonitors } from "../hooks/useLiveMonitors";
import { api, downloadCsv, errorMessage, tokens, unwrap } from "../lib/api";
import type { MonitorSummary, TeamDetail, UserOut } from "../types";

const STATUS = {
  UP: {
    dot: "bg-emerald-500 shadow-emerald-500/40 shadow-[0_0_8px_2px]",
    pill: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    label: "UP",
  },
  DOWN: {
    dot: "bg-red-500 shadow-red-500/40 shadow-[0_0_8px_2px] animate-pulse",
    pill: "bg-red-50 text-red-700 ring-red-200",
    label: "DOWN",
  },
  PAUSED: { dot: "bg-amber-400", pill: "bg-amber-50 text-amber-700 ring-amber-200", label: "PAUSED" },
  PENDING: { dot: "bg-slate-300", pill: "bg-slate-100 text-slate-500 ring-slate-200", label: "PENDING" },
} as const;

function relativeTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  if (diff < 60_000) return "just now";
  if (diff < 3600_000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400_000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function latencyColor(ms: number | null): string {
  if (ms == null) return "text-slate-400";
  if (ms < 220) return "text-emerald-600";
  if (ms < 600) return "text-amber-600";
  return "text-red-600";
}

export default function Dashboard() {
  const navigate = useNavigate();
  const toast = useToast();
  const qc = useQueryClient();
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

  const live = useLiveMonitors();

  const team = useQuery({
    queryKey: ["team"],
    queryFn: () => unwrap<TeamDetail>(api.get("/teams/me")),
    staleTime: 60_000,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["monitors"] });

  const addMonitor = useMutation({
    mutationFn: () =>
      unwrap(
        api.post("/monitors", {
          name: form.name,
          url: form.url,
          interval_min: Number(form.interval_min),
          keyword: form.keyword || null,
        }),
      ),
    onSuccess: () => {
      setForm({ name: "", url: "", interval_min: 5, keyword: "" });
      setShowForm(false);
      setFormError(null);
      toast("Monitor added — checks start within a minute");
      invalidate();
    },
    onError: (err) => setFormError(errorMessage(err)),
  });

  const pauseResume = useMutation({
    mutationFn: (m: MonitorSummary) =>
      unwrap(api.post(`/monitors/${m.id}/${m.is_paused ? "resume" : "pause"}`)),
    onSuccess: (_, v) => {
      toast(v.is_paused ? "Resumed — next check now" : "Paused — checks muted");
      invalidate();
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const removeMonitor = useMutation({
    mutationFn: (m: MonitorSummary) => unwrap(api.delete(`/monitors/${m.id}`)),
    onSuccess: () => {
      toast("Monitor deleted");
      invalidate();
    },
    onError: (e) => toast(errorMessage(e), "err"),
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
    <div className="min-h-screen">
      {/* Top bar */}
      <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/70">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-md shadow-indigo-500/20">
              <span className="text-sm font-black tracking-tight">P</span>
            </div>
            <div>
              <h1 className="text-[17px] font-extrabold tracking-tight text-slate-900">
                PulseTrack <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">AI</span>
              </h1>
              <p className="text-xs text-slate-500">
                {me.data?.user.email ?? "…"} <span className="text-slate-300">•</span> {me.data?.user.role ?? ""}{" "}
                <span className="hidden sm:inline text-slate-300">•</span> <span className="hidden sm:inline">{me.data?.user.name}</span>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/incidents"
              className="hidden sm:inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <span className="text-slate-400">✨</span> Incidents
            </Link>
            <Link
              to="/settings"
              className="hidden sm:inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              <span className="text-slate-400">⚙</span> Settings
            </Link>
            <button
              onClick={logout}
              className="rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 py-8">
        {/* Title + helper */}
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
              Overview
              <span
                title={live ? "Live updates connected" : "Live reconnecting — 30s polling fallback active"}
                className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${
                  live ? "bg-emerald-50 text-emerald-700 ring-emerald-200" : "bg-slate-100 text-slate-500 ring-slate-200"
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-emerald-500 animate-pulse" : "bg-slate-400"}`} />
                {live ? "LIVE" : "SYNCING"}
              </span>
            </h2>
            <p className="text-sm text-slate-500">
              Your websites, watched every minute. Telegram tells you when they go down.{" "}
              {team.data?.slug && (
                <Link to={`/s/${team.data.slug}`} className="font-medium text-indigo-600 hover:underline">
                  View public status page →
                </Link>
              )}
            </p>
          </div>
          <Link to="/settings" className="sm:hidden text-sm font-medium text-indigo-600 hover:underline">
            Settings →
          </Link>
        </div>

        {/* Stat cards */}
        <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="Monitors" value={rows.length} sub="free limit 10" />
          <StatCard label="Up" value={up} accent="text-emerald-600" icon="●" />
          <StatCard label="Down" value={down} accent={down ? "text-red-600" : "text-slate-700"} icon="■" glow={down > 0} />
          <StatCard label="Paused" value={paused} accent="text-amber-600" />
        </div>

        {/* Toolbar */}
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold tracking-wide text-slate-700">MONITORS</h3>
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-md shadow-indigo-500/20 hover:bg-indigo-700"
          >
            <span className="text-base leading-none">+</span> Add monitor
          </button>
        </div>

        {/* Table */}
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          {monitors.isLoading ? (
            <div className="p-6 space-y-3">
              <div className="h-4 w-32 animate-pulse rounded bg-slate-100" />
              <div className="h-10 animate-pulse rounded bg-slate-50" />
              <div className="h-10 animate-pulse rounded bg-slate-50" />
            </div>
          ) : rows.length === 0 ? (
            <div className="px-6 py-14 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-xl">◯</div>
              <p className="font-medium text-slate-900">No monitors yet</p>
              <p className="mx-auto mt-1 max-w-sm text-sm text-slate-500">
                Add your first website and we will ping it every minute. When it goes DOWN we message you on Telegram.
              </p>
              <button
                onClick={() => setShowForm(true)}
                className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-black"
              >
                Add your first monitor
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900 text-[11px] uppercase tracking-widest text-slate-300">
                  <tr>
                    <th className="px-4 py-3.5 font-semibold">Status</th>
                    <th className="px-4 py-3.5 font-semibold">Name</th>
                    <th className="px-4 py-3.5 font-semibold">URL</th>
                    <th className="px-4 py-3.5 font-semibold">Interval</th>
                    <th className="px-4 py-3.5 font-semibold">Latency</th>
                    <th className="px-4 py-3.5 font-semibold">Last check</th>
                    <th className="px-4 py-3.5 text-right font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rows.map((m) => {
                    const s = STATUS[m.current_status];
                    return (
                      <tr key={m.id} className="group hover:bg-indigo-50/40">
                        <td className="px-4 py-3.5">
                          <span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${s.pill}`}>
                            <span className={`h-2 w-2 rounded-full ${s.dot}`} />
                            {s.label}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 font-semibold text-slate-900">{m.name}</td>
                        <td className="max-w-[240px] truncate px-4 py-3.5 text-slate-500" title={m.url}>
                          {m.url}
                        </td>
                        <td className="px-4 py-3.5">
                          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                            {m.interval_min} min
                          </span>
                        </td>
                        <td className={`px-4 py-3.5 font-medium tabular-nums ${latencyColor(m.last_latency_ms)}`}>
                          {m.last_latency_ms != null ? `${m.last_latency_ms} ms` : "—"}
                        </td>
                        <td className="px-4 py-3.5 text-slate-500" title={m.last_checked_at ?? ""}>
                          {relativeTime(m.last_checked_at)}
                        </td>
                        <td className="px-4 py-3.5 text-right">
                          <div className="inline-flex items-center gap-1.5">
                            <button
                              title="Download this monitor's checks as CSV"
                              onClick={() =>
                                downloadCsv(
                                  `/monitors/${m.id}/checks/export`,
                                  `pulsetrack-checks-${m.id.slice(0, 8)}.csv`,
                                ).catch((e: unknown) => toast(errorMessage(e), "err"))
                              }
                              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                            >
                              CSV
                            </button>
                            <button
                              onClick={() => pauseResume.mutate(m)}
                              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                            >
                              {m.is_paused ? "Resume" : "Pause"}
                            </button>
                            {me.data?.user.role === "owner" && (
                              <button
                                onClick={() => {
                                  if (confirm(`Delete monitor "${m.name}"? This also deletes its checks & incidents.`))
                                    removeMonitor.mutate(m);
                                }}
                                className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
                              >
                                Delete
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <p className="mt-3 text-center text-xs text-slate-400">
          Auto-refreshes every 30 s • Telegram alerts •{" "}
          <Link to="/settings" className="font-medium text-indigo-600 hover:underline">
            Configure alerts in Settings
          </Link>
        </p>
      </div>

      {/* Add monitor modal */}
      {showForm && (
        <div className="fixed inset-0 z-40 flex items-center justify-center p-4">
          <button aria-label="close" onClick={() => setShowForm(false)} className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" />
          <div className="relative w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h3 className="text-base font-semibold text-slate-900">Add monitor</h3>
                <p className="text-sm text-slate-500">We will ping this URL every few minutes and Telegram you if it goes down.</p>
              </div>
              <button onClick={() => setShowForm(false)} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100">
                ✕
              </button>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                addMonitor.mutate();
              }}
              className="space-y-4"
            >
              <label className="block">
                <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">NAME</span>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="News site"
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">URL</span>
                <input
                  required
                  type="url"
                  value={form.url}
                  onChange={(e) => setForm({ ...form, url: e.target.value })}
                  placeholder="https://example.com"
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
                />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">EVERY</span>
                  <select
                    value={form.interval_min}
                    onChange={(e) => setForm({ ...form, interval_min: Number(e.target.value) })}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm"
                  >
                    <option value={1}>1 min</option>
                    <option value={5}>5 min</option>
                    <option value={10}>10 min</option>
                    <option value={30}>30 min</option>
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">KEYWORD (optional)</span>
                  <input
                    value={form.keyword}
                    onChange={(e) => setForm({ ...form, keyword: e.target.value })}
                    placeholder="e.g. Checkout"
                    className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
                  />
                </label>
              </div>
              {formError && <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200">{formError}</p>}
              <p className="text-xs text-slate-400">Free plan: up to 10 monitors. Checks start within a minute.</p>
              <div className="flex justify-end gap-2 pt-1">
                <button type="button" onClick={() => setShowForm(false)} className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium hover:bg-slate-50">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addMonitor.isPending}
                  className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-500/20 hover:bg-indigo-700 disabled:opacity-50"
                >
                  {addMonitor.isPending ? "Adding…" : "Create monitor"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
  icon,
  sub,
  glow,
}: {
  label: string;
  value: number;
  accent?: string;
  icon?: string;
  sub?: string;
  glow?: boolean;
}) {
  return (
    <div className={`relative overflow-hidden rounded-2xl border bg-white p-4 shadow-sm ${glow ? "border-red-200 ring-1 ring-red-100" : "border-slate-200"}`}>
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-indigo-600 to-violet-600 opacity-60" />
      <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">{label}</p>
      <div className="mt-2 flex items-baseline gap-2">
        <p className={`text-2xl font-extrabold tracking-tight ${accent ?? "text-slate-900"}`}>{value}</p>
        {icon && <span className={`text-sm ${accent ?? "text-slate-300"}`}>{icon}</span>}
      </div>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
    </div>
  );
}
