// src/hooks/useWebSocket.ts
import { useEffect, useMemo, useRef, useState } from "react";

// Local no-op; avoids bundling a non-existent UI module.
function playGlyphNarration(_: unknown) { /* no-op */ }

// ---------------- Per-tab connection id ----------------
export const FORCE_WS_ID_KEY = "gnet:ws-id";

/** Stable id for the current tab (survives reload via sessionStorage). */
export const WS_ID = (() => {
  try {
    let v = sessionStorage.getItem(FORCE_WS_ID_KEY);
    if (!v) {
      v =
        crypto?.randomUUID?.() ||
        `ws-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      sessionStorage.setItem(FORCE_WS_ID_KEY, v);
    }
    return v;
  } catch {
    return `ws-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }
})();

/** Optional: expose helpers to DevTools for quick testing. */
declare global { interface Window { __WS_ID__?: string; forceWsId?: (id?: string) => void; } }
if (typeof window !== "undefined") {
  window.__WS_ID__ = WS_ID;
  window.forceWsId = (id?: string) => {
    try {
      const next =
        id ||
        `manual-${Math.random().toString(36).slice(2, 6)}-${Date.now()
          .toString(36)
          .slice(-4)}`;
      sessionStorage.setItem(FORCE_WS_ID_KEY, next);
      console.log("[WS] forcing new ws-id:", next, "→ reloading…");
      location.reload();
    } catch (e) {
      console.warn("[WS] unable to force ws-id", e);
    }
  };
}

// ---------------- URL builders ----------------

/** Build a WebSocket URL that works in dev (Vite/Codespaces 5173 → backend 8080) and prod. */
export function getWssUrl(pathOrUrl: string): string {
  // Absolute ws/wss stays as-is
  if (/^wss?:\/\//i.test(pathOrUrl)) return pathOrUrl;

  // http/https → ws/wss
  if (/^https?:\/\//i.test(pathOrUrl)) {
    const u = new URL(pathOrUrl);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    return u.toString();
  }

  const hasWindow = typeof window !== "undefined";
  const isDev = (import.meta as any).env?.DEV;

  // ✅ DEV (Vite/Codespaces): go via the current origin so Vite proxy (`/ws`) forwards
  if (hasWindow && isDev) {
    const originWs = window.location.origin.replace(/^http/, "ws");
    const seg = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`;
    return `${originWs}${seg}`; // e.g. wss://...-5173.app.github.dev/ws/ghx/ucs_hub
  }

  // PROD/default: same host, swap protocol
  const proto = hasWindow && window.location.protocol === "https:" ? "wss" : "ws";
  const host = hasWindow ? window.location.host : "localhost:8080";
  const seg = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`;
  return `${proto}://${host}${seg}`;
}

/** Append/override conn_id on the final WS URL (keeps existing params). */
function addConnIdParam(raw: string): string {
  try {
    const u = new URL(raw);
    u.searchParams.set("conn_id", WS_ID);
    return u.toString();
  } catch {
    const sep = raw.includes("?") ? "&" : "?";
    return `${raw}${sep}conn_id=${encodeURIComponent(WS_ID)}`;
  }
}

// ---------------- Shared helpers for HTTP posts ----------------

/** Add X-Conn-Id header using this tab's WS_ID. */
export function withConnHeaders<T extends Record<string, string>>(headers: T): T & { "X-Conn-Id": string } {
  return { ...headers, "X-Conn-Id": WS_ID };
}

/** Merge meta and attach conn_id for server fanout de-dupe. */
export function withConnMeta<T extends Record<string, any>>(meta?: T): T & { conn_id: string } {
  return { ...(meta as any), conn_id: WS_ID };
}

// ---------------- Hook ----------------

type MsgHandler = (data: any) => void;

export default function useWebSocket(
  pathOrUrl: string,
  onMessage?: MsgHandler,
  filterType?: string[]
) {
  const socketRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastJsonMessage, setLastJsonMessage] = useState<any>(null);

  // Make filter types stable to avoid needless reconnects
  const filterKey = useMemo(
    () => (Array.isArray(filterType) && filterType.length ? [...filterType].sort().join("|") : ""),
    // use a simple string key to avoid object identity churn
    [Array.isArray(filterType) ? filterType.join("|") : ""]
  );

  // Strict-mode & stale-effect guards
  const genRef = useRef(0);
  const manualCloseRef = useRef(false);
  const retryRef = useRef(0);
  const hbRef = useRef<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!pathOrUrl) return;

    manualCloseRef.current = false;
    const myGen = ++genRef.current;

    const finalUrl = addConnIdParam(getWssUrl(pathOrUrl));

    const connect = () => {
      const socket = new WebSocket(finalUrl);
      socketRef.current = socket;

      console.log("[WebSocket] connecting →", finalUrl, "(wsId:", WS_ID, ")");

      const clearHeartbeat = () => {
        if (hbRef.current != null) {
          clearInterval(hbRef.current);
          hbRef.current = null;
        }
      };

      socket.onopen = () => {
        if (genRef.current !== myGen) return;
        setConnected(true);
        retryRef.current = 0;
        console.log("[WebSocket] open →", finalUrl, "(wsId:", WS_ID, ")");

        // keep-alive for proxies
        clearHeartbeat();
        hbRef.current = window.setInterval(() => {
          try {
            socket.send(JSON.stringify({ type: "ping", ts: Date.now(), conn_id: WS_ID }));
          } catch { /* ignore */ }
        }, 25000);
      };

      socket.onmessage = (event) => {
        let data: any = event.data;
        try { data = JSON.parse(event.data); } catch { /* non-JSON payload */ }

        const msgType = data?.type || data?.event;

        // ⚠️ Do NOT drop by top-level conn_id. Some servers set it to the *recipient*.
        // Only drop if server explicitly tags the *origin* connection id.
        const originId =
          data?.meta?.origin_conn_id ??
          data?.meta?.source_conn_id ??
          data?.meta?.from_conn_id ??
          null;

        if (originId && originId === WS_ID) {
          // true self-echo
          return;
        }

        // Tiny trace to verify inbound frames
        if (data?.meta?.conn_id || data?.conn_id) {
          console.debug("[WS in]", {
            type: msgType,
            meta_conn_id: data?.meta?.conn_id,
            top_conn_id: data?.conn_id,
            wsId: WS_ID,
          });
        }

        if (filterType?.length && msgType && !filterType.includes(msgType)) return;

        if (msgType === "glyph_execution" && data?.payload?.glyph) {
          playGlyphNarration(data.payload.glyph);
        }

        setLastJsonMessage(data);
        onMessage?.(data);
      };

      const scheduleReconnect = (why: string) => {
        if (manualCloseRef.current) return;
        const delay = Math.min(4000, 300 + Math.pow(2, retryRef.current) * 150);
        retryRef.current++;
        console.warn(`[WebSocket] reconnect in ${delay}ms (${why})`);
        window.setTimeout(() => {
          if (genRef.current !== myGen) return;
          connect();
        }, delay);
      };

      socket.onerror = (err) => {
        if (genRef.current !== myGen) return;
        setConnected(false);
        console.warn("[WebSocket] error →", finalUrl, err, "(wsId:", WS_ID, ")");
        // onclose will handle reconnect
      };

      socket.onclose = (ev) => {
        if (genRef.current !== myGen) return;
        setConnected(false);
        clearHeartbeat();
        console.log("[WebSocket] close →", finalUrl, ev.code, ev.reason, "(wsId:", WS_ID, ")");
        if (!manualCloseRef.current && ev.code !== 1000) {
          scheduleReconnect(`code ${ev.code || "unknown"}`);
        }
      };
    };

    connect();

    return () => {
      if (genRef.current === myGen) {
        manualCloseRef.current = true;
        try { socketRef.current?.close(); } catch {}
        socketRef.current = null;
        setConnected(false);
      }
      if (hbRef.current != null) {
        clearInterval(hbRef.current);
        hbRef.current = null;
      }
      console.log("[WebSocket] cleanup →", finalUrl, "(wsId:", WS_ID, ")");
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathOrUrl, filterKey]);

  const sendJsonMessage = (payload: any) => {
    const s = socketRef.current;
    if (!s || s.readyState !== WebSocket.OPEN) {
      console.warn("[WebSocket] Cannot send — socket not open (wsId:", WS_ID, ")");
      return;
    }
    try {
      s.send(typeof payload === "string" ? payload : JSON.stringify(payload));
    } catch (e) {
      console.warn("[WebSocket] send failed", e);
    }
  };

  const emit = (event: string, data: any) => sendJsonMessage({ event, ...data });
  const close = () => {
    manualCloseRef.current = true;
    try { socketRef.current?.close(); } catch {}
  };

  return {
    socket: socketRef.current,
    connected,
    sendJsonMessage,
    lastJsonMessage,
    emit,
    close,
    wsId: WS_ID,
  };
}

// Alias for Q-series naming
export const useQfcSocket = useWebSocket;