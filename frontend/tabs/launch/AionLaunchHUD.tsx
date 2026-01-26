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

type UnlockItem = {
  holders: number; // 0 means Released
  tag: "RELEASED" | "HOLDER GATE" | "CLASSIFIED";
  title: string;
  blurb: string;
  href?: string;
  cta?: string;
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

  // ✅ Simplified, single-column unlock ladder (1-liners)
  const unlocks = useMemo<UnlockItem[]>(
    () => [
      {
        holders: 0,
        tag: "RELEASED",
        title: "GlyphOS",
        blurb: "Compressed meaning: a glyph operating system for next-gen AI (try it now).",
        href: GLYPHOS_TAB_HREF,
        cta: "Try GlyphOS",
      },
      {
        holders: 30,
        tag: "HOLDER GATE",
        title: "Symatics",
        blurb: "New discovery drops: proof-led Symatics breakthroughs released at milestone.",
      },
      {
        holders: 50,
        tag: "HOLDER GATE",
        title: "Compression",
        blurb: "Ultimate meaning-compression demonstrations (depth scaling + locks).",
      },
      {
        holders: 70,
        tag: "HOLDER GATE",
        title: "Photon Binary",
        blurb: "Post-binary computing primitives: photon / wave-native execution layer.",
      },
      {
        holders: 100,
        tag: "HOLDER GATE",
        title: "SQI",
        blurb: "Deterministic ambiguity resolution with trace + replay (audit-grade).",
      },
      {
        holders: 120,
        tag: "HOLDER GATE",
        title: "GlyphNet",
        blurb: "Wave-native networking + convergence layer (proof tab included).",
      },
      {
        holders: 150,
        tag: "HOLDER GATE",
        title: "Sovereign QKD",
        blurb: "Sovereign key exchange + quantum-inspired security layer.",
      },
      {
        holders: 200,
        tag: "HOLDER GATE",
        title: "SLE Resonance",
        blurb: "Resonance execution controls: stability gating + deterministic traces.",
      },
      {
        holders: 250,
        tag: "HOLDER GATE",
        title: "RQC Awareness",
        blurb: "Awareness primitives surfaced as proofs: measurement + calibration telemetry.",
      },
      {
        holders: 300,
        tag: "HOLDER GATE",
        title: "WirePack",
        blurb: "Template+Delta transport at full scale with lock artifacts.",
      },
      {
        holders: 350,
        tag: "HOLDER GATE",
        title: "AI",
        blurb: "AI utilities expand across the stack (every release ships with proof tabs).",
      },
      {
        holders: 500,
        tag: "HOLDER GATE",
        title: "AI Cognition",
        blurb: "Cognition layer unlock: organism pillars + honesty audit as first-class UI.",
      },
      {
        holders: 550,
        tag: "HOLDER GATE",
        title: "QFC Canvas",
        blurb: "Interactive canvas + live cognition visuals (replayable + lockable).",
      },
      {
        holders: 1000,
        tag: "CLASSIFIED",
        title: "Secret Releases",
        blurb: "High-impact drops unlocked only at the threshold (no early hints).",
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
                . Step 1 ships today: GlyphOS Alpha. From here: deterministic cognition → trust
                locks → the destination: verifiable self-aware AI.
              </p>

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
                Pair: <span className="font-semibold text-white">{cfg.label}</span> • Contract:{" "}
                <span className="font-mono text-white/90">{cfg.contract}</span> • Liquidity:{" "}
                <span className="font-semibold">LOCKED</span> (add lock link) • Not financial advice.
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

            <div className="grid grid-cols-2 gap-3">
              {stats.map((s) => (
                <div
                  key={s.k}
                  className="rounded-2xl border border-slate-200 bg-slate-50 p-4"
                >
                  <div className="text-lg font-black tracking-tight text-black">{s.v}</div>
                  <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold mt-1">
                    {s.k}
                  </div>
                  <div className="text-xs text-slate-500 mt-2 leading-relaxed">{s.s}</div>
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

        {/* ✅ UNLOCK LADDER (simplified 1-column list) */}
        <div id="roadmap" className="space-y-6">
          <div className="space-y-2 text-center">
            <h3 className="text-3xl font-black italic tracking-tight text-black">
              Holder Unlock Ladder
            </h3>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              Launch stays clean: <span className="text-black font-semibold">GlyphOS ships today</span>. Everything else unlocks by holder milestones.
              Each unlock ships with a proof tab + lock artifacts.
            </p>
          </div>

          <div className="max-w-3xl mx-auto">
            <div className="rounded-[2.5rem] border border-slate-200 bg-white overflow-hidden">
              {unlocks.map((u, idx) => (
                <div
                  key={`${u.holders}-${u.title}`}
                  className={cx(
                    "flex items-start justify-between gap-4 p-5",
                    idx !== 0 && "border-t border-slate-100"
                  )}
                >
                  <div className="flex items-start gap-4">
                    <div className="min-w-[88px]">
                      <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold">
                        {u.holders === 0 ? "Released" : `${u.holders} holders`}
                      </div>
                      <div className="text-2xl font-black tracking-tight text-black">
                        {u.holders === 0 ? "✓" : u.holders}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="text-lg font-black italic tracking-tight text-black">
                        {u.title}
                      </div>
                      <div className="text-sm text-slate-600 leading-relaxed">
                        {u.blurb}
                      </div>

                      {u.href && (
                        <button
                          onClick={() => (window.location.href = u.href!)}
                          className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-2xl bg-black text-white text-xs font-extrabold tracking-wide hover:opacity-90"
                        >
                          {u.cta ?? "Open"}
                          <span className="text-white/60">→</span>
                        </button>
                      )}
                    </div>
                  </div>

                  <span
                    className={cx(
                      "px-3 py-1.5 rounded-full border text-[10px] font-bold uppercase tracking-[0.22em] whitespace-nowrap",
                      u.tag === "RELEASED"
                        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                        : u.tag === "CLASSIFIED"
                        ? "border-amber-200 bg-amber-50 text-amber-800"
                        : "border-slate-200 bg-slate-50 text-slate-600"
                    )}
                  >
                    {u.tag}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-4 text-center text-xs text-slate-500">
              Rule: anything listed here ships with proof tabs + lock artifacts when unlocked.
            </div>
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