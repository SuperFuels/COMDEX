import React, { useMemo, useState } from "react";

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
  const bg = good ? "#ecfdf5" : bad ? "#fef2f2" : "#f9fafb";
  const fg = good ? "#065f46" : bad ? "#991b1b" : "#6b7280";
  const bd = good ? "#a7f3d0" : bad ? "#fecaca" : "#e5e7eb";
  const label = good ? "✅ VERIFIED" : bad ? "❌ FAIL" : "—";
  return { bg, fg, bd, label };
}

function StatTile(props: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
      <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900, letterSpacing: 0.3 }}>{props.label}</div>
      <div style={{ fontSize: 13, color: "#111827", fontWeight: 900, marginTop: 4 }}>{props.value}</div>
      {props.sub ? <div style={{ fontSize: 10, color: "#6b7280", marginTop: 4 }}>{props.sub}</div> : null}
    </div>
  );
}

/** simple 2-bar compare chart: gzip vs wire */
function BytesCompareChart(props: { wire: number; gz: number }) {
  const wire = Number(props.wire || 0);
  const gz = Number(props.gz || 0);
  const max = Math.max(1, wire, gz);
  const w = 560;
  const h = 170;
  const pad = { l: 70, r: 16, t: 18, b: 42 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;

  const bars = [
    { label: "WirePack", v: wire, fill: "#3b82f6" },
    { label: "gzip snapshots", v: gz, fill: "#111827" },
  ];

  const barW = innerW / bars.length;

  const y = (v: number) => pad.t + innerH * (1 - v / max);
  const barH = (v: number) => pad.t + innerH - y(v);

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Bytes comparison</div>
        <div style={{ fontSize: 10, color: "#6b7280" }}>Lower is better (storage + scan cost)</div>
      </div>

      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", marginTop: 8, display: "block" }}>
        {/* axis */}
        <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + innerH} stroke="#e5e7eb" />
        <line x1={pad.l} y1={pad.t + innerH} x2={pad.l + innerW} y2={pad.t + innerH} stroke="#e5e7eb" />

        {/* y ticks */}
        {[0, max].map((t, i) => (
          <g key={i}>
            <line x1={pad.l - 4} y1={y(t)} x2={pad.l} y2={y(t)} stroke="#e5e7eb" />
            <text x={pad.l - 8} y={y(t) + 4} fontSize="10" textAnchor="end" fill="#6b7280">
              {i === 0 ? "0" : bytes(t)}
            </text>
          </g>
        ))}

        {/* bars */}
        {bars.map((b, i) => {
          const x = pad.l + i * barW + Math.max(18, barW * 0.2);
          const bw = Math.max(80, barW * 0.6);
          const top = y(b.v);
          const bh = barH(b.v);
          return (
            <g key={b.label}>
              <rect x={x} y={top} width={bw} height={bh} rx={10} fill={b.fill} opacity={0.9} />
              <text x={x + bw / 2} y={top - 6} fontSize="10" textAnchor="middle" fill="#111827">
                {bytes(b.v)}
              </text>
              <text x={x + bw / 2} y={pad.t + innerH + 18} fontSize="10" textAnchor="middle" fill="#6b7280">
                {b.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
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
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Projection preview</div>
        <div style={{ fontSize: 10, color: "#6b7280" }}>first {Math.min(32, vals.length)} values (magnitude)</div>
      </div>

      {vals.length === 0 ? (
        <div style={{ marginTop: 8, fontSize: 11, color: "#6b7280" }}>No projection-like rows found.</div>
      ) : (
        <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", marginTop: 8, display: "block" }}>
          <line x1={pad.l} y1={pad.t + innerH} x2={pad.l + innerW} y2={pad.t + innerH} stroke="#e5e7eb" />
          {vals.map((v, i) => {
            const x = pad.l + i * barW + Math.max(1, barW * 0.1);
            const bw = Math.max(4, barW * 0.8);
            const bh = innerH * (Math.abs(v) / max);
            const y = pad.t + innerH - bh;
            return <rect key={i} x={x} y={y} width={bw} height={bh} rx={3} fill="#3b82f6" opacity={0.85} />;
          })}
        </svg>
      )}
    </div>
  );
}

/** For histogram: show first 32 bins as bars. Accepts many shapes. */
function HistogramChart(props: { rows: any[] }) {
  const rowsRaw = Array.isArray(props.rows) ? props.rows : [];
  // Interpret each row as [bin, count] or {bin,count}
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
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Histogram preview</div>
        <div style={{ fontSize: 10, color: "#6b7280" }}>first {Math.min(32, data.length)} bins</div>
      </div>

      {data.length === 0 ? (
        <div style={{ marginTop: 8, fontSize: 11, color: "#6b7280" }}>No histogram-like rows found.</div>
      ) : (
        <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", marginTop: 8, display: "block" }}>
          {/* axes */}
          <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + innerH} stroke="#e5e7eb" />
          <line x1={pad.l} y1={pad.t + innerH} x2={pad.l + innerW} y2={pad.t + innerH} stroke="#e5e7eb" />

          {/* y ticks */}
          {[0, max].map((t, i) => (
            <g key={i}>
              <line x1={pad.l - 4} y1={y(t)} x2={pad.l} y2={y(t)} stroke="#e5e7eb" />
              <text x={pad.l - 8} y={y(t) + 4} fontSize="10" textAnchor="end" fill="#6b7280">
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
                <rect x={x} y={top} width={bw} height={bh} rx={6} fill="#111827" opacity={0.85} />
                <text x={x + bw / 2} y={pad.t + innerH + 16} fontSize="9" textAnchor="middle" fill="#6b7280">
                  {d.bin}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
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

  // “dashboard standard” extras
  const [showExamples, setShowExamples] = useState(true);
  const [receiptInput, setReceiptInput] = useState("");

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

      // try v44 route first (if you later add it, this will start working automatically)
      let res = await fetchJson("/api/wirepack/v44/run", body, 60000);
      // fallback to v46
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

  // correctness
  const queryOk = out ? Boolean(out.query_ok ?? out.ok ?? out?.invariants?.query_ok) : null;
  const correctnessBadge = boolBadge(queryOk === null ? null : queryOk);

  // receipts
  const drift = String(rec?.drift_sha256 ?? out?.drift_sha256 ?? "");
  const resultSha = String(rec?.result_sha256 ?? out?.result_sha256 ?? "");
  const leanOk = rec?.LEAN_OK ?? out?.LEAN_OK ?? null;

  // bytes
  const wire = Number(b?.wire_total_bytes ?? 0);
  const gz = Number(b?.gzip_snapshot_bytes_total ?? 0);
  const factor = wire && gz ? gz / wire : null;
  const pctSaved = wire && gz ? (1 - wire / gz) * 100 : null;

  const templateBytes = Number(b?.wire_template_bytes ?? b?.template_bytes ?? 0);
  const deltaBytesTotal = Number(b?.wire_delta_bytes_total ?? b?.delta_bytes_total ?? 0);

  // perf (optional fields)
  const qMs =
    out?.timing_ms?.query ??
    out?.timing_ms ??
    out?.query_ms ??
    out?.query_time_ms ??
    null;

  const ops = Number(turns || 0) * Number(muts || 0);
  const bytesPerOp = ops > 0 ? deltaBytesTotal / ops : null;

  // outputs
  const Q = Array.isArray(out?.Q) ? out.Q : Array.isArray(out?.params?.Q) ? out.params.Q : null;

  const snapshotResult = out?.snapshot_result ?? out?.snapshot ?? out?.snapshot_head ?? null;
  const streamResult = out?.stream_result ?? out?.stream ?? out?.stream_head ?? null;

  const snapArr = Array.isArray(snapshotResult) ? snapshotResult : [];
  const streamArr = Array.isArray(streamResult) ? streamResult : [];

  const previewRows =
    queryId === "histogram"
      ? (Array.isArray(streamArr) && streamArr.length ? streamArr : Array.isArray(snapArr) ? snapArr : [])
      : (Array.isArray(streamArr) && streamArr.length ? streamArr : Array.isArray(snapArr) ? snapArr : []);

  // verifier
  const normalizedInput = receiptInput.trim().toLowerCase();
  const normalizedDrift = (drift || "").trim().toLowerCase();
  const receiptMatch =
    normalizedInput.length >= 8 && normalizedDrift.length >= 8 && normalizedInput === normalizedDrift;

  const receiptBadge = boolBadge(normalizedInput.length === 0 ? null : receiptMatch);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {/* Header + controls */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#111827" }}>v44 — SQL on Streams (Queryable Compression)</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Run SQL-shaped queries directly on compressed delta streams, and ship a receipt that locks correctness.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <select
            value={queryId}
            onChange={(e) => setQueryId(e.target.value as any)}
            style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#fff",
              fontSize: 11,
            }}
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
            <label key={label} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
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
                style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
              />
            </label>
          ))}

          <button
            type="button"
            onClick={() => setShowExamples((s) => !s)}
            style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#fff",
              color: "#111827",
              fontSize: 11,
              fontWeight: 900,
              cursor: "pointer",
            }}
            title="Toggle presets"
          >
            Examples
          </button>

          <button
            type="button"
            onClick={run}
            disabled={busy}
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid " + (busy ? "#e5e7eb" : "#111827"),
              background: busy ? "#f9fafb" : "#111827",
              color: busy ? "#6b7280" : "#fff",
              fontSize: 11,
              fontWeight: 900,
              cursor: busy ? "default" : "pointer",
            }}
          >
            {busy ? "Running…" : "Run"}
          </button>
        </div>
      </div>

      {showExamples ? (
        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Presets</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
            {EXAMPLES.map((ex) => (
              <button
                key={ex.label}
                type="button"
                onClick={() => {
                  setQueryId(ex.queryId);
                  setN(ex.n);
                  setTurns(ex.turns);
                  setMuts(ex.muts);
                  setK(ex.k);
                  setSeed(ex.seed);
                }}
                style={{
                  padding: "6px 10px",
                  borderRadius: 999,
                  border: "1px solid #e5e7eb",
                  background: "#f9fafb",
                  color: "#111827",
                  fontSize: 11,
                  fontWeight: 900,
                  cursor: "pointer",
                }}
              >
                {ex.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {err ? <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      {/* Seller container (pitch) */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
          🎯 SQL-shaped analytics on compressed streams (projection + group-by)
        </div>
        <div style={{ fontSize: 11, color: "#374151", marginTop: 8, lineHeight: 1.55 }}>
          <b>What this demo proves:</b> You can run common “dashboard queries” directly on a compressed delta stream and still produce a{" "}
          <b>verifiable receipt</b>.
          <br />
          <br />
          <b>Query modes:</b>
          <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
            <li>
              <b>Projection</b> — <code>SELECT idx,value WHERE idx IN Q</code> (panel pulls specific metrics fast).
            </li>
            <li>
              <b>Histogram</b> — <code>GROUP BY (value % 256) COUNT(*)</code> (rollups / distributions without scanning raw snapshots).
            </li>
          </ul>
          <div style={{ marginTop: 10 }}>
            <b>Trust model:</b> snapshot result vs stream result must match (<code>query_ok</code>), and the whole run is bound into{" "}
            <code> drift_sha256</code> so any verifier can recompute and confirm the same answer.
          </div>
        </div>
      </div>

      {/* Dashboard: charts + stats */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: 10, alignItems: "start" }}>
        {/* left: result chart (query-dependent) */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {queryId === "histogram" ? (
            <HistogramChart rows={previewRows} />
          ) : (
            <ProjectionSpark rows={previewRows} />
          )}

          {wire || gz ? <BytesCompareChart wire={wire} gz={gz} /> : null}
        </div>

        {/* right: stats tiles */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <StatTile
            label="Correctness"
            value={
              <span
                style={{
                  padding: "2px 8px",
                  borderRadius: 999,
                  border: `1px solid ${correctnessBadge.bd}`,
                  background: correctnessBadge.bg,
                  color: correctnessBadge.fg,
                  fontSize: 11,
                  fontWeight: 900,
                }}
              >
                {correctnessBadge.label}
              </span>
            }
            sub="snapshot vs stream"
          />
          <StatTile label="Query time" value={qMs != null ? `${Number(qMs).toFixed(2)} ms` : "—"} sub="if backend returns timing" />
          <StatTile label="Stream size" value={wire ? bytes(wire) : "—"} sub="WirePack total bytes" />
          <StatTile label="gzip size" value={gz ? bytes(gz) : "—"} sub="snapshot baseline" />
          <StatTile
            label="Compression"
            value={factor ? `~${factor.toFixed(1)}×` : "—"}
            sub={pctSaved != null ? `${pctSaved.toFixed(1)}% less` : "—"}
          />
          <StatTile label="Bytes / op" value={bytesPerOp != null ? `${bytesPerOp.toFixed(2)} B` : "—"} sub={`${ops} ops`} />
          <StatTile label="Template" value={templateBytes ? bytes(templateBytes) : "—"} sub="one-time" />
          <StatTile label="Delta total" value={deltaBytesTotal ? bytes(deltaBytesTotal) : "—"} sub="all deltas" />
        </div>
      </div>

      {/* Receipt verifier */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipt verifier</div>
          <div
            style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: `1px solid ${receiptBadge.bd}`,
              background: receiptBadge.bg,
              color: receiptBadge.fg,
              fontSize: 11,
              fontWeight: 900,
            }}
          >
            {receiptBadge.label}
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 10, alignItems: "center" }}>
          <input
            value={receiptInput}
            onChange={(e) => setReceiptInput(e.target.value)}
            placeholder="Paste drift_sha256 here to verify…"
            style={{
              flex: "1 1 420px",
              padding: "10px 12px",
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              fontSize: 12,
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            }}
          />
          <button
            type="button"
            onClick={() => setReceiptInput(drift || "")}
            style={{
              padding: "8px 10px",
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              color: "#111827",
              fontSize: 11,
              fontWeight: 900,
              cursor: "pointer",
            }}
            title="Copy current drift into the verifier input"
          >
            Use current drift
          </button>
        </div>

        <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280", lineHeight: 1.55 }}>
          <div>
            drift_sha256 (from run): <code style={{ color: "#111827" }}>{drift || "—"}</code>
          </div>
          <div style={{ marginTop: 4 }}>
            Any party can recompute this hash from the same stream + params. Match = “query result is provably the same.”
          </div>
        </div>
      </div>

      {/* Receipt + outputs (same “receipt-shaped” vibe as v32) */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, alignItems: "start" }}>
        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipt</div>
          <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
            <div>query_ok: <code>{out ? String(queryOk) : "—"}</code></div>
            <div>result_sha256: <code>{resultSha || "—"}</code></div>
            <div>drift_sha256: <code>{drift || "—"}</code></div>
            <div>LEAN_OK: <code>{leanOk ?? "—"}</code></div>
          </div>
        </div>

        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Outputs (truncated)</div>
          <pre style={{ marginTop: 8, fontSize: 11, overflow: "auto", maxHeight: 360, whiteSpace: "pre-wrap" }}>
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
                  2
                )
              : "Run to populate outputs."}
          </pre>
        </div>
      </div>

      {/* Raw (full width, like v32) */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Raw response</div>
        <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>
          {out ? JSON.stringify(out, null, 2) : "—"}
        </pre>
      </div>

      {/* Endpoint note */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10, fontSize: 11, color: "#6b7280" }}>
        Endpoints tried:
        <div style={{ marginTop: 6 }}>
          <code>POST /api/wirepack/v44/run</code> → fallback <code>POST /api/wirepack/v46/run</code>
        </div>
      </div>
    </div>
  );
}