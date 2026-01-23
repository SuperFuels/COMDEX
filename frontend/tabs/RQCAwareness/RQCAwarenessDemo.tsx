"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * RQC AWARENESS HORIZON — v0.7.2 (FIXED: NO_FEED + DUP VARS + MISSING NAMES)
 *
 * Fixes your current TS errors:
 *  - ✅ no duplicate `closureLabel`
 *  - ✅ no `liveIsFresh` / `lastLiveAt` references (replaced with feedFresh / lastTelemetryAt)
 *  - ✅ status displayed is `displayStatus` (freshness-aware), not a stale variable
 *  - ✅ last telemetry uses `lastTelemetryAt`
 *  - ✅ auto-reconnect WS with backoff
 *  - ✅ strict metric mapping: ψ never equals ρ; coherence from C/SQI/Φ_coherence
 */

const SESSION_ID = "a99acc96-acde-48d5-9b6d-d2f434536d5b";
const STALE_MS = 2_500;

// log throttles
const TELEMETRY_LOG_EVERY_MS = 650;
const MAX_LOGS = 10;
const EPS = 1e-6;

type LogItem = { t: number; msg: string; kind: "info" | "warn" | "ok" | "bad" };

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

function safeUrl(u: string) {
  try {
    return new URL(u);
  } catch {
    return null;
  }
}

function num(x: any): number | null {
  const n = typeof x === "number" ? x : x != null ? Number(x) : NaN;
  return Number.isFinite(n) ? n : null;
}

function pickMetric(obj: any, keys: string[]) {
  for (const k of keys) {
    if (obj && Object.prototype.hasOwnProperty.call(obj, k)) {
      const v = num(obj[k]);
      if (v != null) return v;
    }
  }
  return null;
}

/**
 * Telemetry extractor (STRICT + DOC-CORRECT)
 *
 * Rules:
 * - Never derive ψ from ρ. ψ comes only from explicit psi/presence keys.
 * - Coherence uses the AION Φ-field contract: Φ_coherence is primary.
 *   Legacy aliases (C/SQI/coherence) are accepted only as compatibility fallbacks.
 * - Entropy uses the AION Φ-field contract: Φ_entropy is primary.
 *   Legacy aliases (E/entropy/Ibar) are accepted only as compatibility fallbacks.
 * - Φ scalar is taken only if explicitly emitted (Φ/phi). Otherwise Φ := Φ_coherence.
 * - ρ is kept separate and never used for ψ or coherence.
 * - Also extracts lock/threshold/id if present (mirror/lock fields).
 */
function extractMetrics(msg: any) {
  const m = msg?.metrics ?? msg?.state?.metrics ?? msg?.state ?? msg ?? {};
  const phiObj = msg?.phi ?? msg?.state?.phi ?? {};

  // ψ / κ / T are never inferred from other channels
  const psi = pickMetric(m, ["ψ", "psi", "wave_presence", "wavePresence", "presence"]);
  const kappa = pickMetric(m, ["κ", "kappa", "curvature"]);
  const T = pickMetric(m, ["T", "temporal", "time", "timestamp", "updatedAt_ms"]);

  // DOC-CORRECT Φ fields (prefer phi.* then metrics.*)
  const C =
    pickMetric(phiObj, ["Φ_coherence", "phi_coherence"]) ??
    pickMetric(m, ["Φ_coherence", "phi_coherence"]) ??
    // compatibility aliases (ONLY if backend defines them as Φ_coherence)
    pickMetric(phiObj, ["coherence"]) ??
    pickMetric(m, ["coherence"]) ??
    pickMetric(m, ["C", "SQI", "sqi"]);

  const entropy =
    pickMetric(phiObj, ["Φ_entropy", "phi_entropy"]) ??
    pickMetric(m, ["Φ_entropy", "phi_entropy"]) ??
    // compatibility aliases (ONLY if backend defines them as Φ_entropy)
    pickMetric(phiObj, ["entropy"]) ??
    pickMetric(m, ["entropy"]) ??
    pickMetric(m, ["E"]);

  // Φ scalar only if explicitly emitted, else display Φ := Φ_coherence
  const Phi =
    pickMetric(phiObj, ["Φ", "phi"]) ??
    pickMetric(m, ["Φ", "phi"]) ??
    (C != null ? C : null);

  // keep rho + Ibar separate (never used for ψ / coherence)
  const rho = pickMetric(phiObj, ["ρ", "rho"]) ?? pickMetric(m, ["ρ", "rho"]);
  const Ibar =
    pickMetric(phiObj, ["Ī", "Ibar", "Ī", "iota"]) ?? pickMetric(m, ["Ī", "Ibar", "Ī", "iota"]);

  // lock fields (if present)
  const lockedRaw = m?.locked ?? msg?.mirror?.locked ?? null;
  const locked =
    typeof lockedRaw === "boolean"
      ? lockedRaw
      : lockedRaw == null
      ? null
      : String(lockedRaw).toLowerCase() === "true";

  const threshold = num(m?.threshold ?? msg?.mirror?.threshold);
  const lockId =
    (m?.lock_id ?? msg?.mirror?.lock_id) != null ? String(m?.lock_id ?? msg?.mirror?.lock_id) : null;

  return { psi, kappa, T, Phi, C, entropy, rho, Ibar, locked, threshold, lockId };
}

