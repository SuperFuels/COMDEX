import React, { useMemo, useState } from "react";

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

function bytes(n: number) {
  const units = ["B", "KB", "MB", "GB"];
  let v = Number(n || 0),
    i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
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

function svgHistogram(opts: {
  hist: number[];
  height?: number;
  highlight?: number | null;
  onHover?: (i: number | null) => void;
  hovered?: number | null;
  showCdf?: boolean;
}) {
  const { hist, height = 160, highlight = null, onHover, hovered, showCdf } = opts;
  const W = 900; // virtual
  const H = height;
  const pad = 18;
  const plotW = W - pad * 2;
  const plotH = H - pad * 2;
  const n = Math.max(1, hist.length);

  let max = 0;
  let sum = 0;
  for (const v of hist) {
    const x = Number(v || 0);
    max = Math.max(max, x);
    sum += x;
  }
  const maxSafe = Math.max(1, max);

  // bars
  const bw = plotW / n;
  const bars = hist.map((v, i) => {
    const x = pad + i * bw;
    const h = Math.max(2, Math.round((Number(v || 0) / maxSafe) * plotH));
    const y = pad + (plotH - h);
    const isHi = highlight === i;
    const isHover = hovered === i;
    const stroke = isHover ? "#111827" : "#e5e7eb";
    const fill = isHi ? "#eef2ff" : "#f9fafb";
    const fill2 = isHover ? "#e0e7ff" : fill;
    return (
      <rect
        key={i}
        x={x + 2}
        y={y}
        width={Math.max(2, bw - 4)}
        height={h}
        rx={7}
        ry={7}
        fill={fill2}
        stroke={stroke}
        onMouseEnter={() => onHover?.(i)}
        onMouseLeave={() => onHover?.(null)}
        style={{ cursor: "default" }}
      />
    );
  });

  // CDF line (optional)
  let cdfPath = "";
  if (showCdf && sum > 0 && hist.length > 1) {
    let acc = 0;
    const pts: Array<[number, number]> = [];
    for (let i = 0; i < hist.length; i++) {
      acc += Number(hist[i] || 0);
      const p = acc / sum; // 0..1
      const x = pad + (i + 0.5) * bw;
      const y = pad + (1 - p) * plotH;
      pts.push([x, y]);
    }
    cdfPath =
      "M " +
      pts
        .map(([x, y], idx) => `${x.toFixed(2)} ${y.toFixed(2)}${idx === pts.length - 1 ? "" : " L "}`)
        .join("");
  }

  const yTicks = [0.25, 0.5, 0.75, 1].map((t) => {
    const y = pad + (1 - t) * plotH;
    return (
      <g key={t}>
        <line x1={pad} y1={y} x2={W - pad} y2={y} stroke="#f3f4f6" />
      </g>
    );
  });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="Histogram graph">
      <rect x={0} y={0} width={W} height={H} rx={16} ry={16} fill="#fff" />
      {yTicks}
      {/* plot border */}
      <rect x={pad} y={pad} width={plotW} height={plotH} rx={12} ry={12} fill="transparent" stroke="#e5e7eb" />
      {bars}
      {showCdf && cdfPath ? (
        <path d={cdfPath} fill="none" stroke="#111827" strokeWidth={2} opacity={0.75} />
      ) : null}
    </svg>
  );
}

