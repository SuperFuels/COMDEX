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

      {/* EXPLAINER (NEW: full Plain English + examples panel) */}
      <div className="border-t border-gray-100 pt-16">
        <div className="max-w-6xl mx-auto space-y-8">
          <div className="text-center space-y-3">
            <h2 className="text-3xl md:text-4xl font-black italic tracking-tight text-black">
              GlyphOS in Plain English
            </h2>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              It’s not “smaller files.” It’s <span className="text-black font-semibold">portable meaning</span>: condensed intent
              that runs deterministically and leaves an audit-grade trace.
            </p>
          </div>

          {/* Wide two-panel row (stack on mobile, side-by-side on xl) */}
          <div className="grid xl:grid-cols-[1.25fr_0.75fr] gap-6">
            {/* LEFT: full explanation */}
            <div className="rounded-[2.25rem] border border-slate-200 bg-white p-6 sm:p-10 space-y-10">
              {/* What it is */}
              <div className="space-y-3">
                <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.22em] text-slate-600">
                  What it is • The problem it solves
                </div>
                <p className="text-slate-700 leading-relaxed">
                  Traditional systems are like sending a novel when you only need to say{" "}
                  <span className="font-semibold text-black">“turn left.”</span> Most software communicates by shipping huge
                  JSON/XML payloads full of redundant keys and repeated structure.
                </p>
              </div>

              {/* Traditional vs GlyphOS code */}
              <div className="grid lg:grid-cols-2 gap-4">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold mb-2">
                    Traditional way (example)
                  </div>
                  <div className="rounded-xl border border-slate-300/70 bg-[#0b1220] p-4 font-mono text-xs leading-relaxed text-slate-100 overflow-auto">
                    <span className="text-slate-300">// Traditional way (327 bytes)</span>
                    {"\n"}
                    <span className="text-emerald-200">{"{"}</span>
                    {"\n"}  <span className="text-sky-200">"operation"</span>:{" "}
                    <span className="text-amber-200">"process_document"</span>,{"\n"}  <span className="text-sky-200">"action_type"</span>:{" "}
                    <span className="text-amber-200">"extract_and_summarize"</span>,{"\n"}  <span className="text-sky-200">"parameters"</span>:{" "}
                    <span className="text-emerald-200">{"{"}</span>
                    {"\n"}    <span className="text-sky-200">"document_id"</span>:{" "}
                    <span className="text-amber-200">"report_2024_Q3"</span>,{"\n"}    <span className="text-sky-200">"extraction_fields"</span>:{" "}
                    <span className="text-emerald-200">[</span>
                    <span className="text-amber-200">"revenue"</span>,{" "}
                    <span className="text-amber-200">"expenses"</span>,{" "}
                    <span className="text-amber-200">"profit"</span>
                    <span className="text-emerald-200">]</span>,{"\n"}    <span className="text-sky-200">"summary_length"</span>:{" "}
                    <span className="text-amber-200">5</span>,{"\n"}    <span className="text-sky-200">"output_format"</span>:{" "}
                    <span className="text-amber-200">"brief"</span>
                    {"\n"}  <span className="text-emerald-200">{"}"}</span>,{"\n"}  <span className="text-sky-200">"metadata"</span>:{" "}
                    <span className="text-emerald-200">{"{"}</span>
                    {"\n"}    <span className="text-sky-200">"timestamp"</span>:{" "}
                    <span className="text-amber-200">"2024-01-26"</span>,{"\n"}    <span className="text-sky-200">"user"</span>:{" "}
                    <span className="text-amber-200">"analyst_01"</span>
                    {"\n"}  <span className="text-emerald-200">{"}"}</span>
                    {"\n"}<span className="text-emerald-200">{"}"}</span>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold mb-2">
                    GlyphOS way (same meaning)
                  </div>
                  <div className="rounded-xl border border-slate-300/70 bg-[#0b1220] p-4 font-mono text-xs leading-relaxed text-slate-100 overflow-auto">
                    <span className="text-slate-300">// GlyphOS way (45 bytes)</span>
                    {"\n"}
                    <span className="text-sky-200">⊕</span>{" "}
                    <span className="text-amber-200">doc</span>(<span className="text-emerald-200">"Q3"</span>){" "}
                    <span className="text-slate-200">→</span>{" "}
                    <span className="text-amber-200">extract</span>(<span className="text-emerald-200">rev, exp, profit</span>){" "}
                    <span className="text-slate-200">→</span>{" "}
                    <span className="text-amber-200">sum</span>(<span className="text-emerald-200">5</span>)
                  </div>

                  <div className="mt-3 rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 leading-relaxed">
                    <span className="font-semibold">Same meaning.</span>{" "}
                    <span className="font-semibold">7× smaller.</span>{" "}
                    And it improves as operations get more complex.
                  </div>
                </div>
              </div>

              {/* Why this matters */}
              <div className="space-y-4">
                <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.22em] text-slate-600">
                  Why this matters • real-world impact
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <div className="font-bold text-black">1) Edge devices can think</div>
                    <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                      Instead of megabytes of verbose instructions, edge devices receive kilobytes of glyphs. That makes more
                      AI operations feasible without cloud round-trips.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <div className="font-bold text-black">2) IoT networks don’t choke</div>
                    <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                      Factories and sensor grids can ship more updates on the same bandwidth because the redundant structure is removed.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <div className="font-bold text-black">3) Audit trails you can trust</div>
                    <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                      Every glyph produces a deterministic trace — run it twice and you get the same outputs byte-for-byte.
                      That turns “logs” into provable execution.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <div className="font-bold text-black">4) Real cost savings</div>
                    <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                      Less bandwidth, less compute churn, and fewer round-trips. The bigger the agent network, the more this compounds.
                    </p>
                  </div>
                </div>
              </div>

              {/* WirePack + determinism */}
              <div className="grid lg:grid-cols-2 gap-4">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <div className="font-bold text-black">WirePack: send once, reference forever</div>
                  <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                    When instructions are similar, GlyphOS ships the structure once as a template — then only the deltas.
                  </p>

                  <div className="mt-3 rounded-xl border border-slate-300/70 bg-[#0b1220] p-4 font-mono text-xs text-slate-100 overflow-auto">
                    <span className="text-slate-300">// Send once (template)</span>
                    {"\n"}
                    <span className="text-sky-200">TEMPLATE_47:</span>{" "}
                    <span className="text-amber-200">⊕</span>{" "}
                    <span className="text-amber-200">doc</span>(<span className="text-sky-200">$NAME</span>){" "}
                    <span className="text-slate-200">→</span>{" "}
                    <span className="text-amber-200">extract</span>(fields){" "}
                    <span className="text-slate-200">→</span>{" "}
                    <span className="text-amber-200">summarize</span>
                    {"\n\n"}
                    <span className="text-slate-300">// Then only deltas</span>
                    {"\n"}
                    <span className="text-sky-200">Task 1:</span>{" "}
                    <span className="text-emerald-200">{"{template: 47, $NAME: \"Q3_Report\"}"}</span>
                    {"\n"}
                    <span className="text-sky-200">Task 2:</span>{" "}
                    <span className="text-emerald-200">{"{template: 47, $NAME: \"Q4_Report\"}"}</span>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <div className="font-bold text-black">Determinism: prove it happened</div>
                  <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                    Execution produces a trace you can reproduce later — auditors, regulators, and courts can replay the same glyph
                    and verify identical results.
                  </p>

                  <div className="mt-3 rounded-xl border border-slate-300/70 bg-[#0b1220] p-4 font-mono text-xs text-slate-100 overflow-auto">
                    <span className="text-sky-200">Trace ID:</span>{" "}
                    <span className="text-emerald-200">GX-51ECA33C</span>
                    {"\n"}
                    <span className="text-slate-300">Step 1:</span> Load doc("Q3_Report") → OK, 23ms
                    {"\n"}
                    <span className="text-slate-300">Step 2:</span> Extract(rev, exp) → OK, 17ms
                    {"\n"}
                    <span className="text-slate-300">Step 3:</span> Summarize(5) → OK, 24ms
                    {"\n\n"}
                    <span className="text-emerald-200">deterministic ✓</span>{" "}
                    <span className="text-slate-300">(same glyph tomorrow → same bytes)</span>
                  </div>
                </div>
              </div>

              {/* What's live today */}
              <div className="rounded-[2rem] border border-blue-200 bg-blue-50 p-6">
                <div className="text-[11px] uppercase tracking-[0.22em] text-blue-700 font-bold">
                  What’s live today
                </div>
                <ul className="mt-3 text-sm text-blue-900 leading-relaxed list-disc pl-5 space-y-1">
                  <li><span className="font-semibold">GlyphOS Alpha</span> — execution engine running</li>
                  <li><span className="font-semibold">Compression benchmarks</span> — reproducible gains on complex programs</li>
                  <li><span className="font-semibold">WirePack v10</span> — template + delta transport</li>
                  <li><span className="font-semibold">Deterministic locks</span> — SHA256-verified artifacts</li>
                </ul>

                <div className="mt-4 rounded-xl border border-blue-300/50 bg-white p-4 font-mono text-xs text-slate-800 overflow-auto">
                  <span className="text-slate-500">$</span>{" "}
                  python3 backend/tests/glyph_compression_benchmark.py --depth 60
                  {"\n"}
                  <span className="text-slate-500">Result:</span> 2,175 bytes (GlyphOS) vs 132,582 bytes (traditional) = 61×
                </div>
              </div>
            </div>

            {/* RIGHT: examples + CTA (grey/white, blue buttons) */}
            <div className="rounded-[2.25rem] border border-slate-200 bg-gradient-to-b from-slate-50 to-white p-6 sm:p-10 space-y-6">
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.22em] text-slate-600">
                  Real examples
                </div>
                <p className="text-slate-600 leading-relaxed">
                  The point is simple: software starts to communicate like humans text — shorthand that preserves meaning,
                  plus templates + deltas, plus proof-grade replay.
                </p>
              </div>

              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-white p-5">
                  <div className="font-bold text-black">Smart Home</div>
                  <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-xs text-slate-800 overflow-auto">
                    thermo(living) → cool(72°) @ 18:00-22:00
                  </div>
                  <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                    Smaller instruction payloads mean more devices per hub with the same compute budget.
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-5">
                  <div className="font-bold text-black">Medical Imaging</div>
                  <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-xs text-slate-800 overflow-auto">
                    MRI(brain) → denoise → segment(tumor) → measure(vol, loc)
                  </div>
                  <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                    Portable scanners can run more of the pipeline locally instead of relying on cloud infrastructure.
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-5">
                  <div className="font-bold text-black">Financial Trading</div>
                  <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-xs text-slate-800 overflow-auto">
                    MA_cross(AAPL, MSFT, GOOGL) → trade(max=1k, stop=2%)
                  </div>
                  <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                    Deterministic traces turn compliance into something reproducible and auditable.
                  </p>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5">
                <div className="font-bold text-black">The bottom line</div>
                <ul className="mt-2 text-sm text-slate-600 leading-relaxed list-disc pl-5 space-y-1">
                  <li><span className="font-semibold text-black">60× less bandwidth</span> on complex programs</li>
                  <li><span className="font-semibold text-black">edge devices become intelligent</span></li>
                  <li><span className="font-semibold text-black">audit trails become verifiable</span></li>
                  <li><span className="font-semibold text-black">enterprise saves infrastructure cost</span></li>
                </ul>
              </div>

              {/* Buttons row */}
              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  onClick={() => (window.location.href = "/glyph")}
                  className="w-full sm:w-auto px-5 py-3 rounded-2xl bg-blue-600 text-white font-extrabold tracking-wide hover:bg-blue-700"
                >
                  Open Glyph OS
                </button>
                <button
                  onClick={() => document.getElementById("proofs")?.scrollIntoView({ behavior: "smooth" })}
                  className="w-full sm:w-auto px-5 py-3 rounded-2xl border border-slate-200 bg-white text-slate-900 font-extrabold tracking-wide hover:border-slate-300"
                >
                  View Proof Repo
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}