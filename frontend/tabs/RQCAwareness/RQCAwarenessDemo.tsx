"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * RQC AWARENESS HORIZON — v0.7 (STRICT METRIC MAPPING + LOG THROTTLE)
 *
 * Fixes:
 *  1) DO NOT map ρ/rho to ψ. Ever. (That was the main bug making ψ==Φ==C)
 *  2) Coherence comes from C/coherence/SQI — not from rho.
 *  3) Event stream is throttled + telemetry line is UPDATED in-place (no flashing).
 *  4) ψ/κ/T stay "—" unless backend actually emits them.
 */

const SESSION_ID = "a99acc96-acde-48d5-9b6d-d2f434536d5b";
const STALE_MS = 2_500;

// log throttles
const TELEMETRY_LOG_EVERY_MS = 650; // don’t spam UI
const MAX_LOGS = 10;

// tiny epsilon to avoid pointless state churn
const EPS = 1e-6;

type Mode = "SIM" | "LIVE" | "LIVE_STALE";
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
 * STRICT extractor:
 * - ψ only from ψ/psi/presence keys (NOT rho)
 * - coherence from C/coherence/SQI keys
 * - rho only from ρ/rho keys
 * - entropy from E/entropy/Ī/Ibar keys
 * - Φ from Φ/phi keys, else fallback to coherence
 */
function extractMetrics(msg: any) {
  const m = msg?.metrics ?? msg?.state?.metrics ?? msg?.state ?? msg ?? {};
  const phiObj = msg?.phi ?? msg?.state?.phi ?? {};

  // ψ MUST NOT accept rho
  const psi = pickMetric(m, ["ψ", "psi", "wave_presence", "wavePresence", "presence"]);

  const kappa = pickMetric(m, ["κ", "kappa", "curvature"]);
  const T = pickMetric(m, ["T", "temporal", "temp", "time"]);

  // coherence from explicit coherence/SQI/C only
  const C =
    pickMetric(phiObj, ["Φ_coherence", "phi_coherence", "C", "coherence", "SQI", "sqi"]) ??
    pickMetric(m, ["Φ_coherence", "phi_coherence", "C", "coherence", "SQI", "sqi"]);

  // entropy from explicit entropy/Ibar only
  const entropy =
    pickMetric(phiObj, ["Φ_entropy", "phi_entropy", "E", "entropy", "Ī", "Ibar", "Ī", "iota"]) ??
    pickMetric(m, ["Φ_entropy", "phi_entropy", "E", "entropy", "Ī", "Ibar", "Ī", "iota"]);

  // Φ explicit else fallback to coherence
  const Phi =
    pickMetric(m, ["Φ", "phi"]) ?? pickMetric(phiObj, ["Φ", "phi"]) ?? (C != null ? C : null);

  // keep rho separate (never used as ψ or C)
  const rho = pickMetric(m, ["ρ", "rho"]) ?? pickMetric(phiObj, ["ρ", "rho"]);
  const Ibar =
    pickMetric(m, ["Ī", "Ibar", "Ī", "iota"]) ?? pickMetric(phiObj, ["Ī", "Ibar", "Ī", "iota"]);

  return { psi, kappa, T, Phi, C, entropy, rho, Ibar };
}

