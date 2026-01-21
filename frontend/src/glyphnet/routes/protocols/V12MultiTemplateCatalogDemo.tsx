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

    // Don’t send a body on GET (some servers/proxies will reject it)
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

// stable JSON so “raw bytes” isn’t field-order dependent
function stableStringify(x: any): string {
  const seen = new WeakSet<object>();
  const walk = (v: any): any => {
    if (v === null || typeof v !== "object") return v;
    if (seen.has(v)) throw new Error("cyclic json");
    seen.add(v);
    if (Array.isArray(v)) return v.map(walk);
    const out: any = {};
    for (const k of Object.keys(v).sort()) out[k] = walk(v[k]);
    return out;
  };
  return JSON.stringify(walk(x));
}

function utf8Len(s: string): number {
  try {
    return new TextEncoder().encode(s).length;
  } catch {
    return s.length;
  }
}

async function gzipLenUtf8(s: string): Promise<number | null> {
  try {
    // @ts-ignore
    if (typeof CompressionStream === "undefined") return null;
    const u8 = new TextEncoder().encode(s);
    // @ts-ignore
    const stream = new Blob([u8]).stream().pipeThrough(new CompressionStream("gzip"));
    const ab = await new Response(stream).arrayBuffer();
    return new Uint8Array(ab).length;
  } catch {
    return null;
  }
}

