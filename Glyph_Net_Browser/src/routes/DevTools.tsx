// Glyph_Net_Browser/src/routes/DevTools.tsx
// Dev Tools dashboard inside the Glyph Net browser.

// NOTE: Photon Pay & WaveSend dev panels are routed in App.tsx
// (see DEV_ROUTES_ENABLED and the devtools hash block).
// This file remains the "normal" Dev Tools dashboard.

import { useState, useEffect, useMemo, type CSSProperties } from "react";
import PhotonEditor from "../components/PhotonEditor";
import LedgerInspector from "../components/LedgerInspector";
import PhotonGuide from "../components/PhotonGuide";
import DevPitch from "../components/DevPitch";
import AionMemoryFieldPanel from "../components/AionMemoryFieldPanel";
import CrystalPanel from "../components/CrystalPanel";
import { HoloProgramEditor } from "../components/HoloProgramEditor";
import { HoloIndexItem } from "../lib/api/holo";
// 3D hologram scene wrapper (Canvas + OrbitControls)
import HologramContainerView from "../components/HologramContainerView";
import QRCode from "qrcode.react";
import ErrorBoundary from "../components/ErrorBoundary";
import QFCViewport from "../components/QFCViewport";
import { useTessarisTelemetry, type TessarisTelemetry } from "../hooks/useTessarisTelemetry";

// Hologram IR + API
import type { HoloIR } from "../lib/types/holo"; 
import {
  exportHoloForContainer,
  fetchLatestHoloForContainer,
  listHolosForContainer,
  fetchHoloAtTick,
} from "../lib/api/holo";
import type { HoloIndexEntry } from "../lib/api/holo";

type ToolId =
  | "editor"
  | "ledger"
  | "guide"
  | "pitch"
  | "field"
  | "aion"
  | "qfc"  
  | "crystal"
  | "docs"
  | "gma"
  | "gma_auth";      

type FrameMetric = {
  psi: number;
  kappa: number;
  tau: number;
  coherence: number;
};

