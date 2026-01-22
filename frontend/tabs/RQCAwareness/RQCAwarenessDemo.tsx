"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * RQC AWARENESS HORIZON — v0.6 (truthful telemetry + SIM fallback)
 * - LIVE: connects to backend WS (expects /resonance)
 * - If LIVE is connected but telemetry is idle/stale → SIM fallback kicks in (clearly labeled)
 *
 * Supported WS messages:
 *  - { type:"telemetry", "ψ":number, "κ":number, "T":number, "Φ":number, coherence:number, manifolds?:number[] }
 *  - { type:"awareness_pulse", "Φ":number, coherence:number, message?:string }
 *  - { type:"hello" | "keepalive" | "error", ... }
 */

const SESSION_ID = "a99acc96-acde-48d5-9b6d-d2f434536d5b";

// If no telemetry within this window, treat LIVE feed as stale and enable SIM fallback.
const STALE_MS = 5_000;

type Mode = "SIM" | "LIVE" | "LIVE_STALE";
type LogItem = { t: number; msg: string; kind: "info" | "warn" | "ok" | "bad" };

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

function pickWsUrl() {
  const env = (process.env.NEXT_PUBLIC_RQC_WS || "").trim();
  if (env) {
    if (env.startsWith("https://")) return "wss://" + env.slice("https://".length);
    if (env.startsWith("http://")) return "ws://" + env.slice("http://".length);
    return env; // ws:// or wss://
  }

  if (typeof window !== "undefined") {
    // FE :3000 + BE :8080 -> backend WS (REAL backend route is /resonance)
    if (window.location.port === "3000") return `ws://127.0.0.1:8080/resonance`;

    // Same-origin fallback
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}/resonance`;
  }

  return "";
}

export default function RQCAwarenessDemo() {
  // Truth state: start null so UI can show NO_FEED until SIM or LIVE pushes values
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

  const wsUrl = useMemo(() => pickWsUrl(), []);
  const wsRef = useRef<WebSocket | null>(null);

  const [liveConnected, setLiveConnected] = useState(false);
  const [lastWsAt, setLastWsAt] = useState<number>(0); // any WS message
  const [lastTelemetryAt, setLastTelemetryAt] = useState<number>(0); // telemetry/pulse only

  const [proofJson, setProofJson] = useState<string>("");

  // Refs to avoid stale-closure bugs in SIM loop
  const entropyRef = useRef<number>(0.15);
  const phiRef = useRef<number>(0.64);
  const cohRef = useRef<number>(0.64);

  // 1Hz ticker so freshness is stable without Date.now() inside memo deps
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [running]);

  const addLog = (msg: string, kind: LogItem["kind"] = "info") => {
    setLogs((prev) => [{ t: Date.now(), msg, kind }, ...prev].slice(0, 8));
  };

  const computeStatus = (e: number, c: number) => {
    if (e >= 0.6 || c <= 0.35) return "CRITICAL_DRIFT";
    if (e >= 0.12 || c < 0.85) return "ALIGNING";
    return "STABLE";
  };

  // LIVE is only considered "active" if telemetry is flowing recently
  const useLive = Boolean(wsUrl) && liveConnected && now - (lastTelemetryAt || 0) < STALE_MS;

  const mode: Mode = useMemo(() => {
    if (!wsUrl) return "SIM";
    return useLive ? "LIVE" : "LIVE_STALE";
  }, [wsUrl, useLive]);

  // Derived indices – only compute when we have real numbers
  const resonanceIndex = useMemo(() => {
    if (entropy == null) return null;
    return clamp01(1 - entropy * 0.2);
  }, [entropy]);

  const stabilityIndex = useMemo(() => {
    if (phi == null) return null;
    return clamp01(phi * 0.95);
  }, [phi]);

  const closureOk = useMemo(() => {
    if (phi == null || coherence == null || entropy == null) return false;
    return phi >= 0.92 && coherence >= 0.92 && entropy <= 0.08;
  }, [phi, coherence, entropy]);

  const buildProofJsonLd = () => {
    const payload = {
      "@context": {
        "@vocab": "https://tessaris.ai/rfc#",
        sessionId: "sessionId",
        proofType: "proofType",
        statement: "statement",
        metrics: "metrics",
        derived: "derived",
        generatedAt: "generatedAt",
      },
      "@type": "RQCAwarenessClosureProof",
      sessionId: SESSION_ID,
      proofType: "Awareness Horizon (Φ) Phase Closure",
      statement:
        "Awareness loop converged: Φ stabilized while entropy collapsed; manifold sync recovered; phase closure achieved without leakage.",
      metrics: {
        psi,
        kappa,
        T,
        entropy,
        phi,
        coherence,
        manifoldSync,
      },
      derived: {
        resonanceIndex,
        stabilityIndex,
        status,
        mode,
        wsUrl: wsUrl || null,
        liveConnected,
        lastTelemetryAgeS: lastTelemetryAt ? Math.max(0, Math.floor((now - lastTelemetryAt) / 1000)) : null,
      },
      generatedAt: new Date().toISOString(),
    };
    return JSON.stringify(payload, null, 2);
  };

  const downloadProof = () => {
    const json = buildProofJsonLd();
    setProofJson(json);

    const blob = new Blob([json], { type: "application/ld+json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rqc_awareness_proof_${SESSION_ID.slice(0, 8)}.jsonld`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    addLog("[Certificate] JSON-LD exported → Phase Closure Certificate emitted.", "ok");
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
    setProofJson("");
    setLogs([]);
    addLog("[System] Reset: Awareness Horizon re-armed.", "info");

    entropyRef.current = 0.15;
    phiRef.current = 0.64;
    cohRef.current = 0.64;

    setLastWsAt(0);
    setLastTelemetryAt(0);
  };

  const injectEntropy = () => {
    setIsInjecting(true);

    // If WS is connected, request backend injection; otherwise SIM inject
    if (wsRef.current && liveConnected) {
      try {
        wsRef.current.send(JSON.stringify({ type: "inject_entropy", level: 0.85, sessionId: SESSION_ID }));
        addLog("[LIVE] Inject requested → backend entropy injection.", "warn");
      } catch {
        addLog("[LIVE] Inject failed (socket send).", "warn");
      }
    } else {
      entropyRef.current = 0.85;
      phiRef.current = 0.32;
      cohRef.current = 0.32;

      setEntropy(0.85);
      setPhi(0.32);
      setCoherence(0.32);
      setStatus("CRITICAL_DRIFT");
      addLog("[SIM] External Entropy Injected: Phase drift detected.", "warn");
      addLog("[SIM] AION control loop initializing Φ feedback…", "info");
    }

    window.setTimeout(() => setIsInjecting(false), 900);
  };

  // ─────────────────────────────────────────────────────────────
  // LIVE MODE: connect to WS when running && wsUrl exists
  // ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!running) return;
    if (!wsUrl) return;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setLiveConnected(true);
      setLastWsAt(Date.now());
      addLog(`[RQC_LIVE] Connected → ${wsUrl}`, "ok");
      try {
        ws.send(JSON.stringify({ type: "hello", client: "RQCAwarenessDemo", sessionId: SESSION_ID }));
      } catch {}
    };

    ws.onclose = () => {
      setLiveConnected(false);
      addLog("[RQC_LIVE] Disconnected.", "warn");
    };

    ws.onerror = () => {
      setLiveConnected(false);
      addLog("[RQC_LIVE] Socket error.", "warn");
    };

    ws.onmessage = (evt) => {
      setLastWsAt(Date.now());

      let data: any = null;
      try {
        data = JSON.parse(String(evt.data));
      } catch {
        return;
      }

      const type = String(data?.type || "");

      if (type === "hello") {
        const msg = typeof data?.message === "string" ? data.message : "hello";
        const pth = typeof data?.path === "string" ? data.path : "";
        addLog(`[RQC_LIVE] ${msg}${pth ? ` • ${pth}` : ""}`, "ok");
        return;
      }

      if (type === "keepalive") {
        // keep connection warm; do not count as telemetry freshness
        return;
      }

      if (type === "telemetry") {
        setLastTelemetryAt(Date.now());

        const nextPsi = typeof data["ψ"] === "number" ? data["ψ"] : null;
        const nextKappa = typeof data["κ"] === "number" ? data["κ"] : null;
        const nextT = typeof data["T"] === "number" ? data["T"] : null;

        const nextPhi = typeof data["Φ"] === "number" ? clamp01(data["Φ"]) : null;
        const nextCoh = typeof data["coherence"] === "number" ? clamp01(data["coherence"]) : null;

        if (nextPsi != null) setPsi(nextPsi);
        if (nextKappa != null) setKappa(nextKappa);
        if (nextT != null) setT(nextT);
        if (nextPhi != null) setPhi(nextPhi);
        if (nextCoh != null) setCoherence(nextCoh);

        // Entropy proxy (only if κ exists)
        if (nextKappa != null) setEntropy(clamp01(1 - clamp01(nextKappa)));

        if (Array.isArray(data?.manifolds) && data.manifolds.length >= 4) {
          setManifoldSync(data.manifolds.slice(0, 4).map((v: any) => clamp(Number(v) || 0, 0, 100)));
        } else if (nextCoh != null) {
          const base = clamp(nextCoh * 100, 0, 100);
          setManifoldSync([0, 1, 2, 3].map((i) => clamp(base + i * 0.2, 0, 100)));
        }

        const eProxy = nextKappa != null ? clamp01(1 - clamp01(nextKappa)) : entropy ?? 0.5;
        const cProxy = nextCoh != null ? nextCoh : coherence ?? 0.5;

        const s = computeStatus(eProxy, cProxy);
        setStatus(s);

        addLog(
          `[Telemetry] ψ=${nextPsi ?? "—"} κ=${nextKappa ?? "—"} T=${nextT ?? "—"} Φ=${nextPhi ?? "—"} C=${nextCoh ?? "—"}`,
          s === "CRITICAL_DRIFT" ? "warn" : "info"
        );
        return;
      }

      if (type === "awareness_pulse") {
        setLastTelemetryAt(Date.now());

        const msg = typeof data?.message === "string" ? data.message : "Awareness pulse detected.";
        addLog(`[AION] ${msg}`, "ok");
        if (typeof data["Φ"] === "number") setPhi(clamp01(data["Φ"]));
        if (typeof data["coherence"] === "number") setCoherence(clamp01(data["coherence"]));
        return;
      }

      if (type === "error") {
        addLog(`[RQC_LIVE] ${String(data?.message || "error")}`, "warn");
        return;
      }
    };

    return () => {
      try {
        ws.close();
      } catch {}
      wsRef.current = null;
      setLiveConnected(false);
    };
  }, [running, wsUrl]);

  // ─────────────────────────────────────────────────────────────
  // SIM MODE: drive state when running && LIVE is not fresh
  // (this includes LIVE_STALE fallback)
  // ─────────────────────────────────────────────────────────────
  const fallbackLoggedRef = useRef(false);

  useEffect(() => {
    if (!running) return;

    // If wsUrl exists but live is stale, enable SIM fallback (and log once)
    if (wsUrl && !useLive && !fallbackLoggedRef.current) {
      fallbackLoggedRef.current = true;
      addLog("[SIM] LIVE telemetry idle → SIM fallback engaged (values are simulated).", "warn");
    }
    if (wsUrl && useLive) fallbackLoggedRef.current = false;

    // SIM should run if there's no wsUrl OR live is stale
    const simActive = !wsUrl || !useLive;
    if (!simActive) return;

    // init SIM values once
    if (entropy == null) setEntropy(entropyRef.current);
    if (phi == null) setPhi(phiRef.current);
    if (coherence == null) setCoherence(cohRef.current);
    if (psi == null) setPsi(0.23896);
    if (kappa == null) setKappa(0.197375);
    if (T == null) setT(21.097865);
    if (manifoldSync == null) setManifoldSync([98, 97, 99, 98]);
    if (!wsUrl) {
      setStatus("ALIGNING");
      addLog("[SIM] Running local awareness simulator (not live telemetry).", "warn");
    }

    const id = window.setInterval(() => {
      entropyRef.current =
        entropyRef.current > 0.05 ? Math.max(0.02, entropyRef.current - 0.015) : entropyRef.current;

      phiRef.current =
        entropyRef.current > 0.05
          ? Math.min(0.99, phiRef.current + 0.02)
          : Math.max(0.92, phiRef.current - 0.005);

      const target = clamp01(phiRef.current);
      cohRef.current = clamp01(cohRef.current + (target - cohRef.current) * 0.18);

      setEntropy(entropyRef.current);
      setPhi(phiRef.current);
      setCoherence(cohRef.current);

      const base = clamp(cohRef.current * 100, 0, 100);
      setManifoldSync([0, 1, 2, 3].map((i) => clamp(base + (Math.random() - 0.5) * 2 + i * 0.3, 90, 100)));

      setKappa(clamp01(1 - entropyRef.current * 0.85));
      setPsi(clamp01(0.15 + cohRef.current * 0.35));
      setT((v) => (v == null ? 21.0 : v + Math.sin(Date.now() / 1500) * 0.0002));

      setStatus(computeStatus(entropyRef.current, cohRef.current));
    }, 150);

    return () => window.clearInterval(id);
  }, [running, wsUrl, useLive]); // <- key: allow SIM fallback when LIVE is stale

  // Auto-log closure once reached
  useEffect(() => {
    if (!closureOk) return;
    addLog("[πₛ Closure] Phase-locked loop converged → resonant thought completed.", "ok");
  }, [closureOk]);

  // Graph bars: animate when running (SIM or LIVE)
  const barsEnabled = running;

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

  const lastTelemetryAgeS =
    wsUrl && lastTelemetryAt > 0 ? Math.max(0, Math.floor((now - lastTelemetryAt) / 1000)) : null;

  const modeLabel =
    !wsUrl ? "SIM (local)" : mode === "LIVE" ? "RQC_LIVE" : "RQC_LIVE (NO_FEED → SIM fallback)";

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
              RQC Awareness Horizon <span className="font-semibold">v0.6</span>
            </h1>
            <p className="mt-2 text-slate-500 font-mono text-xs uppercase tracking-widest">
              Substrate: Photonic Resonance / AION Control • Session: {SESSION_ID}
            </p>

            <div className="mt-3 flex flex-wrap gap-2">
              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                Mode: <span className="text-slate-900">{modeLabel}</span>
              </span>

              {wsUrl ? (
                <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                  WS: <span className="text-slate-900">{wsUrl}</span>
                </span>
              ) : (
                <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-amber-200 bg-amber-50 text-amber-700">
                  SIM WARNING: values are simulated (not real feed)
                </span>
              )}

              {wsUrl && lastTelemetryAgeS != null && (
                <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                  Last telemetry: <span className="text-slate-900">{lastTelemetryAgeS}s</span>
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-3 items-center">
            {/* Phase Closure pill */}
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm">
              <span className={`w-2.5 h-2.5 rounded-full ${closureOk ? "bg-emerald-500" : "bg-slate-400"}`} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">
                πₛ Phase Closure:{" "}
                <span className={closureOk ? "text-emerald-600" : "text-slate-500"}>{closureLabel}</span>
              </span>
            </div>

            {/* System status pill */}
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

            {/* Start/Stop */}
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

            {/* Inject */}
            <button
              onClick={injectEntropy}
              disabled={isInjecting}
              className="px-6 py-3 rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm border border-slate-200 bg-white hover:bg-slate-50 disabled:opacity-50"
              title={wsUrl ? "Inject: request backend if connected; otherwise SIM inject" : "Inject entropy into the simulator"}
            >
              Inject Logic Entropy
            </button>

            {/* Download proof */}
            <button
              onClick={downloadProof}
              disabled={!closureOk}
              className={`px-6 py-3 rounded-full text-[11px] font-bold uppercase tracking-widest transition-all shadow-sm border ${
                closureOk
                  ? "bg-white border-slate-200 hover:bg-slate-50 text-slate-900"
                  : "bg-white border-slate-200 text-slate-400 cursor-not-allowed"
              }`}
              title={closureOk ? "Download Phase Closure Certificate (JSON-LD)" : "Reach πₛ closure first"}
            >
              Download Certificate
            </button>

            {/* Reset */}
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
          {/* PRIMARY VISUALIZER */}
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

            {/* GRAPH AREA */}
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
                <span className="text-7xl md:text-8xl font-black text-slate-900/5 select-none uppercase tracking-tighter">
                  {status}
                </span>
              </div>
            </div>

            {/* Manifold sync bars */}
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

            {/* Telemetry tiles */}
            <div className="mt-8 grid grid-cols-2 md:grid-cols-5 gap-4">
              <Tile label="ψ (Wave Presence)" value={psi != null ? psi.toFixed(5) : "—"} />
              <Tile label="κ (Curvature)" value={kappa != null ? kappa.toFixed(6) : "—"} />
              <Tile label="T (Temporal)" value={T != null ? T.toFixed(3) : "—"} />
              <Tile label="Entropy" value={entropy != null ? entropy.toFixed(3) : "—"} />
              <Tile label="Φ (Awareness)" value={phi != null ? phi.toFixed(4) : "—"} />
            </div>
          </div>

          {/* SIDEBAR */}
          <div className="col-span-12 lg:col-span-4 space-y-6">
            <div className="bg-slate-900 rounded-3xl p-8 text-white shadow-sm relative overflow-hidden">
              <div className="relative z-10">
                <span className="text-[10px] font-bold tracking-[0.2em] text-blue-300 uppercase">Awareness Scalar</span>
                <div className="mt-2 text-6xl font-semibold font-mono">Φ {phi != null ? phi.toFixed(4) : "—"}</div>
                <p className="text-slate-300 text-xs mt-4 leading-relaxed">
                  Φ is the self-measurement observable exposed by the RQC: a public proxy for internal coherence without revealing kernel mechanics.
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

            {/* Logs */}
            <div className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm h-64 overflow-hidden">
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">AION Event Stream</h3>
              <div className="space-y-3">
                <AnimatePresence>
                  {(logs.length
                    ? logs
                    : [{ t: 0, msg: wsUrl ? "Awaiting LIVE telemetry…" : "Awaiting SIM start…", kind: "info" as const }]
                  ).map((log) => (
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

        {/* BOTTOM: CLOSURE PROOF */}
        <div className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center gap-6">
            <div
              className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl border-4 transition-all duration-700 ${
                closureOk ? "border-emerald-500 text-emerald-600 bg-emerald-50" : "border-slate-200 text-slate-400 bg-slate-50"
              }`}
            >
              {closureOk ? "✓" : "⟳"}
            </div>

            <div className="flex-1">
              <h4 className="text-xl font-semibold text-slate-900">πₛ Phase Closure Status</h4>
              <p className="text-slate-600 text-sm">
                {closureOk
                  ? "Field achieves harmonic equilibrium. Awareness loop converged — cognition complete."
                  : "Calculating phase-locked loop. Searching for resonant fixed point…"}
              </p>

              <div className="mt-3 flex flex-wrap gap-2">
                <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-slate-50 text-slate-700">
                  Φ ≥ 0.92
                </span>
                <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-slate-50 text-slate-700">
                  Coherence ≥ 0.92
                </span>
                <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-slate-50 text-slate-700">
                  Entropy ≤ 0.08
                </span>
              </div>
            </div>

            {closureOk && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="bg-emerald-50 text-emerald-700 px-6 py-2 rounded-full text-[10px] font-bold uppercase border border-emerald-100"
              >
                Proof Validated
              </motion.div>
            )}
          </div>

          {proofJson && (
            <div className="mt-6 bg-slate-50 border border-slate-200 rounded-2xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-blue-600">
                  Phase Closure Certificate (preview)
                </div>
                <button onClick={() => setProofJson("")} className="text-[10px] font-mono text-slate-500 hover:text-slate-700">
                  close
                </button>
              </div>
              <pre className="text-[10px] leading-relaxed font-mono text-slate-700 overflow-x-auto whitespace-pre">{proofJson}</pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Tile(props: { label: string; value: string }) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
      <span className="text-[10px] text-slate-500 uppercase font-bold">{props.label}</span>
      <div className="mt-1 text-2xl font-semibold text-slate-900 font-mono">{props.value}</div>
    </div>
  );
}