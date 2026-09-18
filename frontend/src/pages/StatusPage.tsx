import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { API_BASE } from "../lib/api";
import type { PublicIncident, PublicStatus } from "../types";

async function getPublic<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (res.status === 404) throw new Error("Status page not found — check the link.");
  if (!res.ok) throw new Error(`Status page unavailable (${res.status})`);
  const body = (await res.json()) as { data: T; error: { message: string } | null };
  if (body.error) throw new Error(body.error.message);
  return body.data;
}

export default function StatusPage() {
  const { slug = "" } = useParams();

  const statusQ = useQuery({
    queryKey: ["public-status", slug],
    queryFn: () => getPublic<PublicStatus>(`/status/${encodeURIComponent(slug)}`),
    refetchInterval: 30_000,
    retry: false,
  });
  const incidentsQ = useQuery({
    queryKey: ["public-incidents", slug],
    queryFn: () =>
      getPublic<PublicIncident[]>(`/status/${encodeURIComponent(slug)}/incidents?limit=20`),
    refetchInterval: 30_000,
    retry: false,
  });

  const data = statusQ.data;
  const overall = data?.overall ?? "operational";
  const banner =
    overall === "operational"
      ? "bg-emerald-500"
      : overall === "degraded"
        ? "bg-amber-500"
        : "bg-red-500";

  return (
    <div className="min-h-screen bg-[#f8fafc]">
      <div className={`w-full ${banner} transition-colors`}>
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-white/80">
              {data ? `${data.team_name} • status` : "Status"}
            </p>
            <h1 className="text-2xl font-extrabold text-white">
              {statusQ.isLoading
                ? "Loading…"
                : overall === "operational"
                  ? "All systems operational"
                  : overall === "degraded"
                    ? "Partial outage"
                    : "Major outage"}
            </h1>
          </div>
          <Link to="/" className="rounded-lg bg-white/15 px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/25">
            PulseTrack AI
          </Link>
        </div>
      </div>

      <div className="mx-auto max-w-4xl px-4 py-8 space-y-6">
        {statusQ.isError ? (
          <div className="rounded-2xl border border-red-200 bg-white p-8 text-center">
            <p className="font-semibold text-slate-900">Page not found</p>
            <p className="mt-1 text-sm text-slate-500">{(statusQ.error as Error).message}</p>
          </div>
        ) : (
          <>
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-100 px-5 py-3 text-xs font-semibold tracking-wide text-slate-500">
                MONITORS • auto-refreshes every 30s
              </div>
              {(data?.monitors ?? []).map((m) => (
                <div key={m.id} className="flex items-center justify-between border-b border-slate-50 px-5 py-3 last:border-0">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`h-2.5 w-2.5 rounded-full ${
                        m.current_status === "UP"
                          ? "bg-emerald-500"
                          : m.current_status === "DOWN"
                            ? "bg-red-500 animate-pulse"
                            : m.current_status === "PAUSED"
                              ? "bg-amber-400"
                              : "bg-slate-300"
                      }`}
                    />
                    <span className="text-sm font-medium text-slate-900">{m.name}</span>
                  </div>
                  <span className="text-xs text-slate-500">
                    {m.current_status}
                    {m.last_latency_ms != null ? ` • ${m.last_latency_ms}ms` : ""}
                  </span>
                </div>
              ))}
              {(data?.monitors ?? []).length === 0 && !statusQ.isLoading && (
                <p className="px-5 py-6 text-center text-sm text-slate-400">No monitors published yet.</p>
              )}
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">Recent incidents</h2>
              {(incidentsQ.data ?? []).length === 0 ? (
                <p className="mt-2 text-sm text-slate-400">No incidents in the last 90 days. 🎉</p>
              ) : (
                <div className="mt-3 divide-y divide-slate-100">
                  {(incidentsQ.data ?? []).map((i) => (
                    <div key={i.id} className="flex items-center justify-between py-2.5">
                      <div>
                        <p className="text-sm font-medium text-slate-900">{i.monitor_name}</p>
                        <p className="text-xs text-slate-500">
                          {new Date(i.started_at).toLocaleString()}
                          {i.downtime_sec != null ? ` • down ${Math.round(i.downtime_sec / 60)}m` : ""}
                        </p>
                      </div>
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${
                          i.status === "OPEN" || i.status === "ACK"
                            ? "bg-red-50 text-red-700 ring-red-200"
                            : "bg-emerald-50 text-emerald-700 ring-emerald-200"
                        }`}
                      >
                        {i.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
