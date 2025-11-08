// frontend/src/hooks/useGlyphnet.ts
import { useEffect, useRef, useState } from "react";

export type GlyphnetEvent = {
  type: string;
  topic?: string;
  envelope?: any;
  [k: string]: any;
};

// Build the correct WSS/WS URL for GlyphNet in Codespaces, local dev, or same-origin
function glyphnetWsURL(topic: string, token = "dev-token") {
  const host = location.host;
  const encTopic = encodeURIComponent(topic);

  // Codespaces: page is https://<id>-5173.app.github.dev → backend on https://<id>-8080.app.github.dev
  if (host.endsWith(".app.github.dev")) {
    return `wss://${host.replace("-5173", "-8080")}/ws/glyphnet?token=${token}&topic=${encTopic}`;
  }
  // Local dev: Vite on 5173, backend on 8080
  if (host.endsWith(":5173")) {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    return `${scheme}://${host.replace(":5173", ":8080")}/ws/glyphnet?token=${token}&topic=${encTopic}`;
  }
  // Same-origin deploy
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${host}/ws/glyphnet?token=${token}&topic=${encTopic}`;
}

export default function useGlyphnet(recipient: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<GlyphnetEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!recipient) return;

    // If you later store a real token, read it here (fallback to dev-token)
    const token = (localStorage.getItem("gnet:token") || "dev-token").trim();
    const url = glyphnetWsURL(recipient, token);

    console.debug("[useGlyphnet] connecting →", url);

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.debug("[useGlyphnet] open");
      setConnected(true);
    };
    ws.onclose = () => {
      console.debug("[useGlyphnet] close");
      setConnected(false);
    };
    ws.onerror = (e) => {
      console.warn("[useGlyphnet] error", e);
      setError(String((e as any)?.message || "ws error"));
    };

    ws.onmessage = (e) => {
      try {
        const raw: any = JSON.parse(e.data);

        // quick visibility for lock frames
        if (raw?.type === "entanglement_lock") {
          console.debug("[useGlyphnet] lock", raw);
        }

        // Derive a type if needed
        let t: string | undefined =
          (raw?.type as string | undefined) || (raw?.event as string | undefined);

        if (!t && raw?.envelope) {
          t =
            raw.envelope?.type ||
            (raw.envelope?.capsule?.voice_frame ? "glyphnet_voice_frame" : "glyphnet_capsule");
        }

        // Lock events can arrive as explicit frames or legacy acquired/released names
        const isLock =
          t === "entanglement_lock" ||
          raw?.type === "entanglement_lock" ||
          t === "entanglement_lock_acquired" ||
          t === "entanglement_lock_released";

        // Accept canonical capsule types OR lock events OR status OR anything with an envelope
        const accepted =
          isLock ||
          t === "glyphnet_capsule" ||
          t === "gnet_msg" ||
          t === "glyphnet_voice_frame" ||
          t === "status" ||
          !!raw?.envelope;

        if (!accepted) return;

        let msg: GlyphnetEvent = {
          ...raw,
          type: isLock ? "entanglement_lock" : (t || "glyphnet_capsule"),
        };

        if (isLock) {
          const resource =
            raw?.resource ?? raw?.envelope?.resource ?? raw?.payload?.resource;
          const owner =
            raw?.owner ?? raw?.envelope?.owner ?? raw?.payload?.owner;
          const state =
            raw?.state ??
            raw?.envelope?.state ??
            (t === "entanglement_lock_released" ? "free" : "held");
          const granted =
            raw?.granted ??
            raw?.envelope?.granted ??
            (t === "entanglement_lock_acquired"
              ? true
              : t === "entanglement_lock_released"
              ? true
              : undefined);
          const until = raw?.until ?? raw?.envelope?.until;

          msg = {
            ...msg,
            resource,
            owner,
            state,
            granted,
            until,
            // convenience: strip "voice:" so UI can compare to the ucs://… directly
            resourceTopic:
              typeof resource === "string" ? resource.replace(/^voice:/, "") : undefined,
          } as GlyphnetEvent;
        }

        // Coerce envelope voice frames to canonical type field if needed
        if (!isLock && !msg.type && raw?.envelope?.capsule?.voice_frame) {
          msg.type = "glyphnet_voice_frame";
        }

        setMessages((prev) => {
          const next = [...prev, msg];
          if (next.length > 200) next.shift();
          return next;
        });
      } catch {
        // ignore non-JSON payloads
      }
    };

    return () => {
      try {
        ws.close();
      } catch {}
      wsRef.current = null;
    };
  }, [recipient]);

  return { connected, messages, error };
}