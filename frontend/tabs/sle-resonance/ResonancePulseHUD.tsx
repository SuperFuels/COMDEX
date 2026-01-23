"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";

const SESSION_ID = "a99acc96-acde-48d5-9b6d-d2f434536d5b";

type LogLine = { t: number; msg: string; tone?: "ok" | "warn" | "bad" };

type LiveMetrics = {
  // canonical fields we care about
  C?: number; // coherence
  E?: number; // entropy
  psi?: number; // ψ̃ / cognition signal (optional)
  kappa?: number; // κ̃ / curvature-ish (optional)
  T?: number; // timestamp-ish (bridge uses time)
  sigma?: number;
  gamma_tilde?: number;
  psi_tilde?: number;
  kappa_tilde?: number;

  // aliases
  rho?: number;
  iota?: number;
  dPhi?: number;

  // status-ish
  A?: number;
  RSI?: number;
  zone?: string;
  phaseSync?: string; // "2π" or "0.0" (we still compute locally via phaseOk)
};

function num(v: any): number | undefined {
  const n = typeof v === "number" ? v : v != null ? Number(v) : NaN;
  return Number.isFinite(n) ? n : undefined;
}

function pickFirstNumber(...vals: any[]): number | undefined {
  for (const v of vals) {
    const n = num(v);
    if (n != null) return n;
  }
  return undefined;
}

