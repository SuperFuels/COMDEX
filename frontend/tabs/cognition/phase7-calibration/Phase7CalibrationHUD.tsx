"use client";

import React, { useEffect, useMemo, useState } from "react";

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
  metrics?: {
    ece?: number;
    n_total?: number;
    worst_gap?: number;
    worst_bin?: string;
    bins?: Array<{
      bin: string; // e.g. "[0.8-0.9)"
      lo?: number;
      hi?: number;
      count: number;
      mean_conf: number;
      accuracy: number;
      gap: number;
    }>;
    // Optional (if backend adds later)
    events_total?: number;
  };
  curve?: any;
  // Optional (if backend adds later)
  events?: Array<{
    id?: string | number;
    ts?: string | number;
    session?: string;
    goal?: string;
    confidence?: number;
    predicted?: Record<string, any>;
    actual?: Record<string, any>;
    pass?: boolean;
    bin?: string;
  }>;
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

async function fetchJson(url: string) {
  const r = await fetch(url, { cache: "no-store" });
  const t = await r.text();
  let j: any = {};
  try {
    j = t ? JSON.parse(t) : {};
  } catch {
    j = { ok: false, _nonJson: true, _text: t.slice(0, 800) };
  }
  if (!r.ok) throw new Error(j?.error || `HTTP ${r.status}`);
  return j;
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

export default function Phase7CalibrationHUD() {
  const [summary, setSummary] = useState<Phase7Summary | null>(null);
  const [verify, setVerify] = useState<VerifyResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busyVerify, setBusyVerify] = useState(false);

  // “Challenge mode”
  const [challengeMin, setChallengeMin] = useState(0.85);
  const [challengeBin, setChallengeBin] = useState<string | null>(null);

  // “First time” tour
  const [tourOpen, setTourOpen] = useState(false);
  const [tourStep, setTourStep] = useState(0);

  async function load() {
    try {
      setErr(null);
      const j = await fetchJson(`${BRIDGE}/api/phase7`);
      setSummary(j);
    } catch (e: any) {
      setErr(String(e?.message || e));
    }
  }

  async function runVerify() {
    try {
      setBusyVerify(true);
      setErr(null);
      const j = await fetchJson(`${BRIDGE}/api/phase7/verify`);
      setVerify(j);
    } catch (e: any) {
      setErr(String(e?.message || e));
    } finally {
      setBusyVerify(false);
    }
  }

  useEffect(() => {
    load();
    // show tour once
    try {
      const k = "aion_phase7_tour_seen_v1";
      if (!localStorage.getItem(k)) {
        setTourOpen(true);
        setTourStep(0);
        localStorage.setItem(k, "1");
      }
    } catch {
      // ignore
    }
  }, []);

  const headline = useMemo(() => {
    const ece = summary?.metrics?.ece;
    if (typeof ece !== "number") return "—";
    if (ece < 0.05) return "WELL-CALIBRATED";
    if (ece < 0.10) return "DRIFTING";
    return "OVERCONFIDENT";
  }, [summary]);

  const ece = summary?.metrics?.ece;
  const bins = (summary?.metrics?.bins || []) as NonNullable<
    Phase7Summary["metrics"]
  >["bins"];

  // pick the “challenge bin” from bins using challengeMin
  useEffect(() => {
    if (!bins?.length) return;
    const target = clamp01(challengeMin);
    // Prefer bins that contain target, else nearest by mean_conf
    const containing =
      bins.find((b) => {
        const lo = typeof b.lo === "number" ? b.lo : undefined;
        const hi = typeof b.hi === "number" ? b.hi : undefined;
        if (lo == null || hi == null) return false;
        return target >= lo && target < hi;
      }) || null;

    if (containing) {
      setChallengeBin(containing.bin);
      return;
    }

    // fallback: parse from label "[a-b)"
    const parseLoHi = (s: string) => {
      const m = s.match(/\[?\s*([0-9.]+)\s*-\s*([0-9.]+)\s*\)?/);
      if (!m) return null;
      return { lo: Number(m[1]), hi: Number(m[2]) };
    };

    let best: any = null;
    let bestDist = Infinity;
    for (const b of bins) {
      const lh = parseLoHi(b.bin || "");
      const mid =
        typeof b.mean_conf === "number"
          ? b.mean_conf
          : lh
          ? (lh.lo + lh.hi) / 2
          : null;
      if (typeof mid !== "number") continue;
      const d = Math.abs(mid - target);
      if (d < bestDist) {
        bestDist = d;
        best = b;
      }
    }
    setChallengeBin(best?.bin ?? null);
  }, [challengeMin, bins]);

  const challengeStats = useMemo(() => {
    if (!bins?.length || !challengeBin) return null;
    const b = bins.find((x) => x.bin === challengeBin);
    if (!b) return null;
    return {
      bin: b.bin,
      count: b.count,
      mean: b.mean_conf,
      acc: b.accuracy,
      gap: b.gap,
    };
  }, [bins, challengeBin]);

  const verifyBadge = useMemo(() => {
    if (!verify) return "—";
    if (verify.match) return "✅ VERIFIED";
    return "⚠ MISMATCH";
  }, [verify]);

  const pitch = useMemo(() => {
    return {
      title: "AION Trust Dashboard",
      subtitle: "Proof of self-aware uncertainty (calibrated, auditable, reproducible).",
      bullets: [
        "Left-side forecasting emits confidence as a first-class signal (not post-hoc).",
        "Phase 7 measures whether stated confidence matches reality (reliability curve + ECE).",
        "Every output is SHA256-locked to guarantee byte-identical reproducibility.",
      ],
    };
  }, []);

  const tour = useMemo(() => {
    const steps = [
      {
        title: "What this proves",
        body:
          "This dashboard shows AION stating confidence, then proves—across many events—whether that confidence is honest.",
      },
      {
        title: "AION makes forecasts",
        body:
          "Watch forecasts being issued with confidence (left panel in the full page). Each forecast is later judged pass/miss against thresholds.",
      },
      {
        title: "Calibration math",
        body:
          "Forecasts are bucketed into confidence bins. For each bin we compare mean stated confidence (c̄) vs empirical accuracy (ā).",
      },
      {
        title: "ECE (Expected Calibration Error)",
        body:
          "ECE compresses all bin gaps into one number. Lower is better. This is the trust scalar.",
      },
      {
        title: "Deterministic locks",
        body:
          "Click Verify: outputs are compared against the golden lock bundle using SHA256. Same inputs → same bytes.",
      },
      {
        title: "Challenge mode",
        body:
          "Pick a confidence level (e.g. 0.85). We jump to the bin and show its accuracy. This turns trust into user-verifiable math.",
      },
    ];
    return steps;
  }, []);

  const tourHighlight = useMemo(() => {
    // Minimal: just returns which block to “pulse”
    // 0 intro, 1 pitch, 2 bins, 3 ece, 4 verify, 5 challenge
    const map = [null, "pitch", "bins", "ece", "verify", "challenge"] as const;
    return map[Math.min(map.length - 1, Math.max(0, tourStep))] || null;
  }, [tourStep]);

  return (
    <div className="space-y-10">
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

      {/* Pitch block */}
      <div
        className={[
          "p-10 rounded-[2.5rem] border border-gray-100",
          tourHighlight === "pitch" ? "ring-2 ring-black" : "",
        ].join(" ")}
      >
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <div className="space-y-3">
            <h2 className="text-5xl md:text-6xl font-bold tracking-tight italic">
              {pitch.title}
            </h2>
            <p className="text-xl text-gray-500 font-light tracking-tight max-w-3xl">
              {pitch.subtitle}
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => {
                setTourOpen(true);
                setTourStep(0);
              }}
              className="px-5 py-3 rounded-2xl border border-gray-200 text-sm font-medium text-gray-700"
            >
              Walkthrough
            </button>
            <button
              onClick={load}
              className="px-5 py-3 rounded-2xl bg-black text-white text-sm font-medium"
            >
              Refresh
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6 mt-10">
          {pitch.bullets.map((b, i) => (
            <div key={i} className="p-7 rounded-[2rem] bg-gray-50 border border-gray-100">
              <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-600 mb-2">
                {String(i + 1).padStart(2, "0")}
              </div>
              <div className="text-sm text-gray-600 leading-relaxed">{b}</div>
            </div>
          ))}
        </div>

        <div className="mt-10 p-8 rounded-[2.5rem] bg-black text-white">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">
            The bottom line
          </div>
          <p className="text-xl font-medium italic leading-snug">
            When AION says “I’m {fmtPct(0.88)} confident”, it’s not guessing—it’s reporting a measured internal
            coherence state, and Phase 7 verifies whether that statement is historically true.
          </p>
        </div>
      </div>

      {/* Top row: Trust summary */}
      <div className="grid md:grid-cols-3 gap-6">
        <div
          className={[
            "p-8 rounded-[2.5rem] border border-gray-100",
            tourHighlight === "ece" ? "ring-2 ring-black" : "",
          ].join(" ")}
        >
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
            Trust Status
          </div>
          <div className="text-3xl font-bold italic">{headline}</div>
          <div className="text-sm text-gray-500 mt-2">
            ECE: {fmtNum(ece, 4)}
          </div>
          <div className="text-xs text-gray-400 mt-2">
            Lower is better. &lt; 0.05 is typically “well-calibrated”.
          </div>
        </div>

        <div className="p-8 rounded-[2.5rem] border border-gray-100">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
            Samples
          </div>
          <div className="text-3xl font-bold">
            {summary?.metrics?.n_total ?? "—"}
          </div>
          <div className="text-sm text-gray-500 mt-2">
            Worst gap:{" "}
            {typeof summary?.metrics?.worst_gap === "number"
              ? fmtPct(summary!.metrics!.worst_gap, 2)
              : "—"}
            {summary?.metrics?.worst_bin ? ` (${summary.metrics.worst_bin})` : ""}
          </div>
        </div>

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
          <div className="text-sm text-gray-500 mt-3">{verifyBadge}</div>
          <div className="text-xs text-gray-400 mt-2">
            SHA256 checks ensure byte-identical reproducibility.
          </div>
        </div>
      </div>

      {/* Errors */}
      {err && (
        <div className="p-6 rounded-2xl border border-red-200 bg-red-50 text-red-700 text-sm">
          {err}
        </div>
      )}

      {/* Challenge Mode */}
      <div
        className={[
          "p-8 rounded-[2.5rem] border border-gray-100",
          tourHighlight === "challenge" ? "ring-2 ring-black" : "",
        ].join(" ")}
      >
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <div className="space-y-2">
            <h3 className="text-2xl font-bold italic tracking-tight">
              Challenge Mode
            </h3>
            <p className="text-sm text-gray-500 leading-relaxed max-w-3xl">
              Pick a confidence level. We jump to the matching bin and show its empirical accuracy.
              This is the strongest form of trust: you can verify the calibration yourself.
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

        <div className="grid md:grid-cols-4 gap-4 mt-6">
          <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
              Selected Bin
            </div>
            <div className="text-lg font-semibold">
              {challengeStats?.bin ?? "—"}
            </div>
          </div>
          <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
              Bin Count
            </div>
            <div className="text-lg font-semibold">
              {challengeStats?.count ?? "—"}
            </div>
          </div>
          <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
              Mean c̄
            </div>
            <div className="text-lg font-semibold">
              {typeof challengeStats?.mean === "number"
                ? fmtPct(challengeStats.mean, 1)
                : "—"}
            </div>
          </div>
          <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
              Accuracy ā
            </div>
            <div className="text-lg font-semibold">
              {typeof challengeStats?.acc === "number"
                ? fmtPct(challengeStats.acc, 1)
                : "—"}
              {typeof challengeStats?.gap === "number" &&
                (challengeStats.gap > 0.05 ? " ⚠" : " ✓")}
            </div>
          </div>
        </div>

        {/* Optional: event drill-down (if backend later provides events) */}
        {Array.isArray(summary?.events) && summary!.events!.length > 0 && (
          <div className="mt-8 p-6 rounded-2xl border border-gray-100">
            <div className="text-sm font-semibold mb-2">
              Event Explorer (optional)
            </div>
            <div className="text-xs text-gray-500 mb-4">
              Backend can optionally include a small event sample for drill-down.
            </div>
            <pre className="text-xs text-gray-600 whitespace-pre-wrap">
{JSON.stringify(summary!.events!.slice(0, 3), null, 2)}
            </pre>
          </div>
        )}
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
          <table className="min-w-[840px] w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr>
                <th className="py-2">Bin</th>
                <th className="py-2">Count</th>
                <th className="py-2">Mean c̄</th>
                <th className="py-2">Acc ā</th>
                <th className="py-2">Gap</th>
                <th className="py-2">Signal</th>
              </tr>
            </thead>
            <tbody className="text-gray-700">
              {(bins || []).map((b, i) => {
                const hot = challengeBin && b.bin === challengeBin;
                const bad = typeof b.gap === "number" && b.gap > 0.05;
                return (
                  <tr
                    key={i}
                    className={[
                      "border-t border-gray-100",
                      hot ? "bg-amber-50/40" : "",
                    ].join(" ")}
                  >
                    <td className="py-2 font-medium">{b.bin}</td>
                    <td className="py-2">{b.count}</td>
                    <td className="py-2">
                      {typeof b.mean_conf === "number"
                        ? fmtPct(b.mean_conf, 1)
                        : "—"}
                    </td>
                    <td className="py-2">
                      {typeof b.accuracy === "number"
                        ? fmtPct(b.accuracy, 1)
                        : "—"}
                    </td>
                    <td className="py-2">
                      {typeof b.gap === "number" ? fmtPct(b.gap, 2) : "—"}
                    </td>
                    <td className="py-2">
                      <span
                        className={[
                          "inline-flex items-center px-3 py-1 rounded-full text-xs font-medium",
                          bad
                            ? "bg-red-50 text-red-700 border border-red-100"
                            : "bg-green-50 text-green-700 border border-green-100",
                        ].join(" ")}
                      >
                        {bad ? "Over/Under" : "Aligned"}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {(!bins || bins.length === 0) && (
                <tr>
                  <td className="py-6 text-gray-400" colSpan={6}>
                    No bins returned. Run Phase 6 → Phase 7 → make_phase7_lock_bundle.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {typeof ece === "number" && (
          <div className="mt-6 p-6 rounded-2xl bg-gray-50 border border-gray-100">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
              Interpretation
            </div>
            <div className="text-sm text-gray-600 leading-relaxed">
              Current ECE is <strong>{fmtNum(ece, 4)}</strong>.{" "}
              {ece < 0.05
                ? "Confidence is broadly honest: stated confidence tracks observed accuracy."
                : ece < 0.1
                ? "Calibration is drifting: confidence begins to diverge from observed accuracy."
                : "Overconfidence risk: confidence diverges materially from observed accuracy."}
            </div>
          </div>
        )}
      </div>

      {/* Verify details */}
      {verify && !verify.match && (
        <div className="p-8 rounded-[2.5rem] border border-gray-100">
          <h3 className="text-xl font-bold italic mb-4">Verify Details</h3>
          <pre className="text-xs text-gray-600 whitespace-pre-wrap">
{JSON.stringify(verify, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}