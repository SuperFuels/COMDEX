import React, { useMemo, useState } from "react";

// ---------- small shared helpers (keep local so it’s drop-in) ----------
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
  let v = Number(n || 0);
  let i = 0;
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

// ---------- graph: Q density + hit rate + (optional) work vs bound ----------
function svgQGraph(opts: { n: number; q: number; hitsInQ: number; steps: number; bound: number; height?: number }) {
  const { n, q, hitsInQ, steps, bound, height = 180 } = opts;
  const W = 900;
  const H = height;
  const pad = 18;
  const plotW = W - pad * 2;
  const plotH = H - pad * 2;

  const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
  const safe = (x: any, d: number) => {
    const v = Number(x);
    return Number.isFinite(v) ? v : d;
  };

  const nn = safe(n, 0);
  const qq = safe(q, 0);
  const hh = safe(hitsInQ, 0);
  const ss = safe(steps, NaN);
  const bb = safe(bound, 0);

  const qFrac = nn > 0 ? clamp01(qq / nn) : 0;
  const hitFrac = qq > 0 ? clamp01(hh / qq) : 0;
  const workFrac = Number.isFinite(ss) && bb > 0 ? clamp01(ss / bb) : 0;

  const x0 = pad;
  const y0 = pad;
  const x1 = pad + plotW;

  const bandH = Math.round(plotH * 0.22);
  const gap = Math.round(plotH * 0.10);

  const qBandY = y0 + Math.round(plotH * 0.12);
  const workBandY = qBandY + bandH + gap;

  // IMPORTANT: don't force nonzero width at fraction=0
  const qFillW = qFrac > 0 ? Math.max(2, Math.round(qFrac * plotW)) : 0;
  const hitFillW = hitFrac > 0 ? Math.max(2, Math.round(hitFrac * qFillW)) : 0;
  const workFillW = workFrac > 0 ? Math.max(2, Math.round(workFrac * plotW)) : 0;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label="Q scaling graph">
      <rect x={0} y={0} width={W} height={H} rx={16} ry={16} fill="#fff" />

      {/* outer */}
      <rect x={x0} y={y0} width={plotW} height={plotH} rx={12} ry={12} fill="transparent" stroke="#e5e7eb" />

      {/* Q band */}
      <text x={x0} y={qBandY - 6} fontSize={11} fill="#6b7280">
        Q density (|Q| / n) and hit rate (hits_in_Q / |Q|)
      </text>
      <rect x={x0} y={qBandY} width={plotW} height={bandH} rx={12} ry={12} fill="#f9fafb" stroke="#e5e7eb" />
      <rect x={x0} y={qBandY} width={qFillW} height={bandH} rx={12} ry={12} fill="#eef2ff" stroke="#c7d2fe" />
      <rect x={x0} y={qBandY} width={hitFillW} height={bandH} rx={12} ry={12} fill="#ecfeff" stroke="#a5f3fc" />
      <text x={x1} y={qBandY + bandH + 14} fontSize={11} fill="#6b7280" textAnchor="end">
        n={nn.toLocaleString()} · |Q|={qq.toLocaleString()} · hits={hh.toLocaleString()}
      </text>

      {/* Work band */}
      <text x={x0} y={workBandY - 6} fontSize={11} fill="#6b7280">
        Work vs bound (best-effort)
      </text>
      <rect x={x0} y={workBandY} width={plotW} height={bandH} rx={12} ry={12} fill="#f9fafb" stroke="#e5e7eb" />

      {Number.isFinite(ss) && bb > 0 ? (
        <>
          <rect x={x0} y={workBandY} width={workFillW} height={bandH} rx={12} ry={12} fill="#fef9c3" stroke="#fde68a" />
          <text x={x0} y={workBandY + bandH + 14} fontSize={11} fill="#6b7280">
            steps={String(ss)} · bound≈{String(bb)}
          </text>
        </>
      ) : (
        <text x={x0} y={workBandY + bandH + 14} fontSize={11} fill="#6b7280">
          steps unavailable (backend didn’t emit a work counter)
        </text>
      )}

      <line x1={x1} y1={workBandY - 10} x2={x1} y2={workBandY + bandH + 10} stroke="#e5e7eb" />
      <text x={x1} y={workBandY + bandH + 14} fontSize={11} fill="#6b7280" textAnchor="end">
        bound
      </text>
    </svg>
  );
}

