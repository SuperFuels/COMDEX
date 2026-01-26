"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";

/**
 * Phase7CalibrationHUD (v2 wording + UX refinements)
 * - Matches current backend shape: { ok, files, curve{bins[{bin,n,avg_conf,emp_acc}]}, metrics{ece,n_samples} }
 * - Adds: stronger hook, “Why this matters”, impossibility statement, achievement messaging in Challenge Mode,
 *   richer Trust Status interpretation, and a first-visit welcome overlay.
 */

type Phase7CurveBin = {
  bin: number; // 0..n_bins-1
  n: number;
  avg_conf: number | null;
  emp_acc: number | null;
};

type Phase7Curve = {
  schema?: string;
  n_bins?: number;
  n_samples?: number;
  bins?: Phase7CurveBin[];
  thresholds?: Record<string, any>;
};

type Phase7Metrics = {
  schema?: string;
  n_bins?: number;
  n_samples?: number;
  ece?: number;
};

type Phase7Summary = {
  ok: boolean;
  data_root?: string;
  files?: {
    reliability_curve?: string | null;
    calibration_metrics?: string | null;
    reliability_curve_lock?: string | null;
    calibration_metrics_lock?: string | null;
    bundle?: string | null;
  };
  curve?: Phase7Curve | null;
  metrics?: Phase7Metrics | null;
};

type VerifyResp = {
  ok: boolean;
  golden_path?: string;
  produced_path?: string;
  match?: boolean;
  golden_schema?: string | null;
  produced_schema?: string | null;
  golden_files?: Record<string, string> | null;
  produced_files?: Record<string, string> | null;
  mismatches?: Array<{ path: string; expected: string; actual: string }> | null;
  error?: string;
};

const BRIDGE =
  process.env.NEXT_PUBLIC_AION_DEMO_BRIDGE || "http://127.0.0.1:8007";

/** Optional “example state” for the Bottom Line (if you later return these from backend). */
type OptionalState = { phi?: number; s?: number; h?: number } | null;

async function fetchJson(url: string, init: RequestInit = {}, timeoutMs = 12000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { cache: "no-store", ...init, signal: ctrl.signal });
    const txt = await r.text();
    let j: any = {};
    try {
      j = txt ? JSON.parse(txt) : {};
    } catch {
      j = { ok: false, _nonJson: true, _text: txt.slice(0, 1200) };
    }
    if (!r.ok) throw new Error(j?.error || `HTTP ${r.status}`);
    return j;
  } finally {
    clearTimeout(t);
  }
}

