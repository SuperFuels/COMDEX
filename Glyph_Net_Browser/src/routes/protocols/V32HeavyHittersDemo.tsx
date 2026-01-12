import React, { useMemo, useState } from "react";

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

/**
 * v32 — Heavy hitters
 * Endpoint expected: POST /api/wirepack/v32/run
 *
 * This UI is deliberately “receipt-shaped”:
 * params → run → invariants + receipt + raw json
 * so every future demo can reuse the same layout.
 */
export const V32HeavyHittersDemo: React.FC = () => {
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(64);
  const [muts, setMuts] = useState(3);
  const [k, setK] = useState(16);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<any>(null);

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);

    try {
      const body = { seed, n, turns, muts, k };
      const { ok, status, json } = await fetchJson("/api/wirepack/v32/run", body, 60000);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setOut(json);
    } catch (e: any) {
      setErr(e?.message || "Demo failed");
    } finally {
      setBusy(false);
    }
  }

  const invariants = useMemo(() => safeObj(out?.invariants), [out]);
  const receipts = useMemo(() => safeObj(out?.receipts), [out]);
  const b = useMemo(() => safeObj(out?.bytes), [out]);

  // Prefer common naming, but stay robust.
  const heavyOk =
    invariants?.heavy_hitters_ok ??
    invariants?.topk_ok ??
    invariants?.query_ok ??
    invariants?.ok ??
    null;

  const badge = boolBadge(heavyOk === null ? null : Boolean(heavyOk));

  // Try to find a Top-K list in a few plausible places.
  const topk =
    out?.topk ??
    out?.top_k ??
    out?.result?.topk ??
    out?.result?.top_k ??
    out?.results?.topk ??
    out?.results?.top_k ??
    null;

  const topkArr: any[] = Array.isArray(topk) ? topk : [];

  const drift = String(receipts?.drift_sha256 ?? out?.drift_sha256 ?? "");
  const finalState = String(out?.final_state_sha256 ?? receipts?.final_state_sha256 ?? "");
  const leanOk = receipts?.LEAN_OK ?? out?.LEAN_OK ?? null;

  // Bytes (accept several naming conventions)
  const templateBytes =
    b?.wire_template_bytes ??
    b?.template_bytes ??
    b?.template_bytes_out ??
    b?.template ??
    0;

  const deltaBytesTotal =
    b?.wire_delta_bytes_total ??
    b?.wire_delta_bytes_total_sum ??
    b?.delta_bytes_total ??
    b?.delta_total ??
    0;

  const wireTotal =
    b?.wire_total_bytes ??
    (Number(templateBytes || 0) + Number(deltaBytesTotal || 0));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#111827" }}>v32 — Heavy hitters (Top-K)</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Queryable compressed streams: find the “most active indices” efficiently, with a receipt that locks correctness.
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            seed
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value) || 0)}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            n
            <input
              type="number"
              value={n}
              onChange={(e) => setN(Math.max(256, Math.min(1_000_000, Number(e.target.value) || 4096)))}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            turns
            <input
              type="number"
              value={turns}
              onChange={(e) => setTurns(Math.max(1, Math.min(4096, Number(e.target.value) || 64)))}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            muts
            <input
              type="number"
              value={muts}
              onChange={(e) => setMuts(Math.max(1, Math.min(4096, Number(e.target.value) || 3)))}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            K
            <input
              type="number"
              value={k}
              onChange={(e) => setK(Math.max(1, Math.min(128, Number(e.target.value) || 16)))}
              style={{ width: 70, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>

          <button
            type="button"
            onClick={run}
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

      {err ? <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      {/* SELL / PITCH CARD */}
        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12, marginTop: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
            🎯 v32 — Heavy hitters: the “query unlock” on compressed streams
        </div>

        <div style={{ fontSize: 11, color: "#374151", marginTop: 8, lineHeight: 1.5 }}>
            <b>The claim:</b> we can answer <b>“what changed the most?”</b> directly on a delta stream, and we can ship the answer as a
            <b> verifiable receipt</b> (not “trust me telemetry”).
            <br /><br />

            <b>We are testing for:</b> <b>order-independent Top-K correctness</b> under collisions + a <b>deterministic receipt</b> you can lock in CI
            and verify on-device.
            <br /><br />

            <b>Data:</b> an <code>n</code>-wide u32 state space and an edit stream (<code>turns × muts</code>) designed to collide (duplicate indices),
            which is the real-world hard case.
            <br /><br />

            <b>Run:</b> ingest the stream, count “activity” per index, compute Top-K, and bind the whole run into a stable receipt:
            <code> params + bytes + invariants → drift_sha256</code>.
            <br /><br />

            <b>What the results mean:</b>
            <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
            <li><code>topk_ok</code>: Top-K is identical across reorderings (answer is stable).</li>
            <li><code>topk</code>: the actual Top-K indices + hit counts (the dashboard result).</li>
            <li><code>final_state_sha256</code>: a deterministic fingerprint of the activity vector for this run.</li>
            <li><code>drift_sha256</code>: the receipt hash you can pin/verify anywhere (CI, browser/WASM, other runtimes).</li>
            </ul>

            <div style={{ marginTop: 10 }}>
            <b>Why it matters:</b> heavy-hitters is the first “real product query”:
            it turns a compressed delta stream into an <b>actionable ranking</b> (Top-K),
            and the receipt makes the result <b>verifiable</b> across runtimes and devices.
            <br />
            <b>Trust model:</b> you can ship <i>only</i> the stream + <code>drift_sha256</code>;
            any verifier can recompute and confirm the same Top-K.
            <br />
            <b>Lean note:</b> <code>LEAN_OK=1</code> means invariants held end-to-end (designed to be machine-checkable).
            </div>
        </div>
        </div>

      {/* OUTPUT */}
      {out ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {/* Status */}
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Invariant status</div>
              <div
                style={{
                  padding: "6px 10px",
                  borderRadius: 999,
                  border: `1px solid ${badge.bd}`,
                  background: badge.bg,
                  color: badge.fg,
                  fontSize: 11,
                  fontWeight: 900,
                }}
              >
                {badge.label}
                {heavyOk !== null ? ` (${Object.keys(invariants).length ? "invariants" : "ok"})` : ""}
              </div>
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              {Object.keys(invariants).length ? (
                Object.keys(invariants)
                  .sort()
                  .map((k) => (
                    <div key={k}>
                      {k}: <code>{String(invariants[k])}</code>
                    </div>
                  ))
              ) : (
                <div style={{ color: "#6b7280" }}>No invariants object returned (showing raw JSON below).</div>
              )}
            </div>

            {/* Top-K */}
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid #e5e7eb" }}>
              <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Top-K (heavy hitters)</div>
              {topkArr.length ? (
                <ul style={{ margin: "8px 0 0 16px", padding: 0, fontSize: 11, color: "#374151" }}>
                  {topkArr.slice(0, 24).map((x, i) => (
                    <li key={i}>
                      <code>{typeof x === "string" ? x : JSON.stringify(x)}</code>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
                  (No <code>topk</code> array found — if your backend uses a different field name, it’ll still be visible in Raw response.)
                </div>
              )}
            </div>
          </div>

          {/* Receipt */}
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipt</div>
            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              <div>template_bytes: <code>{bytes(Number(templateBytes || 0))}</code></div>
              <div>delta_bytes_total: <code>{bytes(Number(deltaBytesTotal || 0))}</code></div>
              <div>wire_total_bytes: <code>{bytes(Number(wireTotal || 0))}</code></div>

              <div style={{ paddingTop: 8, borderTop: "1px solid #e5e7eb", marginTop: 8 }}>
                final_state_sha256: <code>{finalState}</code>
              </div>
              <div>drift_sha256: <code>{drift}</code></div>
              <div>LEAN_OK: <code>{String(leanOk)}</code></div>
            </div>
          </div>

          {/* Raw */}
          <div style={{ gridColumn: "1 / -1", borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Raw response</div>
            <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>
              {JSON.stringify(out, null, 2)}
            </pre>
          </div>
        </div>
      ) : null}

      {/* Endpoint */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10, fontSize: 11, color: "#6b7280" }}>
        Endpoint used:
        <div style={{ marginTop: 6 }}>
          <code>POST /api/wirepack/v32/run</code>
        </div>
      </div>
    </div>
  );
};