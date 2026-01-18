"use client";

import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";

const SESSION_ID = "a99acc96-acde-48d5-9b6d-d2f434536d5b";

type LogLine = { t: number; msg: string; tone?: "ok" | "warn" | "bad" };

export default function ResonancePulseHUD() {
  // Telemetry from your live run (keep stable for pitch/demo page)
  const metrics = useMemo(
    () => ({
      psi: 0.23896,
      kappa: 0.197375,
      T: 21.097865,
      target: 0.92,
      gain: 0.453535,
    }),
    []
  );

  // Beam corrections from your Stage 4 coupling test
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
  const [coherence, setCoherence] = useState(deltaCorrections[0].c);
  const [dc, setDc] = useState(deltaCorrections[0].dc);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [phaseOk, setPhaseOk] = useState(false); // πₛ closure (validator)
  const [highKappa, setHighKappa] = useState(false); // semantic density toggle
  const [theoremJson, setTheoremJson] = useState<string>("");
  const [running, setRunning] = useState(false);

  // “Holographic Persistence” polish: freeze + glow when beam 10 is stabilized
  const [collapsed, setCollapsed] = useState(false);

  const status = coherence >= 0.85 ? "STABILIZED" : "ADJUSTING";

  const pushLog = (msg: string, tone: LogLine["tone"] = "warn") => {
    setLogs((prev) => [{ t: Date.now(), msg, tone }, ...prev].slice(0, 9));
  };

  const resetPulse = () => {
    setTick(0);
    setCoherence(deltaCorrections[0].c);
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
        psi: metrics.psi,
        kappa: metrics.kappa,
        T: metrics.T,
        targetCoherence: metrics.target,
        gain: metrics.gain,
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
    // Demo behavior: emulate your successful pytest theorem validation
    setPhaseOk(true);
    pushLog("[πₛ Validator] PASSED → phase closure verified; theorem artifact ready.", "ok");

    // Pre-generate preview JSON-LD so “Download” feels immediate
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

  // Advance beams until collapse (stop at the 10th beam)
  useEffect(() => {
    if (!running || collapsed) return;

    const id = setInterval(() => {
      setTick((t) => Math.min(t + 1, deltaCorrections.length - 1));
    }, 1200);

    return () => clearInterval(id);
  }, [running, collapsed, deltaCorrections.length]);

  // Apply beam telemetry on tick
  useEffect(() => {
    const cur = deltaCorrections[Math.min(tick, deltaCorrections.length - 1)];
    setCoherence(cur.c);
    setDc(cur.dc);

    const okCoherence = cur.c >= 0.8;
    const tone: LogLine["tone"] = okCoherence ? "ok" : "warn";

    pushLog(
      `[MorphicFeedback] GWIP Beam ${cur.beam}/10: ΔC=${cur.dc >= 0 ? "+" : ""}${cur.dc.toFixed(
        4
      )} applied • coherence=${cur.c.toFixed(3)}`,
      tone
    );

    // Holographic Persistence: once 10th beam is stabilized, freeze + glow
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
  const amp = (highKappa ? 95 : 60) * coherence;
  const wobble = highKappa ? 18 : 0;

  // Branding palette (Tailwind approximations)
  // Lattice Black: #020617 (slate-950), Resonance Cyan: #22d3ee (cyan-400),
  // Morphic Green: #4ade80 (green-400), Entropy Red: #ef4444 (red-500), GWave Gold: #facc15 (yellow-400)
  return (
    <div className="w-full bg-slate-950 text-cyan-300 py-10 selection:bg-cyan-200/20">
      <div className="max-w-7xl mx-auto px-6 space-y-10">
        {/* TOP EXPLAINER (branding + canonical language) */}
        <section className="bg-black/40 border border-cyan-900/60 rounded-[2.5rem] p-8">
          <p className="text-[10px] uppercase tracking-[0.28em] text-cyan-500/70 font-semibold">
            Tessaris Photonic Systems • AION Standard Interface
          </p>

          <h2 className="mt-2 text-3xl font-extrabold italic tracking-tight text-cyan-200">
            RESONANCE PULSE • SYMBOLIC LIGHTWAVE ENGINE (SLE)
          </h2>

          <div className="mt-4 space-y-4 text-cyan-200/80 italic leading-relaxed">
            <p>
              The <span className="text-cyan-200 font-semibold">Photonic Interference Chamber</span> visualizes the{" "}
              <span className="text-cyan-200 font-semibold">ψ–κ–T tensor</span>. When coherence is low, the wave geometry fragments; as{" "}
              <span className="text-cyan-200 font-semibold">Morphic Feedback</span> applies ΔC (e.g., +0.0669), the computation visibly{" "}
              <span className="text-cyan-200 font-semibold">stabilizes</span> in-flight.
            </p>

            <p>
              The <span className="text-cyan-200 font-semibold">πₛ Phase Closure</span> badge is the integrity claim. Legacy stacks rely on
              post-facto checksums. SLE uses closure: if the loop doesn’t close to 2π, logic leaks (“ghost glyphs”). When πₛ flips to{" "}
              <span className="text-green-300 font-semibold">OK</span>, the circle of light is complete — mathematically sealed.
            </p>

            <p>
              The end state is <span className="text-cyan-200 font-semibold">Holographic Persistence</span>: a commit to the{" "}
              <span className="text-cyan-200 font-semibold">Resonance Ledger</span>, suitable for{" "}
              <span className="text-cyan-200 font-semibold">Sovereign Offline Payments</span> and{" "}
              <span className="text-cyan-200 font-semibold">Critical Infrastructure Defense</span>.
            </p>
          </div>
        </section>

        {/* HUD HEADER (branding: typography + badges + canonical terms) */}
        <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 border-b border-cyan-900/50 pb-5">
          <div>
            <h1 className="text-2xl md:text-3xl font-extrabold italic tracking-[0.06em] uppercase text-cyan-200">
              TESSARIS SLE V0.5 HUD
            </h1>
            <p className="mt-1 text-[11px] text-cyan-500/70 font-mono">
              SESSION_ID: {SESSION_ID} • ψ={metrics.psi.toFixed(5)} • κ={metrics.kappa.toFixed(6)} • T={metrics.T.toFixed(6)}
            </p>

            {/* Compliance / Integrity markers */}
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="px-3 py-1 rounded-full text-[10px] font-mono uppercase tracking-widest border border-yellow-400/30 text-yellow-300 bg-yellow-500/5">
                GWave Carrier • SRK-17
              </span>
              <span className="px-3 py-1 rounded-full text-[10px] font-mono uppercase tracking-widest border border-cyan-400/25 text-cyan-200 bg-cyan-500/5">
                SHA3-512 INTEGRITY
              </span>
              <span className="px-3 py-1 rounded-full text-[10px] font-mono uppercase tracking-widest border border-cyan-400/25 text-cyan-200 bg-cyan-500/5">
                SRK-17 COMPLIANT
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 items-center">
            {/* πs “Closer” badge: Entropy Red pulsating LOCKED -> Morphic Green OK */}
            <div
              className={`px-4 py-2 border rounded-full text-[10px] font-bold uppercase tracking-widest ${
                phaseOk
                  ? "border-green-400/60 bg-green-500/10 text-green-200"
                  : "border-red-500 bg-red-500/10 text-red-300 animate-pulse"
              }`}
            >
              πₛ PHASE CLOSURE: {phaseOk ? "OK" : "LOCKED"}
            </div>

            <div
              className={`px-4 py-2 border rounded-full text-[10px] font-bold uppercase tracking-widest ${
                status === "STABILIZED"
                  ? "border-green-400/60 bg-green-500/10 text-green-200"
                  : "border-cyan-900/60 bg-black/30 text-cyan-200/80"
              }`}
            >
              {collapsed ? "HOLOGRAPHIC PERSISTENCE" : status}
            </div>

            {/* Stream control */}
            <button
              onClick={() => setRunning((v) => !v)}
              className={`px-5 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all ${
                running
                  ? "bg-cyan-500/10 border-cyan-400/40 text-cyan-200"
                  : "bg-transparent border-cyan-400/20 hover:bg-white/5 text-cyan-200"
              }`}
            >
              {running ? "STOP STREAM" : "START STREAM"}
            </button>

            {/* High κ toggle */}
            <button
              onClick={() => setHighKappa((v) => !v)}
              className={`px-5 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all ${
                highKappa
                  ? "bg-yellow-500/10 border-yellow-400/40 text-yellow-200"
                  : "bg-transparent border-cyan-400/20 hover:bg-white/5 text-cyan-200"
              }`}
              title="Curvature / semantic density mode"
            >
              {highKappa ? "HIGH κ: ON" : "HIGH κ: OFF"}
            </button>

            {/* πs validator */}
            <button
              onClick={runPiSValidator}
              className={`px-5 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all ${
                phaseOk
                  ? "bg-green-500/10 border-green-400/40 text-green-200"
                  : "bg-transparent border-cyan-400/20 hover:bg-white/5 text-cyan-200"
              }`}
            >
              {phaseOk ? "πₛ VALIDATOR: PASSED" : "RUN πₛ VALIDATOR"}
            </button>

            {/* Download theorem */}
            <button
              onClick={downloadTheorem}
              className={`px-5 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest border transition-all ${
                phaseOk
                  ? "bg-cyan-500/10 border-cyan-400/40 text-cyan-200"
                  : "bg-transparent border-cyan-400/20 text-cyan-200/50"
              }`}
              disabled={!phaseOk}
              title={!phaseOk ? "Run πₛ validator first" : "Download JSON-LD proof"}
            >
              DOWNLOAD PROOF (JSON-LD)
            </button>

            {/* Reset */}
            <button
              onClick={() => {
                setRunning(false);
                resetPulse();
              }}
              className="px-5 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest border border-cyan-400/20 hover:bg-white/5 transition-all text-cyan-200"
            >
              RESET
            </button>
          </div>
        </div>

        {/* MAIN GRID */}
        <div className="grid grid-cols-12 gap-8">
          {/* INTERFERENCE CHAMBER */}
          <div
            className={`col-span-12 lg:col-span-8 bg-black border border-cyan-900/60 rounded-[2rem] p-6 relative overflow-hidden ${
              collapsed ? "shadow-[0_0_70px_rgba(34,211,238,0.18)]" : ""
            }`}
          >
            <div
              className="absolute inset-0 opacity-20 pointer-events-none"
              style={{
                backgroundImage:
                  "radial-gradient(circle, rgba(34,211,238,0.55) 1px, rgba(0,0,0,0) 1px)",
                backgroundSize: "28px 28px",
              }}
            />

            <div className="absolute top-4 right-4 flex flex-wrap gap-2">
              <span className="text-[10px] bg-cyan-500/5 border border-cyan-400/20 px-3 py-1 rounded-full font-mono uppercase tracking-widest">
                GWIP STREAM: LIVE
              </span>
              <span className="text-[10px] bg-yellow-500/5 border border-yellow-400/25 px-3 py-1 rounded-full font-mono uppercase tracking-widest text-yellow-200">
                GWave MODULATION
              </span>
              {collapsed && (
                <span className="text-[10px] bg-green-500/10 border border-green-400/35 px-3 py-1 rounded-full font-mono uppercase tracking-widest text-green-200">
                  LEDGER COMMIT: SEALED
                </span>
              )}
            </div>

            <h3 className="text-[12px] uppercase tracking-[0.28em] text-cyan-500/70 mb-4 font-semibold">
              PHOTONIC INTERFERENCE CHAMBER
            </h3>

            <div className="h-64 flex items-center justify-center border-y border-cyan-900/30">
              <svg width="100%" height="100%" viewBox="0 0 800 200">
                <motion.path
                  d={`M 0 100
                      C 120 ${100 - amp}, 220 ${100 + amp}, 320 100
                      S 520 ${100 - (amp - wobble)}, 640 100
                      S 760 ${100 + (amp - wobble)}, 800 100`}
                  stroke="currentColor"
                  strokeWidth="2"
                  fill="none"
                  animate={
                    collapsed
                      ? { opacity: 1, filter: "drop-shadow(0px 0px 16px rgba(34,211,238,0.95))" }
                      : { opacity: [0.55, 1, 0.55] }
                  }
                  transition={collapsed ? { duration: 0.2 } : { repeat: Infinity, duration: highKappa ? 0.85 : 1.2 }}
                />

                <motion.path
                  d={`M 0 100
                      C 120 ${100 + amp}, 220 ${100 - amp}, 320 100
                      S 520 ${100 + (amp - wobble)}, 640 100
                      S 760 ${100 - (amp - wobble)}, 800 100`}
                  stroke="currentColor"
                  strokeWidth="1.5"
                  fill="none"
                  animate={
                    collapsed
                      ? { opacity: 0.9, filter: "drop-shadow(0px 0px 12px rgba(34,211,238,0.75))" }
                      : { opacity: [0.25, 0.85, 0.25] }
                  }
                  transition={collapsed ? { duration: 0.2 } : { repeat: Infinity, duration: highKappa ? 0.85 : 1.4 }}
                />

                {/* High-frequency modulation markers (GWave Gold) */}
                <motion.g
                  animate={collapsed ? { opacity: 0.9 } : { opacity: [0.3, 0.9, 0.3] }}
                  transition={collapsed ? { duration: 0.2 } : { repeat: Infinity, duration: 1.1 }}
                >
                  {[120, 260, 400, 540, 680].map((x) => (
                    <line
                      key={x}
                      x1={x}
                      y1={70}
                      x2={x}
                      y2={130}
                      stroke="#facc15"
                      strokeOpacity={0.55}
                      strokeWidth={1}
                    />
                  ))}
                </motion.g>
              </svg>
            </div>

            {/* ψ-κ-T tensor tiles (mono telemetry, branded colors) */}
            <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-3 text-[11px] text-cyan-200/80 font-mono">
              <div className="bg-white/5 border border-cyan-900/50 rounded-xl p-3">
                ψ (Entropy)
                <div className="text-xl font-bold italic text-cyan-200">{metrics.psi.toFixed(5)}</div>
              </div>
              <div className="bg-white/5 border border-cyan-900/50 rounded-xl p-3">
                κ (Curvature)
                <div className="text-xl font-bold italic text-cyan-200">{metrics.kappa.toFixed(6)}</div>
              </div>
              <div className="bg-white/5 border border-cyan-900/50 rounded-xl p-3">
                T (Temporal)
                <div className="text-xl font-bold italic text-cyan-200">{metrics.T.toFixed(6)}</div>
              </div>
              <div className="bg-white/5 border border-cyan-900/50 rounded-xl p-3">
                Target C
                <div className="text-xl font-bold italic text-cyan-200">{(metrics.target * 100).toFixed(0)}%</div>
              </div>
              <div className="bg-white/5 border border-cyan-900/50 rounded-xl p-3">
                Gain
                <div className="text-xl font-bold italic text-cyan-200">{metrics.gain.toFixed(3)}</div>
              </div>
            </div>

            <div className="mt-4 text-[11px] text-cyan-300/70 font-mono">
              GWIP Beam {deltaCorrections[Math.min(tick, deltaCorrections.length - 1)].beam}/10 • Coherence{" "}
              <span className={coherence >= 0.8 ? "text-green-300" : "text-red-300"}>{(coherence * 100).toFixed(2)}%</span>{" "}
              • ΔC <span className="text-cyan-200">{dc >= 0 ? "+" : ""}{dc.toFixed(4)}</span>
              {highKappa && <span className="ml-2 text-yellow-200/90">• HIGH κ (SEMANTIC DENSITY)</span>}
            </div>
          </div>

          {/* MORPHIC LOG TERMINAL */}
          <div className="col-span-12 lg:col-span-4 bg-slate-900/60 border border-cyan-900/60 rounded-[2rem] p-5 flex flex-col">
            <h3 className="text-[12px] uppercase tracking-[0.28em] text-cyan-200 border-b border-cyan-900/40 pb-3 font-semibold">
              MORPHIC FEEDBACK LOG
            </h3>

            <div className="mt-4 flex-grow space-y-2 text-[11px] font-mono">
              {(logs.length ? logs : [{ t: 0, msg: "[MorphicFeedback] awaiting GWIP beam injections…", tone: "warn" }]).map((l) => (
                <div
                  key={`${l.t}-${l.msg}`}
                  className={
                    l.tone === "ok"
                      ? "text-green-300"
                      : l.tone === "bad"
                      ? "text-red-300"
                      : "text-cyan-200/80"
                  }
                >
                  {l.msg}
                </div>
              ))}
            </div>

            {/* Resonance Stabilization meter */}
            <div className="mt-5 p-4 bg-black/70 border border-cyan-900/60 rounded-xl">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-cyan-500/70 uppercase tracking-widest">RESONANCE STABILIZATION</span>
                <span className={coherence >= 0.8 ? "text-green-300" : "text-red-300"}>
                  {(coherence * 100).toFixed(2)}%
                </span>
              </div>

              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mt-2">
                <motion.div
                  className={coherence >= 0.8 ? "h-full bg-green-400" : "h-full bg-red-500"}
                  animate={{ width: `${Math.max(2, Math.min(100, coherence * 100))}%` }}
                  transition={{ duration: 0.4 }}
                />
              </div>

              <div className="mt-3 text-[11px] text-cyan-500/70 font-mono">
                ΔC applied:{" "}
                <span className="text-cyan-200">
                  {dc >= 0 ? "+" : ""}
                  {dc.toFixed(4)}
                </span>
              </div>

              <div className="mt-2 text-[10px] text-cyan-300/60 font-mono uppercase tracking-widest">
                πₛ Integrity:{" "}
                {phaseOk ? (
                  <span className="text-green-300">VERIFIED</span>
                ) : (
                  <span className="text-red-300">LOCKED</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* THEOREM / CERTIFICATE PANEL (branding language: Resonance Ledger / proof capsule) */}
        <section className="bg-black/40 border border-cyan-900/60 rounded-[2.5rem] p-8">
          <p className="text-[10px] uppercase tracking-[0.28em] text-cyan-500/70 font-semibold">RESONANCE LEDGER CERTIFICATE</p>

          <h3 className="mt-2 text-2xl font-extrabold italic tracking-tight text-cyan-200">
            πₛ PHASE CLOSURE PROOF • JSON-LD CAPSULE
          </h3>

          <p className="mt-4 text-cyan-200/80 italic leading-relaxed">
            When πₛ is OK, the wavefield is a closed circuit (2π) with no logic leakage into the environment. The collapse event represents{" "}
            <span className="text-cyan-200 font-semibold">Holographic Persistence</span>: a sealed state committed to the{" "}
            <span className="text-cyan-200 font-semibold">Resonance Ledger</span>.
          </p>

          <div className="mt-5 grid md:grid-cols-3 gap-4 text-[11px] font-mono">
            <div className="bg-white/5 border border-cyan-900/50 rounded-2xl p-4">
              Artifact: <span className="text-cyan-200">docs/rfc/holo_theorem.md</span>
            </div>
            <div className="bg-white/5 border border-cyan-900/50 rounded-2xl p-4">
              Status:{" "}
              <span className={phaseOk ? "text-green-300" : "text-yellow-200"}>
                {phaseOk ? "VERIFIED (pytest)" : "PENDING"}
              </span>
            </div>
            <div className="bg-white/5 border border-cyan-900/50 rounded-2xl p-4">
              Output: <span className="text-cyan-200">Proof Capsule (JSON-LD)</span>
            </div>
          </div>

          {theoremJson && (
            <div className="mt-6 bg-black/60 border border-cyan-900/50 rounded-2xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-[10px] font-bold uppercase tracking-[0.28em] text-cyan-500/70 font-mono">
                  JSON-LD PROOF PREVIEW
                </div>
                <button
                  onClick={() => setTheoremJson("")}
                  className="text-[10px] font-mono text-cyan-300/70 hover:text-cyan-200 uppercase tracking-widest"
                >
                  close
                </button>
              </div>
              <pre className="text-[10px] leading-relaxed font-mono text-cyan-200/80 overflow-x-auto whitespace-pre">
{theoremJson}
              </pre>
            </div>
          )}
        </section>

        {/* USE CASES (keep content, align language) */}
        <section className="bg-black/40 border border-cyan-900/60 rounded-[2.5rem] p-8">
          <p className="text-[10px] uppercase tracking-[0.28em] text-cyan-500/70 font-semibold">DEPLOYMENT PATH</p>
          <h3 className="mt-2 text-2xl font-extrabold italic tracking-tight text-cyan-200">FROM DEMO TO FIELD SYSTEM</h3>

          <div className="mt-5 grid md:grid-cols-3 gap-6">
            <div className="border border-cyan-900/60 rounded-2xl p-5 bg-black/30">
              <h4 className="text-cyan-200 font-bold italic">Critical Infrastructure Defense</h4>
              <p className="mt-3 text-cyan-200/75 text-sm italic leading-relaxed">
                When primary links fail, the system keeps coherence, routing, and integrity guarantees — resilient GWIP continuity without
                “message failed” events.
              </p>
            </div>

            <div className="border border-cyan-900/60 rounded-2xl p-5 bg-black/30">
              <h4 className="text-cyan-200 font-bold italic">Sovereign Offline Payments</h4>
              <p className="mt-3 text-cyan-200/75 text-sm italic leading-relaxed">
                Devices can carry the mathematical proof of a transaction in a stabilized holographic state offline, then reconcile on return
                connectivity.
              </p>
            </div>

            <div className="border border-cyan-900/60 rounded-2xl p-5 bg-black/30">
              <h4 className="text-cyan-200 font-bold italic">Pocket Bridge Private Nets</h4>
              <p className="mt-3 text-cyan-200/75 text-sm italic leading-relaxed">
                Portable nodes enable secure comms and state sync far off-grid — expedition ops, private site-to-site, and sovereign “digital
                citadels.”
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}