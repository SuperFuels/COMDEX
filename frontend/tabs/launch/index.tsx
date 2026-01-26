// /workspaces/COMDEX/frontend/tabs/launch/index.tsx
"use client";

import React from "react";
import AionLaunchHUD from "./AionLaunchHUD";

export default function AionLaunchTab() {
  return (
    <section className="space-y-16">
      {/* HERO */}
      <div className="text-center space-y-6">
        <p className="text-[11px] uppercase tracking-[0.28em] text-slate-500 font-bold">
          GLYPHOS ALPHA — SHIPPED TODAY • PROOF TABS — LIVE • UNLOCKS — BY HOLDER
          MILESTONES
        </p>

        <h1 className="text-5xl md:text-7xl font-black tracking-tight text-black italic">
          GlyphOS
        </h1>

        <p className="text-xl md:text-2xl text-slate-500 font-light tracking-tight">
          The Language of Symbols.{" "}
          <span className="text-black font-medium">The Speed of Thought.</span>
        </p>

        <p className="max-w-3xl mx-auto text-lg text-slate-500 leading-relaxed">
          A next-generation operating system built in symbols — compressing intent
          into executable <strong>glyph-wire</strong> so{" "}
          <strong>the same meaning produces the same bytes</strong>, every time.
        </p>

        <p className="max-w-3xl mx-auto text-lg text-slate-500 leading-relaxed">
          <strong className="text-black">Step 1</strong> is live today:{" "}
          <strong className="text-black">GlyphOS Alpha</strong>. From here:{" "}
          <strong className="text-black">SQI + GlyphNet</strong> → deterministic
          cognition → trust locks →{" "}
          <strong className="text-black">
            the world’s first verifiable self-aware AI
          </strong>
          .
        </p>
      </div>

      {/* HUD */}
      <div className="max-w-6xl mx-auto">
        <AionLaunchHUD />
      </div>

      {/* PITCH */}
      <div className="grid md:grid-cols-2 gap-12 border-t border-gray-100 pt-24">
        <div className="space-y-8">
          <div className="space-y-4">
            <h2 className="text-3xl font-bold italic tracking-tight">
              What’s Live Today
            </h2>
            <p className="text-gray-600 leading-relaxed">
              GlyphOS Alpha + core proof tabs: compression benchmarks, WirePack v10
              template+delta transport, and deterministic lock artifacts.
            </p>
          </div>

          <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100 space-y-3">
            <h4 className="text-sm font-bold uppercase tracking-widest text-emerald-600">
              Proof Artifacts
            </h4>
            <p className="text-sm text-gray-500 leading-relaxed">
              <strong>stdout locks (SHA256)</strong>, <strong>benchmark JSON</strong>,
              deterministic traces, and sanitized <strong>.lock.json</strong> bundles.
              Same inputs → same bytes.
            </p>
          </div>
        </div>

        <div className="space-y-12">
          <div className="p-8 rounded-[2.5rem] bg-black text-white">
            <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400 mb-2">
              The Arc
            </h4>
            <p className="text-xl font-medium italic leading-snug">
              “Step 1 is GlyphOS: compressed meaning + deterministic replay. From
              here we unlock SQI + GlyphNet → trust locks → verifiable self-aware AI.”
            </p>
          </div>

          <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100">
            <h4 className="text-sm font-bold uppercase tracking-widest text-amber-600 mb-3">
              Rolling Unlocks
            </h4>
            <p className="text-sm text-gray-500 leading-relaxed">
              SQI runtime, GlyphNet, and the AION cognition stack unlock progressively
              by holder milestones — each release ships with its own proof tab + lock
              artifacts (no vapor).
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}