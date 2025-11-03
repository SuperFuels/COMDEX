// src/hooks/useWebSocket.ts
import { useEffect, useRef, useState } from "react";

// Local no-op; avoids bundling a non-existent UI module.
function playGlyphNarration(_: unknown) { /* no-op */ }

/**
 * Build a WebSocket URL that works in dev (Vite/Codespaces 5173 → backend 8080) and prod.
 */
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

  // ✅ DEV (Vite/Codespaces): go via the current origin so Vite proxy (`/ws`) forwards to 8080
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

type MsgHandler = (data: any) => void;

export default function useWebSocket(
  pathOrUrl: string,
  onMessage?: MsgHandler,
  filterType?: string[]
) {
  const socketRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastJsonMessage, setLastJsonMessage] = useState<any>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!pathOrUrl) return; // no target yet

    const url = getWssUrl(pathOrUrl);
    console.log("[WebSocket] connecting →", url);

    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      setConnected(true);
      console.log("[WebSocket] open →", url);
    };
    socket.onclose = (ev) => {
      setConnected(false);
      console.log("[WebSocket] close →", url, ev.code, ev.reason);
    };
    socket.onerror = (err) => {
      setConnected(false);
      console.warn("[WebSocket] error →", url, err);
    };

    socket.onmessage = (event) => {
      let data: any = event.data;
      try { data = JSON.parse(event.data); } catch { /* non-JSON payload */ }

      const msgType = data?.type || data?.event;
      if (filterType?.length && msgType && !filterType.includes(msgType)) return;

      if (msgType === "glyph_execution" && data?.payload?.glyph) {
        // Optional audio cue (safe no-op here)
        playGlyphNarration(data.payload.glyph);
      }

      setLastJsonMessage(data);
      onMessage?.(data);
    };

    return () => {
      console.log("[WebSocket] cleanup →", url);
      try { socket.close(); } catch {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathOrUrl, filterType?.join(",")]);

  const sendJsonMessage = (payload: any) => {
    const s = socketRef.current;
    if (!s || s.readyState !== WebSocket.OPEN) {
      console.warn("[WebSocket] Cannot send — socket not open");
      return;
    }
    s.send(typeof payload === "string" ? payload : JSON.stringify(payload));
  };

  const emit = (event: string, data: any) => sendJsonMessage({ event, ...data });
  const close = () => {
    try { socketRef.current?.close(); } catch {}
  };

  return { socket: socketRef.current, connected, sendJsonMessage, lastJsonMessage, emit, close };
}

// Alias for Q-series naming
export const useQfcSocket = useWebSocket;