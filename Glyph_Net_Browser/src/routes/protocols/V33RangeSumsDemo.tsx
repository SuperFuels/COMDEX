import React, { useMemo, useState } from "react";

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

async function fetchJson(url: string, body: any, timeoutMs = 12000) {
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

export const V33RangeSumsDemo: React.FC = () => {
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(64);
  const [muts, setMuts] = useState(3);
  const [l, setL] = useState(0);
  const [r, setR] = useState(127);

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
      const { ok, status, json } = await fetchJson("/api/wirepack/v33/run", body);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setOut(json);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  const inv = out?.invariants || {};
  const b = out?.bytes;
  const workLogOk =
  Boolean(inv?.work_scales_with_logN) ||
  Boolean(inv?.work_scales_with_log_n); // backend key
  const receipts = out?.receipts || {};
  const leanOk = receipts?.LEAN_OK === 1 || receipts?.LEAN_OK === true;

  const rangeLen =
    out?.params?.l != null && out?.params?.r != null
      ? Number(out.params.r) - Number(out.params.l) + 1
      : Math.max(0, r - l + 1);

  const driftSha =
    receipts?.drift_sha256 ||
    out?.drift_sha256 ||
    "—";

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 10,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ fontSize: 13, fontWeight: 900, color: "#111827" }}>v33 — Range sums (L..R)</div>

            {leanOk ? (
                <span
                style={{
                    fontSize: 10,
                    fontWeight: 900,
                    padding: "2px 8px",
                    borderRadius: 999,
                    background: "#ecfdf5",
                    color: "#065f46",
                    border: "1px solid #a7f3d0",
                    lineHeight: "16px",
                }}
                title="Invariants held end-to-end (receipt-locked)"
                >
                LEAN VERIFIED
                </span>
            ) : null}
            </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Maintains a Fenwick tree via <code>sum += (new - old)</code> so the range sum is <b>O(log n)</b>, not a scan.
          </div>
        </div>

        <button
          type="button"
          onClick={run}
          disabled={busy}
          style={{
            padding: "6px 12px",
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

      <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "repeat(6, minmax(0, 1fr))", gap: 8 }}>
        <label style={{ fontSize: 11, color: "#374151" }}>
          seed
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(Number(e.target.value) || 0)}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          n
          <input
            type="number"
            value={n}
            min={256}
            max={65536}
            onChange={(e) => setN(Math.max(256, Math.min(65536, Number(e.target.value) || 4096)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          turns
          <input
            type="number"
            value={turns}
            min={1}
            max={4096}
            onChange={(e) => setTurns(Math.max(1, Math.min(4096, Number(e.target.value) || 64)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          muts
          <input
            type="number"
            value={muts}
            min={1}
            max={4096}
            onChange={(e) => setMuts(Math.max(1, Math.min(4096, Number(e.target.value) || 3)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          L
          <input
            type="number"
            value={l}
            min={0}
            max={n - 1}
            onChange={(e) => setL(Math.max(0, Math.min(n - 1, Number(e.target.value) || 0)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          R
          <input
            type="number"
            value={r}
            min={0}
            max={n - 1}
            onChange={(e) => setR(Math.max(0, Math.min(n - 1, Number(e.target.value) || 0)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }}
          />
        </label>
      </div>

      {err ? <div style={{ marginTop: 10, fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      {out ? (
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Invariant</div>

            <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
              range_ok:{" "}
              <b style={{ color: inv?.range_ok ? "#065f46" : "#991b1b" }}>{inv?.range_ok ? "OK" : "FAIL"}</b>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
            work_scales_with_logN:{" "}
            <b style={{ color: workLogOk ? "#065f46" : "#991b1b" }}>
                {workLogOk ? "OK" : "FAIL"}
            </b>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              sum_baseline: <code>{String(out?.sum_baseline ?? "—")}</code>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              sum_stream: <code>{String(out?.sum_stream ?? "—")}</code>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              final_state_sha256: <code>{String(out?.final_state_sha256 || "—")}</code>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              drift_sha256: <code>{String(driftSha)}</code>
            </div>

            <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
              LEAN_OK: <b style={{ color: leanOk ? "#065f46" : "#991b1b" }}>{leanOk ? "YES" : "NO"}</b>
            </div>
          </div>

          <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Bytes</div>

            <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
              ops_total: <b>{b?.ops_total ?? "—"}</b>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              range: <b>[{out?.params?.l ?? l}..{out?.params?.r ?? r}]</b> &nbsp; len: <b>{rangeLen}</b>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              delta_bytes_total: <b>{b?.delta_bytes_total == null ? "—" : bytes(Number(b.delta_bytes_total))}</b>
              {b?.delta_bytes_total != null ? <span style={{ color: "#6b7280" }}> ({b.delta_bytes_total} B)</span> : null}
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              wire_total_bytes: <b>{b?.wire_total_bytes == null ? "—" : bytes(Number(b.wire_total_bytes))}</b>
              {b?.wire_total_bytes != null ? <span style={{ color: "#6b7280" }}> ({b.wire_total_bytes} B)</span> : null}
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280" }}>
              receipts: <code>{JSON.stringify(receipts || {})}</code>
            </div>
          </div>
          <div
  style={{
    gridColumn: "1 / -1",
    borderRadius: 12,
    border: "1px solid #e5e7eb",
    padding: 10,
    background: "#fff",
  }}
>
  <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>
    🎯 v33 — Range sums: interval queries on a delta stream
  </div>

  <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.55 }}>
    <div>
      <b>The claim:</b> you can compute <code>SUM(state[L..R])</code> without scanning the range or decoding full snapshots.
      Work stays <b>O(log n)</b> per query.
    </div>

    <div style={{ marginTop: 8 }}>
      <b>We are testing for:</b> correctness (<code>range_ok</code>) + bounded query work (<code>work_scales_with_logN</code>) +
      a deterministic receipt (<code>drift_sha256</code>) you can lock in CI and verify anywhere.
    </div>

    <div style={{ marginTop: 8 }}>
      <b>Run:</b>
      <div style={{ marginTop: 4 }}>
        • <b>Baseline</b>: replay all mutations, then scan <code>[L..R]</code> and sum.
      </div>
      <div>
        • <b>Streaming</b>: maintain a Fenwick tree with <code>delta = (new - old)</code>, query via two prefix sums.
      </div>
    </div>

    <div style={{ marginTop: 8 }}>
      <b>What the results mean:</b>
      <div style={{ marginTop: 4 }}>
        • <code>range_ok</code>: streaming range sum exactly matches baseline.
      </div>
      <div>
        • <code>work_scales_with_logN</code>: measured Fenwick “sum steps” stayed within a small multiple of <code>log2(n)</code>.
      </div>
      <div>
        • <code>drift_sha256</code>: receipt hash tying params + bytes + invariants + answer to the same replay.
      </div>
    </div>

    <div style={{ marginTop: 8 }}>
      <b>Why it matters:</b> this is the next primitive after Projection(Q): now you can do <b>interval analytics</b>
      (sliding windows, prefix/range aggregates) directly on the wire stream—cheap to verify, cheap to transport.
    </div>

    <div style={{ marginTop: 8, color: "#6b7280" }}>
      <b>Lean note:</b> <code>LEAN_OK=1</code> means the invariant set held end-to-end and the receipt is replay-locked.
    </div>
  </div>
</div>

          <div
            style={{
              gridColumn: "1 / -1",
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              padding: 10,
              background: "#f9fafb",
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Explanation</div>
            <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.5 }}>
              <div>
                <b>Baseline</b>: replay all mutations, then compute <code>SUM(state[i] for i in [L..R])</code> by scanning the range.
              </div>
              <div style={{ marginTop: 6 }}>
                <b>Streaming</b>: keep a Fenwick tree updated with <code>delta = (new - old)</code> so a range sum is <b>O(log n)</b>.
              </div>
              <div style={{ marginTop: 6 }}>
                <b>Receipt lock</b>: <code>drift_sha256</code> ties the “lean” computation to the exact replay.
              </div>
            </div>
          </div>

          <div style={{ gridColumn: "1 / -1", borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Endpoint</div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              <code>POST /api/wirepack/v33/run</code>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              params: <code>{JSON.stringify(out?.params || {}, null, 0)}</code>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};