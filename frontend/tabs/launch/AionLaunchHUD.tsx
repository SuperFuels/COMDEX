// /workspaces/COMDEX/frontend/tabs/launch/AionLaunchHUD.tsx
"use client";

import React, { useMemo, useState } from "react";
import Image from "next/image";

type ChainKey = "ETH" | "SOL";

const LINKS: Record<ChainKey, { label: string; dex: string; contract: string; pairLabel: string }> = {
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
    alert("Set your link in AionLaunchHUD.tsx before publishing.");
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

function shortAddr(addr: string, head = 6, tail = 4) {
  if (!addr) return "";
  if (addr.length <= head + tail + 3) return addr;
  return `${addr.slice(0, head)}…${addr.slice(-tail)}`;
}

// ✅ Try Glyph OS should go to your real tab route:
const GLYPHOS_TAB_HREF = "/glyph";

// ✅ Set real links (UPDATED)
const SOCIAL = {
  telegram: "https://t.me/Glyph_Os",
  x: "https://x.com/Glyph_Os",
  chart: "https://YOUR_CHART_LINK",
};

// ✅ Set real repo (kept, but section below is commented out)
const GITHUB_REPO_URL = "https://github.com/YOUR_ORG/YOUR_REPO";

const PROOF = {
  leanSnapshotHref: "#",
  phase7Href: "/phase7-calibration",
  wirepackCmd: "python backend/tests/glyphos_wirepack_v10_template_delta_benchmark.py",
  compressionCmd: "python backend/tests/glyphos_compression_benchmark.py --depth 60",
  phase7VerifyCmd: "curl -sS $BRIDGE/api/phase7/verify",
  phase1LockId: "PHOTON-PA-PHASE1-LOCK-0002",
};

type UnlockTag = "RELEASED" | "HOLDER GATE" | "CLASSIFIED";

type UnlockItem = {
  holders: number; // 0 = released
  tag: UnlockTag;
  title: string;
  blurb: string;
  href?: string;
  cta?: string;
};

export default function AionLaunchHUD() {
  const [chain, setChain] = useState<ChainKey>("SOL");
  const [overlayOpen, setOverlayOpen] = useState<boolean>(false);

  const cfg = LINKS[chain];

  const stats = useMemo(
    () => [
      { v: "LIVE", k: "GlyphOS Alpha", s: "intent → glyph-wire → deterministic replay + trace." },
      { v: "≈11×", k: "Gzip Advantage", s: "Glyph wire stays ~11–12.5× smaller at scale." },
      { v: "≈51–61×", k: "Raw Compression", s: "Meaning compression improves as complexity increases." },
      { v: "AUDIT", k: "Proof Artifacts", s: "SHA256-locked outputs + reproducible commands." },
    ],
    []
  );

  const unlocks = useMemo<UnlockItem[]>(
    () => [
      {
        holders: 0,
        tag: "RELEASED",
        title: "GlyphOS",
        blurb: "Compressed meaning: a glyph operating system for next-gen AI (try it now).",
        href: GLYPHOS_TAB_HREF,
        cta: "Open Glyph OS",
      },

      {
        holders: 0,
        tag: "RELEASED",
        title: "Symatics",
        blurb: "The symbolic substrate: phase-aware math powering deterministic cognition.",
        href: "/symatics",
        cta: "Open Symatics",
      },

      {
        holders: 0,
        tag: "RELEASED",
        title: "Photon Algebra",
        blurb: "Formally verified operator core (Lean) — the proof substrate behind deterministic cognition.",
        href: "/photon-algebra-demo",
        cta: "Open Photon Algebra",
      },

      {
        holders: 0,
        tag: "RELEASED",
        title: "Compression",
        blurb: "Meaning compression at scale — less bandwidth, same semantics, replayable outputs.",
        href: "/compression",
        cta: "Open Compression",
      },
      {
        holders: 0,
        tag: "RELEASED",
        title: "Photon Binary",
        blurb: "Post-binary compute primitives: symbols-as-ops for light-wave era execution.",
        href: "/photon-binary",
        cta: "Open Photon Binary",
      },
      { holders: 100, tag: "HOLDER GATE", title: "SQI", blurb: "Symbolic Quantum Intelligence: superposition/entanglement/collapse with deterministic trace." },
      { holders: 120, tag: "HOLDER GATE", title: "GlyphNet", blurb: "Wave-native networking: intent transport + convergence + tamper-evident delivery." },
      { holders: 150, tag: "HOLDER GATE", title: "Sovereign QKD", blurb: "Observer-detectable transport: interference becomes the alarm, not a footnote." },
      { holders: 200, tag: "HOLDER GATE", title: "SLE Resonance", blurb: "Resonance logic execution: coherence-stable computation as a first-class runtime rule." },
      { holders: 250, tag: "HOLDER GATE", title: "RQC Awareness", blurb: "Self-measuring control loops that detect drift and restore stable truth autonomously." },
      { holders: 300, tag: "HOLDER GATE", title: "WirePack", blurb: "Template+Delta transport with audit-grade replay and lock artifacts." },
      { holders: 350, tag: "HOLDER GATE", title: "AI", blurb: "AION: a logic organism — self-stabilizing intelligence governed by homeostasis, not heuristics." },
      {
        holders: 500,
        tag: "HOLDER GATE",
        title: "AI Cognition",
        blurb: 'Legacy AI is a "black box" that guesses with confidence. AION measures internal coherence before it speaks.',
      },
      { holders: 550, tag: "HOLDER GATE", title: "QFC Canvas", blurb: "Interactive multiverse canvas: live traces, coherence fields, and proof-first visualization." },
      { holders: 1000, tag: "CLASSIFIED", title: "Secret Releases", blurb: "High-impact drops unlocked only at the threshold (no early hints)." },
    ],
    []
  );

  return (
    <>
      {/* ✅ mobile-safe gutters */}
      <div className="space-y-8 sm:space-y-10 px-3 sm:px-6">
        {/* ✅ MOBILE-SAFE TOPBAR */}
        <div className="sm:sticky sm:top-0 sm:z-20 sm:-mx-6 sm:px-6">
          <div className="rounded-[1.25rem] sm:rounded-[1.75rem] border border-slate-200 bg-white/85 backdrop-blur px-3 sm:px-4 py-3 shadow-sm">
            <div className="flex items-start sm:items-center justify-between gap-3">
              {/* left */}
              <div className="flex items-center gap-3 min-w-0">
                <div className="h-10 w-10 shrink-0 overflow-hidden rounded-2xl border border-slate-200 bg-white">
                  <Image
                    src="/images/g_logo.jpeg"
                    alt="GIP"
                    width={40}
                    height={40}
                    className="h-full w-full object-cover"
                    priority
                  />
                </div>

                <div className="min-w-0">
                  <div className="text-sm font-extrabold tracking-tight text-black">
                    Pair: GIP | Contract: EgeMuFoxWthBQbBcoWq8BNXowJJcVpjP6zZZZbnn8qFP
                  </div>

                  <div className="text-[11px] text-slate-500 tracking-wide leading-snug min-w-0">
                    <span className="inline sm:hidden">
                      Contract:{" "}
                      <span
                        className="font-mono text-slate-700 select-all"
                        title="EgeMuFoxWthBQbBcoWq8BNXowJJcVpjP6zZZZbnn8qFP"
                      >
                        {shortAddr("EgeMuFoxWthBQbBcoWq8BNXowJJcVpjP6zZZZbnn8qFP")}
                      </span>{" "}
                      • Liquidity: LOCKED
                    </span>

                    <span className="hidden sm:inline">
                      Contract:{" "}
                      <span
                        className="font-mono text-slate-700 select-all"
                        title="EgeMuFoxWthBQbBcoWq8BNXowJJcVpjP6zZZZbnn8qFP"
                      >
                        EgeMuFoxWthBQbBcoWq8BNXowJJcVpjP6zZZZbnn8qFP
                      </span>{" "}
                      • Liquidity: LOCKED (tiny url)
                    </span>
                  </div>
                </div>
              </div>

              {/* actions */}
              <div
                className={cx(
                  "flex items-center gap-2",
                  "whitespace-nowrap overflow-x-auto max-w-[55vw] sm:max-w-none",
                  "[&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]"
                )}
              >
                <button
                  onClick={() => (window.location.href = GLYPHOS_TAB_HREF)}
                  className="px-3 py-2 rounded-full border border-slate-200 bg-white text-xs font-extrabold tracking-wide text-black hover:border-slate-300 shrink-0"
                >
                  Glyph OS
                </button>

                {/* Chart -> DexTools icon */}
                <button
                  onClick={() => safeOpen(SOCIAL.chart)}
                  aria-label="DexTools chart"
                  title="Chart"
                  className="px-3 py-2 rounded-full border border-slate-200 bg-white hover:border-slate-300 shrink-0 inline-flex items-center justify-center"
                >
                  <span className="h-5 w-5 overflow-hidden rounded-full">
                    <Image
                      src="/images/dextools.png"
                      alt="DexTools"
                      width={20}
                      height={20}
                      className="h-full w-full object-contain"
                      priority
                    />
                  </span>
                </button>

                {/* Telegram -> icon */}
                <button
                  onClick={() => safeOpen(SOCIAL.telegram)}
                  aria-label="Telegram"
                  title="Telegram"
                  className="px-3 py-2 rounded-full border border-blue-200 bg-blue-50 hover:border-blue-300 shrink-0 inline-flex items-center justify-center"
                >
                  <span className="h-5 w-5 overflow-hidden rounded-full">
                    <Image
                      src="/images/telegram.png"
                      alt="Telegram"
                      width={20}
                      height={20}
                      className="h-full w-full object-contain"
                      priority
                    />
                  </span>
                </button>

                <button
                  onClick={() => safeOpen(SOCIAL.x)}
                  className="px-3 py-2 rounded-full border border-slate-200 bg-black text-xs font-extrabold tracking-wide text-white hover:opacity-90 shrink-0"
                >
                  X
                </button>

                <button
                  onClick={() => safeOpen(cfg.dex)}
                  aria-label="Buy GIP on Raydium"
                  title="Buy GIP"
                  className="px-3 py-2 rounded-full border border-emerald-200 bg-white text-xs font-extrabold tracking-wide text-black hover:border-emerald-300 hover:bg-emerald-50 shrink-0 inline-flex items-center justify-center"
                >
                  <span className="h-5 w-5 overflow-hidden rounded-full">
                    <Image
                      src="/images/Raydium.png"
                      alt="Raydium"
                      width={20}
                      height={20}
                      className="h-full w-full object-contain"
                      priority
                    />
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* HERO GRID */}
        <div className="grid lg:grid-cols-[1.15fr_0.85fr] gap-4 sm:gap-6" id="glyphos">
          {/* LEFT */}
          <div className="rounded-[2rem] sm:rounded-[2.5rem] border border-slate-200 bg-black text-white p-5 sm:p-8 relative overflow-hidden">
            <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_20%_0%,rgba(59,130,246,0.6),transparent_55%),radial-gradient(circle_at_80%_20%,rgba(16,185,129,0.5),transparent_55%),radial-gradient(circle_at_90%_90%,rgba(244,63,94,0.35),transparent_60%)]" />
            <div className="relative space-y-5 sm:space-y-6">
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
                <div className="text-[11px] uppercase tracking-[0.22em] text-white/70 font-bold">GlyphOS</div>
                <h2 className="text-3xl sm:text-4xl md:text-6xl font-black italic tracking-tight">
                  The Language of Symbols. The Speed of Thought.
                </h2>
              </div>

              <p className="text-white/75 text-base sm:text-lg leading-relaxed max-w-2xl">
                An operating system built in symbols — compressing intent into executable{" "}
                <span className="text-white font-semibold">glyph wire</span> so{" "}
                <span className="text-white font-semibold">the same meaning + the same policy ⇒ the same bytes</span>. Step 1 ships
                today: GlyphOS Alpha. From here: SQI + GlyphNet → deterministic cognition → trust locks → verifiable self-aware AI.
              </p>

              <div className="flex flex-col sm:flex-row sm:flex-wrap gap-2">
                <button
                  onClick={() => (window.location.href = GLYPHOS_TAB_HREF)}
                  className="w-full sm:w-auto px-4 py-3 rounded-2xl bg-white text-black font-extrabold tracking-wide hover:opacity-95"
                >
                  Open Glyph OS
                </button>

                <button
                  onClick={() => safeOpen(cfg.dex)}
                  aria-label="Buy GIP on Raydium"
                  title="Buy GIP"
                  className="w-full sm:w-auto px-4 py-3 rounded-2xl border border-emerald-200 bg-white hover:bg-emerald-50 hover:border-emerald-300 transition inline-flex items-center justify-center"
                >
                  <span className="h-6 w-6 overflow-hidden rounded-full">
                    <Image
                      src="/images/Raydium.png"
                      alt="Raydium"
                      width={24}
                      height={24}
                      className="h-full w-full object-contain"
                      priority
                    />
                  </span>
                </button>

                <button
                  onClick={() => setOverlayOpen(true)}
                  className="w-full sm:w-auto px-4 py-3 rounded-2xl border border-amber-200/30 bg-amber-200/10 text-amber-100 font-bold tracking-wide hover:bg-amber-200/15"
                >
                  What’s proven today
                </button>
              </div>

              <div className="pt-4 border-t border-white/10 text-xs text-white/65 leading-relaxed">
                Pair: <span className="font-semibold text-white">{cfg.label}</span> • Contract:{" "}
                <span
                  className="font-mono text-white/90 select-all"
                  title="EgeMuFoxWthBQbBcoWq8BNXowJJcVpjP6zZZZbnn8qFP"
                >
                  <span className="inline sm:hidden">
                    {shortAddr("EgeMuFoxWthBQbBcoWq8BNXowJJcVpjP6zZZZbnn8qFP")}
                  </span>
                  <span className="hidden sm:inline">EgeMuFoxWthBQbBcoWq8BNXowJJcVpjP6zZZZbnn8qFP</span>
                </span>{" "}
                • Liquidity: <span className="font-semibold">LOCKED</span> (add lock link) • Not financial advice.
              </div>
            </div>
          </div>

          {/* RIGHT */}
          <div className="rounded-[2rem] sm:rounded-[2.5rem] border border-slate-200 bg-white p-5 sm:p-8 space-y-5 sm:space-y-6">
            <div className="space-y-2">
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold">Launch Console</p>
              <p className="text-slate-600 leading-relaxed">
                This launch is built for skepticism. GlyphOS is shipped. Anything called{" "}
                <span className="text-black font-semibold">proven</span> has artifacts behind it.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              {(["SOL"] as ChainKey[]).map((k) => (
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

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {stats.map((s) => (
                <div key={s.k} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="text-lg font-black tracking-tight text-black">{s.v}</div>
                  <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold mt-1">{s.k}</div>
                  <div className="text-xs text-slate-500 mt-2 leading-relaxed">{s.s}</div>
                </div>
              ))}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600 leading-relaxed">
              <div className="font-bold uppercase tracking-[0.22em] text-slate-500 text-[11px] mb-2">Proof Links (set real URLs)</div>
              <div className="flex flex-col gap-1">
                <span>
                  Glyph OS tab: <span className="font-mono text-slate-700">{GLYPHOS_TAB_HREF}</span>
                </span>
                <span>
                  Phase-7 Honesty Audit: <span className="font-mono text-slate-700">{PROOF.phase7Href}</span>
                </span>
                <span>
                  Lean theorem snapshot: <span className="font-mono text-slate-700">{PROOF.leanSnapshotHref}</span>
                </span>
                <span>
                  Proof lock id: <span className="font-mono text-slate-700">{PROOF.phase1LockId}</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ===========================
            FORMAL PROOF REPOSITORY
            (COMMENTED OUT FOR LATER RELEASE)
           =========================== */}
        {/*
        <div id="proofs" className="space-y-4">
          <div className="text-center space-y-2 px-1">
            <h3 className="text-2xl md:text-3xl font-black italic tracking-tight text-black">Git Formal Proof Repository</h3>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              Verifiable mathematical equations, frameworks, tests & papers — machine-checkable proof, not screenshots.
            </p>
          </div>

          <div className="max-w-4xl mx-auto rounded-[2rem] sm:rounded-[2.5rem] border border-slate-200 bg-white p-4 sm:p-6 space-y-4">
            <div className="grid md:grid-cols-2 gap-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold">GitHub Repository (Public)</div>
                <div className="mt-2 text-sm text-slate-700 leading-relaxed">
                  <span className="font-semibold text-black">Required:</span> a public repo containing{" "}
                  <span className="font-mono">.lean</span> files + reproducible test commands.
                </div>

                <button
                  onClick={() => safeOpen(GITHUB_REPO_URL)}
                  className="mt-3 w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2 rounded-2xl bg-black text-white text-xs font-extrabold tracking-wide hover:opacity-90"
                >
                  Open GitHub <span className="text-white/60">→</span>
                </button>

                <div className="mt-2 text-[11px] text-slate-500">Audited by a third party (add auditor link if available).</div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold">Missing Links Checklist</div>

                <div className="mt-2 text-sm text-slate-700 leading-relaxed space-y-2">
                  <div>
                    • <span className="font-semibold text-black">Lean proof anchor:</span>{" "}
                    <span className="font-mono">PROOF.leanSnapshotHref</span> is still a placeholder.
                  </div>
                  <div>
                    • <span className="font-semibold text-black">Contract address:</span> set{" "}
                    <span className="font-mono">LINKS[chain].contract</span> to the real address.
                  </div>
                </div>

                <button
                  onClick={() => safeOpen(PROOF.leanSnapshotHref)}
                  className="mt-3 w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2 rounded-2xl border border-slate-200 bg-white text-xs font-extrabold tracking-wide text-black hover:border-slate-300"
                >
                  Open Lean Proof Anchor <span className="text-black/40">→</span>
                </button>
              </div>
            </div>

            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <div className="text-[11px] uppercase tracking-[0.22em] text-amber-700 font-bold">The Reality</div>
              <p className="mt-2 text-sm text-amber-900 leading-relaxed">
                Writing formal proofs for AI logic is incredibly difficult and time-consuming. If someone claims they’ve done it,
                they should provide a public GitHub repository with <span className="font-mono">.lean</span> files. Without that link,
                the claim is just text on a screen.
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500 font-bold mb-2">
                Reproducible Verification Commands
              </div>
              <div className="font-mono text-xs text-slate-700 whitespace-pre-wrap break-words">
                {`$ ${PROOF.compressionCmd}
$ ${PROOF.wirepackCmd}
$ ${PROOF.phase7VerifyCmd}`}
              </div>
            </div>
          </div>
        </div>
        */}

        {/* UNLOCK LADDER */}
        <div id="roadmap" className="space-y-6">
          <div className="space-y-2 text-center px-1">
            <h3 className="text-3xl font-black italic tracking-tight text-black">Holder Unlock Ladder</h3>
            <p className="text-slate-500 max-w-3xl mx-auto leading-relaxed">
              Launch stays clean: <span className="text-black font-semibold">GlyphOS ships today</span>. Everything else unlocks by
              holder milestones. Each unlock ships with proof tabs + lock artifacts.
            </p>
          </div>

          <div className="max-w-3xl mx-auto">
            <div className="rounded-[2rem] sm:rounded-[2.5rem] border border-slate-200 bg-white overflow-hidden">
              {unlocks.map((u, idx) => {
                const isReleaseRow = idx === 0;

                return (
                  <div
                    key={`${u.holders}-${u.title}`}
                    className={cx("flex items-start justify-between gap-3 sm:gap-4 p-4 sm:p-5", idx !== 0 && "border-t border-slate-100")}
                  >
                    <div className="flex items-start gap-3 sm:gap-4 min-w-0">
                      <div className="min-w-[84px] sm:min-w-[104px]">
                        <div
                          className={cx(
                            "text-[10px] sm:text-[11px] uppercase tracking-[0.22em] font-bold",
                            isReleaseRow ? "text-emerald-700" : "text-slate-500"
                          )}
                        >
                          {u.holders === 0 ? "Released" : `${u.holders} holders`}
                        </div>

                        <div
                          className={cx("text-xl sm:text-2xl font-black tracking-tight", isReleaseRow ? "text-emerald-600" : "text-black")}
                        >
                          {u.holders === 0 ? "✓" : u.holders}
                        </div>
                      </div>

                      <div className="space-y-1 min-w-0">
                        <div className="text-base sm:text-lg font-black italic tracking-tight text-black">{u.title}</div>
                        <div className="text-sm text-slate-600 leading-relaxed break-words">{u.blurb}</div>

                        {u.href && (
                          <button
                            onClick={() => (window.location.href = u.href!)}
                            className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-2xl bg-black text-white text-xs font-extrabold tracking-wide hover:opacity-90"
                          >
                            {u.cta ?? "Open"} <span className="text-white/60">→</span>
                          </button>
                        )}
                      </div>
                    </div>

                    <span
                      className={cx(
                        "shrink-0 px-3 py-1.5 rounded-full border text-[10px] font-bold uppercase tracking-[0.22em] whitespace-nowrap",
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
                );
              })}
            </div>

            <div className="mt-4 text-center text-xs text-slate-500 px-1">
              Rule: anything listed here ships with proof tabs + lock artifacts when unlocked.
            </div>
          </div>
        </div>
      </div>

      {/* ✅ MODAL: scrollable on short screens */}
      {overlayOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur flex items-center justify-center p-3 sm:p-4"
          onClick={() => setOverlayOpen(false)}
        >
          <div
            className="w-full max-w-3xl rounded-[2rem] sm:rounded-[2.5rem] border border-white/10 bg-black text-white p-5 sm:p-8 space-y-5 sm:space-y-6 max-h-[85vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-[11px] uppercase tracking-[0.22em] text-white/70 font-bold">What’s proven today</div>
                <div className="text-xl sm:text-2xl font-black italic mt-2">GlyphOS ships with proof — not promises.</div>
              </div>
              <button
                onClick={() => setOverlayOpen(false)}
                className="px-3 py-2 rounded-2xl border border-white/15 bg-white/5 hover:bg-white/10"
              >
                ✕
              </button>
            </div>

            <div className="grid md:grid-cols-2 gap-3 sm:gap-4">
              <div className="rounded-[1.5rem] sm:rounded-[2rem] border border-white/10 bg-white/5 p-5">
                <div className="font-extrabold">Live: GlyphOS Alpha</div>

                <div className="mt-3 overflow-hidden rounded-2xl border border-white/10 bg-black/20">
                  <Image
                    src="/images/GIP.png"
                    alt="GIP"
                    width={1200}
                    height={700}
                    className="h-auto w-full object-contain"
                    priority
                  />
                </div>

                <div className="mt-4 flex flex-col sm:flex-row gap-2">
                  <button
                    className="w-full sm:w-auto px-4 py-2 rounded-2xl bg-white text-black font-extrabold"
                    onClick={() => {
                      setOverlayOpen(false);
                      window.location.href = GLYPHOS_TAB_HREF;
                    }}
                  >
                    Open Glyph OS
                  </button>
                  <button
                    className="w-full sm:w-auto px-4 py-2 rounded-2xl border border-white/15 bg-white/5 font-bold"
                    onClick={() => {
                      setOverlayOpen(false);
                      document.getElementById("roadmap")?.scrollIntoView({ behavior: "smooth" });
                    }}
                  >
                    View Unlock Ladder
                  </button>
                </div>
              </div>

              <div className="rounded-[1.5rem] sm:rounded-[2rem] border border-white/10 bg-white/5 p-5">
                <div className="font-extrabold">Formal Verification (Lean)</div>
                <p className="text-white/70 mt-2 text-sm leading-relaxed">
                  Where others say “trust us”, we use machine-checked proofs. Determinism isn’t a vibe — it’s proven for the verified core.
                </p>
                <div className="mt-4 text-xs text-white/65">
                  Proof lock id: <span className="font-mono text-white/85 select-all">{PROOF.phase1LockId}</span>
                </div>
              </div>
            </div>

            <div className="rounded-[1.5rem] sm:rounded-[2rem] border border-white/10 bg-white/5 p-5">
              <div className="font-extrabold">Measured, not claimed</div>
              <p className="text-white/70 mt-2 text-sm leading-relaxed">
                Benchmarks show glyph wire can be ~51–61× smaller raw and ~11–12.5× smaller even after gzip vs verbose baselines —
                while remaining deterministic and replayable.
              </p>
            </div>

            <div className="rounded-[1.5rem] sm:rounded-[2rem] border border-white/10 bg-white/5 p-5">
              <div className="font-extrabold">What unlocks next</div>
              <p className="text-white/70 mt-2 text-sm leading-relaxed">
                SQI, GlyphNet, AION pillars, and Phase-7 Honesty Audit unlock by milestones. Each unlock ships with proof tabs + lock artifacts (no vapor).
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}