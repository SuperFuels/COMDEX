import React, { useEffect, useMemo, useState } from "react";

async function fetchJson(url: string, body?: any, timeoutMs = 20000, method: "GET" | "POST" = "POST") {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const init: RequestInit = {
      method,
      headers: { "Content-Type": "application/json" },
      signal: ctrl.signal,
    };
    if (method === "POST") init.body = JSON.stringify(body ?? {});
    const r = await fetch(url, init);
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

// -----------------------------------------------------------------------------
// v12 LOCK-BACKED BENCH (pinned)
// backend/tests/glyphos_wirepack_v12_multitemplate_catalog_benchmark.py
// env: depth=30 families=8 messages=4096 mutate=1.0 seed=1337 skew=0.8
// stdout sha256: 2352c10f8fc74037cecc7a4a913736f0c0a56893e6acc164a31a505a9f34e11c
// script  sha256: 7877073a53831c1a9e0ab35c6558b3cd37f48cad2e2c6c04d4d6cf2a203fb6f6
// -----------------------------------------------------------------------------
const V12_LOCK = {
  run: {
    depth: 30,
    families: 8,
    messages: 4096,
    mutate_rate: 1.0,
    seed: 1337,
    skew: 0.8,
  },
  baselines_gzip_avg_bytes: {
    json: 257.479,
    fallback: 217.246,
    catalog: 167.277,
  },
  handshake_overhead_gz_bytes: 97,
  roundtrip_fail: { fail: 0, total: 4096 },
  out_sha256: "2352c10f8fc74037cecc7a4a913736f0c0a56893e6acc164a31a505a9f34e11c",
  script_sha256: "7877073a53831c1a9e0ab35c6558b3cd37f48cad2e2c6c04d4d6cf2a203fb6f6",
};

function pctDelta(wire: number, baseline: number): number | null {
  if (!baseline || baseline <= 0) return null;
  return (wire / baseline - 1) * 100;
}

function pctSavings(baseline: number, better: number): number | null {
  if (!baseline || baseline <= 0) return null;
  return (1 - better / baseline) * 100;
}

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

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setCatalogErr(null);
        let res = await fetchJson("/api/wirepack/v12/catalog", undefined, 12000, "GET");
        if (!res.ok) res = await fetchJson("/api/wirepack/v12/catalog", {}, 12000, "POST");
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${JSON.stringify(res.json)}`);
        if (!alive) return;

        const list =
          (Array.isArray(res.json?.templates) && res.json.templates) ||
          (Array.isArray(res.json?.catalog?.templates) && res.json.catalog.templates) ||
          [];
        setTemplates(list);

        if (list.length && !list.some((x: any) => x?.id === templateId)) setTemplateId(String(list[0].id));
      } catch (e: any) {
        if (!alive) return;
        setCatalogErr(e?.message || String(e));
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const t = useMemo(() => templates.find((x) => x.id === templateId) || null, [templates, templateId]);

  async function mint() {
    if (busy) return;
    setBusy(true);
    setErr(null);
    setOut(null);

    try {
      const body = { template_id: templateId, seed, n, turns, muts };
      const { ok, status, json } = await fetchJson("/api/wirepack/v12/mint", body, 25000, "POST");
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

  const leanRaw = receipts?.LEAN_OK ?? receipt?.LEAN_OK ?? out?.LEAN_OK ?? out?.lean_ok ?? null;
  const leanOk = leanRaw === 1 || leanRaw === true ? true : leanRaw === 0 ? false : null;
  const lean = badge(leanOk);

  const cacheHit = inv?.cache_hit ?? receipt?.cache_hit ?? out?.cache_hit ?? null;
  const cacheLabel = cacheHit === true ? "CACHE HIT" : cacheHit === false ? "CACHE MISS" : "—";

  const wireTotal = Number(b?.wire_total_bytes ?? receipt?.wire_total_bytes ?? out?.wire_total_bytes ?? 0);

  // LOCKED baselines (gzip avg bytes per message)
  const baseJson = V12_LOCK.baselines_gzip_avg_bytes.json;
  const baseFallback = V12_LOCK.baselines_gzip_avg_bytes.fallback;
  const baseCatalog = V12_LOCK.baselines_gzip_avg_bytes.catalog;

  // If API is returning a per-request wire_total_bytes, compare that to locked baselines *as a reference*.
  // (This is “apples-to-oranges” unless your backend wire_total_bytes corresponds to the same per-message measure.)
  // So we present locked bench primarily, and show wire_total_bytes separately.
  const savingsVsJson = pctSavings(baseJson, baseCatalog);
  const savingsVsFallback = pctSavings(baseFallback, baseCatalog);

  // UI helper: label deltas correctly
  const fmtDelta = (d: number | null) =>
    d == null ? "—" : `${d > 0 ? "+" : ""}${d.toFixed(1)}%`;

  // Optional: if you want to show how wire_total compares to baselines (note: not same unit)
  const wireVsJsonPct = pctDelta(wireTotal, baseJson);
  const wireVsFallbackPct = pctDelta(wireTotal, baseFallback);
  const wireVsCatalogPct = pctDelta(wireTotal, baseCatalog);

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 900, color: "#111827" }}>
            v12 — Multi-template catalog (lock-backed)
          </div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Mixed-shape transport via catalog template_id; cache + deterministic receipt. Bench numbers pinned to stdout/script locks.
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <div
            style={{
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
            }}
          >
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

      <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "2fr repeat(4, 1fr)", gap: 8 }}>
        <label style={{ fontSize: 11, color: "#374151" }}>
          template
          <select
            value={templateId}
            onChange={(e) => setTemplateId(String(e.target.value))}
            style={{ width: "100%", marginTop: 4, padding: "6px 8px", borderRadius: 10, border: "1px solid #e5e7eb", background: "#fff" }}
          >
            {templates.length ? (
              templates.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.title}
                </option>
              ))
            ) : (
              <option value="metrics_v1">metrics_v1</option>
            )}
          </select>
          <div style={{ marginTop: 4, fontSize: 10, color: "#6b7280" }}>
            {t?.blurb || (catalogErr ? "catalog unavailable" : "—")}
          </div>
        </label>

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
            max={1_000_000}
            onChange={(e) => setN(Math.max(256, Math.min(1_000_000, Number(e.target.value) || 4096)))}
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
      </div>

      {catalogErr ? <div style={{ marginTop: 8, fontSize: 11, color: "#b91c1c" }}>catalog: {catalogErr}</div> : null}
      {err ? <div style={{ marginTop: 8, fontSize: 11, color: "#b91c1c" }}>{err}</div> : null}

      {/* LOCKED BENCH PANEL (always visible) */}
      <div style={{ marginTop: 12, borderRadius: 12, border: "1px solid #e5e7eb", padding: 10, background: "#f9fafb" }}>
        <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Locked benchmark (authoritative)</div>

        <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div>
            <div style={{ fontSize: 11, color: "#374151" }}>
              Avg JSON (gzip): <b>{baseJson.toFixed(3)} B</b>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              Avg Fallback (gzip): <b>{baseFallback.toFixed(3)} B</b>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              Avg Catalog msg (gzip): <b>{baseCatalog.toFixed(3)} B</b>
            </div>
          </div>

          <div>
            <div style={{ fontSize: 11, color: "#374151" }}>
              Savings vs JSON (gzip):{" "}
              <b style={{ color: (savingsVsJson ?? 0) >= 0 ? "#065f46" : "#991b1b" }}>
                {savingsVsJson == null ? "—" : `${savingsVsJson.toFixed(2)}%`}
              </b>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              Savings vs fallback (gzip):{" "}
              <b style={{ color: (savingsVsFallback ?? 0) >= 0 ? "#065f46" : "#991b1b" }}>
                {savingsVsFallback == null ? "—" : `${savingsVsFallback.toFixed(2)}%`}
              </b>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              Handshake overhead (gzip): <b>{V12_LOCK.handshake_overhead_gz_bytes} B</b>{" "}
              <span style={{ color: "#6b7280" }}>(one-time)</span>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 10, fontSize: 11, color: "#374151" }}>
          Roundtrip failures:{" "}
          <b style={{ color: V12_LOCK.roundtrip_fail.fail === 0 ? "#065f46" : "#991b1b" }}>
            {V12_LOCK.roundtrip_fail.fail}/{V12_LOCK.roundtrip_fail.total}
          </b>
        </div>

        <div style={{ marginTop: 10, borderTop: "1px solid #e5e7eb", paddingTop: 10, fontSize: 10, color: "#6b7280" }}>
          Locked run: depth={V12_LOCK.run.depth}, families={V12_LOCK.run.families}, messages={V12_LOCK.run.messages}, mutate={V12_LOCK.run.mutate_rate},
          seed={V12_LOCK.run.seed}, skew={V12_LOCK.run.skew}
        </div>

        <div style={{ marginTop: 8, fontSize: 10, color: "#6b7280" }}>
          Audit locks:
          <div style={{ marginTop: 6 }}>
            stdout sha256: <code>{V12_LOCK.out_sha256}</code>
          </div>
          <div style={{ marginTop: 4 }}>
            script sha256: <code>{V12_LOCK.script_sha256}</code>
          </div>
        </div>
      </div>

      {/* LIVE MINT RESULT (optional) */}
      {out ? (
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Template / Cache</div>

            <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
              template_id: <b>{String(receipt?.template_id || "—")}</b>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              cache: <b style={{ color: cacheHit === true ? "#065f46" : cacheHit === false ? "#991b1b" : "#374151" }}>{cacheLabel}</b>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              template_sha256: <code>{String(receipt?.template_sha256 || "—")}</code>
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280" }}>
              fields: <code>{t?.fields ? t.fields.map((f) => `${f.name}:${f.type}`).join(", ") : "—"}</code>
            </div>
          </div>

          <div style={{ borderRadius: 12, border: "1px solid #e5e7eb", padding: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Receipt (from API)</div>

            <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
              template_bytes: <b>{bytes(Number(b?.template_bytes || 0))}</b>{" "}
              <span style={{ color: "#6b7280" }}>({b?.template_bytes ?? 0} B)</span>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              delta_bytes_total: <b>{bytes(Number(b?.delta_bytes_total || 0))}</b>{" "}
              <span style={{ color: "#6b7280" }}>({b?.delta_bytes_total ?? 0} B)</span>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
              wire_total_bytes: <b>{bytes(wireTotal)}</b>{" "}
              <span style={{ color: "#6b7280" }}>({wireTotal} B)</span>
            </div>

            <div style={{ marginTop: 10, borderRadius: 12, border: "1px solid #e5e7eb", background: "#fff", padding: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Reference deltas (note: unit mismatch)</div>
              <div style={{ marginTop: 8, fontSize: 10, color: "#6b7280", lineHeight: 1.55 }}>
                The locked baselines are <b>avg gzip bytes per message</b> from the v12 benchmark. The API’s <code>wire_total_bytes</code> is a
                request-level estimate. We show these deltas only as a rough reference.
              </div>

              <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                wire_total vs Avg JSON(gz):{" "}
                <b style={{ color: (wireVsJsonPct ?? 0) <= 0 ? "#065f46" : "#991b1b" }}>{fmtDelta(wireVsJsonPct)}</b>
              </div>
              <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                wire_total vs Avg Fallback(gz):{" "}
                <b style={{ color: (wireVsFallbackPct ?? 0) <= 0 ? "#065f46" : "#991b1b" }}>{fmtDelta(wireVsFallbackPct)}</b>
              </div>
              <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                wire_total vs Avg Catalog(gz):{" "}
                <b style={{ color: (wireVsCatalogPct ?? 0) <= 0 ? "#065f46" : "#991b1b" }}>{fmtDelta(wireVsCatalogPct)}</b>
              </div>
            </div>

            <div style={{ marginTop: 10, fontSize: 11, color: "#6b7280" }}>
              drift_sha256: <code>{String(receipts?.drift_sha256 || receipt?.drift_sha256 || "—")}</code>
            </div>

            <div style={{ marginTop: 6, fontSize: 11, color: "#6b7280" }}>
              final_state_sha256: <code>{String(receipt?.final_state_sha256 || "—")}</code>
            </div>
          </div>

          <div style={{ gridColumn: "1 / -1", borderRadius: 12, border: "1px solid #e5e7eb", padding: 10, background: "#f9fafb" }}>
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>What this demo proves</div>

            <div style={{ marginTop: 8, fontSize: 11, color: "#374151", lineHeight: 1.55 }}>
              <div>
                <b>Claim</b>: the transport layer supports <b>multiple data shapes</b> (catalog templates) while minting a{" "}
                <b>deterministic receipt</b>.
              </div>
              <div style={{ marginTop: 8 }}>
                <b>We test</b>: (1) <b>template selection</b>, (2) <b>cache behavior</b>, and (3) receipt binding of{" "}
                <code>template_id + template_sha256 + bytes</code> into <code>drift_sha256</code>.
              </div>
              <div style={{ marginTop: 8 }}>
                <b>Important</b>: the locked benchmark demonstrates <b>multi-template traffic</b> (families=8) with skewed distribution and 0 roundtrip failures.
              </div>
            </div>
          </div>

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
        <div style={{ marginTop: 6 }}>
          <code>GET/POST /api/wirepack/v12/catalog</code>
        </div>
        <div style={{ marginTop: 4 }}>
          <code>POST /api/wirepack/v12/mint</code>
        </div>
      </div>
    </div>
  );
};