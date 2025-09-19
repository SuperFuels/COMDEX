// File: frontend/pages/sci/sci_atomsheet_panel.tsx
// 🎛 SCI AtomSheet Panel – Full Upgrade: Phase 5/6/7 integrations, LiveHUD, LightCone, QFC, Dev Fallback

import React, { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { CardContent } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";

// 🔌 Modular UI Panels
import EmotionSQIPanel from "@/components/SQS/EmotionSQIPanel";
import { CellOverlayPanel } from "@/components/SQS/CellOverlayPanel";
import { SheetTraceViewer } from "@/components/SQS/SheetTraceViewer";
import { LiveQpuCpuPanel } from "@/components/SQS/LiveQpuCpuPanel";
import Badge from "@/components/SQS/Badge";

// 🧠 Type for GlyphCell
interface GlyphCell {
  id: string;
  logic: string;
  position: number[];
  emotion?: string;
  prediction?: string;
  trace?: string[];
  linked_cells?: number[][];
  nested_logic?: string;
  sqi_score?: number;
  entropy?: number;
  novelty?: number;
  harmony?: number;
  validated?: boolean;
  result?: string;
  codexlang_render?: string;
  mutationNotes?: string[];
}

// 🌐 Config
const DEV_MODE = process.env.NODE_ENV !== "production";
const BASE_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const AUTH_TOKEN = "valid_token";
const [pinTrace, setPinTrace] = React.useState(false);
const [followSelection, setFollowSelection] = React.useState(true);

// Placeholder dev fallback sheet
const exampleSheet = {
  cells: [
    {
      id: "A1",
      logic: "x + 2",
      position: [0, 0, 0, 0],
      emotion: "inspired",
      prediction: "x predicts 2",
      trace: [],
      sqi_score: 0.5,
      validated: true,
      linked_cells: [],
    },
    {
      id: "B1",
      logic: "y * 3",
      position: [1, 0, 0, 0],
      emotion: "curious",
      prediction: "",
      trace: [],
      sqi_score: 0.5,
      validated: true,
      linked_cells: [],
    },
  ],
};
const MetricBadge = ({
  label,
  value,
  title,
}: {
  label: string;
  value?: number;
  title: string;
}) => {
  const v = typeof value === "number" ? Math.max(0, Math.min(1, value)) : undefined;
  // simple hue: 0→red (0), 60→yellow (0.5), 120→green (1)
  const hue = v === undefined ? 0 : Math.round(120 * v);
  const bg = v === undefined ? "bg-neutral-700" : undefined;
  return (
    <span
      className={[
        "px-1 py-[1px] rounded text-[10px] border",
        bg || "",
      ].join(" ")}
      style={v === undefined ? {} : { borderColor: `hsl(${hue} 70% 50%)`, color: `hsl(${hue} 70% 55%)` }}
      title={`${title}: ${v === undefined ? "—" : v.toFixed(2)}`}
    >
      {label}:{v === undefined ? "—" : v.toFixed(2)}
    </span>
  );
};
// Utility to render CodexLang to human-readable string (placeholder)
const tryInterpret = (logic: string) => `⟦${logic}⟧`;

function ErrorPill({ msg }: { msg?: string }) {
  if (!msg) return null;
  return (
    <span className="ml-2 inline-flex items-center rounded px-1.5 py-[1px] text-[10px] border border-red-700 text-red-300">
      ⚠ {msg}
    </span>
  );
}
// simple debounce (no lodash required)
function debounce<T extends (...args: any[]) => void>(fn: T, wait: number) {
  let t: any;
  const debounced = (...args: Parameters<T>) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
  (debounced as any).cancel = () => clearTimeout(t);
  return debounced as T & { cancel: () => void };
}
// 🔧 Panel props so this component can be hosted in SciPanelHost tabs
type SciAtomSheetProps = {
  wsUrl?: string;        // optional WS endpoint for live HUD/QFC
  containerId?: string;  // per-tab isolated container id (from host)
  defaultFile?: string;  // optional default .atom when fetching by file
};

export default function SCIAtomSheetPanel({
  wsUrl,
  containerId: providedContainerId,
  defaultFile,
}: SciAtomSheetProps) {
  const router = useRouter();

  // one source of truth for which .atom file is open
  const [sheetFile, setSheetFile] = useState<string>(
    defaultFile || "example_sheet.atom"
  );

  // UI state
  const [cells, setCells] = useState<GlyphCell[]>([]);
  const [rawMode, setRawMode] = useState(false);
  const [hoveredCell, setHoveredCell] = useState<GlyphCell | null>(null);
  const [lightconeTrace, setLightconeTrace] = useState<any[]>([]);
  const [traceMode, setTraceMode] = useState<"forward" | "reverse">("forward");

  // ensure URLs like ?file=myfile resolve to myfile.atom
  const normalizeAtomPath = React.useCallback((v: string) => {
    return /\.[A-Za-z0-9]+$/.test(v) ? v.replace(/\.sqs\.json$/i, ".atom") : `${v}.atom`;
  }, []);

  useEffect(() => {
    const qp = router.query.file;
    if (typeof qp === "string" && qp) {
      setSheetFile(normalizeAtomPath(qp));
    }
  }, [router.query.file, normalizeAtomPath]);

  // derive per-tab container; fallback to file name for standalone mode
  const containerId = React.useMemo(
    () => providedContainerId || sheetFile,
    [providedContainerId, sheetFile]
  );

  // ──────────────────────────────
  // Update sheet file from query param
  // ──────────────────────────────
  useEffect(() => {
    const fileParam = router.query.file;
    if (typeof fileParam === "string") {
      setSheetFile(fileParam);
    }
  }, [router.query.file]);

// === LightCone Live HUD (REST) ==============================================
// ──────────────────────────────
// Fetch AtomSheet (exec for E7 → fallback to GET → dev)
// ──────────────────────────────
const fetchSheet = React.useCallback(async () => {
  if (DEV_MODE) {
    // Dev fallback
    setCells(
      exampleSheet.cells.map((cell) => ({
        ...cell,
        codexlang_render: tryInterpret(cell.logic),
      }))
    );
    return;
  }

  // 1) Try execute to enrich with SQI + E7 metrics
  try {
    const execRes = await fetch(`${BASE_API_URL}/atomsheet/execute`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${AUTH_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        file: sheetFile,
        container_id: containerId,
        options: {
          benchmark_silent: true,
          batch_collapse: true,
          expand_nested: false,
          max_nested_depth: 1,
        },
      }),
    });

    if (execRes.ok) {
      const exec = await execRes.json();
      if (Array.isArray(exec?.cells)) {
        setCells(
          exec.cells.map((cell: any) => ({
            ...cell,
            codexlang_render: tryInterpret(cell.logic),
          }))
        );
        return; // success
      }
    } else {
      console.warn(`[atomsheet/execute] ${execRes.status} ${execRes.statusText}`);
    }
  } catch (e) {
    console.warn("⚠️ Execute for E7 metrics failed:", e);
  }

// 2) Fallback: plain GET /atomsheet
try {
  const url =
    `${BASE_API_URL}/atomsheet` +
    `?file=${encodeURIComponent(sheetFile)}` +
    `&container_id=${encodeURIComponent(containerId || "")}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const data = await res.json();

  setCells(
    (data.cells || []).map((cell: GlyphCell) => ({
      ...cell,
      // Prefer server-evaluated CodexLang preview; fallback to client interpreter
      codexlang_render:
        (cell as any).codex_eval && typeof (cell as any).codex_eval === "string"
          ? (cell as any).codex_eval
          : tryInterpret(cell.logic),
    }))
  );
} catch (err) {
  console.error("❌ Failed to fetch AtomSheet:", err);
  setCells([]);
}

useEffect(() => {
  fetchSheet();
}, [fetchSheet]);
// ──────────────────────────────
// LightCone HUD helpers (place after fetchSheet, before WS useEffect)
// ──────────────────────────────
const [pinTrace, setPinTrace] = useState(false);
const [followSelection, setFollowSelection] = useState(true);
const [selectedCellId, setSelectedCellId] = useState<string | null>(null);

// Calls /api/lightcone and updates your HUD state
const updateLiveHUD = React.useCallback(
  async (cid: string) => {
    if (!cid) return;
    try {
      const url =
        `${BASE_API_URL}/lightcone` +
        `?entry_id=${encodeURIComponent(cid)}` +
        `&direction=${encodeURIComponent(traceMode)}` +
        `&file=${encodeURIComponent(sheetFile)}` +
        `&container_id=${encodeURIComponent(containerId || "")}`;

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      setLightconeTrace(data.trace || []);
    } catch (err) {
      console.warn("LightCone update failed:", err);
      setLightconeTrace([]);
    }
  },
  [BASE_API_URL, AUTH_TOKEN, containerId, sheetFile, traceMode]
);

// Debounced wrapper
const debouncedUpdateLiveHUD = React.useMemo(
  () => debounce((cid: string) => updateLiveHUD(cid), 250),
  [updateLiveHUD]
);

// Cleanup so pending timers don’t fire after navigation
React.useEffect(() => {
  return () => debouncedUpdateLiveHUD?.cancel?.();
}, [debouncedUpdateLiveHUD]);

// Follow the current selection when enabled
React.useEffect(() => {
  if (!followSelection) return;
  if (selectedCellId) debouncedUpdateLiveHUD(selectedCellId);
}, [followSelection, selectedCellId, debouncedUpdateLiveHUD]);

// Clear HUD when unpinned and focus is lost
const handleCellMouseLeave = React.useCallback(() => {
  if (!pinTrace) setLightconeTrace([]);
}, [pinTrace]);
// ──────────────────────────────
// Optional live updates (Phase 9/10 streams) — safe no-op if wsUrl is not set
// ──────────────────────────────
useEffect(() => {
  if (typeof window === "undefined") return; // SSR guard
  if (!wsUrl || !containerId) return;

  const url =
    `${wsUrl}${wsUrl.includes("?") ? "&" : "?"}` +
    `container_id=${encodeURIComponent(containerId)}`;

  let ws: WebSocket | null = null;

  try {
    ws = new WebSocket(url);

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        // examples broadcast by backend:
        // - qpu_beam_timeline
        // - qpu_phase9_dreams
        // - qpu_phase10_vectorized
        // - qpu_sheet_metrics
        if (msg?.type === "qpu_beam_timeline" && Array.isArray(msg.timeline)) {
          setLightconeTrace(msg.timeline);
        }
        // add more handlers as needed
      } catch {
        /* ignore parse errors */
      }
    };

    ws.onerror = () => {
      /* noop */
    };
  } catch {
    // ignore WS construction errors; panel still works via REST
  }

  return () => {
    try {
      ws?.close();
    } catch {
      /* noop */
    }
  };
}, [wsUrl, containerId]);

  // ──────────────────────────────
  // Fetch LightCone QFC / HUD projection
  // ──────────────────────────────
  // LightCone fetch (elsewhere in the file)
  const fetchLightConeQFC = async (entryId: string, direction: "forward" | "reverse") => {
    try {
      const url =
        `${BASE_API_URL}/lightcone` +
        `?file=${encodeURIComponent(sheetFile)}` +
        `&entry_id=${encodeURIComponent(entryId)}` +
        `&direction=${encodeURIComponent(direction)}` +
        `&container_id=${encodeURIComponent(containerId)}`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${AUTH_TOKEN}` } });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      return data.trace || [];
    } catch (err) {
      console.error(`❌ Failed to fetch LightCone QFC nodes for ${entryId}:`, err);
      return [];
    }
  };

  // Inside updateLiveHUD (the inner fetch), include container_id too:
  const res = await fetch(
    `${BASE_API_URL}/qfc_entanglement` +
      `?cell_id=${encodeURIComponent(cellId)}` +
      `&file=${encodeURIComponent(sheetFile)}` +
      `&container_id=${encodeURIComponent(containerId)}`,
    { headers: { Authorization: `Bearer ${AUTH_TOKEN}` } }
  );

  const updateLiveHUD = async (cellId: string) => {
    try {
      const lightconeNodes = await fetchLightConeQFC(cellId, traceMode);

      // Optionally fetch entanglement / prediction fork updates
      let entangledUpdates: any[] = [];
      try {
        const url =
          `${BASE_API_URL}/qfc_entanglement` +
          `?cell_id=${encodeURIComponent(cellId)}` +
          `&file=${encodeURIComponent(sheetFile)}` +
          `&container_id=${encodeURIComponent(containerId)}`;

        const res = await fetch(url, {
          headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
        });
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const data = await res.json();
        entangledUpdates = data.updates || [];
      } catch (err) {
        console.warn(`⚠️ Failed to fetch entangled updates for ${cellId}:`, err);
      }

      setLightconeTrace([...lightconeNodes, ...entangledUpdates]);
    } catch (err) {
      console.error(`❌ LiveHUD update failed for ${cellId}:`, err);
      setLightconeTrace([]);
    }
  };

  const fetchEntangledQFC = async (cellId: string) => {
    try {
      const res = await fetch(
        `${BASE_API_URL}/qfc_entangled?cell_id=${encodeURIComponent(cellId)}&container_id=${encodeURIComponent(containerId)}`,
        { headers: { Authorization: `Bearer ${AUTH_TOKEN}` } }
      );
      const data = await res.json();
      return data.updates || [];
    } catch (err) {
      console.error(`❌ Failed to fetch entangled QFC for ${cellId}:`, err);
      return [];
    }
  };
{/* ── Panel Header / Controls ───────────────────────────────────────── */}
<div className="flex items-center gap-2 mb-2 border-b border-neutral-800 pb-2">
  {/* left: context info (optional) */}
  <div className="text-xs text-zinc-400">
    container: <span className="text-zinc-200">{containerId || "—"}</span>
  </div>

  {/* right: actions */}
  <div className="ml-auto flex items-center gap-2">
    <button
      className="px-2 py-1 text-xs rounded border border-zinc-700 hover:bg-white/10"
      onClick={() => setPinTrace(v => !v)}
    >
      {pinTrace ? "📌 Unpin Trace" : "📌 Pin Trace"}
    </button>
    <button
      className="px-2 py-1 text-xs rounded border border-zinc-700 hover:bg-white/10"
      onClick={() => setFollowSelection(v => !v)}
    >
      {followSelection ? "🧲 Stop Follow" : "🧲 Follow Hover"}
    </button>
  </div>