export const V30SumOverQDemo: React.FC = () => {
  // params
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(64);
  const [muts, setMuts] = useState(3);
  const [q, setQ] = useState(128);

  // seller knobs
  const [sellerName, setSellerName] = useState("Seller");
  const [sku, setSku] = useState("SKU-GLYPH-30");
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
      const { ok, status, json } = await fetchJson("/api/wirepack/v30/run", body, 30000);
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

  const leanOkVal = receipts?.LEAN_OK;
  const leanOk = leanOkVal == null ? null : Boolean(Number(leanOkVal));
  const drift = typeof receipts?.drift_sha256 === "string" ? receipts.drift_sha256 : null;

  const sumOk = inv?.sum_ok == null ? null : Boolean(inv.sum_ok);
  const scalesOk = inv?.work_scales_with_Q == null ? null : Boolean(inv.work_scales_with_Q);

  const asFinite = (x: any, fallback: number) => {
    const nn = Number(x);
    return Number.isFinite(nn) ? nn : fallback;
  };

  const q_size = asFinite(b?.q_size, q);
  const hits_in_Q = asFinite(b?.hits_in_Q ?? inv?.hits_in_Q ?? inv?.hits_in_q, 0);

  const measuredStepsRaw = inv?.work_steps ?? inv?.steps ?? inv?.sum_steps ?? inv?.q_steps ?? inv?.tracked_steps;
  const measuredSteps = asFinite(measuredStepsRaw, NaN);
  const hasSteps = Number.isFinite(measuredSteps);
  const bound = hasSteps ? Math.ceil(4 * Math.max(1, q_size)) : 0;

  const ops_total = Number(b?.ops_total ?? turns * muts);
  const wire_total_bytes = Number(b?.wire_total_bytes ?? b?.delta_bytes_total ?? 0);
  const bytes_per_op = Number(b?.bytes_per_op ?? (ops_total ? wire_total_bytes / ops_total : 0));

  // Like-for-like baselines (if backend provides them)
  const rawFull = Number(b?.raw_full_snapshot_bytes ?? NaN);
  const gzFull = Number(b?.gzip_full_snapshot_bytes ?? NaN);
  const rawAns = Number(b?.raw_query_answer_bytes ?? NaN);
  const gzAns = Number(b?.gzip_query_answer_bytes ?? NaN);

  const hasLikeForLike = Number.isFinite(gzFull) && Number.isFinite(gzAns) && gzFull > 0;
  const saved = hasLikeForLike ? gzFull - gzAns : NaN;
  const savedPct = hasLikeForLike ? (saved / gzFull) * 100 : NaN;

  // seller framing
  const fanoutBytes = wire_total_bytes * Math.max(0, Number(audience || 0));
  const estRevenue = Math.max(0, Number(audience || 0)) * Math.max(0, Number(price || 0));

  const curl = useMemo(() => {
    const bodyStr = JSON.stringify({ seed, n, turns, muts, q });
    return `curl -sS -X POST http://127.0.0.1:8787/api/wirepack/v30/run \\
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
            v30 — Sum over Q <span style={{ fontSize: 11, fontWeight: 900, color: "#6b7280" }}>· seller-grade demo</span>
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 3, maxWidth: 920 }}>
            Maintain an incremental sum only for indices in <b>Q</b>. Work scales with <b>|Q|</b>, not <b>n</b>, and the receipt locks
            the result.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <Badge ok={sumOk} label={`sum_ok: ${sumOk === true ? "OK" : sumOk === false ? "FAIL" : "—"}`} />
          <Badge ok={scalesOk} label={`work_scales_with_Q: ${scalesOk === true ? "OK" : scalesOk === false ? "FAIL" : "—"}`} />
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
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <div style={{ minWidth: 260, flex: "1 1 420px" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
                Seller pitch — “Sum(Q) as a product”
                <span style={{ marginLeft: 8, fontSize: 10, fontWeight: 900, color: "#6b7280" }}>subset aggregate framing</span>
              </div>
              <div style={{ marginTop: 6, ...miniText(), maxWidth: 980 }}>
                Imagine <b>Q</b> is your “buyers-of-interest” (VIPs / cohort / watchlist). You ship only the aggregate you care about —
                <b> SUM over Q</b> — and it’s <b>receipt-verifiable</b>.
              </div>
            </div>

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

          {/* KPI strip (more room, like v29) */}
          <div
            style={{
              marginTop: 12,
              display: "grid",
              gridTemplateColumns: "repeat(6, minmax(0, 1fr))",
              gap: 10,
            }}
          >
            {[
              { label: "What you ship (1 consumer)", value: bytes(wire_total_bytes), sub: "wire_total_bytes" },
              { label: "Fanout (all consumers)", value: bytes(fanoutBytes), sub: `${audience.toLocaleString()} consumers` },
              { label: "Ops touched", value: ops_total.toLocaleString(), sub: `${bytes_per_op ? `${bytes_per_op.toFixed(2)} B/op` : "—"}` },
              {
                label: "Saved vs full snapshot",
                value: hasLikeForLike ? `${bytes(saved)} (${savedPct.toFixed(2)}%)` : "—",
                sub: hasLikeForLike ? "like-for-like gzip baseline" : "baseline unavailable",
              },
              { label: "Proof signal", value: `${tri(sumOk).label} / ${tri(scalesOk).label}`, sub: "sum_ok / work_scales_with_Q" },
              { label: "Est. gross revenue", value: estRevenue.toLocaleString(), sub: `${price} × ${audience.toLocaleString()}` },
            ].map((kpi) => (
              <div key={kpi.label} style={{ borderRadius: 16, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
                <div style={{ fontSize: 10, fontWeight: 900, color: "#6b7280", letterSpacing: 0.2 }}>{kpi.label}</div>
                <div style={{ marginTop: 6, fontSize: 13, fontWeight: 900, color: "#111827" }}>{kpi.value}</div>
                <div style={{ marginTop: 4, fontSize: 10, color: "#6b7280" }}>{kpi.sub}</div>
              </div>
            ))}
          </div>

          {/* pitch footer */}
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
                <Badge ok={sumOk} label={`sum_ok: ${sumOk === true ? "OK" : sumOk === false ? "FAIL" : "—"}`} />
                <Badge
                  ok={scalesOk}
                  label={`work_scales_with_Q: ${scalesOk === true ? "OK" : scalesOk === false ? "FAIL" : "—"}`}
                />
                <Badge ok={leanOk} label={`LEAN: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />
              </span>
            </div>

            <div style={{ fontSize: 11, color: "#6b7280" }}>
              Endpoint: <code>POST /api/wirepack/v30/run</code>
            </div>
          </div>
        </div>

        {/* TWO COLUMNS (left: run/graph/outputs, right: explainers) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(560px, 1.2fr) minmax(340px, 0.8fr)",
            gap: 12,
            alignItems: "start",
          }}
        >
          {/* LEFT */}
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
                <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Q scaling graph</div>
                <div style={{ fontSize: 11, color: "#374151" }}>
                  sum_ok: <b style={{ color: tri(sumOk).color }}>{tri(sumOk).label}</b>
                  {"  "}· work_scales_with_Q: <b style={{ color: tri(scalesOk).color }}>{tri(scalesOk).label}</b>
                  {"  "}· LEAN: <b style={{ color: tri(leanOk).color }}>{tri(leanOk).label}</b>
                </div>
              </div>

              <div style={{ marginTop: 10 }}>
                {out ? (
                  <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", overflow: "hidden" }}>
                    {svgQGraph({
                      n: out?.params?.n ?? n,
                      q: q_size,
                      hitsInQ: hits_in_Q,
                      steps: measuredSteps,
                      bound,
                      height: 180,
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
                    <b style={{ color: "#111827" }}>{bytes(wire_total_bytes)}</b>{" "}
                    <span style={{ color: "#6b7280" }}>({bytes_per_op ? `${bytes_per_op.toFixed(2)} B/op` : "—"})</span>
                  </div>
                </div>
              </div>

              <div style={{ marginTop: 10, fontSize: 10, color: "#6b7280" }}>
                Top band: how dense Q is in the whole state, plus how often mutations hit Q. Bottom band: best-effort work counter vs an{" "}
                <code>~O(|Q|)</code> visual bound.
              </div>
            </div>

            {/* Output cards */}
            {out ? (
              <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {/* Invariants */}
                <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 900,
                      color: "#111827",
                      display: "flex",
                      gap: 8,
                      flexWrap: "wrap",
                      alignItems: "center",
                    }}
                  >
                    Invariants
                    <Badge ok={sumOk} label={`sum_ok: ${sumOk === true ? "OK" : sumOk === false ? "FAIL" : "—"}`} />
                    <Badge
                      ok={scalesOk}
                      label={`work_scales_with_Q: ${scalesOk === true ? "OK" : scalesOk === false ? "FAIL" : "—"}`}
                    />
                  </div>

                  <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                    <div>
                      sum_baseline: <code>{String(out?.sum_baseline ?? "—")}</code>
                    </div>
                    <div>
                      sum_stream: <code>{String(out?.sum_stream ?? "—")}</code>
                    </div>
                    <div style={{ color: "#6b7280" }}>
                      final_state_sha256: <code>{String(out?.final_state_sha256 || "—")}</code>
                    </div>
                    <div style={{ color: "#6b7280" }}>
                      drift_sha256: <code>{drift || "—"}</code>
                    </div>
                  </div>
                </div>

                {/* Receipt + Bytes */}
                <div style={{ borderRadius: 16, border: "1px solid #e5e7eb", padding: 12 }}>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 900,
                      color: "#111827",
                      display: "flex",
                      gap: 8,
                      flexWrap: "wrap",
                      alignItems: "center",
                    }}
                  >
                    Receipt & Bytes
                    <Badge ok={leanOk} label={`LEAN_OK: ${leanOk === true ? "OK" : leanOk === false ? "FAIL" : "—"}`} />
                  </div>

                  <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
                    <div style={{ color: "#6b7280" }}>
                      drift_sha256: <code>{drift || "—"}</code>
                    </div>
                    <div style={{ color: "#6b7280" }}>
                      receipts: <code>{JSON.stringify(receipts)}</code>
                    </div>

                    <div style={{ marginTop: 10, fontWeight: 900, color: "#111827" }}>Like-for-like (truthful)</div>
                    {hasLikeForLike ? (
                      <>
                        <div style={{ marginTop: 6 }}>
                          gzip(full snapshot): <b style={{ color: "#111827" }}>{bytes(gzFull)}</b>{" "}
                          <span style={{ color: "#6b7280" }}>{Number.isFinite(rawFull) ? `(raw ${bytes(rawFull)})` : ""}</span>
                        </div>
                        <div>
                          gzip(query answer + receipt): <b style={{ color: "#111827" }}>{bytes(gzAns)}</b>{" "}
                          <span style={{ color: "#6b7280" }}>{Number.isFinite(rawAns) ? `(raw ${bytes(rawAns)})` : ""}</span>
                        </div>
                        <div style={{ marginTop: 6 }}>
                          Saved:{" "}
                          <b style={{ color: "#111827" }}>
                            {bytes(saved)} ({savedPct.toFixed(2)}%)
                          </b>
                        </div>
                      </>
                    ) : (
                      <div style={{ marginTop: 6, color: "#6b7280" }}>
                        Baseline comparison unavailable (backend didn’t return gzip_full_snapshot_bytes / gzip_query_answer_bytes).
                      </div>
                    )}

                    <div style={{ marginTop: 10, fontWeight: 900, color: "#111827" }}>Bytes</div>
                    <div>
                      ops_total: <b style={{ color: "#111827" }}>{String(b?.ops_total ?? "—")}</b>
                    </div>
                    <div>
                      q_size: <b style={{ color: "#111827" }}>{String(b?.q_size ?? "—")}</b> &nbsp; hits_in_Q:{" "}
                      <b style={{ color: "#111827" }}>{String(b?.hits_in_Q ?? "—")}</b>
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

          {/* RIGHT */}
          <div style={{ ...cardStyle() }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>What’s so special?</div>
              <div style={{ fontSize: 10, color: "#6b7280", fontWeight: 900 }}>why v30 matters</div>
            </div>

            <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
                <div style={{ ...miniLabel() }}>1) Aggregates over a tracked subset</div>
                <div style={{ marginTop: 6, ...miniText() }}>
                  You don’t have to track all <code>n</code>. Track only <b>Q</b> and maintain the SUM exactly.
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                  Update rule: <code>sum += (new - old)</code> for indices in Q
                </div>
              </div>

              <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
                <div style={{ ...miniLabel() }}>2) Work scales with |Q|, not n</div>
                <div style={{ marginTop: 6, ...miniText() }}>
                  The invariant <code>work_scales_with_Q</code> says the measured work stayed proportional to the tracked set size.
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>This is the “pay only for what you query” primitive.</div>
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
                  Cohort spend totals, VIP counters, fraud watchlists, feature flags, premium user meters — all cheap to ship and cheap to
                  verify.
                </div>
                <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.55 }}>
                  <div>• “SUM over VIP accounts”</div>
                  <div>• “SUM of flagged events”</div>
                  <div>• “SUM of active feature usage”</div>
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
          endpoint: <code>POST /api/wirepack/v30/run</code>
        </div>
        <div>
          wire: <b style={{ color: "#111827" }}>{bytes(wire_total_bytes)}</b>{" "}
          <span style={{ color: "#6b7280" }}>
            · ops {ops_total.toLocaleString()} · bytes/op {bytes_per_op ? bytes_per_op.toFixed(2) : "—"}
          </span>
        </div>
      </div>
    </div>
  );
};