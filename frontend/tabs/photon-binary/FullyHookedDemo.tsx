"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

// Technical content derived from SRK-10/12/17 Specifications
const PARAGRAPHS = [
  {
    title: "1. The 'Photonary' Breakthrough",
    text: "Traditional binary information is 'collapsed' into bits, then rehydrated into meaning, creating massive 'Semantic Loss'. GlyphNet light waves don't carry bits; they carry symbols via their physical shape—utilizing phase (φ), frequency (f), and coherence (γ). The network becomes the Execution Layer rather than a dumb pipe.",
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

export default function PhotonBridgeDemo() {
  const [stage, setStage] = useState<"binary" | "capsule">("binary");
  const [coherence, setCoherence] = useState(1.0);
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const [isAutoPlaying, setIsAutoPlaying] = useState(false);
  const [progress, setProgress] = useState(0);

  // ✅ Fix: timers typed correctly for browser + Node builds
  const autoPlayTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const progressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const hash = useMemo(() => Math.random().toString(16).slice(2, 8), []);

  // Cleanup all timers
  const clearAllTimers = useCallback(() => {
    if (autoPlayTimerRef.current) clearInterval(autoPlayTimerRef.current);
    if (progressTimerRef.current) clearInterval(progressTimerRef.current);
    autoPlayTimerRef.current = null;
    progressTimerRef.current = null;
    setProgress(0);
  }, []);

  const reset = useCallback(() => {
    clearAllTimers();
    setIsAutoPlaying(false);
    setStage("binary");
    setCoherence(1.0);
    setActiveIndex(-1);
  }, [clearAllTimers]);

  // ✅ Fix: typed param
  const goToIndex = (index: number) => {
    clearAllTimers();
    setIsAutoPlaying(false);
    setStage("capsule");
    setActiveIndex(index);
  };

  const handleNext = () => {
    const nextIndex = (activeIndex + 1) % PARAGRAPHS.length;
    goToIndex(nextIndex);
  };

  const handlePrev = () => {
    const prevIndex = activeIndex <= 0 ? PARAGRAPHS.length - 1 : activeIndex - 1;
    goToIndex(prevIndex);
  };

  const startAutoPlayCycle = useCallback(() => {
    setProgress(0);

    // 10-second interval for reading comprehension
    autoPlayTimerRef.current = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % PARAGRAPHS.length);
      setProgress(0);
    }, 10000);

    // Smooth progress bar update
    progressTimerRef.current = setInterval(() => {
      setProgress((p) => Math.min(p + 1, 100));
    }, 100);
  }, []);

  const toggleAutoPlay = () => {
    if (isAutoPlaying) {
      clearAllTimers();
      setIsAutoPlaying(false);
    } else {
      setStage("capsule");
      setIsAutoPlaying(true);
      if (activeIndex === -1) setActiveIndex(0);
      startAutoPlayCycle();
    }
  };

  // ✅ Optional safety: clear timers if user navigates away while autoplaying
  useEffect(() => {
    return () => clearAllTimers();
  }, [clearAllTimers]);

  // Coherence Decay Simulation
  useEffect(() => {
    if (stage !== "capsule") return;
    const decay = setInterval(() => {
      setCoherence((prev) => Math.max(0.15, prev * 0.9997));
    }, 300);
    return () => clearInterval(decay);
  }, [stage]);

  return (
    <div className="w-full bg-white text-black py-20 selection:bg-blue-100">
      <div className="max-w-7xl mx-auto px-8 space-y-16">
        {/* DEMO CONTAINER */}
        <section className="bg-gray-50 rounded-[3rem] border border-gray-100 p-8 md:p-16 shadow-xl relative overflow-visible">
          <div className="grid lg:grid-cols-2 gap-16">
            {/* VISUALIZER (Left Side) */}
            <div className="space-y-8">
              <div className="flex justify-between items-center px-4">
                <div className="space-y-1">
                  <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Signal Media</p>
                  <p className="text-2xl font-bold italic tracking-tighter">
                    {stage === "binary" ? "Legacy Static" : "Photon Capsule"}
                  </p>
                </div>
                <div className="text-right space-y-1">
                  <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Coherence γ</p>
                  <p className="text-2xl font-mono text-blue-600 font-bold">{(coherence * 100).toFixed(2)}%</p>
                </div>
              </div>

              {/* The "Black Box" Visualizer */}
              <div className="h-[500px] bg-black rounded-[2.5rem] relative flex items-center justify-center overflow-hidden shadow-2xl group border-[12px] border-gray-900/10">
                <AnimatePresence mode="wait">
                  {stage === "binary" ? (
                    <motion.div
                      key="bin"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 0.25 }}
                      exit={{ opacity: 0 }}
                      className="grid grid-cols-8 gap-6 text-blue-500 font-mono text-[10px]"
                    >
                      {Array(64)
                        .fill(0)
                        .map((_, i) => (
                          <span key={i} className="animate-pulse">
                            {Math.round(Math.random())}
                          </span>
                        ))}
                    </motion.div>
                  ) : (
                    <motion.div
                      key="wave"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="w-full flex flex-col items-center"
                    >
                      {/* WAVEFORM DIAGRAM */}
                      <svg
                        width="90%"
                        height="200"
                        viewBox="0 0 400 100"
                        className="drop-shadow-[0_0_25px_rgba(59,130,246,0.6)]"
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
                          transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
                        />
                      </svg>

                      <div className="mt-12 text-center space-y-4">
                        <div className="flex gap-8 justify-center">
                          <div className="text-[10px] font-mono text-gray-500 uppercase">
                            Phase: <span className="text-white">3.141φ</span>
                          </div>
                          <div className="text-[10px] font-mono text-gray-500 uppercase">
                            Entropy: <span className="text-white">{(1 - coherence).toFixed(4)}</span>
                          </div>
                        </div>
                        <p className="text-blue-400 font-mono text-[10px] tracking-[0.4em] bg-blue-950/30 px-4 py-1 rounded-full border border-blue-900/50">
                          ID: Hc_{hash}
                        </p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Visualizer Buttons */}
                <div className="absolute bottom-8 flex gap-4">
                  <button
                    onClick={reset}
                    className="px-8 py-3 bg-white/5 hover:bg-white/10 backdrop-blur-xl rounded-full text-[11px] text-white font-bold uppercase tracking-widest border border-white/10 transition-all"
                  >
                    Reset Substrate
                  </button>
                  <button
                    onClick={toggleAutoPlay}
                    className={`px-8 py-3 rounded-full text-[11px] text-white font-bold uppercase tracking-widest transition-all shadow-xl ${
                      isAutoPlaying ? "bg-red-600 shadow-red-500/20" : "bg-blue-600 shadow-blue-500/40"
                    }`}
                  >
                    {isAutoPlaying ? "Stop Auto-Flow" : "Start Sequence"}
                  </button>
                </div>
              </div>
            </div>

            {/* CONTENT (Right Side) */}
            <div className="flex flex-col justify-between py-10 min-h-[500px]">
              <div className="space-y-10">
                <AnimatePresence mode="wait">
                  {activeIndex === -1 ? (
                    <motion.div
                      key="intro"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-6"
                    >
                      <h2 className="text-5xl font-bold italic tracking-tighter leading-none">The Photon-Binary Bridge</h2>
                      <p className="text-2xl text-gray-400 font-light leading-relaxed italic">
                        Initialize the SRK-10 sequence to observe wave-native networking logic.
                      </p>
                      <button
                        onClick={handleNext}
                        className="group flex items-center gap-4 text-blue-600 font-bold uppercase text-xs tracking-[0.2em] pt-4"
                      >
                        Launch Documentation <span className="group-hover:translate-x-3 transition-transform text-xl">→</span>
                      </button>
                    </motion.div>
                  ) : (
                    <motion.div
                      key={activeIndex}
                      initial={{ opacity: 0, x: 30 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -30 }}
                      className="space-y-8"
                    >
                      <div className="flex items-center gap-4">
                        <span className="w-12 h-12 rounded-2xl bg-blue-600 flex items-center justify-center text-white font-bold italic text-xl shadow-lg shadow-blue-500/20">
                          {activeIndex + 1}
                        </span>
                        <div className="h-[1px] flex-1 bg-gray-200" />
                        <span className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">
                          Reference // SRK-SPEC-v1.2
                        </span>
                      </div>

                      <h2 className="text-4xl font-bold italic tracking-tighter text-black">{PARAGRAPHS[activeIndex].title}</h2>
                      <p className="text-2xl text-gray-600 leading-relaxed font-light italic border-l-4 border-blue-600 pl-8">
                        "{PARAGRAPHS[activeIndex].text}"
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* NAV CONTROLS */}
              <div className="pt-12 space-y-8">
                {/* Reading Progress Bar */}
                {isAutoPlaying && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-[10px] font-mono text-blue-600 uppercase tracking-widest font-bold">
                      <span>Reading Time</span>
                      <span>{Math.round(10 - progress / 10)}s</span>
                    </div>
                    <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-blue-600"
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={{ ease: "linear" }}
                      />
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <div className="flex gap-4">
                    <button
                      onClick={handlePrev}
                      className="w-14 h-14 rounded-full border border-gray-200 flex items-center justify-center hover:bg-white hover:shadow-lg transition-all text-xl"
                    >
                      ←
                    </button>
                    <button
                      onClick={handleNext}
                      className="w-14 h-14 rounded-full border border-gray-200 flex items-center justify-center hover:bg-white hover:shadow-lg transition-all text-xl"
                    >
                      →
                    </button>
                  </div>

                  {/* Bullet Navigation */}
                  <div className="flex gap-3">
                    {PARAGRAPHS.map((_, i) => (
                      <button
                        key={i}
                        onClick={() => goToIndex(i)}
                        className={`h-2 rounded-full transition-all duration-500 ${
                          activeIndex === i ? "w-12 bg-blue-600" : "w-2 bg-gray-200 hover:bg-gray-400"
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECONDARY TECHNICAL CARDS */}
        <section className="grid md:grid-cols-3 gap-10">
          <div className="p-12 bg-gray-50 rounded-[3rem] border border-gray-100 hover:border-blue-100 transition-colors group">
            <p className="text-blue-600 font-bold text-xs uppercase tracking-widest mb-6">Efficiency</p>
            <h3 className="text-3xl font-bold italic mb-4 group-hover:text-blue-600 transition-colors tracking-tighter">
              56x Metadata Reduction
            </h3>
            <p className="text-gray-500 text-lg leading-relaxed font-light">
              By utilizing the WaveCapsule protocol, GlyphNet bypasses standard IP overhead, enabling zero-latency symbolic
              exchange.
            </p>
          </div>
          <div className="p-12 bg-black text-white rounded-[3rem] shadow-2xl relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:scale-110 transition-transform">
              <svg width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
            </div>
            <p className="text-blue-400 font-bold text-xs uppercase tracking-widest mb-6">Security</p>
            <h3 className="text-3xl font-bold italic mb-4 tracking-tighter text-blue-400">Tamper-Proof Entanglement</h3>
            <p className="text-gray-400 text-lg leading-relaxed font-light">
              Quantum Key Distribution (QKD) ensures that any observation forces a wave collapse, making tampering physically
              evident.
            </p>
          </div>
          <div className="p-12 bg-gray-50 rounded-[3rem] border border-gray-100 hover:border-blue-100 transition-colors group">
            <p className="text-blue-600 font-bold text-xs uppercase tracking-widest mb-6">Execution</p>
            <h3 className="text-3xl font-bold italic mb-4 group-hover:text-blue-600 transition-colors tracking-tighter">
              Lyapunov Stability
            </h3>
            <p className="text-gray-500 text-lg leading-relaxed font-light">
              The Resonance Ledger monitors temporal coherence, ensuring that only meaning-stable packets reach the execution
              layer.
            </p>
          </div>
        </section>

        <footer className="pt-20 pb-10 border-t border-gray-100 text-center opacity-40">
          <p className="font-mono text-[10px] uppercase tracking-[0.6em]">
            Tessaris Research Group // SRK-10 Photon Bridge Substrate // 2026
          </p>
        </footer>
      </div>
    </div>
  );
}