</div>
{/* ─────────────────────────────────────────────────────────────────── */}
  // ──────────────────────────────
  // Build 4D grid from loaded cells
  // ──────────────────────────────
<div
  key={`slot-${t}-${z}-${y}-${x}`}
  className={[
    "relative rounded border",
    cell ? "border-zinc-700 bg-neutral-900" : "border-dashed border-zinc-800 bg-neutral-950/60",
    "min-h-[96px] p-2",
  ].join(" ")}

  /* DnD: allow drop into empty slots to create a cell */
  onDragOver={(e) => e.preventDefault()}
  onDrop={async (e) => {
    e.preventDefault();
    if (cell) return; // only create into empty slots
    try {
      const raw = e.dataTransfer.getData("application/x-sci-graph");
      if (!raw) return;
      const payload = JSON.parse(raw); // { logic, emotion?, meta? }
      const position = [x, y, z, t];

      const res = await fetch(`${BASE_API_URL}/atomsheet/upsert`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          file: sheetFile,
          logic: payload.logic,
          position,
          emotion: payload.emotion || "neutral",
          meta: payload.meta || {},
        }),
      });

      if (res.ok) {
        await fetchSheet(); // refresh grid
      } else {
        console.warn("DnD upsert HTTP error:", res.status, res.statusText);
      }
    } catch (err) {
      console.warn("DnD upsert failed:", err);
    }
  }}

  /* LiveHUD: follow hover (debounced) and clear on leave when not pinned */
  onMouseEnter={() => {
    if (!cell?.id) return;
    setHoveredCell(cell);
    setSelectedCellId(cell.id);
    if (followSelection && !pinTrace) debouncedUpdateLiveHUD(cell.id);
  }}
  onMouseLeave={() => {
    setHoveredCell(null);
    handleCellMouseLeave();
  }}

  /* Click → immediate trace + pin */
  onClick={() => {
    if (!cell?.id) return;
    setSelectedCellId(cell.id);
    updateLiveHUD(cell.id); // non-debounced
    setPinTrace(true);
  }}

  /* existing drag start for copying cells out */
  draggable={!!cell}
  onDragStart={(e: React.DragEvent<HTMLDivElement>) => {
    if (cell) e.dataTransfer.setData("cell", JSON.stringify(cell));
  }}
