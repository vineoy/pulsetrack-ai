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
