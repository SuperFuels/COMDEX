// frontend/src/hooks/useGlyphnet.ts
import { useEffect, useMemo, useRef, useState } from "react";
import { resolveApiBase } from "@/utils/base";
import { glyphnetWsUrl } from "@/utils/transport";   // policy-aware WS URL

export type GraphKey = "personal" | "work";

export interface GlyphnetEvent {
  type: string;
  capsule?: any;
  meta?: any;

  // lock fields (when type === "entanglement_lock")
  resource?: string;
  resourceTopic?: string;
  owner?: string;
  state?: "held" | "free";
  granted?: boolean;
  until?: number;

  [k: string]: any;
}

/** Jittered backoff step */
function stepBackoffMs(current: number) {
  const base = Math.min(Math.floor(current * 1.8), 15_000); // cap at 15s
  const jitter = Math.floor(base * 0.2); // ±20%
  return base - jitter + Math.floor(Math.random() * (2 * jitter + 1));
}

export default function useGlyphnet(topic: string, graph?: GraphKey) {
  // Resolve once, then derive WS URLs via transport policy
  const ipBase = useMemo(() => resolveApiBase(), []);
  const wsUrlFor = useMemo(
    () => (t: string, g?: GraphKey) =>
      glyphnetWsUrl(ipBase, t, (g || "personal").toLowerCase()),
    [ipBase]
  );

  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<number | null>(null);
  const backoffRef = useRef(800); // start ~0.8s

  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<GlyphnetEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [reconnecting, setReconnecting] = useState(false);
  const [reconnectIn, setReconnectIn] = useState<number | null>(null);

  useEffect(() => {
    if (!topic) return;

    let dead = false; // guards cleanup vs. onclose

    const open = () => {
      // reset UI flags on (re)open attempt
      setReconnecting(false);
      setReconnectIn(null);

      const wsUrl = wsUrlFor(topic, graph);  // ⬅️ policy-aware WS URL
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
        // reset backoff after any successful connect
        backoffRef.current = 800;
      };

      ws.onmessage = (e) => {
        try {
          const raw: any = JSON.parse(e.data);

          // If events carry a graph tag, drop mismatches
          const evGraph =
            raw?.meta?.graph ??
            raw?.graph ??
            raw?.envelope?.meta?.graph ??
            raw?.envelope?.graph;
          if (graph && evGraph && evGraph !== graph) return;

          // ── Normalize shape (matches your ChatThread expectations) ─────────
          const env = raw?.envelope ?? null;

          let baseType: string | undefined =
            raw?.type ||
            raw?.event ||
            env?.type ||
            (env?.capsule?.voice_frame
              ? "glyphnet_voice_frame"
              : env?.capsule
              ? "glyphnet_capsule"
              : undefined);

          // Detect lock frames in multiple shapes
          const isLock =
            baseType === "entanglement_lock" ||
            raw?.type === "entanglement_lock" ||
            raw?.event === "entanglement_lock" ||
            baseType === "entanglement_lock_acquired" ||
            baseType === "entanglement_lock_released" ||
            !!raw?.entanglement_lock;

          let ev: GlyphnetEvent;

          if (isLock) {
            const lock = raw?.entanglement_lock || env || raw;
            const state =
              lock?.state ??
              (baseType === "entanglement_lock_released" ? "free" : "held");

            ev = {
              ...raw,
              type: "entanglement_lock",
              resource: lock?.resource,
              owner: lock?.owner,
              state,
              granted:
                lock?.granted ??
                (baseType === "entanglement_lock_acquired"
                  ? true
                  : baseType === "entanglement_lock_released"
                  ? true
                  : undefined),
              until: lock?.until,
              resourceTopic:
                typeof lock?.resource === "string"
                  ? String(lock.resource).replace(/^voice:/, "")
                  : undefined,
            };
          } else {
            const capsule = raw?.capsule ?? env?.capsule ?? undefined;
            const meta = raw?.meta ?? env?.meta ?? undefined;

            // Ensure type tracks voice frames explicitly when present
            let t = baseType || "glyphnet_capsule";
            if (capsule?.voice_frame && t !== "glyphnet_voice_frame") {
              t = "glyphnet_voice_frame";
            }

            ev = { ...raw, type: t, capsule, meta };
          }

          // newest-first; ChatThread re-sorts and dedupes anyway
          setMessages((prev) => [ev, ...prev].slice(0, 500));
        } catch {
          // ignore non-JSON payloads
        }
      };

      ws.onerror = (e) => {
        // surface a simple string error; let onclose handle reconnect
        setError(String((e as any)?.message || "ws error"));
        try {
          ws.close();
        } catch {}
      };

      ws.onclose = () => {
        setConnected(false);
        if (dead) return;

        // enter reconnecting phase
        setReconnecting(true);

        const delay = stepBackoffMs(backoffRef.current);
        backoffRef.current = delay;
        setReconnectIn(delay);

        // Optional: small countdown for the UI using rAF
        const start = Date.now();
        const tick = () => {
          if (dead) return;
          const left = Math.max(0, delay - (Date.now() - start));
          setReconnectIn(left);
          if (left > 0) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);

        // schedule reconnect
        timerRef.current = window.setTimeout(() => {
          if (!dead) open();
        }, delay);
      };
    };

    open();

    return () => {
      dead = true;
      try {
        wsRef.current?.close();
      } catch {}
      wsRef.current = null;
      if (timerRef.current != null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      setReconnecting(false);
      setReconnectIn(null);
    };
  }, [topic, graph, wsUrlFor]);

  return { connected, messages, error, reconnecting, reconnectIn };
}