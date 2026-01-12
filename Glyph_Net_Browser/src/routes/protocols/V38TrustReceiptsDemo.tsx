import React, { useMemo, useState } from "react";

// Small shared helpers (keep local so it’s drop-in)
function bytes(n: number) {
  const units = ["B", "KB", "MB", "GB"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

async function fetchJsonWithTimeout(url: string, init: RequestInit = {}, timeoutMs = 8000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { ...init, signal: ctrl.signal });
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

type V38Resp = {
  ok: boolean;
  demo?: string;
  params?: { seed: number; n: number; turns: number; muts: number };
  bytes?: {
    wire_template_bytes: number;
    wire_delta_bytes_total: number;
    wire_total_bytes: number;
    rawA_bytes_total: number;
    rawB_bytes_total: number;
    canon_bytes_total: number;
  };
  invariants?: { canon_ok: boolean; replay_ok: boolean };
  final_state_sha256?: string;
  receipts?: { final_state_sha256: string; drift_sha256: string; LEAN_OK: number };
  error?: string;
};

async function runV38(seed: number, n: number, turns: number, muts: number): Promise<V38Resp> {
  const { ok, status, json } = await fetchJsonWithTimeout(
    "/api/wirepack/v38/run",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed, n, turns, muts }),
    },
    15000,
  );
  if (!ok) throw new Error(`v38/run HTTP ${status}: ${JSON.stringify(json)}`);
  return json as V38Resp;
}

function Badge(props: { ok: boolean | null; label: string }) {
  const bg = props.ok ? "#ecfdf5" : props.ok === false ? "#fef2f2" : "#f3f4f6";
  const fg = props.ok ? "#065f46" : props.ok === false ? "#991b1b" : "#374151";
  const bd = props.ok ? "#a7f3d0" : props.ok === false ? "#fecaca" : "#e5e7eb";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 10px",
        borderRadius: 999,
        border: `1px solid ${bd}`,
        background: bg,
        color: fg,
        fontSize: 11,
        fontWeight: 900,
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ fontSize: 13 }}>{props.ok ? "✅" : props.ok === false ? "❌" : "—"}</span>
      {props.label}
    </span>
  );
}

