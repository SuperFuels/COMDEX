// frontend/src/hooks/useGlyphnet.ts
import { useEffect, useRef, useState } from "react";
import { resolveApiBase } from "@glyphnet/utils/base";
import {
  transportBase,
  buildWsUrl,
  onRadioHealth,
  getTransportMode,
} from "@glyphnet/utils/transport";

// ⬇️ QKD decrypt + lease cache
import { qkdDecrypt } from "../lib/qkd";
import { getLease } from "../lib/qkd_cache";

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

/* ── helpers for decrypt path ────────────────────────────────── */
function u8ToB64(u8: Uint8Array) {
  let s = "";
  for (let i = 0; i < u8.length; i++) s += String.fromCharCode(u8[i]);
  return btoa(s);
}

async function decryptIfNeeded(
  capsule: any,
  kg: string,
  localWA: string,
  remoteWA: string
) {
  // Back-compat: plaintext capsules
  if (!capsule?.enc) return capsule;

  // Choose AAD/purpose based on which field carries ciphertext
  let aad: "glyph" | "voice_note" | "voice_frame" = "glyph";
  if (capsule.voice_frame?.data_b64) aad = "voice_frame";
  else if (capsule.voice_note?.data_b64) aad = "voice_note";
  else if (capsule.glyphs_enc_b64) aad = "glyph";

  const { lease } = await getLease(aad, kg, localWA, remoteWA);

  if (aad === "glyph" && capsule.glyphs_enc_b64) {
    const pt = await qkdDecrypt(lease, capsule.enc, capsule.glyphs_enc_b64, "glyph");
    const text = new TextDecoder().decode(pt);
    try { capsule.glyphs = JSON.parse(text); } catch { capsule.glyphs = [text]; }
    delete capsule.glyphs_enc_b64;
  } else if (aad === "voice_note" && capsule.voice_note?.data_b64) {
    const pt = await qkdDecrypt(lease, capsule.enc, capsule.voice_note.data_b64, "voice_note");
    capsule.voice_note.data_b64 = u8ToB64(pt); // restore plaintext audio
  } else if (aad === "voice_frame" && capsule.voice_frame?.data_b64) {
    const pt = await qkdDecrypt(lease, capsule.enc, capsule.voice_frame.data_b64, "voice_frame");
    capsule.voice_frame.data_b64 = u8ToB64(pt);
  }

  return capsule;
}
/* ───────────────────────────────────────────────────────────── */

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

      ws.onmessage = async (e) => {
        try {
          const raw: any = JSON.parse(e.data);

          // Graph guard (keep this)
          const evGraph =
            raw?.meta?.graph ??
            raw?.graph ??
            raw?.envelope?.meta?.graph ??
            raw?.envelope?.graph;
          if (graph && evGraph && evGraph !== graph) return;

          const env = raw?.envelope ?? null;

          // Uniform envelope for downstream code
          const envelope = env
            ? { capsule: env.capsule, meta: env.meta, id: env.id, ts: env.ts }
            : { capsule: raw?.capsule, meta: raw?.meta, id: raw?.id, ts: raw?.ts };

          const cap0 = envelope.capsule || {};

          // 🔹 FAST-PATH: forward chat_message immediately so bubbles appear live
          if (cap0?.chat_message && typeof cap0.chat_message.text === "string") {
            enqueue({
              type: "glyphnet_capsule",
              capsule: envelope.capsule,
              meta: envelope.meta,
              envelope, // extra field is fine; ChatThread already looks for it
            } as GlyphnetEvent);
            return;
          }

          // ——— original logic for other frames ———
          let baseType: string | undefined =
            raw?.type ||
            raw?.event ||
            env?.type ||
            (env?.capsule?.voice_frame
              ? "glyphnet_voice_frame"
              : env?.capsule
              ? "glyphnet_capsule"
              : undefined);

          // Locks
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
            // Build an envelope shape we can work with whether server sent flat or nested
            const envelope2 = env
              ? { capsule: env.capsule, meta: env.meta }
              : { capsule: raw?.capsule, meta: raw?.meta };

            // Optional QKD decrypt
            try {
              const kgForMsg = envelope2?.meta?.graph || "personal";
              const localWA = "ucs://local/self";
              const remoteWA =
                envelope2?.meta?.localWA ??
                envelope2?.meta?.sender ??
                envelope2?.meta?.recipient ??
                "ucs://unknown";

              envelope2.capsule = await decryptIfNeeded(
                envelope2.capsule,
                kgForMsg,
                localWA,
                remoteWA
              );
            } catch {
              // leave ciphertext as-is if decrypt fails
            }

            const capsule = envelope2.capsule;
            const meta = envelope2.meta;

            let t = baseType || "glyphnet_capsule";
            if (capsule?.voice_frame && t !== "glyphnet_voice_frame") {
              t = "glyphnet_voice_frame";
            }

            ev = { ...raw, type: t, capsule, meta };
          }

          enqueue(ev);
        } catch {
          // ignore non-JSON frames
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