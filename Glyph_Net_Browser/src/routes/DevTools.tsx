// Glyph_Net_Browser/src/routes/DevTools.tsx
// Dev Tools dashboard inside the Glyph Net browser.

import { useState, useEffect } from "react";
import PhotonEditor from "../components/PhotonEditor";
import LedgerInspector from "../components/LedgerInspector";
import PhotonGuide from "../components/PhotonGuide";
import DevPitch from "../components/DevPitch";
import AionMemoryFieldPanel from "../components/AionMemoryFieldPanel";
import CrystalPanel from "../components/CrystalPanel";

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
  | "crystal";

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

  // 📚 Holo index (history)
  const [holoIndex, setHoloIndex] = useState<HoloIndexEntry[] | null>(null);
  const [loadingIndex, setLoadingIndex] = useState(false);

  type FrameMetric = {
    psi: number;
    kappa: number;
    tau: number;
    coherence: number;
  };

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

  // 📚 Load holo index whenever container changes
  useEffect(() => {
    if (!activeContainerId) {
      setHoloIndex(null);
      return;
    }

    let cancelled = false;
    setLoadingIndex(true);

    listHolosForContainer(activeContainerId)
      .then((entries) => {
        if (!cancelled) setHoloIndex(entries);
      })
      .catch(() => {
        if (!cancelled) setHoloIndex(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingIndex(false);
      });

    return () => {
      cancelled = true;
    };
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
      const kappa = Math.min(0.99, 0.5 + 0.02 * ((n + 1) % 5) + 0.008 * Math.log10(base + 1));
      const tau = Math.min(0.99, 0.4 + 0.015 * ((n + 2) % 5) + 0.006 * Math.log10(base + 2));
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
        result.new_revision ??
        updatedHolo?.version?.revision ??
        null;

      const consoleText =
        result.output
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
        nextRevision, // 👈 key change: pass revision
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
        gap: 16,
      }}
    >
      {/* Header – compact */}
      <header
        style={{
          marginBottom: 4,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
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
              color: "#9ca3af",
            }}
          >
            {activeContainerId && (
              <>
                container: <code>{activeContainerId}</code>
                {" · "}
              </>
            )}
            holo:{" "}
            {holo ? (
              <code>{holo.holo_id}</code>
            ) : (
              <span style={{ opacity: 0.7 }}>none</span>
            )}
          </div>
        )}
      </header>

      {/* Tool switcher + (optional) field status */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <div
          style={{
            display: "inline-flex",
            flexWrap: "wrap",
            borderRadius: 999,
            border: "1px solid #e5e7eb",
            background: "#f9fafb",
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
        </div>

        {activeTool === "field" && (
          <div
            style={{
              fontSize: 11,
              color: "#6b7280",
              display: "flex",
              alignItems: "center",
              gap: 6,
              whiteSpace: "nowrap",
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

      {/* Active tool card */}
      <section
        style={{
          flex: 1,
          borderRadius: 12,
          border: "1px solid #e5e7eb",
          background: "#f9fafb",
          padding: 12,
          overflow: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 8,
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
        ) : (
          // Field Lab: HologramContainerView + Holo file "cabinet"
          <div
            style={{
              flex: 1,
              minHeight: 320,
              display: "flex",
              gap: 12,
            }}
          >
            {/* Left: Holo “file cabinet” */}
            <div
              style={{
                width: 240,
                borderRadius: 10,
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
                  fontSize: 11,
                  fontWeight: 600,
                  color: "#111827",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span>Holo Files</span>
                {loadingIndex && (
                  <span style={{ fontSize: 10, color: "#9ca3af" }}>
                    loading…
                  </span>
                )}
              </div>

              {/* simple pseudo tree listing */}
              <div
                style={{
                  fontSize: 11,
                  color: "#374151",
                  maxHeight: 260,
                  overflow: "auto",
                }}
              >
                {holoIndex && holoIndex.length > 0 ? (
                  holoIndex
                    .slice()
                    .sort(
                      (a, b) =>
                        (b.tick ?? 0) - (a.tick ?? 0) ||
                        (b.revision ?? 0) - (a.revision ?? 0),
                    )
                    .map((entry) => {
                      const isActive =
                        holo &&
                        entry.holo_id === (holo as any).holo_id &&
                        entry.revision === (holo as any).revision;
                      const label =
                        entry.tags?.includes("frame_main") ||
                        entry.tags?.includes("main")
                          ? "main.holo"
                          : entry.tags?.includes("loop")
                          ? "loop.holo"
                          : entry.tags?.includes("exec")
                          ? "exec.holo"
                          : entry.tags?.includes("output")
                          ? "output.holo"
                          : `t=${entry.tick ?? 0} · v${entry.revision ?? 1}`;

                      return (
                        <button
                          key={entry.holo_id + ":" + (entry.revision ?? 1)}
                          type="button"
                          onClick={() => handleLoadHoloAt(entry)}
                          style={{
                            width: "100%",
                            textAlign: "left",
                            border: "none",
                            background: isActive
                              ? "rgba(15,23,42,0.9)"
                              : "transparent",
                            color: isActive ? "#e5e7eb" : "#111827",
                            borderRadius: 6,
                            padding: "4px 6px",
                            marginBottom: 2,
                            cursor: "pointer",
                            fontSize: 11,
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                            }}
                          >
                            <span>{label}</span>
                            <span
                              style={{
                                fontSize: 10,
                                color: isActive ? "#9ca3af" : "#6b7280",
                              }}
                            >
                              t={entry.tick ?? 0} · v{entry.revision ?? 1}
                            </span>
                          </div>
                        </button>
                      );
                    })
                ) : (
                  <div
                    style={{
                      fontSize: 11,
                      color: "#9ca3af",
                      padding: "4px 2px",
                    }}
                  >
                    no snapshots yet
                  </div>
                )}
              </div>

              {/* Mini hint about frames */}
              <div
                style={{
                  marginTop: "auto",
                  paddingTop: 6,
                  borderTop: "1px solid #e5e7eb",
                  fontSize: 10,
                  color: "#6b7280",
                }}
              >
                Program frames:
                <ul
                  style={{
                    listStyle: "none",
                    paddingLeft: 0,
                    margin: 0,
                    marginTop: 2,
                  }}
                >
                  {programFrames.map((f: any) => {
                    const fm = lastRunInfo.frameMetrics[f.id];
                    return (
                      <li key={f.id} style={{ marginBottom: 2 }}>
                        • {f.label || f.id}
                        {fm && (
                          <span
                            style={{
                              marginLeft: 4,
                              fontSize: 10,
                              color: "#4b5563",
                            }}
                          >
                            — ψ {fm.psi.toFixed(2)} · κ {fm.kappa.toFixed(2)} · τ{" "}
                            {fm.tau.toFixed(2)}
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>

            {/* Right: 3D canvas container */}
            <div style={{ flex: 1 }}>
              <HologramContainerView
                containerId={activeContainerId ?? "dc_aion_core"}
                title="Hologram Container"
              />
            </div>
          </div>
        )}

        {exportError && activeTool === "field" && (
          <div style={{ fontSize: 11, color: "#b91c1c" }}>{exportError}</div>
        )}

        {activeTool === "field" && (
          <div
            style={{
              marginTop: 8,
              display: "flex",
              flexDirection: "column",
              gap: 4,
            }}
          >
            {/* Runs summary */}
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

            {/* Buttons row: Rehydrate + Export */}
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
        padding: "4px 10px", // smaller
        borderRadius: 999,
        cursor: "pointer",
        fontSize: 11, // smaller
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        minWidth: 120, // less wide
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