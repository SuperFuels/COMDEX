// frontend/src/glyphnet/routes/protocols/V29ProjectionDemo.tsx
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

/** v29 graph: Q density + hit rate. (No work counter in v29, so we do not show a work band.) */
function svgProjectionGraph(opts: { n: number; q: number; hitsInQ: number; height?: number }) {
  const { n, q, hitsInQ, height = 170 } = opts;
  const W = 900;
  const H = height;
  const pad = 18;
  const plotW = W - pad * 2;
  const plotH = H - pad * 2;

  const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
  const nn = Number.isFinite(Number(n)) ? Number(n) : 0;
  const qq = Number.isFinite(Number(q)) ? Number(q) : 0;
  const hits = Number.isFinite(Number(hitsInQ)) ? Number(hitsInQ) : 0;

  const qFrac = nn > 0 ? clamp01(qq / nn) : 0;
  const hitFrac = qq > 0 ? clamp01(hits / qq) : 0;

  const x0 = pad;
  const y0 = pad;
  const x1 = pad + plotW;

  const bandH = Math.round(plotH * 0.38);
  const bandY = y0 + Math.round(plotH * 0.20);

  const qFillW = qq > 0 ? Math.max(2, Math.round(qFrac * plotW)) : 0;
  const hitFillW = hits > 0 ? Math.max(2, Math.round(hitFrac * qFillW)) : 0;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="Projection(Q) graph">
      <rect x={0} y={0} width={W} height={H} rx={16} ry={16} fill="#fff" />

      <rect x={x0} y={y0} width={plotW} height={plotH} rx={12} ry={12} fill="transparent" stroke="#e5e7eb" />

      <text x={x0} y={bandY - 6} fontSize={11} fill="#6b7280">
        Q density (|Q| / n) and hit rate (hits_in_Q / |Q|)
      </text>

      <rect x={x0} y={bandY} width={plotW} height={bandH} rx={12} ry={12} fill="#f9fafb" stroke="#e5e7eb" />
      {/* Q density */}
      <rect x={x0} y={bandY} width={qFillW} height={bandH} rx={12} ry={12} fill="#eef2ff" stroke="#c7d2fe" />
      {/* Hits within Q */}
      <rect x={x0} y={bandY} width={hitFillW} height={bandH} rx={12} ry={12} fill="#ecfeff" stroke="#a5f3fc" />

      <text x={x0} y={bandY + bandH + 14} fontSize={11} fill="#6b7280">
        |Q|={qq.toLocaleString()} / n={nn.toLocaleString()} ({nn ? ((qq / nn) * 100).toFixed(2) : "0.00"}%) · hit-rate{" "}
        {qq ? ((hits / qq) * 100).toFixed(2) : "0.00"}%
      </text>

      <text x={x1} y={bandY + bandH + 14} fontSize={11} fill="#6b7280" textAnchor="end">
        hits={hits.toLocaleString()}
      </text>
    </svg>
  );
}

