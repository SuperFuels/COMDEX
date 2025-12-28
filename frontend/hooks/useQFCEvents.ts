// frontend/hooks/useQFCEvents.ts
import { useEffect, useMemo, useRef, useState } from "react";

type ForkBeamPayload = {
  type?: string;
  wave_id?: string;
  parent_wave_id?: string | null;
  carrier_packet?: unknown;
  scores?: Record<string, number>;
  mutation_cause?: string;
  timestamp?: string | number;
  [k: string]: any;
};

type IndexUpdatePayload = {
  container_id?: string;
  index_name?: string;
  entry?: unknown;
  timestamp?: string | number;
  [k: string]: any;
};

type QFCUpdatePayload = {
  nodes?: any[];
  links?: any[];
  [k: string]: any;
};

type AnyEvent =
  | { tag?: string; payload?: any; data?: any; type?: string; topic?: string }
  | Record<string, any>;

type Options = {
  url?: string;
  topics?: Array<"glyphwave.fork_beam" | "index_update" | "qfc_update">;
  onForkBeam?: (p: ForkBeamPayload) => void;
  onIndexUpdate?: (p: IndexUpdatePayload) => void;
  onQFCUpdate?: (p: QFCUpdatePayload) => void;
  onAny?: (topic: string, payload: unknown) => void;
  maxRetries?: number;
};

type Status = "connecting" | "open" | "closed" | "error";

function wsBaseFromWindow(): string {
  // same-origin default: ws(s)://<host>
  if (typeof window === "undefined") return "ws://localhost";
  return window.location.origin.replace(/^http/i, "ws");
}

function resolveWsEndpoint(url?: string): string {
  // Priority:
  // 1) explicit url option
  // 2) env (vite / next)
  // 3) same-origin "/ws"
  const envUrl =
    (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_WS_URL) ||
    (typeof process !== "undefined" && (process.env as any).NEXT_PUBLIC_WS_URL);

  const raw = url || envUrl || `${wsBaseFromWindow()}/ws`;

  // If they gave http(s), convert to ws(s)
  if (/^https?:\/\//i.test(raw)) return raw.replace(/^http/i, "ws");

  // If already ws(s), keep it
  if (/^wss?:\/\//i.test(raw)) return raw;

  // If relative path like "/ws", join to same-origin ws base
  const base = wsBaseFromWindow();
  const path = raw.startsWith("/") ? raw : `/${raw}`;
  return `${base}${path}`;
}

export function useQFCEvents({
  url,
  topics = ["glyphwave.fork_beam", "index_update", "qfc_update"],
  onForkBeam,
  onIndexUpdate,
  onQFCUpdate,
  onAny,
  maxRetries = 12,
}: Options = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const [status, setStatus] = useState<Status>("connecting");
  const [lastEvent, setLastEvent] = useState<{ topic: string; payload: any } | null>(null);

  const endpoint = useMemo(() => resolveWsEndpoint(url), [url]);

  // stable key for deps
  const topicsKey = useMemo(() => topics.slice().sort().join("|"), [topics]);

  useEffect(() => {
    let cancelled = false;
    let reconnectTimer: number | null = null;

    const scheduleReconnect = () => {
      if (cancelled) return;
      if (retriesRef.current >= maxRetries) return;

      const backoffMs = Math.min(15000, 500 * Math.pow(1.6, retriesRef.current++));
      reconnectTimer = window.setTimeout(connect, backoffMs);
    };

    const connect = () => {
      if (cancelled) return;
      setStatus("connecting");

      // cleanup any previous socket
      try {
        wsRef.current?.close();
      } catch {}
      wsRef.current = null;

      let ws: WebSocket;
      try {
        ws = new WebSocket(endpoint);
      } catch {
        setStatus("error");
        scheduleReconnect();
        return;
      }

      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) return;
        retriesRef.current = 0;
        setStatus("open");
      };

      ws.onmessage = (evt: MessageEvent) => {
        if (cancelled) return;

        let msg: AnyEvent;
        try {
          msg = JSON.parse(evt.data);
        } catch {
          return; // ignore non-JSON frames
        }

        const topic =
          (msg as any).tag ||
          (msg as any).topic ||
          (msg as any).type ||
          "";

        const payload =
          (msg as any).payload ??
          (msg as any).data ??
          // if it's already a structured envelope but no payload/data, pass empty payload
          (("tag" in (msg as any) || "topic" in (msg as any) || "type" in (msg as any)) ? {} : msg);

        if (!topics.includes(topic as any)) return;

        setLastEvent({ topic, payload });

        try {
          if (topic === "glyphwave.fork_beam") onForkBeam?.(payload as ForkBeamPayload);
          else if (topic === "index_update") onIndexUpdate?.(payload as IndexUpdatePayload);
          else if (topic === "qfc_update") onQFCUpdate?.(payload as QFCUpdatePayload);

          onAny?.(topic, payload);
        } catch {
          // swallow callback errors so WS loop stays alive
        }
      };

      ws.onerror = () => {
        if (cancelled) return;
        setStatus("error");
      };

      ws.onclose = () => {
        if (cancelled) return;
        setStatus("closed");
        scheduleReconnect();
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      try {
        wsRef.current?.close();
      } catch {}
      wsRef.current = null;
    };
  }, [
    endpoint,
    topicsKey,
    onForkBeam,
    onIndexUpdate,
    onQFCUpdate,
    onAny,
    maxRetries,
  ]);

  return { status, lastEvent };
}