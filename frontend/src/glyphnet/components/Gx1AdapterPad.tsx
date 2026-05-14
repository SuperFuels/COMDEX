// Glyph_Net_Browser/src/components/Gx1AdapterPad.tsx
import React, { useState } from "react";

export default function Gx1AdapterPad() {
  const [manifestText, setManifestText] = useState<string>("");
  const [datasetText, setDatasetText] = useState<string>("");

  function generatePilot() {
    const manifestObj = {
      gx1_config: {
        schemaVersion: "GX1_CONFIG_V0",
        objective_id: "P21_GX1_GENOMICS_BENCH_V0",
        seed: 1337,
        created_utc: "0000-00-00T00:00:00Z",
        mapping_id: "GX1_MAP_V1",
        chip_mode: "ONEHOT4",
        thresholds: {
          warmup_ticks: 128,
          eval_ticks: 512,
          rho_matched_min: 0.8,
          rho_mismatch_abs_max: 0.2,
          crosstalk_max: 0.2,
          coherence_mean_min: 0.8,
          drift_mean_max: 0.08,
        },
        scenarios: [
          { scenario_id: "matched_key", mode: "matched", k: 1, mutation: null },
          { scenario_id: "mismatched_key", mode: "mismatch", k: 1, mutation: null },
          { scenario_id: "multiplex_k2", mode: "multiplex", k: 2, mutation: null },
          { scenario_id: "mutation_ch0_sev4", mode: "mutation", k: 2, mutation: { target_channel: 0, severity: 4 } },
        ],
      },
      exec: { source: "SIM", sqi_stage: "off" },
    };

    const pilotLine = {
      id: "ex1",
      seq: "ACGTACGTACGTACGT",
      label: "pilot",
      channel_key: "A1",
      mutation: null,
    };

    setManifestText(JSON.stringify(manifestObj, null, 2));
    setDatasetText(`${JSON.stringify(pilotLine)}\n`);
  }

  function sendToGx1(runAfter: boolean) {
    window.dispatchEvent(
      new CustomEvent("gx1.fill_inputs", {
        detail: { manifestText, datasetText, datasetName: "pilot.jsonl", runAfter },
      }),
    );
  }

  return (
    <section style={{ borderRadius: 14, border: "1px solid #e5e7eb", background: "#fff", padding: 14, marginTop: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
        <div style={{ fontSize: 14, fontWeight: 800 }}>GX1 Adapter Pad (end-to-end demo)</div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" onClick={generatePilot}>Generate Pilot Inputs</button>
          <button type="button" onClick={() => sendToGx1(false)} disabled={!manifestText.trim() || !datasetText.trim()}>
            Send to GX1
          </button>
          <button type="button" onClick={() => sendToGx1(true)} disabled={!manifestText.trim() || !datasetText.trim()}>
            Send + Run
          </button>
        </div>
      </div>

      <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700 }}>Manifest (gx1_manifest.json)</div>
          <textarea value={manifestText} onChange={(e) => setManifestText(e.target.value)} style={{ width: "100%", minHeight: 160 }} />
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700 }}>Dataset (JSONL)</div>
          <textarea value={datasetText} onChange={(e) => setDatasetText(e.target.value)} style={{ width: "100%", minHeight: 160 }} />
        </div>
      </div>
    </section>
  );
}