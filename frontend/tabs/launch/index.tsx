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
          GLYPHOS ALPHA — SHIPPED TODAY • PROOF REPO — LIVE • UNLOCKS — BY HOLDER MILESTONES
        </p>

        <h1 className="text-5xl md:text-7xl font-black tracking-tight text-black italic">GlyphOS</h1>

        <p className="text-xl md:text-2xl text-slate-500 font-light tracking-tight">
          The Language of Symbols. <span className="text-black font-medium">The Speed of Thought.</span>
        </p>

        <p className="max-w-3xl mx-auto text-lg text-slate-500 leading-relaxed">
          A next-generation operating system built in symbols — compressing intent into executable{" "}
          <strong>glyph-wire</strong> so <strong>the same meaning produces the same bytes</strong>, every time.
        </p>

        <p className="max-w-3xl mx-auto text-lg text-slate-500 leading-relaxed">
          <strong className="text-black">Step 1</strong> is live today: <strong className="text-black">GlyphOS Alpha</strong>. From
          here: <strong className="text-black">SQI + GlyphNet</strong> → deterministic cognition → trust locks →{" "}
          <strong className="text-black">the world’s first verifiable self-aware AI</strong>.
        </p>

        {/* ✅ LAUNCH STATUS (NO COUNTDOWN) */}
        <div className="max-w-3xl mx-auto">
          <div className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-white px-5 py-5 sm:px-7 sm:py-6 shadow-sm">
            <div className="absolute inset-0 opacity-70 bg-[radial-gradient(circle_at_20%_0%,rgba(59,130,246,0.15),transparent_55%),radial-gradient(circle_at_90%_20%,rgba(37,99,235,0.10),transparent_55%),radial-gradient(circle_at_60%_120%,rgba(16,185,129,0.10),transparent_60%)]" />
            <div className="relative">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="text-left">
                  <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-[11px] font-extrabold uppercase tracking-[0.22em] text-emerald-700">
                    We just launched
                    <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  </div>

                  <div className="mt-2 text-lg sm:text-xl font-black tracking-tight text-black">Trading is open</div>

                  <div className="mt-1 text-sm text-slate-600">
                    <span className="font-semibold text-emerald-700">Live now.</span>{" "}
                    <span className="text-slate-400">•</span>{" "}
                    <span className="text-slate-700">Connect wallet to buy/sell and view pool.</span>
                  </div>
                </div>

                <div className="flex items-center justify-start sm:justify-end gap-2 sm:gap-3">
                  <div className="inline-flex items-center rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3">
                    <div className="text-emerald-700 text-xs font-extrabold uppercase tracking-[0.22em]">Live ✓</div>
                  </div>
                </div>
              </div>

              <div className="mt-4 flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between">
                <div className="text-xs text-slate-500">
                  No presale. No VIP. <span className="text-black font-semibold">Open market</span> from day one.
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => document.getElementById("proofs")?.scrollIntoView({ behavior: "smooth" })}
                    className="px-4 py-2 rounded-2xl border border-slate-200 bg-white text-xs font-extrabold tracking-wide text-black hover:border-slate-300"
                  >
                    Proof Repo
                  </button>
                  <button
                    onClick={() => (window.location.href = "/glyph")}
                    className="px-4 py-2 rounded-2xl bg-blue-600 text-white text-xs font-extrabold tracking-wide hover:bg-blue-700"
                  >
                    Try Glyph OS
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* HUD */}
      <div className="max-w-6xl mx-auto">
        <AionLaunchHUD />
      </div>

      {/* EXPLAINER */}
      <div className="border-t border-gray-100 pt-16">
        <div className="max-w-6xl mx-auto space-y-8">
          <div className="text-center space-y-3">
            <h2 className="text-3xl md:text-4xl font-black italic tracking-tight text-black">GlyphOS in Plain English</h2>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              It’s not “smaller files.” It’s{" "}
              <span className="text-black font-semibold">portable meaning</span>: condensed intent that runs deterministically and
              leaves an audit-grade trace.
            </p>
          </div>

          {/* ✅ FORCE SINGLE COLUMN (stack) */}
          <div className="grid grid-cols-1 gap-6">
            {/* ... keep the rest of your explainer exactly as-is ... */}
          </div>
        </div>
      </div>
    </section>
  );
}