/**
 * If you set NEXT_PUBLIC_API_BASE to:
 *   https://...run.app/api
 * we derive origin as:
 *   https://...run.app
 */
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

  const [status, setStatus] = useState<"STABLE" | "ALIGNING" | "CRITICAL_DRIFT" | "NO_FEED">("NO_FEED");
  const [manifoldSync, setManifoldSync] = useState<number[] | null>(null);

  const [isInjecting, setIsInjecting] = useState(false);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [running, setRunning] = useState(false);

  const wsUrl = useMemo(() => pickRqcWsUrl(), []);
  const aionDemoBase = useMemo(() => pickAionDemoBase(), []);

  useEffect(() => console.log("[RQC] wsUrl =", wsUrl), [wsUrl]);

  const wsRef = useRef<WebSocket | null>(null);
  const [liveConnected, setLiveConnected] = useState(false);
  const [lastLiveAt, setLastLiveAt] = useState<number>(0);

  // refs to dampen rerenders + prevent log spam
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

  // update the top telemetry line instead of adding a new one each frame
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

  const mode: Mode = useMemo(() => {
    if (!wsUrl) return "SIM";
    if (!liveConnected) return "LIVE_STALE";
    const age = lastLiveAt ? Date.now() - lastLiveAt : Infinity;
    return age <= STALE_MS ? "LIVE" : "LIVE_STALE";
  }, [wsUrl, liveConnected, lastLiveAt]);

  const liveIsFresh = mode === "LIVE";

  const resonanceIndex = useMemo(() => (entropy == null ? null : clamp01(1 - entropy * 0.2)), [entropy]);
  const stabilityIndex = useMemo(() => (phi == null ? null : clamp01(phi * 0.95)), [phi]);

  const closureOk = useMemo(() => {
    if (phi == null || coherence == null || entropy == null) return false;
    return phi >= 0.92 && coherence >= 0.92 && entropy <= 0.08;
  }, [phi, coherence, entropy]);

  const setIfChanged = (key: keyof typeof lastValsRef.current, setter: (v: any) => void, next: number | null) => {
    const prev = lastValsRef.current[key];
    if (next == null) return;
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
    setStatus("NO_FEED");
    setIsInjecting(false);
    setLogs([]);
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

  // LIVE WS
  useEffect(() => {
    if (!running) return;
    if (!wsUrl) return;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setLiveConnected(true);
      addLog(`[RQC_LIVE] OPEN → ${wsUrl}`, "ok");
      try {
        ws.send(JSON.stringify({ type: "hello", client: "RQCAwarenessDemo", sessionId: SESSION_ID }));
      } catch {}
    };

    ws.onclose = (ev) => {
      setLiveConnected(false);
      addLog(`[RQC_LIVE] CLOSE code=${ev.code} reason=${ev.reason || "—"}`, "warn");
    };

    ws.onerror = (ev) => {
      setLiveConnected(false);
      console.error("WS error", ev);
      addLog(`[RQC_LIVE] ERROR (see console)`, "warn");
    };

    ws.onmessage = (evt) => {
      setLastLiveAt(Date.now());

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

        // Push only real values; otherwise leave as "—"
        setIfChanged("psi", setPsi, nm.psi != null ? clamp01(nm.psi) : null);
        setIfChanged("kappa", setKappa, nm.kappa != null ? clamp01(nm.kappa) : null);
        setIfChanged("T", setT, nm.T != null ? nm.T : null);

        const nextCoh = nm.C != null ? clamp01(nm.C) : null;
        const nextEntropy = nm.entropy != null ? clamp01(nm.entropy) : null;
        const nextPhi = nm.Phi != null ? clamp01(nm.Phi) : (nextCoh != null ? nextCoh : null);

        setIfChanged("coherence", setCoherence, nextCoh);
        setIfChanged("entropy", setEntropy, nextEntropy);
        setIfChanged("phi", setPhi, nextPhi);

        // Manifold = coherence proxy (only when coherence exists)
        if (nextCoh != null) {
          const base = clamp(nextCoh * 100, 0, 100);
          setManifoldSync([0, 1, 2, 3].map((i) => clamp(base + i * 0.2, 0, 100)));
        }

        // Status calculation requires both entropy + coherence
        const eForStatus = nextEntropy ?? lastValsRef.current.entropy ?? 0.5;
        const cForStatus = nextCoh ?? lastValsRef.current.coherence ?? 0.5;
        const s = computeStatus(eForStatus, cForStatus);
        setStatus(s);

        // Throttled telemetry UI line (prevents flashing)
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

          // Separate RQC line (shows SQI/coherence vs rho vs Ibar) — also throttled
          if (nm.rho != null || nm.Ibar != null || nm.C != null) {
            const rqcLine =
              `[RQC] SQI=${nextCoh != null ? nextCoh.toFixed(4) : "—"} ` +
              `ρ=${nm.rho != null ? clamp01(nm.rho).toFixed(4) : "—"} ` +
              `Ī=${nm.Ibar != null ? clamp01(nm.Ibar).toFixed(4) : "—"}`;
            // don’t spam; update/insert
            setLogs((prev) => {
              const next = [...prev];
              const idx = next.findIndex((x) => x.msg.startsWith("[RQC] "));
              const item = { t: Date.now(), msg: rqcLine, kind: "info" as const };
              if (idx >= 0) next[idx] = item;
              else next.unshift(item);
              return next.slice(0, MAX_LOGS);
            });
          }
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

      // Non-telemetry frames (rare) — keep short
      addLog(`[RQC_LIVE] RX ${raw.slice(0, 140)}`, "info");
    };

    return () => {
      try {
        ws.close();
      } catch {}
      wsRef.current = null;
      setLiveConnected(false);
    };
  }, [running, wsUrl]);

  // SIM MODE (only when no wsUrl)
  const entropyRef = useRef<number>(0.15);
  const phiRef = useRef<number>(0.64);
  const cohRef = useRef<number>(0.64);

  useEffect(() => {
    if (!running) return;
    if (wsUrl) return;

    addLog("[SIM] Running local awareness simulator (not live telemetry).", "warn");
    setStatus("ALIGNING");

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

      setStatus(computeStatus(entropyRef.current, cohRef.current));
    }, 200);

    return () => window.clearInterval(id);
  }, [running, wsUrl]);

  // stale → NO_FEED
  useEffect(() => {
    if (!running) return;
    if (!wsUrl) return;

    const t = window.setInterval(() => {
      const age = lastLiveAt ? Date.now() - lastLiveAt : Infinity;
      if (!liveConnected || age > STALE_MS) setStatus("NO_FEED");
    }, 300);

    return () => window.clearInterval(t);
  }, [running, wsUrl, liveConnected, lastLiveAt]);

  useEffect(() => {
    if (!closureOk) return;
    addLog("[πₛ Closure] Phase-locked loop converged → resonant thought completed.", "ok");
  }, [closureOk]);

  const barsEnabled = running && (!wsUrl || liveIsFresh);

  const displayPhi = phi ?? 0;
  const displayEntropy = entropy ?? 0;

  const pillDot =
    status === "NO_FEED"
      ? "bg-slate-400"
      : status === "CRITICAL_DRIFT"
      ? "bg-rose-500"
      : closureOk
      ? "bg-emerald-500"
      : "bg-blue-500";

  const closureLabel = closureOk ? "OK" : "LOCKED";

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
              RQC Awareness Horizon <span className="font-semibold">v0.7</span>
            </h1>
            <p className="mt-2 text-slate-500 font-mono text-xs uppercase tracking-widest">
              Substrate: Photonic Resonance / AION Control • Session: {SESSION_ID}
            </p>

            <div className="mt-3 flex flex-wrap gap-2">
              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                Mode: <span className="text-slate-900">{!wsUrl ? "SIM (local)" : liveIsFresh ? "RQC_LIVE" : "RQC_LIVE (NO_FEED)"}</span>
              </span>

              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                RQC WS: <span className="text-slate-900">{wsUrl || "—"}</span>
              </span>

              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                AION Demo: <span className="text-slate-900">{aionDemoBase}</span>
              </span>

              {wsUrl && lastLiveAt > 0 && (
                <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                  Last telemetry:{" "}
                  <span className="text-slate-900">{Math.max(0, Math.floor((Date.now() - lastLiveAt) / 1000))}s</span>
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-3 items-center">
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm">
              <span className={`w-2.5 h-2.5 rounded-full ${closureOk ? "bg-emerald-500" : "bg-slate-400"}`} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">
                πₛ Phase Closure: <span className={closureOk ? "text-emerald-600" : "text-slate-500"}>{closureLabel}</span>
              </span>
            </div>

            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm">
              <span className={`w-2.5 h-2.5 rounded-full ${pillDot}`} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">
                Status:{" "}
                <span
                  className={
                    status === "NO_FEED"
                      ? "text-slate-500"
                      : status === "CRITICAL_DRIFT"
                      ? "text-rose-600"
                      : status === "ALIGNING"
                      ? "text-blue-600"
                      : "text-emerald-600"
                  }
                >
                  {status}
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

            <div className={`h-64 flex items-end justify-between gap-1 relative border-b border-slate-100 pb-2 ${!barsEnabled ? "opacity-60" : ""}`}>
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
                <span className="text-7xl md:text-8xl font-black text-slate-900/5 select-none uppercase tracking-tighter">{status}</span>
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