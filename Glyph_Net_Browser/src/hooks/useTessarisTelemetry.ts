import { useEffect, useMemo, useState } from "react";

export type TessarisTelemetry = {
  analytics?: any; // /api/ws/analytics  -> internal 8002
  symatics?: any;  // /api/ws/symatics   -> internal 8001
  fusion?: any;    // /api/ws/fusion     -> internal 8005
  rqfs?: any;      // /api/ws/rqfs_feedback -> internal 8006
  updatedAt?: number;
};

function useJsonWS(url: string, onMsg: (data: any) => void) {
  useEffect(() => {
    let ws: WebSocket | null = null;
    let stopped = false;
    let retryTimer: any = null;

    const connect = () => {
      if (stopped) return;

      ws = new WebSocket(url);

      ws.onmessage = (ev) => {
        try {
          onMsg(JSON.parse(ev.data));
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        if (stopped) return;
        retryTimer = setTimeout(connect, 800);
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
  }, [url, onMsg]);
}

export function useTessarisTelemetry(): TessarisTelemetry {
  const [t, setT] = useState<TessarisTelemetry>({});

  // http base (single port): usually http://localhost:8080 in your setup
  const httpBase =
    (import.meta as any)?.env?.VITE_API_BASE ||
    (typeof window !== "undefined" ? window.location.origin : "http://localhost:8080");

  // ws base: ws://... or wss://...
  const wsBase = useMemo(() => httpBase.replace(/^http/i, "ws"), [httpBase]);

  // connect through the API proxies (single port)
  const WS = useMemo(
    () => ({
      symatics: `${wsBase}/api/ws/symatics`,
      analytics: `${wsBase}/api/ws/analytics`,
      fusion: `${wsBase}/api/ws/fusion`,
      rqfs: `${wsBase}/api/ws/rqfs_feedback`,
      control: `${wsBase}/api/ws/control`, // not used here, but available
    }),
    [wsBase],
  );

  useJsonWS(WS.analytics, (m) =>
    setT((s) => ({ ...s, analytics: m, updatedAt: Date.now() })),
  );
  useJsonWS(WS.symatics, (m) =>
    setT((s) => ({ ...s, symatics: m, updatedAt: Date.now() })),
  );
  useJsonWS(WS.fusion, (m) =>
    setT((s) => ({ ...s, fusion: m, updatedAt: Date.now() })),
  );
  useJsonWS(WS.rqfs, (m) =>
    setT((s) => ({ ...s, rqfs: m, updatedAt: Date.now() })),
  );

  return t;
}