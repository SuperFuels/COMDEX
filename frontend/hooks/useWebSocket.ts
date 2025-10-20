import { useEffect, useRef, useState } from "react";
import { playGlyphNarration } from "@/components/ui/hologram_audio";

/**
 * Build a WebSocket URL that works in dev and production.
 * Automatically normalizes wss/ws based on protocol and env.
 */
export function getWssUrl(pathOrUrl: string): string {
  const isDev = process.env.NODE_ENV === "development";

  // 🧩 Temporary override for GHX or local testing
  const hardcoded = isDev
    ? "ws://localhost:8080/ws/hqce"
    : "wss://comdex-api-375760843948.us-central1.run.app/ws/hqce";

  // Early return for now; fallback logic below is kept intact
  if (hardcoded) return hardcoded;

  // --- Normalization for absolute URLs ---
  if (/^wss?:\/\//i.test(pathOrUrl)) return pathOrUrl.replace(/^http/, "ws");
  if (/^https?:\/\//i.test(pathOrUrl)) {
    const u = new URL(pathOrUrl);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    return u.toString();
  }

  const wsProtocol = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss" : "ws";

  // --- Safe env var handling ---
  const rawEnv = process.env.NEXT_PUBLIC_SOCKET_URL ?? "";
  if (rawEnv) {
    const host = rawEnv.replace(/^wss?:\/\//, "").replace(/\/+$/, "");
    const seg = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`;
    return `${wsProtocol}://${host}${seg}`;
  }

  // --- Fallback to API base or window host ---
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";
  const host =
    apiBase.replace(/^https?:\/\//, "").replace(/\/+api\/?$/, "") ||
    (typeof window !== "undefined" ? window.location.host : "localhost:8080");

  const seg = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`;
  return `${wsProtocol}://${host}${seg}`;
}

type MsgHandler = (data: any) => void;

/**
 * Unified WebSocket Hook
 * - Auto-connects to GHX / QFC endpoints
 * - Safely reconnects and guards against undefined URLs
 */
export default function useWebSocket(
  pathOrUrl: string,
  onMessage?: MsgHandler,
  filterType?: string[]
) {
  const socketRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastJsonMessage, setLastJsonMessage] = useState<any>(null);

  useEffect(() => {
    if (typeof window === "undefined") return; // SSR guard

    const url = getWssUrl(pathOrUrl);
    if (!/^wss?:\/\//i.test(url)) {
      console.warn("[WebSocket] Invalid URL:", url);
      return;
    }

    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);

    socket.onmessage = (event) => {
      let data: any = event.data;
      try {
        data = JSON.parse(event.data);
      } catch {
        // not JSON, leave raw
      }

      const msgType = data?.type || data?.event;
      if (filterType?.length && msgType && !filterType.includes(msgType)) return;

      if (msgType === "glyph_execution" && data?.payload?.glyph) {
        playGlyphNarration(data.payload.glyph);
      }

      setLastJsonMessage(data);
      onMessage?.(data);
    };

    return () => socket.close();
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

  const emit = (event: string, data: any) =>
    sendJsonMessage({ event, ...data });

  const close = () => socketRef.current?.close();

  return {
    socket: socketRef.current,
    connected,
    sendJsonMessage,
    lastJsonMessage,
    emit,
    close,
  };
}

/** Alias for clarity in Q-Series contexts */
export const useQfcSocket = useWebSocket;