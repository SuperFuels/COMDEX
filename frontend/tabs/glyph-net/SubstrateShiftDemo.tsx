"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

// Technical Definitions from SRK-17 & QKD Modules
const GLYPH_INSTRUCTION = "⊕ REDIRECT_FLUX (SRK-10)";
const LEGACY_DATA = "01010111 01000110 01001100 01010101 01011000";

export default function SubstrateShiftDemo() {
  const [isTransmitting, setIsTransmitting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isIntercepted, setIsIntercepted] = useState(false);
  const [status, setStatus] = useState<"idle" | "secure" | "tampered" | "complete">("idle");

  const reset = () => {
    setIsTransmitting(false);
    setProgress(0);
    setIsIntercepted(false);
    setStatus("idle");
  };

  const startDemo = () => {
    reset();
    setIsTransmitting(true);
    setStatus("secure");
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
    }, 50);

    return () => clearInterval(interval);
  }, [isTransmitting, isIntercepted]);

  return (
    <div className="w-full bg-white text-black py-12 selection:bg-blue-100 font-sans">
      <div className="max-w-7xl mx-auto px-6 space-y-12">
        {/* Header Area */}
        <div className="flex justify-between items-end border-b border-gray-100 pb-8">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold italic tracking-tighter uppercase">Substrate Comparison</h1>
            <p className="text-gray-400 font-light italic text-lg">
              Visualizing QKD Policy Enforcement & Physical Security
            </p>
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

        {/* COMPARISON LANES */}
        <div className="grid grid-rows-2 gap-8">
          {/* LANE 1: GLYPHNET (The Wave) */}
          <div
            className={`rounded-[3rem] p-10 border transition-colors duration-700 relative overflow-hidden group ${
              status === "tampered" ? "bg-red-50 border-red-200" : "bg-gray-50 border-gray-100"
            }`}
          >
            <div className="flex justify-between mb-8">
              <div className="space-y-1">
                <span
                  className={`text-[10px] font-bold uppercase tracking-[0.2em] ${
                    status === "tampered" ? "text-red-500" : "text-blue-600"
                  }`}
                >
                  {status === "tampered" ? "Violation Detected" : "Substrate A"}
                </span>
                <h3 className="text-2xl font-bold italic">GlyphNet Wave-Native (QKD)</h3>
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

              {/* Wave Path */}
              <div className="flex-1 relative h-full flex items-center justify-center">
                <AnimatePresence>
                  {isTransmitting && (
                    <motion.div
                      className="absolute left-0 w-full"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                    >
                      {/* Interceptor Icon */}
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
                            // keep your vibe, but avoid the invalid "..." path
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

            {/* QKD Log Output */}
            <div className="mt-8 flex justify-between items-center text-[9px] font-mono uppercase tracking-widest">
              <div className="flex gap-6">
                <p className="text-gray-400">Medium: QKD-Protected Photon</p>
                {isIntercepted && <p className="text-red-600 animate-pulse">Fingerprint Mismatch: Wave Collapse Confirmed</p>}
              </div>
              <p className={status === "tampered" ? "text-red-500" : "text-blue-600"}>Policy: QKD_STRICT_ENFORCE</p>
            </div>
          </div>

          {/* LANE 2: LEGACY (The Pipe) */}
          <div className="bg-gray-50 rounded-[3rem] p-10 border border-gray-100 relative opacity-40 grayscale pointer-events-none">
            <div className="h-full flex items-center justify-center text-gray-400 font-bold italic text-sm">
              Legacy Stack: Vulnerable to Man-in-the-Middle (MITM) without detection.
            </div>
          </div>
        </div>

        {/* REAL-TIME METRICS from SRK-17 */}
        <section className="bg-black text-white rounded-[3rem] p-12 grid grid-cols-4 gap-8">
          <Metric label="Decoherence Risk" glyph={isIntercepted ? "COLLAPSED" : "0.0002%"} legacy="N/A" alert={isIntercepted} />
          <Metric label="Tamper Detection" glyph="Instant (Physical)" legacy="Post-Facto (Log)" highlight />
          <Metric label="Validation Latency" glyph="< 1.2ms" legacy="~45.0ms" highlight />
          <Metric label="Data Integrity" glyph={isIntercepted ? "0.0%" : "99.99%"} legacy="100% (Blind)" alert={isIntercepted} />
        </section>
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