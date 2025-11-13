// frontend/src/hooks/useGlyphnet.ts
import { useEffect, useRef, useState } from "react";
import { resolveApiBase } from "@/utils/base";
import {
  transportBase,
  buildWsUrl,
  onRadioHealth,
  getTransportMode,
} from "@/utils/transport";

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

export default function useGlyphnet(topic: string, graph: GraphKey = "personal") {
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<number | null>(null);
  const backoffRef = useRef(800); // start ~0.8s
  const baseRef = useRef<string>(""); // "", "/radio"
  const rafFlushRef = useRef<number | null>(null);
  const msgBufRef = useRef<GlyphnetEvent[]>([]);

  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<GlyphnetEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [reconnecting, setReconnecting] = useState(false);
  const [reconnectIn, setReconnectIn] = useState<number | null>(null);

  // NEW: track mode changes announced by setTransportMode (same-tab reliable)
  const [modeKey, setModeKey] = useState<string>(getTransportMode());
  useEffect(() => {
    const onMode = (e: any) => setModeKey(String(e.detail || getTransportMode()));
    window.addEventListener("gnet:transport-mode", onMode);
    return () => window.removeEventListener("gnet:transport-mode", onMode);
  }, []);

  // Small buffer → rAF flush to avoid state storms when history arrives quickly
  function enqueue(ev: GlyphnetEvent) {
    msgBufRef.current.push(ev);
    if (rafFlushRef.current != null) return;
    rafFlushRef.current = requestAnimationFrame(() => {
      const chunk = msgBufRef.current;
      msgBufRef.current = [];
      rafFlushRef.current = null;
      if (chunk.length) setMessages((prev) => [...chunk, ...prev].slice(0, 500));
    });
  }

  // compute a fresh base and tell if it changed
  function computeBase(): { base: string; changed: boolean } {
    const next = transportBase(resolveApiBase()); // "" or "/radio"
    const changed = next !== baseRef.current;
    baseRef.current = next;
    return { base: next, changed };
  }

  // Force-reopen WS if the transport base flips (radio health / mode change)
  function forceReopen() {
    try {
      wsRef.current?.close();
    } catch {}
    // onclose handler will schedule the reconnect using the latest baseRef
  }

  useEffect(() => {
    if (!topic) return;

    let dead = false;

    // Track radio health → if base flips in auto mode, force a reopen
    const stopHealth = onRadioHealth(() => {
      if (dead) return;
      const { changed } = computeBase();
      if (changed) forceReopen();
    });

    // React to cross-tab localStorage changes of the mode
    const onStorage = (e: StorageEvent) => {
      if (e.key === "gnet:transportMode") {
        const { changed } = computeBase();
        if (changed) forceReopen();
      }
    };
    window.addEventListener("storage", onStorage);

    // Always compute initial base before opening
    computeBase();

    const open = () => {
      setReconnecting(false);
      setReconnectIn(null);

      const kg = (graph || "personal").toLowerCase();
      const token = (import.meta as any)?.env?.VITE_DEV_WS_TOKEN || "dev-token";
      const qs = new URLSearchParams({ topic, kg, token }).toString();
      const wsUrl = buildWsUrl(baseRef.current, "/ws/glyphnet", qs);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
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

          // Normalize
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

          // Detect lock frames
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

            let t = baseType || "glyphnet_capsule";
            if (capsule?.voice_frame && t !== "glyphnet_voice_frame") {
              t = "glyphnet_voice_frame";
            }

            ev = { ...raw, type: t, capsule, meta };
          }

          enqueue(ev);
        } catch {
          // ignore non-JSON payloads
        }
      };

      ws.onerror = () => {
        setError("ws error");
        try {
          ws.close();
        } catch {}
      };

      ws.onclose = () => {
        setConnected(false);
        if (dead) return;

        // Recompute base before scheduling (health/mode may have flipped)
        computeBase();

        setReconnecting(true);

        const delay = stepBackoffMs(backoffRef.current);
        backoffRef.current = delay;
        setReconnectIn(delay);

        // Optional countdown for UI
        const start = Date.now();
        const tick = () => {
          if (dead) return;
          const left = Math.max(0, delay - (Date.now() - start));
          setReconnectIn(left);
          if (left > 0) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);

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

      if (rafFlushRef.current != null) {
        cancelAnimationFrame(rafFlushRef.current);
        rafFlushRef.current = null;
      }
      msgBufRef.current = [];

      window.removeEventListener("storage", onStorage);
      stopHealth();

      setReconnecting(false);
      setReconnectIn(null);
    };
    // Re-run when topic, graph, **or modeKey** changes
  }, [topic, graph, modeKey]);

  return { connected, messages, error, reconnecting, reconnectIn };
}