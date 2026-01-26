// /workspaces/COMDEX/frontend/tabs/launch/AionLaunchHUD.tsx
"use client";

import React, { useMemo, useState } from "react";

type ChainKey = "ETH" | "SOL";

const LINKS: Record<
  ChainKey,
  { label: string; dex: string; contract: string; pairLabel: string }
> = {
  ETH: {
    label: "ETH",
    pairLabel: "Pair: ETH",
    dex: "https://YOUR_DEX_LINK_FOR_ETH_PAIR",
    contract: "0xYOUR_ETH_CONTRACT_HERE",
  },
  SOL: {
    label: "SOL",
    pairLabel: "Pair: SOL",
    dex: "https://YOUR_DEX_LINK_FOR_SOL_PAIR",
    contract: "So1anaYOUR_MINT_OR_POOL_HERE",
  },
};

function cx(...xs: Array<string | false | null | undefined>) {
  return xs.filter(Boolean).join(" ");
}

function safeOpen(url: string) {
  if (!url || url === "#" || url.includes("YOUR_DEX_LINK")) {
    alert("Set your DEX link in AionLaunchHUD.tsx (LINKS) before publishing.");
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

export default function AionLaunchHUD() {
  const [chain, setChain] = useState<ChainKey>("ETH");
  const [overlayOpen, setOverlayOpen] = useState<boolean>(false);

  const cfg = LINKS[chain];

  const stats = useMemo(
    () => [
      {
        v: "1B",
        k: "Total supply",
        s: "Replace with your real numbers.",
      },
      {
        v: "LOCKED",
        k: "Liquidity",
        s: "Link your lock / vesting proof.",
      },
      {
        v: "61×",
        k: "Meaning compression",
        s: "Depth-60: 2,175B vs 131,069B.",
      },
      {
        v: "54.77%",
        k: "WirePack savings",
        s: "v10 vs gzip’d JSON (locked).",
      },
    ],
    []
  );

  return (
    <>
      <div className="space-y-10">
        {/* TOPBAR */}
        <div className="sticky top-0 z-20">
          <div className="rounded-[1.75rem] border border-slate-200 bg-white/80 backdrop-blur px-4 py-3 shadow-sm">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-2xl border border-slate-200 bg-gradient-to-br from-emerald-200/60 via-white to-blue-200/60" />
                <div>
                  <div className="text-sm font-extrabold tracking-tight text-black">
                    AION Launch
                  </div>
                  <div className="text-[11px] text-slate-500 tracking-wide">
                    Compressed Meaning • Verifiable Intelligence
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <a
                  href="#stack"
                  className="px-3 py-2 rounded-full border border-slate-200 bg-white text-xs font-bold tracking-wide text-slate-600 hover:text-black hover:border-slate-300"
                >
                  Stack
                </a>
                <a
                  href="#wow"
                  className="px-3 py-2 rounded-full border border-slate-200 bg-white text-xs font-bold tracking-wide text-slate-600 hover:text-black hover:border-slate-300"
                >
                  Live Proof
                </a>
                <a
                  href="#roadmap"
                  className="px-3 py-2 rounded-full border border-emerald-200 bg-emerald-50 text-xs font-bold tracking-wide text-emerald-700 hover:border-emerald-300"
                >
                  Alpha Roadmap
                </a>
                <button
                  onClick={() => safeOpen(cfg.dex)}
                  className="px-3 py-2 rounded-full border border-slate-200 bg-black text-xs font-extrabold tracking-wide text-white hover:opacity-90"
                >
                  Buy AION
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* HERO GRID */}
        <div className="grid lg:grid-cols-[1.15fr_0.85fr] gap-6">
          {/* LEFT */}
          <div className="rounded-[2.5rem] border border-slate-200 bg-black text-white p-8 relative overflow-hidden">
            <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_20%_0%,rgba(59,130,246,0.6),transparent_55%),radial-gradient(circle_at_80%_20%,rgba(16,185,129,0.5),transparent_55%),radial-gradient(circle_at_90%_90%,rgba(244,63,94,0.35),transparent_60%)]" />
            <div className="relative space-y-6">
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 text-[11px] font-bold tracking-widest">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  GLYPHOS ALPHA — LIVE TODAY
                </span>
                <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 text-[11px] font-bold tracking-widest">
                  <span className="h-2 w-2 rounded-full bg-amber-300" />
                  ROLLING ALPHAS — WIRES, NET, SQI, AION
                </span>
              </div>

              <h2 className="text-3xl md:text-5xl font-black italic tracking-tight">
                An AI that knows when it’s guessing — and can prove it.
              </h2>

              <p className="text-white/75 text-base md:text-lg leading-relaxed max-w-2xl">
                Most AI confidently hallucinates. AION measures its own coherence,
                reports uncertainty as a first-class signal, and ships every workflow as{" "}
                <span className="text-white font-semibold">compressed meaning</span>{" "}
                with a deterministic trace.
              </p>

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => safeOpen(cfg.dex)}
                  className="px-4 py-3 rounded-2xl bg-white text-black font-extrabold tracking-wide hover:opacity-95"
                >
                  Buy AION ({cfg.label})
                </button>
                <button
                  onClick={() => {
                    document.getElementById("stack")?.scrollIntoView({ behavior: "smooth" });
                  }}
                  className="px-4 py-3 rounded-2xl border border-white/20 bg-white/5 text-white font-bold tracking-wide hover:bg-white/10"
                >
                  Explore the Stack
                </button>
                <button
                  onClick={() => setOverlayOpen(true)}
                  className="px-4 py-3 rounded-2xl border border-amber-200/30 bg-amber-200/10 text-amber-100 font-bold tracking-wide hover:bg-amber-200/15"
                >
                  What you’re about to see
                </button>
              </div>

              <div className="pt-4 border-t border-white/10 text-xs text-white/65 leading-relaxed">
                Pairing today: <span className="font-semibold text-white">{cfg.label}</span>{" "}
                • Contract:{" "}
                <span className="font-mono text-white/90">{cfg.contract}</span>{" "}
                • Liquidity: <span className="font-semibold">LOCKED</span> (add lock link) • Not financial advice.
              </div>

              <div className="text-xs text-white/65 leading-relaxed">
                <span className="font-semibold text-white">Live now:</span> GlyphOS + Compression + WirePack.
                <br />
                <span className="font-semibold text-white">Rolling alpha:</span> GlyphNet, SQI runtime, organism pillars (Φ/ADR/REAL/Mirror), Phase-7 calibration.
              </div>
            </div>
          </div>

          {/* RIGHT */}
          <div className="rounded-[2.5rem] border border-slate-200 bg-white p-8 space-y-6">
            <div className="space-y-2">
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold">
                Launch Console
              </p>
              <p className="text-slate-600 leading-relaxed">
                Choose your pair. Today stays clean:{" "}
                <span className="text-black font-semibold">
                  GlyphOS Alpha + core proof tabs
                </span>
                . Everything else unlocks progressively.
              </p>
            </div>

            {/* toggle */}
            <div className="flex flex-wrap gap-2">
              {(["ETH", "SOL"] as ChainKey[]).map((k) => (
                <button
                  key={k}
                  onClick={() => setChain(k)}
                  className={cx(
                    "px-4 py-2 rounded-full border text-sm font-extrabold tracking-wide transition",
                    k === chain
                      ? "border-blue-300 bg-blue-50 text-black"
                      : "border-slate-200 bg-white text-slate-600 hover:text-black hover:border-slate-300"
                  )}
                >
                  {LINKS[k].pairLabel}
                </button>
              ))}
            </div>

            {/* stats */}
            <div className="grid grid-cols-2 gap-3">
              {stats.map((s) => (
                <div
                  key={s.k}
                  className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
                >
                  <div className="text-lg font-black tracking-tight text-black">
                    {s.v}
                  </div>
                  <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold mt-1">
                    {s.k}
                  </div>
                  <div className="text-xs text-slate-500 mt-2 leading-relaxed">
                    {s.s}
                  </div>
                </div>
              ))}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600 leading-relaxed">
              <div className="font-bold uppercase tracking-[0.22em] text-slate-500 text-[11px] mb-2">
                Quick Links (set)
              </div>
              <div className="flex flex-col gap-1">
                <span>
                  DEX: <span className="font-mono text-slate-700">{cfg.dex}</span>
                </span>
                <span>
                  Docs: <span className="font-mono text-slate-700">https://…</span>
                </span>
                <span>
                  Demo: <span className="font-mono text-slate-700">https://…</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* STACK */}
        <div id="stack" className="space-y-6">
          <div className="space-y-2 text-center">
            <h3 className="text-3xl font-black italic tracking-tight text-black">
              The Stack — from symbols to sentience
            </h3>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              Ship intent as a stable wire-shape. Execute deterministically. Prove trust
              with locks. This is the “wow”: measurable claims, reproducible outputs.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            <StackCard
              status="LIVE TODAY"
              statusTone="live"
              title="GlyphOS"
              subtitle="Compressed meaning + deterministic trace"
              desc="Intent → glyph-wire → execution → audit. Same meaning + same policy ⇒ same wire + same trace."
              wow={`Depth-60 benchmark (locked)
Glyph wire JSON:          2,175 B
Glyph wire JSON (gzip):     379 B
Verbose AST:            131,069 B
Ratio vs verbose AST:   60.26× raw / 11.28× gzip`}
            />
            <StackCard
              status="LIVE TODAY"
              statusTone="live"
              title="Compression Proof"
              subtitle="SHA256-locked reproducibility"
              desc="Nested operator trees compress harder as complexity grows — while remaining replayable."
              wow={`$ python backend/tests/glyphos_compression_benchmark.py --depth 60
Glyph (gzip): 379 B
Verbose AST (gzip): 4,275 B
Result: 61× raw gain
Deterministic: byte-identical`}
            />
            <StackCard
              status="LIVE TODAY"
              statusTone="live"
              title="WirePack v10"
              subtitle="Template + Delta transport"
              desc="Ship the shape once, then ship only mutations. Stable, replayable, audit-friendly."
              wow={`WirePack v10 (locked)
Depth / Messages: 30 / 2000
Avg JSON (gzip):   366.49 B
Avg v10 (gzip):    165.77 B
Savings:           54.77%
Roundtrip fails:   0/2000`}
            />
            <StackCard
              status="ALPHA"
              statusTone="alpha"
              title="GlyphNet"
              subtitle="Wave-native networking"
              desc="Multi-writer convergence (CRDT-style), failover across substrates, tamper-evident delivery."
              wow={`Alpha demos:
• Fiber → Radio mesh downshift
• CRDT merges
• “56× metadata reduction” tab`}
            />
            <StackCard
              status="ALPHA"
              statusTone="alpha"
              title="SQI Runtime"
              subtitle="Quantum-like on laptop"
              desc="Superposition, entanglement, governed collapse — deterministic and auditable."
              wow={`Demo frame:
coherence_before: 0.94
coherence_after:  0.31
trace: superposition → entangle → collapse`}
            />
            <StackCard
              status="ALPHA"
              statusTone="alpha"
              title="AION (Organism)"
              subtitle="Φ / ADR / REAL / Mirror"
              desc="Self-monitoring vitals, self-repair, self-preservation, and reflective narration."
              wow={`Pillars:
• Φ coherence vector
• ADR immune response
• REAL stable-state locks
• Mirror reflection
• Phase-7 calibration`}
            />
          </div>
        </div>

        {/* WOW / PROOF */}
        <div id="wow" className="space-y-6">
          <div className="space-y-2 text-center">
            <h3 className="text-3xl font-black italic tracking-tight text-black">
              Live Proof Engine
            </h3>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              This is the “wow”: compression is locked, traces are deterministic, and
              calibration can be audited.
            </p>
          </div>

          <div className="rounded-[2.5rem] border border-slate-200 bg-black text-white p-8">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-3">
                <div className="h-3 w-3 rounded-full bg-emerald-400 shadow-[0_0_0_8px_rgba(16,185,129,0.15)]" />
                <div className="font-extrabold tracking-tight">Run-it-yourself verification</div>
              </div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-white/70 font-bold">
                Deterministic • Locked • Audit-ready
              </div>
            </div>

            <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-4 mt-6">
              <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5 font-mono text-xs leading-relaxed overflow-auto">
                <div className="text-emerald-300 font-bold">
                  $ python backend/tests/glyphos_wirepack_v10_template_delta_benchmark.py
                </div>
                <div className="text-white/70 mt-2">
                  {`=== ✅ WirePack v10 (Locked) ===
Depth / Messages: 30 / 2000
Avg JSON (gzip): 366.492 B
Avg v10 (gzip):  165.767 B
Savings:         54.77%
Template hits:   2000/2000
Roundtrip fails: 0/2000
Lock stdout SHA256: 79dfafe8b6a373...`}
                </div>

                <div className="text-emerald-300 font-bold mt-4">
                  $ curl -sS $BRIDGE/api/phase7/verify
                </div>
                <div className="text-white/70">
                  {"{ \"match\": true, \"golden_schema\": \"AION.Phase7LockBundle.v2\", \"sha256\": \"…\" }"}
                </div>
              </div>

              <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5 space-y-3">
                <div className="flex items-center justify-between gap-2 text-xs text-white/80">
                  <div>
                    <span className="font-extrabold text-white">Trust calibration</span>{" "}
                    <span className="text-white/60">(Phase-7)</span>
                  </div>
                  <div className="font-mono">ECE ≈ 0.0198 ✓</div>
                </div>

                <div className="h-2 rounded-full border border-white/10 bg-black/40 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-emerald-300/80 to-blue-300/80"
                    style={{ width: "82%" }}
                  />
                </div>

                <div className="text-xs text-white/70 leading-relaxed">
                  <strong className="text-white">Challenge mode:</strong> pick a confidence bin and compare
                  stated confidence vs empirical accuracy. You just audited honesty.
                </div>

                <div className="rounded-2xl border border-white/10 bg-black/30 p-4 font-mono text-xs text-white/80 whitespace-pre-wrap">
                  {`Select 0.85 → inspect matching bin
Stated confidence: 85.0%
Empirical accuracy: 82.6%
Gap: 2.4% ✓`}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ROADMAP */}
        <div id="roadmap" className="space-y-6">
          <div className="space-y-2 text-center">
            <h3 className="text-3xl font-black italic tracking-tight text-black">
              Rolling Alpha Ladder
            </h3>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              Today is clean: GlyphOS + proof tabs. Everything else unlocks in staged
              alphas (so the launch stays accurate).
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <RoadmapStep
              n={1}
              tag="LIVE"
              title="Today — GlyphOS Alpha + Core Proof"
              desc="Compressed intent + deterministic trace. Public locked benchmarks."
              bullets={[
                "GlyphOS presets (Document Intelligence / Orchestration)",
                "Compression proof tab (depth scaling)",
                "WirePack v10 tab (Template+Delta)",
              ]}
            />
            <RoadmapStep
              n={2}
              tag="ALPHA"
              title="Week 1–2 — Transport + Trace UX"
              desc="Make “same meaning → same wire → same trace” visceral."
              bullets={[
                "Trace downloads + lock bundles in UI",
                "Preset gallery: intent → wire → replay",
                "Policy selector (deterministic / conservative)",
              ]}
            />
            <RoadmapStep
              n={3}
              tag="ALPHA"
              title="Week 2–4 — SQI + AION Demos"
              desc="Quantum-like ambiguity resolution + organism feedback loops."
              bullets={[
                "SQI entangled scheduler demo (coherence + trace)",
                "AION pillars: Φ / ADR / REAL / Mirror / Θ heartbeat",
                "Phase-7 calibration surfaced as proof tab",
              ]}
            />
            <RoadmapStep
              n={4}
              tag="ROLLING"
              title="Month 2+ — GlyphNet + Multiverse"
              desc="Wave-native networking + multiverse view demos."
              bullets={[
                "Multiverse view: routing / topology / merges",
                "Mesh downshift: Fiber → Radio",
                "Security story: interference as alarm",
              ]}
            />
          </div>
        </div>

        {/* FOOT */}
        <div className="border-t border-gray-100 pt-10 text-sm text-gray-500 leading-relaxed">
          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div>
              <div className="font-bold text-black">Tessaris AI</div>
              <div>Maintainer: Tessaris AI • Author: Kevin Robinson</div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <a className="px-3 py-2 rounded-full border border-gray-200 bg-gray-50 hover:border-gray-300" href="#">
                X (set)
              </a>
              <a className="px-3 py-2 rounded-full border border-gray-200 bg-gray-50 hover:border-gray-300" href="#">
                Telegram (set)
              </a>
              <a className="px-3 py-2 rounded-full border border-gray-200 bg-gray-50 hover:border-gray-300" href="#">
                Discord (set)
              </a>
              <a className="px-3 py-2 rounded-full border border-gray-200 bg-gray-50 hover:border-gray-300" href="#">
                Docs (set)
              </a>
            </div>
          </div>

          <div className="mt-6 rounded-[2.5rem] border border-amber-200 bg-amber-50 p-6">
            <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-amber-700">
              Disclaimer
            </div>
            <p className="mt-2">
              This page describes software utilities and alpha access. It is not
              financial advice. Replace placeholders (contract, DEX links, lock links)
              before publishing.
            </p>
          </div>
        </div>
      </div>

      {/* OVERLAY */}
      {overlayOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur flex items-center justify-center p-4"
          onClick={() => setOverlayOpen(false)}
        >
          <div
            className="w-full max-w-3xl rounded-[2.5rem] border border-white/10 bg-black text-white p-8 space-y-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.22em] text-white/70 font-bold">
                  Welcome to the AION Launch
                </div>
                <div className="text-2xl font-black italic mt-2">
                  Verifiable intelligence, shipped as compressed meaning.
                </div>
              </div>
              <button
                onClick={() => setOverlayOpen(false)}
                className="px-3 py-2 rounded-2xl border border-white/15 bg-white/5 hover:bg-white/10"
              >
                ✕
              </button>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5">
                <div className="font-extrabold">What’s live today</div>
                <p className="text-white/70 mt-2 text-sm leading-relaxed">
                  GlyphOS Alpha + proof tabs: Compression, WirePack, deterministic traces.
                  The goal is “wow + verifiable” immediately.
                </p>
                <div className="mt-4 flex gap-2 flex-wrap">
                  <button
                    className="px-4 py-2 rounded-2xl bg-white text-black font-extrabold"
                    onClick={() => {
                      setOverlayOpen(false);
                      document.getElementById("stack")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    Explore Stack
                  </button>
                  <button
                    className="px-4 py-2 rounded-2xl border border-white/15 bg-white/5 font-bold"
                    onClick={() => {
                      setOverlayOpen(false);
                      document.getElementById("wow")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    See Live Proof
                  </button>
                </div>
              </div>

              <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5">
                <div className="font-extrabold">What unlocks next</div>
                <p className="text-white/70 mt-2 text-sm leading-relaxed">
                  GlyphNet, SQI runtime, AION organism pillars, and Phase-7 trust calibration
                  unlock progressively so the launch stays accurate.
                </p>
                <div className="mt-4 flex gap-2 flex-wrap">
                  <button
                    className="px-4 py-2 rounded-2xl border border-amber-200/30 bg-amber-200/10 text-amber-100 font-extrabold"
                    onClick={() => {
                      setOverlayOpen(false);
                      document.getElementById("roadmap")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    See Alpha Ladder
                  </button>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5">
              <div className="font-extrabold">Why this matters</div>
              <p className="text-white/70 mt-2 text-sm leading-relaxed">
                Uncalibrated AI can say “95% confident” and be wrong constantly. AION measures
                coherence during computation, then Phase-7 checks whether confidence matches reality —
                with SHA256-locked proof artifacts.
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function StackCard(props: {
  status: string;
  statusTone: "live" | "alpha" | "soon";
  title: string;
  subtitle: string;
  desc: string;
  wow: string;
}) {
  const tone =
    props.statusTone === "live"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : props.statusTone === "alpha"
      ? "border-amber-200 bg-amber-50 text-amber-700"
      : "border-slate-200 bg-slate-50 text-slate-600";

  return (
    <div className="rounded-[2.5rem] border border-gray-200 bg-white p-6 space-y-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cx(
            "px-3 py-1.5 rounded-full border text-[10px] font-bold uppercase tracking-[0.22em]",
            tone
          )}
        >
          {props.status}
        </span>
        <span className="px-3 py-1.5 rounded-full border border-gray-200 bg-gray-50 text-[10px] font-bold uppercase tracking-[0.22em] text-gray-600">
          {props.subtitle}
        </span>
      </div>

      <div className="space-y-1">
        <div className="text-xl font-black italic tracking-tight text-black">
          {props.title}
        </div>
        <p className="text-sm text-gray-600 leading-relaxed">{props.desc}</p>
      </div>

      <pre className="rounded-[1.75rem] border border-gray-200 bg-gray-50 p-4 text-xs text-gray-700 overflow-auto whitespace-pre-wrap">
        {props.wow}
      </pre>
    </div>
  );
}

function RoadmapStep(props: {
  n: number;
  tag: string;
  title: string;
  desc: string;
  bullets: string[];
}) {
  return (
    <div className="rounded-[2.5rem] border border-gray-200 bg-white p-6 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-2xl border border-blue-200 bg-blue-50 grid place-items-center font-black text-black">
            {props.n}
          </div>
          <div className="space-y-1">
            <div className="text-lg font-black italic tracking-tight text-black">
              {props.title}
            </div>
            <div className="text-sm text-gray-600 leading-relaxed">{props.desc}</div>
          </div>
        </div>
        <span className="px-3 py-1.5 rounded-full border border-gray-200 bg-gray-50 text-[10px] font-bold uppercase tracking-[0.22em] text-gray-600">
          {props.tag}
        </span>
      </div>

      <ul className="pl-6 space-y-1 text-sm text-gray-600 leading-relaxed">
        {props.bullets.map((b) => (
          <li key={b} className="list-disc">
            {b}
          </li>
        ))}
      </ul>
    </div>
  );
}