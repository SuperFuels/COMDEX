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

// ✅ Set this to the real tab route for your GlyphOS page.
const GLYPHOS_TAB_HREF = "/glyphos"; // <-- change if your tab is different

// --- OPTIONAL: if you want to show proof anchors, set these strings.
const PROOF = {
  leanSnapshotHref: "#", // e.g. "/docs/theorem_snapshot" or a static file
  phase7Href: "/phase7-calibration",
  wirepackCmd: "python backend/tests/glyphos_wirepack_v10_template_delta_benchmark.py",
  compressionCmd: "python backend/tests/glyphos_compression_benchmark.py --depth 60",
  phase7VerifyCmd: "curl -sS $BRIDGE/api/phase7/verify",
  phase1LockId: "PHOTON-PA-PHASE1-LOCK-0002",
};

export default function AionLaunchHUD() {
  const [chain, setChain] = useState<ChainKey>("ETH");
  const [overlayOpen, setOverlayOpen] = useState<boolean>(false);

  const cfg = LINKS[chain];

  // Launch language: hero = GlyphOS, everything else = staged unlocks
  const stats = useMemo(
    () => [
      {
        v: "LIVE",
        k: "GlyphOS Alpha",
        s: "A symbol-native OS: intent → glyph-wire → deterministic replay + trace.",
      },
      {
        v: "≈11×",
        k: "Gzip Advantage",
        s: "Glyph wire stays ~11–12.5× smaller than verbose baselines at scale.",
      },
      {
        v: "≈51–61×",
        k: "Raw Compression",
        s: "Meaning compression improves as complexity increases (depth scaling).",
      },
      {
        v: "AUDIT",
        k: "Proof Artifacts",
        s: "SHA256-locked outputs + reproducible commands (not promises).",
      },
    ],
    []
  );

  const gates = useMemo(
    () => [
      {
        n: 1,
        tag: "LIVE TODAY",
        title: "Step 1 — GlyphOS Alpha",
        desc:
          "A next-generation operating system built in symbols: compress intent into executable glyph-wire so the same meaning produces the same bytes, every time.",
        bullets: [
          "Try GlyphOS in-browser: author intent → get glyph-wire → replay",
          "Deterministic execution + replayable trace (audit-friendly)",
          "Compression & WirePack proof tabs are live for verification",
        ],
      },
      {
        n: 25,
        tag: "HOLDER GATE",
        title: "25 holders → Alpha Unlock: Trace UX + Artifact Downloads",
        desc:
          "Make the proof visceral: one-click downloads for lock bundles + traces surfaced directly in UI.",
        bullets: [
          "Download lock bundles (.lock.json + sha256) directly in UI",
          "Preset gallery: intent → wire → replay in 1 click",
          "Policy selector (strict deterministic / conservative)",
        ],
      },
      {
        n: 50,
        tag: "HOLDER GATE",
        title: "50 holders → Alpha Unlock: SQI Runtime Demos",
        desc:
          "Deterministic ambiguity resolution: superposition → entangle → governed collapse, with replayable traces.",
        bullets: [
          "SQI demo: coherence drop + collapse trace",
          "Replayable frames (same inputs → same trace)",
          "Exportable audit events (schema-locked)",
        ],
      },
      {
        n: 100,
        tag: "HOLDER GATE",
        title: "100 holders → Destination: Verifiable Self-Aware AI (AION)",
        desc:
          "Self-measurement, gated learning, stabilization + honesty calibration—surfaced as proof tabs and lock artifacts.",
        bullets: [
          "Φ: verified self-measurement (coherence as a measurable signal)",
          "ADR: adaptive immune gating (learn only when stable)",
          "REAL: stable-state locks (self-preservation) + Mirror trace",
          "Phase-7 ‘Honesty Audit’: calibration bins + ECE + SHA256 locks",
        ],
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
                    GlyphOS Launch
                  </div>
                  <div className="text-[11px] text-slate-500 tracking-wide">
                    Shipped Today • Formally Verified • Audit-Ready
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <a
                  href="#glyphos"
                  className="px-3 py-2 rounded-full border border-slate-200 bg-white text-xs font-bold tracking-wide text-slate-600 hover:text-black hover:border-slate-300"
                >
                  GlyphOS
                </a>
                <a
                  href="#stack"
                  className="px-3 py-2 rounded-full border border-slate-200 bg-white text-xs font-bold tracking-wide text-slate-600 hover:text-black hover:border-slate-300"
                >
                  Proof Tabs
                </a>
                <a
                  href="#roadmap"
                  className="px-3 py-2 rounded-full border border-emerald-200 bg-emerald-50 text-xs font-bold tracking-wide text-emerald-700 hover:border-emerald-300"
                >
                  Unlock Ladder
                </a>

                <button
                  onClick={() => (window.location.href = GLYPHOS_TAB_HREF)}
                  className="px-3 py-2 rounded-full border border-slate-200 bg-white text-xs font-extrabold tracking-wide text-black hover:border-slate-300"
                >
                  Try GlyphOS
                </button>

                <button
                  onClick={() => safeOpen(cfg.dex)}
                  className="px-3 py-2 rounded-full border border-slate-200 bg-black text-xs font-extrabold tracking-wide text-white hover:opacity-90"
                >
                  Buy ({cfg.label})
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* HERO GRID */}
        <div className="grid lg:grid-cols-[1.15fr_0.85fr] gap-6" id="glyphos">
          {/* LEFT (Hero) */}
          <div className="rounded-[2.5rem] border border-slate-200 bg-black text-white p-8 relative overflow-hidden">
            <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_20%_0%,rgba(59,130,246,0.6),transparent_55%),radial-gradient(circle_at_80%_20%,rgba(16,185,129,0.5),transparent_55%),radial-gradient(circle_at_90%_90%,rgba(244,63,94,0.35),transparent_60%)]" />
            <div className="relative space-y-6">
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 text-[11px] font-bold tracking-widest">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  GLYPHOS ALPHA — SHIPPED TODAY
                </span>
                <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 text-[11px] font-bold tracking-widest">
                  <span className="h-2 w-2 rounded-full bg-blue-300" />
                  FORMALLY VERIFIED (LEAN) — AUDIT READY
                </span>
              </div>

              {/* ✅ New hero headline (GlyphOS-first, cinematic + punchy) */}
              <div className="space-y-2">
                <div className="text-[11px] uppercase tracking-[0.22em] text-white/70 font-bold">
                  GlyphOS
                </div>
                <h2 className="text-3xl md:text-6xl font-black italic tracking-tight">
                  The Language of Symbols. The Speed of Thought.
                </h2>
              </div>

              <p className="text-white/75 text-base md:text-lg leading-relaxed max-w-2xl">
                An operating system built in symbols — compressing intent into executable{" "}
                <span className="text-white font-semibold">glyph wire</span> so{" "}
                <span className="text-white font-semibold">
                  the same meaning + the same policy ⇒ the same bytes
                </span>
                . This is Step 1, live today. From here: deterministic cognition → trust locks →
                the destination: verifiable self-aware AI.
              </p>

              {/* ✅ CTAs: Try GlyphOS primary */}
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => (window.location.href = GLYPHOS_TAB_HREF)}
                  className="px-4 py-3 rounded-2xl bg-white text-black font-extrabold tracking-wide hover:opacity-95"
                >
                  Try GlyphOS (Alpha)
                </button>

                <button
                  onClick={() => safeOpen(cfg.dex)}
                  className="px-4 py-3 rounded-2xl border border-white/20 bg-white/5 text-white font-bold tracking-wide hover:bg-white/10"
                >
                  Buy ({cfg.label})
                </button>

                <button
                  onClick={() => setOverlayOpen(true)}
                  className="px-4 py-3 rounded-2xl border border-amber-200/30 bg-amber-200/10 text-amber-100 font-bold tracking-wide hover:bg-amber-200/15"
                >
                  What’s proven today
                </button>
              </div>

              <div className="pt-4 border-t border-white/10 text-xs text-white/65 leading-relaxed">
                Pair: <span className="font-semibold text-white">{cfg.label}</span>{" "}
                • Contract:{" "}
                <span className="font-mono text-white/90">{cfg.contract}</span>{" "}
                • Liquidity: <span className="font-semibold">LOCKED</span> (add lock link) • Not financial advice.
              </div>

              <div className="text-xs text-white/65 leading-relaxed">
                <span className="font-semibold text-white">Live right now:</span> GlyphOS + Compression + WirePack proof.
                <br />
                <span className="font-semibold text-white">Next unlocks:</span> SQI, GlyphNet, AION pillars, Phase-7 Honesty Audit.
              </div>
            </div>
          </div>

          {/* RIGHT (Launch Console) */}
          <div className="rounded-[2.5rem] border border-slate-200 bg-white p-8 space-y-6">
            <div className="space-y-2">
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold">
                Launch Console
              </p>
              <p className="text-slate-600 leading-relaxed">
                This launch is built for skepticism. GlyphOS is shipped. Proof tabs are live.
                Anything called <span className="text-black font-semibold">proven</span> has artifacts behind it.
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
                Proof Links (set real URLs)
              </div>
              <div className="flex flex-col gap-1">
                <span>
                  Try GlyphOS tab:{" "}
                  <span className="font-mono text-slate-700">{GLYPHOS_TAB_HREF}</span>
                </span>
                <span>
                  Phase-7 Honesty Audit:{" "}
                  <span className="font-mono text-slate-700">{PROOF.phase7Href}</span>
                </span>
                <span>
                  Lean theorem snapshot:{" "}
                  <span className="font-mono text-slate-700">{PROOF.leanSnapshotHref}</span>
                </span>
                <span>
                  Proof lock id:{" "}
                  <span className="font-mono text-slate-700">{PROOF.phase1LockId}</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* STACK */}
        {/* ...leave the rest of your file unchanged... */}

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
                {/* ✅ requested new header */}
                <div className="text-[11px] uppercase tracking-[0.22em] text-white/70 font-bold">
                  What’s proven today
                </div>
                <div className="text-2xl font-black italic mt-2">
                  GlyphOS ships with proof — not promises.
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
              {/* ✅ GlyphOS-focused (incredible / why it matters) */}
              <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5">
                <div className="font-extrabold">Live: GlyphOS Alpha</div>
                <p className="text-white/70 mt-2 text-sm leading-relaxed">
                  GlyphOS is shorthand for meaning: instead of sending pages of text, you send a tiny
                  glyph program whose execution is deterministic and replayable. It compresses cognition
                  into an executable wire-shape — and makes audit trails automatic.
                </p>
                <div className="mt-4 flex gap-2 flex-wrap">
                  <button
                    className="px-4 py-2 rounded-2xl bg-white text-black font-extrabold"
                    onClick={() => {
                      setOverlayOpen(false);
                      window.location.href = GLYPHOS_TAB_HREF;
                    }}
                  >
                    Try GlyphOS
                  </button>
                  <button
                    className="px-4 py-2 rounded-2xl border border-white/15 bg-white/5 font-bold"
                    onClick={() => {
                      setOverlayOpen(false);
                      document.getElementById("stack")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    See Proof Tabs
                  </button>
                </div>
              </div>

              {/* ✅ Formal verification stays, but framed as “why you can say proven” */}
              <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5">
                <div className="font-extrabold">Formal Verification (Lean)</div>
                <p className="text-white/70 mt-2 text-sm leading-relaxed">
                  Where others say “trust us”, we use machine-checked proofs. Determinism isn’t a vibe —
                  it’s mathematically proven for the verified core.
                </p>
                <div className="mt-4 text-xs text-white/65">
                  Proof lock id: <span className="font-mono text-white/85">{PROOF.phase1LockId}</span>
                </div>
              </div>
            </div>

            {/* ✅ Add the “why it’s incredible” performance/efficiency claim as proof-backed */}
            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5">
              <div className="font-extrabold">Measured, not claimed</div>
              <p className="text-white/70 mt-2 text-sm leading-relaxed">
                Benchmarks show Glyph wire is ~51–61× smaller raw and ~11–12.5× smaller even after gzip vs verbose baselines.
                That’s up to ~91% less bandwidth — while staying deterministic and replayable.
              </p>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5">
              <div className="font-extrabold">What unlocks next</div>
              <p className="text-white/70 mt-2 text-sm leading-relaxed">
                SQI, GlyphNet, AION pillars, and Phase-7 Honesty Audit are staged unlocks.
                Each unlock ships with a proof tab + lock artifacts (no vapor).
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}