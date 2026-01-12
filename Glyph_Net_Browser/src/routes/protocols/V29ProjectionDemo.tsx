import React, { useState } from "react";

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
    try { json = txt ? JSON.parse(txt) : {}; } catch { json = { _nonJson: true, _text: txt.slice(0, 400) }; }
    return { ok: r.ok, status: r.status, json };
  } finally {
    clearTimeout(t);
  }
}

function bytes(n: number) {
  const units = ["B", "KB", "MB"];
  let v = n, i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

export const V29ProjectionDemo: React.FC = () => {
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(64);
  const [muts, setMuts] = useState(3);
  const [q, setQ] = useState(128);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<any>(null);

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);
    try {
      const { ok, status, json } = await fetchJson("/api/wirepack/v29/run", { seed, n, turns, muts, q }, 30000);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setOut(json);
    } catch (e: any) {
      setErr(e?.message || "Demo failed");
    } finally {
      setBusy(false);
    }
  }

  const inv = out?.invariants || {};
  const b = out?.bytes || {};
  const r = out?.receipts || {};

  const okBadge = inv?.projection_ok === true;
  const badgeBg = okBadge ? "#ecfdf5" : "#fef2f2";
  const badgeFg = okBadge ? "#065f46" : "#991b1b";
  const badgeBorder = okBadge ? "#a7f3d0" : "#fecaca";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#111827" }}>
            v29 — Projection(Q) (first query primitive)
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Track only <b>|Q| indices</b> on a delta stream and still get the exact same answer as a full replay.
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
              onChange={(e) => setN(Math.max(256, Math.min(65536, Number(e.target.value) || 4096)))}
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
            |Q|
            <input
              type="number"
              value={q}
              onChange={(e) => setQ(Math.max(1, Math.min(4096, Number(e.target.value) || 128)))}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
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

      {/* Sell / explanation */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
          🎯 v29 — Projection(Q): the “query-on-stream” primitive
        </div>

        <div style={{ fontSize: 11, color: "#374151", marginTop: 8, lineHeight: 1.5 }}>
          <b>The claim:</b> you can ask for a <b>subset of state</b> (Projection over an index set <code>Q</code>) without replaying the whole world.
          <br /><br />

          <b>We are testing for:</b> <b>correctness</b> (Projection(Q) matches full replay) + a <b>deterministic receipt</b> you can lock in CI and verify in-browser/WASM.
          <br /><br />

          <b>Data:</b> a u32 state space (<code>n</code>) and a collision-heavy edit stream (<code>turns × muts</code>) with last-write-wins updates.
          <br /><br />

          <b>Run:</b> compute the answer two ways:
          <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
            <li><b>Baseline:</b> full replay into an <code>n</code>-wide vector, then read indices in <code>Q</code>.</li>
            <li><b>Query-only:</b> track only <code>|Q|</code> indices while ingesting the stream.</li>
          </ul>

          <div style={{ marginTop: 10 }}>
            <b>What the results mean:</b>
            <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
              <li><code>projection_ok</code>: both methods produce the exact same Projection(Q).</li>
              <li><code>hits_in_Q</code>: how many stream ops actually touched your query set (the real work).</li>
              <li><code>drift_sha256</code>: deterministic receipt hash (params + bytes + invariants + answer).</li>
            </ul>
          </div>
          <div style={{ marginTop: 10 }}>
            <b>Work observed:</b> only <code>{String(out?.bytes?.hits_in_Q ?? 0)}</code> of{" "}
            <code>{String(out?.bytes?.ops_total ?? 0)}</code> updates mattered to this query.
          </div>

          <div style={{ marginTop: 10 }}>
            <b>Why it matters:</b> this is the core product move: <b>work scales with |Q| (and hits_in_Q)</b>, not with <code>n</code>.
            You can ship just the stream + receipt, and any verifier can recompute and confirm the same Projection(Q).
            <br />
            <b>Lean note:</b> <code>LEAN_OK=1</code> means invariants held end-to-end (designed to be machine-checkable).
          </div>
        </div>
      </div>

      {/* Output */}
      {out ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Invariant status</div>
              <div style={{ padding: "6px 10px", borderRadius: 999, border: `1px solid ${badgeBorder}`, background: badgeBg, color: badgeFg, fontSize: 11, fontWeight: 900 }}>
                {okBadge ? "✅ VERIFIED (projection_ok)" : "❌ MISMATCH (projection_ok=false)"}
              </div>
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              <div>projection_ok: <code>{String(inv.projection_ok)}</code></div>
              <div>ops_total: <code>{String(b.ops_total)}</code></div>
              <div>q_size: <code>{String(b.q_size)}</code></div>
              <div>hits_in_Q: <code>{String(b.hits_in_Q)}</code></div>

              <div style={{ marginTop: 10, fontWeight: 900, color: "#111827" }}>Projection(Q) (first 12)</div>
              <pre style={{ marginTop: 6, fontSize: 11, whiteSpace: "pre-wrap" }}>
                {JSON.stringify((out.projection || []).slice(0, 12), null, 2)}
              </pre>
            </div>
          </div>

          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipt</div>
            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              <div>template_bytes: <code>{bytes(Number(b.template_bytes || 0))}</code></div>
              <div>delta_bytes_total: <code>{bytes(Number(b.delta_bytes_total || 0))}</code></div>
              <div>wire_total_bytes: <code>{bytes(Number(b.wire_total_bytes || 0))}</code></div>

              <div style={{ paddingTop: 8, borderTop: "1px solid #e5e7eb", marginTop: 8 }}>
                final_state_sha256: <code>{String(out.final_state_sha256 || "")}</code>
              </div>
              <div>drift_sha256: <code>{String(r.drift_sha256 || "")}</code></div>
              <div>LEAN_OK: <code>{String(r.LEAN_OK)}</code></div>
            </div>
          </div>
        </div>
      ) : null}

      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10, fontSize: 11, color: "#6b7280" }}>
        Endpoint used:
        <div style={{ marginTop: 6 }}><code>POST /api/wirepack/v29/run</code></div>
      </div>
    </div>
  );
};