export const V29ProjectionDemo: React.FC = () => {
  // params
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(64);
  const [muts, setMuts] = useState(3);
  const [q, setQ] = useState(128);

  // seller panel knobs
  const [sellerName, setSellerName] = useState("Seller");
  const [sku, setSku] = useState("SKU-GLYPH-29");
  const [audience, setAudience] = useState(2500);
  const [price, setPrice] = useState(19);
  const [showRaw, setShowRaw] = useState(false);

  // run state
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<any | null>(null);

  const body = useMemo(() => ({ seed, n, turns, muts, q }), [seed, n, turns, muts, q]);

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);
    try {
      const { ok, status, json } = await fetchJson("/api/wirepack/v29/run", body, 30000);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setOut(json);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function applyPreset(which: "balanced" | "stress" | "tiny" | "bigQ" | "smallQ") {
    if (which === "balanced") {
      setSeed(1337);
      setN(4096);
      setTurns(64);
      setMuts(3);
      setQ(128);
    } else if (which === "stress") {
      setSeed(9001);
      setN(65536);
      setTurns(256);
      setMuts(6);
      setQ(2048);
    } else if (which === "tiny") {
      setSeed(42);
      setN(1024);
      setTurns(16);
      setMuts(2);
      setQ(64);
    } else if (which === "bigQ") {
      setQ((prev) => clamp(prev * 2, 1, Math.min(4096, n)));
    } else {
      setQ((prev) => clamp(Math.floor(prev / 2), 1, Math.min(4096, n)));
    }
  }

  // parse outputs
  const inv = out?.invariants || {};
  const b = out?.bytes || {};
  const receipts = out?.receipts || {};

  const projectionOk = inv?.projection_ok == null ? null : Boolean(inv.projection_ok);
  const leanOkVal = receipts?.LEAN_OK;
  const leanOk = leanOkVal == null ? null : Boolean(Number(leanOkVal));
  const drift = typeof receipts?.drift_sha256 === "string" ? receipts.drift_sha256 : null;

  const ops_total = Number(b?.ops_total ?? turns * muts);
  const wire_total_bytes = Number(b?.wire_total_bytes ?? 0);
  const subset_wire_total_bytes = Number(b?.subset_wire_total_bytes ?? wire_total_bytes);

  const bytes_per_op = Number(b?.subset_bytes_per_op ?? b?.bytes_per_op ?? (ops_total ? subset_wire_total_bytes / ops_total : 0));

  const q_size = Number(b?.q_size ?? q);
  const hits_in_Q = Number(b?.hits_in_Q ?? inv?.hits_in_Q ?? inv?.hits_in_q ?? 0);

  // seller framing
  const fanoutBytes = subset_wire_total_bytes * Math.max(0, Number(audience || 0));
  const estRevenue = Math.max(0, Number(audience || 0)) * Math.max(0, Number(price || 0));

  const curl = useMemo(() => {
    const bodyStr = JSON.stringify({ seed, n, turns, muts, q });
    return `curl -sS -X POST http://127.0.0.1:8787/api/wirepack/v29/run \\
  -H 'content-type: application/json' \\
  -d '${bodyStr}' | jq`;
  }, [seed, n, turns, muts, q]);

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
            v29 — Projection(Q) <span style={{ fontSize: 11, fontWeight: 900, color: "#6b7280" }}>· seller-grade demo</span>
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 3, maxWidth: 860 }}>
            Track only indices in <b>Q</b> on a delta stream. Still produce the exact same Projection(Q) as full replay — and lock it with a receipt.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <Badge ok={projectionOk} label={`projection_ok: ${projectionOk === true ? "OK" : projectionOk === false ? "FAIL" : "—"}`} />
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
        <button type="button" onClick={() => applyPreset("bigQ")} style={pillStyle(false)} title="Double |Q|">
          Bigger Q
        </button>
        <button type="button" onClick={() => applyPreset("smallQ")} style={pillStyle(false)} title="Halve |Q|">
          Smaller Q
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

      {err ? <div style={{ marginTop: 10, fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 12 }}>
        {/* Seller Pitch (HORIZONTAL) */}
        <div style={{ ...cardStyle(), padding: 14 }}>
          {/* top line: title + story */}
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <div style={{ minWidth: 260, flex: "1 1 420px" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
                Seller pitch — “Projection(Q) as a product”
                <span style={{ marginLeft: 8, fontSize: 10, fontWeight: 900, color: "#6b7280" }}>subset reads on a stream</span>
              </div>
              <div style={{ marginTop: 6, ...miniText(), maxWidth: 980 }}>
                Treat <b>Q</b> as your “customers-of-interest” set (VIPs / fraud watchlist / cohort). You ship{" "}
                <b>only the state they asked for</b> (not the whole world), and the answer is <b>receipt-verifiable</b>.
              </div>
            </div>

            {/* lightweight “offer” controls */}
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <label style={{ fontSize: 11, color: "#374151" }}>
                Seller
                <input
                  value={sellerName}
                  onChange={(e) => setSellerName(e.target.value)}
                  style={{ width: 160, marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
                />
              </label>

              <label style={{ fontSize: 11, color: "#374151" }}>
                SKU
                <input
                  value={sku}
                  onChange={(e) => setSku(e.target.value)}
                  style={{ width: 170, marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
                />
              </label>

              <label style={{ fontSize: 11, color: "#374151" }}>
                Audience
                <input
                  type="number"
                  value={audience}
                  min={0}
                  onChange={(e) => setAudience(Math.max(0, Number(e.target.value) || 0))}
                  style={{ width: 120, marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
                />
              </label>

              <label style={{ fontSize: 11, color: "#374151" }}>
                Price (€)
                <input
                  type="number"
                  value={price}
                  min={0}
                  onChange={(e) => setPrice(Math.max(0, Number(e.target.value) || 0))}
                  style={{ width: 110, marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
                />
              </label>
            </div>
          </div>

          {/* KPI strip */}
          <div
            style={{
              marginTop: 12,
              display: "grid",
              gridTemplateColumns: "repeat(6, minmax(0, 1fr))",
              gap: 10,
            }}
          >
            {[
              { label: "What you ship (1 consumer)", value: bytes(subset_wire_total_bytes), sub: "subset_wire_total_bytes" },
              { label: "Full stream (reference)", value: bytes(wire_total_bytes), sub: "wire_total_bytes" },
              { label: "Paid work", value: `${hits_in_Q.toLocaleString()} hits`, sub: `out of ${ops_total.toLocaleString()} ops` },
              { label: "Bytes / op", value: bytes_per_op ? `${bytes_per_op.toFixed(2)} B/op` : "—", sub: "subset_bytes_per_op" },
              { label: "Fanout (all consumers)", value: bytes(fanoutBytes), sub: `${audience.toLocaleString()} consumers` },
              { label: "Est. gross revenue", value: estRevenue.toLocaleString(), sub: `${price} × ${audience.toLocaleString()}` },
            ].map((kpi) => (
              <div key={kpi.label} style={{ borderRadius: 16, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
                <div style={{ fontSize: 10, fontWeight: 900, color: "#6b7280", letterSpacing: 0.2 }}>{kpi.label}</div>
                <div style={{ marginTop: 6, fontSize: 13, fontWeight: 900, color: "#111827" }}>{kpi.value}</div>
                <div style={{ marginTop: 4, fontSize: 10, color: "#6b7280" }}>{kpi.sub}</div>
              </div>
            ))}
          </div>

          {/* pitch footer: proof + endpoint */}
          <div
            style={{
              marginTop: 12,
              display: "flex",
              justifyContent: "space-between",
              gap: 10,
              flexWrap: "wrap",
              alignItems: "center",
              borderTop: "1px solid #f3f4f6",
              paddingTop: 10,
            }}
          >
            <div style={{ fontSize: 11, color: "#6b7280" }}>
              Proof signal:{" "}
              <span style={{ display: "inline-flex", gap: 8, alignItems: "center", marginLeft: 6 }}>
                <Badge ok={projectionOk} label={`projection_ok: ${projectionOk === true ? "OK" : projectionOk === false ? "FAIL" : "—"}`} />
                <Badge ok={leanOk} label={`LEAN: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />
              </span>
            </div>

            <div style={{ fontSize: 11, color: "#6b7280" }}>
              Endpoint: <code>POST /api/wirepack/v29/run</code>
            </div>
          </div>
        </div>

        {/* Tests underneath: TWO COLUMNS (left: run/graph, right: explainers) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(520px, 1.2fr) minmax(340px, 0.8fr)",
            gap: 12,
            alignItems: "start",
          }}
        >
          {/* LEFT: main controls + graph + outputs */}
          <div style={{ ...cardStyle() }}>
            {/* Controls */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", gap: 8 }}>
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
                    setQ((qq) => clamp(qq, 1, Math.min(4096, nn)));
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
                |Q|
                <input
                  type="number"
                  value={q}
                  min={1}
                  max={Math.min(4096, n)}
                  onChange={(e) => setQ(clamp(Number(e.target.value) || 128, 1, Math.min(4096, n)))}
                  style={{ width: "100%", marginTop: 4, padding: "7px 9px", borderRadius: 12, border: "1px solid #e5e7eb" }}
                />
              </label>
            </div>

            {/* Graph */}
            <div style={{ marginTop: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Projection scaling graph</div>
                <div style={{ fontSize: 11, color: "#374151" }}>
                  projection_ok: <b style={{ color: tri(projectionOk).color }}>{tri(projectionOk).label}</b>
                  {"  "}· LEAN: <b style={{ color: tri(leanOk).color }}>{tri(leanOk).label}</b>
                </div>
              </div>

              <div style={{ marginTop: 10 }}>
                {out ? (
                  <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", overflow: "hidden" }}>
                    {svgProjectionGraph({ n, q: q_size, hitsInQ: hits_in_Q, height: 170 })}
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
                  <div style={{ ...miniLabel() }}>Tracked subset</div>
                  <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                    |Q|: <b style={{ color: "#111827" }}>{q_size.toLocaleString()}</b>{" "}
                    <span style={{ color: "#6b7280" }}>({((q_size / Math.max(1, n)) * 100).toFixed(2)}% of n)</span>
                  </div>
                </div>

                <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                  <div style={{ ...miniLabel() }}>Hits in Q</div>
                  <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                    <b style={{ color: "#111827" }}>{hits_in_Q.toLocaleString()}</b>{" "}
                    <span style={{ color: "#6b7280" }}>(hit-rate {q_size ? ((hits_in_Q / q_size) * 100).toFixed(2) : "0.00"}%)</span>
                  </div>
                </div>

                <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                  <div style={{ ...miniLabel() }}>Wire efficiency</div>
                  <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                    <b style={{ color: "#111827" }}>{bytes(subset_wire_total_bytes)}</b>{" "}
                    <span style={{ color: "#6b7280" }}>({bytes_per_op ? `${bytes_per_op.toFixed(2)} B/op` : "—"})</span>
                  </div>
                </div>
              </div>

              <div style={{ marginTop: 10, fontSize: 10, color: "#6b7280" }}>
                Band shows two levers: how dense your query set is (|Q|/n) and how often the stream actually touches it (hits_in_Q/|Q|).
              </div>
            </div>

            {/* Output cards */}
            {out ? (
              <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                  <div style={{ fontSize: 12, fontWeight: 900, color: "#111827", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                    Invariants
                    <Badge ok={projectionOk} label={`projection_ok: ${projectionOk === true ? "OK" : projectionOk === false ? "FAIL" : "—"}`} />
                  </div>

                  <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                    <div>
                      ops_total: <b style={{ color: "#111827" }}>{String(b?.ops_total ?? "—")}</b>
                    </div>
                    <div>
                      q_size: <b style={{ color: "#111827" }}>{String(b?.q_size ?? "—")}</b> &nbsp; hits_in_Q:{" "}
                      <b style={{ color: "#111827" }}>{String(b?.hits_in_Q ?? "—")}</b>
                    </div>

                    <div style={{ marginTop: 10, fontWeight: 900, color: "#111827" }}>Projection(Q) (first 12)</div>
                    <pre style={{ marginTop: 6, fontSize: 11, whiteSpace: "pre-wrap" }}>
                      {JSON.stringify((out?.projection || []).slice(0, 12), null, 2)}
                    </pre>
                  </div>
                </div>

                <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                  <div style={{ fontSize: 12, fontWeight: 900, color: "#111827", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                    Receipt
                    <Badge ok={leanOk} label={`LEAN_OK: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />
                  </div>

                  <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                    <div style={{ color: "#6b7280" }}>
                      drift_sha256: <code>{drift || "—"}</code>
                    </div>
                    <div style={{ color: "#6b7280" }}>
                      final_state_sha256: <code>{String(out?.final_state_sha256 || "—")}</code>
                    </div>

                    <div style={{ marginTop: 10, fontWeight: 900, color: "#111827" }}>Bytes</div>

                    <div>
                      template_bytes: <b style={{ color: "#111827" }}>{bytes(Number(b?.template_bytes ?? 0))}</b>{" "}
                      <span style={{ color: "#6b7280" }}>{b?.template_bytes != null ? `(${b.template_bytes} B)` : ""}</span>
                    </div>

                    <div>
                      delta_bytes_total: <b style={{ color: "#111827" }}>{bytes(Number(b?.delta_bytes_total ?? 0))}</b>{" "}
                      <span style={{ color: "#6b7280" }}>{b?.delta_bytes_total != null ? `(${b.delta_bytes_total} B)` : ""}</span>
                    </div>

                    <div>
                      wire_total_bytes: <b style={{ color: "#111827" }}>{bytes(Number(b?.wire_total_bytes ?? 0))}</b>{" "}
                      <span style={{ color: "#6b7280" }}>{b?.wire_total_bytes != null ? `(${b.wire_total_bytes} B)` : ""}</span>
                    </div>

                    <div>
                      subset_wire_total_bytes: <b style={{ color: "#111827" }}>{bytes(Number(b?.subset_wire_total_bytes ?? 0))}</b>{" "}
                      <span style={{ color: "#6b7280" }}>
                        {b?.subset_wire_total_bytes != null ? `(${b.subset_wire_total_bytes} B)` : ""}
                      </span>
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

          {/* RIGHT: What’s special explainer */}
          <div style={{ ...cardStyle() }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>What’s so special?</div>
              <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900 }}>why v29 matters</div>
            </div>

            <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
                <div style={{ ...miniLabel() }}>1) The first query primitive</div>
                <div style={{ marginTop: 6, ...miniText() }}>
                  Projection(Q) means: “give me the exact values at indices in Q.” You can do it while ingesting a delta stream, without materializing the full state.
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>Stored: only tracked indices + last-write-wins values</div>
              </div>

              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
                <div style={{ ...miniLabel() }}>2) Pay only for what you ask</div>
                <div style={{ marginTop: 6, ...miniText() }}>
                  The real work isn’t <code>n</code>. It’s how many updates actually touch your query: <code>hits_in_Q</code>.
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                  Signal: <code>hits_in_Q ≪ ops_total</code> in typical sparse-query cases.
                </div>
              </div>

              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
                <div style={{ ...miniLabel() }}>3) Receipt-locked answers</div>
                <div style={{ marginTop: 6, ...miniText() }}>
                  <code>drift_sha256</code> ties params + stream replay + invariants + answer. Same stream, same answer — verifiable.
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                  <code>LEAN_OK</code> is the end-to-end “receipt held” signal.
                </div>
              </div>

              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                <div style={{ ...miniLabel() }}>Seller-grade use cases</div>
                <div style={{ marginTop: 6, ...miniText() }}>
                  Cohorts, premium users, fraud watchlists, feature flags — read only what matters, ship tiny deltas, verify anywhere.
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.55 }}>
                  <div>• “Projection of VIP accounts”</div>
                  <div>• “Projection of flagged users”</div>
                  <div>• “Projection of enabled feature indices”</div>
                </div>
              </div>

              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
                <div style={{ ...miniLabel() }}>Reproducible command</div>
                <pre style={{ marginTop: 8, fontSize: 10, color: "#111827", whiteSpace: "pre-wrap" }}>{curl}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};