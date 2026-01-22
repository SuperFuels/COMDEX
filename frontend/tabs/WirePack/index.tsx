"use client";

import React from "react";
import WirePackWorkbench from "./WirePackWorkbench";

export default function WirePackTab() {
  return (
    <section className="space-y-16">
      {/* 1) HERO HEADER (match Awareness tab rhythm) */}
      <div className="text-center space-y-6">
        <h1 className="text-7xl md:text-9xl font-bold tracking-tight text-black italic">
          WirePack
        </h1>

        <p className="text-2xl text-gray-500 font-light tracking-tight">
          GlyphOS Transport Layer —{" "}
          <span className="text-black font-medium">streaming receipts + trust.</span>
        </p>

        <p className="max-w-3xl mx-auto text-lg text-gray-500 leading-relaxed">
          WirePack is the canonical transport path: template + delta streaming, deterministic
          receipts, and verifiable integrity locks. Start with v46 streaming transport, then
          switch modes (transport / analytics / trust) using the workbench controls.
        </p>

        <div className="flex flex-wrap justify-center gap-2 pt-2">
          <span className="px-4 py-2 rounded-full text-[11px] font-bold uppercase tracking-widest border border-gray-200 bg-white text-gray-700">
            v46 Streaming
          </span>
          <span className="px-4 py-2 rounded-full text-[11px] font-bold uppercase tracking-widest border border-gray-200 bg-white text-gray-700">
            Template + Delta
          </span>
          <span className="px-4 py-2 rounded-full text-[11px] font-bold uppercase tracking-widest border border-gray-200 bg-white text-gray-700">
            Receipt Chain
          </span>
          <span className="px-4 py-2 rounded-full text-[11px] font-bold uppercase tracking-widest border border-gray-200 bg-white text-gray-700">
            Lockable Proofs
          </span>
        </div>
      </div>

      {/* 2) LIVE DEMO (centered, wider container like the others) */}
      <div className="max-w-7xl mx-auto">
        <WirePackWorkbench />
      </div>

      {/* 3) PITCH DECK / EXPLAINER (underneath, same layout rhythm) */}
      <div className="grid md:grid-cols-2 gap-12 border-t border-gray-100 pt-24">
        {/* The Mechanism */}
        <div className="space-y-8">
          <div className="space-y-4">
            <h2 className="text-3xl font-bold italic tracking-tight">
              Streaming Transport with Proof
            </h2>
            <p className="text-gray-600 leading-relaxed">
              Legacy protocols move bytes and hope meaning survives. WirePack moves{" "}
              <strong>structured programs</strong> using a stable template and compact deltas,
              producing a deterministic receipt chain as it streams.
              <br />
              <br />
              The workbench exposes the full loop: encode → stream → verify → lock.
              Switch between <strong>transport</strong>, <strong>analytics</strong>, and{" "}
              <strong>trust</strong> views without changing the underlying artifacts.
            </p>
          </div>

          <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100">
            <h4 className="text-sm font-bold uppercase tracking-widest text-amber-600 mb-4">
              What You’re Seeing
            </h4>
            <p className="text-sm text-gray-500 leading-relaxed">
              WirePack streams a canonical payload as <strong>Template + Delta</strong>, emits
              per-step <strong>receipts</strong>, and validates end-to-end integrity with
              lockable checkpoints. It’s not compression-as-a-trick — it’s{" "}
              <strong>transport that carries proof</strong>.
            </p>
          </div>
        </div>

        {/* The Impact */}
        <div className="space-y-12">
          <div className="grid grid-cols-1 gap-8">
            <div className="space-y-2">
              <h3 className="text-xl font-bold tracking-tight">Why It Matters</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                If the network can transport data <em>and</em> verification in the same flow,
                you get a foundation for offline delivery, intermittent links, and trustable
                replication — without relying on heavyweight middleware.
              </p>
            </div>

            <div className="space-y-2">
              <h3 className="text-xl font-bold tracking-tight">Core Benchmarks</h3>
              <ul className="space-y-3 text-sm text-gray-500">
                <li className="flex items-start gap-3">
                  <span className="text-amber-600 font-bold">01.</span>
                  <span>
                    <strong>Template + Delta:</strong> minimize repeated structure while preserving canonical meaning.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-amber-600 font-bold">02.</span>
                  <span>
                    <strong>Receipt Chain:</strong> per-step receipts make streaming verifiable, not just transferable.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-amber-600 font-bold">03.</span>
                  <span>
                    <strong>Locks:</strong> checkpoints allow “this exact run happened” claims to be sealed and replayed.
                  </span>
                </li>
              </ul>
            </div>
          </div>

          <div className="p-8 rounded-[2.5rem] bg-black text-white">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">
              The Principle
            </h4>
            <p className="text-xl font-medium italic leading-snug">
              "Transport isn’t moving bytes — it’s moving meaning with a trail of receipts
              that can be verified, locked, and replayed."
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}