// Glyph_Net_Browser/src/components/QfcBioDashboard.tsx
"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  gx1DownloadAllArtifacts,
  gx1DownloadRunFile,
  gx1FetchRunFile,
  gx1Inspect,
  gx1Run,
  gx1Verify,
} from "@/lib/gx1Client";

type VerifyLine = { text: string; ok: boolean };

function parseSha256RelList(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => {
      // sha256sum format: "<hash>  <filename>"
      const parts = l.split(/\s+/);
      if (parts.length < 2) return null;
      return parts[parts.length - 1];
    })
    .filter((x): x is string => !!x);
}

class DashboardErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: any }> {
  state = { error: null as any };
  static getDerivedStateFromError(error: any) {
    return { error };
  }
  componentDidCatch(error: any, info: any) {
    console.error("[QfcBioDashboard] crashed:", error, info);
  }
  render() {
    if (this.state.error) {
      const msg =
        typeof this.state.error === "string"
          ? this.state.error
          : this.state.error?.message
            ? String(this.state.error.message)
            : String(this.state.error);

      return (
        <div style={{ padding: 12 }}>
          <div
            style={{
              borderRadius: 14,
              border: "1px solid #fecaca",
              background: "#fff1f2",
              padding: 14,
              color: "#7f1d1d",
              boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
              fontFamily: "ui-monospace, Menlo, monospace",
              fontSize: 12,
              whiteSpace: "pre-wrap",
            }}
          >
            <div style={{ fontWeight: 800, marginBottom: 8 }}>QfcBioDashboard crashed (no more white screen)</div>
            {msg}
            <div style={{ marginTop: 10, opacity: 0.85 }}>Check DevTools Console for the stack trace.</div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}


function InnerDashboard() {
  // Inputs
  const [manifestText, setManifestText] = useState<string>("");
  const [datasetInfo, setDatasetInfo] = useState<{
    name?: string;
    bytes?: number;
    lines?: number;
    preview?: string[];
  }>({});
  const [datasetFile, setDatasetFile] = useState<File | null>(null);

  // Params
  const [keyMode, setKeyMode] = useState<"matched" | "mismatch" | "multiplex" | "mutation">("matched");
  const [seed, setSeed] = useState<number>(1337);
  const [k, setK] = useState<number>(2);
  const [mutationSeverity, setMutationSeverity] = useState<number>(4);
  const [deterministic, setDeterministic] = useState<boolean>(true);

  // SQI / ledger controls (NOW REAL UI)
  const [sqiExportBundle, setSqiExportBundle] = useState<boolean>(false);
  const [sqiStageFabric, setSqiStageFabric] = useState<boolean>(false);
  const [ledgerExportKgWrite, setLedgerExportKgWrite] = useState<boolean>(false);

  // Exec
  const [execMode, setExecMode] = useState<"A" | "B">("A");

  // Run selection / status
  const [runId, setRunId] = useState<string>("");
  const [status, setStatus] = useState<"OK" | "WARN" | "FAIL">("OK");

  const [busy, setBusy] = useState<null | "run" | "inspect" | "verify">(null);
  const [lastError, setLastError] = useState<string>("");

  // ✅ autorun latch for editor -> dashboard bridge
  const pendingAutorunRef = useRef(false);

  // Outputs
  const [metricsJson, setMetricsJson] = useState<any>(null);
  const [runFiles, setRunFiles] = useState<Record<string, string>>({});
  const [indexText, setIndexText] = useState<string>("");
  const [sha256Text, setSha256Text] = useState<string>("");
  const [verifyOut1, setVerifyOut1] = useState<VerifyLine[] | null>(null);
  const [verifyOut2, setVerifyOut2] = useState<VerifyLine[] | null>(null);

  const artifactRelList = useMemo(() => {
    const s = new Set<string>();

    // from Inspect
    for (const k of Object.keys(runFiles || {})) s.add(k);

    // from ARTIFACTS.sha256 (run-local truth)
    for (const k of parseSha256RelList(sha256Text || "")) s.add(k);

    const preferred = [
      "CONFIG.json",
      "METRICS.json",
      "TRACE.jsonl",
      "REPLAY_BUNDLE.json",
      "LEDGER.jsonl",
      "SQI_KG_WRITES.jsonl",
      "ARTIFACTS_INDEX.md",
      "ARTIFACTS.sha256",
    ];

    const prefIndex = new Map(preferred.map((v, i) => [v, i]));

    return Array.from(s).sort((a, b) => {
      const ia = prefIndex.has(a) ? (prefIndex.get(a) as number) : 9999;
      const ib = prefIndex.has(b) ? (prefIndex.get(b) as number) : 9999;
      if (ia !== ib) return ia - ib;
      return a.localeCompare(b);
    });
  }, [runFiles, sha256Text]);

  const [runMeta, setRunMeta] = useState<{
    phase_root?: string;
    run_dir?: string;
    trace_digest?: string;
    sqi_stage?: string;
  } | null>(null);

  // ---------------------------------------------------------------------------
  // gx1.fill_inputs bridge: accept manifestText + datasetText from editor/pad
  // ---------------------------------------------------------------------------
  useEffect(() => {
    async function onFill(ev: any) {
      const d = ev?.detail || {};

      if (typeof d.manifestText === "string") {
        setManifestText(d.manifestText);
      }

      if (typeof d.datasetText === "string") {
        const name = typeof d.datasetName === "string" ? d.datasetName : "gx1_dataset.jsonl";
        const file = new File([d.datasetText], name, { type: "text/plain" });

        setDatasetFile(file);
        const txt = await file.text();
        const lines = txt.split(/\r?\n/).filter((l) => l.length > 0);
        setDatasetInfo({
          name: file.name,
          bytes: file.size,
          lines: lines.length,
          preview: lines.slice(0, 3),
        });
      }

      if (d.runAfter) {
        pendingAutorunRef.current = true;
      }
    }

    if (typeof window !== "undefined") {
      window.addEventListener("gx1.fill_inputs", onFill as any);
      return () => window.removeEventListener("gx1.fill_inputs", onFill as any);
    }
    return;
  }, []);

  // if runAfter was requested, trigger Run once both manifest + dataset are loaded
  useEffect(() => {
    if (!pendingAutorunRef.current) return;
    if (busy !== null) return;
    if (!manifestText.trim()) return;
    if (!datasetFile) return;

    pendingAutorunRef.current = false;
    void apiRun();
  }, [busy, manifestText, datasetFile]);

  function setErr(e: any) {
    const msg = typeof e === "string" ? e : e?.message ? String(e.message) : String(e);
    setLastError(msg);
    console.error(e);
  }

  function formatJson() {
    try {
      const obj = JSON.parse(manifestText);
      setManifestText(JSON.stringify(obj, null, 2));
    } catch {
      // ignore
    }
  }

  const handleDatasetUpload = useCallback(async (file: File) => {
    setDatasetFile(file);

    const txt = await file.text();
    const lines = txt.split(/\r?\n/).filter((l) => l.length > 0);
    setDatasetInfo({
      name: file.name,
      bytes: file.size,
      lines: lines.length,
      preview: lines.slice(0, 3),
    });
  }, []);

    function inferMissingRunFiles(files: Record<string, string>) {
    const out: Record<string, string> = { ...(files || {}) };

    // infer base dir from any known artifact path: ".../<run_dir>/<REL>"
    let base = "";
    for (const rel of Object.keys(out)) {
      const abs = out[rel];
      if (abs && abs.endsWith("/" + rel)) {
        base = abs.slice(0, abs.length - (rel.length + 1));
        break;
      }
    }
    if (!base) return out;

    // ensure these show up with real paths (and gx1Download helpers have something to use)
    const must = ["LEDGER.jsonl", "SQI_KG_WRITES.jsonl"];
    for (const rel of must) {
      if (!out[rel]) out[rel] = `${base}/${rel}`;
    }
    return out;
  }

  async function apiInspect(selectedRunId: string) {
    setBusy("inspect");
    setLastError("");
    try {
      const j = await gx1Inspect(selectedRunId);
      const rid = j.run_id || selectedRunId;

      setRunId(rid);
      const rawFiles: Record<string, string> = j.files || {};
      const files = inferMissingRunFiles(rawFiles);
      setRunFiles(files);
      setIndexText(j.index_text || "");
      setSha256Text(j.sha256_text || "");

      // Inline metrics support
      if (j.metrics) {
        setMetricsJson(j.metrics);
        const st = String(j.metrics?.status || "").toUpperCase();
        if (st === "OK") setStatus("OK");
        else if (st) setStatus("FAIL");
        return;
      }

      if (j.files?.["METRICS.json"]) {
        const res = await gx1FetchRunFile(rid, "METRICS.json");
        try {
          const mj = await res.json();
          setMetricsJson(mj);
          const st = String(mj?.status || "").toUpperCase();
          if (st === "OK") setStatus("OK");
          else if (st) setStatus("FAIL");
        } catch {
          setMetricsJson(null);
        }
      }
    } catch (e) {
      setStatus("FAIL");
      setErr(e);
      throw e;
    } finally {
      setBusy(null);
    }
  }

  async function apiVerify(selectedRunId: string) {
    setBusy("verify");
    setLastError("");
    try {
      const v = await gx1Verify(selectedRunId);
      setVerifyOut1(v.runChecks);
      setVerifyOut2(v.indexChecks);

      const anyFail = [...v.runChecks, ...v.indexChecks].some((x) => !x.ok);
      setStatus(anyFail ? "FAIL" : "OK");
    } catch (e) {
      setStatus("FAIL");
      setVerifyOut1([{ text: String((e as any)?.message || e), ok: false }]);
      setVerifyOut2([{ text: String((e as any)?.message || e), ok: false }]);
      setErr(e);
      throw e;
    } finally {
      setBusy(null);
    }
  }

  function effectiveSqiStage(): "off" | "bundle" | "fabric" {
    if (sqiStageFabric) return "fabric";
    if (sqiExportBundle) return "bundle";
    return "off";
  }

  async function apiRun() {
    setBusy("run");
    setLastError("");

    setMetricsJson(null);
    setRunFiles({});
    setIndexText("");
    setSha256Text("");
    setVerifyOut1(null);
    setVerifyOut2(null);

    try {
      if (!manifestText.trim()) throw new Error("Manifest is empty (Bucket A).");
      if (!datasetFile) throw new Error("Dataset file not selected (Bucket B).");

      if (execMode === "B") {
        throw new Error("Exec B (SLE/Beam) is not supported by gx1_api_min. Use Exec A (SIM).");
      }

      let manifestJson: any;
      try {
        manifestJson = JSON.parse(manifestText);
      } catch {
        throw new Error("Manifest JSON is invalid (Bucket A).");
      }

      const cfgKey = manifestJson.gx1_config ? "gx1_config" : manifestJson.config ? "config" : "gx1_config";
      manifestJson[cfgKey] = manifestJson[cfgKey] || {};

      // force seed lock when deterministic
      if (deterministic && Number.isFinite(seed)) {
        manifestJson[cfgKey].seed = seed;
      }

      // keep UI knobs, but do NOT put them in gx1_config (schema rejects it)
      manifestJson.exec = manifestJson.exec || {};
      manifestJson.exec.ui = {
        key_mode: keyMode,
        k,
        mutation_severity: mutationSeverity,
      };

      // exec contract
      manifestJson.exec = manifestJson.exec || {};
      manifestJson.exec.source = "SIM";
      manifestJson.exec.sqi_stage = effectiveSqiStage();
      manifestJson.exec.kg_write = !!ledgerExportKgWrite;

      setStatus("WARN");

      const j = await gx1Run({
        manifestJson,
        datasetFile,
        manifestFilename: "gx1_manifest.json",
      });

      setRunId(j.run_id);
      setRunMeta({
        phase_root: j.phase_root,
        run_dir: j.run_dir,
        trace_digest: j.trace_digest,
        sqi_stage: manifestJson.exec?.sqi_stage,
      });

      await apiInspect(j.run_id);
    } catch (e) {
      setStatus("FAIL");
      setErr(e);
      alert(String((e as any)?.message || e));
      throw e;
    } finally {
      setBusy(null);
    }
  }

  const inspectDisabled = !runId || busy === "run";
  const verifyDisabled = !runId || busy === "run";
  const runDisabled =
    busy !== null || !manifestText.trim() || !datasetFile || (deterministic && !Number.isFinite(seed));

  // ✅ NEW LAYOUT: top full-width (Run), bottom 2 columns (Inputs | Outputs)
  return (
    <div style={pageStyle}>
      <div style={dashboardWrapStyle}>
        {/* Top: Run / Inspect / Verify (full width) */}
        <section style={cardStyle}>
          <h3 style={h3Style}>Run / Inspect / Verify</h3>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <button
              type="button"
              style={{ ...btnStyle, ...(execMode === "A" ? btnActiveStyle : null) }}
              onClick={() => setExecMode("A")}
              disabled={busy !== null}
            >
              Exec A (SIM Reference){execMode === "A" ? " ✓" : ""}
            </button>

            <button
              type="button"
              style={{ ...btnStyle, ...(execMode === "B" ? btnActiveStyle : null) }}
              onClick={() => setExecMode("B")}
              disabled={busy !== null}
            >
              Exec B (SLE/Beam){execMode === "B" ? " ✓" : ""}
            </button>
          </div>

          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              style={{ ...primaryBtnStyle, ...(runDisabled ? btnDisabledStyle : null) }}
              onClick={() => void apiRun()}
              disabled={runDisabled}
            >
              {busy === "run" ? "Running…" : "Run GX1"}
            </button>

            <button
              type="button"
              style={{ ...btnStyle, ...(inspectDisabled ? btnDisabledStyle : null) }}
              onClick={() => runId && void apiInspect(runId)}
              disabled={inspectDisabled}
            >
              {busy === "inspect" ? "Inspecting…" : "Inspect"}
            </button>

            <button
              type="button"
              style={{ ...btnStyle, ...(verifyDisabled ? btnDisabledStyle : null) }}
              onClick={() => runId && void apiVerify(runId)}
              disabled={verifyDisabled}
            >
              {busy === "verify" ? "Verifying…" : "Verify"}
            </button>
          </div>

          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 13, color: "#6b7280" }}>Selected run_id</div>
            <input
              value={runId}
              onChange={(e) => setRunId(e.target.value)}
              placeholder="Paste run_id (e.g., P21_GX1_…)"
              style={{ ...inputStyle, width: "100%", marginTop: 6 }}
              disabled={busy === "run"}
            />

            <div style={{ marginTop: 10, fontSize: 12, color: "#6b7280" }}>
              Status: <strong style={{ color: statusColor(status) }}>{status}</strong>
            </div>

            {runMeta ? (
              <div style={{ marginTop: 10, fontSize: 12, color: "#6b7280", lineHeight: 1.35 }}>
                {runMeta.phase_root ? <div>phase_root: {runMeta.phase_root}</div> : null}
                {runMeta.run_dir ? <div>run_dir: {runMeta.run_dir}</div> : null}
                {runMeta.trace_digest ? <div>trace_digest: {runMeta.trace_digest}</div> : null}
                {runMeta.sqi_stage ? <div>sqi_stage: {runMeta.sqi_stage}</div> : null}
              </div>
            ) : null}

            {lastError ? (
              <div style={{ marginTop: 10, fontSize: 12, color: "#b91c1c", whiteSpace: "pre-wrap" }}>{lastError}</div>
            ) : null}
          </div>

          <div style={{ marginTop: 14 }}>
            <h4 style={h4Style}>Verify output (raw)</h4>
            <VerifyPanel title="sha256sum -c checksums/$RUN_ID.sha256" lines={verifyOut1} />
            <VerifyPanel title="sha256sum -c ARTIFACTS_INDEX.sha256" lines={verifyOut2} />
          </div>

          <div style={{ marginTop: 14 }}>
            <h4 style={h4Style}>Primary actions</h4>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                type="button"
                style={btnStyle}
                onClick={() => navigator.clipboard?.writeText(runFiles?.["ARTIFACTS_INDEX.md"] || "")}
              >
                Copy run-local index path
              </button>
              <button
                type="button"
                style={btnStyle}
                onClick={() => navigator.clipboard?.writeText(runFiles?.["ARTIFACTS.sha256"] || "")}
              >
                Copy run-local sha path
              </button>
              <button type="button" style={btnStyle} onClick={() => setStatus("OK")}>
                Set OK
              </button>
              <button type="button" style={btnStyle} onClick={() => setStatus("WARN")}>
                Set WARN
              </button>
              <button type="button" style={btnStyle} onClick={() => setStatus("FAIL")}>
                Set FAIL
              </button>
            </div>
          </div>
        </section>

        {/* Bottom: Inputs | Outputs (two columns) */}
        <div style={twoColWrapStyle}>
          {/* Inputs */}
          <section style={cardStyle}>
            <h3 style={h3Style}>Inputs (Buckets)</h3>

            <div style={bucketStyle}>
              <div style={bucketHdrStyle}>
                <strong>Bucket A — Manifest</strong>
                <div style={{ display: "flex", gap: 8 }}>
                  <button type="button" style={btnStyle} onClick={formatJson} disabled={busy !== null}>
                    Format JSON
                  </button>
                </div>
              </div>

              <input
                type="file"
                accept="application/json,.json"
                disabled={busy !== null}
                onChange={async (e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  setManifestText(await f.text());
                }}
              />

              <textarea
                value={manifestText}
                onChange={(e) => setManifestText(e.target.value)}
                placeholder="Paste gx1_manifest.json here…"
                style={textareaStyle}
                disabled={busy !== null}
              />

              <label style={toggleRowStyle} title="(stub) implement localStorage later if desired">
                <input type="checkbox" disabled />
                <span>Use last manifest</span>
              </label>
            </div>

            <div style={bucketStyle}>
              <div style={bucketHdrStyle}>
                <strong>Bucket B — Dataset</strong>
              </div>

              <input
                type="file"
                accept="text/plain,.jsonl,.txt,application/jsonl"
                disabled={busy !== null}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  void handleDatasetUpload(f);
                }}
              />

