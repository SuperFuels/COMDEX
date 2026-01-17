"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

type Stage = "binary" | "capsule";

const PARAGRAPHS = [
  `1. The "Photonary" Breakthrough (Replacing Binary)
The Binary Problem: Traditional information is "collapsed" into bits, then rehydrated into meaning, creating "Semantic Loss" and massive overhead.
The Photon Solution: Light waves don't carry "bits"; they carry Glyphs via their physical shape, utilizing phase (φ), frequency (f), and coherence (γ).
The "Extra": Because the wave is the symbol, you skip the "parsing" step entirely; the network is an Execution Layer rather than a "dumb pipe".`,

  `2. The "Photon Capsule" in Phase 1
A WaveCapsule (SRK-10) is a hybrid object:
The Logic: Includes the opcode (e.g., ⊕, ↔), args, and metadata — the Symbolic Intent.
The Physics: The WaveState (amplitude, phase, coherence) maps to Photon Capsules.
The Compression: from_symbolic_instruction performs the 56x compression by reducing metadata overhead vs JSON-over-TCP.`,

  `3. Why This Surpasses Modern Networks
SRK-17 highlights "Zero Overhead":
In legacy 5G/6G, packet headers are often larger than the data.
In GlyphNet, the "Header" is the data.
The packet is a Self-Executing Program enabling symbolic portability across photonic, radio, and GWave media.`,

  `4. The "Virtual Substrate" Mechanism
You are simulating a photonic computer on top of binary hardware:
Today (Phase 1): phase is a floating-point value in RAM.
Phase 3: phase becomes a physical property of a laser beam in CodexFiber hardware.
Persistence: every transition produces a Collapse Hash (Hc), preserving symbolic lineage as photons propagate.`,

  `5. Resilience & Decay (The Resonance Ledger)
Temporal coherence is tracked via SRK-14:
Coherence decay: γ(t) = γ0 · e^(−λt)
This determines if a photonic message is still "meaning-stable" before execution.
If coherence falls below threshold, the bridge triggers a collapse or downshift to binary to preserve the underlying logic.`,
] as const;

export default function FullyHookedDemo() {
  const [stage, setStage] = useState<Stage>("binary");
  const [coherence, setCoherence] = useState(1.0);
  const [activeParagraphIndex, setActiveParagraphIndex] = useState<number>(-1);

  const timersRef = useRef<number[]>([]);
  const intervalRef = useRef<number | null>(null);
  const ledgerTriggeredRef = useRef(false);

  const hash = useMemo(() => Math.random().toString(16).slice(2, 8), []);

  const clearTimers = () => {
    timersRef.current.forEach((t) => window.clearTimeout(t));
    timersRef.current = [];
  };

  const clearIntervalRef = () => {
    if (intervalRef.current != null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const reset = useCallback(() => {
    clearTimers();
    clearIntervalRef();
    ledgerTriggeredRef.current = false;

    setStage("binary");
    setCoherence(1.0);
    setActiveParagraphIndex(-1);
  }, []);

  const startBridge = useCallback(() => {
    reset();
    setStage("capsule");

    const t0 = window.setTimeout(() => setActiveParagraphIndex(0), 150);
    const t1 = window.setTimeout(() => setActiveParagraphIndex(1), 3000);
    const t2 = window.setTimeout(() => setActiveParagraphIndex(2), 6000);
    const t3 = window.setTimeout(() => setActiveParagraphIndex(3), 9000);
    timersRef.current.push(t0, t1, t2, t3);
  }, [reset]);

  // coherence decay + ledger trigger
  useEffect(() => {
    if (stage !== "capsule") return;

    // ensure no duplicate interval
    clearIntervalRef();

    intervalRef.current = window.setInterval(() => {
      setCoherence((prev) => {
        const next = Math.max(0, prev * 0.998);

        if (!ledgerTriggeredRef.current && next < 0.85) {
          ledgerTriggeredRef.current = true;
          setActiveParagraphIndex(4);
        }

        return next;
      });
    }, 150);

    return () => {
      clearIntervalRef();
    };
  }, [stage]);

  const activeParagraph =
    activeParagraphIndex >= 0 ? PARAGRAPHS[activeParagraphIndex] : "";

  return (
    <div className="flex flex-col gap-4 p-6 bg-slate-950 text-cyan-400 font-mono border border-cyan-500/40 rounded-xl shadow-2xl">
      <div className="flex justify-between items-center border-b border-cyan-900 pb-4">
        <div>
          <h1 className="text-xl font-bold text-amber-500 tracking-tighter">
            PHOTON BINARY BRIDGE
          </h1>
          <p className="text-[10px] uppercase text-cyan-600">
            Substrate: SRK-17 / GlyphNet v1.2
          </p>
        </div>
        <div className="text-right">
          <p className="text-[9px] text-slate-500 uppercase">Compression</p>
          <p className="text-2xl font-bold text-white">
            {stage === "binary" ? "1x" : "56x"}
          </p>
        </div>
      </div>

      <div className="relative h-64 bg-black rounded-lg border border-slate-800 flex flex-col items-center justify-center overflow-hidden">
        <AnimatePresence mode="wait">
          {stage === "binary" ? (
            <motion.div
              key="bin"
              exit={{ opacity: 0, scale: 1.5 }}
              className="grid grid-cols-12 gap-1 opacity-30"
            >
              {Array(48)
                .fill(0)
                .map((_, i) => (
                  <span key={i} className="text-[8px]">
                    {Math.round(Math.random())}
                  </span>
                ))}
            </motion.div>
          ) : (
            <motion.div
              key="wave"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="w-full px-10"
            >
              <svg width="100%" height="100" viewBox="0 0 400 100">
                <motion.path
                  d="M 0 50 C 50 10, 150 10, 200 50 S 350 90, 400 50"
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth="3"
                  animate={{
                    d: [
                      "M 0 50 C 50 10, 150 10, 200 50 S 350 90, 400 50",
                      "M 0 50 C 50 90, 150 90, 200 50 S 350 10, 400 50",
                    ],
                  }}
                  transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                />
              </svg>
              <div className="flex justify-between mt-4 text-[10px] text-amber-500/70">
                <span>PHASE: 3.14φ</span>
                <span>COHERENCE: {coherence.toFixed(4)}γ</span>
                <span>HASH: Hc_{hash}</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="min-h-[130px] p-4 bg-slate-900/50 border-l-2 border-amber-500 rounded-r">
        <h3 className="text-[10px] font-bold text-amber-500 mb-1 uppercase tracking-widest">
          Technical Substrate Documentation
        </h3>
        <AnimatePresence mode="wait">
          <motion.pre
            key={activeParagraphIndex}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            className="whitespace-pre-wrap text-[11px] leading-relaxed text-slate-300 italic"
          >
            {activeParagraph ||
              "Awaiting Symbolic Instruction... Initializing S-ISA Pipeline."}
          </motion.pre>
        </AnimatePresence>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={reset}
          className="py-2 text-[11px] border border-cyan-900 hover:bg-cyan-900/30 transition uppercase"
        >
          Reset to Binary
        </button>
        <button
          onClick={startBridge}
          className="py-2 text-[11px] bg-amber-600 text-black font-bold hover:bg-amber-500 transition uppercase"
        >
          Trigger WaveCapsule ↔
        </button>
      </div>
    </div>
  );
}