function resolveOrigin(): string {
  const raw = (
    process.env.NEXT_PUBLIC_AION_DEMO_HTTP_BASE ||
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_AION_API_BASE ||
    process.env.NEXT_PUBLIC_API_BASE ||
    ""
  ).trim();

  const u = raw ? safeUrl(raw) : null;
  if (u) {
    u.pathname = "/";
    u.search = "";
    u.hash = "";
    return u.toString().replace(/\/+$/, "");
  }
  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

function pickRqcWsUrl() {
  const normalizeWs = (raw: string) => {
    let s = (raw || "").trim().replace(/\/+$/, "");
    if (!s) return "";
    if (s.startsWith("https://")) s = "wss://" + s.slice("https://".length);
    else if (s.startsWith("http://")) s = "ws://" + s.slice("http://".length);
    return s;
  };

  const raw = normalizeWs(process.env.NEXT_PUBLIC_RQC_WS || "");
  if (raw) return raw;

  const demoBase =
    (process.env.NEXT_PUBLIC_AION_DEMO_BASE || process.env.NEXT_PUBLIC_AION_DEMO_HTTP_BASE || "").trim();

  if (demoBase) {
    const http = demoBase.replace(/\/+$/, "");
    const wsRoot = normalizeWs(http);
    if (http.endsWith("/aion-demo")) return `${wsRoot}/ws/aion-demo`;
    return `${wsRoot}/aion-demo/ws/aion-demo`;
  }

  const origin = resolveOrigin();
  if (origin) {
    const wsRoot = normalizeWs(origin);
    return `${wsRoot}/aion-demo/ws/aion-demo`;
  }

  if (typeof window !== "undefined") {
    const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocal) return "ws://127.0.0.1:8007/ws/aion-demo";
  }

  return "";
}

function pickAionDemoBase() {
  const origin = resolveOrigin();
  return origin ? `${origin}/aion-demo` : "";
}

async function postJson(url: string, body: any, timeoutMs = 8000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body ?? {}),
      signal: ctrl.signal,
    });
    const txt = await r.text();
    let json: any = null;
    try {
      json = txt ? JSON.parse(txt) : null;
    } catch {
      json = { _nonJson: true, _text: txt.slice(0, 500) };
    }
    return { ok: r.ok, status: r.status, json };
  } finally {
    clearTimeout(t);
  }
}

