// /// /workspaces/COMDEX/frontend/tabs/launch/index.tsx
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

      {/* EXPLAINER */}
      <div className="border-t border-gray-100 pt-16">
        <div className="max-w-6xl mx-auto space-y-8">
          <div className="text-center space-y-3">
            <h2 className="text-3xl md:text-4xl font-black italic tracking-tight text-black">
              GlyphOS in Plain English
            </h2>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              It’s not “smaller files.” It’s{" "}
              <span className="text-black font-semibold">portable meaning</span>:
              condensed intent that runs deterministically and leaves an audit-grade
              trace.
            </p>
          </div>

          {/* ✅ FORCE SINGLE COLUMN (stack) */}
          <div className="grid grid-cols-1 gap-6">
            {/* CARD 1: What it is + core code comparison */}
            <div className="rounded-[2.25rem] border border-slate-200 bg-white p-6 sm:p-10 space-y-10">
              {/* What it is */}
              <div className="space-y-3">
                <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.22em] text-slate-600">
                  What it is • The problem it solves
                </div>
                <p className="text-slate-700 leading-relaxed">
                  Traditional systems are like sending a novel when you only need to
                  say{" "}
                  <span className="font-semibold text-black">“turn left.”</span>{" "}
                  Most software communicates by shipping huge JSON/XML payloads full
                  of redundant keys and repeated structure.
                </p>
              </div>

              {/* ✅ Traditional vs GlyphOS (keep 2-up on desktop, but fix code styling) */}
              <div className="grid lg:grid-cols-2 gap-4">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold mb-2">
                    Traditional way (example)
                  </div>

                  {/* ✅ plain: dark grey text on light grey */}
                  <pre className="rounded-xl border border-slate-200 bg-slate-100 p-4 font-mono text-xs leading-relaxed text-slate-800 overflow-auto whitespace-pre-wrap break-words">
{`// Traditional way (327 bytes)
{
  "operation": "process_document",
  "action_type": "extract_and_summarize",
  "parameters": {
    "document_id": "report_2024_Q3",
    "extraction_fields": ["revenue", "expenses", "profit"],
    "summary_length": 5,
    "output_format": "brief"
  },
  "metadata": {
    "timestamp": "2024-01-26",
    "user": "analyst_01"
  }
}`}
                  </pre>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold mb-2">
                    GlyphOS way (same meaning)
                  </div>

                  {/* ✅ plain: dark grey text on light grey */}
                  <pre className="rounded-xl border border-slate-200 bg-slate-100 p-4 font-mono text-xs leading-relaxed text-slate-800 overflow-auto whitespace-pre-wrap break-words">
{`// GlyphOS way (45 bytes)
⊕ doc("Q3") → extract(rev, exp, profit) → sum(5)`}
                  </pre>

                  <div className="mt-3 rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 leading-relaxed">
                    <span className="font-semibold">Same meaning.</span>{" "}
                    <span className="font-semibold">7× smaller.</span> And it
                    improves as operations get more complex.
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
                      Instead of megabytes of verbose instructions, edge devices
                      receive kilobytes of glyphs. That makes more AI operations
                      feasible without cloud round-trips.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <div className="font-bold text-black">2) IoT networks don’t choke</div>
                    <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                      Factories and sensor grids can ship more updates on the same
                      bandwidth because the redundant structure is removed.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <div className="font-bold text-black">3) Audit trails you can trust</div>
                    <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                      Every glyph produces a deterministic trace — run it twice and
                      you get the same outputs byte-for-byte. That turns “logs” into
                      provable execution.
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <div className="font-bold text-black">4) Real cost savings</div>
                    <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                      Less bandwidth, less compute churn, and fewer round-trips. The
                      bigger the agent network, the more this compounds.
                    </p>
                  </div>
                </div>
              </div>

              {/* WirePack + determinism (keep as-is layout, but fix code styling) */}
              <div className="grid lg:grid-cols-2 gap-4">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <div className="font-bold text-black">WirePack: send once, reference forever</div>
                  <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                    When instructions are similar, GlyphOS ships the structure once
                    as a template — then only the deltas.
                  </p>

                  {/* ✅ plain code */}
                  <pre className="mt-3 rounded-xl border border-slate-200 bg-slate-100 p-4 font-mono text-xs leading-relaxed text-slate-800 overflow-auto whitespace-pre-wrap break-words">
{`// Send once (template)
TEMPLATE_47: ⊕ doc($NAME) → extract(fields) → summarize

// Then only deltas
Task 1: { template: 47, $NAME: "Q3_Report" }
Task 2: { template: 47, $NAME: "Q4_Report" }`}
                  </pre>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <div className="font-bold text-black">Determinism: prove it happened</div>
                  <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                    Execution produces a trace you can reproduce later — auditors,
                    regulators, and courts can replay the same glyph and verify
                    identical results.
                  </p>

                  {/* ✅ plain code */}
                  <pre className="mt-3 rounded-xl border border-slate-200 bg-slate-100 p-4 font-mono text-xs leading-relaxed text-slate-800 overflow-auto whitespace-pre-wrap break-words">
{`Trace ID: GX-51ECA33C
Step 1: Load doc("Q3_Report") → OK, 23ms
Step 2: Extract(rev, exp) → OK, 17ms
Step 3: Summarize(5) → OK, 24ms

deterministic ✓ (same glyph tomorrow → same bytes)`}
                  </pre>
                </div>
              </div>

              {/* What's live today (keep as-is) */}
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

                <pre className="mt-4 rounded-xl border border-blue-300/50 bg-white p-4 font-mono text-xs text-slate-800 overflow-auto whitespace-pre-wrap break-words">
{`$ python3 backend/tests/glyph_compression_benchmark.py --depth 60
Result: 2,175 bytes (GlyphOS) vs 132,582 bytes (traditional) = 61×`}
                </pre>
              </div>
            </div>

            {/* CARD 2: Real examples (now stacked under, not right column) */}
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