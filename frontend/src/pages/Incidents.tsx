import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useToast } from "../components/Toast";
import { api, downloadCsv, errorMessage, unwrap } from "../lib/api";
import type { Analysis, AskAnswer, IncidentOut } from "../types";

type Filter = "ALL" | "OPEN" | "ACK" | "RESOLVED";

export default function Incidents() {
  const toast = useToast();
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Filter>("ALL");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");

  const incidents = useQuery({
    queryKey: ["incidents", filter],
    queryFn: () =>
      unwrap<IncidentOut[]>(
        api.get("/incidents", { params: filter === "ALL" ? {} : { status: filter } }),
      ),
  });

  const selected = (incidents.data ?? []).find((i) => i.id === selectedId) ?? null;

  const analysis = useQuery({
    queryKey: ["analysis", selectedId],
    queryFn: () => unwrap<Analysis>(api.get(`/incidents/${selectedId}/analysis`)),
    enabled: !!selectedId,
    retry: false,
  });

  const explain = useMutation({
    mutationFn: () => unwrap<Analysis>(api.post(`/incidents/${selectedId}/analyze`)),
    onSuccess: (data) => {
      qc.setQueryData(["analysis", selectedId], data);
      toast(data.cached ? "Loaded saved analysis ($0)" : "AI analysis ready");
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const ack = useMutation({
    mutationFn: () => unwrap<IncidentOut>(api.post(`/incidents/${selectedId}/acknowledge`)),
    onSuccess: () => {
      toast("Acknowledged — escalation stopped");
      qc.invalidateQueries({ queryKey: ["incidents"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const ask = useMutation({
    mutationFn: () => unwrap<AskAnswer>(api.post("/ai/ask", { question })),
    onError: (e) => toast(errorMessage(e), "err"),
  });

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <Link to="/" className="text-sm font-medium text-slate-600 hover:text-slate-900">
            ← Back to Dashboard
          </Link>
          <div className="hidden sm:block text-sm text-slate-500">AI explains every outage</div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">Incidents</h1>
          <p className="text-sm text-slate-500">
            Every outage, with AI root-cause. Acknowledge to stop escalation.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
          {/* List */}
          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between gap-1.5 border-b border-slate-100 px-4 py-3">
              <div className="flex gap-1.5">
                {(["ALL", "OPEN", "ACK", "RESOLVED"] as Filter[]).map((f) => (
                  <button
                    key={f}
                    onClick={() => {
                      setFilter(f);
                      setSelectedId(null);
                    }}
                    className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${
                      filter === f
                        ? "bg-slate-900 text-white ring-slate-900"
                        : "bg-white text-slate-500 ring-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>
              <button
                title="Download incidents as CSV (respects the filter)"
                onClick={() => {
                  const q = filter === "ALL" ? "" : `?status=${filter}`;
                  downloadCsv("/incidents/export" + q, "pulsetrack-incidents.csv").catch(
                    (e: unknown) => toast(errorMessage(e), "err"),
                  );
                }}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                Export CSV
              </button>
            </div>
            {incidents.isLoading ? (
              <p className="px-4 py-6 text-sm text-slate-400">Loading incidents…</p>
            ) : (incidents.data ?? []).length === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-slate-400">
                No incidents here. Break something to see AI in action. 🎉
              </p>
            ) : (
              <div className="divide-y divide-slate-100">
                {(incidents.data ?? []).map((i) => (
                  <button
                    key={i.id}
                    onClick={() => setSelectedId(i.id)}
                    className={`block w-full px-4 py-3 text-left hover:bg-indigo-50/40 ${
                      selectedId === i.id ? "bg-indigo-50/60" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-mono text-xs text-slate-500">{i.id.slice(0, 8)}</p>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ${
                          i.status === "OPEN"
                            ? "bg-red-50 text-red-700 ring-red-200"
                            : i.status === "ACK"
                              ? "bg-amber-50 text-amber-700 ring-amber-200"
                              : "bg-emerald-50 text-emerald-700 ring-emerald-200"
                        }`}
                      >
                        {i.status}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {new Date(i.started_at).toLocaleString()}
                      {i.downtime_sec != null ? ` • down ${Math.round(i.downtime_sec / 60)}m` : ""}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </section>

          {/* Detail */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            {!selected ? (
              <p className="py-10 text-center text-sm text-slate-400">
                Select an incident to inspect it.
              </p>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <p className="font-mono text-sm text-slate-700">{selected.id.slice(0, 8)}</p>
                  {selected.status === "OPEN" && (
                    <button
                      onClick={() => ack.mutate()}
                      disabled={ack.isPending}
                      className="rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-black disabled:opacity-50"
                    >
                      {ack.isPending ? "Acking…" : "Acknowledge (stop escalation)"}
                    </button>
                  )}
                </div>

                {/* AI analysis */}
                <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-900">✨ AI root-cause</h3>
                    <button
                      onClick={() => explain.mutate()}
                      disabled={explain.isPending}
                      className="rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {explain.isPending ? "Thinking…" : "Explain"}
                    </button>
                  </div>
                  {analysis.data?.summary ? (
                    <>
                      <p className="whitespace-pre-wrap text-sm text-slate-700">
                        {analysis.data.summary}
                      </p>
                      {analysis.data.cached && (
                        <p className="mt-1 text-xs text-slate-400">Served from cache — $0, ~50ms.</p>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-slate-400">
                      {analysis.isError
                        ? "No analysis yet — hit Explain."
                        : explain.isPending
                          ? "Asking Gemini… (1 call, then cached 24h)"
                          : "No analysis yet — hit Explain."}
                    </p>
                  )}
                </div>
              </div>
            )}
          </section>
        </div>

        {/* Ask */}
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Ask about your outages</h2>
          <p className="text-sm text-slate-500">Grounded in your team's history, backed by SRE knowledge. Try “give me a solution”.</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (question.trim().length >= 3) ask.mutate();
            }}
            className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto]"
          >
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Why was my site down on Tuesday?"
              className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
            />
            <button
              type="submit"
              disabled={ask.isPending || question.trim().length < 3}
              className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {ask.isPending ? "Asking…" : "Ask AI"}
            </button>
          </form>
          {ask.data?.answer && (
            <p className="mt-3 whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-sm text-slate-700">
              {ask.data.answer}
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
