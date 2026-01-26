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
  metrics?: any;
  curve?: any;
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

const BRIDGE = process.env.NEXT_PUBLIC_AION_DEMO_BRIDGE || "http://127.0.0.1:8007";

async function fetchJson(url: string) {
  const r = await fetch(url, { cache: "no-store" });
  const t = await r.text();
  let j: any = {};
  try { j = t ? JSON.parse(t) : {}; } catch { j = { ok: false, _nonJson: true, _text: t.slice(0, 500) }; }
  if (!r.ok) throw new Error(j?.error || `HTTP ${r.status}`);
  return j;
}

export default function Phase7CalibrationHUD() {
  const [summary, setSummary] = useState<Phase7Summary | null>(null);
  const [verify, setVerify] = useState<VerifyResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
      setBusy(true);
      setErr(null);
      const j = await fetchJson(`${BRIDGE}/api/phase7/verify`);
      setVerify(j);
    } catch (e: any) {
      setErr(String(e?.message || e));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { load(); }, []);

  const headline = useMemo(() => {
    const ece = summary?.metrics?.ece;
    if (typeof ece !== "number") return "—";
    if (ece < 0.05) return "WELL-CALIBRATED";
    if (ece < 0.10) return "DRIFTING";
    return "OVERCONFIDENT";
  }, [summary]);

  return (
    <div className="space-y-10">
      {/* Top row: Trust summary */}
      <div className="grid md:grid-cols-3 gap-6">
        <div className="p-8 rounded-[2.5rem] border border-gray-100">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
            Trust Status
          </div>
          <div className="text-3xl font-bold italic">{headline}</div>
          <div className="text-sm text-gray-500 mt-2">
            ECE: {typeof summary?.metrics?.ece === "number" ? summary!.metrics.ece.toFixed(4) : "—"}
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
            Worst gap: {summary?.metrics?.worst_gap ?? "—"}
          </div>
        </div>

        <div className="p-8 rounded-[2.5rem] border border-gray-100">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-gray-400 mb-2">
            Lock Verification
          </div>
          <button
            onClick={runVerify}
            disabled={busy}
            className="px-5 py-3 rounded-2xl bg-black text-white text-sm font-medium"
          >
            {busy ? "Verifying…" : "Verify vs Golden"}
          </button>
          <div className="text-sm text-gray-500 mt-3">
            {verify ? (verify.match ? "✅ VERIFIED" : "⚠ MISMATCH") : "—"}
          </div>
        </div>
      </div>

      {/* Errors */}
      {err && (
        <div className="p-6 rounded-2xl border border-red-200 bg-red-50 text-red-700 text-sm">
          {err}
        </div>
      )}

      {/* Bin table */}
      <div className="p-8 rounded-[2.5rem] border border-gray-100">
        <div className="flex items-baseline justify-between mb-6">
          <h3 className="text-2xl font-bold italic tracking-tight">Calibration Bins</h3>
          <button onClick={load} className="text-sm text-gray-500 underline">
            Refresh
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-[720px] w-full text-sm">
            <thead className="text-left text-gray-500">
              <tr>
                <th className="py-2">Bin</th>
                <th className="py-2">Count</th>
                <th className="py-2">Mean c̄</th>
                <th className="py-2">Acc ā</th>
                <th className="py-2">Gap</th>
              </tr>
            </thead>
            <tbody className="text-gray-700">
              {(summary?.metrics?.bins || []).map((b: any, i: number) => (
                <tr key={i} className="border-t border-gray-100">
                  <td className="py-2">{b.bin}</td>
                  <td className="py-2">{b.count}</td>
                  <td className="py-2">{typeof b.mean_conf === "number" ? b.mean_conf.toFixed(3) : b.mean_conf}</td>
                  <td className="py-2">{typeof b.accuracy === "number" ? b.accuracy.toFixed(3) : b.accuracy}</td>
                  <td className="py-2">
                    {typeof b.gap === "number" ? b.gap.toFixed(3) : b.gap}
                    {typeof b.gap === "number" && b.gap > 0.05 ? " ⚠" : ""}
                  </td>
                </tr>
              ))}
              {(!summary?.metrics?.bins || summary.metrics.bins.length === 0) && (
                <tr>
                  <td className="py-6 text-gray-400" colSpan={5}>
                    No bins returned. Run Phase 6 → Phase 7 → make_phase7_lock_bundle.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
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