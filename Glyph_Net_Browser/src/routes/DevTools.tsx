// Glyph_Net_Browser/src/routes/DevTools.tsx
// Dev Tools dashboard inside the Glyph Net browser.

// NOTE: Photon Pay & WaveSend dev panels are routed in App.tsx
// (see DEV_ROUTES_ENABLED and the devtools hash block).
// This file remains the "normal" Dev Tools dashboard.

import { useState, useEffect } from "react";
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
  | "crystal"
  | "docs";

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
                                <code>{leg.channel}</code> · {leg.amount_pho} PHO →{" "}
                                {leg.to_account}
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
                          disabled={
                            d.status === "EXECUTED" || d.status === "CANCELLED"
                          }
                          onClick={() => handleSign(d.doc_id, d.party_a)}
                          style={{
                            padding: "3px 8px",
                            borderRadius: 999,
                            border: "1px solid #6b7280",
                            background: "#f9fafb",
                            color: "#374151",
                            fontSize: 10,
                            cursor:
                              d.status === "EXECUTED" ||
                              d.status === "CANCELLED"
                                ? "default"
                                : "pointer",
                          }}
                        >
                          Sign as {d.party_a}
                        </button>
                        <button
                          type="button"
                          disabled={
                            d.status === "EXECUTED" || d.status === "CANCELLED"
                          }
                          onClick={() => handleSign(d.doc_id, d.party_b)}
                          style={{
                            padding: "3px 8px",
                            borderRadius: 999,
                            border: "1px solid #6b7280",
                            background: "#f9fafb",
                            color: "#374151",
                            fontSize: 10,
                            cursor:
                              d.status === "EXECUTED" ||
                              d.status === "CANCELLED"
                                ? "default"
                                : "pointer",
                          }}
                        >
                          Sign as {d.party_b}
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
                            background:
                              d.status === "DRAFT" ? "#0369a1" : "#e5e7eb",
                            color:
                              d.status === "DRAFT" ? "#f9fafb" : "#9ca3af",
                            fontSize: 10,
                            cursor:
                              d.status === "DRAFT" ? "pointer" : "default",
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
                            background:
                              d.status === "ACTIVE" ? "#16a34a" : "#e5e7eb",
                            color:
                              d.status === "ACTIVE" ? "#ecfdf5" : "#9ca3af",
                            fontSize: 10,
                            cursor:
                              d.status === "ACTIVE" ? "pointer" : "default",
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