// V33RangeSumsDemo.tsx
// ============================================================
// v33 — Range sums (L..R) · seller-grade demo  ✅ FULL REPLACE
// Layout update: horizontal seller bar + 2-column body (more room for demo)
// Semantics update: work bar shows Fenwick QUERY cost vs ~O(log n) bound
// Bytes update: adds Like-for-like (truthful) block if backend provides fields
// ============================================================

import React, { useMemo, useState } from "react";

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

async function fetchJson(url: string, body: any, timeoutMs = 20000) {
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

function tri(ok: boolean | null) {
  if (ok === null) return { label: "—", color: "#6b7280", bg: "#f9fafb", bd: "#e5e7eb", icon: "•" };
  return ok
    ? { label: "OK", color: "#065f46", bg: "#ecfdf5", bd: "#a7f3d0", icon: "✅" }
    : { label: "FAIL", color: "#991b1b", bg: "#fef2f2", bd: "#fecaca", icon: "⚠️" };
}

function Badge(props: { ok: boolean | null; label: string }) {
  const t = tri(props.ok);
  return (
    <span
      style={{
        padding: "5px 10px",
        borderRadius: 999,
        border: `1px solid ${t.bd}`,
        background: t.bg,
        color: t.color,
        fontSize: 11,
        fontWeight: 900,
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        whiteSpace: "nowrap",
      }}
      title={props.label}
    >
      <span style={{ fontSize: 12 }}>{t.icon}</span>
      {props.label}
    </span>
  );
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function pillStyle(active: boolean) {
  return {
    padding: "6px 10px",
    borderRadius: 999,
    border: "1px solid " + (active ? "#111827" : "#e5e7eb"),
    background: active ? "#111827" : "#fff",
    color: active ? "#fff" : "#111827",
    fontSize: 11,
    fontWeight: 900 as const,
    cursor: "pointer",
    whiteSpace: "nowrap" as const,
  };
}

function cardStyle() {
  return { borderRadius: 16, border: "1px solid #e5e7eb", background: "#fff", padding: 12 };
}

function miniLabel() {
  return { fontSize: 11, color: "#374151", fontWeight: 900 as const };
}

function miniText() {
  return { fontSize: 11, color: "#6b7280", lineHeight: 1.45 };
}

function kvBox() {
  return { borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 };
}

function asNum(x: any, fb: number) {
  const v = Number(x);
  return Number.isFinite(v) ? v : fb;
}

function svgRangeWork(opts: {
  n: number;
  l: number;
  r: number;
  steps: number;
  bound: number;
  height?: number;
}) {
  const { n, l, r, steps, bound, height = 170 } = opts;
  const W = 900;
  const H = height;
  const pad = 18;
  const plotW = W - pad * 2;
  const plotH = H - pad * 2;

  const clamp01 = (z: number) => Math.max(0, Math.min(1, z));
  const frac = bound > 0 ? clamp01(steps / bound) : 0;

  const nn = Math.max(1, Number(n || 1));
  const ll = clamp(Number(l || 0), 0, nn - 1);
  const rr = clamp(Number(r || 0), 0, nn - 1);

  const rangeStart = nn > 1 ? clamp01(ll / (nn - 1)) : 0;
  const rangeEnd = nn > 1 ? clamp01(rr / (nn - 1)) : 0;

  const x0 = pad;
  const y0 = pad;
  const x1 = pad + plotW;

  const rx0 = x0 + Math.min(rangeStart, rangeEnd) * plotW;
  const rx1 = x0 + Math.max(rangeStart, rangeEnd) * plotW;

  const barY = y0 + Math.round(plotH * 0.12);
  const barH = Math.round(plotH * 0.22);
  const barW = frac > 0 ? Math.max(2, Math.round(frac * plotW)) : 0;

  const bandY = y0 + Math.round(plotH * 0.58);
  const bandH = Math.round(plotH * 0.22);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="Range sum work graph">
      <rect x={0} y={0} width={W} height={H} rx={16} ry={16} fill="#fff" />
      <rect x={x0} y={y0} width={plotW} height={plotH} rx={12} ry={12} fill="transparent" stroke="#e5e7eb" />

      {/* Work bar */}
      <text x={x0} y={barY - 6} fontSize={11} fill="#6b7280">
        Work (Fenwick QUERY steps) vs bound
      </text>
      <text x={x1} y={barY - 6} fontSize={11} fill="#6b7280" textAnchor="end">
        bound
      </text>
      <rect x={x0} y={barY} width={plotW} height={barH} rx={12} ry={12} fill="#f9fafb" stroke="#e5e7eb" />
      {barW > 0 ? (
        <rect x={x0} y={barY} width={barW} height={barH} rx={12} ry={12} fill="#eef2ff" stroke="#c7d2fe" />
      ) : null}
      <line x1={x1} y1={barY - 10} x2={x1} y2={barY + barH + 10} stroke="#e5e7eb" />
      <text x={x0} y={barY + barH + 14} fontSize={11} fill="#6b7280">
        steps={Number.isFinite(steps) ? steps : "—"} · bound≈{Number.isFinite(bound) ? bound : "—"}
      </text>

      {/* Range highlight */}
      <text x={x0} y={bandY - 6} fontSize={11} fill="#6b7280">
        Queried interval on [0..n-1]
      </text>
      <rect x={x0} y={bandY} width={plotW} height={bandH} rx={12} ry={12} fill="#f9fafb" stroke="#e5e7eb" />
      <rect x={rx0} y={bandY} width={Math.max(2, rx1 - rx0)} height={bandH} rx={12} ry={12} fill="#ecfeff" stroke="#a5f3fc" />
      <text x={x0} y={bandY + bandH + 14} fontSize={11} fill="#6b7280">
        index 0
      </text>
      <text x={x1} y={bandY + bandH + 14} fontSize={11} fill="#6b7280" textAnchor="end">
        index {nn - 1}
      </text>
    </svg>
  );
}

export const V33RangeSumsDemo: React.FC = () => {
  // wirepack params
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(64);
  const [muts, setMuts] = useState(3);
  const [l, setL] = useState(0);
  const [r, setR] = useState(127);

  // seller framing
  const [sellerName, setSellerName] = useState("Seller");
  const [sku, setSku] = useState("SKU-GLYPH-33");
  const [buyers, setBuyers] = useState(2500);
  const [price, setPrice] = useState(29);
  const [showRaw, setShowRaw] = useState(false);

  // run state
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<any | null>(null);

  const body = useMemo(() => ({ seed, n, turns, muts, l, r }), [seed, n, turns, muts, l, r]);

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);
    try {
      const { ok, status, json } = await fetchJson("/api/wirepack/v33/run", body, 30000);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setOut(json);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function applyPreset(which: "balanced" | "stress" | "tiny" | "wideRange" | "narrowRange") {
    if (which === "balanced") {
      setSeed(1337);
      setN(4096);
      setTurns(64);
      setMuts(3);
      setL(0);
      setR(127);
    } else if (which === "stress") {
      setSeed(9001);
      setN(65536);
      setTurns(256);
      setMuts(6);
      setL(1024);
      setR(8191);
    } else if (which === "tiny") {
      setSeed(42);
      setN(1024);
      setTurns(16);
      setMuts(2);
      setL(0);
      setR(31);
    } else if (which === "wideRange") {
      setL(0);
      setR(Math.max(0, n - 1));
    } else {
      const mid = Math.floor(n / 2);
      setL(Math.max(0, mid - 8));
      setR(Math.min(n - 1, mid + 8));
    }
  }

  // parse outputs
  const inv = out?.invariants || {};
  const b = out?.bytes || {};
  const receipts = out?.receipts || {};

  const leanOkVal = receipts?.LEAN_OK;
  const leanOk = leanOkVal == null ? null : Boolean(Number(leanOkVal));

  const rangeOk = typeof inv?.range_ok === "boolean" ? inv.range_ok : inv?.range_ok == null ? null : Boolean(inv.range_ok);
  const workOkRaw = inv?.work_scales_with_logN ?? inv?.work_scales_with_log_n;
  const workOk = typeof workOkRaw === "boolean" ? workOkRaw : workOkRaw == null ? null : Boolean(workOkRaw);

  const driftSha = typeof receipts?.drift_sha256 === "string" ? receipts.drift_sha256 : out?.drift_sha256 || "—";

  const nn = Math.max(1, Number(out?.params?.n ?? n ?? 1));
  const ll = clamp(Number(out?.params?.l ?? l ?? 0), 0, nn - 1);
  const rr = clamp(Number(out?.params?.r ?? r ?? 0), 0, nn - 1);
  const rangeLen = Math.max(0, rr - ll + 1);

  // bytes + ops
  const ops_total = asNum(b?.ops_total, (Number(turns || 0) * Number(muts || 0)) || 0);
  const wire_total_bytes = asNum(b?.wire_total_bytes ?? b?.delta_bytes_total, 0);
  const bytes_per_op = asNum(b?.bytes_per_op, ops_total ? wire_total_bytes / ops_total : 0);

  // work counters (best-effort)
  const logN = asNum(inv?.logN, Math.ceil(Math.log2(Math.max(2, nn))));
  const scanSteps = asNum(inv?.scan_steps, NaN);
  const fenwickQuerySteps = asNum(inv?.fenwick_query_steps ?? inv?.fenwick_steps, NaN);
  const fenwickUpdateStepsTotal = asNum(inv?.fenwick_update_steps_total, NaN);

  // graph uses QUERY steps (the O(log n) story)
  const measuredSteps = Number.isFinite(fenwickQuerySteps) ? fenwickQuerySteps : 0;

  // Visual query bound: ~4*logN (safe headroom)
  const bound = Math.max(1, Math.ceil(4 * logN));

  // seller fanout framing
  const fanoutBytes = Math.max(0, Number(buyers || 0)) * Math.max(0, Number(wire_total_bytes || 0));
  const estRevenue = Math.max(0, Number(buyers || 0)) * Math.max(0, Number(price || 0));

  // like-for-like (truthful) if backend provides
  const raw_full_snapshot_bytes = asNum(b?.raw_full_snapshot_bytes, NaN);
  const gzip_full_snapshot_bytes = asNum(b?.gzip_full_snapshot_bytes, NaN);
  const raw_query_answer_bytes = asNum(b?.raw_query_answer_bytes, NaN);
  const gzip_query_answer_bytes = asNum(b?.gzip_query_answer_bytes, NaN);

  const hasLikeForLike =
    Number.isFinite(gzip_full_snapshot_bytes) && Number.isFinite(gzip_query_answer_bytes) && gzip_full_snapshot_bytes > 0;

  const savedBytes = hasLikeForLike ? gzip_full_snapshot_bytes - gzip_query_answer_bytes : NaN;
  const savedPct = hasLikeForLike ? (savedBytes / gzip_full_snapshot_bytes) * 100 : NaN;

  const curl = useMemo(() => {
    const body = JSON.stringify({ seed, n, turns, muts, l, r });
    return `curl -sS -X POST http://127.0.0.1:8787/api/wirepack/v33/run \\
  -H 'content-type: application/json' \\
  -d '${body}' | jq`;
  }, [seed, n, turns, muts, l, r]);

  async function copyCurl() {
    try {
      await navigator.clipboard.writeText(curl);
    } catch {
      // ignore
    }
  }

  return (
    <div style={{ ...cardStyle(), padding: 14 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 900, color: "#111827" }}>
            v33 — Range sums (L..R) <span style={{ fontSize: 11, fontWeight: 900, color: "#6b7280" }}>· seller-grade demo</span>
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 3, maxWidth: 900 }}>
            Interval analytics on a delta stream: maintain a Fenwick tree with <code>delta = (new - old)</code> so a range sum is{" "}
            <b>O(log n)</b>, not a scan — and lock it with a receipt.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <Badge ok={leanOk} label={`LEAN: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />
          <button
            type="button"
            onClick={run}
            disabled={busy}
            style={{
              padding: "7px 12px",
              borderRadius: 999,
              border: "1px solid " + (busy ? "#e5e7eb" : "#111827"),
              background: busy ? "#f3f4f6" : "#111827",
              color: busy ? "#6b7280" : "#fff",
              fontSize: 11,
              fontWeight: 900,
              cursor: busy ? "not-allowed" : "pointer",
            }}
          >
            {busy ? "Running…" : "Run"}
          </button>
        </div>
      </div>

      {/* Presets + quick actions */}
      <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: 11, color: "#6b7280", fontWeight: 900 }}>Presets</span>
        <button type="button" onClick={() => applyPreset("balanced")} style={pillStyle(false)}>
          Balanced
        </button>
        <button type="button" onClick={() => applyPreset("stress")} style={pillStyle(false)}>
          Stress
        </button>
        <button type="button" onClick={() => applyPreset("tiny")} style={pillStyle(false)}>
          Tiny
        </button>
        <button type="button" onClick={() => applyPreset("wideRange")} style={pillStyle(false)}>
          Wide range
        </button>
        <button type="button" onClick={() => applyPreset("narrowRange")} style={pillStyle(false)}>
          Narrow range
        </button>

        <span style={{ width: 1, height: 18, background: "#e5e7eb", marginLeft: 6, marginRight: 6 }} />

        <button type="button" onClick={copyCurl} style={pillStyle(false)} title="Copy a reproducible curl">
          Copy curl
        </button>

        <label style={{ display: "inline-flex", gap: 8, alignItems: "center", fontSize: 11, fontWeight: 900, color: "#111827" }}>
          <input type="checkbox" checked={showRaw} onChange={(e) => setShowRaw(e.target.checked)} />
          Raw JSON
        </label>
      </div>

      {/* ============================================================
          HORIZONTAL SELLER BAR  ✅ NEW
         ============================================================ */}
      <div
        style={{
          marginTop: 12,
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#fff",
          padding: 12,
          display: "grid",
          gridTemplateColumns: "1.2fr 1.2fr 0.9fr 0.9fr 1.6fr",
          gap: 10,
          alignItems: "start",
        }}
      >
        {/* Left: framing */}
        <div>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Seller panel</div>
            <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900 }}>interval query framing</div>
          </div>
          <div style={{ marginTop: 8, ...miniText() }}>
            Treat the stream as “inventory counts per SKU / region”. Buyers ask: “what’s the total in this window?” without pulling
            state.
          </div>
          <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280" }}>
            endpoint: <code>POST /api/wirepack/v33/run</code>
          </div>
        </div>

        {/* Inputs */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <label style={{ fontSize: 11, color: "#374151" }}>
            Seller name
            <input
              value={sellerName}
              onChange={(e) => setSellerName(e.target.value)}
              style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
            />
          </label>
          <label style={{ fontSize: 11, color: "#374151" }}>
            SKU
            <input
              value={sku}
              onChange={(e) => setSku(e.target.value)}
              style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
            />
          </label>
          <label style={{ fontSize: 11, color: "#374151" }}>
            Buyers
            <input
              type="number"
              value={buyers}
              min={0}
              onChange={(e) => setBuyers(Math.max(0, Number(e.target.value) || 0))}
              style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
            />
          </label>
          <label style={{ fontSize: 11, color: "#374151" }}>
            Price (€)
            <input
              type="number"
              value={price}
              min={0}
              onChange={(e) => setPrice(Math.max(0, Number(e.target.value) || 0))}
              style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
            />
          </label>
        </div>

        {/* Ship metrics */}
        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
          <div style={{ ...miniLabel() }}>What the seller “ships”</div>
          <div style={{ marginTop: 8, display: "grid", gap: 6, fontSize: 11, color: "#374151" }}>
            <div>
              Update bytes (one buyer): <b style={{ color: "#111827" }}>{bytes(Number(wire_total_bytes || 0))}</b>
            </div>
            <div>
              Fanout bytes (all buyers): <b style={{ color: "#111827" }}>{bytes(fanoutBytes)}</b>
            </div>
            <div>
              Ops touched: <b style={{ color: "#111827" }}>{String(ops_total)}</b>{" "}
              <span style={{ color: "#6b7280" }}>({bytes_per_op ? `${bytes_per_op.toFixed(2)} B/op` : "—"})</span>
            </div>
            <div>
              Est. gross revenue: <b style={{ color: "#111827" }}>{estRevenue.toLocaleString()}</b>{" "}
              <span style={{ color: "#6b7280" }}>({buyers.toLocaleString()} buyers)</span>
            </div>
          </div>
        </div>

        {/* Like-for-like (truthful) */}
        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
          <div style={{ ...miniLabel() }}>Like-for-like (truthful)</div>
          {hasLikeForLike ? (
            <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              <div>
                gzip(full snapshot): <b style={{ color: "#111827" }}>{bytes(gzip_full_snapshot_bytes)}</b>{" "}
                <span style={{ color: "#6b7280" }}>{Number.isFinite(raw_full_snapshot_bytes) ? `(raw ${bytes(raw_full_snapshot_bytes)})` : ""}</span>
              </div>
              <div>
                gzip(answer + receipt): <b style={{ color: "#111827" }}>{bytes(gzip_query_answer_bytes)}</b>{" "}
                <span style={{ color: "#6b7280" }}>{Number.isFinite(raw_query_answer_bytes) ? `(raw ${bytes(raw_query_answer_bytes)})` : ""}</span>
              </div>
              <div style={{ marginTop: 6 }}>
                Saved:{" "}
                <b style={{ color: "#111827" }}>
                  {bytes(savedBytes)} ({savedPct.toFixed(2)}%)
                </b>
              </div>
            </div>
          ) : (
            <div style={{ marginTop: 8, fontSize: 11, color: "#6b7280", lineHeight: 1.5 }}>
              Baseline comparison unavailable (backend didn’t return{" "}
              <code>gzip_full_snapshot_bytes</code> / <code>gzip_query_answer_bytes</code>).
            </div>
          )}
        </div>

        {/* Repro command */}
        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
          <div style={{ ...miniLabel() }}>Reproducible command</div>
          <pre style={{ marginTop: 8, fontSize: 10, color: "#111827", whiteSpace: "pre-wrap" }}>{curl}</pre>
        </div>
      </div>

      {/* ============================================================
          2-COLUMN BODY  ✅ NEW
         ============================================================ */}
      <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "minmax(620px, 1fr) minmax(300px, 360px)", gap: 12 }}>
        {/* LEFT: Demo (wide) */}
        <div style={{ ...cardStyle() }}>
          {/* Controls */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, minmax(0, 1fr))", gap: 8 }}>
            <label style={{ fontSize: 11, color: "#374151" }}>
              seed
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value) || 0)}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>
            <label style={{ fontSize: 11, color: "#374151" }}>
              n
              <input
                type="number"
                value={n}
                min={256}
                max={65536}
                onChange={(e) => {
                  const nn = clamp(Number(e.target.value) || 4096, 256, 65536);
                  setN(nn);
                  setL((prev) => clamp(prev, 0, nn - 1));
                  setR((prev) => clamp(prev, 0, nn - 1));
                }}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>
            <label style={{ fontSize: 11, color: "#374151" }}>
              turns
              <input
                type="number"
                value={turns}
                min={1}
                max={4096}
                onChange={(e) => setTurns(clamp(Number(e.target.value) || 64, 1, 4096))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>
            <label style={{ fontSize: 11, color: "#374151" }}>
              muts
              <input
                type="number"
                value={muts}
                min={1}
                max={4096}
                onChange={(e) => setMuts(clamp(Number(e.target.value) || 3, 1, 4096))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>
            <label style={{ fontSize: 11, color: "#374151" }}>
              L
              <input
                type="number"
                value={l}
                min={0}
                max={n - 1}
                onChange={(e) => {
                  const ll = clamp(Number(e.target.value) || 0, 0, n - 1);
                  setL(ll);
                  setR((rr) => Math.max(rr, ll));
                }}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>
            <label style={{ fontSize: 11, color: "#374151" }}>
              R
              <input
                type="number"
                value={r}
                min={0}
                max={n - 1}
                onChange={(e) => {
                  const rr = clamp(Number(e.target.value) || 0, 0, n - 1);
                  setR(rr);
                  setL((ll) => Math.min(ll, rr));
                }}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>
          </div>

          {err ? <div style={{ marginTop: 10, fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

          {/* Graph */}
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Work + range graph</div>
              <div style={{ fontSize: 11, color: "#374151" }}>
                range_ok: <b style={{ color: tri(rangeOk).color }}>{tri(rangeOk).label}</b>
                {"  "}· work_scales_with_logN: <b style={{ color: tri(workOk).color }}>{tri(workOk).label}</b>
                {"  "}· LEAN: <b style={{ color: tri(leanOk).color }}>{tri(leanOk).label}</b>
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              {out ? (
                <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", overflow: "hidden" }}>
                  {svgRangeWork({
                    n: nn,
                    l: ll,
                    r: rr,
                    steps: measuredSteps,
                    bound,
                    height: 170,
                  })}
                </div>
              ) : (
                <div
                  style={{
                    borderRadius: 16,
                    border: "1px dashed #e5e7eb",
                    background: "#f9fafb",
                    padding: 14,
                    fontSize: 11,
                    color: "#6b7280",
                  }}
                >
                  No output yet — hit <b>Run</b>.
                </div>
              )}
            </div>

            {/* Summary cards */}
            <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <div style={kvBox()}>
                <div style={{ ...miniLabel() }}>Range</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  <b style={{ color: "#111827" }}>
                    [{ll}..{rr}]
                  </b>{" "}
                  <span style={{ color: "#6b7280" }}>len {rangeLen}</span>
                </div>
              </div>

              <div style={kvBox()}>
                <div style={{ ...miniLabel() }}>Work (scan vs Fenwick)</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  scan_steps: <b style={{ color: "#111827" }}>{Number.isFinite(scanSteps) ? String(scanSteps) : "—"}</b>
                </div>
                <div style={{ marginTop: 4, fontSize: 11, color: "#374151" }}>
                  fenwick_query_steps: <b style={{ color: "#111827" }}>{Number.isFinite(fenwickQuerySteps) ? String(fenwickQuerySteps) : "—"}</b>{" "}
                  <span style={{ color: "#6b7280" }}>bound≈{bound}</span>
                </div>
                <div style={{ marginTop: 4, fontSize: 11, color: "#374151" }}>
                  fenwick_update_steps_total:{" "}
                  <b style={{ color: "#111827" }}>{Number.isFinite(fenwickUpdateStepsTotal) ? String(fenwickUpdateStepsTotal) : "—"}</b>
                </div>
                <div style={{ marginTop: 4, fontSize: 11, color: "#6b7280" }}>
                  logN: <b style={{ color: "#111827" }}>{String(logN)}</b>
                </div>
              </div>

              <div style={kvBox()}>
                <div style={{ ...miniLabel() }}>Wire efficiency</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  <b style={{ color: "#111827" }}>{bytes(Number(wire_total_bytes || 0))}</b>{" "}
                  <span style={{ color: "#6b7280" }}>({bytes_per_op ? `${bytes_per_op.toFixed(2)} B/op` : "—"})</span>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 10, fontSize: 10, color: "#6b7280" }}>
              Lower band shows the queried interval on <code>[0..n-1]</code>. Upper bar shows Fenwick <b>query</b> work vs a{" "}
              <code>~O(log n)</code> bound (best-effort; depends on backend counters).
            </div>
          </div>

          {/* Output cards */}
          {out ? (
            <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Result + receipt</div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                  <div>
                    sum_baseline: <code>{String(out?.sum_baseline ?? "—")}</code>
                  </div>
                  <div>
                    sum_stream: <code>{String(out?.sum_stream ?? "—")}</code>
                  </div>
                  <div>
                    final_state_sha256: <code>{String(out?.final_state_sha256 || "—")}</code>
                  </div>
                  <div>
                    drift_sha256: <code>{String(driftSha)}</code>
                  </div>
                </div>
              </div>

              <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Bytes</div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                  <div>
                    ops_total: <b style={{ color: "#111827" }}>{String(b?.ops_total ?? "—")}</b>
                  </div>
                  <div>
                    delta_bytes_total:{" "}
                    <b style={{ color: "#111827" }}>{b?.delta_bytes_total == null ? "—" : bytes(Number(b.delta_bytes_total))}</b>{" "}
                    <span style={{ color: "#6b7280" }}>{b?.delta_bytes_total != null ? `(${b.delta_bytes_total} B)` : ""}</span>
                  </div>
                  <div>
                    wire_total_bytes:{" "}
                    <b style={{ color: "#111827" }}>{b?.wire_total_bytes == null ? "—" : bytes(Number(b.wire_total_bytes))}</b>{" "}
                    <span style={{ color: "#6b7280" }}>{b?.wire_total_bytes != null ? `(${b.wire_total_bytes} B)` : ""}</span>
                  </div>
                  <div style={{ color: "#6b7280" }}>
                    receipts: <code>{JSON.stringify(receipts || {})}</code>
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {out && showRaw ? (
            <div style={{ marginTop: 12, borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Raw response</div>
              <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>
                {JSON.stringify(out, null, 2)}
              </pre>
            </div>
          ) : null}
        </div>

        {/* RIGHT: Explainer (stacked) */}
        <div style={{ ...cardStyle() }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>What’s so special?</div>
            <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900 }}>why v33 matters</div>
          </div>

          <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>1) Interval queries without scanning</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                Range sums are a core analytics primitive. Baseline is <b>O(len)</b>. v33 keeps updates streaming and answers{" "}
                <b>O(log n)</b> using a Fenwick tree.
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                Query: <code>SUM(state[L..R]) = prefix(R) - prefix(L-1)</code>
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>2) Delta updates are additive</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                Each mutation updates one index. Fenwick update is <code>+delta</code> to a logarithmic set of nodes. No full rebuild, no
                full snapshot.
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                Update: <code>delta = new - old</code> then <code>add(i, delta)</code>
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>3) Receipts + LEAN checks</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                The answer is tied to the exact replay via <code>drift_sha256</code> and validated invariants. Downstream can verify
                “same params + same stream ⇒ same sum”.
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                <code>range_ok</code> · <code>work_scales_with_logN</code> · <code>LEAN_OK</code>
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
              <div style={{ ...miniLabel() }}>Seller-grade use cases</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                Sliding window totals, cohort sums, inventory in a region slice, rate-limit windows, partial ledger totals — all
                verifiable and cheap to broadcast.
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.55 }}>
                <div>• “units sold in region [L..R]”</div>
                <div>• “spend last 7 days” over a time-indexed stream</div>
                <div>• “errors in shard window” for operational analytics</div>
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
              <div style={{ ...miniLabel() }}>Endpoint</div>
              <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
                <code>POST /api/wirepack/v33/run</code>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          marginTop: 12,
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 10,
          fontSize: 11,
          color: "#6b7280",
          display: "flex",
          justifyContent: "space-between",
          gap: 10,
          flexWrap: "wrap",
        }}
      >
        <div>
          endpoint: <code>POST /api/wirepack/v33/run</code>
        </div>
        <div>
          wire: <b style={{ color: "#111827" }}>{bytes(Number(wire_total_bytes || 0))}</b>{" "}
          <span style={{ color: "#6b7280" }}>
            · ops {String(ops_total)} · bytes/op {bytes_per_op ? bytes_per_op.toFixed(2) : "—"}
          </span>
        </div>
      </div>
    </div>
  );
};