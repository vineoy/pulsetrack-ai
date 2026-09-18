import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useToast } from "../components/Toast";
import { api, errorMessage, unwrap } from "../lib/api";
import { API_BASE } from "../lib/api";
import type {
  ApiKey,
  ApiKeyCreated,
  AuditPage,
  Heartbeat,
  HeartbeatCreated,
  InviteOut,
  MaintenanceWindow,
  MonitorSummary,
  OutboundWebhook,
  TeamDetail,
  TelegramChannel,
  TelegramConnect,
  TelegramConnectStatus,
  UserOut,
} from "../types";

interface PendingConnect extends TelegramConnect {
  expiresAt: number;
}

function formatCountdown(ms: number): string {
  const s = Math.max(0, Math.ceil(ms / 1000));
  const m = Math.floor(s / 60);
  const rest = s % 60;
  return `${m}:${String(rest).padStart(2, "0")}`;
}

export default function Settings() {
  const toast = useToast();
  const qc = useQueryClient();
  const [chatId, setChatId] = useState("");
  const [label, setLabel] = useState("");
  const [connectLabel, setConnectLabel] = useState("");
  const [pending, setPending] = useState<PendingConnect | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [justConnected, setJustConnected] = useState<string | null>(null);
  const [maintForm, setMaintForm] = useState({ monitor_id: "", starts_at: "", ends_at: "", reason: "" });

  const channels = useQuery({
    queryKey: ["channels"],
    queryFn: () => unwrap<TelegramChannel[]>(api.get("/notification-channels")),
  });
  const maintenance = useQuery({
    queryKey: ["maintenance"],
    queryFn: () => unwrap<MaintenanceWindow[]>(api.get("/maintenance")),
  });
  const monitors = useQuery({
    queryKey: ["monitors"],
    queryFn: () => unwrap<MonitorSummary[]>(api.get("/monitors")),
  });

  // Countdown ticker while waiting for Telegram Start
  useEffect(() => {
    if (!pending) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [pending]);

  const connectMutation = useMutation({
    mutationFn: () =>
      unwrap<TelegramConnect>(
        api.post("/notification-channels/connect", { label: connectLabel || null }),
      ),
    onSuccess: (data) => {
      setPending({ ...data, expiresAt: Date.now() + data.expires_in_sec * 1000 });
      setJustConnected(null);
      if (data.deep_link) {
        window.open(data.deep_link, "_blank", "noopener,noreferrer");
      }
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const connectStatus = useQuery({
    queryKey: ["connect-status", pending?.token],
    queryFn: () =>
      unwrap<TelegramConnectStatus>(api.get(`/notification-channels/connect/${pending!.token}/status`)),
    enabled: !!pending,
    refetchInterval: 3000,
    retry: false,
  });

  useEffect(() => {
    const s = connectStatus.data;
    if (!s || !pending) return;
    if (s.status === "connected" && s.channel) {
      setJustConnected(s.channel.telegram_chat_id);
      setPending(null);
      toast("Telegram connected ✅ — no chat ID needed");
      qc.invalidateQueries({ queryKey: ["channels"] });
    } else if (s.status === "expired") {
      setPending(null);
      toast("Connect link expired — tap Connect again", "err");
    }
  }, [connectStatus.data, pending, qc, toast]);

  const cancelConnect = useMutation({
    mutationFn: () => unwrap(api.delete(`/notification-channels/connect/${pending!.token}`)),
    onSuccess: () => {
      setPending(null);
      toast("Connect cancelled");
    },
    onError: () => setPending(null),
  });

  const addChannel = useMutation({
    mutationFn: () => unwrap(api.post("/notification-channels", { telegram_chat_id: chatId.trim(), label: label || null })),
    onSuccess: () => {
      setChatId("");
      setLabel("");
      toast("Telegram channel added");
      qc.invalidateQueries({ queryKey: ["channels"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const deleteChannel = useMutation({
    mutationFn: (c: TelegramChannel) => unwrap(api.delete(`/notification-channels/${c.id}`)),
    onSuccess: () => {
      toast("Channel removed");
      qc.invalidateQueries({ queryKey: ["channels"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const testChannel = useMutation({
    mutationFn: (c: TelegramChannel) => unwrap(api.post(`/notification-channels/${c.id}/test`)),
    onSuccess: () => toast("Test sent — check Telegram"),
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const addMaint = useMutation({
    mutationFn: () =>
      unwrap(
        api.post("/maintenance", {
          monitor_id: maintForm.monitor_id || null,
          starts_at: new Date(maintForm.starts_at).toISOString(),
          ends_at: new Date(maintForm.ends_at).toISOString(),
          reason: maintForm.reason || null,
        }),
      ),
    onSuccess: () => {
      setMaintForm({ monitor_id: "", starts_at: "", ends_at: "", reason: "" });
      toast("Maintenance window created — alerts muted in that window");
      qc.invalidateQueries({ queryKey: ["maintenance"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const deleteMaint = useMutation({
    mutationFn: (w: MaintenanceWindow) => unwrap(api.delete(`/maintenance/${w.id}`)),
    onSuccess: () => {
      toast("Window removed");
      qc.invalidateQueries({ queryKey: ["maintenance"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  // Heartbeats (Phase 5 — reverse monitors)
  const [hbForm, setHbForm] = useState({ name: "", period_min: 5, grace_min: 2 });
  const [revealedKey, setRevealedKey] = useState<string | null>(null);

  const heartbeats = useQuery({
    queryKey: ["heartbeats"],
    queryFn: () => unwrap<Heartbeat[]>(api.get("/heartbeats")),
  });

  const addHeartbeat = useMutation({
    mutationFn: () =>
      unwrap<HeartbeatCreated>(
        api.post("/heartbeats", {
          name: hbForm.name,
          period_min: Number(hbForm.period_min),
          grace_min: Number(hbForm.grace_min),
        }),
      ),
    onSuccess: (hb) => {
      setHbForm({ name: "", period_min: 5, grace_min: 2 });
      setRevealedKey(hb.ping_key);
      toast("Heartbeat created — copy the ping URL now (shown once)");
      qc.invalidateQueries({ queryKey: ["heartbeats"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const deleteHeartbeat = useMutation({
    mutationFn: (h: Heartbeat) => unwrap(api.delete(`/heartbeats/${h.id}`)),
    onSuccess: () => {
      toast("Heartbeat removed");
      qc.invalidateQueries({ queryKey: ["heartbeats"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  // Backend base that follows the environment: :8000 in local dev (Vite runs on
  // :5173), VITE_API_URL in production (Northflank). So the ping command below
  // keeps working after deploy with zero edits.
  function backendBase(): string {
    if (API_BASE.startsWith("http")) return API_BASE.replace(/\/api\/v1\/?$/, "");
    if (window.location.port === "5173") {
      return `${window.location.protocol}//${window.location.hostname}:8000`;
    }
    return window.location.origin;
  }

  function pingUrl(key: string): string {
    return `${backendBase()}/api/v1/heartbeats/${key}/ping`;
  }

  function pingCommand(key: string): string {
    return `curl.exe -X POST "${pingUrl(key)}"`;
  }

  // API keys (Phase 7 — machine credentials, raw value shown once)
  const [keyName, setKeyName] = useState("");
  const [revealedApiKey, setRevealedApiKey] = useState<ApiKeyCreated | null>(null);

  const apiKeys = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => unwrap<ApiKey[]>(api.get("/api-keys")),
  });

  const createApiKey = useMutation({
    mutationFn: () => unwrap<ApiKeyCreated>(api.post("/api-keys", { name: keyName })),
    onSuccess: (k) => {
      setKeyName("");
      setRevealedApiKey(k);
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const revokeApiKey = useMutation({
    mutationFn: (k: ApiKey) => unwrap(api.delete(`/api-keys/${k.id}`)),
    onSuccess: () => {
      toast("API key revoked — calls with it now fail");
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  // Outbound webhooks (Phase 7 — signed incident POSTs to your URL)
  const [whForm, setWhForm] = useState({ url: "", secret: "" });
  const [revealedWhSecret, setRevealedWhSecret] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<Record<string, string>>({});

  const webhooks = useQuery({
    queryKey: ["webhooks"],
    queryFn: () => unwrap<OutboundWebhook[]>(api.get("/webhooks/outbound")),
  });

  const createWebhook = useMutation({
    mutationFn: () =>
      unwrap<{ id: string; secret: string }>(
        api.post("/webhooks/outbound", {
          url: whForm.url,
          secret: whForm.secret || null,
        }),
      ),
    onSuccess: (w) => {
      setWhForm({ url: "", secret: "" });
      if (w.secret !== "••••••••") setRevealedWhSecret(w.secret);
      else toast("Webhook added");
      qc.invalidateQueries({ queryKey: ["webhooks"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const testWebhook = useMutation({
    mutationFn: (w: OutboundWebhook) =>
      unwrap<{ ok: boolean; status_code: number | null; error: string | null }>(
        api.post(`/webhooks/outbound/${w.id}/test`),
      ),
    onSuccess: (res, w) => {
      setTestResult((m) => ({
        ...m,
        [w.id]: res.ok ? `Delivered (HTTP ${res.status_code})` : `Failed: ${res.error}`,
      }));
      toast(res.ok ? "Test delivered ✅" : `Test failed: ${res.error}`, res.ok ? "ok" : "err");
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const deleteWebhook = useMutation({
    mutationFn: (w: OutboundWebhook) => unwrap(api.delete(`/webhooks/outbound/${w.id}`)),
    onSuccess: () => {
      toast("Webhook removed");
      qc.invalidateQueries({ queryKey: ["webhooks"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  // Audit trail (Phase 7 — Owner reader)
  const [auditAction, setAuditAction] = useState("");
  const [auditPage, setAuditPage] = useState(1);

  const audit = useQuery({
    queryKey: ["audit", auditAction, auditPage],
    queryFn: () =>
      unwrap<AuditPage>(
        api.get("/audit-logs", {
          params: {
            ...(auditAction ? { action: auditAction } : {}),
            page: auditPage,
            limit: 20,
          },
        }),
      ),
  });

  // Team & members (owner invites, everyone sees the list)
  const [inviteForm, setInviteForm] = useState({ email: "", role: "member" });
  const [revealedInvite, setRevealedInvite] = useState<InviteOut | null>(null);

  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => unwrap<{ user: UserOut }>(api.get("/auth/me")),
    staleTime: 60_000,
  });

  const team = useQuery({
    queryKey: ["team"],
    queryFn: () => unwrap<TeamDetail>(api.get("/teams/me")),
    staleTime: 60_000,
  });

  const members = useQuery({
    queryKey: ["members"],
    queryFn: () => unwrap<UserOut[]>(api.get("/teams/members")),
  });

  const isOwner = me.data?.user.role === "owner";

  const inviteMember = useMutation({
    mutationFn: () =>
      unwrap<InviteOut>(
        api.post("/teams/invite", { email: inviteForm.email, role: inviteForm.role }),
      ),
    onSuccess: (inv) => {
      setInviteForm({ email: "", role: "member" });
      setRevealedInvite(inv);
      qc.invalidateQueries({ queryKey: ["members"] });
      qc.invalidateQueries({ queryKey: ["team"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const removeMember = useMutation({
    mutationFn: (m: UserOut) => unwrap(api.delete(`/teams/members/${m.id}`)),
    onSuccess: () => {
      toast("Member removed — their login stops working instantly");
      qc.invalidateQueries({ queryKey: ["members"] });
      qc.invalidateQueries({ queryKey: ["team"] });
    },
    onError: (e) => toast(errorMessage(e), "err"),
  });

  const connectedCount = (channels.data ?? []).length;
  const remaining = pending ? pending.expiresAt - now : 0;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <Link to="/" className="text-sm font-medium text-slate-600 hover:text-slate-900">
            ← Back to Dashboard
          </Link>
          <div className="flex items-center gap-2">
            <div className="hidden sm:block text-sm text-slate-500">Telegram auto-connect • escalation 10 min</div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 py-8 space-y-8">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">Settings</h1>
          <p className="text-sm text-slate-500">Connect Telegram in one tap. No chat ID copy-paste. All alerts go to Telegram.</p>
        </div>

        {/* Team */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-sm font-semibold tracking-wide text-slate-900">Team</h2>
              <p className="text-sm text-slate-500">
                {team.data ? (
                  <>
                    {team.data.name} • {team.data.plan} plan • {(members.data ?? []).length} member{(members.data ?? []).length === 1 ? "" : "s"}
                  </>
                ) : (
                  "Who shares this dashboard."
                )}
              </p>
            </div>
            {isOwner && (
              <span className="hidden sm:inline-flex rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-200">
                You are owner
              </span>
            )}
          </div>

          {isOwner && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (inviteForm.email.trim()) inviteMember.mutate();
              }}
              className="grid gap-3 sm:grid-cols-[1fr_140px_auto]"
            >
              <label className="block">
                <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">EMAIL</span>
                <input
                  required
                  type="email"
                  value={inviteForm.email}
                  onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                  placeholder="teammate@mail.com"
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">ROLE</span>
                <select
                  value={inviteForm.role}
                  onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value })}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm"
                >
                  <option value="member">member</option>
                  <option value="viewer">viewer</option>
                </select>
              </label>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={inviteMember.isPending}
                  className="w-full rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-500/20 hover:bg-indigo-700 disabled:opacity-50 sm:w-auto"
                >
                  {inviteMember.isPending ? "Inviting…" : "Invite"}
                </button>
              </div>
            </form>
          )}

          <div className="mt-4">
            {members.isLoading ? (
              <p className="text-sm text-slate-400">Loading members…</p>
            ) : (
              <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
                {(members.data ?? []).map((m) => (
                  <div key={m.id} className="flex items-center justify-between gap-3 bg-white px-4 py-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {m.name}{" "}
                        <span className="font-normal text-slate-500">• {m.role}</span>
                        {me.data?.user.id === m.id && (
                          <span className="ml-1.5 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
                            you
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-slate-400">{m.email}</p>
                    </div>
                    {isOwner && me.data?.user.id !== m.id && (
                      <button
                        onClick={() => {
                          if (confirm(`Remove ${m.email}? Their login stops working instantly.`)) removeMember.mutate(m);
                        }}
                        className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Telegram auto-connect */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-sm font-semibold tracking-wide text-slate-900">Telegram alerts</h2>
              <p className="text-sm text-slate-500">
                Tap Connect → open the bot → press Start. We link it automatically.
              </p>
            </div>
            <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
                <span className={`h-1.5 w-1.5 rounded-full ${connectedCount > 0 ? "bg-emerald-500" : "bg-slate-300"}`} />
                {connectedCount > 0 ? `${connectedCount} connected` : "Not connected"}
              </span>
          </div>

          {/* 3 steps */}
          <div className="mb-5 grid gap-2 sm:grid-cols-3">
            {[
              { n: "1", title: "Connect", desc: "Tap the button below" },
              { n: "2", title: "Start bot", desc: "Press Start in Telegram" },
              { n: "3", title: "Done ✅", desc: "Channel appears here" },
            ].map((s) => (
              <div key={s.n} className="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2.5">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                  {s.n}
                </span>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{s.title}</p>
                  <p className="text-xs text-slate-500">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {justConnected && (
            <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
              Telegram connected ✅ — chat <span className="font-mono">{justConnected}</span> will now get DOWN / RECOVERED alerts.
            </div>
          )}

          {!pending ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                connectMutation.mutate();
              }}
              className="grid gap-3 sm:grid-cols-[1fr_auto]"
            >
              <label className="block">
                <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">LABEL (optional)</span>
                <input
                  value={connectLabel}
                  onChange={(e) => setConnectLabel(e.target.value)}
                  placeholder="My DM, Ops channel"
                  className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
                />
              </label>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={connectMutation.isPending}
                  className="w-full rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-500/20 hover:bg-indigo-700 disabled:opacity-50 sm:w-auto"
                >
                  {connectMutation.isPending ? "Creating link…" : "ⓣ Connect Telegram"}
                </button>
              </div>
            </form>
          ) : (
            <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4">
              <div className="flex items-center gap-3">
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-300 border-t-indigo-600" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-slate-900">Waiting for you to press Start in Telegram…</p>
                  <p className="text-xs text-slate-500">
                    Link expires in {formatCountdown(remaining)} • This page auto-refreshes — keep it open.
                  </p>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {pending.deep_link ? (
                  <a
                    href={pending.deep_link}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
                  >
                    Open Telegram bot again
                  </a>
                ) : (
                  <span className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-700 ring-1 ring-amber-200">
                    Bot username not configured on server — ask admin to set TELEGRAM_BOT_USERNAME.
                  </span>
                )}
                {pending.deep_link && (
                  <button
                    type="button"
                    onClick={() => {
                      void navigator.clipboard?.writeText(pending.deep_link!);
                      toast("Bot link copied");
                    }}
                    className="rounded-xl border border-indigo-200 bg-white px-4 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-50"
                  >
                    Copy link
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => cancelConnect.mutate()}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div className="mt-6">
            {channels.isLoading ? (
              <p className="text-sm text-slate-400">Loading channels…</p>
            ) : (channels.data ?? []).length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center">
                <p className="text-sm font-medium text-slate-700">No Telegram channel yet</p>
                <p className="text-sm text-slate-500">Tap Connect above, press Start in the bot — you will get a ✅ message.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
                {(channels.data ?? []).map((c) => (
                  <div key={c.id} className="flex items-center justify-between gap-3 bg-white px-4 py-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        <span className="mr-1.5 inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                        {c.label || "Telegram"} <span className="font-normal text-slate-500">• {c.telegram_chat_id}</span>
                      </p>
                      <p className="text-xs text-slate-400">{new Date(c.created_at).toLocaleString()}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => testChannel.mutate(c)}
                        disabled={testChannel.isPending}
                        className="rounded-lg border border-indigo-200 bg-white px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
                      >
                        Test
                      </button>
                      <button
                        onClick={() => {
                          if (confirm("Remove this Telegram channel?")) deleteChannel.mutate(c);
                        }}
                        className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Advanced manual fallback (groups / supergroups) */}
          <details className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm">
            <summary className="cursor-pointer font-medium text-slate-600 hover:text-slate-900">
              Advanced: add a group / supergroup manually by chat ID
            </summary>
            <p className="mt-2 text-xs text-slate-500">
              Deep-link Start only works for private DMs. For a group: add the bot to the group, send any message,
              then read the group chat ID via <code className="rounded bg-slate-100 px-1">getUpdates</code> and paste it below.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                addChannel.mutate();
              }}
              className="mt-3 grid gap-3 sm:grid-cols-[1fr_1fr_auto]"
            >
              <label className="block">
                <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">TELEGRAM CHAT ID</span>
                <input
                  required
                  value={chatId}
                  onChange={(e) => setChatId(e.target.value)}
                  placeholder="123456789 or -1001234567890"
                  className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">LABEL (optional)</span>
                <input
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  placeholder="Ops group"
                  className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
                />
              </label>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={addChannel.isPending}
                  className="w-full rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-black disabled:opacity-50 sm:w-auto"
                >
                  {addChannel.isPending ? "Adding…" : "Add manually"}
                </button>
              </div>
            </form>
          </details>
        </section>

        {/* Heartbeats */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold tracking-wide text-slate-900">Heartbeats — reverse monitors</h2>
          <p className="text-sm text-slate-500">
            Your cron pings us. Silence past period + grace → Telegram says “Cron dead”. Alerts reuse your
            connected Telegram channels above.
          </p>

          {revealedKey && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm font-semibold text-amber-900">
                Paste this in PowerShell to send one ping now — key shown once:
              </p>
              <code className="mt-1 block overflow-x-auto whitespace-nowrap rounded-lg bg-slate-900 px-3 py-2 text-xs text-emerald-300">
                {pingCommand(revealedKey)}
              </code>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    void navigator.clipboard?.writeText(pingCommand(revealedKey));
                    toast("Ping command copied — paste it in PowerShell");
                  }}
                  className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-black"
                >
                  Copy command
                </button>
                <button
                  type="button"
                  onClick={() => setRevealedKey(null)}
                  className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-100"
                >
                  I saved it
                </button>
              </div>
              <p className="mt-2 text-xs text-amber-700">
                Run it every N minutes (Task Scheduler / cron) to keep this heartbeat ALIVE.
                The URL follows your environment — localhost now, your Northflank URL after deploy.
              </p>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              addHeartbeat.mutate();
            }}
            className="mt-4 grid gap-3 sm:grid-cols-[1fr_120px_120px_auto]"
          >
            <label className="block">
              <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">NAME</span>
              <input
                required
                value={hbForm.name}
                onChange={(e) => setHbForm({ ...hbForm, name: e.target.value })}
                placeholder="nightly-backup"
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">EVERY (min)</span>
              <input
                required
                type="number"
                min={1}
                max={10080}
                value={hbForm.period_min}
                onChange={(e) => setHbForm({ ...hbForm, period_min: Number(e.target.value) })}
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">GRACE (min)</span>
              <input
                required
                type="number"
                min={0}
                max={1440}
                value={hbForm.grace_min}
                onChange={(e) => setHbForm({ ...hbForm, grace_min: Number(e.target.value) })}
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm"
              />
            </label>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={addHeartbeat.isPending}
                className="w-full rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-500/20 hover:bg-indigo-700 disabled:opacity-50 sm:w-auto"
              >
                {addHeartbeat.isPending ? "Creating…" : "Create"}
              </button>
            </div>
          </form>

          <div className="mt-4">
            {heartbeats.isLoading ? (
              <p className="text-sm text-slate-400">Loading heartbeats…</p>
            ) : (heartbeats.data ?? []).length === 0 ? (
              <p className="text-sm text-slate-400">No heartbeats yet. Create one for your next cron job.</p>
            ) : (
              <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
                {(heartbeats.data ?? []).map((h) => (
                  <div key={h.id} className="flex items-center justify-between gap-3 bg-white px-4 py-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        <span
                          className={`mr-1.5 inline-flex h-2 w-2 rounded-full ${h.status === "ALIVE" ? "bg-emerald-500" : "bg-red-500 animate-pulse"}`}
                        />
                        {h.name}{" "}
                        <span className="font-normal text-slate-500">
                          • every {h.period_min}m + {h.grace_min}m grace • {h.status}
                        </span>
                      </p>
                      <p className="text-xs text-slate-400">
                        {h.last_ping_at ? `last ping ${new Date(h.last_ping_at).toLocaleString()}` : "never pinged"}
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        if (confirm("Delete this heartbeat? The ping URL stops working.")) deleteHeartbeat.mutate(h);
                      }}
                      className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* API keys */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold tracking-wide text-slate-900">API keys — for scripts & CI</h2>
          <p className="text-sm text-slate-500">
            Works anywhere your password does: <code className="rounded bg-slate-100 px-1">Authorization: Bearer pk_live_…</code>.
            The raw key is shown once — we store only its fingerprint.
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (keyName.trim()) createApiKey.mutate();
            }}
            className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto]"
          >
            <label className="block">
              <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">KEY NAME</span>
              <input
                required
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                placeholder="CI deploy, cron script"
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
              />
            </label>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={createApiKey.isPending}
                className="w-full rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-500/20 hover:bg-indigo-700 disabled:opacity-50 sm:w-auto"
              >
                {createApiKey.isPending ? "Creating…" : "Create key"}
              </button>
            </div>
          </form>

          <div className="mt-4">
            {apiKeys.isLoading ? (
              <p className="text-sm text-slate-400">Loading keys…</p>
            ) : (apiKeys.data ?? []).length === 0 ? (
              <p className="text-sm text-slate-400">No keys yet. Create one for your first script.</p>
            ) : (
              <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
                {(apiKeys.data ?? []).map((k) => (
                  <div key={k.id} className="flex items-center justify-between gap-3 bg-white px-4 py-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {k.name} <span className="font-mono font-normal text-slate-500">• {k.prefix}…</span>
                      </p>
                      <p className="text-xs text-slate-400">{new Date(k.created_at).toLocaleString()}</p>
                    </div>
                    <button
                      onClick={() => {
                        if (confirm(`Revoke key "${k.name}"? Scripts using it stop working instantly.`)) revokeApiKey.mutate(k);
                      }}
                      className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
                    >
                      Revoke
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Outbound webhooks */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold tracking-wide text-slate-900">Outbound webhooks — push outages to your URL</h2>
          <p className="text-sm text-slate-500">
            Signed JSON on every DOWN + recovery (<code className="rounded bg-slate-100 px-1">X-Signature</code> HMAC).
            Tip: paste a <code className="rounded bg-slate-100 px-1">webhook.site</code> URL to watch it live.
          </p>

          {revealedWhSecret && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm font-semibold text-amber-900">Signing secret — shown once, save it:</p>
              <code className="mt-1 block overflow-x-auto rounded-lg bg-slate-900 px-3 py-2 text-xs text-emerald-300">
                {revealedWhSecret}
              </code>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    void navigator.clipboard?.writeText(revealedWhSecret);
                    toast("Secret copied");
                  }}
                  className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-black"
                >
                  Copy
                </button>
                <button
                  type="button"
                  onClick={() => setRevealedWhSecret(null)}
                  className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-100"
                >
                  I saved it
                </button>
              </div>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault();
              createWebhook.mutate();
            }}
            className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto]"
          >
            <label className="block">
              <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">URL</span>
              <input
                required
                value={whForm.url}
                onChange={(e) => setWhForm({ ...whForm, url: e.target.value })}
                placeholder="https://…"
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">SECRET (blank = auto)</span>
              <input
                value={whForm.secret}
                onChange={(e) => setWhForm({ ...whForm, secret: e.target.value })}
                placeholder="whsec_…"
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
              />
            </label>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={createWebhook.isPending}
                className="w-full rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-500/20 hover:bg-indigo-700 disabled:opacity-50 sm:w-auto"
              >
                {createWebhook.isPending ? "Adding…" : "Add webhook"}
              </button>
            </div>
          </form>

          <div className="mt-4">
            {webhooks.isLoading ? (
              <p className="text-sm text-slate-400">Loading webhooks…</p>
            ) : (webhooks.data ?? []).length === 0 ? (
              <p className="text-sm text-slate-400">No webhooks yet.</p>
            ) : (
              <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
                {(webhooks.data ?? []).map((w) => (
                  <div key={w.id} className="flex items-center justify-between gap-3 bg-white px-4 py-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">{w.url}</p>
                      <p className="text-xs text-slate-400">
                        {new Date(w.created_at).toLocaleString()}
                        {testResult[w.id] ? ` • ${testResult[w.id]}` : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        onClick={() => testWebhook.mutate(w)}
                        disabled={testWebhook.isPending}
                        className="rounded-lg border border-indigo-200 bg-white px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
                      >
                        Test
                      </button>
                      <button
                        onClick={() => {
                          if (confirm("Delete this webhook?")) deleteWebhook.mutate(w);
                        }}
                        className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Maintenance */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold tracking-wide text-slate-900">Maintenance windows</h2>
          <p className="text-sm text-slate-500">Mute alerts while you deploy. Checks still run — only Telegram is muted.</p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              addMaint.mutate();
            }}
            className="mt-4 grid gap-3 sm:grid-cols-2"
          >
            <label className="block">
              <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">MONITOR (empty = whole team)</span>
              <select
                value={maintForm.monitor_id}
                onChange={(e) => setMaintForm({ ...maintForm, monitor_id: e.target.value })}
                className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm"
              >
                <option value="">All monitors</option>
                {(monitors.data ?? []).map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">REASON</span>
              <input
                value={maintForm.reason}
                onChange={(e) => setMaintForm({ ...maintForm, reason: e.target.value })}
                placeholder="Deploying v2.1"
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">STARTS AT</span>
              <input
                required
                type="datetime-local"
                value={maintForm.starts_at}
                onChange={(e) => setMaintForm({ ...maintForm, starts_at: e.target.value })}
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-semibold tracking-wide text-slate-600">ENDS AT</span>
              <input
                required
                type="datetime-local"
                value={maintForm.ends_at}
                onChange={(e) => setMaintForm({ ...maintForm, ends_at: e.target.value })}
                className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm"
              />
            </label>
            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={addMaint.isPending}
                className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-black disabled:opacity-50"
              >
                {addMaint.isPending ? "Creating…" : "Create window"}
              </button>
            </div>
          </form>

          <div className="mt-6">
            {(maintenance.data ?? []).length === 0 ? (
              <p className="text-sm text-slate-400">No windows. Create one for your next deploy.</p>
            ) : (
              <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
                {(maintenance.data ?? []).map((w) => (
                  <div key={w.id} className="flex items-center justify-between gap-3 bg-white px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-slate-900">
                        {w.reason || "Maintenance"} <span className="font-normal text-slate-500">• {w.monitor_id ? "one monitor" : "whole team"}</span>
                      </p>
                      <p className="text-xs text-slate-500">
                        {new Date(w.starts_at).toLocaleString()} → {new Date(w.ends_at).toLocaleString()}
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        if (confirm("Cancel this window?")) deleteMaint.mutate(w);
                      }}
                      className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Audit trail */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold tracking-wide text-slate-900">Audit trail — who did what</h2>
          <p className="text-sm text-slate-500">Owner-only. Every write in the app lands here, newest first.</p>

          <div className="mt-4 flex gap-2">
            <input
              value={auditAction}
              onChange={(e) => {
                setAuditAction(e.target.value);
                setAuditPage(1);
              }}
              placeholder="Filter by action, e.g. monitor.deleted"
              className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10"
            />
            {(audit.data?.total ?? 0) > 20 && (
              <div className="flex shrink-0 items-center gap-1">
                <button
                  disabled={auditPage <= 1}
                  onClick={() => setAuditPage((p) => p - 1)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium hover:bg-slate-50 disabled:opacity-40"
                >
                  ←
                </button>
                <span className="px-1 text-xs text-slate-500">{auditPage}</span>
                <button
                  disabled={(audit.data?.items ?? []).length < 20}
                  onClick={() => setAuditPage((p) => p + 1)}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium hover:bg-slate-50 disabled:opacity-40"
                >
                  →
                </button>
              </div>
            )}
          </div>

          <div className="mt-4">
            {audit.isLoading ? (
              <p className="text-sm text-slate-400">Loading audit…</p>
            ) : audit.isError ? (
              <p className="text-sm text-slate-400">Audit is owner-only.</p>
            ) : (audit.data?.items ?? []).length === 0 ? (
              <p className="text-sm text-slate-400">Nothing logged yet.</p>
            ) : (
              <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
                {(audit.data?.items ?? []).map((a) => (
                  <div key={a.id} className="bg-white px-4 py-2.5">
                    <p className="text-sm font-medium text-slate-900">
                      <span className="font-mono text-xs text-indigo-700">{a.action}</span>{" "}
                      <span className="font-normal text-slate-500">
                        {a.target_type ? `• ${a.target_type}` : ""}
                      </span>
                    </p>
                    <p className="text-xs text-slate-400">
                      {new Date(a.created_at).toLocaleString()}
                      {a.ip ? ` • ${a.ip}` : ""}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Show-once invite login modal */}
        {revealedInvite && (
          <div className="fixed inset-0 z-30 flex items-center justify-center p-4">
            <button aria-label="close" onClick={() => setRevealedInvite(null)} className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" />
            <div className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
              <h3 className="text-sm font-bold text-slate-900">
                {revealedInvite.user.email} added ✅
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                Send them this login (shown once — the password is stored hashed and can never be revealed again).
              </p>
              <code className="mt-3 block overflow-x-auto whitespace-nowrap rounded-lg bg-slate-900 px-3 py-2.5 text-xs text-emerald-300">
                {revealedInvite.user.email} / {revealedInvite.temp_password}
              </code>
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => {
                    void navigator.clipboard?.writeText(`${revealedInvite.user.email} / ${revealedInvite.temp_password}`);
                    toast("Login copied — send it to them");
                  }}
                  className="flex-1 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
                >
                  Copy login
                </button>
                <button
                  onClick={() => setRevealedInvite(null)}
                  className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Show-once API key modal */}
        {revealedApiKey && (
          <div className="fixed inset-0 z-30 flex items-center justify-center p-4">
            <button aria-label="close" onClick={() => setRevealedApiKey(null)} className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" />
            <div className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
              <h3 className="text-sm font-bold text-slate-900">Key created — copy it now</h3>
              <p className="mt-1 text-xs text-slate-500">
                Shown once. We store only the fingerprint — this can never be revealed again.
              </p>
              <code className="mt-3 block overflow-x-auto whitespace-nowrap rounded-lg bg-slate-900 px-3 py-2.5 text-xs text-emerald-300">
                {revealedApiKey.key}
              </code>
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => {
                    void navigator.clipboard?.writeText(revealedApiKey.key);
                    toast("Key copied — store it somewhere safe");
                  }}
                  className="flex-1 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
                >
                  Copy key
                </button>
                <button
                  onClick={() => setRevealedApiKey(null)}
                  className="flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  I saved it
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
