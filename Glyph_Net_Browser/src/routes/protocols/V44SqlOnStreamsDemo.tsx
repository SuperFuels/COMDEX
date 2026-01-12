import { useState } from "react";

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

  async function run() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);

    const body = JSON.stringify({ query_id: queryId, n, turns, muts, k, seed });

    async function post(path: string) {
      const r = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      const j = await r.json().catch(() => ({}));
      return { r, j };
    }

    try {
      // try v44 route first (if you later add it, this will start working automatically)
      let { r, j } = await post("/api/wirepack/v44/run");

      // fallback to v46 (which you confirmed exists)
      if (r.status === 404) {
        ({ r, j } = await post("/api/wirepack/v46/run"));
      }

      if (!r.ok || !j?.ok) throw new Error(j?.error || `HTTP ${r.status}`);
      setOut(j);
    } catch (e: any) {
      setErr(e?.message || "v44 failed");
    } finally {
      setBusy(false);
    }
  }
  const b = out?.bytes;
  const rec = out?.receipts;

  const wire = b?.wire_total_bytes;
  const gz = b?.gzip_snapshot_bytes_total;
  const factor = wire && gz ? gz / wire : null;
  const pctSaved = wire && gz ? (1 - wire / gz) * 100 : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
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
          <label
            key={label}
            style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "#374151" }}
          >
            {label}
            <input
              type="number"
              value={val}
              min={lo}
              max={hi}
              onChange={(e) => setVal(Number(e.target.value) || val)}
              style={{ width: 90, padding: "6px 8px", borderRadius: 999, border: "1px solid #e5e7eb" }}
            />
          </label>
        ))}

        <button
          type="button"
          onClick={run}
          disabled={busy}
          style={{
            padding: "6px 12px",
            borderRadius: 999,
            border: "1px solid #111827",
            background: busy ? "#374151" : "#111827",
            color: "#fff",
            fontSize: 11,
            fontWeight: 800,
            cursor: busy ? "default" : "pointer",
          }}
        >
          {busy ? "Running…" : "Run v44"}
        </button>
      </div>

      {err ? <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      {/* Result correctness (full width) */}
      <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Result correctness</div>
        <div style={{ fontSize: 11, color: "#374151", marginTop: 6 }}>
          snapshot vs stream: <code>{out ? (out.query_ok ? "OK" : "FAIL") : "—"}</code>
        </div>
        <div style={{ fontSize: 11, color: "#6b7280", marginTop: 10 }}>
          <div>
            result_sha256: <code>{rec?.result_sha256 || "—"}</code>
          </div>
          <div>
            drift_sha256: <code>{rec?.drift_sha256 || "—"}</code>
          </div>
          <div>
            LEAN_OK: <code>{rec?.LEAN_OK ?? "—"}</code>
          </div>
        </div>
      </div>

      {/* Outputs + Sell side-by-side */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, alignItems: "start" }}>
        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Outputs (truncated)</div>
          <pre style={{ marginTop: 8, fontSize: 11, overflow: "auto", maxHeight: 360 }}>
            {out
              ? JSON.stringify(
                  {
                    query_id: out.query_id,
                    params: out.params,
                    Q: out.Q?.slice?.(0, 16),
                    snapshot_head: Array.isArray(out.snapshot_result)
                      ? out.snapshot_result.slice(0, 16)
                      : out.snapshot_result,
                    stream_head: Array.isArray(out.stream_result) ? out.stream_result.slice(0, 16) : out.stream_result,
                    ops: out.ops,
                  },
                  null,
                  2,
                )
              : "Run v44 to populate outputs."}
          </pre>
        </div>

        <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#111827" }}>Bytes (the sell)</div>

          {factor ? (
            <div style={{ marginTop: 8, fontSize: 13, fontWeight: 900, color: "#111827" }}>
              ~{factor.toFixed(1)}× smaller{" "}
              <span style={{ fontSize: 11, fontWeight: 700, color: "#6b7280" }}>
                ({pctSaved!.toFixed(1)}% less)
              </span>
            </div>
          ) : (
            <div style={{ marginTop: 8, fontSize: 11, color: "#6b7280" }}>—</div>
          )}

          <div style={{ fontSize: 11, color: "#374151", marginTop: 10 }}>
            WirePack: <code>{b ? `${bytes(b.wire_total_bytes)} (${b.wire_total_bytes} B)` : "—"}</code>
          </div>
          <div style={{ fontSize: 11, color: "#374151", marginTop: 6 }}>
            gzip snapshots: <code>{b ? `${bytes(b.gzip_snapshot_bytes_total)} (${b.gzip_snapshot_bytes_total} B)` : "—"}</code>
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 10 }}>
            template: <code>{b ? `${b.wire_template_bytes} B` : "—"}</code> · delta total:{" "}
            <code>{b ? `${b.wire_delta_bytes_total} B` : "—"}</code>
          </div>
        </div>
      </div>
    </div>
  );}