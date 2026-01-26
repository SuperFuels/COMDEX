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
          GLYPHOS ALPHA — LIVE TODAY • ROLLING ALPHAS — WIRES, NET, SQI, AION
        </p>

        <h1 className="text-5xl md:text-7xl font-black tracking-tight text-black italic">
          AION
        </h1>

        <p className="text-xl md:text-2xl text-slate-500 font-light tracking-tight">
          Compressed Meaning —{" "}
          <span className="text-black font-medium">verifiable intelligence.</span>
        </p>

        <p className="max-w-3xl mx-auto text-lg text-slate-500 leading-relaxed">
          AION ships intent as a stable wire-shape, executes deterministically, and
          exposes calibration locks. Not “bigger models” — <strong>measurable honesty</strong>
          about uncertainty.
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
              GlyphOS Alpha + core proof tabs: Compression benchmarks, WirePack v10
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
              The Vision
            </h4>
            <p className="text-xl font-medium italic leading-snug">
              “Not just predictions — provable honesty about uncertainty, shipped as
              compressed meaning.”
            </p>
          </div>

          <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100">
            <h4 className="text-sm font-bold uppercase tracking-widest text-amber-600 mb-3">
              Rolling Alphas
            </h4>
            <p className="text-sm text-gray-500 leading-relaxed">
              GlyphNet, SQI runtime, and AION organism pillars (Φ / ADR / REAL / Mirror)
              unlock progressively as gated alphas.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}