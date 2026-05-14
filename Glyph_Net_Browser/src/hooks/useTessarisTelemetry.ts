import { useEffect, useMemo, useRef, useState } from "react";

export type TessarisTelemetry = {
  analytics?: any; // /api/ws/analytics  -> proxied upstream
  symatics?: any;  // /api/ws/symatics
  fusion?: any;    // /api/ws/fusion
  rqfs?: any;      // /api/ws/rqfs_feedback
  updatedAt?: number;
};

function trimSlash(s: string) {
  return s.replace(/\/+$/, "");
}

function httpToWs(httpBase: string) {
  return httpBase.replace(/^http:/i, "ws:").replace(/^https:/i, "wss:");
}

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
        retryMs = 800;
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
  }, [url]);
}

export function useTessarisTelemetry(): TessarisTelemetry {
  const [t, setT] = useState<TessarisTelemetry>({});

  // Next-compatible env (browser-safe). Prefer explicit env, else same-origin.
  const httpBase = useMemo(() => {
    const envBase = (process.env.NEXT_PUBLIC_API_URL || "").trim();
    if (envBase) return trimSlash(envBase);

    // same-origin (works with your Next rewrites: /api/* -> backend)
    if (typeof window !== "undefined") return window.location.origin;

    // SSR fallback (should rarely matter because this hook runs client-side)
    return "http://localhost:8080";
  }, []);

  const wsBase = useMemo(() => {
    const envWs = (process.env.NEXT_PUBLIC_WS_URL || "").trim();
    if (envWs) return trimSlash(envWs);
    return trimSlash(httpToWs(httpBase));
  }, [httpBase]);

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