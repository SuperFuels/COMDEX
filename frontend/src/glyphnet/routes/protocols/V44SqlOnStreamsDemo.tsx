"use client";

import React, { useEffect, useMemo, useState } from "react";

/** ---------- shared helpers ---------- */

async function fetchJson(url: string, body: any, timeoutMs = 30000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body ?? {}),
      signal: ctrl.signal,
    });
    const txt = await r.text();
    let json: any = {};
    try {
      json = txt ? JSON.parse(txt) : {};
    } catch {
      json = { _nonJson: true, _text: txt.slice(0, 400) };
    }
    return { ok: r.ok, status: r.status, json };
  } finally {
    clearTimeout(t);
  }
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function bytes(n: number) {
  const units = ["B", "KB", "MB", "GB"];
  let v = Number(n || 0);
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

function safeObj(x: any) {
  return x && typeof x === "object" ? x : {};
}

function boolBadge(ok: boolean | null) {
  const good = ok === true;
  const bad = ok === false;
  const label = good ? "✅ VERIFIED" : bad ? "❌ FAIL" : "—";
  const cls = good
    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
    : bad
      ? "border-red-200 bg-red-50 text-red-800"
      : "border-slate-200 bg-slate-50 text-slate-500";
  return { label, cls };
}

// stable JSON (deterministic ordering)
function stableStringify(x: any): string {
  const seen = new WeakSet<object>();
  const walk = (v: any): any => {
    if (v === null || typeof v !== "object") return v;
    if (seen.has(v)) throw new Error("cyclic json");
    seen.add(v);
    if (Array.isArray(v)) return v.map(walk);
    const out: any = {};
    for (const k of Object.keys(v).sort()) out[k] = walk(v[k]);
    return out;
  };
  return JSON.stringify(walk(x));
}

function utf8Len(s: string): number {
  try {
    return new TextEncoder().encode(s).length;
  } catch {
    return s.length;
  }
}

async function gzipLenUtf8(s: string): Promise<number | null> {
  try {
    // @ts-ignore
    if (typeof CompressionStream === "undefined") return null;
    const u8 = new TextEncoder().encode(s);
    // @ts-ignore
    const stream = new Blob([u8]).stream().pipeThrough(new CompressionStream("gzip"));
    const ab = await new Response(stream).arrayBuffer();
    return new Uint8Array(ab).length;
  } catch {
    return null;
  }
}

/** ---------- branded atoms ---------- */

function Card(props: { title?: string; right?: React.ReactNode; children: React.ReactNode; subtitle?: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      {(props.title || props.right) && (
        <div className="flex items-start justify-between gap-4">
          <div>
            {props.title ? (
              <div className="text-sm font-extrabold tracking-tight text-slate-900">{props.title}</div>
            ) : null}
            {props.subtitle ? <div className="mt-1 text-xs font-medium text-slate-500">{props.subtitle}</div> : null}
          </div>
          {props.right ? <div className="shrink-0">{props.right}</div> : null}
        </div>
      )}
      <div className={(props.title || props.right) ? "mt-3" : ""}>{props.children}</div>
    </div>
  );
}

function PillButton(props: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "ghost" | "primary";
  title?: string;
}) {
  const v = props.variant || "ghost";
  const base =
    "px-4 py-2 rounded-full text-xs font-semibold border transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B74E4]/30";
  const ghost = "border-slate-200 bg-white text-slate-800 hover:bg-slate-50";
  const primary = "border-[#1B74E4] bg-[#1B74E4] text-white hover:brightness-110";
  const disabled = "opacity-60 cursor-default hover:brightness-100";

  return (
    <button
      type="button"
      onClick={props.onClick}
      disabled={props.disabled}
      title={props.title}
      className={[base, v === "primary" ? primary : ghost, props.disabled ? disabled : ""].join(" ")}
    >
      {props.children}
    </button>
  );
}

function StatTile(props: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
      <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{props.label}</div>
      <div className="mt-1 text-sm font-extrabold text-slate-900">{props.value}</div>
      {props.sub ? <div className="mt-1 text-[11px] text-slate-500">{props.sub}</div> : null}
    </div>
  );
}

