// frontend/src/hooks/useGlyphnet.ts
import { useEffect, useMemo, useRef, useState } from "react";
import { glyphnetWsUrl } from "@/lib/net";

export type GlyphnetEvent = {
  type: string;
  topic?: string;
  envelope?: any;
  [k: string]: any;
};

export default function useGlyphnet(recipient: string) {
  const url = useMemo(() => (recipient ? glyphnetWsUrl(recipient) : ""), [recipient]);
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<GlyphnetEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!url) return;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = (e) => setError(String((e as any)?.message || "ws error"));

    ws.onmessage = (e) => {
      try {
        const msg: GlyphnetEvent = JSON.parse(e.data);
        // Normalize the capsule shape we send from backend
        if (msg.type === "glyphnet_capsule" || msg.type === "gnet_msg") {
          setMessages((prev) => [msg, ...prev].slice(0, 200)); // keep tail short
        }
      } catch (err) {
        // ignore
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [url]);

  return { connected, messages, error };
}