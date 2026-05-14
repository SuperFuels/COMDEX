import { useEffect, useMemo, useRef, useState } from "react";

export type TessarisTelemetry = {
  analytics?: any; // /api/ws/analytics  -> proxied to 8002 (/ws/analytics)
  symatics?: any;  // /api/ws/symatics   -> proxied to 8001 (/ws/symatics)
  fusion?: any;    // /api/ws/fusion     -> proxied to 8005 (/ws/fusion)
  rqfs?: any;      // /api/ws/rqfs_feedback -> proxied to 8006 (/ws/rqfs_feedback)
  control?: any;   // /api/ws/control (optional)
  qfc?: any;       // /api/ws/qfc (optional, only if backend serves it)
  updatedAt?: number;

  // Optional per-stream freshness (helps UI decide NO_FEED vs LIVE)
  ageMs?: Partial<Record<keyof Omit<TessarisTelemetry, "updatedAt" | "ageMs">, number>>;
};

function stripSlash(s: string) {
  return (s || "").trim().replace(/\/+$/, "");
}

/**
 * Convert a configured HTTP base into a WS ORIGIN only.
 * This avoids broken URLs like:
 *   wss://host/aion-demo/api/ws/fusion   (wrong)
 *   wss://host/api/api/ws/fusion        (wrong)
 */
function wsOriginFromHttpBase(input: string) {
  const s = (input || "").trim();
  if (!s) return "";

  // already ws(s)://
  if (s.startsWith("ws://") || s.startsWith("wss://")) {
    try {
      const u = new URL(s);
      return `${u.protocol}//${u.host}`;
    } catch {
      return stripSlash(s);
    }
  }

  // http(s)://
  if (s.startsWith("http://") || s.startsWith("https://")) {
    try {
      const u = new URL(s);
      const proto = u.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${u.host}`;
    } catch {
      const cleaned = stripSlash(s);
      if (cleaned.startsWith("https://")) return "wss://" + cleaned.slice("https://".length);
      if (cleaned.startsWith("http://")) return "ws://" + cleaned.slice("http://".length);
      return cleaned;
    }
  }

  // bare host
  return "wss://" + stripSlash(s).replace(/^\/+/, "");
}

/**
 * IMPORTANT: this hook is for the *backend origin* (or FE origin if proxying).
 * Do NOT use NEXT_PUBLIC_AION_DEMO_HTTP_BASE here.
 */
function resolveHttpBase() {
  const env =
    (process.env.NEXT_PUBLIC_API_ORIGIN as string | undefined) ||
    (process.env.NEXT_PUBLIC_GLYPHNET_HTTP_BASE as string | undefined) ||
    (process.env.NEXT_PUBLIC_API_URL as string | undefined) ||
    (process.env.NEXT_PUBLIC_API_BASE as string | undefined) ||
    (process.env.NEXT_PUBLIC_AION_API_BASE as string | undefined) ||
    "";

  const cleaned = stripSlash(env);
  if (cleaned) return cleaned;

  // Local dev (FE :5173/3000) usually wants BE :8080 unless you proxy.
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    const port = window.location.port;
    const isLocal = host === "localhost" || host === "127.0.0.1";

    if (isLocal && (port === "5173" || port === "3000")) return "http://127.0.0.1:8080";

    // Same-origin only works if you proxy /api/ws/* from the frontend.
    return window.location.origin;
  }

  return "http://127.0.0.1:8080";
}

/**
 * WS prefix is deployment-dependent:
 * - "/api/ws" when FE proxies to backend
 * - "/ws" when hitting backend directly
 */
function wsPrefix() {
  const p = (process.env.NEXT_PUBLIC_WS_PREFIX || "/api/ws").trim();
  return (p.startsWith("/") ? p : "/" + p).replace(/\/+$/, "");
}

function useJsonWS(
  url: string,
  onMsg: (data: any) => void,
  onHealth?: (ev: { ok: boolean; at: number; err?: string }) => void
) {
  const onMsgRef = useRef(onMsg);
  onMsgRef.current = onMsg;

  const onHealthRef = useRef(onHealth);
  onHealthRef.current = onHealth;

  useEffect(() => {
    if (!url) return;

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
        retryMs = 800;
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
        } catch {}
      };
    };

    connect();

    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      try {
        ws?.close();
      } catch {}
    };
  }, [url]);
}

export function useTessarisTelemetry(): TessarisTelemetry {
  const [t, setT] = useState<TessarisTelemetry>({ ageMs: {} });

  const httpBase = useMemo(() => resolveHttpBase(), []);
  const wsBase = useMemo(() => wsOriginFromHttpBase(httpBase), [httpBase]);
  const prefix = useMemo(() => wsPrefix(), []);

  const WS = useMemo(
    () => ({
      symatics: `${wsBase}${prefix}/symatics`,
      analytics: `${wsBase}${prefix}/analytics`,
      fusion: `${wsBase}${prefix}/fusion`,
      rqfs: `${wsBase}${prefix}/rqfs_feedback`,
      control: `${wsBase}${prefix}/control`,
      qfc: `${wsBase}${prefix}/qfc`,
    }),
    [wsBase, prefix]
  );

  // live age ticker
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

  useJsonWS(WS.analytics, (m) =>
    setT((s) => ({ ...s, analytics: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), analytics: 0 } }))
  );
  useJsonWS(WS.symatics, (m) =>
    setT((s) => ({ ...s, symatics: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), symatics: 0 } }))
  );
  useJsonWS(WS.fusion, (m) =>
    setT((s) => ({ ...s, fusion: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), fusion: 0 } }))
  );
  useJsonWS(WS.rqfs, (m) =>
    setT((s) => ({ ...s, rqfs: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), rqfs: 0 } }))
  );
  useJsonWS(WS.control, (m) =>
    setT((s) => ({ ...s, control: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), control: 0 } }))
  );

  // OPTIONAL (only if endpoint exists):
  // useJsonWS(WS.qfc, (m) =>
  //   setT((s) => ({ ...s, qfc: m, updatedAt: Date.now(), ageMs: { ...(s.ageMs || {}), qfc: 0 } }))
  // );

  return t;
}