/** simple 2-bar compare chart: baseline vs wire */
function BytesCompareChart(props: { wire: number; base: number; baseLabel: string }) {
  const wire = Number(props.wire || 0);
  const base = Number(props.base || 0);
  const max = Math.max(1, wire, base);
  const w = 560;
  const h = 170;
  const pad = { l: 70, r: 16, t: 18, b: 42 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;

  const bars = [
    { label: "WirePack", v: wire, fill: "#1B74E4" },
    { label: props.baseLabel, v: base, fill: "#0f172a" },
  ];

  const barW = innerW / bars.length;
  const y = (v: number) => pad.t + innerH * (1 - v / max);
  const barH = (v: number) => pad.t + innerH - y(v);

  return (
    <Card title="Bytes comparison" subtitle="Like-for-like only. Positive % means WirePack is larger.">
      <svg viewBox={`0 0 ${w} ${h}`} className="mt-2 block w-full">
        <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + innerH} stroke="#e2e8f0" />
        <line x1={pad.l} y1={pad.t + innerH} x2={pad.l + innerW} y2={pad.t + innerH} stroke="#e2e8f0" />

        {[0, max].map((t, i) => (
          <g key={i}>
            <line x1={pad.l - 4} y1={y(t)} x2={pad.l} y2={y(t)} stroke="#e2e8f0" />
            <text x={pad.l - 8} y={y(t) + 4} fontSize="10" textAnchor="end" fill="#64748b">
              {i === 0 ? "0" : bytes(t)}
            </text>
          </g>
        ))}

        {bars.map((b, i) => {
          const x = pad.l + i * barW + Math.max(18, barW * 0.2);
          const bw = Math.max(80, barW * 0.6);
          const top = y(b.v);
          const bh = barH(b.v);
          return (
            <g key={b.label}>
              <rect x={x} y={top} width={bw} height={bh} rx={10} fill={b.fill} opacity={0.9} />
              <text x={x + bw / 2} y={top - 6} fontSize="10" textAnchor="middle" fill="#0f172a">
                {bytes(b.v)}
              </text>
              <text x={x + bw / 2} y={pad.t + innerH + 18} fontSize="10" textAnchor="middle" fill="#64748b">
                {b.label}
              </text>
            </g>
          );
        })}
      </svg>
    </Card>
  );
}

