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
          GLYPHOS ALPHA — SHIPPED TODAY • PROOF REPO — LIVE • UNLOCKS — BY HOLDER
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

      {/* EXPLAINER (replaces the old 4 containers) */}
      <div className="border-t border-gray-100 pt-16">
        <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-8">
          {/* LEFT: Plain-English explainer */}
          <div className="rounded-[2.5rem] border border-slate-200 bg-white p-7 md:p-10 space-y-8">
            <div className="space-y-3">
              <h2 className="text-3xl md:text-4xl font-black italic tracking-tight text-black">
                GlyphOS in Plain English
              </h2>
              <p className="text-slate-600 leading-relaxed">
                Most systems ship <em>pages</em> of text or bloated metadata to describe an action.
                GlyphOS ships a <strong>tiny glyph program</strong> — a compact wire-shape —
                that executes deterministically and produces a replayable trace.
              </p>
            </div>

            {/* Why significant */}
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold">
                  Why it’s significant
                </div>
                <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                  It turns meaning into a stable executable shape: transportable, versionable,
                  and replayable. That makes auditing and governance tractable.
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold">
                  What it enables
                </div>
                <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                  Dense symbolic programs on the wire — edge devices, agents, and networks can
                  ship whole intentions with minimal bytes and deterministic outcomes.
                </p>
              </div>
            </div>

            {/* One-glyph / wire-shape example */}
            <div className="rounded-[2rem] border border-slate-200 bg-white p-5">
              <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold mb-2">
                Example: “One glyph” can represent a whole program shape
              </div>
              <p className="text-sm text-slate-600 leading-relaxed mb-3">
                GlyphOS represents programs as nested operator trees (“wire-shapes”).
                A compact expression becomes a small, transport-friendly structure.
              </p>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 font-mono text-xs text-slate-700 whitespace-pre-wrap">
{`Human: (A ↔ B) ⊕ C
Wire:  { "⊕": [ { "↔": ["A","B"] }, "C" ] }

Human: f''(x) → repeat_n(step) → ∇(result)
Wire:  { "→": [
          { "f''": ["x"] },
          { "←-": { "n": n, "do": "step" } },
          { "∇": ["result"] }
        ] }`}
              </div>
            </div>

            {/* Proof + performance summary */}
            <div className="rounded-[2rem] border border-emerald-200 bg-emerald-50 p-5">
              <div className="text-[11px] uppercase tracking-[0.22em] text-emerald-700 font-bold">
                What’s live today (and measurable)
              </div>
              <p className="mt-2 text-sm text-emerald-900 leading-relaxed">
                GlyphOS Alpha + compression benchmarks + WirePack v10 template+delta transport +
                deterministic lock artifacts. Benchmarks show roughly{" "}
                <strong>~51–61× smaller raw</strong> and <strong>~11–12.5× smaller after gzip</strong>{" "}
                vs verbose baselines (ratios improve with complexity).
              </p>
            </div>
          </div>

          {/* RIGHT: Clean “Arc” + unlocks + proof artifacts */}
          <div className="rounded-[2.5rem] bg-black text-white p-7 md:p-10 space-y-8">
            <div className="space-y-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">
                The Arc
              </div>
              <p className="text-xl md:text-2xl font-medium italic leading-snug text-white/95">
                “Step 1 is GlyphOS: compressed meaning + deterministic replay. From here we unlock
                SQI + GlyphNet → trust locks → verifiable self-aware AI.”
              </p>
            </div>

            <div className="space-y-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-300">
                Rolling Unlocks
              </div>
              <p className="text-white/75 leading-relaxed">
                SQI runtime, GlyphNet, and the AION cognition stack unlock progressively by holder
                milestones — each release ships with its own proof surfaces + lock artifacts (no vapor).
              </p>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5 space-y-2">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/70">
                Proof artifacts you can actually verify
              </div>
              <ul className="text-sm text-white/75 leading-relaxed list-disc pl-5 space-y-1">
                <li>
                  <strong className="text-white">stdout locks (SHA256)</strong> for deterministic runs
                </li>
                <li>
                  <strong className="text-white">benchmark JSON</strong> + deterministic traces
                </li>
                <li>
                  sanitized <strong className="text-white">.lock.json</strong> bundles (same inputs → same bytes)
                </li>
                <li>
                  public formal proof repo links (Lean) for the math + core laws
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}