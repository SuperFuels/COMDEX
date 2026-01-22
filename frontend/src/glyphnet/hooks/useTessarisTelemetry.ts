import { useEffect, useMemo, useRef, useState } from "react";

export type TessarisTelemetry = {
  analytics?: any; // /api/ws/analytics  -> proxied to 8002 (/ws/analytics)
  symatics?: any; // /api/ws/symatics   -> proxied to 8001 (/ws/symatics)
  fusion?: any; // /api/ws/fusion     -> proxied to 8005 (/ws/fusion)
  rqfs?: any; // /api/ws/rqfs_feedback -> proxied to 8006 (/ws/rqfs_feedback)
  control?: any; // /api/ws/control (optional)
  qfc?: any; // /api/ws/qfc (optional, only if backend serves it)
  updatedAt?: number;

  // Optional per-stream freshness (helps UI decide NO_FEED vs LIVE)
  ageMs?: Partial<Record<keyof Omit<TessarisTelemetry, "updatedAt" | "ageMs">, number>>;
};

function normalizeWsBase(input: string) {
  const s = (input || "").trim().replace(/\/+$/, "");
  if (!s) return "";

  // allow people to paste a ws:// or wss:// directly
  if (s.startsWith("ws://") || s.startsWith("wss://")) return s;

  // convert http(s):// to ws(s)://
  if (s.startsWith("https://")) return "wss://" + s.slice("https://".length);
  if (s.startsWith("http://")) return "ws://" + s.slice("http://".length);

  // if they provided a bare host, assume wss
  return "wss://" + s.replace(/^\/+/, "");
}

function resolveHttpBase() {
  // Prefer explicit "this is the backend origin" vars
  const env =
    (process.env.NEXT_PUBLIC_API_ORIGIN as string | undefined) ||
    (process.env.NEXT_PUBLIC_GLYPHNET_HTTP_BASE as string | undefined) ||
    "";

  const cleaned = (env || "").trim().replace(/\/+$/, "");
  if (cleaned) return cleaned;

  // Local dev (FE :5173/3000) usually wants BE :8080 unless you proxy.
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const port = window.location.port;
    const isLocal = host === "localhost" || host === "127.0.0.1";

    // If you're on a local FE port, default BE to :8080.
    if (isLocal && (port === "5173" || port === "3000")) return "http://127.0.0.1:8080";

    // Otherwise use same-origin (works only if you actually proxy /api/ws/*)
    return window.location.origin;
  }

  return "http://127.0.0.1:8080";
}

function useJsonWS(url: string, onMsg: (data: any) => void, onHealth?: (ev: { ok: boolean; at: number; err?: string }) => void) {
  const onMsgRef = useRef(onMsg);
  onMsgRef.current = onMsg;

  const onHealthRef = useRef(onHealth);
  onHealthRef.current = onHealth;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let stopped = false;
    let retryTimer: any = null;
    let retryMs = 800;

    const connect = () => {
      if (stopped) return;

      try {
        ws = new WebSocket(url);
      } catch (e: any) {
        onHealthRef.current?.({ ok: false, at: Date.now(), err: String(e?.message || e) });
        retryTimer = setTimeout(connect, retryMs);
        retryMs = Math.min(10_000, Math.floor(retryMs * 1.5));
        return;
      }

      ws.onmessage = (ev) => {
        onHealthRef.current?.({ ok: true, at: Date.now() });
        try {
          onMsgRef.current(JSON.parse(String(ev.data)));
        } catch {
          // ignore parse errors
        }
      };

      ws.onopen = () => {
        retryMs = 800; // reset backoff after a clean connect
        onHealthRef.current?.({ ok: true, at: Date.now() });
      };

      ws.onclose = () => {
        onHealthRef.current?.({ ok: false, at: Date.now(), err: "closed" });
        if (stopped) return;
        retryTimer = setTimeout(connect, retryMs);
        retryMs = Math.min(10_000, Math.floor(retryMs * 1.5));
      };

      ws.onerror = () => {
        onHealthRef.current?.({ ok: false, at: Date.now(), err: "socket_error" });
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
  const [t, setT] = useState<TessarisTelemetry>({ ageMs: {} });

  const httpBase = useMemo(() => resolveHttpBase(), []);
  const wsBase = useMemo(() => normalizeWsBase(httpBase), [httpBase]);

  const WS = useMemo(
    () => ({
      symatics: `${wsBase}/api/ws/symatics`,
      analytics: `${wsBase}/api/ws/analytics`,
      fusion: `${wsBase}/api/ws/fusion`,
      rqfs: `${wsBase}/api/ws/rqfs_feedback`,
      control: `${wsBase}/api/ws/control`,
      // Only useful if your backend actually serves /api/ws/qfc
      qfc: `${wsBase}/api/ws/qfc`,
    }),
    [wsBase]
  );

  const markAge = (k: keyof TessarisTelemetry) => {
    const now = Date.now();
    setT((s) => ({
      ...s,
      updatedAt: now,
      ageMs: { ...(s.ageMs || {}), [k as any]: 0 },
    }));
  };

  // live age ticker (optional but useful)
  useEffect(() => {
    const id = window.setInterval(() => {
      setT((s) => {
        const ageMs = { ...(s.ageMs || {}) } as any;
        for (const key of Object.keys(ageMs)) {
          const v = ageMs[key];
          if (typeof v === "number") ageMs[key] = Math.min(60_000, v + 250);
        }
        return { ...s, ageMs };
      });
    }, 250);
    return () => window.clearInterval(id);
  }, []);

  useJsonWS(WS.analytics, (m) => setT((s) => ({ ...s, analytics: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), analytics: 0 } })));
  useJsonWS(WS.symatics, (m) => setT((s) => ({ ...s, symatics: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), symatics: 0 } })));
  useJsonWS(WS.fusion, (m) => setT((s) => ({ ...s, fusion: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), fusion: 0 } })));
  useJsonWS(WS.rqfs, (m) => setT((s) => ({ ...s, rqfs: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), rqfs: 0 } })));
  useJsonWS(WS.control, (m) => setT((s) => ({ ...s, control: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), control: 0 } })));

  // OPTIONAL: only keep this if /api/ws/qfc exists on your backend
  // useJsonWS(WS.qfc, (m) => setT((s) => ({ ...s, qfc: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), qfc: 0 } })));

  return t;
}