              <div style={{ marginTop: 8, fontSize: 13, color: "#374151" }}>
                <div>
                  lines: {datasetInfo.lines ?? "—"} | bytes: {datasetInfo.bytes ?? "—"} | file: {datasetInfo.name ?? "—"}
                </div>

                <div style={previewBoxStyle}>
                  {(datasetInfo.preview || []).map((l, i) => (
                    <div key={i} style={previewLineStyle}>
                      {l}
                    </div>
                  ))}
                </div>
              </div>

              <label style={toggleRowStyle} title="(stub) implement localStorage later if desired">
                <input type="checkbox" disabled />
                <span>Use last dataset</span>
              </label>
            </div>

            <div style={bucketStyle}>
              <div style={bucketHdrStyle}>
                <strong>Bucket C — Keys / Params</strong>
              </div>

              <div style={rowStyle}>
                <label style={lblStyle}>Key mode</label>
                <select
                  value={keyMode}
                  onChange={(e) => setKeyMode(e.target.value as any)}
                  style={inputStyle}
                  disabled={busy !== null}
                >
                  <option value="matched">matched</option>
                  <option value="mismatch">mismatch</option>
                  <option value="multiplex">multiplex</option>
                  <option value="mutation">mutation</option>
                </select>
              </div>

              <div style={rowStyle}>
                <label style={lblStyle}>Seed</label>
                <input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(parseInt(e.target.value || "0", 10))}
                  style={inputStyle}
                  disabled={busy !== null}
                />
              </div>

              {(keyMode === "multiplex" || keyMode === "mutation") && (
                <div style={rowStyle}>
                  <label style={lblStyle}>k</label>
                  <input
                    type="number"
                    value={k}
                    onChange={(e) => setK(parseInt(e.target.value || "0", 10))}
                    style={inputStyle}
                    disabled={busy !== null}
                  />
                </div>
              )}

              {keyMode === "mutation" && (
                <div style={rowStyle}>
                  <label style={lblStyle}>Mutation severity</label>
                  <input
                    type="number"
                    value={mutationSeverity}
                    onChange={(e) => setMutationSeverity(parseInt(e.target.value || "0", 10))}
                    style={inputStyle}
                    disabled={busy !== null}
                  />
                </div>
              )}

              <label style={toggleRowStyle}>
                <input
                  type="checkbox"
                  checked={deterministic}
                  onChange={(e) => setDeterministic(e.target.checked)}
                  disabled={busy !== null}
                />
                <span>Deterministic (forces seed lock)</span>
              </label>

              <label style={toggleRowStyle}>
                <input
                  type="checkbox"
                  checked={sqiExportBundle}
                  onChange={(e) => {
                    const v = e.target.checked;
                    setSqiExportBundle(v);
                    if (!v) setSqiStageFabric(false);
                  }}
                  disabled={busy !== null}
                />
                <span>SQI export (bundle)</span>
              </label>

              <label style={toggleRowStyle}>
                <input
                  type="checkbox"
                  checked={sqiStageFabric}
                  onChange={(e) => {
                    const v = e.target.checked;
                    setSqiStageFabric(v);
                    if (v) setSqiExportBundle(true);
                  }}
                  disabled={busy !== null}
                />
                <span>SQI stage (fabric)</span>
              </label>

              <label style={toggleRowStyle}>
                <input
                  type="checkbox"
                  checked={ledgerExportKgWrite}
                  onChange={(e) => setLedgerExportKgWrite(e.target.checked)}
                  disabled={busy !== null}
                />
                <span>Ledger export (kg_write)</span>
              </label>

              <div style={{ marginTop: 8, fontSize: 12, color: "#6b7280" }}>
                Effective SQI stage: <strong>{effectiveSqiStage()}</strong>
              </div>
            </div>
          </section>

          {/* Outputs */}
          <section style={cardStyle}>
            <h3 style={h3Style}>Outputs / Evidence</h3>

            <div style={bucketStyle}>
              <strong>1) Metrics summary</strong>
              <div style={monoBlockStyle}>
                {metricsJson ? (
                  <>
                    <div>rho_matched: {metricsJson?.summary?.rho_matched ?? "—"}</div>
                    <div>rho_mismatch: {metricsJson?.summary?.rho_mismatch ?? "—"}</div>
                    <div>crosstalk_max: {metricsJson?.summary?.crosstalk_max ?? "—"}</div>
                    <div>coherence_mean: {metricsJson?.summary?.coherence_mean ?? "—"}</div>
                    <div>drift_mean: {metricsJson?.summary?.drift_mean ?? "—"}</div>
                  </>
                ) : (
                  <div>— (load by Inspect)</div>
                )}
              </div>
            </div>

            <div style={bucketStyle}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}>
                <strong>2) Artifacts</strong>
                <button
                  type="button"
                  style={{ ...btnStyle, ...(artifactRelList.length ? null : btnDisabledStyle) }}
                  disabled={!runId || !artifactRelList.length}
                  onClick={() => {
                    if (!runId) return;
                    const m: Record<string, string> = {};
                    for (const rel of artifactRelList) m[rel] = runFiles?.[rel] || "";
                    gx1DownloadAllArtifacts(runId, m);
                  }}
                >
                  Download all
                </button>
              </div>

              <div style={{ marginTop: 8 }}>
                {artifactRelList.length ? (
                  artifactRelList.map((rel) => {
                    const abs = runFiles?.[rel] || "";
                    const isSqi = rel === "SQI_KG_WRITES.jsonl";
                    return (
                      <div key={rel} style={artifactRowStyle}>
                        <div style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 12 }}>
                          {rel} {isSqi ? <span style={{ marginLeft: 8, fontSize: 11, opacity: 0.8 }}>(SQI)</span> : null}
                        </div>

                        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                          <div style={artifactPathStyle} title={abs || ""}>
                            {abs || "—"}
                          </div>

                          <button
                            type="button"
                            style={miniBtnStyle}
                            disabled={!runId}
                            onClick={() => runId && gx1DownloadRunFile(runId, rel)}
                          >
                            Download
                          </button>

                          <button
                            type="button"
                            style={miniBtnStyle}
                            onClick={() => navigator.clipboard?.writeText(rel)}
                            title="Copy relative filename (rel)"
                          >
                            Copy rel
                          </button>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div style={monoBlockStyle}>— (load by Inspect)</div>
                )}
              </div>
            </div>

            <div style={bucketStyle}>
              <strong>3) Run-local ARTIFACTS_INDEX.md</strong>
              <pre style={preStyle}>{indexText || "—"}</pre>
            </div>

            <div style={bucketStyle}>
              <strong>4) Run-local ARTIFACTS.sha256</strong>
              <pre style={preStyle}>{sha256Text || "—"}</pre>
            </div>

            <div style={bucketStyle}>
              <strong>Audit Registry live feed (v1 stub)</strong>
              <div style={{ marginTop: 8, fontSize: 13, color: "#4b5563" }}>
                Wire a stream here during run finalization:
                <ul style={{ marginTop: 8, marginBottom: 0 }}>
                  <li>write CONFIG.json … sha256 …</li>
                  <li>write METRICS.json … sha256 …</li>
                  <li>write checksums/&lt;run&gt;.sha256 …</li>
                  <li>finalize_run_artifacts … ARTIFACTS_INDEX.md … ARTIFACTS.sha256 …</li>
                </ul>
              </div>
            </div>

            <div style={bucketStyle}>
              <strong>Warmup vs Eval windowing on rho trace (v1 slot)</strong>
              <div style={{ marginTop: 8, fontSize: 13, color: "#4b5563" }}>
                Add sparklines in Scenario summaries with Nwarm shaded + Neval highlighted.
              </div>
            </div>

            <div style={bucketStyle}>
              <strong>SQI Fabric expansion tree</strong>
              <div style={{ marginTop: 8, fontSize: 13, color: "#4b5563" }}>
                {effectiveSqiStage() === "fabric" ? (
                  <div style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 12 }}>
                    Run → Scenario → Channel → Container → Write-intents
                    <div style={{ opacity: 0.8, marginTop: 6 }}>(wire UCS statuses: Materializing / Executing / Write-back)</div>
                  </div>
                ) : (
                  <div>— (enable SQI stage)</div>
                )}
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