>
  <CardContent className="w-full h-full">
    {cell ? (
      <div className="relative flex flex-col justify-between h-full text-xs">
        {/* top: logic / codexlang */}
        <div className="font-mono text-sm break-words pr-12">
          {rawMode ? cell.logic : cell.codexlang_render}
          {(cell as any)?.codex_error && <ErrorPill msg={(cell as any).codex_error} />}
        </div>

        {/* bottom: SQI + E7 + prediction + scrolls/memory */}
        <div className="flex items-center justify-between text-[10px] pt-1">
          <div className="flex items-center gap-2">
            <EmotionSQIPanel emotion={cell.emotion} sqi={cell.sqi_score} />

            {/* E7 badges */}
            <div className="flex items-center gap-1">
              <span
                className="px-1 py-[1px] rounded text-[10px] border"
                title={`Harmony: ${typeof cell.harmony === "number" ? cell.harmony.toFixed(2) : "—"}`}
                style={
                  typeof cell.harmony === "number"
                    ? {
                        borderColor: `hsl(${Math.round(120 * cell.harmony)} 70% 50%)`,
                        color: `hsl(${Math.round(120 * cell.harmony)} 70% 55%)`,
                      }
                    : {}
                }
              >
                H:{typeof cell.harmony === "number" ? cell.harmony.toFixed(2) : "—"}
              </span>
              <span
                className="px-1 py-[1px] rounded text-[10px] border"
                title={`Novelty: ${typeof cell.novelty === "number" ? cell.novelty.toFixed(2) : "—"}`}
                style={
                  typeof cell.novelty === "number"
                    ? {
                        borderColor: `hsl(${Math.round(120 * cell.novelty)} 70% 50%)`,
                        color: `hsl(${Math.round(120 * cell.novelty)} 70% 55%)`,
                      }
                    : {}
                }
              >
                N:{typeof cell.novelty === "number" ? cell.novelty.toFixed(2) : "—"}
              </span>
              <span
                className="px-1 py-[1px] rounded text-[10px] border"
                title={`Entropy: ${typeof cell.entropy === "number" ? cell.entropy.toFixed(2) : "—"}`}
                style{
                  typeof cell.entropy === "number"
                    ? {
                        borderColor: `hsl(${Math.round(120 * cell.entropy)} 70% 50%)`,
                        color: `hsl(${Math.round(120 * cell.entropy)} 70% 55%)`,
                      }
                    : {}
                }
              >
                E:{typeof cell.entropy === "number" ? cell.entropy.toFixed(2) : "—"}
              </span>
            </div>

            {/* 📜 Scrolls/Memory popover */}
            {(
              ((cell as any)?.scrolls &&
                (Array.isArray((cell as any).scrolls) ? (cell as any).scrolls.length > 0 : true)) ||
              ((cell as any)?.memory &&
                (Array.isArray((cell as any).memory) ? (cell as any).memory.length > 0 : true))
            ) && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className="px-1 py-[1px] text-[10px] rounded border border-zinc-700 text-zinc-300 hover:bg-white/10"
                    title="View Scrolls & Memory"
                  >
                    📜
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-sm text-left">
                  <div className="text-xs space-y-1">
                    {(cell as any)?.scrolls && (
                      <div>
                        <div className="font-semibold text-zinc-300 mb-1">Scrolls</div>
                        {Array.isArray((cell as any).scrolls) ? (
                          <ul className="list-disc pl-4">
                            {(cell as any).scrolls.map((s: any, i: number) => (
                              <li key={i} className="text-zinc-200 break-words">
                                {String(s)}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="text-zinc-200 break-words">
                            {String((cell as any).scrolls)}
                          </div>
                        )}
                      </div>
                    )}
                    {(cell as any)?.memory && (
                      <div className="pt-1">
                        <div className="font-semibold text-zinc-300 mb-1">Memory</div>
                        {Array.isArray((cell as any).memory) ? (
                          <ul className="list-disc pl-4">
                            {(cell as any).memory.map((m: any, i: number) => (
                              <li key={i} className="text-zinc-200 break-words">
                                {String(m)}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="text-zinc-200 break-words">
                            {String((cell as any).memory)}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </TooltipContent>
              </Tooltip>
            )}
          </div>

          {/* right side: prediction (if any) */}
          {cell.prediction && (
            <span className="text-yellow-300 whitespace-nowrap">🔮 {cell.prediction}</span>
          )}
        </div>

        {/* nested-expansion quick action (A5) */}
        {(cell as any)?.meta?.nested?.type === "ref" &&
          (cell as any)?.meta?.nested?.path && (
            <button
              className="absolute top-1 right-1 text-[10px] px-1 py-[2px] rounded border border-zinc-700 text-zinc-300 hover:bg-white/10"
              onClick={(e) => {
                e.stopPropagation();
                const childPath = (cell as any).meta.nested.path as string;
                router.push(`/sci/sci_atomsheet_panel?file=${encodeURIComponent(childPath)}`);
              }}
              title="Expand nested AtomSheet"
              aria-label="Expand nested AtomSheet"
            >
              ↘ expand
            </button>
          )}
      </div>
    ) : (
      <div className="h-full w-full flex items-center justify-center text-[10px] text-zinc-500">
        Drop from SCI Graph…
      </div>
    )}
  </CardContent>
</div>

  // ──────────────────────────────
  // (Render section begins below)
  // ──────────────────────────────

return (
  <div className="p-6 relative">
    {/* ───────────── HEADER ───────────── */}
    <div className="flex justify-between items-center mb-4">
      <h2 className="text-2xl font-bold">🧠 AtomSheet Viewer (.atom)</h2>
      <div className="flex gap-2">
        <Button variant="outline" onClick={fetchSheet}>🔁 Reload</Button>
        <Button variant="outline" onClick={() => setRawMode(!rawMode)}>
          {rawMode ? "🔣 Show CodexLang" : "🧬 Show Raw"}
        </Button>
        <Button variant="outline" onClick={() => setTraceMode(prev => prev === "forward" ? "reverse" : "forward")}>
          🌌 {traceMode === "forward" ? "→ Forward" : "← Reverse"}
        </Button>
      </div>
    </div>

    {/* ───────────── LIGHTCONE TRACE ───────────── */}
    {lightconeTrace.length > 0 && (
      <div className="mb-4">
        <h4 className="text-md font-semibold">🌌 LightCone Trace</h4>
        <SheetTraceViewer trace={lightconeTrace} />
      </div>
    )}

    {/* ───────────── LIVE QPU/CPU PANEL ───────────── */}
    <div className="mb-4">
      <h4 className="text-md font-semibold">⚛️ Live CPU / QPU Metrics</h4>
      <LiveQpuCpuPanel containerId={containerId} />
    </div>

    {/* ───────────── GRID ───────────── */}
    {grid.map((zLayers, t) => (
      <div key={`time-${t}`} className="mb-4">
        <h3 className="text-lg font-semibold">Time Layer {t}</h3>
        {zLayers.map((rows, z) => (
          <div key={`z-${z}`} className="mb-2">
            <h4 className="text-md font-medium">Z Level {z}</h4>
            <div
              className="grid gap-2"
              style={{ gridTemplateColumns: `repeat(${maxX + 1}, minmax(100px, 1fr))` }}
            >
              {rows.map((row, y) =>
                row?.map((cell, x) => (
                  <Tooltip key={`${t}-${z}-${y}-${x}`}>
                    <TooltipTrigger asChild>
                      <div
                        className="h-24 p-2 flex items-center justify-center text-center hover:bg-gray-700 hover:shadow-xl transition-all border rounded bg-white/5"
                        draggable
                        onMouseEnter={() => {
                          setHoveredCell(cell || null);
                          if (cell?.id && followSelection && !pinTrace) {
                            debouncedUpdateLiveHUD(cell.id);
                          }
                        }}
                        onMouseLeave={() => {
                          setHoveredCell(null);
                          setLightconeTrace([]);
                        }}
                        onClick={() => {
                          if (!cell?.id) return;
                          // Immediate (non-debounced) trace + pin
                          updateLiveHUD(cell.id);
                          setPinTrace(true);
                        }}
                        onDragStart={(e: React.DragEvent<HTMLDivElement>) => {
                          if (cell) e.dataTransfer.setData("cell", JSON.stringify(cell));
                        }}
                      >
                        <CardContent className="w-full h-full">
                          {cell ? (
                            <div className="relative flex flex-col justify-between h-full text-xs">
                              {/* top: logic / codexlang */}
                              <div className="font-mono text-sm break-words pr-12">
                                {rawMode ? cell.logic : cell.codexlang_render}
                                {(cell as any)?.codex_error && <ErrorPill msg={(cell as any).codex_error} />}
                              </div>

                              {/* bottom: SQI + E7 + prediction */}
                              <div className="flex items-center justify-between text-[10px] pt-1">
                                <div className="flex items-center gap-2">
                                  <EmotionSQIPanel emotion={cell.emotion} sqi={cell.sqi_score} />
                                  {/* E7 badges */}
                                  <div className="flex items-center gap-1">
                                    <Badge label="H" value={cell.harmony} title="Harmony: structural consistency" />
                                    <Badge label="N" value={cell.novelty} title="Novelty: divergence from prior patterns" />
                                    <Badge label="E" value={cell.entropy} title="Entropy: uncertainty / dispersion" />
                                  </div>
                                </div>

                                {cell.prediction && (
                                  <span className="text-yellow-300 whitespace-nowrap">🔮 {cell.prediction}</span>
                                )}
                              </div>

                              {/* nested-expansion quick action (A5) */}
                              {(cell as any)?.meta?.nested?.type === "ref" &&
                                (cell as any)?.meta?.nested?.path && (
                                  <button
                                    className="absolute top-1 right-1 text-[10px] px-1 py-[2px] rounded border border-zinc-700 text-zinc-300 hover:bg-white/10"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      const childPath = (cell as any).meta.nested.path as string;
                                      router.push(
                                        `/sci/sci_atomsheet_panel?file=${encodeURIComponent(childPath)}`
                                      );
                                    }}
                                    title="Expand nested AtomSheet"
                                  >
                                    ↘ expand
                                  </button>
                                )}
                            </div>
                          ) : (
                            <div className="text-gray-300">·</div>
                          )}
                        </CardContent>
                      </div>
                    </TooltipTrigger>
                    {cell && (
                      <TooltipContent className="max-w-sm text-left">
                        <div className="text-xs">
                          <strong>ID:</strong> {cell.id}<br />
                          <strong>Position:</strong> [{cell.position.join(", ")}]<br />
                          <strong>Validated:</strong> {cell.validated ? "✅" : "❌"}<br />
                          <strong>Result:</strong> {cell.result || "—"}<br />
                          <strong>Prediction:</strong> {cell.prediction || "—"}<br />
                        </div>
                      </TooltipContent>
                    )}
                  </Tooltip>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    ))}

    {/* ───────────── HOVER PANEL ───────────── */}
    {hoveredCell && (
      <div className="absolute top-0 right-0 p-4 z-50">
        <CellOverlayPanel cell={hoveredCell} />
      </div>
    )}
  </div>
);

// 🧪 DEV fallback
const exampleSheet: { cells: GlyphCell[] } = {
  cells: [
    {
      id: "a1",
      logic: "x + 2",
      position: [0, 0, 0, 0],
      sqi_score: 0.91,
      emotion: "curious",
      validated: true,
      result: "Result(x + 2)",
      prediction: "4",
      entropy: 0.42,
      mutationNotes: ["renamed x to foo"],
    },
    {
      id: "a2",
      logic: "sin(y)",
      position: [1, 0, 0, 0],
      sqi_score: 0.88,
      emotion: "introspective",
      validated: true,
      result: "Result(sin(y))",
      prediction: "~0.84",
      entropy: 0.37,
    },
    {
      id: "b1",
      logic: "if x > 0: return x**2",
      position: [0, 1, 0, 0],
      sqi_score: 0.95,
      emotion: "protective",
      validated: false,
      result: "⚠️ Blocked by SoulLaw",
      mutationNotes: ["contradiction injected"],
    },
  ],
};

// 🧠 CodexLang toggle
function tryInterpret(raw: string): string {
  if (!raw || typeof raw !== "string") return raw;
  try {
    if (/(if|return|for|while|\+|\*|=>|⊕|∨|∧|¬|→)/.test(raw)) {
      return `⟦ Logic | ${raw} ⟧`;
    }
    return `⟦ ${raw} ⟧`;
  } catch (e) {
    return raw;
  }
}

// --- E7 helpers: badge tone + safe percent ---
const pct = (v?: number) => (typeof v === "number" ? Math.round(v * 100) : null);

// green → yellow → red
const metricTone = (v?: number) => {
  if (v == null || Number.isNaN(v)) return "border-zinc-700 text-zinc-400";
  if (v < 0.33) return "border-red-500/40 text-red-300";
  if (v < 0.66) return "border-amber-500/40 text-amber-300";
  return "border-emerald-500/40 text-emerald-300";
};

const Badge = ({
  label,
  value,
  title,
}: {
  label: string;
  value?: number;
  title: string;
}) => (
  <Tooltip>
    <TooltipTrigger asChild>
      <span
        className={[
          "inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] leading-none cursor-default",
          metricTone(value),
        ].join(" ")}
        title={title}
      >
        <span className="opacity-80">{label}</span>
        <span className="font-medium">{value == null ? "—" : `${pct(value)}%`}</span>
      </span>
    </TooltipTrigger>
    <TooltipContent>{title}</TooltipContent>
  </Tooltip>
);