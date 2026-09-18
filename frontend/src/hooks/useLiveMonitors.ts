import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { tokens } from "../lib/api";
import type { LiveCheckEvent, MonitorSummary } from "../types";

function wsUrl(): string | null {
  const access = tokens.access;
  if (!access) return null;
  // In dev the page is on :5173 with no WS proxy — talk straight to :8000.
  // In prod VITE_API_URL is the absolute backend URL.
  const apiUrl = import.meta.env.VITE_API_URL as string | undefined;
  let base: string;
  if (apiUrl && apiUrl.startsWith("http")) {
    base = apiUrl.replace(/\/api\/v1\/?$/, "");
  } else if (window.location.port === "5173") {
    base = `${window.location.protocol}//${window.location.hostname}:8000`;
  } else {
    base = window.location.origin;
  }
  const wsBase = base.replace(/^http/, "ws");
  return `${wsBase}/ws/monitors?token=${encodeURIComponent(access)}`;
}

/** Live WS subscription: patches the ["monitors"] cache on each check event. */
export function useLiveMonitors() {
  const qc = useQueryClient();
  const [live, setLive] = useState(false);
  const retry = useRef(0);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    let timer: number | undefined;

    const connect = () => {
      const url = wsUrl();
      if (!url) return;
      try {
        ws = new WebSocket(url);
      } catch {
        schedule();
        return;
      }
      ws.onopen = () => {
        retry.current = 0;
        setLive(true);
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data) as LiveCheckEvent & { type: string };
          if (msg.type !== "check" || !msg.monitor_id) return;
          qc.setQueryData<MonitorSummary[]>(["monitors"], (old) => {
            if (!old) return old;
            return old.map((m) =>
              m.id === msg.monitor_id
                ? {
                    ...m,
                    current_status: m.is_paused ? m.current_status : msg.status,
                    last_latency_ms: msg.latency_ms ?? m.last_latency_ms,
                    last_checked_at: msg.checked_at ?? m.last_checked_at,
                  }
                : m,
            );
          });
        } catch {
          // ignore malformed frames
        }
      };
      ws.onclose = () => {
        setLive(false);
        schedule();
      };
      ws.onerror = () => {
        try {
          ws?.close();
        } catch {
          // ignore
        }
      };
    };

    const schedule = () => {
      if (closed) return;
      const backoff = Math.min(1000 * 2 ** retry.current, 15000);
      retry.current += 1;
      timer = window.setTimeout(connect, backoff);
    };

    connect();
    // Keep-alive ping so proxies don't kill idle sockets.
    const keep = window.setInterval(() => {
      try {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send("ping");
      } catch {
        // ignore
      }
    }, 25000);

    return () => {
      closed = true;
      window.clearTimeout(timer);
      window.clearInterval(keep);
      try {
        ws?.close();
      } catch {
        // ignore
      }
    };
  }, [qc]);

  return live;
}
