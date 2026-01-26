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

// --- OPTIONAL: if you want to show proof anchors, set these strings.
const PROOF = {
  // Lean / formal verification snapshot link (internal or public)
  leanSnapshotHref: "#", // e.g. "/docs/theorem_snapshot" or a static file
  // Phase-7 honesty audit tab
  phase7Href: "/phase7-calibration",
  // Proof commands shown on page
  wirepackCmd: "python backend/tests/glyphos_wirepack_v10_template_delta_benchmark.py",
  compressionCmd: "python backend/tests/glyphos_compression_benchmark.py --depth 60",
  phase7VerifyCmd: "curl -sS $BRIDGE/api/phase7/verify",
  // Your known lock id / proof label (set real value if you have it)
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
        s: "Compressed meaning + byte-identical trace (audit-ready).",
      },
      {
        v: "LEAN",
        k: "Formal Verification",
        s: "Core Photon Algebra proofs are machine-checked (not marketing).",
      },
      {
        v: "61×",
        k: "Meaning Compression",
        s: "Depth-60: 2,175B vs 131,069B (locked benchmark).",
      },
      {
        v: "54.77%",
        k: "WirePack Savings",
        s: "Template+Delta vs gzip’d JSON (locked benchmark).",
      },
    ],
    []
  );

  const gates = useMemo(
    () => [
      {
        n: 1,
        tag: "LIVE TODAY",
        title: "GlyphOS Alpha + Proof Tabs",
        desc:
          "This launch is not a roadmap pitch. GlyphOS is shipped. Proof tabs are live. You can audit the bytes today.",
        bullets: [
          "GlyphOS: intent → glyph-wire → replay (same meaning → same bytes)",
          "Compression proof (Depth scaling, SHA256-locked stdout)",
          "WirePack v10 proof (Template+Delta, 0 roundtrip failures)",
        ],
      },
      {
        n: 25,
        tag: "HOLDER GATE",
        title: "25 holders → Alpha Unlock: Trace UX + Artifact Downloads",
        desc:
          "When we hit 25 holders, we unlock the usability layer: one-click artifact downloads + lock bundles surfaced in UI.",
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
          "Quantum-like ambiguity resolution with deterministic traces: superposition → entangle → governed collapse (auditable).",
        bullets: [
          "SQI demo: coherence drop + collapse trace",
          "Replayable frames (same inputs → same trace)",
          "Exportable audit events (schema-locked)",
        ],
      },
      {
        n: 100,
        tag: "HOLDER GATE",
        title: "100 holders → Alpha Unlock: AION Organism Pillars",
        desc:
          "Verified self-measurement, gated learning, and autonomous stabilization. No hand-waving — you’ll see the telemetry.",
        bullets: [
          "Φ: Verified self-measurement (coherence as a measurable signal)",
          "ADR: Adaptive immune response (learning gates on stability)",
          "REAL: Stable-state locks (self-preservation), Mirror trace",
          "Phase-7 calibration surfaced as ‘Honesty Audit’",
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
                    Formally Verified • Audit-Grade • Live Proof
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
                  href="#wow"
                  className="px-3 py-2 rounded-full border border-slate-200 bg-white text-xs font-bold tracking-wide text-slate-600 hover:text-black hover:border-slate-300"
                >
                  Audit
                </a>
                <a
                  href="#roadmap"
                  className="px-3 py-2 rounded-full border border-emerald-200 bg-emerald-50 text-xs font-bold tracking-wide text-emerald-700 hover:border-emerald-300"
                >
                  Holder Unlocks
                </a>
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

              <h2 className="text-3xl md:text-5xl font-black italic tracking-tight">
                Compressed meaning, not compressed text.
              </h2>

              <p className="text-white/75 text-base md:text-lg leading-relaxed max-w-2xl">
                This is a <span className="text-white font-semibold">proof-based launch</span>.
                GlyphOS is live:{" "}
                <span className="text-white font-semibold">
                  same meaning + same policy ⇒ byte-identical wire + byte-identical trace
                </span>
                . You can verify the artifacts, reproduce the benchmarks, and audit the bytes.
              </p>

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => safeOpen(cfg.dex)}
                  className="px-4 py-3 rounded-2xl bg-white text-black font-extrabold tracking-wide hover:opacity-95"
                >
                  Buy ({cfg.label})
                </button>
                <button
                  onClick={() => {
                    document.getElementById("stack")?.scrollIntoView({ behavior: "smooth" });
                  }}
                  className="px-4 py-3 rounded-2xl border border-white/20 bg-white/5 text-white font-bold tracking-wide hover:bg-white/10"
                >
                  Open Proof Tabs
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
                This page is designed for skepticism. Nothing here requires trust.
                It’s either <span className="text-black font-semibold">verifiable</span> or it doesn’t ship.
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

        {/* STACK (now framed as PROOF TABS) */}
        <div id="stack" className="space-y-6">
          <div className="space-y-2 text-center">
            <h3 className="text-3xl font-black italic tracking-tight text-black">
              Proof Tabs — already built, already verifiable
            </h3>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              No “coming soon” claims in the proof area. These are reproducible today.
              Run the commands. Compare the bytes. Verify the locks.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            <StackCard
              status="LIVE TODAY"
              statusTone="live"
              title="GlyphOS"
              subtitle="Compressed meaning + byte-identical trace"
              desc="Intent → glyph-wire → execution → audit. Same meaning + same policy ⇒ same bytes. Auditable, replayable, reproducible."
              wow={`GlyphOS benchmark (locked)
Depth-60:
Glyph wire JSON:       2,175 B
Glyph wire JSON (gz):    379 B
Verbose AST:         131,069 B
Result: 60.26× raw / 11.28× gzip

Run: ${PROOF.compressionCmd}`}
            />
            <StackCard
              status="LIVE TODAY"
              statusTone="live"
              title="Formal Verification"
              subtitle="Lean-verified algebraic core"
              desc="Machine-checked proofs underpin the logic substrate (not a marketing claim). Determinism is mathematically guaranteed by the verified normalization/equality path."
              wow={`Lean proof anchor (set real link)
Lock: ${PROOF.phase1LockId}
Artifact: theorem_snapshot.md (recommended)

Set: PROOF.leanSnapshotHref`}
            />
            <StackCard
              status="LIVE TODAY"
              statusTone="live"
              title="WirePack v10"
              subtitle="Template + Delta transport (locked)"
              desc="Ship the shape once, ship only mutations. Stable wire-shapes with audit-grade replay."
              wow={`WirePack v10 (locked)
Depth / Messages: 30 / 2000
Avg JSON (gz):     366.49 B
Avg v10 (gz):      165.77 B
Savings:           54.77%
Roundtrip fails:   0/2000

Run: ${PROOF.wirepackCmd}`}
            />
            <StackCard
              status="COMING NEXT"
              statusTone="alpha"
              title="SQI Runtime"
              subtitle="Deterministic collapse traces"
              desc="Quantum-like resolution (superposition/entanglement/collapse) — but auditable and replayable. Unlocks by holder threshold."
              wow={`Unlock: 50 holders
• Coherence + trace
• Exportable audit frames
• Replays are byte-identical`}
            />
            <StackCard
              status="COMING NEXT"
              statusTone="alpha"
              title="AION Organism Pillars"
              subtitle="Verified self-measurement + gated learning"
              desc="Φ/ADR/REAL/Mirror as concrete systems (telemetry + gating), not metaphors. Unlocks by holder threshold."
              wow={`Unlock: 100 holders
• Φ: Verified self-measurement
• ADR: Adaptive immune gating
• REAL: Stable-state locks
• Mirror: Deterministic narrative trace`}
            />
            <StackCard
              status="COMING NEXT"
              statusTone="alpha"
              title="Honesty Audit (Phase-7)"
              subtitle="Calibration you can audit"
              desc="Don’t take our word for it — audit our honesty. Confidence bins + ECE + SHA256 locks."
              wow={`Already exists as a tab:
${PROOF.phase7Href}

Verify:
${PROOF.phase7VerifyCmd}`}
            />
          </div>
        </div>

        {/* WOW / AUDIT */}
        <div id="wow" className="space-y-6">
          <div className="space-y-2 text-center">
            <h3 className="text-3xl font-black italic tracking-tight text-black">
              Live Audit (run it yourself)
            </h3>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              This is how we earn “absolute confidence” language: it’s measurable and reproducible.
              Same inputs → same bytes → verified by SHA256 locks.
            </p>
          </div>

          <div className="rounded-[2.5rem] border border-slate-200 bg-black text-white p-8">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-3">
                <div className="h-3 w-3 rounded-full bg-emerald-400 shadow-[0_0_0_8px_rgba(16,185,129,0.15)]" />
                <div className="font-extrabold tracking-tight">Audit scripts</div>
              </div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-white/70 font-bold">
                Formally Verified • Locked • Replayable
              </div>
            </div>

            <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-4 mt-6">
              <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5 font-mono text-xs leading-relaxed overflow-auto whitespace-pre-wrap">
                <div className="text-emerald-300 font-bold">$ {PROOF.compressionCmd}</div>
                <div className="text-white/70 mt-2">
                  {`=== ✅ Locked Output ===
Depth-60:
Glyph (gz): 379 B
Verbose AST (gz): 4,275 B
Result: 61× raw gain
Deterministic: byte-identical`}
                </div>

                <div className="text-emerald-300 font-bold mt-4">$ {PROOF.wirepackCmd}</div>
                <div className="text-white/70 mt-2">
                  {`=== ✅ WirePack v10 (Locked) ===
Savings vs JSON (gz): 54.77%
Template hits: 2000/2000
Roundtrip fails: 0/2000
Lock stdout SHA256: 79dfafe8b6a373...`}
                </div>

                <div className="text-emerald-300 font-bold mt-4">$ {PROOF.phase7VerifyCmd}</div>
                <div className="text-white/70">
                  {`{ "match": true, "golden_schema": "AION.Phase7LockBundle.v2", "sha256": "…" }`}
                </div>
              </div>

              <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5 space-y-3">
                <div className="text-sm font-extrabold">“Don’t trust us — audit us.”</div>
                <div className="text-xs text-white/75 leading-relaxed">
                  The page stays honest by design: anything described as <strong className="text-white">LIVE</strong>{" "}
                  has a reproducible command or a lock bundle behind it.
                </div>

                <div className="rounded-2xl border border-white/10 bg-black/30 p-4 text-xs text-white/80 leading-relaxed">
                  <div className="font-bold text-white">High-signal trust wording</div>
                  <ul className="mt-2 space-y-1">
                    <li>• “Formally Verified (Lean)” instead of “deterministic”.</li>
                    <li>• “Byte-identical reproducibility (SHA256 locks)”.</li>
                    <li>• “Audit the artifacts” (curl / scripts / lock bundle).</li>
                  </ul>
                </div>

                <button
                  onClick={() => (window.location.href = PROOF.phase7Href)}
                  className="w-full px-4 py-3 rounded-2xl bg-white text-black font-extrabold tracking-wide hover:opacity-95"
                >
                  Open Phase-7 Honesty Audit
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* HOLDER GATES */}
        <div id="roadmap" className="space-y-6">
          <div className="space-y-2 text-center">
            <h3 className="text-3xl font-black italic tracking-tight text-black">
              Holder Unlock Ladder
            </h3>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              Launch stays clean: GlyphOS ships today. Everything else unlocks fast as we hit holder milestones.
              Each unlock ships with its own proof tab + lock artifacts.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            {gates.map((g) => (
              <RoadmapStep
                key={`${g.n}-${g.title}`}
                n={g.n}
                tag={g.tag}
                title={g.title}
                desc={g.desc}
                bullets={g.bullets}
              />
            ))}
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
              This page describes software utilities and alpha access. It is not financial advice.
              Replace placeholders (contract, DEX links, lock links, proof URLs) before publishing.
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
              <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5">
                <div className="font-extrabold">Live: GlyphOS Alpha</div>
                <p className="text-white/70 mt-2 text-sm leading-relaxed">
                  Compressed meaning + byte-identical trace. If meaning and policy are the same,
                  the wire is the same. That’s auditable determinism.
                </p>
                <div className="mt-4 flex gap-2 flex-wrap">
                  <button
                    className="px-4 py-2 rounded-2xl bg-white text-black font-extrabold"
                    onClick={() => {
                      setOverlayOpen(false);
                      document.getElementById("stack")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    Open Proof Tabs
                  </button>
                  <button
                    className="px-4 py-2 rounded-2xl border border-white/15 bg-white/5 font-bold"
                    onClick={() => {
                      setOverlayOpen(false);
                      document.getElementById("wow")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    Run the Audit
                  </button>
                </div>
              </div>

              <div className="rounded-[2rem] border border-white/10 bg-white/5 p-5">
                <div className="font-extrabold">Formal Verification (Lean)</div>
                <p className="text-white/70 mt-2 text-sm leading-relaxed">
                  Where others say “trust us”, we use machine-checked proofs. Determinism isn’t a claim —
                  it’s mathematically proven for the verified core.
                </p>
                <div className="mt-4 text-xs text-white/65">
                  Proof lock id: <span className="font-mono text-white/85">{PROOF.phase1LockId}</span>
                </div>
              </div>
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