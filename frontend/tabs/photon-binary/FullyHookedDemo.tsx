"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

// High-level narrative for the "Why it's good" paragraphs
const PARAGRAPHS = [
  {
    title: "1. The 'Photonary' Breakthrough",
    text: "Traditional binary information is 'collapsed' into bits, then rehydrated into meaning, creating massive 'Semantic Loss'. GlyphNet light waves don't carry bits; they carry symbols via their physical shape—utilizing phase (φ), frequency (f), and coherence (γ). You skip the parsing step entirely; the network becomes the Execution Layer.",
  },
  {
    title: "2. The WaveCapsule (SRK-10)",
    text: "A WaveCapsule is a hybrid object where the logic (opcodes like ⊕, ↔) is bound directly to the physics. By mapping symbolic instructions to photon capsules, we achieve a 56x compression efficiency, drastically reducing metadata overhead compared to legacy JSON-over-TCP protocols.",
  },
  {
    title: "3. Surpassing Modern Networks",
    text: "In legacy 5G/6G, packet headers are often larger than the data they carry. In GlyphNet, the 'Header' is the data. The packet is a self-executing program, enabling total symbolic portability across photonic, radio, and GWave media without re-encoding.",
  },
  {
    title: "4. Virtual Substrate Mechanism",
    text: "We are simulating a photonic computer on classical hardware. While Phase 1 treats 'phase' as a float in RAM, Phase 3 transitions this to physical properties of laser beams in CodexFiber hardware. Every state transition produces a Collapse Hash (Hc), preserving symbolic lineage.",
  },
  {
    title: "5. Resilience & The Resonance Ledger",
    text: "Temporal coherence is tracked via SRK-14 using the decay formula: γ(t) = γ0 · e^(−λt). This determines if a message is 'meaning-stable'. If coherence falls below the Lyapunov threshold, the system triggers a fail-closed collapse to preserve the underlying logic.",
  },
];