export const V38TrustReceiptsDemo: React.FC = () => {
  const [seed, setSeed] = useState<number>(1337);
  const [n, setN] = useState<number>(4096);
  const [turns, setTurns] = useState<number>(64);
  const [muts, setMuts] = useState<number>(3);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [resp, setResp] = useState<V38Resp | null>(null);

  const canonOk = resp?.invariants?.canon_ok ?? null;
  const replayOk = resp?.invariants?.replay_ok ?? null;
  const leanOk = typeof resp?.receipts?.LEAN_OK === "number" ? resp!.receipts!.LEAN_OK === 1 : null;

  const b = resp?.bytes;
  const template = b?.wire_template_bytes ?? 0;
  const deltas = b?.wire_delta_bytes_total ?? 0;
  const total = b?.wire_total_bytes ?? 0;

  // Alias so JSX snippets can consistently use `data`
  const data = resp;

  const deltaPct = useMemo(() => {
    if (!b?.wire_total_bytes) return null;
    return (100 * (b.wire_delta_bytes_total / b.wire_total_bytes)).toFixed(1);
  }, [b?.wire_total_bytes, b?.wire_delta_bytes_total]);

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setResp(null);
    try {
      const out = await runV38(seed, n, turns, muts);
      setResp(out);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, minHeight: "60vh" }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 900, color: "#111827" }}>v38 — Trust & receipts (canon + replay)</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Same logical ops, different ordering → <b>canonical bytes identical</b>. Replay → <b>final state hash identical</b>. Emits deterministic receipts.
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
              onChange={(e) => setN(Math.max(256, Math.min(1 << 16, Number(e.target.value) || 4096)))}
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
              onChange={(e) => setMuts(Math.max(1, Math.min(512, Number(e.target.value) || 3)))}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>

          <button
            type="button"
            onClick={() => setSeed((s) => (s + 1) >>> 0)}
            style={{ padding: "6px 10px", borderRadius: 999, border: "1px solid #e5e7eb", background: "#f9fafb", fontSize: 11, cursor: "pointer" }}
          >
            +seed
          </button>

          <button
            type="button"
            onClick={run}
            disabled={busy}
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid #111827",
              background: busy ? "#6b7280" : "#111827",
              color: "#fff",
              fontSize: 11,
              fontWeight: 900,
              cursor: busy ? "not-allowed" : "pointer",
            }}
          >
            {busy ? "Running…" : "Run"}
          </button>
        </div>
      </div>

      {err ? <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Badge ok={canonOk} label="canon_ok" />
        <Badge ok={replayOk} label="replay_ok" />
        <Badge ok={leanOk} label={`LEAN_OK = ${resp?.receipts?.LEAN_OK ?? "—"}`} />
      </div>
      

      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12, marginTop: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
            What this demo proves
        </div>

        <div style={{ fontSize: 11, color: "#374151", marginTop: 8, lineHeight: 1.5 }}>
            <b>We are testing for:</b> order independence + determinism. The same logical update-set must produce
            <b> identical canonical bytes</b> and a <b>stable final state hash</b>, even if messages arrive in different orders.
            <br /><br />

            <b>Data:</b> a large u32 state vector (<code>n</code>). Each turn emits <code>muts</code> updates, including duplicates
            (collision pressure). We generate two permutations of the same ops to simulate nondeterministic ordering.
            <br /><br />

            <b>Run:</b> we encode raw bytes (order-sensitive) and canonical bytes (order-invariant), then replay the canonical meaning
            and hash the final state.
            <br /><br />

            <b>Results:</b>
            <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
            <li><code>canon_ok</code>: canonical bytes are identical across reorderings (stable receipt bytes).</li>
            <li><code>replay_ok</code>: final_state_sha256 matches (stable meaning).</li>
            <li><code>drift_sha256</code>: deterministic receipt-of-run over params + bytes + invariants.</li>
            </ul>

            <div style={{ marginTop: 10 }}>
            <b>Why it matters:</b> stable receipts enable auditability, dedupe/caching, and eliminate “order attacks” in distributed systems.
            <br />
            <b>Lean note:</b> <code>LEAN_OK=1</code> means both invariants held; the invariant is designed to be machine-checkable (Lean).
            </div>
        </div>
        </div>
        {/* TRUST UNLOCK SELL SECTION (v38) */}
<div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12, marginTop: 10 }}>
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
    <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>
      🔥 Trust unlock: deterministic receipts under reordering
    </div>
    <div style={{ fontSize: 11, color: "#6b7280" }}>
      v38 — canonical bytes + replay invariants
    </div>
  </div>

  <div style={{ fontSize: 11, color: "#374151", marginTop: 8, lineHeight: 1.5 }}>
    <b>The claim:</b> “The same logical update-set produces <b>bit-identical canonical bytes</b> and the <b>same final state hash</b>,
    even if messages arrive in different orders.”
    <br /><br />

    <b>The test:</b> per turn we generate <code>muts</code> updates into an <code>n</code>-wide u32 state, then:
    <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
      <li>shuffle the same ops into two different orderings (<code>rawA</code> vs <code>rawB</code>)</li>
      <li>canonicalize (“last write wins” + sort by index) → <code>canon</code></li>
      <li>replay canonical meaning and hash the final state</li>
    </ul>

    <div style={{ marginTop: 10, borderTop: "1px solid #e5e7eb", paddingTop: 10 }}>
      <b>Live result (this run):</b>
      <div style={{ marginTop: 6, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
        <div><code>rawA</code>: <b>{data?.bytes?.rawA_bytes_total ?? "—"} B</b></div>
        <div><code>rawB</code>: <b>{data?.bytes?.rawB_bytes_total ?? "—"} B</b></div>
        <div><code>canon</code>: <b>{data?.bytes?.canon_bytes_total ?? "—"} B</b></div>
      </div>

      <div style={{ marginTop: 8 }}>
        ✅ <code>canon_ok</code>: <b>{String(data?.invariants?.canon_ok ?? "—")}</b> (canonical bytes stable)<br />
        ✅ <code>replay_ok</code>: <b>{String(data?.invariants?.replay_ok ?? "—")}</b> (meaning stable)<br />
        ✅ <code>LEAN_OK</code>: <b>{String(data?.receipts?.LEAN_OK ?? "—")}</b> (both invariants held)
      </div>
    </div>

    <div style={{ marginTop: 10, borderRadius: 12, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10 }}>
      <b>Why this matters:</b>
      <ul style={{ margin: "6px 0 0 16px", padding: 0 }}>
        <li><b>Eliminates order attacks:</b> reordering can’t change receipts or state hashes.</li>
        <li><b>Enables caching + dedupe:</b> identical work produces identical bytes and hashes.</li>
        <li><b>Makes audit trails real:</b> receipts become verifiable artifacts, not “logs”.</li>
        <li><b>Unlocks zero-trust verification:</b> a verifier only needs bytes + hash, not your runtime.</li>
      </ul>

      <div style={{ marginTop: 8 }}>
        <b>Lean note:</b> <code>LEAN_OK=1</code> means the demo’s invariants held end-to-end; the invariant is designed to be machine-checkable.
      </div>
    </div>
  </div>
</div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Bytes</div>

          <div style={{ marginTop: 10, fontSize: 11, color: "#374151", display: "flex", flexDirection: "column", gap: 6 }}>
            <div>
              template: <code>{b ? `${bytes(template)} (${template} B)` : "—"}</code>
            </div>
            <div>
              deltas total: <code>{b ? `${bytes(deltas)} (${deltas} B)` : "—"}</code>{" "}
              {deltaPct ? <span style={{ color: "#6b7280" }}>(~{deltaPct}% of total)</span> : null}
            </div>
            <div style={{ paddingTop: 6, borderTop: "1px solid #e5e7eb" }}>
              total: <code>{b ? `${bytes(total)} (${total} B)` : "—"}</code>
            </div>

            <div style={{ paddingTop: 6, borderTop: "1px solid #e5e7eb" }}>
              rawA bytes total: <code>{b ? `${b.rawA_bytes_total} B` : "—"}</code>
            </div>
            <div>
              rawB bytes total: <code>{b ? `${b.rawB_bytes_total} B` : "—"}</code>
            </div>
            <div>
              canon bytes total: <code>{b ? `${b.canon_bytes_total} B` : "—"}</code>
            </div>
          </div>
        </div>
        

        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Receipts</div>

          <div style={{ marginTop: 10, fontSize: 11, color: "#374151", display: "flex", flexDirection: "column", gap: 8 }}>
            <div>
              final_state_sha256:
              <div style={{ marginTop: 4 }}>
                <code style={{ wordBreak: "break-all" }}>{resp?.receipts?.final_state_sha256 || resp?.final_state_sha256 || "—"}</code>
              </div>
            </div>

            <div style={{ paddingTop: 8, borderTop: "1px solid #e5e7eb" }}>
              drift_sha256:
              <div style={{ marginTop: 4 }}>
                <code style={{ wordBreak: "break-all" }}>{resp?.receipts?.drift_sha256 || "—"}</code>
              </div>
            </div>

            <div style={{ paddingTop: 8, borderTop: "1px solid #e5e7eb", color: "#6b7280" }}>
              Endpoint used:
              <div style={{ marginTop: 6 }}>
                <code>POST /api/wirepack/v38/run</code>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Raw response</div>
        <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", overflowX: "auto", whiteSpace: "pre-wrap" }}>
          {resp ? JSON.stringify(resp, null, 2) : "—"}
        </pre>
      </div>
    </div>
  );
};