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
  if (ok === null) return { label: "—", color: "#6b7280", bg: "#f9fafb", bd: "#e5e7eb" };
  return ok
    ? { label: "OK", color: "#065f46", bg: "#ecfdf5", bd: "#a7f3d0" }
    : { label: "FAIL", color: "#991b1b", bg: "#fef2f2", bd: "#fecaca" };
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

function svgSteps(opts: {
  n: number;
  l: number;
  r: number;
  steps: number;
  maxSteps: number;
  height?: number;
}) {
  const { n, l, r, steps, maxSteps, height = 170 } = opts;
  const W = 900;
  const H = height;
  const pad = 18;
  const plotW = W - pad * 2;
  const plotH = H - pad * 2;

  const frac = maxSteps > 0 ? Math.max(0, Math.min(1, steps / maxSteps)) : 0;

  const rangeStart = n > 0 ? Math.max(0, Math.min(1, l / Math.max(1, n - 1))) : 0;
  const rangeEnd = n > 0 ? Math.max(0, Math.min(1, r / Math.max(1, n - 1))) : 0;

  const x0 = pad;
  const y0 = pad;
  const x1 = pad + plotW;
  const y1 = pad + plotH;

  const rx0 = x0 + rangeStart * plotW;
  const rx1 = x0 + rangeEnd * plotW;

  const barW = Math.max(6, Math.round(frac * plotW));
  const barX = x0;
  const barY = y0 + Math.round(plotH * 0.15);
  const barH = Math.round(plotH * 0.22);

  const cap = 10;
  const ticks = [0.25, 0.5, 0.75, 1].map((t) => {
    const y = y0 + (1 - t) * plotH;
    return <line key={t} x1={x0} y1={y} x2={x1} y2={y} stroke="#f3f4f6" />;
  });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="Range sum work graph">
      <rect x={0} y={0} width={W} height={H} rx={16} ry={16} fill="#fff" />
      {ticks}
      <rect x={x0} y={y0} width={plotW} height={plotH} rx={12} ry={12} fill="transparent" stroke="#e5e7eb" />

      {/* Range highlight */}
      <rect
        x={Math.min(rx0, rx1)}
        y={y0 + plotH * 0.58}
        width={Math.max(2, Math.abs(rx1 - rx0))}
        height={plotH * 0.22}
        rx={12}
        ry={12}
        fill="#f9fafb"
        stroke="#e5e7eb"
      />
      <text x={x0} y={y0 + plotH * 0.94} fontSize={11} fill="#6b7280">
        index 0
      </text>
      <text x={x1} y={y0 + plotH * 0.94} fontSize={11} fill="#6b7280" textAnchor="end">
        index {n - 1}
      </text>

      {/* Work bar */}
      <rect x={barX} y={barY} width={plotW} height={barH} rx={12} ry={12} fill="#f9fafb" stroke="#e5e7eb" />
      <rect x={barX} y={barY} width={barW} height={barH} rx={12} ry={12} fill="#eef2ff" stroke="#c7d2fe" />
      <line x1={barX + plotW} y1={barY - cap} x2={barX + plotW} y2={barY + barH + cap} stroke="#e5e7eb" />

      <text x={barX} y={barY - 6} fontSize={11} fill="#6b7280">
        Work (Fenwick steps) vs bound
      </text>
      <text x={barX + plotW} y={barY - 6} fontSize={11} fill="#6b7280" textAnchor="end">
        bound
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

  // “seller panel” knobs (narrative framing)
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
      // narrowRange
      const mid = Math.floor(n / 2);
      setL(Math.max(0, mid - 8));
      setR(Math.min(n - 1, mid + 8));
    }
  }

  const inv = out?.invariants || {};
  const b = out?.bytes || {};
  const receipts = out?.receipts || {};

  const leanOk =
    receipts?.LEAN_OK === 1 || receipts?.LEAN_OK === true
      ? true
      : receipts?.LEAN_OK === 0
        ? false
        : null;
  const leanTri = tri(leanOk);

  const rangeOk = typeof inv?.range_ok === "boolean" ? inv.range_ok : null;
  const rangeTri = tri(rangeOk);

  const workLogOk = Boolean(inv?.work_scales_with_logN) || Boolean(inv?.work_scales_with_log_n);
  const workTri = tri(typeof workLogOk === "boolean" ? workLogOk : null);

  const rangeLen =
    out?.params?.l != null && out?.params?.r != null
      ? Number(out.params.r) - Number(out.params.l) + 1
      : Math.max(0, r - l + 1);

  const driftSha = receipts?.drift_sha256 || out?.drift_sha256 || "—";

  const wire_total_bytes = b?.wire_total_bytes ?? b?.delta_bytes_total ?? 0;
  const ops_total = b?.ops_total ?? (turns * muts);
  const bytes_per_op = Number(b?.bytes_per_op ?? (ops_total ? Number(wire_total_bytes || 0) / ops_total : 0));

  // work “graph” inputs (best-effort across possible backend key names)
  const log2n = Math.log2(Math.max(2, Number(n || 2)));
  const bound = Math.ceil(8 * log2n); // “small multiple of log2(n)” — visual bound, not a proof
  const measuredSteps =
    Number(inv?.fenwick_steps ?? inv?.work_steps ?? inv?.sum_steps ?? inv?.steps ?? inv?.fenwick_sum_steps ?? 0) || 0;

  // seller fanout framing
  const fanoutBytes = Number(wire_total_bytes || 0) * Math.max(0, Number(buyers || 0));
  const estRevenue = Math.max(0, Number(buyers || 0)) * Math.max(0, Number(price || 0));

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
            v33 — Range sums (L..R){" "}
            <span style={{ fontSize: 11, fontWeight: 900, color: "#6b7280" }}>· seller-grade demo</span>
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 3, maxWidth: 860 }}>
            Interval analytics on a delta stream: maintain a Fenwick tree with <code>delta = (new - old)</code> so a range sum is{" "}
            <b>O(log n)</b>, not a scan — and lock it with a receipt.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "5px 10px",
              borderRadius: 999,
              border: "1px solid " + leanTri.bd,
              background: leanTri.bg,
              color: leanTri.color,
              fontSize: 11,
              fontWeight: 900,
              whiteSpace: "nowrap",
            }}
            title="Server reports LEAN_OK for invariants verification"
          >
            LEAN: {leanTri.label}
          </div>

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

      {/* 3-column “full demo” */}
      <div
        style={{
          marginTop: 12,
          display: "grid",
          gridTemplateColumns: "minmax(260px, 320px) minmax(420px, 1fr) minmax(260px, 340px)",
          gap: 12,
        }}
      >
        {/* Seller panel */}
        <div style={{ ...cardStyle() }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Seller panel</div>
            <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900 }}>interval query framing</div>
          </div>
          <div style={{ marginTop: 8, ...miniText() }}>
            Treat the stream as “inventory counts per SKU / region”. Buyers ask: “what’s the total in this window?” without pulling state.
          </div>

          <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
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

          <div style={{ marginTop: 12, borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
            <div style={{ ...miniLabel() }}>What the seller “ships”</div>
            <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr", gap: 6, fontSize: 11, color: "#374151" }}>
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

          <div style={{ marginTop: 10, borderTop: "1px solid #f3f4f6", paddingTop: 10 }}>
            <div style={{ ...miniLabel() }}>Endpoint</div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              <code>POST /api/wirepack/v33/run</code>
            </div>
          </div>
        </div>

        {/* Main graph + controls */}
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
                  // keep L/R valid
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
                range_ok: <b style={{ color: rangeTri.color }}>{rangeTri.label}</b>
                {"  "}· work_scales_with_logN: <b style={{ color: workTri.color }}>{workTri.label}</b>
                {"  "}· LEAN: <b style={{ color: leanTri.color }}>{leanTri.label}</b>
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              {out ? (
                <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", overflow: "hidden" }}>
                  {svgSteps({
                    n,
                    l: out?.params?.l ?? l,
                    r: out?.params?.r ?? r,
                    steps: measuredSteps || 0,
                    maxSteps: bound,
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

            <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                <div style={{ ...miniLabel() }}>Range</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  <b style={{ color: "#111827" }}>
                    [{out?.params?.l ?? l}..{out?.params?.r ?? r}]
                  </b>{" "}
                  <span style={{ color: "#6b7280" }}>len {rangeLen}</span>
                </div>
              </div>
              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                <div style={{ ...miniLabel() }}>Measured steps</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  <b style={{ color: "#111827" }}>{measuredSteps ? String(measuredSteps) : "—"}</b>{" "}
                  <span style={{ color: "#6b7280" }}>bound ≈ {bound}</span>
                </div>
              </div>
              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                <div style={{ ...miniLabel() }}>Wire efficiency</div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                  <b style={{ color: "#111827" }}>{bytes(Number(wire_total_bytes || 0))}</b>{" "}
                  <span style={{ color: "#6b7280" }}>
                    ({bytes_per_op ? `${bytes_per_op.toFixed(2)} B/op` : "—"})
                  </span>
                </div>
              </div>
            </div>

            <div style={{ marginTop: 10, fontSize: 10, color: "#6b7280" }}>
              The lower band shows the queried interval on <code>[0..n-1]</code>. The upper bar shows measured Fenwick work vs a{" "}
              <code>~8·log2(n)</code> visual bound (best-effort; depends on backend counters).
            </div>
          </div>

          {/* Receipts + values */}
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
                    delta_bytes_total: <b style={{ color: "#111827" }}>{b?.delta_bytes_total == null ? "—" : bytes(Number(b.delta_bytes_total))}</b>{" "}
                    <span style={{ color: "#6b7280" }}>{b?.delta_bytes_total != null ? `(${b.delta_bytes_total} B)` : ""}</span>
                  </div>
                  <div>
                    wire_total_bytes: <b style={{ color: "#111827" }}>{b?.wire_total_bytes == null ? "—" : bytes(Number(b.wire_total_bytes))}</b>{" "}
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

        {/* What’s special explainer */}
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
                Each mutation updates one index. Fenwick tree update is <code>+delta</code> to a logarithmic set of nodes. No full
                rebuild, no full snapshot.
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
              <div style={{ ...miniLabel() }}>Reproducible command</div>
              <pre style={{ marginTop: 8, fontSize: 10, color: "#111827", whiteSpace: "pre-wrap" }}>{curl}</pre>
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
          <span style={{ color: "#6b7280" }}>· ops {String(ops_total)} · bytes/op {bytes_per_op ? bytes_per_op.toFixed(2) : "—"}</span>
        </div>
      </div>
    </div>
  );
};