/** For projection: show first N points as a bar-ish sparkline (value magnitude). */
function ProjectionSpark(props: { rows: any[] }) {
  const rows = Array.isArray(props.rows) ? props.rows.slice(0, 32) : [];
  const vals = rows
    .map((r) => {
      if (r == null) return null;
      if (typeof r === "number") return r;
      if (Array.isArray(r) && r.length >= 2) return Number(r[1]);
      if (typeof r === "object") return Number((r as any).value ?? (r as any).v ?? (r as any)[1]);
      return null;
    })
    .filter((x) => typeof x === "number" && Number.isFinite(x)) as number[];

  const max = Math.max(1, ...vals.map((v) => Math.abs(v)));
  const w = 560;
  const h = 160;
  const pad = { l: 12, r: 12, t: 18, b: 24 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const n = Math.max(1, vals.length);
  const barW = innerW / n;

  return (
    <Card title="Projection preview" subtitle={`first ${Math.min(32, vals.length)} values (magnitude)`}>
      {vals.length === 0 ? (
        <div className="mt-2 text-xs text-slate-500">No projection-like rows found.</div>
      ) : (
        <svg viewBox={`0 0 ${w} ${h}`} className="mt-2 block w-full">
          <line x1={pad.l} y1={pad.t + innerH} x2={pad.l + innerW} y2={pad.t + innerH} stroke="#e2e8f0" />
          {vals.map((v, i) => {
            const x = pad.l + i * barW + Math.max(1, barW * 0.1);
            const bw = Math.max(4, barW * 0.8);
            const bh = innerH * (Math.abs(v) / max);
            const y = pad.t + innerH - bh;
            return <rect key={i} x={x} y={y} width={bw} height={bh} rx={3} fill="#1B74E4" opacity={0.85} />;
          })}
        </svg>
      )}
    </Card>
  );
}

/** For histogram: show first 32 bins as bars. Accepts many shapes. */
function HistogramChart(props: { rows: any[] }) {
  const rowsRaw = Array.isArray(props.rows) ? props.rows : [];
  const bins: { bin: number; count: number }[] = [];
  for (const r of rowsRaw) {
    if (r == null) continue;
    if (Array.isArray(r) && r.length >= 2) {
      const bin = Number(r[0]);
      const count = Number(r[1]);
      if (Number.isFinite(bin) && Number.isFinite(count)) bins.push({ bin, count });
      continue;
    }
    if (typeof r === "object") {
      const bin = Number((r as any).bin ?? (r as any).bucket ?? (r as any).k ?? (r as any).key);
      const count = Number((r as any).count ?? (r as any).c ?? (r as any).value);
      if (Number.isFinite(bin) && Number.isFinite(count)) bins.push({ bin, count });
    }
  }

  bins.sort((a, b) => a.bin - b.bin);
  const data = bins.slice(0, 32);
  const max = Math.max(1, ...data.map((d) => d.count));

  const w = 560;
  const h = 170;
  const pad = { l: 44, r: 16, t: 18, b: 42 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const n = Math.max(1, data.length);
  const barW = innerW / n;

  const y = (v: number) => pad.t + innerH * (1 - v / max);

  return (
    <Card title="Histogram preview" subtitle={`first ${Math.min(32, data.length)} bins`}>
      {data.length === 0 ? (
        <div className="mt-2 text-xs text-slate-500">No histogram-like rows found.</div>
      ) : (
        <svg viewBox={`0 0 ${w} ${h}`} className="mt-2 block w-full">
          <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + innerH} stroke="#e2e8f0" />
          <line x1={pad.l} y1={pad.t + innerH} x2={pad.l + innerW} y2={pad.t + innerH} stroke="#e2e8f0" />

          {[0, max].map((t, i) => (
            <g key={i}>
              <line x1={pad.l - 4} y1={y(t)} x2={pad.l} y2={y(t)} stroke="#e2e8f0" />
              <text x={pad.l - 8} y={y(t) + 4} fontSize="10" textAnchor="end" fill="#64748b">
                {t}
              </text>
            </g>
          ))}

          {data.map((d, i) => {
            const x = pad.l + i * barW + Math.max(2, barW * 0.12);
            const bw = Math.max(6, barW * 0.76);
            const top = y(d.count);
            const bh = pad.t + innerH - top;
            return (
              <g key={`${d.bin}-${i}`}>
                <rect x={x} y={top} width={bw} height={bh} rx={6} fill="#0f172a" opacity={0.85} />
                <text x={x + bw / 2} y={pad.t + innerH + 16} fontSize="9" textAnchor="middle" fill="#64748b">
                  {d.bin}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </Card>
  );
}

/** ---------- v44 UI ---------- */

export function V44SqlOnStreamsDemo() {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<any>(null);

  const [queryId, setQueryId] = useState<"projection" | "histogram">("projection");
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(256);
  const [muts, setMuts] = useState(3);
  const [k, setK] = useState(64);
  const [seed, setSeed] = useState(1337);

  const [showExamples, setShowExamples] = useState(true);
  const [receiptInput, setReceiptInput] = useState("");

  // baseline interpretation (fixes “wirepack losing” confusion)
  const [baseLabel, setBaseLabel] = useState("gzip baseline");
  const [baseNote, setBaseNote] = useState<string | null>(null);
  const [snapPayloadRaw, setSnapPayloadRaw] = useState<number | null>(null);
  const [snapPayloadGz, setSnapPayloadGz] = useState<number | null>(null);

  const EXAMPLES = [
    { label: "Projection (dashboard panel)", queryId: "projection" as const, n: 4096, turns: 256, muts: 3, k: 64, seed: 1337 },
    { label: "Histogram (rollup/group-by)", queryId: "histogram" as const, n: 4096, turns: 256, muts: 3, k: 64, seed: 1337 },
    { label: "Bigger state (n=65k)", queryId: "projection" as const, n: 65536, turns: 256, muts: 3, k: 128, seed: 2026 },
    { label: "More churn (turns=1024)", queryId: "histogram" as const, n: 4096, turns: 1024, muts: 5, k: 64, seed: 9090 },
  ];

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);

    try {
      const body = { query_id: queryId, n, turns, muts, k, seed };

      let res = await fetchJson("/api/wirepack/v44/run", body, 60000);
      if (res.status === 404) res = await fetchJson("/api/wirepack/v46/run", body, 60000);

      if (!res.ok) throw new Error(`HTTP ${res.status}: ${JSON.stringify(res.json)}`);
      if (!res.json?.ok && res.json?.ok !== undefined) throw new Error(res.json?.error || "backend returned ok=false");

      setOut(res.json);
    } catch (e: any) {
      setErr(e?.message || "v44 failed");
    } finally {
      setBusy(false);
    }
  }

  const b = useMemo(() => safeObj(out?.bytes), [out]);
  const rec = useMemo(() => safeObj(out?.receipts), [out]);

  const queryOk = out ? Boolean(out.query_ok ?? out.ok ?? out?.invariants?.query_ok) : null;
  const correctnessBadge = boolBadge(queryOk === null ? null : queryOk);

  const drift = String(rec?.drift_sha256 ?? out?.drift_sha256 ?? "");
  const resultSha = String(rec?.result_sha256 ?? out?.result_sha256 ?? "");
  const leanOk = rec?.LEAN_OK ?? out?.LEAN_OK ?? null;

  const wire = Number(b?.wire_total_bytes ?? 0);
  const gzBackend = Number(b?.gzip_snapshot_bytes_total ?? 0);

  const templateBytes = Number(b?.wire_template_bytes ?? b?.template_bytes ?? 0);
  const deltaBytesTotal = Number(b?.wire_delta_bytes_total ?? b?.delta_bytes_total ?? 0);

  const qMs = out?.timing_ms?.query ?? out?.timing_ms ?? out?.query_ms ?? out?.query_time_ms ?? null;

  const ops = Number(out?.ops ?? (Number(turns || 0) * Number(muts || 0)));
  const bytesPerOp = ops > 0 ? deltaBytesTotal / ops : null;

  const Q = Array.isArray(out?.Q) ? out.Q : Array.isArray(out?.params?.Q) ? out.params.Q : null;

  const snapshotResult = out?.snapshot_result ?? out?.snapshot ?? out?.snapshot_head ?? null;
  const streamResult = out?.stream_result ?? out?.stream ?? out?.stream_head ?? null;

  const snapArr = Array.isArray(snapshotResult) ? snapshotResult : [];
  const streamArr = Array.isArray(streamResult) ? streamResult : [];

  const previewRows =
    Array.isArray(streamArr) && streamArr.length ? streamArr : Array.isArray(snapArr) ? snapArr : [];

  // --- baseline scope detection (important) ---
  useEffect(() => {
    let alive = true;
    (async () => {
      setBaseNote(null);
      setSnapPayloadRaw(null);
      setSnapPayloadGz(null);

      if (!out) {
        setBaseLabel("gzip baseline");
        return;
      }

      // If backend “gzip_snapshot_bytes_total” is tiny, it may actually be gzip(query result payload).
      // We test by gzipping snapshotResult payload client-side and comparing.
      if (snapArr.length) {
        try {
          const canon = stableStringify(snapArr);
          const raw = utf8Len(canon);
          const gz = await gzipLenUtf8(canon);

          if (!alive) return;

          setSnapPayloadRaw(raw);
          setSnapPayloadGz(gz);

          if (gz != null && gzBackend > 0) {
            const ratio = gzBackend / gz; // ~1 means match
            const close = ratio > 0.8 && ratio < 1.25; // within 25%
            if (close) {
              setBaseLabel("gzip(query result payload)");
              setBaseNote("Backend baseline matches gzip(snapshot_result payload). This is NOT gzip of full snapshots-over-time.");
            } else {
              setBaseLabel("gzip(backend baseline)");
              setBaseNote("Backend baseline scope differs from gzip(snapshot_result payload). Check server definition of gzip_snapshot_bytes_total.");
            }
          } else {
            setBaseLabel("gzip(backend baseline)");
            setBaseNote(typeof CompressionStream === "undefined" ? "Browser gzip unsupported; baseline label uses backend only." : null);
          }
        } catch {
          setBaseLabel("gzip(backend baseline)");
        }
      } else {
        setBaseLabel("gzip(backend baseline)");
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [out]);

  // Correct comparison math:
  // ratio = wire/gzip, pct = (wire/gzip - 1)*100 (positive means WirePack is bigger)
  const base = gzBackend;
  const ratioWireOverBase = wire > 0 && base > 0 ? wire / base : null;
  const pctWireVsBase = wire > 0 && base > 0 ? (wire / base - 1) * 100 : null;

  const normalizedInput = receiptInput.trim().toLowerCase();
  const normalizedDrift = (drift || "").trim().toLowerCase();
  const receiptMatch = normalizedInput.length >= 8 && normalizedDrift.length >= 8 && normalizedInput === normalizedDrift;
  const receiptBadge = boolBadge(normalizedInput.length === 0 ? null : receiptMatch);

  return (
    <div className="flex flex-col gap-3">
      {/* Header + controls */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-sm font-extrabold text-slate-900">v44 — SQL on Streams (Queryable Compression)</div>
          <div className="mt-1 text-xs font-medium text-slate-600">
            Run SQL-shaped queries directly on compressed delta streams, and ship a receipt that locks correctness.
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={queryId}
            onChange={(e) => setQueryId(e.target.value as any)}
            className="px-4 py-2 rounded-full text-xs font-semibold border border-slate-200 bg-white text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B74E4]/30"
          >
            <option value="projection">SELECT idx,value WHERE idx IN Q</option>
            <option value="histogram">GROUP BY (value % 256) COUNT(*)</option>
          </select>

          {[
            ["n", n, setN, 256, 65536],
            ["turns", turns, setTurns, 16, 2048],
            ["muts", muts, setMuts, 1, 128],
            ["k", k, setK, 1, 4096],
            ["seed", seed, setSeed, 1, 1_000_000],
          ].map(([label, val, setVal, lo, hi]: any) => (
            <label key={label} className="flex items-center gap-2 text-xs font-semibold text-slate-600">
              {label}
              <input
                type="number"
                value={val}
                min={lo}
                max={hi}
                onChange={(e) => {
                  const nv = Number(e.target.value);
                  if (!Number.isFinite(nv)) return;
                  setVal(clamp(nv, lo, hi));
                }}
                className="w-[92px] px-3 py-2 rounded-full border border-slate-200 bg-white text-slate-800 text-xs font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B74E4]/30"
              />
            </label>
          ))}

          <PillButton onClick={() => setShowExamples((s) => !s)} title="Toggle presets">
            Examples
          </PillButton>

          <PillButton onClick={run} disabled={busy} variant="primary">
            {busy ? "Running…" : "Run"}
          </PillButton>
        </div>
      </div>

      {showExamples ? (
        <Card title="Presets">
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <PillButton
                key={ex.label}
                onClick={() => {
                  setQueryId(ex.queryId);
                  setN(ex.n);
                  setTurns(ex.turns);
                  setMuts(ex.muts);
                  setK(ex.k);
                  setSeed(ex.seed);
                }}
              >
                {ex.label}
              </PillButton>
            ))}
          </div>
        </Card>
      ) : null}

      {err ? <div className="text-xs font-semibold text-red-700">{err}</div> : null}

      {/* Pitch */}
      <Card
        title="🎯 SQL-shaped analytics on compressed streams (projection + group-by)"
        subtitle={
          <span>
            <span className="font-semibold text-slate-700">What this proves:</span>{" "}
            dashboard queries can execute on the delta stream and still emit a verifiable receipt.
          </span>
        }
      >
        <div className="text-xs text-slate-700 leading-relaxed">
          <div className="mt-1">
            <span className="font-semibold">Projection</span>{" "}
            <code className="text-slate-900">SELECT idx,value WHERE idx IN Q</code>
            {" — "}panel pulls specific metrics fast.
          </div>
          <div className="mt-1">
            <span className="font-semibold">Histogram</span>{" "}
            <code className="text-slate-900">GROUP BY (value % 256) COUNT(*)</code>
            {" — "}rollups without scanning raw snapshots.
          </div>
          <div className="mt-3">
            <span className="font-semibold">Trust model:</span>{" "}
            snapshot vs stream must match (<code className="text-slate-900">query_ok</code>) and the run is bound into{" "}
            <code className="text-slate-900">drift_sha256</code>.
          </div>
        </div>
      </Card>

      {/* Dashboard: charts + stats */}
      <div className="grid gap-3 lg:grid-cols-[1.2fr_0.8fr] items-start">
        <div className="flex flex-col gap-3">
          {queryId === "histogram" ? <HistogramChart rows={previewRows} /> : <ProjectionSpark rows={previewRows} />}
          {wire || base ? <BytesCompareChart wire={wire} base={base} baseLabel={baseLabel} /> : null}
          {baseNote ? (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
              <span className="font-semibold">Note:</span> {baseNote}
              {snapPayloadRaw != null ? (
                <div className="mt-1 text-slate-500">
                  snapshot_result payload raw≈{bytes(snapPayloadRaw)}
                  {snapPayloadGz != null ? ` · gzip≈${bytes(snapPayloadGz)}` : ""}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <StatTile
            label="Correctness"
            value={
              <span className={`px-3 py-1 rounded-full border text-xs font-extrabold ${correctnessBadge.cls}`}>
                {correctnessBadge.label}
              </span>
            }
            sub="snapshot vs stream"
          />
          <StatTile label="Query time" value={qMs != null ? `${Number(qMs).toFixed(2)} ms` : "—"} sub="if backend returns timing" />
          <StatTile label="Stream bytes" value={wire ? bytes(wire) : "—"} sub="wire_total_bytes" />
          <StatTile label={baseLabel} value={base ? bytes(base) : "—"} sub="backend field" />

          <StatTile
            label="Wire vs gzip"
            value={ratioWireOverBase != null ? `${ratioWireOverBase.toFixed(2)}×` : "—"}
            sub={pctWireVsBase != null ? `${pctWireVsBase >= 0 ? "+" : ""}${pctWireVsBase.toFixed(1)}% (WirePack vs baseline)` : "—"}
          />

          <StatTile label="Bytes / op" value={bytesPerOp != null ? `${bytesPerOp.toFixed(2)} B` : "—"} sub={`${ops} ops`} />
          <StatTile label="Template" value={templateBytes ? bytes(templateBytes) : "—"} sub="one-time" />
          <StatTile label="Delta total" value={deltaBytesTotal ? bytes(deltaBytesTotal) : "—"} sub="all deltas" />
        </div>
      </div>

      {/* Receipt verifier */}
      <Card
        title="Receipt verifier"
        right={
          <span className={`px-3 py-1 rounded-full border text-xs font-extrabold ${receiptBadge.cls}`}>
            {receiptBadge.label}
          </span>
        }
      >
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={receiptInput}
            onChange={(e) => setReceiptInput(e.target.value)}
            placeholder="Paste drift_sha256 here to verify…"
            className="flex-1 min-w-[320px] px-3 py-2 rounded-xl border border-slate-200 bg-white text-slate-900 text-xs font-mono focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B74E4]/30"
          />
          <PillButton onClick={() => setReceiptInput(drift || "")} title="Copy current drift into the verifier input">
            Use current drift
          </PillButton>
        </div>

        <div className="mt-3 text-xs text-slate-500 leading-relaxed">
          <div>
            drift_sha256 (from run): <code className="text-slate-900">{drift || "—"}</code>
          </div>
          <div className="mt-1">Match = “query result is provably the same.”</div>
        </div>
      </Card>

      {/* Receipt + outputs */}
      <div className="grid gap-3 lg:grid-cols-2 items-start">
        <Card title="Receipt">
          <div className="text-xs text-slate-700 leading-relaxed">
            <div>
              query_ok: <code className="text-slate-900">{out ? String(queryOk) : "—"}</code>
            </div>
            <div>
              result_sha256: <code className="text-slate-900">{resultSha || "—"}</code>
            </div>
            <div>
              drift_sha256: <code className="text-slate-900">{drift || "—"}</code>
            </div>
            <div>
              LEAN_OK: <code className="text-slate-900">{leanOk ?? "—"}</code>
            </div>
          </div>
        </Card>

        <Card title="Outputs (truncated)">
          <pre className="mt-1 max-h-[360px] overflow-auto whitespace-pre-wrap text-xs text-slate-900">
            {out
              ? JSON.stringify(
                  {
                    query_id: out.query_id,
                    params: out.params,
                    Q_head: Array.isArray(Q) ? Q.slice(0, 16) : Q,
                    snapshot_head: Array.isArray(snapshotResult) ? snapshotResult.slice(0, 16) : snapshotResult,
                    stream_head: Array.isArray(streamResult) ? streamResult.slice(0, 16) : streamResult,
                    ops: out.ops ?? ops,
                    bytes: out.bytes,
                  },
                  null,
                  2,
                )
              : "Run to populate outputs."}
          </pre>
        </Card>
      </div>

      {/* Raw */}
      <Card title="Raw response">
        <pre className="mt-1 whitespace-pre-wrap text-xs text-slate-900">
          {out ? JSON.stringify(out, null, 2) : "—"}
        </pre>
      </Card>

      {/* Endpoint note */}
      <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-500">
        Endpoints tried: <code className="text-slate-900">POST /api/wirepack/v44/run</code> → fallback{" "}
        <code className="text-slate-900">POST /api/wirepack/v46/run</code>
      </div>
    </div>
  );
}