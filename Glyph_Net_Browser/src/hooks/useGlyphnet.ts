// frontend/src/hooks/useGlyphnet.ts
import { useEffect, useMemo, useRef, useState } from "react";

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

/**
 * Build the correct WS/WSS URL for GlyphNet in Codespaces, local dev, or same-origin.
 */
function glyphnetWsURL(topic: string, graph?: GraphKey, token?: string) {
  const host = location.host;
  const encTopic = encodeURIComponent(topic);
  const kgParam = graph ? `&kg=${encodeURIComponent(graph)}` : "";
  const t = (token ?? localStorage.getItem("gnet:token") ?? "dev-token").trim();

  const scheme = location.protocol === "https:" ? "wss" : "ws";

  // Codespaces: page https://<id>-5173.app.github.dev → backend https://<id>-8080.app.github.dev
  if (host.endsWith(".app.github.dev")) {
    return `wss://${host.replace("-5173", "-8080")}/ws/glyphnet?token=${t}&topic=${encTopic}${kgParam}`;
  }

  // Local dev: Vite on 5173, backend on 8080
  if (host.endsWith(":5173")) {
    return `${scheme}://${host.replace(":5173", ":8080")}/ws/glyphnet?token=${t}&topic=${encTopic}${kgParam}`;
  }

  // Same-origin
  return `${scheme}://${host}/ws/glyphnet?token=${t}&topic=${encTopic}${kgParam}`;
}

/** Jittered backoff step */
function stepBackoffMs(current: number) {
  const base = Math.min(Math.floor(current * 1.8), 15_000); // cap at 15s
  const jitter = Math.floor(base * 0.2); // ±20%
  return base - jitter + Math.floor(Math.random() * (2 * jitter + 1));
}

export default function useGlyphnet(topic: string, graph?: GraphKey) {
  const urlBuilder = useMemo(() => (t: string, g?: GraphKey) => glyphnetWsURL(t, g), []);

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

      const wsUrl = urlBuilder(topic, graph);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        // connected
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
  }, [topic, graph, urlBuilder]);

  return { connected, messages, error, reconnecting, reconnectIn };
}