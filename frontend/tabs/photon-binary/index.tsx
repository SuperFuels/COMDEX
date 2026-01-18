"use client";

import FullyHookedDemo from "./FullyHookedDemo";

export default function BridgeTab() {
  return (
    // FIX: match the working tabs (Glyph) — no pb-24 / mt-32 patterns that can fight a parent scroll container.
    // Content is unchanged.
    <section className="space-y-16">
      {/* 1. HERO HEADER - Matching Compression Style */}
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
          Photon Binary
        </h1>
        <p className="text-2xl text-gray-500 font-light tracking-tight">
          Beyond the binary bootloader —{" "}
          <span className="text-black font-medium">wave-native logic.</span>
        </p>
        <p className="max-w-3xl mx-auto text-lg text-gray-500 leading-relaxed">
          The transition from discrete digital logic to continuous photonic
          resonance. A network where the medium and the message are
          indistinguishable.
        </p>
      </div>

      {/* 2. LIVE INTERACTIVE BRIDGE DEMO */}
      <div className="max-w-5xl mx-auto">
        <FullyHookedDemo />
      </div>

      {/* 3. THE PITCH DECK (UNDERNEATH) */}
      <div className="grid md:grid-cols-2 gap-12 border-t border-gray-100 pt-24">
        {/* The Strategy */}
        <div className="space-y-8">
          <div className="space-y-4">
            <h2 className="text-3xl font-bold italic tracking-tight">
              The Virtual Substrate
            </h2>
            <p className="text-gray-600 leading-relaxed">
              Standard networking treats light as a "dumb pipe" for binary data.
              <strong>GlyphNet inverts the stack.</strong> By utilizing
              Phase-Coherent photonic fields, we enable symbolic computation
              that is 56x more efficient than traditional intensity-based
              optical binary.
              <br />
              <br />
              We are simulating a photonic computer on top of classical
              hardware. While Phase 1 uses floating-point values in RAM to mock
              wave behavior, Phase 3 will map these instructions directly to
              laser-tuned spatial metrics.
            </p>
          </div>

          <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100">
            <h4 className="text-sm font-bold uppercase tracking-widest text-amber-600 mb-4">
              Core Mechanism
            </h4>
            <p className="text-sm text-gray-500 leading-relaxed">
              The demo above visualizes the{" "}
              <strong>PhotonBinary Bridge (SRK-10)</strong>. It tracks the{" "}
              <strong>Resonance Ledger</strong> in real-time, simulating
              coherence decay and triggering symbolic collapse when stability
              thresholds are breached.
            </p>
          </div>
        </div>

        {/* The Impact */}
        <div className="space-y-12">
          <div className="grid grid-cols-1 gap-8">
            <div className="space-y-2">
              <h3 className="text-xl font-bold tracking-tight">
                Why It Surpasses 5G/6G
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                In the legacy world, packet headers create massive semantic loss
                and overhead. With <strong>Zero-Overhead Routing</strong>, the
                waveform shape itself is the instruction. There is no parsing—only
                resonance.
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
                    <strong>SRK-17 Efficiency:</strong> 56x reduction in metadata
                    overhead vs JSON-over-TCP.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-amber-600 font-bold">02.</span>
                  <span>
                    <strong>Validation:</strong> &lt;1.2ms latency for full
                    SHA3-512 integrity and SoulLaw enforcement.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-amber-600 font-bold">03.</span>
                  <span>
                    <strong>Coherence:</strong> 99.98% stability over 10,000
                    recursive symbolic operations.
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
              "The SRK-10 architecture proves that binary is merely the
              bootloader. We are moving toward a future where computation is
              resonance and communication is entanglement."
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}