import React, { useEffect, useMemo, useState } from "react";

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
    try { json = txt ? JSON.parse(txt) : {}; }
    catch { json = { _nonJson: true, _text: txt.slice(0, 400) }; }
    return { ok: r.ok, status: r.status, json };
  } finally { clearTimeout(t); }
}

function bytes(n: number) {
  const units = ["B", "KB", "MB", "GB"];
  let v = Number(n || 0), i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
}

function badge(ok: boolean | null) {
  const good = ok === true;
  const bad = ok === false;
  return {
    bg: good ? "#ecfdf5" : bad ? "#fef2f2" : "#f9fafb",
    fg: good ? "#065f46" : bad ? "#991b1b" : "#6b7280",
    bd: good ? "#a7f3d0" : bad ? "#fecaca" : "#e5e7eb",
    label: good ? "LEAN VERIFIED" : bad ? "FAIL" : "LEAN PENDING",
  };
}

type Template = {
  id: string;
  title: string;
  blurb: string;
  fields: Array<{ name: string; type: string }>;
  template_bytes: number;
  template_sha256: string;
};

export const V12MultiTemplateCatalogDemo: React.FC = () => {
  const [seed, setSeed] = useState(1337);
  const [n, setN] = useState(4096);
  const [turns, setTurns] = useState(64);
  const [muts, setMuts] = useState(3);

  const [templateId, setTemplateId] = useState<string>("metrics_v1");
  const [templates, setTemplates] = useState<Template[]>([]);
  const [catalogErr, setCatalogErr] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [out, setOut] = useState<any>(null);

  // load catalog once (and whenever the demo mounts)
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setCatalogErr(null);
        const { ok, status, json } = await fetchJson("/api/wirepack/v12/catalog", {}, 12000);
        if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
        if (!alive) return;
        setTemplates(Array.isArray(json?.templates) ? json.templates : []);
      } catch (e: any) {
        if (!alive) return;
        setCatalogErr(e?.message || String(e));
      }
    })();
    return () => { alive = false; };
  }, []);

  const t = useMemo(
    () => templates.find((x) => x.id === templateId) || null,
    [templates, templateId]
  );

  async function mint() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);
    try {
      const body = { template_id: templateId, seed, n, turns, muts };
      const { ok, status, json } = await fetchJson("/api/wirepack/v12/mint", body, 25000);
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setOut(json);
    } catch (e: any) {
      setErr(e?.message || "Demo failed");
    } finally {
      setBusy(false);
    }
  }

  const receipts = out?.receipts || {};
  const receipt = out?.receipt || {};
  const b = receipt?.bytes || out?.bytes || {};
  const inv = receipt?.invariants || out?.invariants || {};

  const leanOk = receipts?.LEAN_OK === 1 || receipts?.LEAN_OK === true ? true : (receipts?.LEAN_OK === 0 ? false : null);
  const lean = badge(leanOk);

  const cacheHit = inv?.cache_hit === true;
  const cacheLabel = cacheHit ? "CACHE HIT" : (inv?.cache_hit === false ? "CACHE MISS" : "—");

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 900, color: "#111827" }}>
            v12 — Multi-template catalog
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Multiple templates cached + selected; real-world shape variability; receipt per template.
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "4px 10px",
            borderRadius: 999,
            border: `1px solid ${lean.bd}`,
            background: lean.bg,
            color: lean.fg,
            fontSize: 11,
            fontWeight: 900,
            whiteSpace: "nowrap",
          }}>
            {lean.label}
          </div>

          <button
            type="button"
            onClick={mint}
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
            {busy ? "Minting…" : "Mint receipt"}
          </button>
        </div>
      </div>

      {/* Controls */}
      <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "2fr repeat(4, 1fr)", gap: 8 }}>
        <label style={{ fontSize: 11, color: "#374151" }}>
          template
          <select
            value={templateId}
            onChange={(e) => setTemplateId(String(e.target.value))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb", background: "#fff" }}
          >
            {templates.length ? templates.map((x) => (
              <option key={x.id} value={x.id}>{x.title}</option>
            )) : (
              <option value="metrics_v1">metrics_v1</option>
            )}
          </select>
          <div style={{ marginTop: 4, fontSize: 10, color: "#6b7280" }}>
            {t?.blurb || (catalogErr ? "catalog unavailable" : "—")}
          </div>
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          seed
          <input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value) || 0)}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }} />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          n
          <input type="number" value={n} min={256} max={1_000_000}
            onChange={(e) => setN(Math.max(256, Math.min(1_000_000, Number(e.target.value) || 4096)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }} />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          turns
          <input type="number" value={turns} min={1} max={4096}
            onChange={(e) => setTurns(Math.max(1, Math.min(4096, Number(e.target.value) || 64)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }} />
        </label>

        <label style={{ fontSize: 11, color: "#374151" }}>
          muts
          <input type="number" value={muts} min={1} max={4096}
            onChange={(e) => setMuts(Math.max(1, Math.min(4096, Number(e.target.value) || 3)))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb" }} />
        </label>
      </div>

      {catalogErr ? <div style={{ marginTop: 8, fontSize: 11, color: "#b91c1c" }}>catalog: {catalogErr}</div> : null}
      {err ? <div style={{ marginTop: 8, fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      {/* Output */}
      {out ? (
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Template / Cache</div>

            <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
              template_id: <b>{String(receipt?.template_id || "—")}</b>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              cache:{" "}
              <b style={{ color: cacheHit ? "#065f46" : "#991b1b" }}>
                {cacheLabel}
              </b>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              template_sha256: <code>{String(receipt?.template_sha256 || "—")}</code>
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280" }}>
              fields:{" "}
              <code>
                {t?.fields ? t.fields.map((f) => `${f.name}:${f.type}`).join(", ") : "—"}
              </code>
            </div>
          </div>

          <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Receipt</div>

            <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
              template_bytes: <b>{bytes(Number(b?.template_bytes || 0))}</b> <span style={{ color: "#6b7280" }}>({b?.template_bytes ?? 0} B)</span>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              delta_bytes_total: <b>{bytes(Number(b?.delta_bytes_total || 0))}</b> <span style={{ color: "#6b7280" }}>({b?.delta_bytes_total ?? 0} B)</span>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              wire_total_bytes: <b>{bytes(Number(b?.wire_total_bytes || 0))}</b> <span style={{ color: "#6b7280" }}>({b?.wire_total_bytes ?? 0} B)</span>
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280" }}>
              drift_sha256: <code>{String(receipts?.drift_sha256 || "—")}</code>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              final_state_sha256: <code>{String(receipt?.final_state_sha256 || "—")}</code>
            </div>
          </div>

          {/* What this demo proves */}
          <div style={{ gridColumn: "1 / -1", borderRadius: 12, border: "1px solid #e5e7eb", padding: 10, background: "#f9fafb" }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>What this demo proves</div>

            <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.55 }}>
              <div><b>Claim</b>: the transport layer can support <b>multiple real-world data shapes</b> (templates) and still mint a <b>deterministic receipt</b> per template.</div>

              <div style={{ marginTop: 8 }}>
                <b>We are testing for</b>: (1) <b>template selection</b>, (2) <b>template caching</b> (no re-sending schema every time),
                and (3) a receipt that binds <code>template_id + template_sha256 + bytes</code> into <code>drift_sha256</code>.
              </div>

              <div style={{ marginTop: 8 }}>
                <b>Why it matters</b>: this is the “product” unlock — you can carry logs, metrics, traces (different shapes) through the same pipeline
                without losing verifiability or efficiency.
              </div>
            </div>
          </div>

          {/* Raw */}
          <div style={{ gridColumn: "1 / -1", borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Raw response</div>
            <pre style={{ marginTop: 8, fontSize: 11, color: "#111827", whiteSpace: "pre-wrap" }}>
              {JSON.stringify(out, null, 2)}
            </pre>
          </div>
        </div>
      ) : null}

      <div style={{ marginTop: 12, borderRadius: 12, border: "1px solid #e5e7eb", background: "#f9fafb", padding: 10, fontSize: 11, color: "#6b7280" }}>
        Endpoints:
        <div style={{ marginTop: 6 }}><code>POST /api/wirepack/v12/catalog</code></div>
        <div style={{ marginTop: 4 }}><code>POST /api/wirepack/v12/mint</code></div>
      </div>
    </div>
  );
};