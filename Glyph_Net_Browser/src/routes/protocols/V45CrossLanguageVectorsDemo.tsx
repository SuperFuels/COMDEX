import React, { useState } from "react";

async function fetchJson(url: string, body: any, timeoutMs = 15000) {
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
      json = { _nonJson: true, _text: txt.slice(0, 300) };
    }
    return { ok: r.ok, status: r.status, json };
  } finally {
    clearTimeout(t);
  }
}

function bytes(n: number) {
  const units = ["B", "KB", "MB"];
  let v = n,
    i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

export const V45CrossLanguageVectorsDemo: React.FC = () => {
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(256);
  const [turns, setTurns] = useState(16);
  const [muts, setMuts] = useState(128);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<any>(null);

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);

    try {
      const { ok, status, json } = await fetchJson("/api/wirepack/v45/run", { seed, n, turns, muts }, 30000);
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

  const okBadge = inv?.vector_ok === true;
  const badgeBg = okBadge ? "#ecfdf5" : "#fef2f2";
  const badgeFg = okBadge ? "#065f46" : "#991b1b";
  const badgeBorder = okBadge ? "#a7f3d0" : "#fecaca";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#111827" }}>v45 — Cross-language vectors (byte identity)</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Same inputs → <b>byte-identical template+delta</b> and <b>stable meaning</b> across implementations.
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
              onChange={(e) => setN(Math.max(256, Math.min(65536, Number(e.target.value) || 256)))}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            turns
            <input
              type="number"
              value={turns}
              onChange={(e) => setTurns(Math.max(1, Math.min(256, Number(e.target.value) || 16)))}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}>
            muts
            <input
              type="number"
              value={muts}
              onChange={(e) => setMuts(Math.max(1, Math.min(512, Number(e.target.value) || 128)))}
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

      {/* 🔥 SELL / PITCH (main deck on one slide) */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12, marginTop: 2 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
          🎯 v45 — The “Polyglot Proof”: cross-language byte identity
        </div>

        <div style={{ fontSize: 11, color: "#374151", marginTop: 8, lineHeight: 1.5 }}>
          <b>The ultimate trust claim:</b> Python and Node.js produce <b>byte-identical encoding</b>. Not similar. Not equivalent.{" "}
          <b>Identical.</b>
          <br />
          <br />

          <b>What this demo is testing for:</b> zero ambiguity at the trust boundary — different runtimes must agree on the{" "}
          <b>exact same bytes</b> and the <b>exact same final state hash</b> for the same logical stream.
          <br />
          <br />

          <b>What the test does (at a high level):</b>
          <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
            <li>
              Generate a deterministic vector state (<code>n</code>) and a collision-heavy edit stream (<code>turns × muts</code>) to stress
              last-write + duplicates.
            </li>
            <li>
              Encode + decode the <b>template</b> in both implementations.
            </li>
            <li>
              Encode + decode the <b>deltas</b> in both implementations.
            </li>
            <li>
              Replay to a final state and compare <b>sha256(state)</b>.
            </li>
          </ul>

          <div style={{ marginTop: 10 }}>
            <b>How to read the result:</b> <code>vector_ok=true</code> means <b>all five checks</b> passed:
            <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
              <li>
                <code>template_bytes_ok</code>: Python template bytes = Node template bytes (same schema → same wire format)
              </li>
              <li>
                <code>template_decode_ok</code>: both parsers agree on the decoded template structure
              </li>
              <li>
                <code>delta_bytes_ok</code>: Python deltas = Node deltas (bit-identical stream encoding)
              </li>
              <li>
                <code>delta_decode_ok</code>: both parsers recover the same ops stream from those bytes
              </li>
              <li>
                <code>final_state_ok</code>: replay produces the same final state hash (cryptographic agreement)
              </li>
            </ul>
          </div>

          <div style={{ marginTop: 10, borderRadius: 12, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
            <b>Why this is significant:</b> this removes the “polyglot trust gap”. Receipts generated by one language can be{" "}
            <b>verified by another</b> (and next: Rust/WASM in-browser). That’s what makes every other demo credible — transport,
            analytics, and audits can rely on <b>stable receipt bytes + stable hashes</b>, not “same-ish decoding”.
            <br />
            <br />
            <b>Lean note:</b> <code>LEAN_OK=1</code> means the invariants held end-to-end and the property is structured to be{" "}
            <b>machine-checkable</b> (Lean).
          </div>
        </div>
      </div>

      {/* Output */}
      {out ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Invariant status</div>
              <div
                style={{
                  padding: "6px 10px",
                  borderRadius: 999,
                  border: `1px solid ${badgeBorder}`,
                  background: badgeBg,
                  color: badgeFg,
                  fontSize: 11,
                  fontWeight: 900,
                }}
              >
                {okBadge ? "✅ VERIFIED (vector_ok)" : "❌ MISMATCH (vector_ok=false)"}
              </div>
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              <div>
                template_bytes_ok: <code>{String(inv.template_bytes_ok)}</code>
              </div>
              <div>
                template_decode_ok: <code>{String(inv.template_decode_ok)}</code>
              </div>
              <div>
                delta_bytes_ok: <code>{String(inv.delta_bytes_ok)}</code>
              </div>
              <div>
                delta_decode_ok: <code>{String(inv.delta_decode_ok)}</code>
              </div>
              <div>
                final_state_ok: <code>{String(inv.final_state_ok)}</code>
              </div>

              {out?.first_mismatch ? (
                <div style={{ marginTop: 8, color: "#991b1b" }}>
                  first_mismatch: <code>{JSON.stringify(out.first_mismatch)}</code>
                </div>
              ) : null}
            </div>
          </div>

          <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipt</div>
            <div style={{ marginTop: 10, fontSize: 11, color: "#374151", lineHeight: 1.6 }}>
              <div>
                template_bytes: <code>{bytes(Number(b.template_bytes || 0))}</code>
              </div>
              <div>
                delta_bytes_total: <code>{bytes(Number(b.delta_bytes_total || 0))}</code>
              </div>
              <div style={{ paddingTop: 8, borderTop: "1px solid #e5e7eb", marginTop: 8 }}>
                final_state_sha256: <code>{String(out.final_state_sha256 || "")}</code>
              </div>
              <div>
                drift_sha256: <code>{String(r.drift_sha256 || "")}</code>
              </div>
              <div>
                LEAN_OK: <code>{String(r.LEAN_OK)}</code>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10, fontSize: 11, color: "#6b7280" }}>
        Endpoint used:
        <div style={{ marginTop: 6 }}>
          <code>POST /api/wirepack/v45/run</code>
        </div>
      </div>
    </div>
  );
};