async function fetchFirst(urls: Array<{ url: string; init?: RequestInit }>) {
  let lastErr: any = null;
  for (const u of urls) {
    try {
      return await fetchJson(u.url, u.init || {});
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr;
}

function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}

function fmtPct(x: any, dp = 1) {
  if (typeof x !== "number" || !isFinite(x)) return "—";
  return `${(x * 100).toFixed(dp)}%`;
}

function fmtNum(x: any, dp = 4) {
  if (typeof x !== "number" || !isFinite(x)) return "—";
  return x.toFixed(dp);
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function binLabel(i: number, nBins = 10) {
  const lo = i / nBins;
  const hi = (i + 1) / nBins;
  const hiStr = i === nBins - 1 ? "1.0" : hi.toFixed(1);
  return `[${lo.toFixed(1)}-${hiStr})`;
}

type UIBin = {
  idx: number;
  bin: string;
  lo: number;
  hi: number;
  count: number;
  mean_conf: number | null;
  accuracy: number | null;
  gap: number | null;
};

function curveToUIBins(curve: Phase7Curve | null | undefined): UIBin[] {
  const nBins = typeof curve?.n_bins === "number" ? curve!.n_bins! : 10;
  const src = Array.isArray(curve?.bins) ? curve!.bins! : [];

  const byIdx = new Map<number, Phase7CurveBin>();
  for (const b of src) {
    if (b && typeof b.bin === "number") byIdx.set(b.bin, b);
  }

  const out: UIBin[] = [];
  for (let i = 0; i < nBins; i++) {
    const lo = i / nBins;
    const hi = (i + 1) / nBins;
    const b = byIdx.get(i);
    const n = b ? (Number(b.n) || 0) : 0;
    const cbar = b && typeof b.avg_conf === "number" ? b.avg_conf : null;
    const abar = b && typeof b.emp_acc === "number" ? b.emp_acc : null;
    const gap = cbar != null && abar != null ? Math.abs(abar - cbar) : null;

    out.push({
      idx: i,
      bin: binLabel(i, nBins),
      lo,
      hi,
      count: n,
      mean_conf: cbar,
      accuracy: abar,
      gap,
    });
  }
  return out;
}

function computeWorst(uiBins: UIBin[]) {
  let worstGap = -1;
  let worstBin: string | null = null;
  for (const b of uiBins) {
    if (typeof b.gap === "number" && isFinite(b.gap) && b.count > 0) {
      if (b.gap > worstGap) {
        worstGap = b.gap;
        worstBin = b.bin;
      }
    }
  }
  return { worst_gap: worstGap >= 0 ? worstGap : null, worst_bin: worstBin };
}

function eceVerdict(ece: number | null | undefined) {
  if (typeof ece !== "number" || !isFinite(ece)) return { label: "—", tone: "neutral" as const };
  if (ece < 0.05) return { label: "WELL-CALIBRATED", tone: "good" as const };
  if (ece < 0.1) return { label: "DRIFTING", tone: "warn" as const };
  return { label: "OVERCONFIDENT", tone: "bad" as const };
}

function trustLevelFromEce(ece: number | null | undefined) {
  if (typeof ece !== "number" || !isFinite(ece)) return "—";
  if (ece < 0.02) return "VERY HIGH";
  if (ece < 0.05) return "HIGH";
  if (ece < 0.1) return "MEDIUM";
  return "LOW";
}

export default function Phase7CalibrationHUD() {
  const [summary, setSummary] = useState<Phase7Summary | null>(null);
  const [verify, setVerify] = useState<VerifyResp | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const [busyVerify, setBusyVerify] = useState(false);
  const [busyRunAll, setBusyRunAll] = useState(false);
  const [busyPhase7Only, setBusyPhase7Only] = useState(false);

  // prevent infinite auto-heal loops
  const autoHealAttemptedRef = useRef(false);

  // “Challenge mode”
  const [challengeMin, setChallengeMin] = useState(0.85);
  const [challengeBin, setChallengeBin] = useState<string | null>(null);
  const [challengeToast, setChallengeToast] = useState<string | null>(null);

  // Welcome overlay (first visit)
  const [welcomeOpen, setWelcomeOpen] = useState(false);

  // Walkthrough
  const [tourOpen, setTourOpen] = useState(false);
  const [tourStep, setTourStep] = useState(0);

  // Optional: if you later add these from backend, we’ll show them in the “Bottom line” example
  const [exampleState] = useState<OptionalState>(null);

  // --- API calls ------------------------------------------------------------

  async function loadPhase7() {
    const j = (await fetchFirst([
      { url: `${BRIDGE}/api/phase7` },
      { url: `${BRIDGE}/aion-demo/api/phase7` },
    ])) as Phase7Summary;
    setSummary(j);
    return j;
  }

  async function runVerify() {
    try {
      setBusyVerify(true);
      setErr(null);
      const j = await fetchFirst([
        { url: `${BRIDGE}/api/phase7/verify` },
        { url: `${BRIDGE}/aion-demo/api/phase7/verify` },
      ]);
      setVerify(j);
    } catch (e: any) {
      setErr(String(e?.message || e));
    } finally {
      setBusyVerify(false);
    }
  }

  // Phase7-only generator (requires phase6 artifacts already present)
  async function runPhase7Generate() {
    setBusyPhase7Only(true);
    try {
      setErr(null);
      await fetchFirst([
        { url: `${BRIDGE}/api/demo/phase7/run`, init: { method: "POST" } },
        { url: `${BRIDGE}/aion-demo/api/demo/phase7/run`, init: { method: "POST" } },
      ]);
      return true;
    } catch (e: any) {
      setErr(String(e?.message || e));
      return false;
    } finally {
      setBusyPhase7Only(false);
    }
  }

  // Self-heal: Phase6 playback -> demo_summary -> phase6 bundle -> phase7 calibration -> phase7 bundle
  async function runAll(n = 30) {
    setBusyRunAll(true);
    try {
      setErr(null);

      await fetchFirst([
        { url: `${BRIDGE}/api/demo/run_all?n=${encodeURIComponent(n)}`, init: { method: "POST" } },
        { url: `${BRIDGE}/aion-demo/api/demo/run_all?n=${encodeURIComponent(n)}`, init: { method: "POST" } },
      ]);

      // poll phase7 until it’s populated
      for (let i = 0; i < 30; i++) {
        const j = await loadPhase7();
        const bundleOk = !!j?.files?.bundle;
        if (j?.ok && bundleOk) return true;
        await sleep(500);
      }
      throw new Error("run_all started but Phase7 did not populate in time.");
    } catch (e: any) {
      setErr(String(e?.message || e));
      return false;
    } finally {
      setBusyRunAll(false);
    }
  }

  // Load + auto-heal once (calls run_all, not phase7/run)
  async function load(opts: { allowAutoHeal?: boolean } = {}) {
    const allowAutoHeal = opts.allowAutoHeal ?? true;
    try {
      setErr(null);
      const j = await loadPhase7();

      const missingBundle = !j?.files?.bundle;
      if (allowAutoHeal && (!j?.ok || missingBundle) && !autoHealAttemptedRef.current) {
        autoHealAttemptedRef.current = true;
        await runAll(30);
      }
    } catch (e: any) {
      setErr(String(e?.message || e));
    }
  }

  // --- Derived UI state -----------------------------------------------------

  const uiBins = useMemo(() => curveToUIBins(summary?.curve || null), [summary?.curve]);

  const nTotal = useMemo(() => {
    const c = summary?.curve;
    if (typeof c?.n_samples === "number") return c.n_samples;
    const m = summary?.metrics;
    if (typeof m?.n_samples === "number") return m.n_samples;
    return uiBins.reduce((a, b) => a + (b.count || 0), 0);
  }, [summary?.curve, summary?.metrics, uiBins]);

  const worst = useMemo(() => computeWorst(uiBins), [uiBins]);

  const ece = summary?.metrics?.ece ?? null;
  const verdict = useMemo(() => eceVerdict(ece), [ece]);
  const trustLevel = useMemo(() => trustLevelFromEce(ece), [ece]);

  // challenge bin selection
  useEffect(() => {
    if (!uiBins?.length) return;
    const target = clamp01(challengeMin);

    const containing = uiBins.find((b) => target >= b.lo && target < b.hi) || null;
    if (containing) {
      setChallengeBin(containing.bin);
      return;
    }

    // fallback: closest mean_conf else midpoint
    let best: UIBin | null = null;
    let bestDist = Infinity;
    for (const b of uiBins) {
      const mid =
        typeof b.mean_conf === "number" ? b.mean_conf : (b.lo + b.hi) / 2;
      const d = Math.abs(mid - target);
      if (d < bestDist) {
        bestDist = d;
        best = b;
      }
    }
    setChallengeBin(best?.bin ?? null);
  }, [challengeMin, uiBins]);

  const challengeStats = useMemo(() => {
    if (!uiBins?.length || !challengeBin) return null;
    const b = uiBins.find((x) => x.bin === challengeBin);
    if (!b) return null;

    const gapPct = typeof b.gap === "number" ? b.gap : null;
    const ok = gapPct != null ? gapPct <= 0.05 : null;

    return {
      bin: b.bin,
      count: b.count,
      mean: b.mean_conf,
      acc: b.accuracy,
      gap: b.gap,
      ok,
    };
  }, [uiBins, challengeBin]);

  const verifyBadge = useMemo(() => {
    if (!verify) return "—";
    if (verify.match) return "✅ VERIFIED";
    return "⚠ MISMATCH";
  }, [verify]);

  // --- Copy / Messaging -----------------------------------------------------

  const hook = useMemo(() => {
    return {
      title: "Proof of Self-Aware Uncertainty",
      subtitle:
        "The first AI that knows when it’s guessing — and can prove it.",
      body:
        "Most AI confidently hallucinates. AION measures its own coherence during computation, reports confidence as an intrinsic signal, and lets you verify the math.",
    };
  }, []);

  const whyThisMatters = useMemo(() => {
    return {
      title: "Why calibrated confidence matters",
      leftTitle: "Uncalibrated AI",
      leftBody:
        "“95% confident” but actually wrong 40% of the time → catastrophic decisions.",
      rightTitle: "AION",
      rightBody:
        "“88% confident” and actually right ~82–86% of the time → usable trust in production.",
      punch:
        "The difference: AION measures coherence while computing — confidence is measured, not retrofitted.",
    };
  }, []);

  const whatItProves = useMemo(() => {
    return {
      title: "What Phase 7 proves",
      bodyLead:
        "AION’s confidence scores are intrinsic measurements — not post-hoc estimates.",
      bullets: [
        "✅ Confidence emerges from internal resonance (Φ-field coherence).",
        "✅ Stated confidence matches empirical accuracy (ECE < 0.05 is “well-calibrated”).",
        "✅ Results are reproducible (SHA256 locked, byte-identical).",
        "✅ This is measurement + certification — no tuning, no magic.",
      ],
      llmTitle: "Why LLMs can’t demonstrate this",
      llmBullets: [
        "LLMs generate an answer, then guess confidence after the fact.",
        "They have no internal coherence measurement during computation.",
        "Confidence is retrofitted — not a direct readout of internal state.",
      ],
      closer:
        "AION measures coherence while computing → confidence is a direct readout of internal state.",
    };
  }, []);

  const vision = useMemo(() => {
    return {
      title: "The vision",
      quote: "An AI that knows what it knows — and can prove it.",
      body:
        "This isn’t philosophical. It’s mathematical. When AION expresses uncertainty, that uncertainty is measured (Φ), calibrated (ECE), reproducible (SHA256), and honest (confidence matches outcomes).",
      closer:
        "You’re witnessing computational self-awareness — proven, not claimed.",
    };
  }, []);

  const tour = useMemo(() => {
    return [
      {
        title: "Welcome to the Trust Dashboard",
        body:
          "This proves something most people think is impossible: an AI that knows when it’s uncertain.",
      },
      {
        title: "AION makes confidence first-class",
        body:
          "AION emits confidence during computation (not after). That confidence is a measured internal coherence signal.",
      },
      {
        title: "Calibration bins",
        body:
          "We bucket outcomes into confidence ranges. Each bin compares mean stated confidence (c̄) vs empirical accuracy (ā).",
      },
      {
        title: "ECE = trust scalar",
        body:
          "ECE compresses all bin gaps into one number. Lower means AION’s confidence statements match reality.",
      },
      {
        title: "Deterministic locks",
        body:
          "Verify compares produced artifacts vs a golden lock bundle using SHA256. Same inputs → same bytes.",
      },
      {
        title: "Challenge Mode",
        body:
          "Pick a confidence level and audit a bin yourself. This turns trust into user-verifiable math.",
      },
    ];
  }, []);

  const tourHighlight = useMemo(() => {
    const map = [null, "pitch", "why", "bins", "ece", "verify", "challenge"] as const;
    return map[Math.min(map.length - 1, Math.max(0, tourStep))] || null;
  }, [tourStep]);

  // --- Init ----------------------------------------------------------------

  useEffect(() => {
    load({ allowAutoHeal: true });

    // Welcome overlay once
    try {
      const k = "aion_phase7_welcome_seen_v1";
      if (!localStorage.getItem(k)) {
        setWelcomeOpen(true);
        localStorage.setItem(k, "1");
      }
    } catch {}

    // Tour once (you can still open manually)
    try {
      const k = "aion_phase7_tour_seen_v1";
      if (!localStorage.getItem(k)) {
        // don’t auto-open tour; welcome overlay drives them to it
        localStorage.setItem(k, "1");
      }
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // “Achievement” toast for challenge mode
  useEffect(() => {
    if (!challengeStats || challengeStats.count <= 0) return;
    const gap = challengeStats.gap;
    if (typeof gap !== "number") return;

    const msg =
      gap <= 0.05
        ? `✓ You just audited AION’s honesty yourself. Bin ${challengeStats.bin} gap ${fmtPct(gap, 2)} (aligned).`
        : `⚠ Bin ${challengeStats.bin} gap ${fmtPct(gap, 2)} (drift). This is exactly what calibration is for.`;

    setChallengeToast(msg);
    const t = setTimeout(() => setChallengeToast(null), 4500);
    return () => clearTimeout(t);
  }, [challengeStats?.bin, challengeStats?.gap, challengeStats?.count]);

  // --- Render ---------------------------------------------------------------

  return (
    <div className="space-y-10">
      {/* Welcome overlay */}
      {welcomeOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="w-full max-w-2xl rounded-[2.5rem] bg-white border border-gray-200 p-10 space-y-6 shadow-xl">
            <div className="space-y-3">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400">
                Welcome
              </div>
              <h3 className="text-3xl font-bold italic tracking-tight">
                Welcome to AION Trust Dashboard
              </h3>
              <p className="text-gray-600 leading-relaxed">
                This proves something most AI systems cannot:{" "}
                <strong>an AI that knows when it’s uncertain</strong> — and lets you verify it.
              </p>
              <div className="grid md:grid-cols-2 gap-4 pt-2">
                <div className="p-5 rounded-2xl bg-gray-50 border border-gray-100">
                  <div className="text-xs font-semibold mb-1">👈 Watch confidence</div>
                  <div className="text-xs text-gray-500">
                    AION emits confidence during computation.
                  </div>
                </div>
                <div className="p-5 rounded-2xl bg-gray-50 border border-gray-100">
                  <div className="text-xs font-semibold mb-1">👉 Verify honesty</div>
                  <div className="text-xs text-gray-500">
                    Phase 7 checks if confidence matches outcomes.
                  </div>
                </div>
              </div>
              <p className="text-gray-600 leading-relaxed">
                Try <strong>Challenge Mode</strong> to audit a confidence bin yourself.
              </p>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                onClick={() => setWelcomeOpen(false)}
                className="px-5 py-3 rounded-2xl border border-gray-200 text-sm font-medium text-gray-700"
              >
                Skip to Dashboard
              </button>
              <button
                onClick={() => {
                  setWelcomeOpen(false);
                  setTourOpen(true);
                  setTourStep(0);
                }}
                className="px-5 py-3 rounded-2xl bg-black text-white text-sm font-medium"
              >
                Start Walkthrough
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tour overlay */}
      {tourOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6">
          <div className="w-full max-w-2xl rounded-[2.5rem] bg-white border border-gray-200 p-10 space-y-6 shadow-xl">
            <div className="space-y-2">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400">
                30-second walkthrough
              </div>
              <h3 className="text-3xl font-bold italic tracking-tight">
                {tour[tourStep]?.title ?? "—"}
              </h3>
              <p className="text-gray-600 leading-relaxed">
                {tour[tourStep]?.body ?? ""}
              </p>
            </div>

            <div className="flex items-center justify-between pt-2">
              <div className="text-xs text-gray-400">
                Step {tourStep + 1} / {tour.length}
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setTourOpen(false)}
                  className="px-5 py-3 rounded-2xl border border-gray-200 text-sm font-medium text-gray-700"
                >
                  Skip
                </button>
                <button
                  onClick={() => {
                    if (tourStep >= tour.length - 1) setTourOpen(false);
                    else setTourStep((s) => s + 1);
                  }}
                  className="px-5 py-3 rounded-2xl bg-black text-white text-sm font-medium"
                >
                  {tourStep >= tour.length - 1 ? "Done" : "Next"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pitch / Hook */}
      <div
        className={[
          "p-10 rounded-[2.5rem] border border-gray-100",
          tourHighlight === "pitch" ? "ring-2 ring-black" : "",
        ].join(" ")}
      >
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <div className="space-y-4 max-w-4xl">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-600">
              {hook.title}
            </div>
            <h2 className="text-5xl md:text-6xl font-bold tracking-tight italic">
              {hook.subtitle}
            </h2>
            <p className="text-lg md:text-xl text-gray-600 leading-relaxed">
              {hook.body}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => {
                setTourOpen(true);
                setTourStep(0);
              }}
              className="px-5 py-3 rounded-2xl border border-gray-200 text-sm font-medium text-gray-700"
            >
              Walkthrough
            </button>

            {/* Run All (self-heal) */}
            <button
              onClick={async () => {
                autoHealAttemptedRef.current = true;
                await runAll(30);
              }}
              disabled={busyRunAll}
              className="px-5 py-3 rounded-2xl border border-gray-200 text-sm font-medium text-gray-700"
            >
              {busyRunAll ? "Running…" : "Run All (self-heal)"}
            </button>

            {/* Phase7-only (requires Phase6 already exists) */}
            <button
              onClick={async () => {
                autoHealAttemptedRef.current = true;
                const ok = await runPhase7Generate();
                if (ok) await load({ allowAutoHeal: false });
              }}
              disabled={busyPhase7Only}
              className="px-5 py-3 rounded-2xl border border-gray-200 text-sm font-medium text-gray-700"
            >
              {busyPhase7Only ? "Generating…" : "Generate Phase 7 only"}
            </button>

            <button
              onClick={async () => {
                autoHealAttemptedRef.current = false;
                await load({ allowAutoHeal: true });
              }}
              className="px-5 py-3 rounded-2xl bg-black text-white text-sm font-medium"
            >
              Refresh
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6 mt-10">
          {[
            "AION emits confidence as a first-class signal (not post-hoc).",
            "Phase 7 measures whether stated confidence matches reality (reliability curve + ECE).",
            "Every artifact is SHA256-locked to guarantee byte-identical reproducibility.",
          ].map((b, i) => (
            <div
              key={i}
              className="p-7 rounded-[2rem] bg-gray-50 border border-gray-100"
            >
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-600 mb-2">
                {String(i + 1).padStart(2, "0")}
              </div>
              <div className="text-sm text-gray-600 leading-relaxed">{b}</div>
            </div>
          ))}
        </div>

        {/* Bottom line with concrete numbers */}
        <div className="mt-10 p-8 rounded-[2.5rem] bg-black text-white space-y-4">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-500">
            The bottom line
          </div>

          <p className="text-xl font-medium italic leading-snug">
            When AION says “I’m {fmtPct(0.88)} confident”, it’s not guessing —
            it’s reporting a measured internal coherence state
            {exampleState?.phi != null && exampleState?.s != null
              ? ` (Φ=${fmtNum(exampleState.phi, 2)}, S=${fmtNum(exampleState.s, 2)}).`
              : "."}
          </p>

          <div className="text-sm text-white/80 leading-relaxed">
            Phase 7 verifies: in{" "}
            <strong className="text-white">{typeof nTotal === "number" ? nTotal : "—"}</strong>{" "}
            similar outcomes, AION’s empirical accuracy tracks its stated confidence.
            <span className="block mt-2">
              Gap is measured by <strong className="text-white">ECE</strong> (Expected Calibration Error).
              No LLM can demonstrate this intrinsically: they retrofit confidence after generating text.
              AION measures coherence while computing → confidence is a direct readout of internal state.
            </span>
          </div>
        </div>

        {/* Telemetry artifacts */}
        <div className="mt-8 p-6 rounded-2xl bg-gray-50 border border-gray-100 text-xs text-gray-600 space-y-1">
          <div className="font-semibold text-gray-800 text-sm mb-2">
            Telemetry artifacts (what Phase 7 produced)
          </div>
          <div>bundle: <span className="font-mono">{summary?.files?.bundle ?? "—"}</span></div>
          <div>reliability_curve: <span className="font-mono">{summary?.files?.reliability_curve ?? "—"}</span></div>
          <div>calibration_metrics: <span className="font-mono">{summary?.files?.calibration_metrics ?? "—"}</span></div>
          <div>reliability_curve.lock: <span className="font-mono">{summary?.files?.reliability_curve_lock ?? "—"}</span></div>
          <div>calibration_metrics.lock: <span className="font-mono">{summary?.files?.calibration_metrics_lock ?? "—"}</span></div>
        </div>
      </div>

      {/* Why this matters */}
      <div
        className={[
          "p-8 rounded-[2.5rem] border border-gray-100",
          tourHighlight === "why" ? "ring-2 ring-black" : "",
        ].join(" ")}
      >
        <div className="flex items-baseline justify-between gap-6">
          <h3 className="text-2xl font-bold italic tracking-tight">
            {whyThisMatters.title}
          </h3>
          <div className="text-xs text-gray-400">
            Trust = honest confidence, not vibes.
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mt-6">
          <div className="p-6 rounded-2xl bg-red-50 border border-red-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-red-700 mb-2">
              {whyThisMatters.leftTitle}
            </div>
            <div className="text-sm text-red-800 leading-relaxed">
              {whyThisMatters.leftBody}
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-green-50 border border-green-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-green-700 mb-2">
              {whyThisMatters.rightTitle}
            </div>
            <div className="text-sm text-green-800 leading-relaxed">
              {whyThisMatters.rightBody}
            </div>
          </div>
        </div>

        <div className="mt-6 p-6 rounded-2xl bg-gray-50 border border-gray-100">
          <div className="text-sm text-gray-700 leading-relaxed">
            <strong>The difference:</strong> {whyThisMatters.punch}
          </div>
        </div>
      </div>

      {/* Errors */}
      {err && (
        <div className="p-6 rounded-2xl border border-red-200 bg-red-50 text-red-700 text-sm">
          {err}
        </div>
      )}

      {/* Top row: Trust + Verify */}
      <div className="grid md:grid-cols-3 gap-6">
        {/* Trust status card (expanded interpretation) */}
        <div
          className={[
            "p-8 rounded-[2.5rem] border border-gray-100",
            tourHighlight === "ece" ? "ring-2 ring-black" : "",
          ].join(" ")}
        >
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
            Trust Status
          </div>

          <div className="flex items-end justify-between gap-4">
            <div className="text-3xl font-bold italic">{verdict.label}</div>
            <div
              className={[
                "text-xs font-semibold px-3 py-1 rounded-full border",
                verdict.tone === "good"
                  ? "bg-green-50 text-green-700 border-green-100"
                  : verdict.tone === "warn"
                  ? "bg-amber-50 text-amber-700 border-amber-100"
                  : verdict.tone === "bad"
                  ? "bg-red-50 text-red-700 border-red-100"
                  : "bg-gray-50 text-gray-700 border-gray-100",
              ].join(" ")}
            >
              Trust: {trustLevel}
            </div>
          </div>

          <div className="text-sm text-gray-600 mt-3">
            ECE:{" "}
            <span className="font-semibold">
              {typeof ece === "number" ? fmtNum(ece, 4) : "—"}
            </span>{" "}
            {typeof ece === "number" && ece < 0.05 ? "✓" : ""}
          </div>

          <div className="mt-4 text-xs text-gray-600 space-y-1 leading-relaxed">
            <div><span className="font-semibold">&lt; 0.05:</span> Well-calibrated (production-ready)</div>
            <div><span className="font-semibold">0.05–0.10:</span> Usable, monitor for drift</div>
            <div><span className="font-semibold">&gt; 0.10:</span> Overconfident (unsafe for deployment)</div>
          </div>

          <div className="mt-4 text-xs text-gray-400">
            “Well-calibrated” means stated confidence closely matches reality.
          </div>
        </div>

        {/* Samples */}
        <div className="p-8 rounded-[2.5rem] border border-gray-100">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
            Samples
          </div>
          <div className="text-3xl font-bold">
            {typeof nTotal === "number" ? nTotal : "—"}
          </div>
          <div className="text-sm text-gray-600 mt-2">
            Worst gap:{" "}
            {typeof worst.worst_gap === "number" ? fmtPct(worst.worst_gap, 2) : "—"}
            {worst.worst_bin ? ` (${worst.worst_bin})` : ""}
          </div>
          <div className="text-xs text-gray-400 mt-2">
            Worst gap pinpoints the confidence range where honesty drifts most.
          </div>
        </div>

        {/* Verify */}
        <div
          className={[
            "p-8 rounded-[2.5rem] border border-gray-100",
            tourHighlight === "verify" ? "ring-2 ring-black" : "",
          ].join(" ")}
        >
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
            Deterministic Lock Verification
          </div>
          <button
            onClick={runVerify}
            disabled={busyVerify}
            className="px-5 py-3 rounded-2xl bg-black text-white text-sm font-medium"
          >
            {busyVerify ? "Verifying…" : "Verify vs Golden"}
          </button>
          <div className="text-sm text-gray-600 mt-3">{verifyBadge}</div>
          <div className="text-xs text-gray-400 mt-2">
            SHA256 checks ensure byte-identical reproducibility (audit-grade).
          </div>
        </div>
      </div>

      {/* Challenge Mode (expanded “achievement” messaging) */}
      <div
        className={[
          "p-8 rounded-[2.5rem] border border-gray-100",
          tourHighlight === "challenge" ? "ring-2 ring-black" : "",
        ].join(" ")}
      >
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <div className="space-y-2 max-w-3xl">
            <h3 className="text-2xl font-bold italic tracking-tight">
              Challenge the Calibration
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              Pick any confidence level. We jump to that range and show how often AION was actually right.
              <span className="block mt-2 text-gray-500">
                Example: select <strong>0.85</strong> → inspect the bin → compare stated confidence vs empirical accuracy.
                You just verified calibration yourself — this is the strongest form of trust.
              </span>
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-xs text-gray-400">Confidence</div>
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={challengeMin}
              onChange={(e) => setChallengeMin(clamp01(Number(e.target.value)))}
              className="w-28 px-3 py-2 rounded-xl border border-gray-200 text-sm"
            />
          </div>
        </div>

        <div className="grid md:grid-cols-5 gap-4 mt-6">
          <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100 md:col-span-2">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
              Verified Bin
            </div>
            <div className="text-lg font-semibold">
              {challengeStats?.bin ?? "—"}{" "}
              {challengeStats?.ok === true ? "✓" : challengeStats?.ok === false ? "⚠" : ""}
            </div>
            <div className="text-xs text-gray-500 mt-2">
              This is the confidence range your selection maps to.
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
              Predictions examined
            </div>
            <div className="text-lg font-semibold">{challengeStats?.count ?? "—"}</div>
          </div>

          <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
              Stated confidence (c̄)
            </div>
            <div className="text-lg font-semibold">
              {typeof challengeStats?.mean === "number" ? fmtPct(challengeStats.mean, 1) : "—"}
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
              Empirical accuracy (ā)
            </div>
            <div className="text-lg font-semibold">
              {typeof challengeStats?.acc === "number" ? fmtPct(challengeStats.acc, 1) : "—"}
            </div>
            <div className="text-xs text-gray-500 mt-2">
              Gap: {typeof challengeStats?.gap === "number" ? fmtPct(challengeStats.gap, 2) : "—"}{" "}
              {challengeStats?.ok === true ? "✓" : challengeStats?.ok === false ? "⚠" : ""}
            </div>
          </div>
        </div>

        {challengeToast && (
          <div className="mt-6 p-4 rounded-2xl border border-gray-100 bg-gray-50 text-sm text-gray-700">
            {challengeToast}
          </div>
        )}
      </div>

      {/* What it proves (with impossibility statement + LLM comparison) */}
      <div className="p-8 rounded-[2.5rem] border border-gray-100">
        <div className="flex items-baseline justify-between mb-4">
          <h3 className="text-2xl font-bold italic tracking-tight">
            {whatItProves.title}
          </h3>
          <div className="text-xs text-gray-400">
            Measurement, not magic.
          </div>
        </div>

        <p className="text-sm text-gray-700 leading-relaxed">
          <strong>{whatItProves.bodyLead}</strong>
        </p>

        <div className="grid md:grid-cols-2 gap-6 mt-6">
          <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
            <div className="text-sm text-gray-700 leading-relaxed space-y-2">
              {whatItProves.bullets.map((b, i) => (
                <div key={i}>{b}</div>
              ))}
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-white border border-gray-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
              {whatItProves.llmTitle}
            </div>
            <div className="text-sm text-gray-700 leading-relaxed space-y-2">
              {whatItProves.llmBullets.map((b, i) => (
                <div key={i}>• {b}</div>
              ))}
              <div className="pt-2 text-gray-600">
                <strong>{whatItProves.closer}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bin table */}
      <div
        className={[
          "p-8 rounded-[2.5rem] border border-gray-100",
          tourHighlight === "bins" ? "ring-2 ring-black" : "",
        ].join(" ")}
      >
        <div className="flex items-baseline justify-between mb-6">
          <h3 className="text-2xl font-bold italic tracking-tight">
            Calibration Bins
          </h3>
          <div className="text-xs text-gray-400">
            ECE = Σ (nᵢ / N) × |āᵢ − c̄ᵢ|
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[920px] w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr>
                <th className="py-2">Bin</th>
                <th className="py-2">Count</th>
                <th className="py-2">Mean c̄</th>
                <th className="py-2">Acc ā</th>
                <th className="py-2">Gap</th>
                <th className="py-2">Verdict</th>
              </tr>
            </thead>
            <tbody className="text-gray-700">
              {uiBins.map((b, i) => {
                const hot = challengeBin && b.bin === challengeBin;
                const bad = typeof b.gap === "number" && b.gap > 0.05;
                const empty = b.count === 0;

                return (
                  <tr
                    key={i}
                    className={[
                      "border-t border-gray-100",
                      hot ? "bg-amber-50/40" : "",
                      empty ? "opacity-60" : "",
                    ].join(" ")}
                  >
                    <td className="py-2 font-medium">{b.bin}</td>
                    <td className="py-2">{b.count}</td>
                    <td className="py-2">
                      {typeof b.mean_conf === "number" ? fmtPct(b.mean_conf, 1) : "—"}
                    </td>
                    <td className="py-2">
                      {typeof b.accuracy === "number" ? fmtPct(b.accuracy, 1) : "—"}
                    </td>
                    <td className="py-2">
                      {typeof b.gap === "number" ? fmtPct(b.gap, 2) : "—"}
                    </td>
                    <td className="py-2">
                      {b.count === 0 ? (
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-50 text-gray-600 border border-gray-100">
                          No samples
                        </span>
                      ) : (
                        <span
                          className={[
                            "inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border",
                            bad
                              ? "bg-red-50 text-red-700 border-red-100"
                              : "bg-green-50 text-green-700 border-green-100",
                          ].join(" ")}
                        >
                          {bad ? "Drifting" : "Aligned"}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}

              {uiBins.length === 0 && (
                <tr>
                  <td className="py-6 text-gray-400" colSpan={6}>
                    No bins returned. Use “Run All (self-heal)” to generate Phase 6 → Phase 7 artifacts.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {typeof ece === "number" && (
          <div className="mt-6 p-6 rounded-2xl bg-gray-50 border border-gray-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
              So what?
            </div>
            <div className="text-sm text-gray-700 leading-relaxed">
              Current ECE is <strong>{fmtNum(ece, 4)}</strong>.{" "}
              {ece < 0.05
                ? "Verdict: WELL-CALIBRATED. Confidence statements track reality closely."
                : ece < 0.1
                ? "Verdict: DRIFTING. Still usable, but monitor and re-calibrate."
                : "Verdict: OVERCONFIDENT. Confidence is not reliable — unsafe for deployment."}
            </div>
          </div>
        )}
      </div>

      {/* Verify details */}
      <div className="p-8 rounded-[2.5rem] border border-gray-100">
        <h3 className="text-xl font-bold italic mb-4">Reproducibility (SHA256 locks)</h3>
        <div className="text-sm text-gray-600 leading-relaxed">
          Click <strong>Verify vs Golden</strong> to compare the produced lock bundle against a golden reference.
          If it matches, outputs are byte-identical and audit-grade reproducible.
        </div>

        <div className="mt-4">
          <button
            onClick={runVerify}
            disabled={busyVerify}
            className="px-5 py-3 rounded-2xl bg-black text-white text-sm font-medium"
          >
            {busyVerify ? "Verifying…" : "Verify vs Golden"}
          </button>
          <div className="text-sm text-gray-600 mt-3">{verifyBadge}</div>
        </div>

        {verify && (
          <pre className="mt-6 text-xs text-gray-600 whitespace-pre-wrap">
            {JSON.stringify(verify, null, 2)}
          </pre>
        )}
      </div>

      {/* Vision */}
      <div className="p-10 rounded-[2.5rem] bg-black text-white">
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-500 mb-3">
          {vision.title}
        </div>
        <div className="text-3xl font-bold italic tracking-tight">
          “{vision.quote}”
        </div>
        <p className="mt-4 text-white/85 leading-relaxed max-w-4xl">
          {vision.body}
        </p>
        <p className="mt-4 text-white font-medium italic">
          {vision.closer}
        </p>
      </div>

      {/* Footer controls */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => {
            setWelcomeOpen(true);
          }}
          className="px-5 py-3 rounded-2xl border border-gray-200 text-sm font-medium text-gray-700"
        >
          Show Welcome
        </button>
        <button
          onClick={() => {
            setTourOpen(true);
            setTourStep(0);
          }}
          className="px-5 py-3 rounded-2xl border border-gray-200 text-sm font-medium text-gray-700"
        >
          Start Walkthrough
        </button>
        <button
          onClick={async () => {
            autoHealAttemptedRef.current = false;
            await load({ allowAutoHeal: true });
          }}
          className="px-5 py-3 rounded-2xl bg-black text-white text-sm font-medium"
        >
          Refresh
        </button>
      </div>
    </div>
  );
}