export default function DevTools() {
  const [activeTool, setActiveTool] = useState<ToolId>("editor");

  // 🔭 Holo / container state
  const [activeContainerId, setActiveContainerId] = useState<string | null>(
    null,
  );
  const [holo, setHolo] = useState<HoloIR | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [lastRunRevision, setLastRunRevision] = useState<number | null>(null);

  // 📚 Holo index (history) – legacy shape used by existing UI
  const [holoIndex, setHoloIndex] = useState<HoloIndexEntry[] | null>(null);
  const [loadingIndex, setLoadingIndex] = useState(false);
  const telemetry = useTessarisTelemetry();

  // 📁 Shared “Holo Files” cabinet (used by Text Editor + Field Lab)
  const [holoFiles, setHoloFiles] = useState<HoloIndexItem[]>([]);

  const [lastRunInfo, setLastRunInfo] = useState<{
    revision: number | null;
    lastRunAt: string | null;
    consoleText: string | null;
    frameMetrics: Record<string, FrameMetric>;
  }>({
    revision: null,
    lastRunAt: null,
    consoleText: null,
    frameMetrics: {},
  });

  // 👁️‍🗨️ Derive active container id from URL query (?container=dc_xxx)
  // Fallback for now is dc_aion_core (matches existing .dc.json + exports)
  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const cid =
        params.get("container") ||
        params.get("containerId") ||
        "dc_aion_core";
      setActiveContainerId(cid);
    } catch {
      // non-browser env / SSR safe no-op
      setActiveContainerId("dc_aion_core");
    }
  }, []);

  // 🔁 On container change, try to load the latest .holo snapshot (if any)
  useEffect(() => {
    if (!activeContainerId) {
      setHolo(null);
      return;
    }

    let cancelled = false;

    fetchLatestHoloForContainer(activeContainerId)
      .then((h) => {
        if (!cancelled) setHolo(h);
      })
      .catch(() => {
        // no holo yet (404) is fine – just clear state
        if (!cancelled) setHolo(null);
      });

    return () => {
      cancelled = true;
    };
  }, [activeContainerId]);

  // 📚 Load holo index + holo files whenever container changes
  useEffect(() => {
    if (!activeContainerId) {
      setHoloIndex(null);
      setHoloFiles([]);
      return;
    }

    let cancelled = false;
    setLoadingIndex(true);

    listHolosForContainer(activeContainerId)
      .then((items) => {
        if (cancelled) return;
        // Shared cabinet data
        setHoloFiles(items);
        // Legacy index consumers still work (shape is compatible enough)
        setHoloIndex(items as any);
      })
      .catch(() => {
        if (cancelled) return;
        setHoloFiles([]);
        setHoloIndex(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingIndex(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeContainerId]);

  // 🔄 Refresh Holo Files / index whenever a .holo is saved
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handler = (ev: Event) => {
      const detail = (ev as CustomEvent).detail;
      const saved = detail?.holo;
      if (!saved?.container_id) return;
      if (!activeContainerId || saved.container_id !== activeContainerId)
        return;

      listHolosForContainer(activeContainerId)
        .then((items) => {
          setHoloFiles(items);
          setHoloIndex(items as any);
        })
        .catch(() => {
          /* ignore */
        });
    };

    window.addEventListener("devtools.holo_saved", handler as any);
    return () =>
      window.removeEventListener("devtools.holo_saved", handler as any);
  }, [activeContainerId]);

  // 👂 listen for global tab-switch events (from PhotonEditor, etc.)
  useEffect(() => {
    function handleSwitch(ev: Event) {
      const detail = (ev as CustomEvent).detail || {};

      // Preferred: detail.tool is one of our ToolId values
      let target: ToolId | undefined = detail.tool;

      // Fallback mapping if something sends { tab: "field-lab" } etc.
      if (!target && detail.tab) {
        if (detail.tab === "field-lab") target = "field";
        if (detail.tab === "editor") target = "editor";
        if (detail.tab === "ledger") target = "ledger";
        if (detail.tab === "language") target = "guide";
        if (detail.tab === "pitch") target = "pitch";
        if (detail.tab === "aion") target = "aion";
        if (detail.tab === "crystal") target = "crystal";
        if (detail.tab === "qfc") target = "qfc";
      }

      if (target) setActiveTool(target);
    }

    window.addEventListener("devtools.switch_tab", handleSwitch as any);
    return () =>
      window.removeEventListener("devtools.switch_tab", handleSwitch as any);
  }, []);

  function deriveFrameMetricsFromResult(result: any): Record<string, FrameMetric> {
    const updatedHolo = result?.updated_holo || {};
    const extra = updatedHolo.extra || {};
    const frames: any[] = Array.isArray(extra.program_frames)
      ? extra.program_frames
      : [];

    const metrics = result?.metrics || {};
    const numBeams = Number(metrics.num_beams ?? 1) || 1;

    const out: Record<string, FrameMetric> = {};

    frames.forEach((f, idx) => {
      const id = f.id || `frame_${idx}`;
      const base = Math.max(1, numBeams);
      const n = idx + 1;

      const psi = Math.min(0.99, 0.6 + 0.03 * (n % 5) + 0.01 * Math.log10(base));
      const kappa = Math.min(
        0.99,
        0.5 + 0.02 * ((n + 1) % 5) + 0.008 * Math.log10(base + 1),
      );
      const tau = Math.min(
        0.99,
        0.4 + 0.015 * ((n + 2) % 5) + 0.006 * Math.log10(base + 2),
      );
      const coherence = Math.min(0.99, psi * 0.6 + kappa * 0.3 + tau * 0.1);

      out[id] = {
        psi: Number(psi.toFixed(3)),
        kappa: Number(kappa.toFixed(3)),
        tau: Number(tau.toFixed(3)),
        coherence: Number(coherence.toFixed(3)),
      };
    });

    return out;
  }

  useEffect(() => {
    function handleHoloRun(ev: Event) {
      const detail = (ev as CustomEvent).detail || {};
      const result = detail.result || {};

      const updatedHolo = result.updated_holo || {};
      const extra = updatedHolo.extra || {};
      const lastRunAt: string | null = extra.last_run_at ?? null;

      const revision =
        result.new_revision ?? updatedHolo?.version?.revision ?? null;

      const consoleText = result.output
        ? JSON.stringify(result.output, null, 2)
        : result.metrics
        ? JSON.stringify(result.metrics, null, 2)
        : null;

      const frameMetrics = deriveFrameMetricsFromResult(result);

      setLastRunInfo({
        revision,
        lastRunAt,
        consoleText,
        frameMetrics,
      });
    }

    window.addEventListener("devtools.holo_run", handleHoloRun as any);
    return () =>
      window.removeEventListener("devtools.holo_run", handleHoloRun as any);
  }, []);

  const [rehydrating, setRehydrating] = useState(false);

  async function handleRehydrateFromHolo() {
    if (!holo) return;

    try {
      setRehydrating(true);
      const resp = await fetch("/api/holo/rehydrate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ holo }),
      });

      const data = await resp.json();
      console.info("[DevTools] Rehydrated HST:", data);

      if (typeof window !== "undefined" && data?.hst) {
        window.dispatchEvent(
          new CustomEvent("devtools.hst_rehydrated", {
            detail: {
              source: "devtools.rehydrate",
              hst: data.hst,
            },
          }),
        );
      }
    } catch (err) {
      console.error("[DevTools] Rehydrate from .holo failed:", err);
    } finally {
      setRehydrating(false);
    }
  }

  async function handleExportHolo() {
    if (!activeContainerId) return;
    setExporting(true);
    setExportError(null);

    // 🔢 Figure out next revision number for this container
    const revisions =
      (holoIndex ?? [])
        .map((e) => e.revision ?? 0)
        .filter((n) => Number.isFinite(n)) as number[];

    const nextRevision =
      (revisions.length ? Math.max(...revisions) : 0) + 1;

    try {
      const snapshot = await exportHoloForContainer(
        activeContainerId,
        {
          tick: 0, // manual DevTools snapshots all at tick 0 for now
          reason: "devtools_manual_export",
          source_view: "qfc",
          frame: "mutated",
        },
        nextRevision, // 👈 pass revision
      );

      setHolo(snapshot);
      console.info(
        "[DevTools] Holo exported:",
        snapshot.holo_id,
        "rev=",
        nextRevision,
      );

      // Refresh index after export so history shows new snapshot
      try {
        const entries = await listHolosForContainer(activeContainerId);
        setHoloIndex(entries);
      } catch {
        // non-fatal
      }
    } catch (err: any) {
      console.error("[DevTools] Holo export failed:", err);
      setExportError(err?.message ?? "Holo export failed");
    } finally {
      setExporting(false);
    }
  }

  async function handleLoadHoloAt(entry: HoloIndexEntry) {
    if (!activeContainerId) return;
    if (entry.tick == null || entry.revision == null) return;

    setExportError(null);
    try {
      const h = await fetchHoloAtTick(
        activeContainerId,
        entry.tick,
        entry.revision,
      );
      if (h) {
        setHolo(h);
        console.info(
          "[DevTools] Loaded holo snapshot:",
          h.holo_id,
          "tick=",
          entry.tick,
          "rev=",
          entry.revision,
        );
      }
    } catch (err: any) {
      console.error("[DevTools] Failed to load holo at tick:", err);
      setExportError(err?.message ?? "Failed to load holo snapshot");
    }
  }

  async function handleRunHoloSnapshot() {
    if (!holo) return;

    setRunning(true);
    setExportError(null);

    try {
      const resp = await fetch("/api/holo/run_snapshot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          holo,
          input_ctx: {
            source: "devtools",
            container_id: activeContainerId,
          },
          mode: "qqc",
        }),
      });

      const data = await resp.json();

      // persist updated holo snapshot into global devtools context
      if (data.updated_holo) {
        (window as any).__DEVTOOLS_LAST_HOLO = data.updated_holo;
        setHolo(data.updated_holo as HoloIR);
      }

      // figure out revision label for "Runs:" UI
      const revisionLabel =
        data.new_revision ?? data.updated_holo?.version?.revision ?? null;

      if (revisionLabel != null) {
        setLastRunRevision(revisionLabel);
      }

      // optionally broadcast beams to the Field Lab canvas
      if (Array.isArray(data.beams)) {
        window.dispatchEvent(
          new CustomEvent("devtools.holo_run", {
            detail: {
              source: "run_snapshot",
              container_id: activeContainerId,
              result: data,
            },
          }),
        );
      }
    } catch (err) {
      console.error("[DevTools] run_holo_snapshot failed:", err);
      setExportError(
        (err as any)?.message ?? "Run .holo snapshot failed",
      );
    } finally {
      setRunning(false);
    }
  }

  // Small helper to pull any program_frames metadata out of the holo
  function getProgramFramesFromHolo(holoVal: HoloIR | null) {
    const extra = (holoVal as any)?.extra || {};
    const frames = (extra.program_frames as any[]) || [];
    if (Array.isArray(frames) && frames.length) return frames;

    // Fallback labels so the sidebar always feels like a small program
    return [
      { id: "frame_main", role: "main", label: "main.holo" },
      { id: "frame_loop", role: "loop", label: "loop.holo" },
      { id: "frame_exec", role: "exec", label: "exec.holo" },
      { id: "frame_output", role: "output", label: "output.holo" },
    ];
  }

  const programFrames = getProgramFramesFromHolo(holo);

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <section
        style={{
          flex: 1,
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {/* Header + tab row – all inside the card now */}
        <header
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "#111827",
              }}
            >
              Dev Tools
            </div>
            {activeTool === "field" && (
              <div
                style={{
                  fontSize: 11,
                  color: "#6b7280",
                  display: "flex",
                  gap: 6,
                  alignItems: "center",
                  flexWrap: "wrap",
                }}
              >
                {activeContainerId && (
                  <>
                    <span>
                      container: <code>{activeContainerId}</code>
                    </span>
                    <span>·</span>
                  </>
                )}
                <span>
                  holo:{" "}
                  {holo ? (
                    <code>{holo.holo_id}</code>
                  ) : (
                    <span style={{ opacity: 0.7 }}>none</span>
                  )}
                </span>
              </div>
            )}
          </div>

          {/* Tool switcher pill row */}
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
            <ToolButton
              id="editor"
              label="Text Editor"
              description="Photon scratchpad"
              activeTool={activeTool}
              onSelect={setActiveTool}
            />
            <ToolButton
              id="ledger"
              label="Ledger"
              description="KG ledger entries"
              activeTool={activeTool}
              onSelect={setActiveTool}
            />
            <ToolButton
              id="guide"
              label="Language"
              description=".ptn / .phn / .photon"
              activeTool={activeTool}
              onSelect={setActiveTool}
            />
            <ToolButton
              id="pitch"
              label="Why compress?"
              description="Dev pitch"
              activeTool={activeTool}
              onSelect={setActiveTool}
            />
            <ToolButton
              id="field"
              label="Field Lab"
              description="GHX / QField canvas"
              activeTool={activeTool}
              onSelect={setActiveTool}
            />
            <ToolButton
              id="qfc"
              label="QFC HUD"
              description="Scenario HUD + knobs"
              activeTool={activeTool}
              onSelect={setActiveTool}
            />
            <ToolButton
              id="aion"
              label="AION Memory"
              description="Internal holo seeds"
              activeTool={activeTool}
              onSelect={setActiveTool}
            />
            <ToolButton
              id="crystal"
              label="Crystals"
              description="Compressed motifs"
              activeTool={activeTool}
              onSelect={setActiveTool}
            />
            <ToolButton
              id="gma"
              label="GMA"
              description="Monetary state (dev)"
              activeTool={activeTool}
              onSelect={setActiveTool}
            />
            <ToolButton
              id="gma_auth"
              label="GMA"
              description="Monetary authority"
              activeTool={activeTool}
              onSelect={setActiveTool}
            />
            <ToolButton
              id="docs"
              label="Docs"
              description="Transactable docs"
              activeTool={activeTool}
              onSelect={setActiveTool}
            />
          </div>
        </header>

        {/* Main tool body */}
        <div
          style={{
            flex: 1,
            borderRadius: 12,
            border: "1px solid #e5e7eb",
            background: "#f3f4f6",
            padding: 10,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <ErrorBoundary
            title="DevTools panel crashed"
            onReset={() => setActiveTool("editor")}
          >
            {activeTool === "editor" ? (
              <PhotonEditor docId="devtools" />
            ) : activeTool === "ledger" ? (
              <LedgerInspector />
            ) : activeTool === "guide" ? (
              <PhotonGuide />
            ) : activeTool === "pitch" ? (
              <DevPitch />
            ) : activeTool === "aion" ? (
              <AionMemoryFieldPanel />
            ) : activeTool === "crystal" ? (
              <CrystalPanel />
            ) : activeTool === "docs" ? (
              <TransactableDocsDevPanel />
            ) : activeTool === "gma_auth" ? (
              <GMAMonetaryAuthorityPanel />
            ) : activeTool === "qfc" ? (
              <QFCHudPanel
                containerId={activeContainerId ?? "dc_aion_core"}
                telemetry={telemetry}
              />
            ) : (
              <>
                {/* Field Lab: Hologram container fills full width (owns its own Holo Files cabinet) */}
                <div
                  style={{
                    flex: 1,
                    minHeight: 320,
                    overflow: "hidden",
                  }}
                >
                  <HologramContainerView
                    containerId={activeContainerId ?? "dc_aion_core"}
                    title="Hologram Container"
                    holo={holo}
                    holoFiles={holoFiles}
                    onSelectHolo={async (item) => {
                      if (!activeContainerId) return;
                      const snap = await fetchHoloAtTick(
                        activeContainerId,
                        item.tick,
                        item.revision,
                      );
                      if (snap) setHolo(snap);
                    }}
                  />
                </div>

                <div style={{ marginTop: 12 }}>
                  <HoloProgramEditor
                    value={holo as any}
                    onChange={setHolo as any}
                    apiBase="/api"
                  />
                </div>
              </>
            )}
          </ErrorBoundary>
        </div>

        {/* Field-only footer: errors + run/export controls */}
        {activeTool === "field" && (
          <>
            {exportError && (
              <div
                style={{
                  marginTop: 8,
                  fontSize: 11,
                  color: "#b91c1c",
                }}
              >
                {exportError}
              </div>
            )}

            <div
              style={{
                marginTop: 8,
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  fontSize: 11,
                  color: "#6b7280",
                }}
              >
                <span>
                  Runs:{" "}
                  {lastRunInfo.revision != null ? (
                    <code>v{lastRunInfo.revision}</code>
                  ) : (
                    <span style={{ opacity: 0.7 }}>—</span>
                  )}
                </span>

                {lastRunInfo.lastRunAt && (
                  <span>
                    last: <code>{lastRunInfo.lastRunAt}</code>
                  </span>
                )}
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: 8,
                }}
              >
                <button
                  type="button"
                  onClick={handleRehydrateFromHolo}
                  disabled={rehydrating || !holo}
                  style={{
                    padding: "4px 10px",
                    borderRadius: 999,
                    border: "1px solid #0ea5e9",
                    background: rehydrating ? "#e5e7eb" : "#e0f2fe",
                    color: rehydrating ? "#6b7280" : "#0f172a",
                    cursor: rehydrating ? "default" : "pointer",
                    fontSize: 11,
                    fontWeight: 500,
                    whiteSpace: "nowrap",
                  }}
                >
                  {rehydrating ? "Rehydrating…" : "Rehydrate to Field"}
                </button>

                <button
                  type="button"
                  onClick={handleRunHoloSnapshot}
                  disabled={running || !holo}
                  style={{
                    padding: "4px 10px",
                    borderRadius: 999,
                    border: "1px solid #4b5563",
                    background: running ? "#e5e7eb" : "#4b5563",
                    color: running ? "#9ca3af" : "#e5e7eb",
                    cursor: running ? "default" : "pointer",
                    fontSize: 11,
                    fontWeight: 500,
                    whiteSpace: "nowrap",
                  }}
                >
                  {running ? "Running…" : "Run snapshot"}
                </button>

                <button
                  type="button"
                  onClick={handleExportHolo}
                  disabled={exporting || !activeContainerId}
                  style={{
                    padding: "4px 10px",
                    borderRadius: 999,
                    border: "1px solid #0f172a",
                    background: exporting ? "#e5e7eb" : "#0f172a",
                    color: exporting ? "#6b7280" : "#e5e7eb",
                    cursor: exporting ? "default" : "pointer",
                    fontSize: 11,
                    fontWeight: 500,
                    whiteSpace: "nowrap",
                  }}
                >
                  {exporting ? "Exporting…" : "Export .holo"}
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

type ToolButtonProps = {
  id: ToolId;
  label: string;
  description: string;
  activeTool: ToolId;
  onSelect: (id: ToolId) => void;
};

function ToolButton({
  id,
  label,
  description,
  activeTool,
  onSelect,
}: ToolButtonProps) {
  const active = activeTool === id;
  return (
    <button
      type="button"
      onClick={() => onSelect(id)}
      style={{
        border: "none",
        padding: "4px 10px",
        borderRadius: 999,
        cursor: "pointer",
        fontSize: 11,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        minWidth: 120,
        background: active ? "#0f172a" : "transparent",
        color: active ? "#e5e7eb" : "#111827",
        boxShadow: active ? "0 0 0 1px #0ea5e9 inset" : "none",
      }}
    >
      <span style={{ fontWeight: 600 }}>{label}</span>
      <span
        style={{
          fontSize: 10,
          opacity: 0.8,
        }}
      >
        {description}
      </span>
    </button>
  );
}

type DevDocSignature = {
  signer: string;
  signed_at_ms: number;
  note?: string | null;
};

type DevPaymentChannel =
  | "ESCROW_DEV"
  | "PHO_TRANSFER"
  | "PHOTON_PAY_INVOICE";

type TransactableDocPaymentLeg = {
  leg_id: string;
  from_account: string;
  to_account: string;
  amount_pho: string;
  channel: DevPaymentChannel;   // 👈 use the union here
  status: string;
  created_at_ms: number;
  executed_at_ms: number | null;
  ref_id?: string | null;       // receipt / escrow id from backend
};

type TransactableDoc = {
  doc_id: string;
  title: string;
  party_a: string;
  party_b: string;
  raw_text: string | null;
  glyph_stream: string | null;
  status: "DRAFT" | "ACTIVE" | "EXECUTED" | "CANCELLED";
  created_at_ms: number;
  updated_at_ms: number;
  executed_at_ms: number | null;
  doc_hash?: string;
  required_signers?: string[];
  activation_policy?: string;
  signatures: DevDocSignature[];
  payment_legs: TransactableDocPaymentLeg[];

  // 🛰️ new holo fields
  holo_container_id?: string | null;
  holo_commit_id?: string | null;
  holo_committed_at_ms?: number | null;
};

type TranslateResponse = {
  translated?: string;
  glyph_count?: number;
  chars_before?: number;
  chars_after?: number;
  compression_ratio?: number;
};

async function translateDocToGlyph(raw: string): Promise<TranslateResponse> {
  const res = await fetch("/api/photon/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: raw,
      language: "python",   // use python mode to trigger wiki/capsule mapping
    }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} — ${text || res.statusText}`);
  }

  return (await res.json()) as TranslateResponse;
}

type GmaSnapshot = any;

function GmaDevPanel() {
  const [snapshot, setSnapshot] = useState<GmaSnapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function refreshSnapshot() {
    try {
      setBusy(true);
      setErr(null);
      const res = await fetch("/api/gma/state/dev_snapshot");
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || `HTTP ${res.status}`);
      }
      const json = await res.json();
      setSnapshot(json);
    } catch (e: any) {
      console.error("[GMA] dev_snapshot failed:", e);
      setErr(e?.message || "Failed to load GMA snapshot");
      setSnapshot(null);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refreshSnapshot();
  }, []);

  const state = snapshot?.state || snapshot || {};
  const reserves: any[] = state.reserves || state.reserve_positions || [];
  const mintBurnLog: any[] = state.mint_burn_log || [];

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: "#111827",
        }}
      >
        GMA – Monetary State (dev)
      </div>

      <p
        style={{
          margin: 0,
          fontSize: 11,
          color: "#6b7280",
        }}
      >
        Live view over <code>/api/gma/state/dev_snapshot</code> – PHO/TESS
        supply, reserves and mint/burn log.
      </p>

      {err && (
        <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div>
      )}

      <div
        style={{
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 8,
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "#111827",
            }}
          >
            Snapshot
          </div>
          <button
            type="button"
            onClick={refreshSnapshot}
            style={{
              padding: "3px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              fontSize: 11,
              cursor: "pointer",
            }}
          >
            {busy ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {!snapshot ? (
          <div style={{ fontSize: 11, color: "#9ca3af" }}>
            {busy ? "Loading snapshot…" : "No snapshot yet."}
          </div>
        ) : (
          <>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 12,
                fontSize: 11,
                color: "#4b5563",
              }}
            >
              <div>
                <div style={{ color: "#6b7280" }}>Photon supply (PHO)</div>
                <div style={{ fontWeight: 600 }}>
                  {state.photon_supply_pho ?? state.photonSupply ?? "—"}
                </div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Tesseract supply (TESS)</div>
                <div style={{ fontWeight: 600 }}>
                  {state.tesseract_supply_tess ?? state.tesseractSupply ?? "—"}
                </div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Equity (PHO terms)</div>
                <div style={{ fontWeight: 600 }}>
                  {state.equity_pho ?? "—"}
                </div>
              </div>
              <div>
                <div style={{ color: "#6b7280" }}>Reserves</div>
                <div style={{ fontWeight: 600 }}>
                  {reserves.length} position
                  {reserves.length === 1 ? "" : "s"}
                </div>
              </div>
            </div>

            {/* Reserves table */}
            <div
              style={{
                marginTop: 8,
                borderTop: "1px solid #e5e7eb",
                paddingTop: 6,
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: "#111827",
                  marginBottom: 4,
                }}
              >
                Reserve positions
              </div>
              {reserves.length === 0 ? (
                <div style={{ fontSize: 11, color: "#9ca3af" }}>
                  No reserves recorded.
                </div>
              ) : (
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    fontSize: 11,
                  }}
                >
                  <thead>
                    <tr style={{ textAlign: "left", color: "#6b7280" }}>
                      <th style={{ padding: "3px 4px" }}>Asset</th>
                      <th style={{ padding: "3px 4px" }}>Amount</th>
                      <th style={{ padding: "3px 4px" }}>Value (PHO)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reserves.map((r, idx) => (
                      <tr key={idx}>
                        <td style={{ padding: "3px 4px" }}>
                          {r.asset_id || r.asset || "—"}
                        </td>
                        <td style={{ padding: "3px 4px" }}>
                          {r.amount ?? r.quantity ?? "—"}
                        </td>
                        <td style={{ padding: "3px 4px" }}>
                          {r.value_pho ?? r.valuePho ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Mint / burn log (if present) */}
            <div
              style={{
                marginTop: 8,
                borderTop: "1px solid #e5e7eb",
                paddingTop: 6,
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: "#111827",
                  marginBottom: 4,
                }}
              >
                Mint / burn log
              </div>
              {mintBurnLog.length === 0 ? (
                <div style={{ fontSize: 11, color: "#9ca3af" }}>
                  No mint/burn events yet.
                </div>
              ) : (
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 16,
                    fontSize: 11,
                    color: "#4b5563",
                  }}
                >
                  {mintBurnLog
                    .slice()
                    .reverse()
                    .slice(0, 10)
                    .map((e, idx) => (
                      <li key={idx}>
                        <code>{e.kind || e.type || "?"}</code> ·{" "}
                        {e.amount_pho ?? e.amount ?? "?"} PHO{" "}
                        {e.reason && (
                          <span style={{ color: "#6b7280" }}>
                            {" "}
                            – {e.reason}
                          </span>
                        )}
                      </li>
                    ))}
                </ul>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function GMAMonetaryAuthorityPanel() {
  const [authority, setAuthority] = useState<any | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function refresh() {
    try {
      setBusy(true);
      setErr(null);

      // Try a dedicated authority endpoint first (if it exists)
      let res = await fetch("/api/gma/state/dev_authority");

      // Fallback: reuse dev_snapshot and pull any authority-ish fields
      if (!res.ok) {
        res = await fetch("/api/gma/state/dev_snapshot");
      }

      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(txt || `HTTP ${res.status}`);
      }

      const json = await res.json();

      const state = json?.state || json || {};
      const auth =
        state?.authority ||
        state?.monetary_authority ||
        state?.gma_authority ||
        json?.authority ||
        json?.monetary_authority ||
        json?.gma_authority ||
        null;

      setAuthority(auth ?? state);
    } catch (e: any) {
      console.error("[GMA] authority load failed:", e);
      setErr(e?.message || "Failed to load monetary authority");
      setAuthority(null);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: "#111827" }}>
        GMA – Monetary Authority (dev)
      </div>

      <p style={{ margin: 0, fontSize: 11, color: "#6b7280" }}>
        Read-only view of dev authority configuration / controls. Tries{" "}
        <code>/api/gma/state/dev_authority</code> then falls back to{" "}
        <code>/api/gma/state/dev_snapshot</code>.
      </p>

      {err && <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div>}

      <div
        style={{
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 8,
          display: "flex",
          flexDirection: "column",
          gap: 6,
          overflow: "auto",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: "#111827" }}>Authority snapshot</div>
          <button
            type="button"
            onClick={refresh}
            style={{
              padding: "3px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              fontSize: 11,
              cursor: busy ? "default" : "pointer",
              opacity: busy ? 0.6 : 1,
            }}
          >
            {busy ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {!authority ? (
          <div style={{ fontSize: 11, color: "#9ca3af" }}>
            {busy ? "Loading authority…" : "No authority data yet."}
          </div>
        ) : (
          <pre
            style={{
              margin: 0,
              padding: 8,
              borderRadius: 10,
              border: "1px dashed #e5e7eb",
              background: "#f9fafb",
              fontSize: 10,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {JSON.stringify(authority, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}

type ReserveRow = {
  asset_id: string;
  quantity: string;
  price_pho: string;
  value_pho: string;
};

function normalizeReserves(
  reserves:
    | Record<string, any>
    | any[]
    | null
    | undefined,
): ReserveRow[] {
  if (!reserves) return [];

  // Array shape: [{asset_id, quantity/amount, price_pho, value_pho}, ...]
  if (Array.isArray(reserves)) {
    return reserves.map((r: any, i: number) => ({
      asset_id: String(r?.asset_id ?? r?.asset ?? r?.denom ?? `asset_${i}`),
      quantity: String(r?.quantity ?? r?.amount ?? r?.units ?? r?.notional ?? "0"),
      price_pho: String(r?.price_pho ?? r?.pricePho ?? r?.mark_price_pho ?? r?.price ?? "0"),
      value_pho: String(
        r?.value_pho ?? r?.valuePho ?? r?.valuation_pho ?? r?.mark_to_market_pho ?? "0",
      ),
    }));
  }

  // Object shape: { "BTC": {quantity, price_pho, value_pho}, ... }
  if (typeof reserves === "object") {
    return Object.entries(reserves).map(([asset_id, r]) => ({
      asset_id,
      quantity: String((r as any)?.quantity ?? (r as any)?.amount ?? (r as any)?.units ?? (r as any)?.notional ?? "0"),
      price_pho: String((r as any)?.price_pho ?? (r as any)?.pricePho ?? (r as any)?.mark_price_pho ?? (r as any)?.price ?? "0"),
      value_pho: String(
        (r as any)?.value_pho ??
          (r as any)?.valuePho ??
          (r as any)?.valuation_pho ??
          (r as any)?.mark_to_market_pho ??
          "0",
      ),
    }));
  }

  return [];
}

function GMADashboardPanel() {
  const [snapshot, setSnapshot] = useState<any | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function refresh() {
    try {
      setBusy(true);
      setErr(null);

      const res = await fetch("/api/gma/state/dev_snapshot");
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(txt || `HTTP ${res.status}`);
      }

      const json = await res.json();
      setSnapshot(json);
    } catch (e: any) {
      console.error("[GMA] dev_snapshot failed:", e);
      setErr(e?.message || "Failed to load GMA snapshot");
      setSnapshot(null);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  // ✅ Early return so render never touches undefined snapshot
  if (!snapshot) {
    return (
      <div style={{ fontSize: 12, color: "#9ca3af" }}>
        {busy ? "Loading…" : "No snapshot yet."}
        {err ? <div style={{ marginTop: 6, color: "#b91c1c" }}>{err}</div> : null}
      </div>
    );
  }

  const state = snapshot?.state || snapshot || {};

  // ✅ Always normalize reserves into an array
  const reservesArr = normalizeReserves(
    state?.reserves ??
      state?.reserve_positions ??
      state?.reserves_by_asset ??
      snapshot?.reserves ??
      snapshot?.reserve_positions,
  );

  // ✅ Ensure log is always an array
  const mintBurnLog: any[] = Array.isArray(state?.mint_burn_log)
    ? state.mint_burn_log
    : Array.isArray(snapshot?.mint_burn_log)
    ? snapshot.mint_burn_log
    : [];

  const photonSupply =
    state.photon_supply_pho ??
    state.photon_supply ??
    state.photonSupply ??
    state.pho_supply ??
    null;

  const tesseractSupply =
    state.tesseract_supply_tess ??
    state.tesseract_supply ??
    state.tesseractSupply ??
    state.tess_supply ??
    null;

  const equityPho =
    state.equity_pho ??
    state.equityPho ??
    null;

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: "#111827" }}>
        GMA Dashboard (dev)
      </div>

      <p style={{ margin: 0, fontSize: 11, color: "#6b7280" }}>
        Read-only view over <code>/api/gma/state/dev_snapshot</code>. Shows current PHO/TESS supply,
        equity in PHO terms, reserves, and recent mint/burn log entries.
      </p>

      {err && <div style={{ fontSize: 11, color: "#b91c1c" }}>{err}</div>}

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {/* Summary card */}
        <div
          style={{
            flex: 1,
            minWidth: 220,
            borderRadius: 12,
            border: "1px solid #e5e7eb",
            background: "#ffffff",
            padding: 8,
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 600, color: "#111827", marginBottom: 6 }}>
            Balance sheet snapshot
          </div>
          <dl style={{ margin: 0, fontSize: 11, color: "#4b5563" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <dt>Photon supply (PHO)</dt>
              <dd><code>{photonSupply ?? "—"}</code></dd>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 2 }}>
              <dt>Tesseract supply (TESS)</dt>
              <dd><code>{tesseractSupply ?? "—"}</code></dd>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 2 }}>
              <dt>Equity (PHO terms)</dt>
              <dd><code>{equityPho ?? "—"}</code></dd>
            </div>
          </dl>
        </div>

        {/* Reserves card */}
        <div
          style={{
            flex: 1,
            minWidth: 260,
            borderRadius: 12,
            border: "1px solid #e5e7eb",
            background: "#ffffff",
            padding: 8,
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 600, color: "#111827", marginBottom: 4 }}>
            Reserves (dev)
          </div>

          {reservesArr.length === 0 ? (
            <div style={{ fontSize: 11, color: "#9ca3af" }}>
              No reserve positions in snapshot.
            </div>
          ) : (
            <div style={{ maxHeight: 160, overflow: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
                <thead>
                  <tr style={{ textAlign: "left", color: "#6b7280" }}>
                    <th style={{ padding: "2px 4px" }}>Asset</th>
                    <th style={{ padding: "2px 4px" }}>Qty</th>
                    <th style={{ padding: "2px 4px" }}>Price (PHO)</th>
                    <th style={{ padding: "2px 4px" }}>Value (PHO)</th>
                  </tr>
                </thead>
                <tbody>
                  {reservesArr.map((r, idx) => (
                    <tr key={r.asset_id || idx}>
                      <td style={{ padding: "2px 4px" }}>{r.asset_id || "?"}</td>
                      <td style={{ padding: "2px 4px" }}><code>{r.quantity ?? "—"}</code></td>
                      <td style={{ padding: "2px 4px" }}><code>{r.price_pho ?? "—"}</code></td>
                      <td style={{ padding: "2px 4px" }}><code>{r.value_pho ?? "—"}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Mint/burn log */}
      <div
        style={{
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 8,
          marginTop: 4,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: "#111827" }}>
            Mint / burn log (dev)
          </div>
          <button
            type="button"
            onClick={refresh}
            style={{
              padding: "3px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              fontSize: 11,
              cursor: busy ? "default" : "pointer",
              opacity: busy ? 0.6 : 1,
            }}
          >
            {busy ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {mintBurnLog.length === 0 ? (
          <div style={{ fontSize: 11, color: "#9ca3af" }}>
            No mint/burn entries found in snapshot.
          </div>
        ) : (
          <div style={{ maxHeight: 180, overflow: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10 }}>
              <thead>
                <tr style={{ textAlign: "left", color: "#6b7280" }}>
                  <th style={{ padding: "2px 4px" }}>When</th>
                  <th style={{ padding: "2px 4px" }}>Kind</th>
                  <th style={{ padding: "2px 4px" }}>Amount (PHO)</th>
                  <th style={{ padding: "2px 4px" }}>Reason</th>
                </tr>
              </thead>
              <tbody>
                {mintBurnLog
                  .slice()
                  .reverse()
                  .slice(0, 20)
                  .map((row: any, idx: number) => (
                    <tr key={idx}>
                      <td style={{ padding: "2px 4px" }}>
                        {row.created_at_ms ? new Date(row.created_at_ms).toLocaleString() : "—"}
                      </td>
                      <td style={{ padding: "2px 4px" }}>
                        {row.kind || row.type || "?"}
                      </td>
                      <td style={{ padding: "2px 4px" }}>
                        <code>{row.amount_pho ?? row.amount ?? "—"}</code>
                      </td>
                      <td style={{ padding: "2px 4px" }}>
                        {row.reason || row.note || "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

type ScenarioId = "BG01" | "G01" | "TN01" | "MT01" | "C01";

type ScenarioConfig = {
  id: ScenarioId;
  label: string;
  theme: {
    gravity: string;
    matter: string;
    photon: string;
    connect: string;
    danger: string;
  };
  defaults: { kappa: number; chi: number; sigma: number; alpha: number };
  mode: "gravity" | "tunnel" | "matter" | "connect";
};

const SCENARIOS: Record<ScenarioId, ScenarioConfig> = {
  BG01: {
    id: "BG01",
    label: "BG01 Base Grid",
    theme: {
      gravity: "rgba(56,189,248,0.65)",
      matter: "rgba(226,232,240,0.65)",
      photon: "rgba(251,191,36,0.70)",
      connect: "rgba(34,211,238,0.70)",
      danger: "rgba(239,68,68,0.80)",
    },
    defaults: { kappa: 0.11, chi: 0.25, sigma: 0.5, alpha: 0.1 },
    mode: "gravity",
  },
  G01: {
    id: "G01",
    label: "G01 Gravity Well",
    theme: {
      gravity: "rgba(99,102,241,0.70)",
      matter: "rgba(148,163,184,0.65)",
      photon: "rgba(251,191,36,0.70)",
      connect: "rgba(34,211,238,0.70)",
      danger: "rgba(239,68,68,0.80)",
    },
    defaults: { kappa: 0.18, chi: 0.18, sigma: 0.42, alpha: 0.08 },
    mode: "gravity",
  },
  TN01: {
    id: "TN01",
    label: "TN01 Light Tunneling",
    theme: {
      gravity: "rgba(56,189,248,0.45)",
      matter: "rgba(148,163,184,0.60)",
      photon: "rgba(251,191,36,0.85)",
      connect: "rgba(34,211,238,0.70)",
      danger: "rgba(239,68,68,0.85)",
    },
    defaults: { kappa: 0.06, chi: 0.22, sigma: 0.78, alpha: 0.14 },
    mode: "tunnel",
  },
  MT01: {
    id: "MT01",
    label: "MT01 Matter Soliton",
    theme: {
      gravity: "rgba(56,189,248,0.40)",
      matter: "rgba(226,232,240,0.85)",
      photon: "rgba(251,191,36,0.55)",
      connect: "rgba(34,211,238,0.70)",
      danger: "rgba(239,68,68,0.80)",
    },
    defaults: { kappa: 0.12, chi: 0.28, sigma: 0.35, alpha: 0.11 },
    mode: "matter",
  },
  C01: {
    id: "C01",
    label: "C01 Connectivity Jump",
    theme: {
      gravity: "rgba(56,189,248,0.35)",
      matter: "rgba(148,163,184,0.55)",
      photon: "rgba(251,191,36,0.55)",
      connect: "rgba(34,211,238,0.90)",
      danger: "rgba(239,68,68,0.80)",
    },
    defaults: { kappa: 0.09, chi: 0.34, sigma: 0.62, alpha: 0.16 },
    mode: "connect",
  },
};

type QFCFrame = {
  t: number;
  kappa?: number;
  chi?: number;
  sigma?: number;
  alpha?: number;
  curl_rms?: number;
  curv?: number;
  coupling_score?: number;
  max_norm?: number;
};

function QFCHudPanel({ containerId, telemetry }: { containerId: string; telemetry?: TessarisTelemetry }) {
  // --- scenario selector ---
  const [scenario, setScenario] = useState<ScenarioId>(() => {
    try {
      const p = new URLSearchParams(window.location.search);
      return (p.get("scenario") as ScenarioId) || "BG01";
    } catch {
      return "BG01";
    }
  });

  const cfg = SCENARIOS[scenario] ?? SCENARIOS.BG01;

  const [controller, setController] = useState("unknown");
  const [seed, setSeed] = useState<number>(1);
  const [runHash, setRunHash] = useState<string>("—");

  // --- knobs (top-right MVP) ---
  const [kappa, setKappa] = useState(() => cfg.defaults.kappa);
  const [chi, setChi] = useState(() => cfg.defaults.chi);
  const [sigma, setSigma] = useState(() => cfg.defaults.sigma);
  const [alpha, setAlpha] = useState(() => cfg.defaults.alpha);

  // --- rolling stream ---
  const [frames, setFrames] = useState<QFCFrame[]>([]);
  const [connected, setConnected] = useState(false);
  const [paused, setPaused] = useState(false);

  const [cursor, setCursor] = useState(0);

  // ✅ put meanTail here (if you haven’t already defined it above)
  const meanTail = (xs: number[], n = 80) => {
    const tail = xs.slice(Math.max(0, xs.length - n));
    if (!tail.length) return 0;
    return tail.reduce((a, b) => a + b, 0) / tail.length;
  };

  // ✅ PUT THESE LINES RIGHT HERE (before return)
  const sigmaMean = meanTail(frames.map((f) => Number(f.sigma ?? 0)), 80);
  const gammaMean = meanTail(frames.map((f) => Number(f.coupling_score ?? 0)), 80);

  useEffect(() => {
    setKappa(cfg.defaults.kappa);
    setChi(cfg.defaults.chi);
    setSigma(cfg.defaults.sigma);
    setAlpha(cfg.defaults.alpha);

    setFrames([]);
    setCursor(0);
    setRunHash("—");

    // later: ws?.send(JSON.stringify({ type:"scenario", scenario }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenario]);  

  // Connect to a WS stream if present; otherwise simulate.
  // You can later point this to your real stream endpoint.

  const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
  // ✅ LIVE STREAM: derive frames from rqfs_feedback.state (+ fusion/analytics) via useTessarisTelemetry
  // helper funcs (put these just above the LIVE STREAM useEffect, inside QFCHudPanel)
  const pickNum = (...vals: any[]) => {
    for (const v of vals) {
      const n = Number(v);
      if (Number.isFinite(n)) return n;
    }
    return 0;
  };

  // ✅ LIVE STREAM: derive frames from rqfs_feedback.state (+ fusion/analytics) via useTessarisTelemetry
  useEffect(() => {
    if (paused) return;

    const t: any = telemetry ?? {};

    // ✅ support both keys (your stream often uses rqfs_feedback.state)
    const rqfsAny: any = t.rqfs_feedback ?? t.rqfs ?? {};
    const rqfs: any = rqfsAny?.state ?? rqfsAny ?? {};

    const fusion: any = t.fusion ?? {};
    const analytics: any = t.analytics ?? {};

    const hasAny =
      (rqfs && Object.keys(rqfs).length > 0) ||
      (fusion && Object.keys(fusion).length > 0) ||
      (analytics && Object.keys(analytics).length > 0);

    if (!hasAny) {
      setConnected(false);
      return;
    }
    setConnected(true);

    const pickNum = (...vals: any[]) => {
      for (const v of vals) {
        const n = Number(v);
        if (Number.isFinite(n)) return n;
      }
      return NaN;
    };

    const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

    // ✅ map exactly like your original working dashboard
    const kappaLive = clamp01(
      pickNum(
        rqfs.nu_bias,
        rqfs.nu,
        rqfs.kappa,
        analytics.mean_nu,
        analytics.nu_mean,
        analytics.meanNu,
        0,
      ) || 0,
    );

    const chiLive = clamp01(
      pickNum(
        rqfs.amp_bias,
        rqfs.amp,
        rqfs.psi,
        analytics.mean_amp,
        analytics.amp_mean,
        analytics.meanAmp,
        0,
      ) || 0,
    );

    const sigmaLive = clamp01(
      pickNum(
        fusion.stability,
        fusion.sigma,
        analytics.stability,
        analytics.sigma,
        0,
      ) || 0,
    );

    const alphaLive =
      pickNum(
        rqfs.feedback_gain,
        rqfs.gamma,
        fusion.fusion_score,
        fusion.fusion,
        analytics.feedback_gain,
        analytics.gamma,
        1.0,
      ) || 1.0;

    // ψ̃ from fusion (may be -1..+1). Convert to 0..1 for the chart.
    const psiRaw =
      pickNum(
        fusion["ψ̃"],
        fusion.psi_tilde,
        fusion.cognition_signal,
        fusion.inference_strength,
        fusion.signal,
        NaN,
      );

    const psi01 = Number.isFinite(psiRaw) ? clamp01(0.5 + 0.5 * psiRaw) : 0;

    const f: QFCFrame = {
      t: Date.now(),

      // κ̃ line in chart uses f.kappa
      kappa: kappaLive,

      // ψ̃ line in chart uses f.chi
      chi: psi01,

      // σ line in chart uses f.sigma
      sigma: sigmaLive,

      // γ̃ line in chart uses f.alpha (keep feedback gain here)
      alpha: alphaLive,

      // extras (for object data + other panels)
      curl_rms: pickNum(fusion.curl_rms, fusion.curl, analytics.curl_rms) || 0,
      curv: pickNum(fusion.curv, fusion.curvature, analytics.curv, analytics.curvature) || 0,
      coupling_score:
        pickNum(fusion.coupling_score, fusion.gamma_tilde, fusion["γ̃"], fusion.stability, analytics.stability) || 0,
      max_norm: pickNum(fusion.max_norm, analytics.max_norm) || 0,
    };

    setFrames((prev) => {
      const next = prev.length > 400 ? prev.slice(prev.length - 400) : prev.slice();
      next.push(f);
      return next;
    });
  }, [telemetry, paused]);

  // keep cursor valid
  useEffect(() => {
    setCursor((c) => Math.min(c, Math.max(0, frames.length - 1)));
  }, [frames.length]);

  const active = frames.length ? frames[cursor] : null;

  const exportSnapshot = () => {
    const payload = {
      meta: { scenario, controller, seed, run_hash: runHash, container_id: containerId },
      knobs: { kappa, chi, sigma, alpha },
      cursor,
      frame: active,
      frames_tail: frames.slice(Math.max(0, frames.length - 200)),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `qfc_${scenario}_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  // (inside QFCHudPanel)
  const hudShell: CSSProperties = {
    height: "100%",
    display: "flex",
    flexDirection: "column",
    gap: 10,
  };

  const hudWrap: React.CSSProperties = {
    borderRadius: 16,
    border: "1px solid rgba(148,163,184,0.28)",
    background: "linear-gradient(180deg, rgba(2,6,23,0.82), rgba(15,23,42,0.62))",
    boxShadow: "0 0 0 1px rgba(56,189,248,0.10) inset, 0 18px 60px rgba(0,0,0,0.35)",
    color: "#e5e7eb",
    overflow: "hidden",
  };

  const hudHeader: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
    padding: "10px 12px",
    borderBottom: "1px solid rgba(148,163,184,0.20)",
    background: "linear-gradient(90deg, rgba(15,23,42,0.75), rgba(2,6,23,0.25))",
  };

  const hudTitle: React.CSSProperties = {
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: "uppercase",
    color: "rgba(226,232,240,0.85)",
    fontWeight: 700,
  };

  const hudSub: React.CSSProperties = {
    fontSize: 10,
    color: "rgba(226,232,240,0.65)",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  };

  const grid: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "1.35fr 1.1fr 1fr",
    gridTemplateRows: "320px 240px", // was 250px
    gap: 10,
    padding: 12,
  };

  const panelBase: React.CSSProperties = {
    borderRadius: 14,
    border: "1px solid rgba(148,163,184,0.22)",
    background: "linear-gradient(180deg, rgba(2,6,23,0.55), rgba(15,23,42,0.35))",
    boxShadow: "0 0 0 1px rgba(56,189,248,0.08) inset",
    padding: 10,
    position: "relative",
    overflow: "hidden",
  };

  const panelLabel: React.CSSProperties = {
    fontSize: 10,
    letterSpacing: 0.9,
    textTransform: "uppercase",
    color: "rgba(226,232,240,0.72)",
    marginBottom: 8,
    display: "flex",
    justifyContent: "space-between",
    gap: 10,
    alignItems: "center",
  };

  const mono: React.CSSProperties = {
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  };

  function HudPanel({
    title,
    right,
    style,
    children,
  }: {
    title: string;
    right?: React.ReactNode;
    style?: React.CSSProperties;
    children: React.ReactNode;
  }) {
    return (
      <div style={{ ...panelBase, ...style }}>
        <div style={panelLabel}>
          <span>{title}</span>
          {right ? <span style={{ opacity: 0.9 }}>{right}</span> : null}
        </div>
        {children}
      </div>
    );
  }

  function LegendChip({ label, color, active }: { label: string; color: string; active?: boolean }) {
    return (
      <span
        style={{
          padding: "5px 10px",
          borderRadius: 999,
          border: active ? "1px solid rgba(226,232,240,0.45)" : "1px solid rgba(148,163,184,0.22)",
          background: active ? "rgba(226,232,240,0.08)" : "rgba(2,6,23,0.25)",
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          fontSize: 10,
          ...mono,
          opacity: active ? 1 : 0.85,
        }}
        title={label}
      >
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: 999,
            background: color,
            boxShadow: `0 0 16px ${color}`,
            opacity: 0.9,
          }}
        />
        {label}
      </span>
    );
  }

  function ResonanceScope({
    frames,
    footerLeft,
    footerRight,
  }: {
    frames: QFCFrame[];
    footerLeft?: React.ReactNode;
    footerRight?: React.ReactNode;
  }) {
    const tail = frames.slice(Math.max(0, frames.length - 180));

    // SVG size
    const W = 920;
    const H = 240; // ✅ was 190 (or 170 in the older version)

    // Plot paddings (space for axes)
    const padL = 46;
    const padR = 52;
    const padT = 10;
    const padB = 26;

    const w = W - padL - padR;
    const h = H - padT - padB;

    const safeSeries = (ys: number[], fallback: number) => {
      if (ys.length >= 2) return ys;
      const v = ys.length === 1 ? ys[0] : fallback;
      return [v, v];
    };

    const sigma = safeSeries(tail.map((f) => Number(f.sigma ?? 0)), 0.9);  // σ
    const gamma = safeSeries(tail.map((f) => Number(f.alpha ?? 1)), 1.0);  // γ̃
    const psi   = safeSeries(tail.map((f) => Number(f.chi ?? 0)), 0.2);    // ψ̃
    // κ̃ should be fusion curl_rms (small ~0.02–0.10), so scale to 0..1 for visibility
    const KAPPA_SCALE = 10; // tweak 8–14 if you want bigger/smaller
    const kappa = safeSeries(
      tail.map((f) => clamp(Number(f.curl_rms ?? 0) * KAPPA_SCALE, 0, 1)),
      0.1,
    );

    const toPath = (ys: number[], yMin: number, yMax: number) => {
      const norm = (v: number) => {
        const t = (v - yMin) / Math.max(1e-9, yMax - yMin);
        return Math.max(0, Math.min(1, t));
      };

      return ys
        .map((v, i) => {
          const px = padL + (i / Math.max(1, ys.length - 1)) * w;
          const py = padT + (1 - norm(v)) * h;
          return `${i === 0 ? "M" : "L"} ${px.toFixed(2)} ${py.toFixed(2)}`;
        })
        .join(" ");
    };

    const pSigma = toPath(sigma, 0, 1);
    const pPsi   = toPath(psi,   0, 1);
    const pKappa = toPath(kappa, 0, 1);
    const pGamma = toPath(gamma, 0.6, 2.0);

    // axis ticks
    const yTicksLeft = [1, 0.75, 0.5, 0.25, 0];
    const yTicksRight = [2.0, 1.6, 1.2, 0.8, 0.6];

    const formatTime = (ms: number) => {
      const d = new Date(ms);
      const hh = String(d.getHours()).padStart(2, "0");
      const mm = String(d.getMinutes()).padStart(2, "0");
      const ss = String(d.getSeconds()).padStart(2, "0");
      return `${hh}:${mm}:${ss}`;
    };

    // bottom time ticks (up to ~8 labels)
    const tSeries = tail.map((f) => Number(f.t ?? NaN)).filter((n) => Number.isFinite(n));
    const xLabelCount = Math.min(8, tail.length);
    const xLabelEvery = Math.max(1, Math.floor(tail.length / xLabelCount));

    return (
      <div
        style={{
          borderRadius: 12,
          border: "1px solid rgba(148,163,184,0.18)",
          overflow: "hidden",
          position: "relative",
          height: "100%", // ✅ fill parent (removes bottom gap when parent gives height)
        }}
      >
        <svg
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="none"
          style={{
            width: "100%",
            height: "100%", // ✅ fill wrapper
            display: "block", // ✅ removes baseline gap
          }}
        >
          {/* plot bg grid */}
          {Array.from({ length: 9 }).map((_, i) => {
            const y = padT + (i / 8) * h;
            return (
              <line
                key={`h-${i}`}
                x1={padL}
                y1={y}
                x2={padL + w}
                y2={y}
                stroke="rgba(148,163,184,0.12)"
                strokeWidth="1"
              />
            );
          })}
          {Array.from({ length: 13 }).map((_, i) => {
            const x = padL + (i / 12) * w;
            return (
              <line
                key={`v-${i}`}
                x1={x}
                y1={padT}
                x2={x}
                y2={padT + h}
                stroke="rgba(148,163,184,0.10)"
                strokeWidth="1"
              />
            );
          })}

          {/* left axis labels (0..1) */}
          {yTicksLeft.map((v) => {
            const y = padT + (1 - v) * h;
            return (
              <g key={`yl-${v}`}>
                <text
                  x={padL - 8}
                  y={y + 3}
                  textAnchor="end"
                  fontSize="10"
                  fill="rgba(226,232,240,0.72)"
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                >
                  {v.toFixed(2)}
                </text>
              </g>
            );
          })}

          {/* right axis labels (γ̃ 0.6..2.0) */}
          {yTicksRight.map((v) => {
            const t = (v - 0.6) / (2.0 - 0.6);
            const y = padT + (1 - Math.max(0, Math.min(1, t))) * h;
            return (
              <g key={`yr-${v}`}>
                <text
                  x={padL + w + 8}
                  y={y + 3}
                  textAnchor="start"
                  fontSize="10"
                  fill="rgba(226,232,240,0.72)"
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                >
                  {v.toFixed(1)}
                </text>
              </g>
            );
          })}

          {/* bottom time labels */}
          {tail.map((f, i) => {
            if (i % xLabelEvery !== 0) return null;
            const t = Number(f.t ?? NaN);
            if (!Number.isFinite(t)) return null;
            const x = padL + (i / Math.max(1, tail.length - 1)) * w;
            return (
              <text
                key={`xt-${i}`}
                x={x}
                y={padT + h + 18}
                textAnchor="end"
                fontSize="10"
                fill="rgba(226,232,240,0.65)"
                fontFamily="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
                transform={`rotate(-25 ${x} ${padT + h + 18})`}
              >
                {formatTime(t)}
              </text>
            );
          })}

          {/* series */}
          <path d={pSigma} fill="none" stroke="rgba(110,231,183,0.95)" strokeWidth="3" />
          <path d={pGamma} fill="none" stroke="rgba(125,211,252,0.90)" strokeWidth="2.2" strokeDasharray="4 4" />
          <path d={pPsi}   fill="none" stroke="rgba(251,191,36,0.85)" strokeWidth="2.2" strokeDasharray="10 7" />
          <path d={pKappa} fill="none" stroke="rgba(244,114,182,0.85)" strokeWidth="2.2" strokeDasharray="7 7" />
        </svg>

        {/* existing footer */}
        {(footerLeft || footerRight) ? (
          <div
            style={{
              position: "absolute",
              left: 10,
              right: 10,
              bottom: 6,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 10,
              fontSize: 10,
              color: "rgba(226,232,240,0.78)",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
              pointerEvents: "none",
            }}
          >
            <div style={{ whiteSpace: "nowrap", opacity: 0.9 }}>{footerLeft}</div>
            <div style={{ whiteSpace: "nowrap", opacity: 0.9 }}>{footerRight}</div>
          </div>
        ) : null}
      </div>
    );
  }

  function TensorMetricsLegend() {
    const row = (label: string, style: React.CSSProperties) => (
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11 }}>
        <span style={{ width: 34, height: 0, borderTop: "2px solid", ...style }} />
        <span style={{ opacity: 0.92 }}>{label}</span>
      </div>
    );

    return (
      <div
        style={{
          padding: 10,
          borderRadius: 12,
          border: "1px solid rgba(148,163,184,0.22)",
          background: "rgba(2,6,23,0.70)",
          color: "rgba(226,232,240,0.92)",
        }}
      >
        <div style={{ fontSize: 14, fontWeight: 800, marginBottom: 8 }}>
          Tensor Metrics
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {row("σ (Stability Index)", { borderColor: "rgba(110,231,183,0.95)" })}
          {row("γ̃ (Feedback Gain)", { borderColor: "rgba(125,211,252,0.90)", borderTopStyle: "dotted" as any })}
          {row("ψ̃ (Cognitive Wave)", { borderColor: "rgba(251,191,36,0.85)", borderTopStyle: "dashed" as any })}
          {row("κ̃ (Resonance Field)", { borderColor: "rgba(244,114,182,0.85)", borderTopStyle: "dashed" as any })}
        </div>
      </div>
    );
  }

  function MetricTile({
    title,
    value,
    valueColor,
  }: {
    title: string;
    value: string;
    valueColor: string;
  }) {
    return (
      <div
        style={{
          flex: 1,
          borderRadius: 10,
          border: "1px solid rgba(148,163,184,0.22)",
          background: "rgba(226,232,240,0.75)",
          padding: 10,
        }}
      >
        <div style={{ fontSize: 12, color: "rgba(2,6,23,0.75)", marginBottom: 6 }}>
          {title}
        </div>
        <div style={{ fontSize: 40, fontWeight: 700, color: valueColor }}>
          {value}
        </div>
      </div>
    );
  }

  function Radar({ score }: { score: number }) {
    const s = Number.isFinite(score) ? score : 0;
    const r = 62;
    const cx = 70;
    const cy = 70;
    const ang = Math.PI * 2 * (0.15 + s * 0.7);
    const px = cx + Math.cos(ang) * (r * (0.25 + 0.7 * s));
    const py = cy + Math.sin(ang) * (r * (0.25 + 0.7 * s));

    return (
      <svg width="100%" viewBox="0 0 140 140">
        <circle cx={cx} cy={cy} r={r} fill="rgba(2,6,23,0.35)" stroke="rgba(148,163,184,0.22)" />
        {[0.25, 0.5, 0.75].map((k) => (
          <circle key={k} cx={cx} cy={cy} r={r * k} fill="none" stroke="rgba(148,163,184,0.14)" />
        ))}
        <line x1={cx - r} y1={cy} x2={cx + r} y2={cy} stroke="rgba(148,163,184,0.14)" />
        <line x1={cx} y1={cy - r} x2={cx} y2={cy + r} stroke="rgba(148,163,184,0.14)" />

        <path
          d={`M ${cx} ${cy} L ${cx + r} ${cy} A ${r} ${r} 0 0 1 ${cx + Math.cos(ang) * r} ${cy + Math.sin(ang) * r} Z`}
          fill="rgba(56,189,248,0.10)"
        />

        <circle cx={px} cy={py} r="4.2" fill="rgba(34,197,94,0.65)" stroke="rgba(226,232,240,0.9)" />
        <circle cx={px} cy={py} r="10" fill="none" stroke="rgba(34,197,94,0.25)" />
      </svg>
    );
  }
  const [demosOpen, setDemosOpen] = useState(false);
  const neonCard: CSSProperties = {
    borderRadius: 14,
    border: "1px solid rgba(148,163,184,0.35)",
    background:
      "linear-gradient(180deg, rgba(2,6,23,0.65), rgba(15,23,42,0.55))",
    boxShadow:
      "0 0 0 1px rgba(56,189,248,0.15) inset, 0 12px 40px rgba(0,0,0,0.25)",
    color: "#e5e7eb",
  };

  const label: CSSProperties = {
    fontSize: 10,
    letterSpacing: 0.8,
    textTransform: "uppercase",
    color: "rgba(226,232,240,0.75)",
  };

  const value: CSSProperties = {
    fontFamily:
      "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    fontSize: 12,
    color: "#e5e7eb",
  };

  return (
    <div
      style={{
        ...hudShell,
        minHeight: 0, // ✅ allow children to shrink inside flex column
        overflow: "hidden", // ✅ prevent page scroll; keep layout inside panel
      }}
    >
      {/* ✅ constrain the viewport height so it doesn't eat the whole panel */}
      <div style={{ flex: "0 0 520px", minHeight: 420, overflow: "hidden" }}>
        <QFCViewport
          title="Quantum Field Canvas"
          subtitle={`scenario=${scenario} · mode=${((active as any)?.mode ?? cfg.mode)} · container=${containerId}`}
          rightBadge={connected ? "LIVE" : "DISCONNECTED"}
          theme={((active as any)?.theme as any) ?? cfg.theme}
          mode={((active as any)?.mode as any) ?? cfg.mode}
          frame={active}
          frames={frames}
        />
      </div>

      {/* ✅ bottom HUD takes remaining space */}
      <div
        style={{
          ...hudWrap,
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Futuristic VISUAL ANALYSIS HUD (replaces old neonCard panel) */}
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        {/* Demo buttons */}
        <div style={{ position: "relative" }}>
          <button
            type="button"
            onClick={() => setDemosOpen((v) => !v)}
            style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid rgba(148,163,184,0.30)",
              background: "rgba(2,6,23,0.35)",
              color: "#e5e7eb",
              fontSize: 11,
              cursor: "pointer",
              ...mono,
            }}
          >
            Demos ▾
          </button>

          {demosOpen ? (
            <div
              style={{
                position: "absolute",
                top: "calc(100% + 8px)",
                left: 0,
                zIndex: 50,
                minWidth: 220,
                padding: 8,
                borderRadius: 14,
                border: "1px solid rgba(148,163,184,0.22)",
                background: "rgba(2,6,23,0.88)",
                boxShadow: "0 18px 60px rgba(0,0,0,0.45)",
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              {[
                { label: "Demo Gravity", id: "G01" as ScenarioId },
                { label: "Demo Tunnel", id: "TN01" as ScenarioId },
                { label: "Demo Matter", id: "MT01" as ScenarioId },
                { label: "Demo Connect", id: "C01" as ScenarioId },
              ].map((d) => (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => {
                    setScenario(d.id);
                    setDemosOpen(false);
                  }}
                  style={{
                    textAlign: "left",
                    padding: "8px 10px",
                    borderRadius: 12,
                    border: "1px solid rgba(148,163,184,0.18)",
                    background: "rgba(148,163,184,0.08)",
                    color: "#e5e7eb",
                    fontSize: 11,
                    cursor: "pointer",
                    ...mono,
                  }}
                >
                  {d.label}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        {/* Scenario selector */}
        <select
          value={scenario}
          onChange={(e) => setScenario(e.target.value as ScenarioId)}
          style={{
            padding: "6px 10px",
            borderRadius: 999,
            border: "1px solid rgba(148,163,184,0.30)",
            background: "rgba(2,6,23,0.35)",
            color: "#e5e7eb",
            fontSize: 11,
            cursor: "pointer",
            ...mono,
          }}
        >
          {Object.values(SCENARIOS).map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>

        {/* Stream badge */}
        <span
          style={{
            padding: "6px 10px",
            borderRadius: 999,
            border: "1px solid rgba(148,163,184,0.25)",
            background: "rgba(2,6,23,0.35)",
            fontSize: 10,
            ...mono,
          }}
        >
          {connected ? "WS STREAM" : "SIM STREAM"}
        </span>

        {/* Pause / Clear */}
        <button
          type="button"
          onClick={() => setPaused((p) => !p)}
          style={{
            padding: "6px 10px",
            borderRadius: 999,
            border: "1px solid rgba(56,189,248,0.45)",
            background: paused ? "rgba(148,163,184,0.15)" : "rgba(56,189,248,0.12)",
            color: "#e5e7eb",
            fontSize: 11,
            cursor: "pointer",
          }}
        >
          {paused ? "Resume" : "Pause"}
        </button>

        <button
          type="button"
          onClick={() => {
            setFrames([]);
            setCursor(0);
            setRunHash("—");
          }}
          style={{
            padding: "6px 10px",
            borderRadius: 999,
            border: "1px solid rgba(148,163,184,0.35)",
            background: "rgba(148,163,184,0.10)",
            color: "#e5e7eb",
            fontSize: 11,
            cursor: "pointer",
          }}
        >
          Clear
        </button>

          {/* Legend */}
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            <LegendChip label="Gravity" color={cfg.theme.gravity} active={cfg.mode === "gravity"} />
            <LegendChip label="Tunnel" color={cfg.theme.photon} active={cfg.mode === "tunnel"} />
            <LegendChip label="Matter" color={cfg.theme.matter} active={cfg.mode === "matter"} />
            <LegendChip label="Connect" color={cfg.theme.connect} active={cfg.mode === "connect"} />
          </div>
        </div>

        {/* ✅ scroll only the middle grid if needed; keep header + footer visible */}
        <div style={{ flex: 1, minHeight: 0, overflow: "auto" }}>
          <div style={grid}>
            {/* Top-left: Resonance scope (spans 2 columns) */}
            <HudPanel
              title="Resonance Scope"
              right={<span style={{ ...mono, fontSize: 10 }}>AI signal</span>}
              style={{ gridColumn: "1 / span 2" }}
            >
              {/* ✅ Chart left + Tensor Metrics legend right (prevents clipping) */}
              <div style={{ display: "flex", gap: 12, alignItems: "stretch", height: "100%" }}>
                <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                  {/* ✅ let the chart grow to fill the panel */}
                  <div style={{ flex: 1, minHeight: 240 }}>
                    <ResonanceScope
                      frames={frames}
                      footerLeft={<span>σ_mean={sigmaMean.toFixed(3)} · γ̃_mean={gammaMean.toFixed(3)}</span>}
                      footerRight={
                        <span>
                          t={active?.t ?? "—"} · coupling={active?.coupling_score?.toFixed?.(4) ?? "—"}
                        </span>
                      }
                    />
                  </div>

                  <div
                    style={{
                      display: "flex",
                      gap: 10,
                      flexWrap: "wrap",
                      fontSize: 10,
                      color: "rgba(226,232,240,0.72)",
                    }}
                  >
                    <span style={mono}>container={containerId}</span>
                  </div>
                </div>

                <div style={{ width: 220, flex: "0 0 220px", alignSelf: "stretch" }}>
                  <TensorMetricsLegend />
                </div>
              </div>
            </HudPanel>

            {/* Top-right: Object data */}
            <HudPanel
              title="Object Data"
              right={<span style={{ ...mono, fontSize: 10 }}>QFCFrame</span>}
            >
              <pre
                style={{
                  margin: 0,
                  padding: 10,
                  borderRadius: 12,
                  border: "1px dashed rgba(148,163,184,0.22)",
                  background: "rgba(2,6,23,0.28)",
                  fontSize: 10,
                  ...mono,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  maxHeight: 190,
                  overflow: "auto",
                }}
              >
                {JSON.stringify(active ?? {}, null, 2)}
              </pre>
            </HudPanel>

            {/* Bottom-left: Radiation/health */}
            <HudPanel
              title="Radiation Level"
              right={<span style={{ ...mono, fontSize: 10 }}>NORMAL</span>}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ fontSize: 10, color: "rgba(226,232,240,0.75)" }}>
                  Resonance health derived from coupling + curl.
                </div>

                <div
                  style={{
                    borderRadius: 12,
                    border: "1px solid rgba(148,163,184,0.20)",
                    background: "rgba(2,6,23,0.30)",
                    padding: 10,
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 10,
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <div style={{ fontSize: 10, color: "rgba(226,232,240,0.70)" }}>
                      coupling_score
                    </div>
                    <div style={{ ...mono, fontSize: 13 }}>
                      {active?.coupling_score?.toFixed?.(4) ?? "—"}
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <div style={{ fontSize: 10, color: "rgba(226,232,240,0.70)" }}>
                      curl_rms
                    </div>
                    <div style={{ ...mono, fontSize: 13 }}>
                      {active?.curl_rms?.toFixed?.(4) ?? "—"}
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                    <div style={{ fontSize: 10, color: "rgba(226,232,240,0.70)" }}>
                      curvature
                    </div>
                    <div style={{ ...mono, fontSize: 13 }}>
                      {active?.curv?.toFixed?.(4) ?? "—"}
                    </div>
                  </div>
                </div>
              </div>
            </HudPanel>

            {/* Bottom-middle: Radar/targeting */}
            <HudPanel
              title="Targeting"
              right={<span style={{ ...mono, fontSize: 10 }}>TRACK</span>}
            >
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <div style={{ width: 160, height: 160 }}>
                  <Radar score={Number(active?.coupling_score ?? 0)} />
                </div>

                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                    fontSize: 10,
                    color: "rgba(226,232,240,0.75)",
                  }}
                >
                  <div style={mono}>kappa={kappa.toFixed(3)}</div>
                  <div style={mono}>chi={chi.toFixed(3)}</div>
                  <div style={mono}>sigma={sigma.toFixed(3)}</div>
                  <div style={mono}>alpha={alpha.toFixed(3)}</div>

                  <div style={{ marginTop: 6, opacity: 0.85 }}>
                    lock quality ≈{" "}
                    <span style={mono}>
                      {(Number(active?.coupling_score ?? 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            </HudPanel>

            {/* Bottom-right: knobs */}
            <HudPanel
              title="Key Knobs"
              right={<span style={{ ...mono, fontSize: 10 }}>LIVE</span>}
            >
              <KnobRow name="kappa" value={kappa} onChange={setKappa} />
              <KnobRow name="chi" value={chi} onChange={setChi} />
              <KnobRow name="sigma" value={sigma} onChange={setSigma} />
              <KnobRow name="alpha" value={alpha} onChange={setAlpha} />
            </HudPanel>
          </div>
        </div>

        {/* Time scrubber + export (footer stays pinned) */}
        <div
          style={{
            padding: "10px 12px 12px",
            borderTop: "1px solid rgba(148,163,184,0.18)",
            display: "flex",
            alignItems: "center",
            gap: 10,
            flexWrap: "wrap",
          }}
        >
          <div
            style={{
              fontSize: 10,
              letterSpacing: 0.9,
              textTransform: "uppercase",
              color: "rgba(226,232,240,0.70)",
            }}
          >
            Time
          </div>

          <input
            type="range"
            min={0}
            max={Math.max(0, frames.length - 1)}
            value={cursor}
            onChange={(e) => setCursor(Number(e.target.value))}
            style={{ flex: 1, minWidth: 240 }}
          />

          <div
            style={{
              ...mono,
              fontSize: 11,
              color: "rgba(226,232,240,0.78)",
            }}
          >
            {frames.length ? `idx ${cursor} / ${frames.length - 1}` : "no frames"}
          </div>

          <button
            type="button"
            onClick={exportSnapshot}
            disabled={!frames.length}
            style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid rgba(34,197,94,0.45)",
              background: frames.length
                ? "rgba(34,197,94,0.12)"
                : "rgba(148,163,184,0.10)",
              color: frames.length ? "#e5e7eb" : "rgba(226,232,240,0.6)",
              fontSize: 11,
              cursor: frames.length ? "pointer" : "default",
            }}
          >
            Snapshot / Export
          </button>
        </div>
      </div>
    </div>
  );
}

function KnobRow({
  name,
  value,
  onChange,
}: {
  name: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
      <div
        style={{
          width: 58,
          fontSize: 10,
          textTransform: "uppercase",
          letterSpacing: 0.8,
          color: "rgba(226,232,240,0.75)",
        }}
      >
        {name}
      </div>
      <input
        type="range"
        min={0}
        max={1}
        step={0.001}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ flex: 1 }}
      />
      <div
        style={{
          width: 58,
          textAlign: "right",
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          fontSize: 12,
          color: "#e5e7eb",
        }}
      >
        {value.toFixed(3)}
      </div>
    </div>
  );
}

function MetricChip({ label, value }: { label: string; value: any }) {
  const v =
    value == null
      ? "—"
      : typeof value === "number"
      ? Number.isFinite(value)
        ? value.toFixed(4)
        : "—"
      : String(value);

  return (
    <div
      style={{
        borderRadius: 999,
        border: "1px solid rgba(148,163,184,0.25)",
        background: "rgba(2,6,23,0.45)",
        padding: "6px 10px",
        display: "flex",
        gap: 8,
        alignItems: "center",
      }}
    >
      <span
        style={{
          fontSize: 10,
          letterSpacing: 0.8,
          textTransform: "uppercase",
          color: "rgba(226,232,240,0.70)",
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          fontSize: 12,
          color: "#e5e7eb",
        }}
      >
        {v}
      </span>
    </div>
  );
}
function TransactableDocsDevPanel() {
  const [docs, setDocs] = useState<TransactableDoc[]>([]);
  const [docsErr, setDocsErr] = useState<string | null>(null);
  const [docsBusy, setDocsBusy] = useState<boolean>(false);
  const [docsMsg, setDocsMsg] = useState<string | null>(null);

  // simple form
  const [title, setTitle] = useState("Home build escrow contract");
  const [partyA, setPartyA] = useState("pho1-buyer");
  const [partyB, setPartyB] = useState("pho1-builder");
  const [rawText, setRawText] = useState(
    "Spec for home build, payment on signature.",
  );
  const [amountPho, setAmountPho] = useState("500.0");
  const [channel, setChannel] = useState("ESCROW_DEV");

  const [glyphStream, setGlyphStream] = useState<string | null>(null);
  const [translateBusy, setTranslateBusy] = useState(false);
  const [compressionStats, setCompressionStats] = useState<{
    before: number;
    after: number;
    pct: number;
  } | null>(null);

  const refreshDocs = async () => {
    try {
      setDocsErr(null);
      setDocsBusy(true);
      const resp = await fetch("/api/transactable_docs/dev/list");
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }
      const json = await resp.json();
      const list = (json.docs || []) as TransactableDoc[];
      list.sort(
        (a, b) => (b.created_at_ms || 0) - (a.created_at_ms || 0),
      );
      setDocs(list);
    } catch (e: any) {
      console.error("[DocsDev] refresh docs failed:", e);
      setDocs([]);
      setDocsErr(e?.message || "Failed to load transactable docs");
    } finally {
      setDocsBusy(false);
    }
  };

  useEffect(() => {
    refreshDocs();
  }, []);

  const handleCreate = async () => {
    try {
      setDocsErr(null);
      setDocsMsg(null);

      const body = {
        title: title.trim() || "Untitled doc",
        party_a: partyA.trim(),
        party_b: partyB.trim(),
        raw_text: rawText,
        glyph_stream: glyphStream,
        payment_legs: [
          {
            from_account: partyA.trim(),
            to_account: partyB.trim(),
            amount_pho: amountPho.trim(),
            channel: channel.trim() || "ESCROW_DEV",
          },
        ],
        required_signers: [partyA.trim(), partyB.trim()],
        activation_policy: "ALL",
      };

      const resp = await fetch("/api/transactable_docs/dev/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      const json = await resp.json();
      setDocsMsg(`Created doc ${json.doc?.doc_id || ""}`);
      await refreshDocs();
    } catch (e: any) {
      console.error("[DocsDev] create doc failed:", e);
      setDocsErr(e?.message || "Failed to create transactable doc");
    }
  };

  const handleSign = async (doc_id: string, signer: string) => {
    try {
      setDocsErr(null);
      setDocsMsg(null);

      const resp = await fetch("/api/transactable_docs/dev/sign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_id, signer }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      const json = await resp.json();
      setDocsMsg(
        `Signed doc ${json.doc?.doc_id || doc_id} as ${signer}`,
      );
      await refreshDocs();
    } catch (e: any) {
      console.error("[DocsDev] sign doc failed:", e);
      setDocsErr(e?.message || "Failed to sign doc");
    }
  };

  const [commitBusy, setCommitBusy] = useState<string | null>(null);

  async function handleCommitToHolo(doc_id: string) {
    try {
      setCommitBusy(doc_id);
      setDocsErr(null);
      setDocsMsg(null);

      const resp = await fetch("/api/transactable_docs/dev/commit_holo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_id }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      const json = await resp.json();
      setDocsMsg(
        `Committed doc ${json.doc?.doc_id || doc_id} to Holo/DC stub`,
      );
      await refreshDocs();
    } catch (e: any) {
      console.error("[DocsDev] commit_holo failed:", e);
      setDocsErr(e?.message || "Failed to commit doc to Holo");
    } finally {
      setCommitBusy(null);
    }
  }

  const handleActivate = async (doc_id: string) => {
    try {
      setDocsErr(null);
      setDocsMsg(null);

      const resp = await fetch("/api/transactable_docs/dev/activate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_id }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      const json = await resp.json();
      setDocsMsg(`Activated doc ${json.doc?.doc_id || doc_id}`);
      await refreshDocs();
    } catch (e: any) {
      console.error("[DocsDev] activate doc failed:", e);
      setDocsErr(e?.message || "Failed to activate doc");
    }
  };

  const handleExecute = async (doc_id: string) => {
    try {
      setDocsErr(null);
      setDocsMsg(null);

      const resp = await fetch("/api/transactable_docs/dev/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_id }),
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }

      const json = await resp.json();
      setDocsMsg(
        `Executed doc ${json.doc?.doc_id || doc_id} (legs: ${
          (json.payment_refs || []).length
        })`,
      );
      await refreshDocs();
    } catch (e: any) {
      console.error("[DocsDev] execute doc failed:", e);
      setDocsErr(e?.message || "Failed to execute doc");
    }
  };

  // 🔁 hook point for your existing glyph translator
  const handleTranslateToGlyphs = async () => {
    if (!rawText.trim()) {
      setGlyphStream(null);
      setCompressionStats(null);
      return;
    }

    try {
      setTranslateBusy(true);
      const resp = await translateDocToGlyph(rawText);
      const translated = resp.translated || rawText;

      setGlyphStream(translated);

      const before = resp.chars_before ?? rawText.length;
      const after  = resp.chars_after ?? translated.length;
      const pct    = before > 0 ? (1 - after / before) * 100 : 0;

      setCompressionStats({ before, after, pct });
    } catch (e) {
      console.error("[DocsDev] translate-to-glyphs failed:", e);
    } finally {
      setTranslateBusy(false);
    }
  };

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: "#111827",
        }}
      >
        Transactable Docs (dev)
      </div>

      <p
        style={{
          margin: 0,
          fontSize: 11,
          color: "#6b7280",
        }}
      >
        Draft contracts that can execute PHO legs via the transactable_docs dev
        backend. Later this becomes the backing engine for a GlyphNote /
        DocuSign-style document editor.
      </p>

      {docsErr && (
        <div style={{ fontSize: 11, color: "#b91c1c" }}>{docsErr}</div>
      )}
      {docsMsg && (
        <div style={{ fontSize: 11, color: "#047857" }}>{docsMsg}</div>
      )}

      {/* Editor */}
      <div
        style={{
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 8,
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        <div
          style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 4 }}
        >
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            style={{
              flex: 1,
              minWidth: 140,
              padding: "4px 8px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 11,
            }}
          />
          <input
            type="text"
            value={partyA}
            onChange={(e) => setPartyA(e.target.value)}
            placeholder="Party A (payer)"
            style={{
              minWidth: 140,
              padding: "4px 8px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 11,
            }}
          />
          <input
            type="text"
            value={partyB}
            onChange={(e) => setPartyB(e.target.value)}
            placeholder="Party B (beneficiary)"
            style={{
              minWidth: 140,
              padding: "4px 8px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 11,
            }}
          />
        </div>

        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          rows={3}
          placeholder="Contract text..."
          style={{
            width: "100%",
            padding: "6px 8px",
            borderRadius: 8,
            border: "1px solid #e5e7eb",
            fontSize: 11,
            fontFamily: "system-ui, sans-serif",
            marginBottom: 4,
          }}
        />

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 6,
            alignItems: "center",
          }}
        >
          <button
            type="button"
            onClick={handleTranslateToGlyphs}
            disabled={translateBusy}
            style={{
              padding: "4px 10px",
              borderRadius: 999,
              border: "1px solid #0f172a",
              background: translateBusy ? "#374151" : "#0f172a",
              color: "#f9fafb",
              fontSize: 11,
              fontWeight: 600,
              cursor: translateBusy ? "default" : "pointer",
              opacity: translateBusy ? 0.7 : 1,
            }}
          >
            {translateBusy ? "Translating…" : "Translate to glyph stream (dev)"}
          </button>
          <span style={{ fontSize: 10, color: "#6b7280" }}>
            Uses Photon /api/photon/translate_block backend.
          </span>
        </div>

        {compressionStats && (
          <div
            style={{
              marginTop: 4,
              fontSize: 11,
              color: "#6b7280",
            }}
          >
            <span>
              📦 Compression:{" "}
              <span
                style={{
                  fontFamily:
                    "JetBrains Mono, ui-monospace, SFMono-Regular, monospace",
                }}
              >
                {compressionStats.pct.toFixed(1)}% shorter
              </span>{" "}
              ({compressionStats.before} → {compressionStats.after} chars)
            </span>
          </div>
        )}

        {glyphStream && (
          <pre
            style={{
              margin: 0,
              marginTop: 4,
              padding: 6,
              borderRadius: 8,
              background: "#f9fafb",
              border: "1px dashed #e5e7eb",
              fontSize: 10,
              whiteSpace: "pre-wrap",
            }}
          >
            {glyphStream}
          </pre>
        )}

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 6,
            alignItems: "center",
            marginTop: 6,
          }}
        >
          <input
            type="number"
            inputMode="decimal"
            value={amountPho}
            onChange={(e) => setAmountPho(e.target.value)}
            placeholder="Amount PHO"
            style={{
              width: 120,
              padding: "4px 8px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 11,
              textAlign: "right",
            }}
          />

          {/* Channel selector */}
          <select
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            style={{
              width: 200,
              padding: "4px 8px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              fontSize: 11,
              background: "#ffffff",
            }}
          >
            <option value="ESCROW_DEV">ESCROW_DEV (escrow)</option>
            <option value="PHO_TRANSFER">PHO_TRANSFER (wallet)</option>
            <option value="PHOTON_PAY_INVOICE">
              PHOTON_PAY_INVOICE (Photon Pay)
            </option>
          </select>

          <button
            type="button"
            onClick={handleCreate}
            style={{
              padding: "5px 10px",
              borderRadius: 999,
              border: "1px solid #111827",
              background: "#111827",
              color: "#f9fafb",
              fontSize: 11,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Create doc
          </button>
        </div>
      </div>

      {/* Docs table */}
      <div
        style={{
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 8,
          marginTop: 4,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 4,
          }}
        >
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "#111827",
            }}
          >
            Documents
          </div>
          <button
            type="button"
            onClick={refreshDocs}
            style={{
              padding: "3px 10px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              fontSize: 11,
              cursor: "pointer",
            }}
          >
            {docsBusy ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {docs.length === 0 ? (
          <div style={{ fontSize: 11, color: "#9ca3af" }}>
            No docs yet. Create one above.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 11,
              }}
            >
              <thead>
                <tr style={{ textAlign: "left", color: "#6b7280" }}>
                  <th style={{ padding: "4px 4px" }}>Title / Hash</th>
                  <th style={{ padding: "4px 4px" }}>Parties</th>
                  <th style={{ padding: "4px 4px" }}>Status</th>
                  <th style={{ padding: "4px 4px" }}>Signatures</th>
                  <th style={{ padding: "4px 4px" }}>Payments</th>
                  <th style={{ padding: "4px 4px" }}>Created</th>
                  <th style={{ padding: "4px 4px" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((d) => {
                  const created = d.created_at_ms
                    ? new Date(d.created_at_ms).toLocaleString()
                    : "—";

                  const sigList = (d.signatures || [])
                    .map((s) => s.signer)
                    .join(", ");

                  return (
                    <tr key={d.doc_id}>
                      <td style={{ padding: "4px 4px", color: "#111827" }}>
                        <div>{d.title}</div>

                        {d.doc_hash && (
                          <div
                            style={{
                              fontSize: 10,
                              color: "#9ca3af",
                              marginTop: 2,
                            }}
                          >
                            hash: <code>{d.doc_hash.slice(0, 10)}…</code>
                          </div>
                        )}

                        {d.holo_commit_id && (
                          <div
                            style={{
                              fontSize: 10,
                              color: "#0f766e",
                              marginTop: 2,
                            }}
                          >
                            holo:{" "}
                            <code>
                              {d.holo_container_id || "dc_transactable_doc_v1"} /{" "}
                              {d.holo_commit_id}
                            </code>
                          </div>
                        )}
                      </td>

                      <td style={{ padding: "4px 4px", color: "#4b5563" }}>
                        {d.party_a} → {d.party_b}
                      </td>

                      <td style={{ padding: "4px 4px", color: "#6b7280" }}>
                        {d.status}
                      </td>

                      {/* Signatures */}
                      <td style={{ padding: "4px 4px", color: "#6b7280" }}>
                        {sigList || "—"}
                      </td>

                      {/* Payments + receipts */}
                      <td style={{ padding: "4px 4px", color: "#4b5563" }}>
                        {d.payment_legs && d.payment_legs.length ? (
                          <ul style={{ margin: 0, paddingLeft: 16 }}>
                            {d.payment_legs.map((leg) => (
                              <li key={leg.leg_id}>
                                <code>{leg.channel}</code>
                                {leg.channel === "PHO_TRANSFER" && (
                                  <span style={{ marginLeft: 4 }}>(wallet)</span>
                                )}
                                {leg.channel === "ESCROW_DEV" && (
                                  <span style={{ marginLeft: 4 }}>(escrow)</span>
                                )}
                                {leg.channel === "PHOTON_PAY_INVOICE" && (
                                  <span style={{ marginLeft: 4 }}>(Photon Pay)</span>
                                )}
                                {" · "}
                                {leg.amount_pho} PHO → {leg.to_account}
                                {leg.ref_id && (
                                  <span
                                    style={{
                                      marginLeft: 8,
                                      fontSize: 11,
                                      color: "#6b7280",
                                    }}
                                  >
                                    receipt: <code>{leg.ref_id}</code>
                                  </span>
                                )}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <span style={{ color: "#9ca3af" }}>—</span>
                        )}
                      </td>

                      {/* Created timestamp */}
                      <td style={{ padding: "4px 4px", color: "#6b7280" }}>
                        {created}
                      </td>

                      {/* Actions */}
                      <td
                        style={{
                          padding: "4px 4px",
                          display: "flex",
                          gap: 6,
                          flexWrap: "wrap",
                        }}
                      >
                        {/* Quick sign as each party while DRAFT/ACTIVE */}
                        <button
                          type="button"
                          disabled={d.status === "EXECUTED" || d.status === "CANCELLED"}
                          onClick={() => handleSign(d.doc_id, d.party_a)}
                          style={{
                            padding: "3px 8px",
                            borderRadius: 999,
                            border: "1px solid #6b7280",
                            background: "#f9fafb",
                            color: "#374151",
                            fontSize: 10,
                            cursor:
                              d.status === "EXECUTED" || d.status === "CANCELLED"
                                ? "default"
                                : "pointer",
                          }}
                        >
                          Sign as {d.party_a}
                        </button>

                        <button
                          type="button"
                          disabled={d.status === "EXECUTED" || d.status === "CANCELLED"}
                          onClick={() => handleSign(d.doc_id, d.party_b)}
                          style={{
                            padding: "3px 8px",
                            borderRadius: 999,
                            border: "1px solid #6b7280",
                            background: "#f9fafb",
                            color: "#374151",
                            fontSize: 10,
                            cursor:
                              d.status === "EXECUTED" || d.status === "CANCELLED"
                                ? "default"
                                : "pointer",
                          }}
                        >
                          Sign as {d.party_b}
                        </button>

                        {/* Commit to Holo (dev stub) */}
                        <button
                          type="button"
                          disabled={
                            !!d.holo_commit_id ||
                            !(d.status === "ACTIVE" || d.status === "EXECUTED") ||
                            commitBusy === d.doc_id
                          }
                          onClick={() => handleCommitToHolo(d.doc_id)}
                          style={{
                            padding: "3px 8px",
                            borderRadius: 999,
                            border: "1px solid #0f766e",
                            background:
                              d.holo_commit_id ||
                              !(d.status === "ACTIVE" || d.status === "EXECUTED")
                                ? "#e5e7eb"
                                : "#0f766e",
                            color:
                              d.holo_commit_id ||
                              !(d.status === "ACTIVE" || d.status === "EXECUTED")
                                ? "#9ca3af"
                                : "#ecfdf5",
                            fontSize: 10,
                            cursor:
                              d.holo_commit_id ||
                              !(d.status === "ACTIVE" || d.status === "EXECUTED")
                                ? "default"
                                : "pointer",
                          }}
                        >
                          {d.holo_commit_id
                            ? "Committed"
                            : commitBusy === d.doc_id
                            ? "Committing…"
                            : "Commit to Holo"}
                        </button>

                        {/* Existing Activate / Execute buttons */}
                        <button
                          type="button"
                          disabled={d.status !== "DRAFT"}
                          onClick={() => handleActivate(d.doc_id)}
                          style={{
                            padding: "3px 8px",
                            borderRadius: 999,
                            border: "1px solid #0369a1",
                            background: d.status === "DRAFT" ? "#0369a1" : "#e5e7eb",
                            color: d.status === "DRAFT" ? "#f9fafb" : "#9ca3af",
                            fontSize: 10,
                            cursor: d.status === "DRAFT" ? "pointer" : "default",
                          }}
                        >
                          Activate
                        </button>

                        <button
                          type="button"
                          disabled={d.status !== "ACTIVE"}
                          onClick={() => handleExecute(d.doc_id)}
                          style={{
                            padding: "3px 8px",
                            borderRadius: 999,
                            border: "1px solid #16a34a",
                            background: d.status === "ACTIVE" ? "#16a34a" : "#e5e7eb",
                            color: d.status === "ACTIVE" ? "#ecfdf5" : "#9ca3af",
                            fontSize: 10,
                            cursor: d.status === "ACTIVE" ? "pointer" : "default",
                          }}
                        >
                          Execute
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}