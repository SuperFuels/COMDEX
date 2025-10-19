// frontend/hooks/useWebSocket.ts
import { useEffect, useRef, useState } from "react";
import { playGlyphNarration } from "@/components/ui/hologram_audio";

// Build a ws/wss URL from a path or absolute URL
export function getWssUrl(pathOrUrl: string): string {
  // Temporary override for testing GHX connections
  const isDev = process.env.NODE_ENV === "development";

  // 👇 This is the only line that matters right now
  const hardcoded = isDev
    ? "ws://localhost:8080/ws/hqce"
    : "wss://comdex-api-375760843948.us-central1.run.app/ws/hqce";

  return hardcoded;

  // If they pass an absolute ws(s):// or http(s):// URL, normalize it.
  if (/^wss?:\/\//i.test(pathOrUrl)) return pathOrUrl.replace(/^http/, "ws");
  if (/^https?:\/\//i.test(pathOrUrl)) {
    const u = new URL(pathOrUrl);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    return u.toString();
  }

  const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";

  // Optional explicit socket host
  const raw = process.env.NEXT_PUBLIC_SOCKET_URL;
  if (raw) {
    const host = raw.replace(/^wss?:\/\//, "").replace(/\/+$/, "");
    const seg = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`;
    return `${wsProtocol}://${host}${seg}`;
  }

  // Fallback to API base or current host
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
  const host =
    apiBase
      .replace(/^https?:\/\//, "")
      .replace(/\/+api\/?$/, "") || window.location.host;

  const seg = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`;
  return `${wsProtocol}://${host}${seg}`;
}

type MsgHandler = (data: any) => void;

/**
 * Unified WebSocket hook
 * - Works with either pattern:
 *   a) const { emit } = useWebSocket(path, onMessage)
 *   b) const { sendJsonMessage, lastJsonMessage } = useWebSocket(path)
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
    // SSR guard
    if (typeof window === "undefined") return;

    const url = getWssUrl(pathOrUrl);
    if (!/^wss?:\/\//i.test(url)) {
      console.warn("[WebSocket] Invalid URL:", url);
      return;
    }

    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      setConnected(true);
      // console.info(`[WebSocket] Connected: ${url}`);
    };

    socket.onclose = () => {
      setConnected(false);
      // console.warn("[WebSocket] Disconnected:", url);
    };

    socket.onerror = (e) => {
      setConnected(false);
      // console.error("[WebSocket] Error:", e);
    };

    socket.onmessage = (event) => {
      let data: any = event.data;
      try {
        data = JSON.parse(event.data);
      } catch {
        // leave as raw if not JSON
      }

      const msgType = data?.type || data?.event;
      if (filterType?.length && msgType && !filterType.includes(msgType)) return;

      // Optional nicety: narrate glyphs when we see them
      if (msgType === "glyph_execution" && data?.payload?.glyph) {
        playGlyphNarration(data.payload.glyph);
      }

      setLastJsonMessage(data);
      onMessage?.(data);
    };

    return () => {
      socket.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathOrUrl, filterType?.join(",")]); // keep deps stable

  const sendJsonMessage = (payload: any) => {
    const s = socketRef.current;
    if (!s || s.readyState !== WebSocket.OPEN) {
      console.warn("[WebSocket] Cannot send — socket not open");
      return;
    }
    s.send(typeof payload === "string" ? payload : JSON.stringify(payload));
  };

  // Back-compat alias for existing code
  const emit = (event: string, data: any) =>
    sendJsonMessage({ event, ...data });

  const close = () => socketRef.current?.close();

  return {
    socket: socketRef.current,
    connected,
    // New/expected API:
    sendJsonMessage,
    lastJsonMessage,
    // Back-compat:
    emit,
    close,
  };
}

/** Lightweight alias you can import if you prefer a named export */
export const useQfcSocket = useWebSocket;