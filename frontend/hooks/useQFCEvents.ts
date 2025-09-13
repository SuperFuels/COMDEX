// src/hooks/useQFCEvents.ts
import { useEffect, useMemo, useRef, useState } from "react";

type ForkBeamPayload = {
  type?: string;                 // e.g. "workspace_result_beam"
  wave_id?: string;
  parent_wave_id?: string | null;
  carrier_packet?: unknown;
  scores?: Record<string, number>;
  mutation_cause?: string;
  timestamp?: string | number;
  // allow extra fields
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
  | { tag?: string; payload?: any; data?: any; type?: string }   // common server shapes
  | Record<string, any>;                                         // be permissive

type Options = {
  /** WS endpoint; pass your own or let it pick from envs */
  url?: string;
  /** Which topics to react to */
  topics?: Array<"glyphwave.fork_beam" | "index_update" | "qfc_update">;
  /** Callbacks fired on each topic */
  onForkBeam?: (p: ForkBeamPayload) => void;
  onIndexUpdate?: (p: IndexUpdatePayload) => void;
  onQFCUpdate?: (p: QFCUpdatePayload) => void;
  /** Optional catch-all */
  onAny?: (topic: string, payload: unknown) => void;
  /** Reconnect behavior */
  maxRetries?: number;
};

type Status = "connecting" | "open" | "closed" | "error";

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

  const endpoint = useMemo(() => {
    // Prefer explicit url, then env, then sensible default
    return (
      url ||
      (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_WS_URL) ||
      (typeof process !== "undefined" && (process.env as any).NEXT_PUBLIC_WS_URL) ||
      "ws://localhost:8000/ws"
    );
  }, [url]);

  useEffect(() => {
    let cancelled = false;
    let reconnectTimer: any;

    const connect = () => {
      if (cancelled) return;
      setStatus("connecting");

      try {
        wsRef.current = new WebSocket(endpoint);
      } catch (e) {
        setStatus("error");
        scheduleReconnect();
        return;
      }

      const ws = wsRef.current;

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
          // Some servers send plain strings; skip if not JSON
          return;
        }

        // Normalize: detect topic + payload across common shapes
        const topic =
          (msg as any).tag ||
          (msg as any).topic ||
          (msg as any).type || // some servers put the channel in "type"
          "";

        const payload =
          (msg as any).payload ??
          (msg as any).data ??
          // Some servers just inline fields; if so, pass the whole object
          (("tag" in (msg as any) || "topic" in (msg as any) || "type" in (msg as any)) ? {} : msg);

        if (!topics.includes(topic as any)) return;

        setLastEvent({ topic, payload });

        // Dispatch by topic
        try {
          if (topic === "glyphwave.fork_beam") {
            onForkBeam?.(payload as ForkBeamPayload);
          } else if (topic === "index_update") {
            onIndexUpdate?.(payload as IndexUpdatePayload);
          } else if (topic === "qfc_update") {
            onQFCUpdate?.(payload as QFCUpdatePayload);
          }
          onAny?.(topic, payload);
        } catch {
          /* swallow UI callback errors */
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

    const scheduleReconnect = () => {
      if (retriesRef.current >= maxRetries) return;
      const backoffMs = Math.min(15000, 500 * Math.pow(1.6, retriesRef.current++));
      reconnectTimer = setTimeout(connect, backoffMs);
    };

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      try {
        wsRef.current?.close();
      } catch {}
      wsRef.current = null;
    };
  }, [endpoint, topics.join("|"), onForkBeam, onIndexUpdate, onQFCUpdate, onAny, maxRetries]);

  return { status, lastEvent };
}