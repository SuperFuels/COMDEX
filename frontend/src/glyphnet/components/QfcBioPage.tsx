// Glyph_Net_Browser/src/components/QfcBioPage.tsx
"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useTessarisTelemetry } from "../hooks/useTessarisTelemetry";
import { QFCHudPanel, type ScenarioId } from "../routes/DevTools";
import QfcBioDashboard from "./QfcBioDashboard";
import PhotonEditor from "./PhotonEditor";

type ToolId =
  | "editor"
  | "ledger"
  | "guide"
  | "pitch"
  | "field"
  | "qfc"
  | "qfc_bio"
  | "aion"
  | "crystal"
  | "gma"
  | "gma_auth"
  | "docs";

const PILOT_DATASET_JSONL = `{"id":"ex1","seq":"ACGTACGTACGTACGT","label":"pilot","channel_key":"A1","mutation":null}
`;

const PILOT_MANIFEST_JSON = `{
  "gx1_config": {
    "schemaVersion": "GX1_CONFIG_V0",
    "objective_id": "P21_GX1_GENOMICS_BENCH_V0",
    "seed": 1337,
    "created_utc": "0000-00-00T00:00:00Z",
    "dataset_path": "UPLOAD:pilot.jsonl",
    "output_root": "AUTO",
    "mapping_id": "GX1_MAP_V1",
    "chip_mode": "ONEHOT4",
    "thresholds": {
      "warmup_ticks": 128,
      "eval_ticks": 512,
      "rho_matched_min": 0.8,
      "rho_mismatch_abs_max": 0.2,
      "crosstalk_max": 0.2,
      "coherence_mean_min": 0.8,
      "drift_mean_max": 0.08
    },
    "scenarios": [
      { "scenario_id": "matched_key", "mode": "matched", "k": 1, "mutation": null },
      { "scenario_id": "mismatched_key", "mode": "mismatch", "k": 1, "mutation": null },
      { "scenario_id": "multiplex_k2", "mode": "multiplex", "k": 2, "mutation": null },
      { "scenario_id": "mutation_ch0_sev4", "mode": "mutation", "k": 2, "mutation": { "target_channel": 0, "severity": 4 } }
    ]
  },
  "exec": { "source": "SIM", "sqi_stage": "off", "kg_write": false }
}
`;

const miniBtn: React.CSSProperties = {
  padding: "8px 10px",
  borderRadius: 10,
  border: "1px solid #7dd3fc",
  background: "#e0f2fe",
  color: "#075985",
  cursor: "pointer",
  fontSize: 13,
  boxShadow: "0 1px 1px rgba(0,0,0,0.04)",
};

// keep in sync with DevTools.tsx ScenarioId union
const SCENARIO_IDS = ["BG01", "G01", "TN01", "MT01", "C01", "WH01", "GN01", "GO01"] as const;
function isScenarioId(v: any): v is ScenarioId {
  return typeof v === "string" && (SCENARIO_IDS as readonly string[]).includes(v);
}

function ToolButton({
  id,
  label,
  description,
  activeTool,
  onSelect,
}: {
  id: ToolId;
  label: string;
  description: string;
  activeTool: ToolId;
  onSelect: () => void;
}) {
  const active = activeTool === id;

  return (
    <button
      type="button"
      onClick={onSelect}
      style={{
        border: 0,
        cursor: "pointer",
        borderRadius: 999,
        padding: "8px 10px",
        background: active ? "#0b1220" : "transparent",
        color: active ? "#ffffff" : "#111827",
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "flex-start",
        gap: 1,
        minWidth: 110,
      }}
    >
      <div style={{ fontSize: 12, fontWeight: 700, lineHeight: 1 }}>{label}</div>
      <div style={{ fontSize: 10, lineHeight: 1, opacity: active ? 0.85 : 0.65, whiteSpace: "nowrap" }}>
        {description}
      </div>
    </button>
  );
}