export default function RQCAwarenessDemo() {
  const [psi, setPsi] = useState<number | null>(null);
  const [kappa, setKappa] = useState<number | null>(null);
  const [T, setT] = useState<number | null>(null);

  const [entropy, setEntropy] = useState<number | null>(null);
  const [phi, setPhi] = useState<number | null>(null);
  const [coherence, setCoherence] = useState<number | null>(null);

  const [statusFromMetrics, setStatusFromMetrics] = useState<"STABLE" | "ALIGNING" | "CRITICAL_DRIFT">("ALIGNING");
  const [manifoldSync, setManifoldSync] = useState<number[] | null>(null);

  const [isInjecting, setIsInjecting] = useState(false);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [running, setRunning] = useState(false);

  const wsUrl = useMemo(() => pickRqcWsUrl(), []);
  const aionDemoBase = useMemo(() => pickAionDemoBase(), []);

  const wsRef = useRef<WebSocket | null>(null);
  const [liveConnected, setLiveConnected] = useState(false);

  // freshness is based on TELEMETRY arrival time (not wsConnected flag)
  const [lastTelemetryAt, setLastTelemetryAt] = useState<number>(0);

  // backend lock fields (optional)
  const [locked, setLocked] = useState<boolean | null>(null);
  const [lockId, setLockId] = useState<string | null>(null);
  const [lockThreshold, setLockThreshold] = useState<number | null>(null);

  const lastTelemetryLogAtRef = useRef<number>(0);
  const lastValsRef = useRef({
    psi: null as number | null,
    kappa: null as number | null,
    T: null as number | null,
    entropy: null as number | null,
    phi: null as number | null,
    coherence: null as number | null,
  });

  const addLog = (msg: string, kind: LogItem["kind"] = "info") => {
    setLogs((prev) => [{ t: Date.now(), msg, kind }, ...prev].slice(0, MAX_LOGS));
  };

  const upsertTelemetryLine = (msg: string, kind: LogItem["kind"]) => {
    setLogs((prev) => {
      const next = [...prev];
      const idx = next.findIndex((x) => x.msg.startsWith("[Telemetry]"));
      const item = { t: Date.now(), msg, kind };
      if (idx >= 0) next[idx] = item;
      else next.unshift(item);
      return next.slice(0, MAX_LOGS);
    });
  };

  const computeStatus = (e: number, c: number) => {
    if (e >= 0.6 || c <= 0.35) return "CRITICAL_DRIFT";
    if (e >= 0.12 || c < 0.85) return "ALIGNING";
    return "STABLE";
  };

  const feedAgeMs = lastTelemetryAt ? Date.now() - lastTelemetryAt : Infinity;
  const feedFresh = running && !!wsUrl && feedAgeMs <= STALE_MS;

  const displayStatus: "STABLE" | "ALIGNING" | "CRITICAL_DRIFT" | "NO_FEED" = feedFresh
    ? statusFromMetrics
    : "NO_FEED";

  const resonanceIndex = useMemo(() => (entropy == null ? null : clamp01(1 - entropy * 0.2)), [entropy]);
  const stabilityIndex = useMemo(() => (phi == null ? null : clamp01(phi * 0.95)), [phi]);

  // πₛ closure:
  // - if backend emits locked=true -> closed
  // - else fall back to convergence thresholds
  const closureOk = useMemo(() => {
    if (locked === true) return true;
    if (phi == null || coherence == null || entropy == null) return false;
    return phi >= 0.92 && coherence >= 0.92 && entropy <= 0.08;
  }, [locked, phi, coherence, entropy]);

  const closureLabel = closureOk ? "LOCKED" : "UNLOCKED";

  const setIfChanged = (
    key: keyof typeof lastValsRef.current,
    setter: (v: any) => void,
    next: number | null
  ) => {
    if (next == null) return;
    const prev = lastValsRef.current[key];
    if (prev == null || Math.abs(prev - next) > EPS) {
      lastValsRef.current[key] = next;
      setter(next);
    }
  };

  const reset = () => {
    setPsi(null);
    setKappa(null);
    setT(null);
    setEntropy(null);
    setPhi(null);
    setCoherence(null);
    setManifoldSync(null);
    setIsInjecting(false);
    setLogs([]);
    setLiveConnected(false);
    setLastTelemetryAt(0);
    setLocked(null);
    setLockId(null);
    setLockThreshold(null);
    lastValsRef.current = { psi: null, kappa: null, T: null, entropy: null, phi: null, coherence: null };
    addLog("[System] Reset: Awareness Horizon re-armed.", "info");
  };

  const injectEntropy = async () => {
    setIsInjecting(true);
    try {
      const r = await postJson(`${aionDemoBase}/api/demo/inject_entropy`, { sessionId: SESSION_ID });
      if (r.ok) addLog(`[AION_DEMO] Inject triggered via /api/demo/inject_entropy`, "warn");
      else {
        const r2 = await postJson(`${aionDemoBase}/api/demo/phi/inject_entropy`, { sessionId: SESSION_ID });
        if (r2.ok) addLog(`[AION_DEMO] Φ entropy injected via /api/demo/phi/inject_entropy`, "warn");
        else addLog(`[AION_DEMO] Inject failed (HTTP ${r.status})`, "warn");
      }
    } catch (e: any) {
      addLog(`[AION_DEMO] Inject error: ${e?.message || String(e)}`, "warn");
    }
    window.setTimeout(() => setIsInjecting(false), 900);
  };

  // LIVE WS (auto-reconnect)
  useEffect(() => {
    if (!running) return;
    if (!wsUrl) return;

    let stopped = false;
    let retry = 0;
    let retryTimer: any = null;

    const scheduleReconnect = () => {
      if (stopped) return;
      const base = Math.min(8000, 300 * Math.pow(2, retry));
      const jitter = Math.floor(Math.random() * 250);
      const delay = base + jitter;
      retry = Math.min(6, retry + 1);
      retryTimer = window.setTimeout(connect, delay);
    };

    const connect = () => {
      if (stopped) return;

      try {
        wsRef.current?.close(1000, "reconnect");
      } catch {}
      wsRef.current = null;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setLiveConnected(true);
        retry = 0;
        addLog(`[RQC_LIVE] OPEN → ${wsUrl}`, "ok");
        try {
          ws.send(JSON.stringify({ type: "hello", client: "RQCAwarenessDemo", sessionId: SESSION_ID }));
        } catch {}
      };

      ws.onclose = (ev) => {
        setLiveConnected(false);
        addLog(`[RQC_LIVE] CLOSE code=${ev.code} reason=${ev.reason || "—"}`, "warn");
        scheduleReconnect();
      };

      ws.onerror = (ev) => {
        setLiveConnected(false);
        console.error("WS error", ev);
        addLog(`[RQC_LIVE] ERROR (see console)`, "warn");
        try {
          ws.close();
        } catch {}
      };

      ws.onmessage = (evt) => {
        setLastTelemetryAt(Date.now());

        const raw = String(evt.data);
        let data: any;
        try {
          data = JSON.parse(raw);
        } catch {
          return;
        }

        const type = String(data?.type || "");

        if (type === "telemetry" || type === "awareness_pulse") {
          const nm = extractMetrics(data);

          if (nm.locked != null) setLocked(nm.locked);
          if (nm.lockId != null) setLockId(nm.lockId);
          if (nm.threshold != null) setLockThreshold(nm.threshold);

          setIfChanged("psi", setPsi, nm.psi != null ? clamp01(nm.psi) : null);
          setIfChanged("kappa", setKappa, nm.kappa != null ? clamp01(nm.kappa) : null);
          setIfChanged("T", setT, nm.T != null ? nm.T : null);

          const nextCoh = nm.C != null ? clamp01(nm.C) : null;
          const nextEntropy = nm.entropy != null ? clamp01(nm.entropy) : null;
          const nextPhi = nm.Phi != null ? clamp01(nm.Phi) : nextCoh != null ? nextCoh : null;

          setIfChanged("coherence", setCoherence, nextCoh);
          setIfChanged("entropy", setEntropy, nextEntropy);
          setIfChanged("phi", setPhi, nextPhi);

          if (nextCoh != null) {
            const base = clamp(nextCoh * 100, 0, 100);
            setManifoldSync([0, 1, 2, 3].map((i) => clamp(base + i * 0.2, 0, 100)));
          }

          const eForStatus = nextEntropy ?? lastValsRef.current.entropy ?? 0.5;
          const cForStatus = nextCoh ?? lastValsRef.current.coherence ?? 0.5;
          const s = computeStatus(eForStatus, cForStatus);
          setStatusFromMetrics(s);

          const now = Date.now();
          if (now - lastTelemetryLogAtRef.current >= TELEMETRY_LOG_EVERY_MS) {
            lastTelemetryLogAtRef.current = now;

            const line =
              `[Telemetry] ψ=${nm.psi != null ? clamp01(nm.psi).toFixed(5) : "—"} ` +
              `κ=${nm.kappa != null ? clamp01(nm.kappa).toFixed(5) : "—"} ` +
              `T=${nm.T != null ? Number(nm.T).toFixed(3) : "—"} ` +
              `C=${nextCoh != null ? nextCoh.toFixed(4) : "—"} ` +
              `E=${nextEntropy != null ? nextEntropy.toFixed(4) : "—"} ` +
              `Φ=${nextPhi != null ? nextPhi.toFixed(4) : "—"}`;

            upsertTelemetryLine(line, s === "CRITICAL_DRIFT" ? "warn" : "info");

            const rqcLine =
              `[RQC] SQI=${nextCoh != null ? nextCoh.toFixed(4) : "—"} ` +
              `ρ=${nm.rho != null ? clamp01(nm.rho).toFixed(4) : "—"} ` +
              `Ī=${nm.Ibar != null ? clamp01(nm.Ibar).toFixed(4) : "—"}`;

            setLogs((prev) => {
              const next = [...prev];
              const idx = next.findIndex((x) => x.msg.startsWith("[RQC] "));
              const item = { t: Date.now(), msg: rqcLine, kind: "info" as const };
              if (idx >= 0) next[idx] = item;
              else next.unshift(item);
              return next.slice(0, MAX_LOGS);
            });
          }
          return;
        }

        if (type === "hello") {
          addLog(`[RQC_LIVE] ${String(data?.message || "hello")}`, "ok");
          return;
        }

        if (type === "error") {
          addLog(`[RQC_LIVE] ${String(data?.message || "error")}`, "warn");
          return;
        }
      };
    };

    connect();

    return () => {
      stopped = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      retryTimer = null;
      try {
        wsRef.current?.close(1000, "client stop");
      } catch {}
      wsRef.current = null;
      setLiveConnected(false);
    };
  }, [running, wsUrl]);

  // SIM mode if no WS
  const entropyRef = useRef<number>(0.15);
  const phiRef = useRef<number>(0.64);
  const cohRef = useRef<number>(0.64);

  useEffect(() => {
    if (!running) return;
    if (wsUrl) return;

    addLog("[SIM] Running local awareness simulator (not live telemetry).", "warn");

    const id = window.setInterval(() => {
      entropyRef.current = entropyRef.current > 0.05 ? Math.max(0.02, entropyRef.current - 0.015) : entropyRef.current;

      phiRef.current =
        entropyRef.current > 0.05 ? Math.min(0.99, phiRef.current + 0.02) : Math.max(0.92, phiRef.current - 0.005);

      const target = clamp01(phiRef.current);
      cohRef.current = clamp01(cohRef.current + (target - cohRef.current) * 0.18);

      setEntropy(entropyRef.current);
      setPhi(phiRef.current);
      setCoherence(cohRef.current);

      const base = clamp(cohRef.current * 100, 0, 100);
      setManifoldSync([0, 1, 2, 3].map((i) => clamp(base + i * 0.3, 0, 100)));

      setPsi(clamp01(0.15 + cohRef.current * 0.35));
      setKappa(null);
      setT(null);

      setStatusFromMetrics(computeStatus(entropyRef.current, cohRef.current));
      setLastTelemetryAt(Date.now());
    }, 200);

    return () => window.clearInterval(id);
  }, [running, wsUrl]);

  // UI helpers
  const barsEnabled = running && (!wsUrl || feedFresh);
  const displayPhi = phi ?? 0;
  const displayEntropy = entropy ?? 0;

  const pillDot =
    displayStatus === "NO_FEED"
      ? "bg-slate-400"
      : displayStatus === "CRITICAL_DRIFT"
      ? "bg-rose-500"
      : closureOk
      ? "bg-emerald-500"
      : "bg-blue-500";

  return (
    <div className="min-h-screen w-full bg-[#f8fafc] text-slate-900 font-sans py-10">
      <div className="max-w-6xl mx-auto px-6 space-y-8">
        {/* HEADER */}
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6 border-b border-slate-200 pb-8">
          <div>
            <h2 className="text-[10px] font-bold tracking-[0.3em] text-blue-600 uppercase">
              Tessaris Photonic Systems • Research Division
            </h2>
            <h1 className="mt-2 text-4xl tracking-tight text-slate-900">
              RQC Awareness Horizon <span className="font-semibold">v0.7.2</span>
            </h1>
            <p className="mt-2 text-slate-500 font-mono text-xs uppercase tracking-widest">
              Substrate: Photonic Resonance / AION Control • Session: {SESSION_ID}
            </p>

            <div className="mt-3 flex flex-wrap gap-2">
              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                Mode:{" "}
                <span className="text-slate-900">
                  {!wsUrl ? "SIM (local)" : feedFresh ? "RQC_LIVE" : "RQC_LIVE (NO_FEED)"}
                </span>
              </span>

              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                RQC WS: <span className="text-slate-900">{wsUrl || "—"}</span>
              </span>

              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                AION Demo: <span className="text-slate-900">{aionDemoBase || "—"}</span>
              </span>

              {running && (wsUrl || !wsUrl) && lastTelemetryAt > 0 && (
                <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                  Last telemetry:{" "}
                  <span className="text-slate-900">{Math.max(0, Math.floor(feedAgeMs / 1000))}s</span>
                </span>
              )}
            </div>

            {(lockId || lockThreshold != null || locked != null) && (
              <div className="mt-2 text-[10px] font-mono text-slate-500">
                lock_id={lockId || "—"} • locked={locked == null ? "—" : String(locked)} • threshold=
                {lockThreshold == null ? "—" : lockThreshold.toFixed(4)}
              </div>
            )}
          </div>

          <div className="flex flex-wrap gap-3 items-center">
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm">
              <span className={`w-2.5 h-2.5 rounded-full ${closureOk ? "bg-emerald-500" : "bg-slate-400"}`} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">
                πₛ Phase Closure:{" "}
                <span className={closureOk ? "text-emerald-600" : "text-slate-500"}>{closureLabel}</span>
              </span>
            </div>

            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm">
              <span className={`w-2.5 h-2.5 rounded-full ${pillDot}`} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">
                Status:{" "}
                <span
                  className={
                    displayStatus === "NO_FEED"
                      ? "text-slate-500"
                      : displayStatus === "CRITICAL_DRIFT"
                      ? "text-rose-600"
                      : displayStatus === "ALIGNING"
                      ? "text-blue-600"
                      : "text-emerald-600"
                  }
                >
                  {displayStatus}
                </span>
              </span>
            </div>

            <button
              onClick={() => setRunning((v) => !v)}
              className={`px-6 py-3 rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm border ${
                running
                  ? "bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100"
                  : "bg-slate-900 border-slate-900 text-white hover:bg-blue-600 hover:border-blue-600"
              }`}
            >
              {running ? "Stop Stream" : "Start Stream"}
            </button>

            <button
              onClick={injectEntropy}
              disabled={isInjecting}
              className="px-6 py-3 rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50"
              title="Inject via AION demo bridge if present; otherwise no-op for read-only feeds."
            >
              Inject Logic Entropy
            </button>

            <button
              onClick={() => {
                setRunning(false);
                reset();
              }}
              className="px-6 py-3 rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm border border-slate-200 bg-white hover:bg-slate-50"
            >
              Reset
            </button>
          </div>
        </div>

        {/* MAIN HUD GRID */}
        <div className="grid grid-cols-12 gap-8">
          <div className="col-span-12 lg:col-span-8 bg-white rounded-3xl border border-slate-200 shadow-sm p-8 relative overflow-hidden">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-10">
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">Φ (Awareness) vs. Entropy Evolution</h3>

              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Awareness (Φ)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-rose-400" />
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Entropy</span>
                </div>
              </div>
            </div>

            <div
              className={`h-64 flex items-end justify-between gap-1 relative border-b border-slate-100 pb-2 ${
                !barsEnabled ? "opacity-60" : ""
              }`}
            >
              {[...Array(40)].map((_, i) => {
                const base = Math.max(10, displayPhi * 80);
                const wiggle = barsEnabled ? Math.sin(i + Date.now() / 1000) * 10 : 0;
                const heightPct = `${base + wiggle}%`;
                const color = displayEntropy > 0.4 ? "#fb7185" : "#3b82f6";
                return (
                  <motion.div
                    key={i}
                    className="w-full rounded-t-sm"
                    animate={{ height: heightPct, backgroundColor: color }}
                    transition={barsEnabled ? { type: "spring", stiffness: 90, damping: 14 } : { duration: 0 }}
                  />
                );
              })}

              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-7xl md:text-8xl font-black text-slate-900/5 select-none uppercase tracking-tighter">
                  {displayStatus}
                </span>
              </div>
            </div>

            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
              {(manifoldSync ?? [0, 0, 0, 0]).map((val, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-between text-[10px] font-bold text-slate-400">
                    <span>MANIFOLD M-{i + 1}</span>
                    <span>{manifoldSync ? val.toFixed(1) : "—"}%</span>
                  </div>
                  <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-slate-900"
                      animate={{ width: `${manifoldSync ? val : 0}%` }}
                      transition={barsEnabled ? { duration: 0.25 } : { duration: 0 }}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 grid grid-cols-2 md:grid-cols-5 gap-4">
              <Tile label="ψ (Wave Presence)" value={psi != null ? psi.toFixed(5) : "—"} />
              <Tile label="κ (Curvature)" value={kappa != null ? kappa.toFixed(6) : "—"} />
              <Tile label="T (Temporal)" value={T != null ? T.toFixed(3) : "—"} />
              <Tile label="Entropy" value={entropy != null ? entropy.toFixed(3) : "—"} />
              <Tile label="Φ (Awareness)" value={phi != null ? phi.toFixed(4) : "—"} />
            </div>
          </div>

          <div className="col-span-12 lg:col-span-4 space-y-6">
            <div className="bg-slate-900 rounded-3xl p-8 text-white shadow-sm relative overflow-hidden">
              <div className="relative z-10">
                <span className="text-[10px] font-bold tracking-[0.2em] text-blue-300 uppercase">Awareness Scalar</span>
                <div className="mt-2 text-6xl font-semibold font-mono">Φ {phi != null ? phi.toFixed(4) : "—"}</div>
                <p className="text-slate-300 text-xs mt-4 leading-relaxed">
                  Φ is the self-measurement observable. If Φ is not explicitly emitted, it falls back to coherence (SQI/C).
                </p>

                <div className="mt-5 grid grid-cols-2 gap-3">
                  <div className="bg-white/10 border border-white/10 rounded-2xl p-4">
                    <div className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">Resonance Index</div>
                    <div className="mt-1 text-xl font-mono text-white">{resonanceIndex != null ? resonanceIndex.toFixed(3) : "—"}</div>
                  </div>
                  <div className="bg-white/10 border border-white/10 rounded-2xl p-4">
                    <div className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">Stability Index</div>
                    <div className="mt-1 text-xl font-mono text-white">{stabilityIndex != null ? stabilityIndex.toFixed(3) : "—"}</div>
                  </div>
                </div>
              </div>

              <motion.div
                className="absolute bottom-0 left-0 right-0 bg-blue-500/20"
                animate={{ height: `${(phi ?? 0) * 100}%` }}
                transition={{ duration: barsEnabled ? 0.25 : 0 }}
              />
            </div>

            <div className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm h-64 overflow-hidden">
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">AION Event Stream</h3>
              <div className="space-y-3">
                <AnimatePresence>
                  {(logs.length ? logs : [{ t: 0, msg: "Awaiting telemetry…", kind: "info" as const }]).map((log) => (
                    <motion.div
                      key={`${log.t}-${log.msg}`}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 10 }}
                      className={`text-[11px] font-mono p-2 rounded-lg border ${
                        log.kind === "warn" || log.kind === "bad"
                          ? "bg-rose-50 text-rose-700 border-rose-100"
                          : log.kind === "ok"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-100"
                          : "bg-slate-50 text-slate-700 border-slate-100"
                      }`}
                    >
                      {log.msg}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>

        <div className="text-[10px] text-slate-400 uppercase tracking-widest font-mono pt-2">
          Maintainer: Tessaris AI • Author: Kevin Robinson • Session: {SESSION_ID}
        </div>
      </div>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{label}</div>
      <div className="mt-1 text-xl font-mono text-slate-900">{value}</div>
    </div>
  );
}