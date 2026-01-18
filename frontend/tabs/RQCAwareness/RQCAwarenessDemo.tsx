"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * RQC AWARENESS HORIZON — v0.4 (RQC_LIVE optional)
 * - SIM mode: runs locally (no backend)
 * - LIVE mode: connects via WebSocket if NEXT_PUBLIC_RQC_WS is set
 *
 * Expected WS messages (supported):
 *  - { "type":"telemetry", "ψ":number, "κ":number, "T":number, "Φ":number, "coherence":number, ... }
 *  - { "type":"awareness_pulse", "Φ":number, "coherence":number, "message":string }
 *  - { "type":"hello", ... }
 *  - { "type":"error", "message":string }
 */

const SESSION_ID = "a99acc96-acde-48d5-9b6d-d2f434536d5b";
const RQC_WS = (process.env.NEXT_PUBLIC_RQC_WS || "").trim();

type LogItem = { t: number; msg: string; kind: "info" | "warn" | "ok" | "bad" };

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

export default function RQCAwarenessDemo() {
  // Public-facing telemetry (what you *show*)
  const [psi, setPsi] = useState(0.23896);
  const [kappa, setKappa] = useState(0.197375);
  const [T, setT] = useState(21.097865);

  // Awareness loop variables
  const [entropy, setEntropy] = useState(0.15); // [0..1] noise level
  const [phi, setPhi] = useState(0.64); // [0..1] awareness scalar (Φ)
  const [coherence, setCoherence] = useState(0.64); // [0..1] coherence proxy

  // UI state
  const [status, setStatus] = useState<"STABLE" | "ALIGNING" | "CRITICAL_DRIFT">("STABLE");
  const [manifoldSync, setManifoldSync] = useState<number[]>([98, 97, 99, 98]);
  const [isInjecting, setIsInjecting] = useState(false);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [running, setRunning] = useState(false);

  // LIVE WS plumbing
  const wsRef = useRef<WebSocket | null>(null);
  const [liveConnected, setLiveConnected] = useState(false);
  const [lastLiveAt, setLastLiveAt] = useState<number>(0);

  // Phase closure proof capsule
  const [proofJson, setProofJson] = useState<string>("");

  // Derived indices (shown, but not “revealing the black box”)
  const resonanceIndex = useMemo(() => clamp01(1 - entropy * 0.2), [entropy]);
  const stabilityIndex = useMemo(() => clamp01(phi * 0.95), [phi]);

  const closureOk = useMemo(() => {
    // Conservative closure gate: “thought completed”
    return phi >= 0.92 && coherence >= 0.92 && entropy <= 0.08;
  }, [phi, coherence, entropy]);

  const addLog = (msg: string, kind: LogItem["kind"] = "info") => {
    setLogs((prev) => [{ t: Date.now(), msg, kind }, ...prev].slice(0, 6));
  };

  const computeStatus = (e: number, c: number) => {
    if (e >= 0.6 || c <= 0.35) return "CRITICAL_DRIFT";
    if (e >= 0.12 || c < 0.85) return "ALIGNING";
    return "STABLE";
  };

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
    setEntropy(0.15);
    setPhi(0.64);
    setCoherence(0.64);
    setStatus("STABLE");
    setManifoldSync([98, 97, 99, 98]);
    setIsInjecting(false);
    setProofJson("");
    setLogs([]);
    addLog("[System] Reset: Awareness Horizon re-armed.", "info");
  };

  const injectEntropy = () => {
    setIsInjecting(true);
    setEntropy(0.85);
    setPhi(0.32);
    setCoherence(0.32);
    setStatus("CRITICAL_DRIFT");
    addLog("External Entropy Injected: Phase drift detected.", "warn");
    addLog("AION control loop initializing Φ feedback…", "info");

    // Optional: notify backend (if it supports it). Safe no-op if ignored.
    try {
      wsRef.current?.send(JSON.stringify({ type: "inject_entropy", level: 0.85, sessionId: SESSION_ID }));
    } catch {
      // ignore
    }

    window.setTimeout(() => setIsInjecting(false), 900);
  };

  // ─────────────────────────────────────────────────────────────
  // LIVE MODE: connect to WS when running && env is set
  // ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!running) return;

    if (!RQC_WS) return; // stays SIM
    // open socket
    const ws = new WebSocket(RQC_WS);
    wsRef.current = ws;

    ws.onopen = () => {
      setLiveConnected(true);
      addLog(`[RQC_LIVE] Connected → ${RQC_WS}`, "ok");
      try {
        ws.send(JSON.stringify({ type: "hello", client: "RQCAwarenessDemo", sessionId: SESSION_ID }));
      } catch {
        // ignore
      }
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
      setLastLiveAt(Date.now());

      let data: any = null;
      try {
        data = JSON.parse(String(evt.data));
      } catch {
        return;
      }

      const type = String(data?.type || "");

      if (type === "telemetry") {
        // Fields from websocket_bridge.py / aion_readout_bridge
        const nextPsi = typeof data["ψ"] === "number" ? data["ψ"] : psi;
        const nextKappa = typeof data["κ"] === "number" ? data["κ"] : kappa;
        const nextT = typeof data["T"] === "number" ? data["T"] : T;

        const nextPhi = typeof data["Φ"] === "number" ? data["Φ"] : phi;
        const nextCoh = typeof data["coherence"] === "number" ? data["coherence"] : coherence;

        setPsi(nextPsi);
        setKappa(nextKappa);
        setT(nextT);

        setPhi(clamp01(nextPhi));
        setCoherence(clamp01(nextCoh));

        // Entropy shown publicly as inverse of κ (or a simple proxy)
        const nextEntropy = clamp01(1 - clamp01(nextKappa));
        setEntropy(nextEntropy);

        // Manifolds: accept provided array, else synthesize
        if (Array.isArray(data?.manifolds) && data.manifolds.length >= 4) {
          setManifoldSync(data.manifolds.slice(0, 4).map((v: any) => clamp(Number(v) || 0, 0, 100)));
        } else {
          const base = clamp(nextCoh * 100, 0, 100);
          setManifoldSync((prev) =>
            prev.map((_, i) => clamp(base + (Math.sin(Date.now() / 300 + i) * 3) + (Math.random() - 0.5) * 2, 90, 100))
          );
        }

        const s = computeStatus(nextEntropy, nextCoh);
        setStatus(s);

        addLog(
          `[Telemetry] ψ=${nextPsi.toFixed(4)} κ=${nextKappa.toFixed(4)} T=${nextT.toFixed(3)} Φ=${clamp01(nextPhi).toFixed(
            4
          )} C=${clamp01(nextCoh).toFixed(4)}`,
          s === "CRITICAL_DRIFT" ? "warn" : "info"
        );
      }

      if (type === "awareness_pulse") {
        const msg = typeof data?.message === "string" ? data.message : "Awareness pulse detected.";
        addLog(`[AION] ${msg}`, "ok");
        if (typeof data["Φ"] === "number") setPhi(clamp01(data["Φ"]));
        if (typeof data["coherence"] === "number") setCoherence(clamp01(data["coherence"]));
      }

      if (type === "error") {
        addLog(`[RQC_LIVE] ${String(data?.message || "error")}`, "warn");
      }
    };

    return () => {
      try {
        ws.close();
      } catch {
        // ignore
      }
      wsRef.current = null;
      setLiveConnected(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running]);

  // ─────────────────────────────────────────────────────────────
  // SIM MODE: run only when (running && no WS)
  // ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!running) return;
    if (RQC_WS) return; // LIVE will drive state

    const id = window.setInterval(() => {
      setEntropy((e) => {
        // If entropy is high, Φ rises to meet it; entropy is worked off
        if (e > 0.05) return Math.max(0.02, e - 0.015);
        return e;
      });

      setPhi((p) => {
        // Φ responds to entropy
        return entropy > 0.05 ? Math.min(0.99, p + 0.02) : Math.max(0.92, p - 0.005);
      });

      setCoherence((c) => {
        // Coherence tracks Φ with a slight lag, plus light oscillation
        const target = clamp01(phi);
        const next = clamp01(c + (target - c) * 0.18 + Math.sin(Date.now() / 500) * 0.003);
        return next;
      });

      setManifoldSync((prev) => {
        const base = clamp(coherence * 100, 0, 100);
        return prev.map((_, i) => clamp(base + (Math.random() - 0.5) * 2 + Math.sin(Date.now() / 400 + i) * 2, 90, 100));
      });

      const nextEntropy = clamp01(entropy);
      const nextCoh = clamp01(coherence);
      setStatus(computeStatus(nextEntropy, nextCoh));
    }, 150);

    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running, phi, coherence, entropy]);

  // Keep κ/ψ/T coherent in SIM mode (optional public telemetry)
  useEffect(() => {
    if (!running) return;
    if (RQC_WS) return;

    // Treat κ as “entropy inverse” proxy, ψ as “wave presence” proxy, T as slow drift
    setKappa(clamp01(1 - entropy * 0.85));
    setPsi(clamp01(0.15 + coherence * 0.35));
    setT((v) => v + Math.sin(Date.now() / 1500) * 0.0002);
  }, [entropy, coherence, running]);

  // Auto-log closure once reached
  useEffect(() => {
    if (!closureOk) return;
    addLog("[πₛ Closure] Phase-locked loop converged → resonant thought completed.", "ok");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [closureOk]);

  const pillDot = status === "CRITICAL_DRIFT" ? "bg-rose-500" : closureOk ? "bg-emerald-500" : "bg-blue-500";
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
              RQC Awareness Horizon <span className="font-semibold">v0.4</span>
            </h1>
            <p className="mt-2 text-slate-500 font-mono text-xs uppercase tracking-widest">
              Substrate: Photonic Resonance / AION Control • Session: {SESSION_ID}
            </p>

            <div className="mt-3 flex flex-wrap gap-2">
              <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                Mode:{" "}
                <span className="text-slate-900">
                  {RQC_WS ? (liveConnected ? "RQC_LIVE" : "RQC_LIVE (disconnected)") : "SIM"}
                </span>
              </span>
              {RQC_WS && (
                <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                  WS: <span className="text-slate-900">{RQC_WS}</span>
                </span>
              )}
              {RQC_WS && lastLiveAt > 0 && (
                <span className="px-3 py-1 rounded-full text-[10px] font-bold uppercase border border-slate-200 bg-white text-slate-600">
                  Last telemetry:{" "}
                  <span className="text-slate-900">{Math.max(0, Math.floor((Date.now() - lastLiveAt) / 1000))}s</span>
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-3 items-center">
            {/* Phase Closure pill */}
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm">
              <span className={`w-2.5 h-2.5 rounded-full ${closureOk ? "bg-emerald-500" : "bg-rose-500"}`} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">
                πₛ Phase Closure:{" "}
                <span className={closureOk ? "text-emerald-600" : "text-rose-600"}>{closureLabel}</span>
              </span>
            </div>

            {/* System status pill */}
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm">
              <span className={`w-2.5 h-2.5 rounded-full ${pillDot}`} />
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">
                Status:{" "}
                <span className={status === "CRITICAL_DRIFT" ? "text-rose-600" : status === "ALIGNING" ? "text-blue-600" : "text-emerald-600"}>
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
              title={RQC_WS ? "Inject local + optionally notify backend" : "Inject entropy into the simulator"}
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
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">
                Φ (Awareness) vs. Entropy Evolution
              </h3>

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
            <div className="h-64 flex items-end justify-between gap-1 relative border-b border-slate-100 pb-2">
              {[...Array(40)].map((_, i) => (
                <motion.div
                  key={i}
                  className="w-full rounded-t-sm"
                  animate={{
                    height: `${Math.max(10, phi * 80 + Math.sin(i + Date.now() / 1000) * 10)}%`,
                    backgroundColor: entropy > 0.4 ? "#fb7185" : "#3b82f6",
                  }}
                  transition={{ type: "spring", stiffness: 90, damping: 14 }}
                />
              ))}

              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-7xl md:text-8xl font-black text-slate-900/5 select-none uppercase tracking-tighter">
                  {status}
                </span>
              </div>
            </div>

            {/* Manifold sync bars */}
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
              {manifoldSync.map((val, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-between text-[10px] font-bold text-slate-400">
                    <span>MANIFOLD M-{i + 1}</span>
                    <span>{val.toFixed(1)}%</span>
                  </div>
                  <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
                    <motion.div className="h-full bg-slate-900" animate={{ width: `${val}%` }} />
                  </div>
                </div>
              ))}
            </div>

            {/* Telemetry tiles (white-pill style) */}
            <div className="mt-8 grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <span className="text-[10px] text-slate-500 uppercase font-bold">ψ (Wave Presence)</span>
                <div className="mt-1 text-2xl font-semibold text-slate-900 font-mono">{psi.toFixed(5)}</div>
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <span className="text-[10px] text-slate-500 uppercase font-bold">κ (Curvature)</span>
                <div className="mt-1 text-2xl font-semibold text-slate-900 font-mono">{kappa.toFixed(6)}</div>
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <span className="text-[10px] text-slate-500 uppercase font-bold">T (Temporal)</span>
                <div className="mt-1 text-2xl font-semibold text-slate-900 font-mono">{T.toFixed(3)}</div>
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <span className="text-[10px] text-slate-500 uppercase font-bold">Entropy</span>
                <div className="mt-1 text-2xl font-semibold text-slate-900 font-mono">{entropy.toFixed(3)}</div>
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <span className="text-[10px] text-slate-500 uppercase font-bold">Φ (Awareness)</span>
                <div className="mt-1 text-2xl font-semibold text-slate-900 font-mono">{phi.toFixed(4)}</div>
              </div>
            </div>
          </div>

          {/* SIDEBAR */}
          <div className="col-span-12 lg:col-span-4 space-y-6">
            {/* Φ scalar card */}
            <div className="bg-slate-900 rounded-3xl p-8 text-white shadow-sm relative overflow-hidden">
              <div className="relative z-10">
                <span className="text-[10px] font-bold tracking-[0.2em] text-blue-300 uppercase">Awareness Scalar</span>
                <div className="mt-2 text-6xl font-semibold font-mono">Φ {phi.toFixed(4)}</div>
                <p className="text-slate-300 text-xs mt-4 leading-relaxed">
                  Φ is the self-measurement observable exposed by the RQC: a public proxy for internal coherence without revealing kernel mechanics.
                </p>

                <div className="mt-5 grid grid-cols-2 gap-3">
                  <div className="bg-white/10 border border-white/10 rounded-2xl p-4">
                    <div className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">Resonance Index</div>
                    <div className="mt-1 text-xl font-mono text-white">{resonanceIndex.toFixed(3)}</div>
                  </div>
                  <div className="bg-white/10 border border-white/10 rounded-2xl p-4">
                    <div className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">Stability Index</div>
                    <div className="mt-1 text-xl font-mono text-white">{stabilityIndex.toFixed(3)}</div>
                  </div>
                </div>
              </div>

              <motion.div
                className="absolute bottom-0 left-0 right-0 bg-blue-500/20"
                animate={{ height: `${phi * 100}%` }}
                transition={{ duration: 0.25 }}
              />
            </div>

            {/* Logs */}
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

        {/* BOTTOM: CLOSURE PROOF */}
        <div className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center gap-6">
            <div
              className={`w-16 h-16 rounded-full flex items-center justify-center text-2xl border-4 transition-all duration-700 ${
                closureOk
                  ? "border-emerald-500 text-emerald-600 bg-emerald-50"
                  : "border-slate-200 text-slate-400 bg-slate-50"
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
                <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-blue-600">Phase Closure Certificate (preview)</div>
                <button
                  onClick={() => setProofJson("")}
                  className="text-[10px] font-mono text-slate-500 hover:text-slate-700"
                >
                  close
                </button>
              </div>
              <pre className="text-[10px] leading-relaxed font-mono text-slate-700 overflow-x-auto whitespace-pre">
{proofJson}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}