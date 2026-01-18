"use client";

import React, { useMemo, useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

// =====================
// DEMO A: Substrate Comparison (existing)
// =====================

// Technical Definitions from SRK-17 & QKD Modules
const GLYPH_INSTRUCTION = "⊕ REDIRECT_FLUX (SRK-10)";
const LEGACY_DATA = "01010111 01000110 01001100 01010101 01011000";

// =====================
// DEMO B: Mesh Resilience (new)
// =====================

// Technical Definitions from Photon v0.2 Spec (compressed for UI)
type Transport = "FIBER" | "RADIO" | "BT";

const MESH_STATUS: Record<
  Transport,
  { label: string; speed: string; latency: string; colorText: string; colorBg: string; pacingSec: number; security: string }
> = {
  FIBER: {
    label: "Fiber Optic",
    speed: "10 Gbps",
    latency: "2ms",
    colorText: "text-blue-500",
    colorBg: "bg-blue-500",
    pacingSec: 0.9,
    security: "TLS 1.3",
  },
  RADIO: {
    label: "RF Mesh (SRK-17)",
    speed: "250 Mbps",
    latency: "12ms",
    colorText: "text-orange-500",
    colorBg: "bg-orange-500",
    pacingSec: 2.6, // ✅ paced burst animation
    security: "QKD + AES-GCM",
  },
  BT: {
    label: "P2P Bluetooth",
    speed: "2 Mbps",
    latency: "45ms",
    colorText: "text-purple-500",
    colorBg: "bg-purple-500",
    pacingSec: 3.6,
    security: "Pairing + E2EE",
  },
};

export default function SubstrateShiftDemo() {
  // =====================
  // DEMO A state
  // =====================
  const [isTransmitting, setIsTransmitting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isIntercepted, setIsIntercepted] = useState(false);
  const [status, setStatus] = useState<"idle" | "secure" | "tampered" | "complete">("idle");

  const legacyProgress = useMemo(() => {
    const lagged = Math.max(0, progress - 18);
    return Math.min(100, Math.floor(lagged * 0.88));
  }, [progress]);

  const legacySlice = useMemo(() => {
    const raw = LEGACY_DATA.replace(/\s/g, "");
    const n = Math.max(0, Math.min(raw.length, Math.floor((legacyProgress / 100) * raw.length)));
    const chunked = raw.slice(0, n).replace(/(.{8})/g, "$1 ").trim();
    return chunked || "…";
  }, [legacyProgress]);

  const reset = () => {
    setIsTransmitting(false);
    setProgress(0);
    setIsIntercepted(false);
    setStatus("idle");

    // Also stop mesh sending if it was running (keeps UX clean)
    setMeshIsSending(false);
    setMeshSpool(0);
  };

  const startDemo = () => {
    reset();
    setIsTransmitting(true);
    setStatus("secure");

    // start mesh sending too (they’re conceptually linked)
    setMeshIsSending(true);
    setMeshActiveMessage("Substrate Stable: Fiber Active");
  };

  const triggerIntercept = () => {
    if (isTransmitting && progress < 80) {
      setIsIntercepted(true);
      setStatus("tampered");
    }
  };

  useEffect(() => {
    if (!isTransmitting) return;

    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          if (!isIntercepted) setStatus("complete");
          return 100;
        }
        return prev + 1;
      });
    }, 70); // ✅ slowed

    return () => clearInterval(interval);
  }, [isTransmitting, isIntercepted]);

  // =====================
  // DEMO B: Mesh Resilience state (new)
  // =====================
  const [meshTransport, setMeshTransport] = useState<Transport>("FIBER");
  const [meshIsLineCut, setMeshIsLineCut] = useState(false);
  const [meshSyncStatus, setMeshSyncStatus] = useState<number>(100);
  const [meshActiveMessage, setMeshActiveMessage] = useState<string>("Substrate Stable: Fiber Active");
  const [meshIsSending, setMeshIsSending] = useState(false);

  // RF spooler depth (0..100)
  const [meshSpool, setMeshSpool] = useState<number>(0);

  const handleCutLine = () => {
    if (meshIsLineCut) return;
    setMeshIsLineCut(true);
    setMeshActiveMessage("CRITICAL: Primary Substrate Lost...");

    // fiber is gone immediately, then reroute after short handover
    setTimeout(() => {
      setMeshTransport("RADIO");
      setMeshActiveMessage("RE-ROUTING: RF Mesh Active (SRK-17)");
      setMeshSyncStatus(98.4);
    }, 1500);
  };

  const resetMesh = () => {
    setMeshIsLineCut(false);
    setMeshTransport("FIBER");
    setMeshSyncStatus(100);
    setMeshActiveMessage("Substrate Stable: Fiber Active");
    setMeshSpool(0);
    setMeshIsSending(false);
  };

  // If we restore infra, go back to fiber and drain spool
  const restoreInfrastructure = () => {
    setMeshActiveMessage("Infrastructure Restored: Returning to Fiber...");
    setTimeout(() => {
      setMeshIsLineCut(false);
      setMeshTransport("FIBER");
      setMeshSyncStatus(100);
      setMeshActiveMessage("Substrate Stable: Fiber Active");
      setMeshSpool(0);
    }, 900);
  };

  // RF Spooler behavior: fills when sending on RADIO, drains on FIBER
  useEffect(() => {
    const t = setInterval(() => {
      setMeshSpool((prev) => {
        if (!meshIsSending) return Math.max(0, prev - 6);

        if (meshTransport === "RADIO") {
          // Fill slowly to show pacing / outbox queue
          return Math.min(100, prev + 2);
        }
        if (meshTransport === "FIBER") {
          // Drain quickly (high bandwidth)
          return Math.max(0, prev - 10);
        }
        // BT: moderate drain/fill
        return Math.min(100, Math.max(0, prev + 1));
      });
    }, 220);

    return () => clearInterval(t);
  }, [meshIsSending, meshTransport]);

  // Let mesh "send" be driven by main demo buttons, but keep independent toggles too
  const toggleMeshSend = () => setMeshIsSending((v) => !v);

  // =====================
  // Render
  // =====================
  return (
    <div className="w-full bg-white text-black py-12 selection:bg-blue-100 font-sans">
      <div className="max-w-7xl mx-auto px-6 space-y-12">
        {/* Header Area (kept) */}
        <div className="flex justify-between items-end border-b border-gray-100 pb-8">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold italic tracking-tighter uppercase">Substrate Comparison</h1>
            <p className="text-gray-400 font-light italic text-lg">Visualizing QKD Policy Enforcement & Physical Security</p>
          </div>

          <div className="flex gap-4">
            <button
              onClick={triggerIntercept}
              disabled={!isTransmitting || isIntercepted || progress > 70}
              className={`px-8 py-4 rounded-full font-bold uppercase text-[10px] tracking-widest transition-all border-2 ${
                isIntercepted ? "border-red-200 text-red-300" : "border-black hover:bg-black hover:text-white"
              }`}
            >
              {isIntercepted ? "Interception Logged" : "Attempt Intercept"}
            </button>

            <button
              onClick={isTransmitting ? reset : startDemo}
              className={`px-10 py-4 rounded-full font-bold uppercase text-[10px] tracking-widest transition-all ${
                isTransmitting
                  ? "bg-gray-100 text-gray-500"
                  : "bg-blue-600 text-white shadow-xl shadow-blue-500/30 hover:scale-105"
              }`}
            >
              {isTransmitting ? "Reset" : "Transmit Wave"}
            </button>
          </div>
        </div>

        {/* DEMO A: COMPARISON LANES (kept) */}
        <div className="grid grid-rows-2 gap-8">
          {/* LANE 1: GLYPHNET */}
          <div
            className={`rounded-[3rem] p-10 border transition-colors duration-700 relative overflow-hidden group ${
              status === "tampered" ? "bg-red-50 border-red-200" : "bg-gray-50 border-gray-100"
            }`}
          >
            <div className="flex justify-between mb-8">
              <div className="space-y-2">
                <span
                  className={`text-[10px] font-bold uppercase tracking-[0.2em] ${
                    status === "tampered" ? "text-red-500" : "text-blue-600"
                  }`}
                >
                  {status === "tampered" ? "Violation Detected" : "Substrate A"}
                </span>

                <div className="space-y-1">
                  <h3 className="text-2xl font-bold italic">GlyphNet Wave-Native (QKD)</h3>
                  <p className="text-sm text-gray-500 italic">
                    Wave-native packets: the waveform carries routing + meaning — interception disturbs coherence and becomes
                    the alarm.
                  </p>
                </div>
              </div>

              <div className="text-right font-mono text-[10px]">
                <p className="text-gray-400">LAYER: PHOTONIC SUBSTRATE</p>
                <p className={status === "tampered" ? "text-red-600 font-bold" : "text-blue-600"}>
                  STATUS: {status.toUpperCase()}
                </p>
              </div>
            </div>

            <div className="relative h-48 bg-black rounded-[2rem] flex items-center justify-between px-16 overflow-hidden">
              <DesktopIcon label="Source" active={isTransmitting} />

              <div className="flex-1 relative h-full flex items-center justify-center">
                <AnimatePresence>
                  {isTransmitting && (
                    <motion.div
                      className="absolute left-0 w-full"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      <div className="absolute left-1/2 -translate-x-1/2 top-4 z-20 flex flex-col items-center">
                        <div
                          className={`p-2 rounded-full border transition-all ${
                            isIntercepted ? "bg-red-600 border-red-400" : "bg-gray-900 border-gray-700"
                          }`}
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                            <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                          </svg>
                        </div>
                        <span className="text-[7px] text-gray-500 font-bold uppercase mt-1">Eavesdropper</span>
                      </div>

                      <svg width="100%" height="80" viewBox="0 0 800 100">
                        <motion.path
                          d="M 0 50 Q 25 10, 50 50 T 100 50 T 150 50 T 200 50 T 250 50 T 300 50 T 350 50 T 400 50 T 450 50 T 500 50 T 550 50 T 600 50 T 650 50 T 700 50 T 750 50 T 800 50"
                          fill="none"
                          stroke={isIntercepted ? "#ef4444" : "#3b82f6"}
                          strokeWidth="3"
                          strokeDasharray={isIntercepted ? "5,5" : "0"}
                          animate={{
                            d: isIntercepted
                              ? ["M 0 50 L 800 50", "M 0 52 L 800 48", "M 0 50 L 800 50"]
                              : [
                                  "M 0 50 Q 25 10, 50 50 T 100 50 T 150 50 T 200 50 T 250 50 T 300 50 T 350 50 T 400 50 T 450 50 T 500 50 T 550 50 T 600 50 T 650 50 T 700 50 T 750 50 T 800 50",
                                  "M 0 50 Q 25 90, 50 50 T 100 50 T 150 50 T 200 50 T 250 50 T 300 50 T 350 50 T 400 50 T 450 50 T 500 50 T 550 50 T 600 50 T 650 50 T 700 50 T 750 50 T 800 50",
                                ],
                          }}
                          transition={{ repeat: Infinity, duration: isIntercepted ? 0.12 : 0.9, ease: "linear" }}
                        />
                      </svg>

                      {!isIntercepted && (
                        <motion.div
                          className="absolute top-0 px-4 py-1 bg-blue-600 text-white text-[8px] font-mono rounded-full whitespace-nowrap shadow-lg shadow-blue-500/40"
                          style={{ left: `${progress}%` }}
                        >
                          {GLYPH_INSTRUCTION}
                        </motion.div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <DesktopIcon label="Receiver" active={progress === 100} alert={status === "tampered"} />
            </div>

            <div className="mt-8 flex justify-between items-center text-[9px] font-mono uppercase tracking-widest">
              <div className="flex gap-6">
                <p className="text-gray-400">Medium: QKD-Protected Photon</p>
                {isIntercepted && <p className="text-red-600 animate-pulse">Fingerprint Mismatch: Wave Collapse Confirmed</p>}
              </div>
              <p className={status === "tampered" ? "text-red-500" : "text-blue-600"}>Policy: QKD_STRICT_ENFORCE</p>
            </div>
          </div>

          {/* LANE 2: LEGACY */}
          <div className="bg-gray-50 rounded-[3rem] p-10 border border-gray-100 relative overflow-hidden">
            <div className="flex justify-between mb-8">
              <div className="space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400">Substrate B</span>
                <div className="space-y-1">
                  <h3 className="text-2xl font-bold italic text-gray-700">Legacy Packet Stack (Binary)</h3>
                  <p className="text-sm text-gray-500 italic">
                    Bits are copied and reassembled from headers — interception can occur without a physical alarm.
                  </p>
                </div>
              </div>

              <div className="text-right font-mono text-[10px]">
                <p className="text-gray-400">LAYER: ROUTED PACKETS</p>
                <p className="text-gray-500">
                  STATUS: {isTransmitting ? (legacyProgress >= 100 ? "DELIVERED" : "TRANSMITTING") : "IDLE"}
                </p>
              </div>
            </div>

            <div className="relative h-48 bg-white rounded-[2rem] border border-gray-100 flex items-center justify-between px-16 overflow-hidden">
              <DesktopIcon label="Source" active={isTransmitting} />

              <div className="flex-1 relative h-full flex items-center justify-center">
                <div className="absolute left-8 right-8 h-[2px] bg-gray-200" />

                <div className="absolute left-1/2 -translate-x-1/2 top-6 z-10 flex flex-col items-center">
                  <div className="p-2 rounded-full border bg-gray-50 border-gray-200">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="2">
                      <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <span className="text-[7px] text-gray-400 font-bold uppercase mt-1">MITM</span>
                </div>

                <AnimatePresence>
                  {isTransmitting && (
                    <motion.div
                      key="legacy-flow"
                      className="absolute left-8 right-8 h-full"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      {Array.from({ length: 10 }).map((_, i) => (
                        <motion.div
                          key={i}
                          className="absolute top-1/2 -translate-y-1/2 px-2 py-1 rounded-md bg-gray-100 border border-gray-200 text-[8px] font-mono text-gray-500 shadow-sm"
                          initial={{ x: 0, opacity: 0.0 }}
                          animate={{ x: "100%", opacity: 1 }}
                          transition={{ repeat: Infinity, duration: 2.2, ease: "linear", delay: i * 0.18 }}
                          style={{ left: 0 }}
                        >
                          pkt
                        </motion.div>
                      ))}

                      <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-12 w-[260px]">
                        <div className="text-[8px] font-mono uppercase tracking-widest text-gray-400 mb-2">
                          Reassembly Buffer
                        </div>
                        <div className="bg-gray-50 border border-gray-200 rounded-xl px-3 py-2">
                          <div className="text-[10px] font-mono text-gray-600">{legacySlice}</div>
                          <div className="mt-1 text-[9px] font-mono text-gray-400">{legacyProgress}% • headers + retries</div>
                          {isIntercepted && (
                            <div className="mt-1 text-[9px] font-mono text-gray-400">
                              Tap present • <span className="text-gray-500">no physical alarm</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <DesktopIcon label="Receiver" active={legacyProgress >= 100 && isTransmitting} />
            </div>

            <div className="mt-8 flex justify-between items-center text-[9px] font-mono uppercase tracking-widest">
              <div className="flex gap-6">
                <p className="text-gray-400">Medium: Routed Packets</p>
                <p className="text-gray-400">Detection: Optional / Post-Facto</p>
              </div>
              <p className="text-gray-500">Policy: BEST_EFFORT_DELIVERY</p>
            </div>
          </div>
        </div>

        {/* DEMO A metrics (kept) */}
        <section className="bg-black text-white rounded-[3rem] p-12 grid grid-cols-4 gap-8">
          <Metric label="Decoherence Risk" glyph={isIntercepted ? "COLLAPSED" : "0.0002%"} legacy="N/A" alert={isIntercepted} />
          <Metric label="Tamper Detection" glyph="Instant (Physical)" legacy="Post-Facto (Log)" highlight />
          <Metric label="Validation Latency" glyph="< 1.2ms" legacy="~45.0ms" highlight />
          <Metric label="Data Integrity" glyph={isIntercepted ? "0.0%" : "99.99%"} legacy="100% (Blind)" alert={isIntercepted} />
        </section>

        {/* =====================
            DEMO B: Mesh Resilience (new section)
           ===================== */}
        <section className="w-full bg-black text-white py-16 px-8 rounded-[4rem] overflow-hidden border border-gray-800">
          <div className="max-w-6xl mx-auto space-y-12">
            <div className="flex justify-between items-start">
              <div className="space-y-2">
                <h2 className="text-3xl font-bold italic tracking-tighter">MESH RESILIENCE</h2>
                <p className="text-gray-500 font-mono text-xs uppercase tracking-widest">
                  Protocol: Photon v0.2 / CRDT Sync Layer
                </p>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={toggleMeshSend}
                  className={`px-6 py-3 rounded-full text-[10px] font-bold uppercase tracking-widest transition-all border ${
                    meshIsSending ? "bg-white/10 border-white/10" : "bg-transparent border-white/10 hover:bg-white/5"
                  }`}
                >
                  {meshIsSending ? "Stop Sending" : "Start Sending"}
                </button>

                {!meshIsLineCut ? (
                  <button
                    onClick={handleCutLine}
                    className="px-6 py-3 bg-red-600/10 border border-red-500 text-red-500 rounded-full text-[10px] font-bold uppercase tracking-widest hover:bg-red-500 hover:text-white transition-all"
                  >
                    Simulate Internet Cut
                  </button>
                ) : (
                  <button
                    onClick={restoreInfrastructure}
                    className="px-6 py-3 bg-blue-600 text-white rounded-full text-[10px] font-bold uppercase tracking-widest"
                  >
                    Restore Infrastructure
                  </button>
                )}

                <button
                  onClick={resetMesh}
                  className="px-6 py-3 bg-white/5 border border-white/10 rounded-full text-[10px] font-bold uppercase tracking-widest hover:bg-white/10 transition-all"
                >
                  Reset Mesh
                </button>
              </div>
            </div>

            {/* MESH VISUALIZER */}
            <div className="relative h-96 bg-gray-900/50 rounded-[3rem] border border-white/5 flex flex-col items-center justify-center overflow-hidden">
              <div
                className="absolute inset-0 opacity-20 pointer-events-none"
                style={{
                  backgroundImage: "radial-gradient(circle, #3b82f6 1px, transparent 1px)",
                  backgroundSize: "30px 30px",
                }}
              />

              <div className="flex w-full justify-around items-center z-10">
                <NodeBox label="Node_Alpha (Local)" active />

                {/* Bridge */}
                <div className="flex-1 relative h-20 flex items-center justify-center px-4">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={meshTransport + String(meshIsLineCut)}
                      initial={{ opacity: 0, scale: 0.96 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 1.04 }}
                      className="w-full h-full flex items-center justify-center"
                    >
                      {/* baseline connector */}
                      <div
                        className={`w-full h-[2px] relative ${
                          meshIsLineCut && meshTransport === "FIBER" ? "bg-transparent" : "bg-white/10"
                        }`}
                      >
                        {/* FIBER: solid beam */}
                        {!meshIsLineCut && meshTransport === "FIBER" && (
                          <motion.div
                            className="absolute inset-0 bg-blue-500 shadow-[0_0_15px_#3b82f6]"
                            animate={{ x: [-500, 500] }}
                            transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                          />
                        )}

                        {/* RADIO: paced burst packets + faint carrier */}
                        {meshIsLineCut && meshTransport === "RADIO" && (
                          <div className="absolute inset-0">
                            <div className="absolute inset-0 bg-orange-500/10" />
                            <div className="absolute inset-0 flex items-center">
                              {[1, 2, 3].map((i) => (
                                <motion.div
                                  key={i}
                                  className="w-2 h-2 bg-orange-500 rounded-full shadow-[0_0_10px_#f97316] absolute"
                                  style={{ left: 0 }}
                                  animate={{ x: [-40, 520], opacity: [0, 1, 0] }}
                                  transition={{
                                    repeat: Infinity,
                                    duration: MESH_STATUS.RADIO.pacingSec,
                                    delay: i * 0.7,
                                    ease: "easeInOut",
                                  }}
                                />
                              ))}
                            </div>

                            {/* QKD badge */}
                            <div className="absolute -bottom-10 left-1/2 -translate-x-1/2 flex items-center gap-2 text-[9px] text-green-400 font-mono">
                              <LockIcon />
                              QKD_VERIFIED: COLLAPSE_HASH_STABLE
                            </div>
                          </div>
                        )}

                        {/* BT (optional): slow shimmer if ever used */}
                        {meshTransport === "BT" && (
                          <motion.div
                            className="absolute inset-0 bg-purple-500/30 shadow-[0_0_18px_rgba(168,85,247,0.35)]"
                            animate={{ opacity: [0.2, 0.7, 0.2] }}
                            transition={{ repeat: Infinity, duration: 2.2 }}
                          />
                        )}
                      </div>
                    </motion.div>
                  </AnimatePresence>

                  {/* Transport badge */}
                  <div className="absolute -top-8 bg-black border border-white/10 px-4 py-1 rounded-full text-[9px] font-mono flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full animate-pulse ${MESH_STATUS[meshTransport].colorBg}`} />
                    {MESH_STATUS[meshTransport].label}
                    <span className="text-gray-500">•</span>
                    <span className="text-gray-400">{MESH_STATUS[meshTransport].security}</span>
                  </div>
                </div>

                <NodeBox label="Node_Omega (Remote)" active />
              </div>

              {/* Terminal */}
              <div className="absolute bottom-6 left-6 right-6 h-24 bg-black/80 rounded-2xl border border-white/5 p-4 font-mono text-[10px] space-y-1">
                <p className="text-blue-400 font-bold">{`> ${meshActiveMessage}`}</p>
                <p className="text-gray-500">{`> CRDT Vector Clock: [${Math.floor(Date.now() / 1000)}]`}</p>
                <p className="text-gray-500">{`> Substrate: ${meshTransport} • ${MESH_STATUS[meshTransport].speed} • ${MESH_STATUS[meshTransport].latency}`}</p>
                <p className="text-gray-500">{`> Efficiency: ${
                  meshTransport === "FIBER" ? "99.9%" : "56x Compression Active"
                } • Send: ${meshIsSending ? "ON" : "OFF"}`}</p>
                {meshIsLineCut && meshTransport === "RADIO" && (
                  <p className="text-orange-400 animate-pulse">{`> MESH_HANDOVER_SUCCESS: No Packet Loss Recorded`}</p>
                )}
              </div>
            </div>

            {/* METRICS */}
            <div className="grid grid-cols-4 gap-8">
              <div className="bg-gray-900 p-8 rounded-[2.5rem] border border-white/5">
                <p className="text-[10px] text-gray-500 uppercase tracking-tighter mb-2">Sync Consistency</p>
                <h4 className="text-3xl font-bold italic">{meshSyncStatus}%</h4>
                <p className="text-[9px] text-blue-400 mt-2">Yjs Conflict-Free Merging</p>
              </div>

              <div className="bg-gray-900 p-8 rounded-[2.5rem] border border-white/5">
                <p className="text-[10px] text-gray-500 uppercase tracking-tighter mb-2">Failover Latency</p>
                <h4 className="text-3xl font-bold italic">{meshIsLineCut ? "1.2ms" : "0ms"}</h4>
                <p className="text-[9px] text-blue-400 mt-2">Zero-Data-Loss Handover</p>
              </div>

              <div className="bg-gray-900 p-8 rounded-[2.5rem] border border-white/5">
                <p className="text-[10px] text-gray-500 uppercase tracking-tighter mb-2">Substrate State</p>
                <h4 className={`text-3xl font-bold italic ${MESH_STATUS[meshTransport].colorText}`}>{meshTransport}</h4>
                <p className="text-[9px] text-gray-400 mt-2">
                  Mode: {meshIsLineCut ? "Self-Healing Mesh" : "Standard Infrastructure"}
                </p>
              </div>

              {/* ✅ RF Spooler Depth (new metric) */}
              <div className="bg-gray-900 p-8 rounded-[2.5rem] border border-white/5">
                <p className="text-[10px] text-gray-500 uppercase tracking-tighter mb-2">RF Spooler Depth</p>
                <div className="w-full h-2 bg-black rounded-full overflow-hidden mt-4">
                  <motion.div
                    className="h-full bg-orange-500"
                    animate={{
                      width:
                        meshTransport === "RADIO" && meshIsSending
                          ? `${Math.max(8, Math.min(100, meshSpool))}%`
                          : "0%",
                    }}
                    transition={{ ease: "linear", duration: 0.2 }}
                  />
                </div>
                <p className="text-[9px] text-orange-400 mt-2">
                  {meshTransport === "RADIO" && meshIsSending ? `Outbox: ${meshSpool.toFixed(0)}% • Pacing bursts` : "Idle"}
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* tiny spacer */}
        <div className="h-2" />
      </div>
    </div>
  );
}

function DesktopIcon({
  label,
  active,
  alert,
}: {
  label: string;
  active?: boolean;
  alert?: boolean;
}) {
  return (
    <div className="flex flex-col items-center space-y-3 z-10">
      <div
        className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300 ${
          alert ? "bg-red-600 animate-bounce" : active ? "bg-blue-600" : "bg-gray-800"
        }`}
      >
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
        </svg>
      </div>
      <span className={`text-[9px] font-bold uppercase tracking-widest ${alert ? "text-red-600" : "text-gray-500"}`}>
        {alert ? "ALARM" : label}
      </span>
    </div>
  );
}

function Metric({
  label,
  glyph,
  legacy,
  highlight,
  alert,
}: {
  label: string;
  glyph: string;
  legacy: string;
  highlight?: boolean;
  alert?: boolean;
}) {
  return (
    <div className="space-y-4">
      <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{label}</p>
      <div className="space-y-1">
        <p className={`text-xl font-bold italic ${alert ? "text-red-500" : highlight ? "text-blue-400" : "text-white"}`}>
          {glyph}
        </p>
        <p className="text-[10px] text-gray-600">vs {legacy}</p>
      </div>
    </div>
  );
}

function NodeBox({ label, active }: { label: string; active?: boolean }) {
  return (
    <div className="flex flex-col items-center gap-4">
      <div
        className={`w-24 h-24 rounded-3xl border-2 flex items-center justify-center transition-all duration-1000 ${
          active ? "border-blue-500 shadow-[0_0_30px_rgba(59,130,246,0.2)]" : "border-gray-800"
        }`}
      >
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <path d="M8 21h8M12 17v4" />
        </svg>
      </div>
      <span className="text-[10px] font-bold uppercase text-gray-500 tracking-tighter">{label}</span>
    </div>
  );
}

function LockIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}