async function gzipStreamLenUtf8(parts: string[], sep = "\n"): Promise<number | null> {
  try {
    // @ts-ignore
    if (typeof CompressionStream === "undefined") return null;
    const joined = parts.join(sep);
    const u8 = new TextEncoder().encode(joined);
    // @ts-ignore
    const stream = new Blob([u8]).stream().pipeThrough(new CompressionStream("gzip"));
    const ab = await new Response(stream).arrayBuffer();
    return new Uint8Array(ab).length;
  } catch {
    return null;
  }
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

  const [rawJsonTotalBytes, setRawJsonTotalBytes] = useState<number | null>(null);
  const [gzipFrameTotalBytes, setGzipFrameTotalBytes] = useState<number | null>(null);
  const [gzipStreamTotalBytes, setGzipStreamTotalBytes] = useState<number | null>(null);
  const [baselineNote, setBaselineNote] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        setCatalogErr(null);

        // Try GET first (common), fall back to POST (your original)
        let res = await fetchJson("/api/wirepack/v12/catalog", undefined, 12000, "GET");
        if (!res.ok) res = await fetchJson("/api/wirepack/v12/catalog", {}, 12000, "POST");
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${JSON.stringify(res.json)}`);
        if (!alive) return;

        const list =
          (Array.isArray(res.json?.templates) && res.json.templates) ||
          (Array.isArray(res.json?.catalog?.templates) && res.json.catalog.templates) ||
          [];
        setTemplates(list);

        // If current templateId not present, snap to first available
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

    setRawJsonTotalBytes(null);
    setGzipFrameTotalBytes(null);
    setGzipStreamTotalBytes(null);
    setBaselineNote(null);

    try {
      const body = { template_id: templateId, seed, n, turns, muts };

      const { ok, status, json } = await fetchJson("/api/wirepack/v12/mint", body, 25000, "POST");
      if (!ok) throw new Error(`HTTP ${status}: ${JSON.stringify(json)}`);
      setOut(json);

      const receipt = json?.receipt || {};
      const samples: any[] | null =
        Array.isArray(receipt?.baseline_samples) ? receipt.baseline_samples :
        Array.isArray(json?.baseline_samples) ? json.baseline_samples :
        null;

      const parts: string[] = [];

      if (samples && samples.length) {
        // IMPORTANT: if backend already gives canonical JSON strings, don’t re-stringify them
        for (const s of samples) {
          if (typeof s === "string") parts.push(s);
          else parts.push(stableStringify(s));
        }
      } else {
        const maxTurns = Math.max(1, Math.min(256, Number(turns || 1)));
        const maxMuts = Math.max(1, Math.min(32, Number(muts || 1)));

        const baseMsg: any =
          templateId === "metrics_v1"
            ? { cpu: 0.12, mem: 0.34, p95_ms: 12.3 }
            : { template_id: templateId, value: 0 };

        let x = (seed >>> 0) || 1;
        const R = () => {
          x ^= (x << 13) >>> 0;
          x ^= (x >>> 17) >>> 0;
          x ^= (x << 5) >>> 0;
          return x >>> 0;
        };

        let cur = baseMsg;
        for (let i = 0; i < maxTurns; i++) {
          const msg = typeof structuredClone === "function" ? structuredClone(cur) : JSON.parse(JSON.stringify(cur));
          for (let j = 0; j < maxMuts; j++) {
            const r = R();
            if ("cpu" in msg) msg.cpu = Number(msg.cpu) + (((r % 7) - 3) * 0.001);
            if ("mem" in msg) msg.mem = Number(msg.mem) + ((((r >>> 3) % 7) - 3) * 0.001);
            if ("p95_ms" in msg) msg.p95_ms = Number(msg.p95_ms) + ((((r >>> 6) % 5) - 2) * 0.1);
            msg._t = i;
          }
          parts.push(stableStringify(msg));
          cur = msg;
        }
        setBaselineNote("baselines = client-side synthetic stream (bounded); backend can optionally return baseline_samples for exactness");
      }

      let rawTotal = 0;
      for (const p of parts) rawTotal += utf8Len(p);
      setRawJsonTotalBytes(rawTotal);

      let gzFrameKnown = true;
      let gzFrameTotal = 0;
      for (const p of parts) {
        const g = await gzipLenUtf8(p);
        if (g == null) {
          gzFrameKnown = false;
          break;
        }
        gzFrameTotal += g;
      }
      setGzipFrameTotalBytes(gzFrameKnown ? gzFrameTotal : null);

      const gzStream = await gzipStreamLenUtf8(parts);
      setGzipStreamTotalBytes(gzStream);

      // @ts-ignore
      if (typeof CompressionStream === "undefined") {
        setBaselineNote((prev) => (prev ? prev + " · gzip unsupported in this browser" : "gzip unsupported in this browser"));
      }
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

  // Robust LEAN_OK sources (you were only checking out.receipts)
  const leanRaw =
    receipts?.LEAN_OK ?? receipt?.LEAN_OK ?? out?.LEAN_OK ?? out?.lean_ok ?? null;
  const leanOk = leanRaw === 1 || leanRaw === true ? true : leanRaw === 0 ? false : null;
  const lean = badge(leanOk);

  const cacheHit = inv?.cache_hit ?? receipt?.cache_hit ?? out?.cache_hit ?? null;
  const cacheLabel = cacheHit === true ? "CACHE HIT" : cacheHit === false ? "CACHE MISS" : "—";

  const wireTotal = Number(b?.wire_total_bytes ?? receipt?.wire_total_bytes ?? out?.wire_total_bytes ?? 0);

  const wireVsRawPct =
    rawJsonTotalBytes != null && rawJsonTotalBytes > 0 ? (wireTotal / rawJsonTotalBytes - 1) * 100 : null;

  const wireVsGzFramePct =
    gzipFrameTotalBytes != null && gzipFrameTotalBytes > 0 ? (wireTotal / gzipFrameTotalBytes - 1) * 100 : null;

  const wireVsGzStreamPct =
    gzipStreamTotalBytes != null && gzipStreamTotalBytes > 0 ? (wireTotal / gzipStreamTotalBytes - 1) * 100 : null;

  return (
    <div style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 12 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 900, color: "#111827" }}>v12 — Multi-template catalog</div>
          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>
            Multiple templates cached + selected; real-world shape variability; receipt per template.
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
            <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Receipt</div>

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
              <div style={{ fontSize: 11, fontWeight: 900, color: "#111827" }}>Baselines (client-side)</div>

              <div style={{ marginTop: 8, fontSize: 11, color: "#374151" }}>
                raw_json_total: <b>{rawJsonTotalBytes == null ? "—" : bytes(rawJsonTotalBytes)}</b>{" "}
                <span style={{ color: "#6b7280" }}>({rawJsonTotalBytes ?? "—"} B)</span>{" "}
                {wireVsRawPct != null ? (
                  <span style={{ color: wireVsRawPct <= 0 ? "#065f46" : "#991b1b", fontWeight: 900 }}>
                    {" "}({wireVsRawPct > 0 ? "+" : ""}{wireVsRawPct.toFixed(1)}%)
                  </span>
                ) : null}
              </div>

              <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                gzip_per_frame_total: <b>{gzipFrameTotalBytes == null ? "—" : bytes(gzipFrameTotalBytes)}</b>{" "}
                <span style={{ color: "#6b7280" }}>({gzipFrameTotalBytes ?? "—"} B)</span>{" "}
                {wireVsGzFramePct != null ? (
                  <span style={{ color: wireVsGzFramePct <= 0 ? "#065f46" : "#991b1b", fontWeight: 900 }}>
                    {" "}({wireVsGzFramePct > 0 ? "+" : ""}{wireVsGzFramePct.toFixed(1)}%)
                  </span>
                ) : (
                  <span style={{ color: "#6b7280" }}> (unsupported)</span>
                )}
              </div>

              <div style={{ marginTop: 6, fontSize: 11, color: "#374151" }}>
                gzip_stream_total: <b>{gzipStreamTotalBytes == null ? "—" : bytes(gzipStreamTotalBytes)}</b>{" "}
                <span style={{ color: "#6b7280" }}>({gzipStreamTotalBytes ?? "—"} B)</span>{" "}
                {wireVsGzStreamPct != null ? (
                  <span style={{ color: wireVsGzStreamPct <= 0 ? "#065f46" : "#991b1b", fontWeight: 900 }}>
                    {" "}({wireVsGzStreamPct > 0 ? "+" : ""}{wireVsGzStreamPct.toFixed(1)}%)
                  </span>
                ) : (
                  <span style={{ color: "#6b7280" }}> (unsupported)</span>
                )}
              </div>

              <div style={{ marginTop: 8, fontSize: 10, color: "#6b7280" }}>
                per-frame = gzip each message; stream = gzip across the whole run (stronger gzip).
                {baselineNote ? <span> · {baselineNote}</span> : null}
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
                <b>Claim</b>: the transport layer can support <b>multiple real-world data shapes</b> (templates) and still mint a <b>deterministic receipt</b> per template.
              </div>

              <div style={{ marginTop: 8 }}>
                <b>We are testing for</b>: (1) <b>template selection</b>, (2) <b>template caching</b>, and (3) a receipt that binds{" "}
                <code>template_id + template_sha256 + bytes</code> into <code>drift_sha256</code>.
              </div>

              <div style={{ marginTop: 8 }}>
                <b>WirePack vs baseline (messaging)</b>: baselines computed from a <b>message stream</b>, not the request body.
              </div>

              <div style={{ marginTop: 8 }}>
                <b>Why it matters</b>: logs/metrics/traces (different shapes) through the same pipeline without losing verifiability or efficiency.
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