export default function QfcBioDashboard() {
  return (
    <DashboardErrorBoundary>
      <InnerDashboard />
    </DashboardErrorBoundary>
  );
}

function VerifyPanel({ title, lines }: { title: string; lines: VerifyLine[] | null }) {
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 6 }}>{title}</div>
      <div style={verifyBoxStyle}>
        {lines ? (
          lines.map((l, i) => (
            <div
              key={i}
              style={{
                color: l.ok ? "#16a34a" : "#dc2626",
                fontFamily: "ui-monospace, Menlo, monospace",
                fontSize: 12,
                whiteSpace: "pre-wrap",
              }}
            >
              {l.text}
            </div>
          ))
        ) : (
          <div style={{ opacity: 0.7, fontFamily: "ui-monospace, Menlo, monospace", fontSize: 12 }}>—</div>
        )}
      </div>
    </div>
  );
}

function statusColor(s: "OK" | "WARN" | "FAIL") {
  if (s === "OK") return "#16a34a";
  if (s === "WARN") return "#d97706";
  return "#dc2626";
}

/* =========================
   Styles
   ========================= */

const pageStyle: React.CSSProperties = { padding: 0, margin: 0, width: "100%", boxSizing: "border-box" };

// 🔧 ALSO: replace your old gridWrapStyle with THESE two styles (same Styles section as before):

const dashboardWrapStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 12,
  width: "100%",
  alignItems: "stretch",
  boxSizing: "border-box",
};

// auto-fit makes it behave well on narrow screens without media queries
const twoColWrapStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))",
  gap: 12,
  width: "100%",
  alignItems: "start",
  boxSizing: "border-box",
};

const cardStyle: React.CSSProperties = {
  borderRadius: 14,
  border: "1px solid #e5e7eb",
  background: "#ffffff",
  padding: 14,
  boxShadow: "0 1px 2px rgba(0,0,0,0.06), 0 10px 24px rgba(0,0,0,0.06)",
  color: "#111827",
  boxSizing: "border-box",
};

const h3Style: React.CSSProperties = { margin: "0 0 10px 0", fontSize: 14, fontWeight: 700, color: "#111827" };
const h4Style: React.CSSProperties = { margin: "14px 0 0 0", fontSize: 13, fontWeight: 700, color: "#111827" };

const bucketStyle: React.CSSProperties = {
  marginTop: 10,
  padding: 12,
  borderRadius: 12,
  border: "1px solid #e5e7eb",
  background: "#f9fafb",
};

const bucketHdrStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: 10,
  alignItems: "center",
  marginBottom: 8,
};

const textareaStyle: React.CSSProperties = {
  width: "100%",
  minHeight: 140,
  marginTop: 8,
  borderRadius: 10,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#111827",
  padding: 10,
  fontFamily: "ui-monospace, Menlo, monospace",
  fontSize: 12,
  boxSizing: "border-box",
};

