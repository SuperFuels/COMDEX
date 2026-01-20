import { useEffect, useMemo, useRef, useState } from "react";

export type TessarisTelemetry = {
  analytics?: any; // /api/ws/analytics  -> proxied to 8002 (/ws/analytics)
  symatics?: any;  // /api/ws/symatics   -> proxied to 8001 (/ws/symatics)
  fusion?: any;    // /api/ws/fusion     -> proxied to 8005 (/ws/fusion)
  rqfs?: any;      // /api/ws/rqfs_feedback -> proxied to 8006 (/ws/rqfs_feedback)
  updatedAt?: number;
};

function useJsonWS(url: string, onMsg: (data: any) => void) {
  const onMsgRef = useRef(onMsg);
  onMsgRef.current = onMsg;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let stopped = false;
    let retryTimer: any = null;
    let retryMs = 800;

    const connect = () => {
      if (stopped) return;

      ws = new WebSocket(url);

      ws.onmessage = (ev) => {
        try {
          onMsgRef.current(JSON.parse(ev.data));
        } catch {
          // ignore parse errors
        }
      };

      ws.onopen = () => {
        retryMs = 800; // reset backoff after a clean connect
      };

      ws.onclose = () => {
        if (stopped) return;
        retryTimer = setTimeout(connect, retryMs);
        retryMs = Math.min(10_000, Math.floor(retryMs * 1.5));
      };

      ws.onerror = () => {
        try {
          ws?.close();
        } catch {
          // ignore
        }
      };
    };

    connect();

    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      try {
        ws?.close();
      } catch {
        // ignore
      }
    };
  }, [url]); // IMPORTANT: only url
}

export function useTessarisTelemetry(): TessarisTelemetry {
  const [t, setT] = useState<TessarisTelemetry>({});

  // We want WS to go through the Vite dev server (5173) so proxy rules apply.
  const httpBase =
    (process.env.NEXT_PUBLIC_API_ORIGIN as string | undefined) ||
    (process.env.NEXT_PUBLIC_GLYPHNET_HTTP_BASE as string | undefined) ||
    (typeof window !== "undefined"
      ? window.location.origin
      : "http://localhost:8080");

  const wsBase = useMemo(() => httpBase.replace(/^http/i, "ws"), [httpBase]);

  const WS = useMemo(
    () => ({
      symatics: `${wsBase}/api/ws/symatics`,
      analytics: `${wsBase}/api/ws/analytics`,
      fusion: `${wsBase}/api/ws/fusion`,
      rqfs: `${wsBase}/api/ws/rqfs_feedback`,
      control: `${wsBase}/api/ws/control`,
    }),
    [wsBase],
  );

  useJsonWS(WS.analytics, (m) => setT((s) => ({ ...s, analytics: m, updatedAt: Date.now() })));
  useJsonWS(WS.symatics, (m) => setT((s) => ({ ...s, symatics: m, updatedAt: Date.now() })));
  useJsonWS(WS.fusion, (m) => setT((s) => ({ ...s, fusion: m, updatedAt: Date.now() })));
  useJsonWS(WS.rqfs, (m) => setT((s) => ({ ...s, rqfs: m, updatedAt: Date.now() })));

  return t;
}