export default function FullyHookedDemo() {
  const [stage, setStage] = useState<"binary" | "capsule">("binary");
  const [coherence, setCoherence] = useState(1.0);
  const [activeParagraphIndex, setActiveParagraphIndex] = useState(-1);

  const timersRef = useRef<number[]>([]);
  const intervalRef = useRef<number | null>(null);
  const ledgerTriggeredRef = useRef(false);

  const hash = useMemo(() => Math.random().toString(16).slice(2, 8), []);

  const reset = useCallback(() => {
    timersRef.current.forEach((t) => window.clearTimeout(t));
    timersRef.current = [];
    if (intervalRef.current) window.clearInterval(intervalRef.current);
    intervalRef.current = null;
    ledgerTriggeredRef.current = false;

    setStage("binary");
    setCoherence(1.0);
    setActiveParagraphIndex(-1);
  }, []);

  const startBridge = useCallback(() => {
    reset();
    setStage("capsule");

    // Sequence the paragraphs for a storytelling effect
    const schedule = [150, 3000, 6000, 9000];
    schedule.forEach((ms, idx) => {
      timersRef.current.push(
        window.setTimeout(() => setActiveParagraphIndex(idx), ms)
      );
    });
  }, [reset]);

  useEffect(() => {
    if (stage !== "capsule") return;

    // ensure no duplicate interval
    if (intervalRef.current) window.clearInterval(intervalRef.current);

    intervalRef.current = window.setInterval(() => {
      setCoherence((prev) => {
        const next = Math.max(0, prev * 0.9985);

        if (!ledgerTriggeredRef.current && next < 0.88) {
          ledgerTriggeredRef.current = true;
          setActiveParagraphIndex(4);
        }

        return next;
      });
    }, 150);

    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    };
  }, [stage]);

  return (
    // FIXES:
    // 1) remove min-h-screen (can fight the tab panel scroll container)
    // 2) remove internal header to prevent "double header" with the tab page hero
    <div className="w-full bg-white text-black selection:bg-blue-100">
      {/* Scrollable Container */}
      <div className="max-w-6xl mx-auto px-6 space-y-24">
        {/* Main Demo UI Card */}
        {/* FIX: remove overflow-hidden here (can swallow scroll in some tab containers) */}
        <section className="bg-gray-50 rounded-[3rem] p-4 md:p-12 border border-gray-100 shadow-sm">
          <div className="grid lg:grid-cols-2 gap-12">
            {/* Visualizer Side */}
            <div className="space-y-6">
              <div className="flex justify-between items-end px-4">
                <div className="space-y-1">
                  <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                    Signal Media
                  </p>
                  <p className="text-xl font-bold italic">
                    {stage === "binary" ? "Static Binary" : "Photon Capsule"}
                  </p>
                </div>
                <div className="text-right space-y-1">
                  <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                    Coherence
                  </p>
                  <p className="text-xl font-mono text-blue-600 font-bold">
                    {(coherence * 100).toFixed(2)}%
                  </p>
                </div>
              </div>

              {/* keep overflow-hidden here (only for the visual box) */}
              <div className="h-[400px] bg-black rounded-[2.5rem] relative flex items-center justify-center overflow-hidden shadow-2xl">
                <AnimatePresence mode="wait">
                  {stage === "binary" ? (
                    <motion.div
                      key="bin"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 0.2 }}
                      exit={{ opacity: 0 }}
                      className="grid grid-cols-8 gap-4 text-white font-mono text-xs"
                    >
                      {Array(64)
                        .fill(0)
                        .map((_, i) => (
                          <span key={i}>{Math.round(Math.random())}</span>
                        ))}
                    </motion.div>
                  ) : (
                    <motion.div
                      key="wave"
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="w-full flex flex-col items-center"
                    >
                      <svg
                        width="80%"
                        height="120"
                        viewBox="0 0 400 100"
                        className="drop-shadow-[0_0_15px_rgba(59,130,246,0.5)]"
                      >
                        <motion.path
                          d="M 0 50 C 50 10, 150 10, 200 50 S 350 90, 400 50"
                          fill="none"
                          stroke="#3b82f6"
                          strokeWidth="3"
                          strokeLinecap="round"
                          animate={{
                            d: [
                              "M 0 50 C 50 10, 150 10, 200 50 S 350 90, 400 50",
                              "M 0 50 C 50 90, 150 90, 200 50 S 350 10, 400 50",
                            ],
                          }}
                          transition={{
                            repeat: Infinity,
                            duration: 2,
                            ease: "easeInOut",
                          }}
                        />
                      </svg>
                      <div className="mt-12 grid grid-cols-2 gap-x-12 gap-y-4 text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                        <div>
                          Phase: <span className="text-white">3.141φ</span>
                        </div>
                        <div>
                          Hash: <span className="text-white">Hc_{hash}</span>
                        </div>
                        <div className="col-span-2 text-center text-blue-400">
                          Status: Entangled Stream Active
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={reset}
                  className="py-5 rounded-full border border-gray-200 text-xs font-bold uppercase tracking-widest hover:bg-white transition-all"
                >
                  Reset State
                </button>
                <button
                  onClick={startBridge}
                  className="py-5 rounded-full bg-blue-600 text-white text-xs font-bold uppercase tracking-widest hover:bg-blue-700 shadow-xl shadow-blue-500/20 transition-all"
                >
                  Trigger Bridge
                </button>
              </div>
            </div>

            {/* Content Side */}
            <div className="flex flex-col justify-center space-y-8 lg:pl-6">
              <div className="min-h-[300px] flex flex-col justify-center">
                <AnimatePresence mode="wait">
                  {activeParagraphIndex === -1 ? (
                    <motion.div
                      key="idle"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="space-y-4"
                    >
                      <h2 className="text-3xl font-bold italic">
                        Awaiting symbolic instruction...
                      </h2>
                      <p className="text-gray-400 leading-relaxed font-light">
                        Initialize the Photonary bridge to see how GlyphNet
                        transforms legacy binary data into self-executing
                        photonic logic.
                      </p>
                    </motion.div>
                  ) : (
                    <motion.div
                      key={activeParagraphIndex}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="space-y-6"
                    >
                      <h2 className="text-3xl font-bold italic text-blue-600">
                        {PARAGRAPHS[activeParagraphIndex].title}
                      </h2>
                      <p className="text-xl text-gray-600 leading-relaxed font-light italic">
                        {PARAGRAPHS[activeParagraphIndex].text}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="flex gap-2">
                {PARAGRAPHS.map((_, i) => (
                  <div
                    key={i}
                    className={`h-1 flex-1 rounded-full transition-all duration-500 ${
                      activeParagraphIndex >= i ? "bg-blue-600" : "bg-gray-200"
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Supporting Narrative Cards */}
        <section className="grid md:grid-cols-3 gap-8">
          <div className="p-10 bg-gray-50 rounded-[3rem] space-y-4 border border-gray-100">
            <p className="text-blue-600 font-bold text-xs uppercase tracking-widest">
              Performance
            </p>
            <h3 className="text-2xl font-bold italic">56x Reduction</h3>
            <p className="text-gray-500 text-sm leading-relaxed">
              By treating light as the message itself rather than a carrier for
              binary, we eliminate the metadata bloat found in TCP/IP.
            </p>
          </div>

          <div className="p-10 bg-black text-white rounded-[3rem] space-y-4 shadow-2xl">
            <p className="text-blue-400 font-bold text-xs uppercase tracking-widest">
              Security
            </p>
            <h3 className="text-2xl font-bold italic">Collapse Hashes</h3>
            <p className="text-gray-400 text-sm leading-relaxed">
              Every state transition is cryptographically bound to its physical
              wave properties, making tampering physically impossible.
            </p>
          </div>

          <div className="p-10 bg-gray-50 rounded-[3rem] space-y-4 border border-gray-100">
            <p className="text-blue-600 font-bold text-xs uppercase tracking-widest">
              Hardware
            </p>
            <h3 className="text-2xl font-bold italic">Edge Native</h3>
            <p className="text-gray-500 text-sm leading-relaxed">
              Runs on classical silicon today via SQI, transitioning to native
              photonic fibers in the next iteration.
            </p>
          </div>
        </section>

        {/* Footer info to ensure scrolling depth */}
        <footer className="pt-24 pb-12 border-t border-gray-100 text-center">
          <p className="text-gray-300 font-mono text-[10px] uppercase tracking-[0.5em]">
            Tessaris Research Group // SRK-17 Pipeline
          </p>
        </footer>
      </div>
    </div>
  );
}