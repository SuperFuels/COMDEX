"use client";

import React from "react";
import ResonancePulseHUD from "./ResonancePulseHUD";

export default function SLEResonanceTab() {
  return (
    // Match Photon Binary tab structure: hero header + centered content container + pitch deck region.
    // ResonancePulseHUD remains unchanged (no functionality/content lost).
    <section className="space-y-16">
      {/* 1. HERO HEADER - Matching Photon Binary Style */}
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
          Resonance Pulse
        </h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          Symbolic Lightwave Engine —{" "}
          <span className="text-black font-medium">morphic coherence.</span>
        </p>
        <p className="max-w-3xl mx-auto text-lg text-gray-500 leading-relaxed">
          A wave-native computation loop where meaning is stabilized inside light.
          Morphic feedback repairs coherence in-flight, and πₛ phase closure seals
          the proof into holographic persistence.
        </p>
      </div>

      {/* 2. LIVE HUD (centered like the other demo) */}
      <div className="max-w-6xl mx-auto">
        <ResonancePulseHUD />
      </div>

      {/* 3. PITCH DECK (UNDERNEATH) - Same layout rhythm */}
      <div className="grid md:grid-cols-2 gap-12 border-t border-gray-100 pt-24">
        {/* The Mechanism */}
        <div className="space-y-8">
          <div className="space-y-4">
            <h2 className="text-3xl font-bold italic tracking-tight">
              The Morphic Coherence Loop
            </h2>
            <p className="text-gray-600 leading-relaxed">
              Standard compute treats instability as failure. The SLE treats it as
              a control problem: entropy (ψ) rises, curvature (κ) reshapes the
              semantic density, and morphic feedback applies ΔC corrections until
              the wavefield stabilizes. When the loop seals to 2π, πₛ phase closure
              flips to OK — not a checksum after the fact, but a closed circuit
              proof.
              <br />
              <br />
              The HUD above visualizes that process directly: the interference
              geometry “repairs” as ΔC is applied, and the final collapse marks a
              committed holographic state.
            </p>
          </div>

          <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100">
            <h4 className="text-sm font-bold uppercase tracking-widest text-amber-600 mb-4">
              Core Mechanism
            </h4>
            <p className="text-sm text-gray-500 leading-relaxed">
              This interface renders the{" "}
              <strong>Photonic Interference Chamber</strong>, streams{" "}
              <strong>Morphic Feedback</strong> events (ΔC), and asserts{" "}
              <strong>πₛ Phase Closure</strong> before exporting a JSON-LD theorem
              proof capsule suitable for a <strong>Resonance Ledger</strong>{" "}
              commit.
            </p>
          </div>
        </div>

        {/* The Impact */}
        <div className="space-y-12">
          <div className="grid grid-cols-1 gap-8">
            <div className="space-y-2">
              <h3 className="text-xl font-bold tracking-tight">
                Why It Matters
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                Offline systems fail when they can’t verify integrity. With SLE,
                the device can hold the mathematical proof of state transitions
                without relying on a live network — enabling sovereign offline
                payments and resilient critical infrastructure coordination.
              </p>
            </div>

            <div className="space-y-2">
              <h3 className="text-xl font-bold tracking-tight">
                Technical Benchmarks
              </h3>
              <ul className="space-y-3 text-sm text-gray-500">
                <li className="flex items-start gap-3">
                  <span className="text-amber-600 font-bold">01.</span>
                  <span>
                    <strong>πₛ Closure:</strong> closed-circuit phase sum (2π)
                    validation as an integrity primitive.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-amber-600 font-bold">02.</span>
                  <span>
                    <strong>Morphic Feedback:</strong> ΔC stabilization events
                    visible in real-time (no opaque “error correction”).
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-amber-600 font-bold">03.</span>
                  <span>
                    <strong>Proof Export:</strong> JSON-LD theorem capsule for
                    replayable verification and ledger commits.
                  </span>
                </li>
              </ul>
            </div>
          </div>

          <div className="p-8 rounded-[2.5rem] bg-black text-white">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">
              The Vision
            </h4>
            <p className="text-xl font-medium italic leading-snug">
              "If binary is the bootloader, coherence is the operating system:
              computation becomes resonance, and integrity becomes phase closure."
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}