// ✅ MUST be at module scope (NOT inside QfcBioPage)
function Gx1AdapterPad() {
  const [manifestText, setManifestText] = useState<string>("");
  const [datasetText, setDatasetText] = useState<string>("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const m = window.localStorage.getItem("gx1_adapter_manifest") || "";
    const d = window.localStorage.getItem("gx1_adapter_dataset") || "";
    if (!manifestText && m) setManifestText(m);
    if (!datasetText && d) setDatasetText(d);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("gx1_adapter_manifest", manifestText);
  }, [manifestText]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem("gx1_adapter_dataset", datasetText);
  }, [datasetText]);

  function generatePilot() {
    setManifestText(PILOT_MANIFEST_JSON.trim() + "\n");
    setDatasetText(PILOT_DATASET_JSONL);
  }

  function sendToGx1(runAfter: boolean) {
    if (typeof window === "undefined") return;

    window.dispatchEvent(
      new CustomEvent("gx1.fill_inputs", {
        detail: {
          manifestText,
          datasetText,
          datasetName: "pilot.jsonl",
          runAfter,
        },
      }),
    );
  }

  const canSend = manifestText.trim().length > 0 && datasetText.trim().length > 0;

  return (
    <section
      style={{
        borderRadius: 14,
        border: "1px solid #e5e7eb",
        background: "#ffffff",
        padding: 14,
        boxShadow: "0 1px 2px rgba(0,0,0,0.06), 0 10px 24px rgba(0,0,0,0.06)",
        marginTop: 10,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
        <div style={{ fontSize: 14, fontWeight: 800, color: "#111827" }}>GX1 Adapter Pad (end-to-end demo)</div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" onClick={generatePilot} style={miniBtn}>
            Generate Pilot Inputs
          </button>

          <button
            type="button"
            onClick={() => sendToGx1(false)}
            disabled={!canSend}
            style={{ ...miniBtn, opacity: canSend ? 1 : 0.55 }}
          >
            Send to GX1
          </button>

          <button
            type="button"
            onClick={() => sendToGx1(true)}
            disabled={!canSend}
            style={{
              ...miniBtn,
              opacity: canSend ? 1 : 0.55,
              background: "#38bdf8",
              borderColor: "#38bdf8",
              color: "#ffffff",
            }}
          >
            Send + Run
          </button>
        </div>
      </div>

      <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#374151" }}>Manifest (gx1_manifest.json)</div>
          <textarea
            value={manifestText}
            onChange={(e) => setManifestText(e.target.value)}
            placeholder="Paste or generate manifest JSON…"
            style={{
              width: "100%",
              minHeight: 160,
              marginTop: 6,
              borderRadius: 10,
              border: "1px solid #d1d5db",
              padding: 10,
              fontFamily: "ui-monospace, Menlo, monospace",
              fontSize: 12,
              boxSizing: "border-box",
            }}
          />
        </div>

        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#374151" }}>Dataset (JSONL)</div>
          <textarea
            value={datasetText}
            onChange={(e) => setDatasetText(e.target.value)}
            placeholder='One JSON object per line, e.g. {"id":"ex1","seq":"ACGT..."}'
            style={{
              width: "100%",
              minHeight: 160,
              marginTop: 6,
              borderRadius: 10,
              border: "1px solid #d1d5db",
              padding: 10,
              fontFamily: "ui-monospace, Menlo, monospace",
              fontSize: 12,
              boxSizing: "border-box",
            }}
          />
        </div>
      </div>

      <div style={{ marginTop: 10, fontSize: 12, color: "#6b7280" }}>
        Dispatches <code>gx1.fill_inputs</code> to auto-fill Bucket A/B. “Send + Run” triggers a run once both are loaded.
      </div>
    </section>
  );
}

// robust param getter (works with hash routers too)
function getParam(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    const sp = new URLSearchParams(window.location.search);
    const v1 = sp.get(key);
    if (v1) return v1;

    const h = window.location.hash || "";
    const qIdx = h.indexOf("?");
    if (qIdx >= 0) {
      const qs = h.slice(qIdx + 1);
      const hp = new URLSearchParams(qs);
      const v2 = hp.get(key);
      if (v2) return v2;
    }
  } catch {
    // ignore
  }
  return null;
}

