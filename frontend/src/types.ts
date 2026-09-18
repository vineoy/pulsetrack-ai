export interface UserOut {
  id: string;
  name: string;
  email: string;
  role: "owner" | "member" | "viewer";
  is_active: boolean;
  created_at: string;
}

export interface TeamOut {
  id: string;
  name: string;
  slug: string;
  plan: string;
  created_at: string;
}

export interface AuthOut {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserOut;
}

export interface MonitorSummary {
  id: string;
  name: string;
  url: string;
  method: string;
  interval_min: number;
  keyword: string | null;
  ssl_check: boolean;
  is_paused: boolean;
  next_check_at: string | null;
  created_at: string;
  current_status: "UP" | "DOWN" | "PAUSED" | "PENDING";
  last_latency_ms: number | null;
  last_checked_at: string | null;
}

export interface CheckOut {
  id: string;
  status: "UP" | "DOWN";
  latency_ms: number | null;
  status_code: number | null;
  error: string | null;
  checked_at: string;
}

export interface StatsOut {
  monitor_id: string;
  days: number;
  total_checks: number;
  up_checks: number;
  down_checks: number;
  uptime_pct: number;
  avg_latency_ms: number | null;
  p50_latency_ms: number | null;
  p95_latency_ms: number | null;
  last_checked_at: string | null;
}

export interface TelegramChannel {
  id: string;
  team_id: string;
  type: string;
  telegram_chat_id: string;
  label: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TelegramConnect {
  token: string;
  deep_link: string | null;
  expires_in_sec: number;
}

export interface TelegramConnectStatus {
  status: "pending" | "connected" | "expired";
  channel: TelegramChannel | null;
}

export interface MaintenanceWindow {
  id: string;
  team_id: string;
  monitor_id: string | null;
  starts_at: string;
  ends_at: string;
  reason: string | null;
  created_at: string;
}

export interface IncidentOut {
  id: string;
  team_id: string;
  monitor_id: string;
  status: "OPEN" | "ACK" | "RESOLVED";
  started_at: string;
  ack_at: string | null;
  resolved_at: string | null;
  downtime_sec: number | null;
  escalated_at: string | null;
  created_at: string;
}

export interface TeamDetail {
  id: string;
  name: string;
  slug: string;
  plan: string;
  created_at: string;
  members_count: number;
}

export interface InviteOut {
  user: UserOut;
  temp_password: string;
}

export interface LiveCheckEvent {
  type: string;
  team_id: string;
  monitor_id: string;
  status: "UP" | "DOWN";
  latency_ms: number | null;
  status_code: number | null;
  checked_at: string;
  incident: string | null;
}

export interface PublicMonitor {
  id: string;
  name: string;
  current_status: "UP" | "DOWN" | "PAUSED" | "PENDING";
  last_latency_ms: number | null;
  last_checked_at: string | null;
}

export interface PublicStatus {
  team_name: string;
  slug: string;
  overall: "operational" | "degraded" | "outage";
  open_incidents: number;
  monitors: PublicMonitor[];
}

export interface PublicIncident {
  id: string;
  monitor_name: string;
  status: string;
  started_at: string;
  resolved_at: string | null;
  downtime_sec: number | null;
}

export interface Heartbeat {
  id: string;
  team_id: string;
  name: string;
  period_min: number;
  grace_min: number;
  last_ping_at: string | null;
  status: "ALIVE" | "MISSING";
  created_at: string;
}

export interface HeartbeatCreated extends Heartbeat {
  ping_key: string;
}

export interface Analysis {
  summary: string | null;
  cached: boolean;
}

export interface AskAnswer {
  answer: string | null;
}

export interface ApiKey {
  id: string;
  team_id: string;
  name: string;
  prefix: string;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKey {
  key: string;
}

export interface OutboundWebhook {
  id: string;
  team_id: string;
  url: string;
  is_active: boolean;
  created_at: string;
}

export interface AuditLog {
  id: string;
  team_id: string | null;
  user_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  detail: Record<string, unknown> | null;
  ip: string | null;
  created_at: string;
}

export interface AuditPage {
  items: AuditLog[];
  total: number;
  page: number;
  limit: number;
}