const preStyle: React.CSSProperties = {
  marginTop: 8,
  marginBottom: 0,
  borderRadius: 10,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#111827",
  padding: 10,
  fontFamily: "ui-monospace, Menlo, monospace",
  fontSize: 12,
  maxHeight: 220,
  overflow: "auto",
  whiteSpace: "pre-wrap",
};

const rowStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "150px 1fr",
  gap: 10,
  alignItems: "center",
  marginTop: 8,
};

const lblStyle: React.CSSProperties = { fontSize: 13, color: "#374151" };

const inputStyle: React.CSSProperties = {
  borderRadius: 10,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#111827",
  padding: "8px 10px",
  fontSize: 13,
  boxSizing: "border-box",
};

const toggleRowStyle: React.CSSProperties = {
  display: "flex",
  gap: 8,
  alignItems: "center",
  marginTop: 10,
  fontSize: 13,
  color: "#374151",
};

const btnStyle: React.CSSProperties = {
  padding: "8px 10px",
  borderRadius: 10,
  border: "1px solid #7dd3fc",
  background: "#e0f2fe",
  color: "#075985",
  cursor: "pointer",
  fontSize: 13,
  boxShadow: "0 1px 1px rgba(0,0,0,0.04)",
};

const miniBtnStyle: React.CSSProperties = {
  padding: "6px 10px",
  borderRadius: 999,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#111827",
  cursor: "pointer",
  fontSize: 12,
};

const btnActiveStyle: React.CSSProperties = { border: "1px solid #38bdf8", background: "#bae6fd" };
const btnDisabledStyle: React.CSSProperties = { opacity: 0.55, cursor: "not-allowed" };

const primaryBtnStyle: React.CSSProperties = { ...btnStyle, background: "#38bdf8", border: "1px solid #38bdf8", color: "#ffffff" };

const verifyBoxStyle: React.CSSProperties = { border: "1px solid #e5e7eb", borderRadius: 10, padding: 10, background: "#ffffff" };

const monoBlockStyle: React.CSSProperties = {
  marginTop: 8,
  fontSize: 12,
  fontFamily: "ui-monospace, Menlo, monospace",
  color: "#111827",
};

const artifactRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
  padding: "8px 0",
  borderBottom: "1px dashed rgba(0,0,0,0.08)",
};

const artifactPathStyle: React.CSSProperties = {
  opacity: 0.75,
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
  maxWidth: 260,
  fontSize: 12,
};

const previewBoxStyle: React.CSSProperties = {
  marginTop: 6,
  fontFamily: "ui-monospace, Menlo, monospace",
  fontSize: 12,
  color: "#111827",
  opacity: 0.9,
};

const previewLineStyle: React.CSSProperties = { whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" };