export default function QfcBioPage() {
  const telemetry = useTessarisTelemetry();
  const [containerId, setContainerId] = useState<string>("dc_aion_core");
  const [adapterBuf, setAdapterBuf] = useState<string>("");

  useEffect(() => {
    const cid = getParam("container") || getParam("containerId") || "dc_aion_core";
    setContainerId(cid);
  }, []);

  // ✅ ScenarioId-safe: validate + fallback
  const scenarioFromUrl: ScenarioId = useMemo(() => {
    const raw = getParam("scenario") || getParam("bio_scenario") || "GN01";
    return isScenarioId(raw) ? raw : "GN01";
  }, []);

  const qs = typeof window !== "undefined" ? window.location.search : "";
  const withQS = useMemo(() => (path: string) => (qs ? `${path}${qs}` : path), [qs]);

  const navHash = (path: string) => {
    const p = path.startsWith("/") ? path : `/${path}`;
    const target = withQS(p);

    if (typeof window !== "undefined") {
      if (window.location.hash && window.location.hash.startsWith("#")) {
        window.location.hash = `#${p}`;
        return;
      }
      window.location.href = target;
    }
  };

  const activeTool: ToolId = "qfc_bio";

  function openInAdapter(name: string, source: string) {
    if (typeof window === "undefined") return;
    window.dispatchEvent(
      new CustomEvent("devtools.photon_open", {
        detail: { docId: "gx1_adapter", name, source },
      }),
    );
  }

  function pushToGx1Manifest(text: string) {
    if (typeof window === "undefined") return;
    window.dispatchEvent(new CustomEvent("gx1.set_manifest_text", { detail: { text } }));
  }

  function pushToGx1Dataset(text: string, filename = "dataset.jsonl") {
    if (typeof window === "undefined") return;
    window.dispatchEvent(new CustomEvent("gx1.set_dataset_text", { detail: { text, filename } }));
  }

  return (
    <div style={{ minHeight: "100vh", padding: 12, background: "transparent" }}>
      <section
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <header style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#111827" }}>Dev Tools</div>
          </div>

          <div
            style={{
              display: "inline-flex",
              flexWrap: "wrap",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#ffffff",
              padding: 2,
              gap: 2,
            }}
          >
            <ToolButton id="editor" label="Text Editor" description="Photon scratchpad" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="ledger" label="Ledger" description="KG ledger entries" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="guide" label="Language" description=".ptn / .phn / .photon" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="pitch" label="Why compress?" description="Dev pitch" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="field" label="Field Lab" description="GHX / QField canvas" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="qfc" label="QFC HUD" description="Scenario HUD + knobs" activeTool={activeTool} onSelect={() => navHash("/qfc-hud")} />
            <ToolButton id="qfc_bio" label="QFC Bio" description="Biology-focused HUD" activeTool={activeTool} onSelect={() => navHash("/qfc-bio")} />
            <ToolButton id="aion" label="AION Memory" description="Internal holo seeds" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="crystal" label="Crystals" description="Compressed motifs" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="gma" label="GMA" description="Monetary state (dev)" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="gma_auth" label="GMA" description="Monetary authority" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
            <ToolButton id="docs" label="Docs" description="Transactable docs" activeTool={activeTool} onSelect={() => navHash("/devtools")} />
          </div>
        </header>

        <div
          style={{
            borderRadius: 16,
            border: "1px solid #e5e7eb",
            background: "#ffffff",
            padding: 12,
            boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
            minHeight: 420,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 800, color: "#111827", marginBottom: 8 }}>
            QFC Canvas (BIO)
          </div>

          <div style={{ flex: 1, minHeight: 360 }}>
            <QFCHudPanel
              containerId={containerId}
              telemetry={telemetry}
              urlPrefix="bio_"
              defaultScenario={scenarioFromUrl}
              domainLabel="BIO"
              variant="canvasOnly"
            />
          </div>
        </div>

        <details
          style={{
            borderRadius: 14,
            border: "1px solid #e5e7eb",
            background: "#ffffff",
            padding: 12,
            boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
          }}
        >
          <summary style={{ cursor: "pointer", fontWeight: 700, color: "#111827" }}>
            Adapter Script (optional) — build canonical dataset/manifest in-browser
          </summary>

          <div style={{ marginTop: 10, display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button type="button" onClick={() => openInAdapter("gx1_manifest.json", PILOT_MANIFEST_JSON)} style={miniBtn}>
              Load pilot manifest template
            </button>

            <button type="button" onClick={() => openInAdapter("pilot.jsonl", PILOT_DATASET_JSONL)} style={miniBtn}>
              Load pilot dataset JSONL
            </button>

            <button type="button" onClick={() => pushToGx1Manifest(adapterBuf)} style={miniBtn} disabled={!adapterBuf.trim()}>
              Send buffer → Bucket A (Manifest)
            </button>

            <button type="button" onClick={() => pushToGx1Dataset(adapterBuf, "dataset.jsonl")} style={miniBtn} disabled={!adapterBuf.trim()}>
              Send buffer → Bucket B (Dataset JSONL)
            </button>
          </div>

          <div style={{ marginTop: 10 }}>
            <PhotonEditor docId="gx1_adapter" holoFiles={[]} onSourceChange={setAdapterBuf} />
          </div>

          <div style={{ marginTop: 8, fontSize: 12, color: "#6b7280" }}>
            Rule: whatever raw format you start from, the adapter output MUST be canonical GX1 dataset (JSONL or pack) + stable dataset identity.
          </div>
        </details>

        <div>
          <Gx1AdapterPad />
          <QfcBioDashboard />
        </div>
      </section>
    </div>
  );
}