export const V34HistogramDemo: React.FC = () => {
  // wirepack params
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(64);
  const [muts, setMuts] = useState(3);
  const [buckets, setBuckets] = useState(32);
  const [mode, setMode] = useState<"idx_mod" | "val_mod">("idx_mod");

  // “seller panel” (narrative knobs)
  const [sellerName, setSellerName] = useState("Seller");
  const [sku, setSku] = useState("SKU-GLYPH-34");
  const [buyers, setBuyers] = useState(2500);
  const [price, setPrice] = useState(29);
  const [showCdf, setShowCdf] = useState(true);
  const [showRaw, setShowRaw] = useState(false);

  // run state
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<any | null>(null);

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);
    try {
      const body = { seed, n, turns, muts, buckets, mode };
      const { ok, status, json } = await fetchJson("/api/wirepack/v34/run", body, 30000);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setOut(json);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function applyPreset(which: "balanced" | "stress" | "tiny") {
    if (which === "balanced") {
      setSeed(1337);
      setN(4096);
      setTurns(64);
      setMuts(3);
      setBuckets(32);
      setMode("idx_mod");
    } else if (which === "stress") {
      setSeed(9001);
      setN(65536);
      setTurns(256);
      setMuts(6);
      setBuckets(128);
      setMode("val_mod");
    } else {
      setSeed(42);
      setN(1024);
      setTurns(16);
      setMuts(2);
      setBuckets(16);
      setMode("idx_mod");
    }
  }

  const receipt = out?.receipt || {};
  const receipts = out?.receipts || {};
  const inv = receipt?.invariants || out?.invariants || {};
  const b = receipt?.bytes || out?.bytes || {};

  const hist: number[] = Array.isArray(out?.histogram)
    ? out.histogram
    : Array.isArray(receipt?.histogram)
      ? receipt.histogram
      : [];

  const derived = useMemo(() => {
    let max = 0;
    let maxBucket: number | null = null;
    let sum = 0;
    for (let i = 0; i < hist.length; i++) {
      const v = Number(hist[i] || 0);
      sum += v;
      if (v > max) {
        max = v;
        maxBucket = i;
      }
    }
    const mean = hist.length ? sum / hist.length : 0;
    let varSum = 0;
    for (let i = 0; i < hist.length; i++) {
      const v = Number(hist[i] || 0);
      varSum += (v - mean) * (v - mean);
    }
    const stdev = hist.length ? Math.sqrt(varSum / hist.length) : 0;

    // a tiny “skew” score: max/mean (>=1)
    const skew = mean > 0 ? max / mean : 0;

    return { max, maxBucket, sum, mean, stdev, skew };
  }, [hist]);

  const histOk = typeof inv?.hist_ok === "boolean" ? inv.hist_ok : null;
  const histTri = tri(histOk);

  const leanOk =
    receipts?.LEAN_OK === 1 || receipts?.LEAN_OK === true
      ? true
      : receipts?.LEAN_OK === 0
        ? false
        : null;
  const leanTri = tri(leanOk);

  const ops_total = b?.ops_total ?? (turns * muts);
  const wire_total_bytes = b?.wire_total_bytes ?? b?.delta_bytes_total ?? 0;
  const bytes_per_op = Number(b?.bytes_per_op ?? (ops_total ? Number(wire_total_bytes || 0) / ops_total : 0));

  // “seller fanout” story: what would it cost to push this update to buyers?
  const fanoutBytes = Number(wire_total_bytes || 0) * Math.max(0, Number(buyers || 0));
  const estRevenue = Math.max(0, Number(buyers || 0)) * Math.max(0, Number(price || 0));

  const [hovered, setHovered] = useState<number | null>(null);

  const curl = useMemo(() => {
    const body = JSON.stringify({ seed, n, turns, muts, buckets, mode });
    return `curl -sS -X POST http://127.0.0.1:8787/api/wirepack/v34/run \\
  -H 'content-type: application/json' \\
  -d '${body}' | jq`;
  }, [seed, n, turns, muts, buckets, mode]);

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
            v34 — Histogram query (buckets / modulus){" "}
            <span style={{ fontSize: 11, fontWeight: 900, color: "#6b7280" }}>· seller-grade demo</span>
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 3, maxWidth: 820 }}>
            Run a distribution query on the live stream and get a verifiable receipt (drift hash + LEAN check). This layout
            frames it as a “seller pushes updates to many buyers” problem.
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

        <span style={{ width: 1, height: 18, background: "#e5e7eb", marginLeft: 6, marginRight: 6 }} />

        <button type="button" onClick={copyCurl} style={pillStyle(false)} title="Copy a reproducible curl">
          Copy curl
        </button>

        <label style={{ display: "inline-flex", gap: 8, alignItems: "center", fontSize: 11, fontWeight: 900, color: "#111827" }}>
          <input type="checkbox" checked={showCdf} onChange={(e) => setShowCdf(e.target.checked)} />
          Show CDF line
        </label>

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
            <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900 }}>fanout framing</div>
          </div>
          <div style={{ marginTop: 8, ...miniText() }}>
            Treat the stream as “catalog/inventory updates”. The histogram is a distribution query on the stream without shipping full state.
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

          <div style={{ marginTop: 10, ...miniText() }}>
            Tip: raise <b>turns</b>/<b>muts</b> to simulate more frequent catalog changes; raise <b>buckets</b> to increase
            histogram resolution (more bins).
          </div>

          <div style={{ marginTop: 10, borderTop: "1px solid #f3f4f6", paddingTop: 10 }}>
            <div style={{ ...miniLabel() }}>Endpoint</div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              <code>POST /api/wirepack/v34/run</code>
            </div>
          </div>
        </div>

        {/* Main graph + controls */}
        <div style={{ ...cardStyle() }}>
          {/* Controls (compact, upgraded) */}
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
                max={1_000_000}
                onChange={(e) => setN(clamp(Number(e.target.value) || 4096, 256, 1_000_000))}
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
              buckets
              <input
                type="number"
                value={buckets}
                min={2}
                max={4096}
                onChange={(e) => setBuckets(clamp(Number(e.target.value) || 32, 2, 4096))}
                style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
              />
            </label>

            <label style={{ fontSize: 11, color: "#374151" }}>
              mode
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as any)}
                style={{
                  width: "100%",
                  marginTop: 4,
                  padding: "7px 9px",
                  borderRadius: 12,
                  border: "1px solid #e5e7eb",
                  background: "#fff",
                }}
              >
                <option value="idx_mod">idx_mod</option>
                <option value="val_mod">val_mod</option>
              </select>
            </label>
          </div>

          {err ? <div style={{ marginTop: 10, fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

          {/* Graph */}
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Distribution graph</div>
              <div style={{ fontSize: 11, color: "#374151" }}>
                hist_ok: <b style={{ color: histTri.color }}>{histTri.label}</b>
                {"  "}· LEAN: <b style={{ color: leanTri.color }}>{leanTri.label}</b>
                {"  "}· max: <b>{String(inv?.max ?? derived.max ?? "—")}</b>{" "}
                <span style={{ color: "#6b7280" }}>
                  (bucket <b>{String(inv?.max_bucket ?? derived.maxBucket ?? "—")}</b>)
                </span>
              </div>
            </div>

            <div style={{ marginTop: 10 }}>
              {hist.length ? (
                <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", overflow: "hidden" }}>
                  {svgHistogram({
                    hist,
                    height: 170,
                    highlight: (inv?.max_bucket ?? derived.maxBucket) ?? null,
                    onHover: setHovered,
                    hovered,
                    showCdf,
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

            {/* Hover tooltip line */}
            {hist.length ? (
              <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                  <div style={{ ...miniLabel() }}>Hovered bucket</div>
                  <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                    {hovered === null ? "—" : `#${hovered} = ${hist[hovered] ?? 0}`}
                  </div>
                </div>
                <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                  <div style={{ ...miniLabel() }}>Skew (max/mean)</div>
                  <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                    <b style={{ color: "#111827" }}>{derived.mean ? derived.skew.toFixed(2) : "—"}</b>{" "}
                    <span style={{ color: "#6b7280" }}>
                      (mean {derived.mean.toFixed(2)}, σ {derived.stdev.toFixed(2)})
                    </span>
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
            ) : null}

            <div style={{ marginTop: 10, fontSize: 10, color: "#6b7280" }}>
              Bars show bucket counts. Mode <code>{mode}</code> maps <code>{mode === "val_mod" ? "value" : "index"}</code> to{" "}
              <code>% buckets</code>. Optional black line is the cumulative distribution (CDF).
            </div>
          </div>

          {/* Receipts (compact but complete) */}
          {out ? (
            <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipt (verifiable)</div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                  <div>
                    drift_sha256: <code>{String(receipts?.drift_sha256 || "—")}</code>
                  </div>
                  <div>
                    final_state_sha256: <code>{String(out?.final_state_sha256 || receipt?.final_state_sha256 || "—")}</code>
                  </div>
                  <div>
                    wire_total_bytes: <code>{String(b?.wire_total_bytes ?? b?.delta_bytes_total ?? "—")}</code>
                  </div>
                </div>
              </div>

              <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Seller story (what buyers get)</div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                  <div>
                    Seller: <b>{sellerName || "Seller"}</b> · SKU: <b>{sku || "—"}</b>
                  </div>
                  <div>
                    One buyer update: <b>{bytes(Number(wire_total_bytes || 0))}</b>
                  </div>
                  <div>
                    Broadcast to {buyers.toLocaleString()} buyers: <b>{bytes(fanoutBytes)}</b>
                  </div>
                  <div style={{ color: "#6b7280" }}>
                    “Proof stamp” is the receipt + LEAN_OK — buyers can verify your distribution claim without trusting you.
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {/* Raw */}
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
            <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900 }}>why this matters</div>
          </div>

          <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>1) Query the stream, don’t ship the state</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                You’re not sending 4,096 items to everyone. You send a <b>tiny delta</b> and still answer “what’s the distribution?”
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                Example claim: <code>histogram = f(stream, buckets)</code>
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>2) Verifiable receipts (anti-drift)</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                The result comes with a drift hash + final state hash so downstream systems can detect mismatch / tampering.
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                <div>
                  <code>drift_sha256</code> = <span style={{ color: "#6b7280" }}>“did we diverge?”</span>
                </div>
                <div>
                  <code>final_state_sha256</code> = <span style={{ color: "#6b7280" }}>“what state produced this?”</span>
                </div>
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
              <div style={{ ...miniLabel() }}>3) LEAN-checked invariants</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                If <b>LEAN_OK</b> is true, you’re not just trusting the server’s math — invariants like histogram integrity are machine-checked.
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                <code>hist_ok</code> · <code>hist_sum_ok</code>
              </div>
            </div>

            <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
              <div style={{ ...miniLabel() }}>4) Seller-grade use cases</div>
              <div style={{ marginTop: 6, ...miniText() }}>
                Anywhere you broadcast frequent updates: pricing, inventory, rate limits, anomaly buckets, feature flags, or telemetry summaries.
              </div>
              <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.55 }}>
                <div>• Latency buckets: <code>dur_ms % 64</code></div>
                <div>• Status distribution: <code>status % 16</code></div>
                <div>• WAF/security: <code>ip_hash % 128</code></div>
                <div>• Fleet health: error codes bucketed per device group</div>
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
          endpoint: <code>POST /api/wirepack/v34/run</code>
        </div>
        <div>
          wire: <b style={{ color: "#111827" }}>{bytes(Number(wire_total_bytes || 0))}</b>{" "}
          <span style={{ color: "#6b7280" }}>· ops {String(ops_total)} · bytes/op {bytes_per_op ? bytes_per_op.toFixed(2) : "—"}</span>
        </div>
      </div>
    </div>
  );
};