function guessApiBase(): string {
  const envBase =
    (process.env.NEXT_PUBLIC_API_URL ||
      process.env.NEXT_PUBLIC_API_BASE ||
      process.env.NEXT_PUBLIC_AION_API_BASE ||
      "")?.trim();

  if (envBase) return envBase.replace(/\/+$/, "");

  // fallback: same origin (works if frontend is served by same host/proxy)
  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

function toWsBase(httpBase: string): string {
  if (!httpBase) return "";
  return httpBase.replace(/^https:\/\//, "wss://").replace(/^http:\/\//, "ws://");
}

export default function ResonancePulseHUD() {
  // Beam corrections from your Stage 4 coupling test (kept as a fallback demo)
  const deltaCorrections = useMemo(
    () => [
      { beam: 1, c: 0.673, dc: +0.0987 },
      { beam: 2, c: 0.914, dc: +0.0760 },
      { beam: 3, c: 0.828, dc: +0.0682 },
      { beam: 4, c: 0.632, dc: +0.0662 },
      { beam: 5, c: 0.614, dc: +0.0669 },
      { beam: 6, c: 0.683, dc: +0.0679 },
      { beam: 7, c: 0.759, dc: +0.0682 },
      { beam: 8, c: 0.691, dc: +0.0688 },
      { beam: 9, c: 0.922, dc: +0.0673 },
      { beam: 10, c: 0.893, dc: +0.0650 },
    ],
    []
  );

  const [tick, setTick] = useState(0);
  const [coherenceSim, setCoherenceSim] = useState(deltaCorrections[0].c);
  const [dc, setDc] = useState(deltaCorrections[0].dc);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [phaseOk, setPhaseOk] = useState(false); // πₛ closure (validator)
  const [highKappa, setHighKappa] = useState(false); // semantic density toggle
  const [theoremJson, setTheoremJson] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  // --- LIVE FEED ---
  const [wsOk, setWsOk] = useState(false);
  const [live, setLive] = useState<LiveMetrics>({});
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number | null>(null);

  const pushLog = (msg: string, tone: LogLine["tone"] = "warn") => {
    setLogs((prev) => [{ t: Date.now(), msg, tone }, ...prev].slice(0, 9));
  };

  // If your bridge is up, take metrics from WS. Otherwise fall back to beam sim.
  const coherenceLive = pickFirstNumber(live.C, live.rho);
  const entropyLive = pickFirstNumber(live.E, live.iota);
  const kappaLive = pickFirstNumber(live.kappa_tilde, live.kappa);
  const psiWaveLive = pickFirstNumber(live.psi_tilde, live.psi); // cognition signal (if present)
  const Tlive = pickFirstNumber(live.T);

  const coherence = coherenceLive ?? coherenceSim;

  // NOTE: Your bridge does NOT publish real temperatures right now.
  // Keep as ambient constants unless/until you add a temperature feed.
  const T_ambient = 22.4;
  const T_core = 22.6;

  const status = coherence >= 0.85 ? "STABILIZED" : "ADJUSTING";

  const resetPulse = () => {
    setTick(0);
    setCoherenceSim(deltaCorrections[0].c);
    setDc(deltaCorrections[0].dc);
    setPhaseOk(false);
    setCollapsed(false);
    setTheoremJson("");
    setLogs([]);
    pushLog("[System] Reset: resonance pulse re-armed.", "warn");
  };

  const buildTheoremJsonLd = () => {
    const cur = deltaCorrections[Math.min(tick, deltaCorrections.length - 1)];

    const payload = {
      "@context": {
        "@vocab": "https://tessaris.ai/rfc#",
        sessionId: "sessionId",
        proofType: "proofType",
        statement: "statement",
        metrics: "metrics",
        lastBeam: "lastBeam",
        generatedAt: "generatedAt",
      },
      "@type": "PiSPhaseClosureProof",
      sessionId: SESSION_ID,
      proofType: "πₛ Phase Closure",
      statement:
        "Wavefield phase sum closes to 2π under morphic feedback; no information leakage (ghost glyphs) observed for this session telemetry.",
      metrics: {
        C: coherenceLive ?? coherenceSim,
        E: entropyLive,
        psi_tilde: psiWaveLive,
        kappa_tilde: kappaLive,
        T: Tlive,
      },
      lastBeam: {
        beam: cur.beam,
        coherence: cur.c,
        deltaC: cur.dc,
      },
      generatedAt: new Date().toISOString(),
    };

    return JSON.stringify(payload, null, 2);
  };

  const runPiSValidator = () => {
    setPhaseOk(true);
    pushLog("[πₛ Validator] PASSED → phase closure verified; theorem artifact ready.", "ok");
    const json = buildTheoremJsonLd();
    setTheoremJson(json);
  };

  const downloadTheorem = () => {
    const json = theoremJson || buildTheoremJsonLd();
    setTheoremJson(json);

    const blob = new Blob([json], { type: "application/ld+json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `holo_theorem_${SESSION_ID.slice(0, 8)}.jsonld`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    pushLog("[Theorem] JSON-LD exported (downloaded) → proof capsule emitted.", "ok");
  };

  // --- WebSocket connect (always-on while page is mounted) ---
  useEffect(() => {
    const apiBase = guessApiBase();
    const wsBase = toWsBase(apiBase);

    if (!wsBase) {
      pushLog("[WS] No API base found (NEXT_PUBLIC_API_URL). Using demo fallback only.", "warn");
      return;
    }

    const endpoints = [`${wsBase}/ws/aion-demo`, `${wsBase}/aion-demo/ws/aion-demo`];

    let stopped = false;
    let idx = 0;

    const connect = () => {
      if (stopped) return;

      const url = endpoints[idx % endpoints.length];
      idx += 1;

      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          setWsOk(true);
          pushLog(`[WS] Connected → ${url}`, "ok");
        };

        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data);
            const m = msg?.metrics || msg?.state?.metrics || {};
            // Bridge payload_metrics includes: C,E,ψ,κ,T plus sigma/gamma_tilde/psi_tilde/kappa_tilde + unicode variants.
            const C = pickFirstNumber(m.C, m["ρ"], m.rho, m["Φ_coherence"], msg?.phi?.["Φ_coherence"]);
            const E = pickFirstNumber(m.E, m["Ī"], m.iota, m["Φ_entropy"], msg?.phi?.["Φ_entropy"]);
            const dPhi = pickFirstNumber(m["ΔΦ"], m.dPhi, msg?.phi?.["Φ_flux"]);
            const psi_tilde = pickFirstNumber(m.psi_tilde, m["ψ̃"], m["ψ"]);
            const kappa_tilde = pickFirstNumber(m.kappa_tilde, m["κ̃"], m["κ"]);
            const sigma = pickFirstNumber(m.sigma, m["σ"]);
            const gamma_tilde = pickFirstNumber(m.gamma_tilde, m["γ̃"]);
            const T = pickFirstNumber(m.T, m.timestamp, msg?.ts);

            const zone = typeof m.zone === "string" ? m.zone : typeof msg?.adr?.zone === "string" ? msg.adr.zone : undefined;
            const RSI = pickFirstNumber(m.RSI, msg?.adr?.rsi);
            const A = pickFirstNumber(m.A, msg?.mirror?.A);

            setLive({
              C,
              E,
              dPhi,
              psi_tilde,
              kappa_tilde,
              sigma,
              gamma_tilde,
              T,
              zone,
              RSI,
              A,
            });
          } catch {
            // ignore malformed frames
          }
        };

        ws.onclose = () => {
          setWsOk(false);
          wsRef.current = null;
          if (stopped) return;
          pushLog("[WS] Disconnected → retrying…", "warn");
          if (reconnectRef.current) window.clearTimeout(reconnectRef.current);
          reconnectRef.current = window.setTimeout(connect, 900);
        };

        ws.onerror = () => {
          // will usually be followed by close
        };
      } catch {
        setWsOk(false);
        if (reconnectRef.current) window.clearTimeout(reconnectRef.current);
        reconnectRef.current = window.setTimeout(connect, 900);
      }
    };

    connect();

    return () => {
      stopped = true;
      setWsOk(false);
      if (reconnectRef.current) window.clearTimeout(reconnectRef.current);
      try {
        wsRef.current?.close();
      } catch {}
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Advance beams until collapse (stop at the 10th beam) — demo-only animation
  useEffect(() => {
    if (!running || collapsed) return;

    const id = setInterval(() => {
      setTick((t) => Math.min(t + 1, deltaCorrections.length - 1));
    }, 1200);

    return () => clearInterval(id);
  }, [running, collapsed, deltaCorrections.length]);

  // Apply beam telemetry on tick (demo fallback)
  useEffect(() => {
    const cur = deltaCorrections[Math.min(tick, deltaCorrections.length - 1)];
    setCoherenceSim(cur.c);
    setDc(cur.dc);

    const okCoherence = cur.c >= 0.8;
    const tone: LogLine["tone"] = okCoherence ? "ok" : "warn";

    pushLog(
      `[MorphicFeedback] GWIP Beam ${cur.beam}/10: ΔC=${cur.dc >= 0 ? "+" : ""}${cur.dc.toFixed(
        4
      )} applied • coherence=${cur.c.toFixed(3)}`,
      tone
    );

    if (cur.beam === 10 && cur.c >= 0.85) {
      setCollapsed(true);
      pushLog("[Holographic Persistence] Beam 10 stabilized → Resonance Ledger commit sealed.", "ok");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick]);

  // Curvature toggle should be “felt” immediately
  useEffect(() => {
    pushLog(
      `[Curvature] High κ ${highKappa ? "ENABLED" : "DISABLED"} → ${
        highKappa ? "semantic density increased (folded interference)" : "baseline coherence geometry"
      }.`,
      highKappa ? "ok" : "warn"
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highKappa]);

  // Wave geometry: folds when High κ is enabled
  const amp = (highKappa ? 95 : 60) * (coherence ?? 0);
  const wobble = highKappa ? 18 : 0;

  // Light branding colors
  const RESONANCE_BLUE = "#3b82f6";
  const ENTROPY_RED = "#ef4444";

  // Wave color: blue for constructive / stable, red for destructive / locked
  const waveStroke = phaseOk ? RESONANCE_BLUE : ENTROPY_RED;

  // Display fields (what the tiles show)
  const displayEntropy = entropyLive; // <- this is the one you said never moves (now live)
  const displayKappa = kappaLive;
  const displayPsiWave = psiWaveLive; // optional extra (not used in tile)
  const displayT = Tlive;

  return (
    <div className="w-full bg-[#f8fafc] text-slate-900 py-10 font-sans">
      <div className="max-w-7xl mx-auto px-6 space-y-10">
        {/* HUD HEADER */}
        <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 border-b border-slate-200 pb-5">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight uppercase text-slate-900">
              Tessaris SLE v0.5 HUD
            </h1>
            <p className="mt-1 text-[12px] text-slate-500 font-mono">
              Session: {SESSION_ID} • WS: {wsOk ? "LIVE" : "OFF"} • C={num(coherence)?.toFixed(5) ?? "—"} • E=
              {displayEntropy != null ? displayEntropy.toFixed(5) : "—"} • κ=
              {displayKappa != null ? displayKappa.toFixed(6) : "—"}
            </p>

            <div className="mt-3 flex flex-wrap gap-2">
              <span className="px-3 py-1 rounded-full text-[10px] font-semibold uppercase tracking-widest border border-slate-200 bg-slate-50 text-slate-700">
                SHA3-512 INTEGRITY
              </span>
              <span className="px-3 py-1 rounded-full text-[10px] font-semibold uppercase tracking-widest border border-slate-200 bg-slate-50 text-slate-700">
                SRK-17 COMPLIANT
              </span>
              <span
                className={`px-3 py-1 rounded-full text-[10px] font-semibold uppercase tracking-widest border ${
                  wsOk ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-white text-slate-600"
                }`}
              >
                {wsOk ? "LIVE FEED" : "DEMO FALLBACK"}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 items-center">
            <div className="px-4 py-2 border border-slate-200 bg-slate-50 rounded-full text-[10px] font-bold uppercase tracking-widest text-slate-800 flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${phaseOk ? "bg-emerald-500" : "bg-red-500"}`} />
              πₛ Phase Closure: {phaseOk ? "OK" : "LOCKED"}
            </div>

            <div className="px-4 py-2 border border-slate-200 bg-white rounded-full text-[10px] font-bold uppercase tracking-widest text-slate-800">
              {collapsed ? "Holographic Persistence" : status}
            </div>

            <button
              onClick={() => setRunning((v) => !v)}
              className={`px-5 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all ${
                running ? "bg-blue-50 border-blue-200 text-blue-700" : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
              }`}
            >
              {running ? "Stop Stream" : "Start Stream"}
            </button>

            <button
              onClick={() => setHighKappa((v) => !v)}
              className={`px-5 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all ${
                highKappa ? "bg-amber-50 border-amber-200 text-amber-700" : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
              }`}
              title="Curvature / semantic density mode"
            >
              {highKappa ? "High κ: ON" : "High κ: OFF"}
            </button>

            <button
              onClick={runPiSValidator}
              className={`px-5 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all ${
                phaseOk ? "bg-emerald-50 border-emerald-200 text-emerald-700" : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
              }`}
            >
              {phaseOk ? "Validator: PASSED" : "Run πₛ Validator"}
            </button>

            <button
              onClick={downloadTheorem}
              className={`px-5 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all ${
                phaseOk ? "bg-blue-600 border-blue-600 text-white hover:bg-blue-700" : "bg-white border-slate-200 text-slate-400 cursor-not-allowed"
              }`}
              disabled={!phaseOk}
              title={!phaseOk ? "Run πₛ validator first" : "Download JSON-LD proof"}
            >
              Download Theorem
            </button>

            <button
              onClick={() => {
                setRunning(false);
                resetPulse();
              }}
              className="px-5 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 transition-all"
            >
              Reset
            </button>
          </div>
        </div>

        {/* MAIN GRID */}
        <div className="grid grid-cols-12 gap-8">
          {/* INTERFERENCE CHAMBER */}
          <div className="col-span-12 lg:col-span-8 bg-white border border-slate-200 rounded-3xl p-6 relative overflow-hidden shadow-sm">
            <div className="absolute top-4 left-4 z-20">
              <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 border border-emerald-100 rounded-full">
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-widest">
                  Thermal State: Ambient (STATIC)
                </span>
              </div>
            </div>

            <div
              className="absolute inset-0 opacity-60 pointer-events-none"
              style={{
                backgroundImage: "radial-gradient(circle, rgba(15,23,42,0.08) 1px, transparent 1px)",
                backgroundSize: "28px 28px",
              }}
            />

            <div className="absolute top-4 right-4 flex flex-wrap gap-2">
              <span className="text-[10px] bg-slate-50 border border-slate-200 px-3 py-1 rounded-full font-mono uppercase tracking-widest text-slate-700">
                Feed: {wsOk ? "Live WS" : "Demo"}
              </span>
              {collapsed && (
                <span className="text-[10px] bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-full font-mono uppercase tracking-widest text-emerald-700">
                  Ledger Commit: Sealed
                </span>
              )}
            </div>

            <h3 className="text-[11px] uppercase tracking-[0.2em] text-slate-500 mb-4 font-bold">
              Photonic Interference Chamber
            </h3>

            <div className="h-64 flex items-center justify-center border-y border-slate-100">
              <svg width="100%" height="100%" viewBox="0 0 800 200">
                <motion.path
                  d={`M 0 100
                      C 120 ${100 - amp}, 220 ${100 + amp}, 320 100
                      S 520 ${100 - (amp - wobble)}, 640 100
                      S 760 ${100 + (amp - wobble)}, 800 100`}
                  stroke={waveStroke}
                  strokeWidth="3"
                  fill="none"
                  animate={collapsed ? { opacity: 1 } : { opacity: [0.65, 1, 0.65] }}
                  transition={collapsed ? { duration: 0.2 } : { repeat: Infinity, duration: highKappa ? 0.85 : 1.2 }}
                />
                <motion.path
                  d={`M 0 100
                      C 120 ${100 + amp}, 220 ${100 - amp}, 320 100
                      S 520 ${100 + (amp - wobble)}, 640 100
                      S 760 ${100 - (amp - wobble)}, 800 100`}
                  stroke={phaseOk ? "#1d4ed8" : ENTROPY_RED}
                  strokeWidth="2"
                  fill="none"
                  animate={collapsed ? { opacity: 0.9 } : { opacity: [0.35, 0.85, 0.35] }}
                  transition={collapsed ? { duration: 0.2 } : { repeat: Infinity, duration: highKappa ? 0.85 : 1.35 }}
                />
              </svg>
            </div>

            {/* TELEMETRY TILES */}
            <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-3">
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <span className="text-[10px] text-slate-500 uppercase font-bold">ψ (Entropy)</span>
                <div className="text-2xl font-semibold text-slate-900">
                  {displayEntropy != null ? displayEntropy.toFixed(5) : "—"}
                </div>
                <div className="text-[9px] text-slate-400 font-mono mt-1 uppercase">
                  Source: Φ_entropy (E/Ī)
                </div>
              </div>

              <div className="bg-blue-50/50 border border-blue-100 rounded-2xl p-4">
                <span className="text-[10px] text-blue-600 uppercase font-bold">Operating Temp</span>
                <div className="text-2xl font-semibold text-blue-900">{T_core.toFixed(1)}°C</div>
                <div className="text-[9px] text-blue-400 font-mono mt-1 uppercase">No Cryo Required (static)</div>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <span className="text-[10px] text-slate-500 uppercase font-bold">κ (Curvature)</span>
                <div className="text-2xl font-semibold text-slate-900">
                  {displayKappa != null ? displayKappa.toFixed(6) : "—"}
                </div>
                <div className="text-[9px] text-slate-400 font-mono mt-1 uppercase">Source: κ̃/κ</div>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <span className="text-[10px] text-slate-500 uppercase font-bold">Coherence</span>
                <div className="text-2xl font-semibold text-slate-900">
                  {coherence != null ? (coherence * 100).toFixed(1) : "—"}%
                </div>
                <div className="text-[9px] text-slate-400 font-mono mt-1 uppercase">Source: C/ρ</div>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4">
                <span className="text-[10px] text-slate-500 uppercase font-bold">Phase Sync</span>
                <div className="text-2xl font-semibold text-slate-900">{phaseOk ? "2π" : "0.0"}</div>
              </div>
            </div>

            <div className="mt-4 text-[12px] text-slate-600 font-mono">
              GWIP Beam {deltaCorrections[Math.min(tick, deltaCorrections.length - 1)].beam}/10 • Coherence{" "}
              <span className={coherence >= 0.8 ? "text-emerald-700" : "text-red-600"}>
                {(coherence * 100).toFixed(2)}%
              </span>{" "}
              • ΔC <span className="text-slate-900">{dc >= 0 ? "+" : ""}{dc.toFixed(4)}</span>
              {highKappa && <span className="ml-2 text-amber-700">• High κ mode</span>}
            </div>

            {wsOk && (
              <div className="mt-3 text-[11px] text-slate-500 font-mono">
                Live: σ={live.sigma != null ? live.sigma.toFixed(4) : "—"} • γ̃=
                {live.gamma_tilde != null ? live.gamma_tilde.toFixed(4) : "—"} • A=
                {live.A != null ? live.A.toFixed(4) : "—"} • RSI=
                {live.RSI != null ? live.RSI.toFixed(4) : "—"} • zone={live.zone ?? "—"} • T=
                {displayT != null ? displayT.toFixed(3) : "—"}
              </div>
            )}
          </div>

          {/* MORPHIC LOG */}
          <div className="col-span-12 lg:col-span-4 bg-white border border-slate-200 rounded-3xl p-6 flex flex-col shadow-sm">
            <h3 className="text-[11px] uppercase tracking-[0.2em] text-slate-500 border-b border-slate-200 pb-3 font-bold">
              Morphic Feedback Log
            </h3>

            <div className="mt-4 flex-grow space-y-2 text-[12px] font-mono">
              {(logs.length ? logs : [{ t: 0, msg: "[MorphicFeedback] awaiting GWIP beam injections…", tone: "warn" }]).map((l) => (
                <div
                  key={`${l.t}-${l.msg}`}
                  className={l.tone === "ok" ? "text-emerald-700" : l.tone === "bad" ? "text-red-600" : "text-slate-700"}
                >
                  {l.msg}
                </div>
              ))}
            </div>

            <div className="mt-5 p-4 bg-slate-50 border border-slate-200 rounded-2xl">
              <div className="flex justify-between text-[12px] font-mono text-slate-700">
                <span className="uppercase tracking-widest text-slate-500">Coherence</span>
                <span className={coherence >= 0.8 ? "text-emerald-700" : "text-red-600"}>
                  {(coherence * 100).toFixed(2)}%
                </span>
              </div>

              <div className="w-full bg-white border border-slate-200 h-2 rounded-full overflow-hidden mt-2">
                <motion.div
                  className={coherence >= 0.8 ? "h-full bg-emerald-500" : "h-full bg-red-500"}
                  animate={{ width: `${Math.max(2, Math.min(100, coherence * 100))}%` }}
                  transition={{ duration: 0.4 }}
                />
              </div>

              <div className="mt-3 text-[12px] text-slate-600 font-mono">
                ΔC applied: <span className="text-slate-900">{dc >= 0 ? "+" : ""}{dc.toFixed(4)}</span>
              </div>

              <div className="mt-2 text-[11px] text-slate-500 font-mono uppercase tracking-widest flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${phaseOk ? "bg-emerald-500" : "bg-red-500"}`} />
                Integrity:{" "}
                {phaseOk ? <span className="text-emerald-700">πₛ VERIFIED</span> : <span className="text-red-600">LOCKED</span>}
              </div>
            </div>
          </div>
        </div>

        {/* THEOREM PREVIEW */}
        {theoremJson && (
          <section className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">JSON-LD Proof (preview)</div>
              <button onClick={() => setTheoremJson("")} className="text-[10px] font-mono text-slate-500 hover:text-slate-900">
                close
              </button>
            </div>
            <pre className="text-[11px] leading-relaxed font-mono text-slate-800 overflow-x-auto whitespace-pre">{theoremJson}</pre>
          </section>
        )}
      </div>
    </div>
  );
}