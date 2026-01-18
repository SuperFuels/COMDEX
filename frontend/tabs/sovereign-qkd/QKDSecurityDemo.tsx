"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

type Status = "IDLE" | "HANDSHAKE" | "SECURE" | "INTERCEPTED";

type InfoParagraph = { title: string; text: string };

export default function QKDSecurityDemo() {
  const [status, setStatus] = useState<Status>("IDLE");
  const [logs, setLogs] = useState<string[]>([]);
  const [activeInfo, setActiveInfo] = useState<number>(0);

  const INFO_PARAGRAPHS: InfoParagraph[] = [
    {
      title: "1. The Observer Paradox (Anti-Eavesdropping)",
      text: "In GlyphNet, a message is a coherent wave. If an outside party attempts to 'listen' or intercept the transmission, the laws of physics force the wave to collapse. The data literally disappears or scrambles the moment it is observed by an unauthorized party.",
    },
    {
      title: "2. Decoherence Fingerprinting",
      text: "Our SRK-14 Ledger monitors 'Phase Stability'. When a hacker taps the line, they introduce phase-noise. The system detects this 'Decoherence Fingerprint' instantly, invalidating the GKey before a single bit of meaning can be extracted.",
    },
    {
      title: "3. Sovereign AI Communication",
      text: "This allows AI agents to exchange high-level strategic intent over public channels with total privacy. If the wave reaches the destination in a coherent state, we have physical proof that no one looked at it during transit.",
    },
  ];

  const addLog = (msg: string) =>
    setLogs((prev) => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev].slice(0, 5));

  const triggerHandshake = () => {
    setStatus("HANDSHAKE");
    addLog("Emitting Entangled Wave-Pair...");

    window.setTimeout(() => {
      setStatus("SECURE");
      addLog("✅ Verified: Zero-Interference Detected.");
    }, 2000);
  };

  const simulateAttack = () => {
    addLog("🚨 UNAUTHORIZED OBSERVATION DETECTED!");
    setStatus("INTERCEPTED");
    addLog("❌ Wave Collapse Triggered (SRK-10).");
    addLog("🔒 Session Terminated: No Data Leaked.");
  };

  return (
    <section className="space-y-16 pb-24">
      {/* Hero Header */}
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">Sovereign QKD</h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          Privacy enforced by <span className="text-black font-medium">physical collapse.</span>
        </p>
      </div>

      <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-8 bg-white p-2 rounded-[3rem] shadow-2xl border border-gray-100 overflow-hidden">
        {/* Left: The "Quantum Pipe" */}
        <div
          className={`relative h-[550px] rounded-[2.5rem] overflow-hidden transition-all duration-700 ${
            status === "INTERCEPTED" ? "bg-red-600" : "bg-slate-950"
          }`}
        >
          <div className="flex flex-col items-center justify-center h-full">
            <AnimatePresence mode="wait">
              {status === "IDLE" && (
                <button
                  onClick={triggerHandshake}
                  className="bg-white text-black px-10 py-5 rounded-full font-bold text-sm tracking-widest transition-all hover:scale-105"
                >
                  START SECURE STREAM
                </button>
              )}

              {status === "SECURE" && (
                <div className="flex flex-col items-center gap-8">
                  <motion.div
                    animate={{ scale: [1, 1.1, 1], opacity: [0.5, 1, 0.5] }}
                    transition={{ repeat: Infinity, duration: 2 }}
                    className="w-64 h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent shadow-[0_0_20px_cyan]"
                  />
                  <button
                    onClick={simulateAttack}
                    className="border border-red-500/50 text-red-500 px-6 py-2 rounded-full text-[10px] font-bold uppercase tracking-widest hover:bg-red-500 hover:text-white transition-all"
                  >
                    Attempt Interception
                  </button>
                </div>
              )}

              {status === "INTERCEPTED" && (
                <motion.div initial={{ scale: 2, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="text-center text-white p-12">
                  <h2 className="text-4xl font-bold italic mb-2">COLLAPSED</h2>
                  <p className="text-xs font-mono text-red-200">The act of listening destroyed the message.</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Right: Technical Narrative */}
        <div className="flex flex-col gap-8 p-10">
          <div className="space-y-6">
            <div className="min-h-[160px]">
              <h3 className="text-xs font-bold uppercase tracking-widest text-blue-600 mb-2">
                {INFO_PARAGRAPHS[activeInfo].title}
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed font-light">{INFO_PARAGRAPHS[activeInfo].text}</p>
            </div>
            <div className="flex gap-4">
              {[0, 1, 2].map((i) => (
                <button
                  key={i}
                  onClick={() => setActiveInfo(i)}
                  className={`h-1 flex-1 rounded-full transition-all ${activeInfo === i ? "bg-black" : "bg-gray-100"}`}
                />
              ))}
            </div>
          </div>

          <div className="bg-black rounded-3xl p-6 font-mono text-[10px] h-44 overflow-hidden space-y-2">
            <div className="text-blue-500 mb-2"># QKD_LOG_STREAM</div>
            {logs.map((log, i) => (
              <div key={i} className={log.includes("🚨") ? "text-red-500 font-bold animate-pulse" : "text-gray-400"}>
                {log}
              </div>
            ))}
          </div>

          <button
            onClick={() => {
              setStatus("IDLE");
              setLogs([]);
            }}
            className="text-[10px] font-bold uppercase text-gray-400 hover:text-black"
          >
            Clear Interference
          </button>
        </div>
      </div>
    </section>
  );
}