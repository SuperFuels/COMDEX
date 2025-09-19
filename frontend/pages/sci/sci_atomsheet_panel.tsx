// File: frontend/pages/sci/sci_atomsheet_panel.tsx
// 🎛 SCI AtomSheet Panel – Phase 5/6/7 integrations, LiveHUD, LightCone, QFC, Dev Fallback

import React from "react";
import { useRouter } from "next/router";
import { CardContent } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";

// 🔌 Modular UI Panels
import EmotionSQIPanel from "@/components/SQS/EmotionSQIPanel";
import { CellOverlayPanel } from "@/components/SQS/CellOverlayPanel";
import { SheetTraceViewer } from "@/components/SQS/SheetTraceViewer";
import { LiveQpuCpuPanel } from "@/components/SQS/LiveQpuCpuPanel";
import Badge from "@/components/SQS/Badge";

/* ────────────────────────────────────────────────────────────────────────── */
/* Types                                                                     */
/* ────────────────────────────────────────────────────────────────────────── */
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

/* ────────────────────────────────────────────────────────────────────────── */
/* Config & Dev Fallback                                                     */
/* ────────────────────────────────────────────────────────────────────────── */
const DEV_MODE = process.env.NODE_ENV !== "production";
const BASE_API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api";
const AUTH_TOKEN = "valid_token";

/** Placeholder dev fallback sheet (used only when DEV_MODE=true) */
const exampleSheet: { cells: GlyphCell[] } = {
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

/* ────────────────────────────────────────────────────────────────────────── */
/* Small helpers                                                             */
/* ────────────────────────────────────────────────────────────────────────── */

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
  const hue = v === undefined ? 0 : Math.round(120 * v);
  const bg = v === undefined ? "bg-neutral-700" : undefined;
  return (
    <span
      className={["px-1 py-[1px] rounded text-[10px] border", bg || ""].join(" ")}
      style={
        v === undefined
          ? {}
          : { borderColor: `hsl(${hue} 70% 50%)`, color: `hsl(${hue} 70% 55%)` }
      }
      title={`${title}: ${v === undefined ? "—" : v.toFixed(2)}`}
    >
      {label}:{v === undefined ? "—" : v.toFixed(2)}
    </span>
  );
};

const tryInterpret = (logic: string) => `⟦${logic}⟧`;

function ErrorPill({ msg }: { msg?: string }) {
  if (!msg) return null;
  return (
    <span className="ml-2 inline-flex items-center rounded px-1.5 py-[1px] text-[10px] border border-red-700 text-red-300">
      ⚠ {msg}
    </span>
  );
}

/** simple debounce (no lodash required) */
function debounce<T extends (...args: any[]) => void>(fn: T, wait: number) {
  let t: any;
  const debounced = (...args: Parameters<T>) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
  (debounced as any).cancel = () => clearTimeout(t);
  return debounced as T & { cancel: () => void };
}

/* ────────────────────────────────────────────────────────────────────────── */
/* Component                                                                 */
/* ────────────────────────────────────────────────────────────────────────── */
type SciAtomSheetProps = {
  wsUrl?: string;
  containerId?: string;
  defaultFile?: string;
};

export default function SCIAtomSheetPanel({
  wsUrl,
  containerId: providedContainerId,
  defaultFile,
}: SciAtomSheetProps) {
  const router = useRouter();

  // One source of truth for which .atom file is open
  const [sheetFile, setSheetFile] = React.useState<string>(
    defaultFile || "backend/data/sheets/example_sheet.atom"
  );

  // UI state
  const [cells, setCells] = React.useState<GlyphCell[]>([]);
  const [rawMode, setRawMode] = React.useState(false);
  const [hoveredCell, setHoveredCell] = React.useState<GlyphCell | null>(null);
  const [lightconeTrace, setLightconeTrace] = React.useState<any[]>([]);
  const [traceMode, setTraceMode] = React.useState<"forward" | "reverse">("forward");

  // derive per-tab container; fallback to file name for standalone mode
  const containerId = React.useMemo(
    () => providedContainerId || sheetFile,
    [providedContainerId, sheetFile]
  );

  // Ensure URLs like ?file=myfile resolve to myfile.atom
  const normalizeAtomPath = React.useCallback((v: string) => {
    return /\.[A-Za-z0-9]+$/.test(v)
      ? v.replace(/\.sqs\.json$/i, ".atom")
      : `${v}.atom`;
  }, []);

  React.useEffect(() => {
    const qp = router.query.file;
    if (typeof qp === "string" && qp) {
      setSheetFile(normalizeAtomPath(qp));
    }
  }, [router.query.file, normalizeAtomPath]);

  /* ── Fetch AtomSheet (exec for E7 → fallback to GET → dev) ───────────── */
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
  }, [containerId, sheetFile]);

  React.useEffect(() => {
    fetchSheet();
  }, [fetchSheet]);

  /* ── LightCone HUD state & updater ────────────────────────────────────── */
  const [pinTrace, setPinTrace] = React.useState(false);
  const [followSelection, setFollowSelection] = React.useState(true);
  const [selectedCellId, setSelectedCellId] = React.useState<string | null>(null);

  // Calls /api/lightcone and updates HUD state (single source of truth)
  const updateLiveHUD = React.useCallback(
    async (cellId: string) => {
      if (!cellId) return;

      try {
        // 1) Base LightCone nodes
        const lightconeNodes = await fetchLightConeQFC(cellId, traceMode);

        // 2) Optional entanglement / prediction-fork updates
        let entangledUpdates: any[] = [];
        try {
          const entRes = await fetch(
            `${BASE_API_URL}/qfc_entanglement` +
              `?cell_id=${encodeURIComponent(cellId)}` +
              `&file=${encodeURIComponent(sheetFile)}` +
              `&container_id=${encodeURIComponent(containerId || "")}`,
            { headers: { Authorization: `Bearer ${AUTH_TOKEN}` } }
          );
          if (entRes.ok) {
            const data = await entRes.json();
            entangledUpdates = data.updates || [];
          }
        } catch (err) {
          console.warn(`⚠️ Failed to fetch entangled updates for ${cellId}:`, err);
        }

        setLightconeTrace([...lightconeNodes, ...entangledUpdates]);
      } catch (err) {
        console.error(`❌ LiveHUD update failed for ${cellId}:`, err);
        setLightconeTrace([]);
      }
    },
    [containerId, sheetFile, traceMode]
  );

  // Debounced variant for hover-follow
  const debouncedUpdateLiveHUD = React.useMemo(
    () => debounce(updateLiveHUD, 150),
    [updateLiveHUD]
  );

  // Cleanup so pending timers don’t fire after navigation
  React.useEffect(() => {
    return () => debouncedUpdateLiveHUD?.cancel?.();
  }, [debouncedUpdateLiveHUD]);

  // Follow the current selection when enabled
  React.useEffect(() => {
    if (!followSelection || !selectedCellId) return;
    debouncedUpdateLiveHUD(selectedCellId);
  }, [followSelection, selectedCellId, debouncedUpdateLiveHUD]);

  // Clear HUD when unpinned and focus is lost
  const handleCellMouseLeave = React.useCallback(() => {
    if (!pinTrace) setLightconeTrace([]);
  }, [pinTrace]);

  // Optional live updates (Phase 9/10 streams) — safe no-op if wsUrl is not set
  React.useEffect(() => {
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
        } catch {
          /* ignore parse errors */
        }
      };
      ws.onerror = () => { /* noop */ };
    } catch {
      // ignore WS construction errors; panel still works via REST
    }

    return () => {
      try { ws?.close(); } catch { /* noop */ }
    };
  }, [wsUrl, containerId]);

  // Fetch LightCone QFC / HUD projection helper
  const fetchLightConeQFC = React.useCallback(
    async (entryId: string, direction: "forward" | "reverse") => {
      try {
        const url =
          `${BASE_API_URL}/lightcone` +
          `?file=${encodeURIComponent(sheetFile)}` +
          `&entry_id=${encodeURIComponent(entryId)}` +
          `&direction=${encodeURIComponent(direction)}` +
          `&container_id=${encodeURIComponent(containerId || "")}`;

        const res = await fetch(url, {
          headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
        });
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const data = await res.json();
        return data.trace || [];
      } catch (err) {
        console.error(`❌ Failed to fetch LightCone QFC nodes for ${entryId}:`, err);
        return [];
      }
    },
    [containerId, sheetFile]
  );

  // (Optional) separate helper if you need it elsewhere
  const fetchEntangledQFC = React.useCallback(
    async (cellId: string) => {
      try {
        const res = await fetch(
          `${BASE_API_URL}/qfc_entangled` +
            `?cell_id=${encodeURIComponent(cellId)}` +
            `&container_id=${encodeURIComponent(containerId || "")}`,
          { headers: { Authorization: `Bearer ${AUTH_TOKEN}` } }
        );
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const data = await res.json();
        return data.updates || [];
      } catch (err) {
        console.error(`❌ Failed to fetch entangled QFC for ${cellId}:`, err);
        return [];
      }
    },
    [containerId]
  );
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

// Index cells by x:y:z:t for O(1) lookup while rendering
const cellIndex = React.useMemo(() => {
  const m = new Map<string, GlyphCell>();
  for (const c of cells) {
    const [x = 0, y = 0, z = 0, t = 0] = (c.position || []) as number[];
    m.set(`${x}:${y}:${z}:${t}`, c);
  }
  return m;
}, [cells]);

// Determine extents (exclusive upper-bounds)
const dims = React.useMemo(() => {
  let maxX = 0, maxY = 0, maxZ = 0, maxT = 0;
  for (const c of cells) {
    const [x = 0, y = 0, z = 0, t = 0] = (c.position || []) as number[];
    if (x + 1 > maxX) maxX = x + 1;
    if (y + 1 > maxY) maxY = y + 1;
    if (z + 1 > maxZ) maxZ = z + 1;
    if (t + 1 > maxT) maxT = t + 1;
  }
  // sensible minimums
  return {
    X: Math.max(1, maxX),
    Y: Math.max(1, maxY),
    Z: Math.max(1, maxZ),
    T: Math.max(1, maxT),
  };
}, [cells]);

// Helper to render one slot at (x,y,z,t)
const renderSlot = (x: number, y: number, z: number, t: number) => {
  const cell = cellIndex.get(`${x}:${y}:${z}:${t}`);

  return (
    <div
      key={`slot-${t}-${z}-${y}-${x}`}
      className={[
        "relative rounded border",
        cell ? "border-zinc-700 bg-neutral-900" : "border-dashed border-zinc-800 bg-neutral-950/60",
        "min-h-[96px] p-2",
      ].join(" ")}

      // DnD: allow drop into empty slots to create a cell
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

      // LiveHUD: follow hover (debounced) and clear on leave when not pinned
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

      // Click → immediate trace + pin
      onClick={() => {
        if (!cell?.id) return;
        setSelectedCellId(cell.id);
        updateLiveHUD(cell.id);  // non-debounced
        setPinTrace(true);
      }}

      // existing drag start for copying cells out
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
                        ? { borderColor: `hsl(${Math.round(120 * cell.harmony)} 70% 50%)`, color: `hsl(${Math.round(120 * cell.harmony)} 70% 55%)` }
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
                        ? { borderColor: `hsl(${Math.round(120 * cell.novelty)} 70% 50%)`, color: `hsl(${Math.round(120 * cell.novelty)} 70% 55%)` }
                        : {}
                    }
                  >
                    N:{typeof cell.novelty === "number" ? cell.novelty.toFixed(2) : "—"}
                  </span>
                  <span
                    className="px-1 py-[1px] rounded text-[10px] border"
                    title={`Entropy: ${typeof cell.entropy === "number" ? cell.entropy.toFixed(2) : "—"}`}
                    style={
                      typeof cell.entropy === "number"
                        ? { borderColor: `hsl(${Math.round(120 * cell.entropy)} 70% 50%)`, color: `hsl(${Math.round(120 * cell.entropy)} 70% 55%)` }
                        : {}
                    }
                  >
                    E:{typeof cell.entropy === "number" ? cell.entropy.toFixed(2) : "—"}
                  </span>
                </div>

                {/* 📜 Scrolls/Memory popover */}
                {(
                  ((cell as any)?.scrolls && (Array.isArray((cell as any).scrolls) ? (cell as any).scrolls.length > 0 : true)) ||
                  ((cell as any)?.memory && (Array.isArray((cell as any).memory) ? (cell as any).memory.length > 0 : true))
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
                                  <li key={i} className="text-zinc-200 break-words">{String(s)}</li>
                                ))}
                              </ul>
                            ) : (
                              <div className="text-zinc-200 break-words">{String((cell as any).scrolls)}</div>
                            )}
                          </div>
                        )}
                        {(cell as any)?.memory && (
                          <div className="pt-1">
                            <div className="font-semibold text-zinc-300 mb-1">Memory</div>
                            {Array.isArray((cell as any).memory) ? (
                              <ul className="list-disc pl-4">
                                {(cell as any).memory.map((m: any, i: number) => (
                                  <li key={i} className="text-zinc-200 break-words">{String(m)}</li>
                                ))}
                              </ul>
                            ) : (
                              <div className="text-zinc-200 break-words">{String((cell as any).memory)}</div>
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
  );
};

// Render T → Z → Y rows; each row has X slots
{Array.from({ length: dims.T }).map((_, t) => (
  <div key={`t-layer-${t}`} className="mb-6">
    <div className="text-xs text-zinc-400 mb-2">t = {t}</div>
    {Array.from({ length: dims.Z }).map((__, z) => (
      <div key={`t-${t}-z-${z}`} className="mb-4">
        <div className="text-[10px] text-zinc-500 mb-1">z = {z}</div>
        {Array.from({ length: dims.Y }).map((___, y) => (
          <div key={`t-${t}-z-${z}-y-${y}`} className="grid gap-2" style={{ gridTemplateColumns: `repeat(${dims.X}, minmax(0, 1fr))` }}>
            {Array.from({ length: dims.X }).map((____, x) => renderSlot(x, y, z, t))}
          </div>
        ))}
      </div>
    ))}
  </div>
))}

// ──────────────────────────────
// (Render section begins below)
// ──────────────────────────────
return (
  <div className="p-6 relative">
    {/* ───────────── HEADER ───────────── */}
    <div className="flex justify-between items-center mb-4">
      <h2 className="text-2xl font-bold">🧠 AtomSheet Viewer (.atom)</h2>
      <div className="flex gap-2">
        <button
          onClick={fetchSheet}
          className="px-3 py-1 rounded border border-zinc-700 hover:bg-white/10 text-sm"
        >
          🔁 Reload
        </button>
        <button
          onClick={() => setRawMode((v) => !v)}
          className="px-3 py-1 rounded border border-zinc-700 hover:bg-white/10 text-sm"
        >
          {rawMode ? "🔣 Show CodexLang" : "🧬 Show Raw"}
        </button>
        <button
          onClick={() => setTraceMode((p) => (p === "forward" ? "reverse" : "forward"))}
          className="px-3 py-1 rounded border border-zinc-700 hover:bg-white/10 text-sm"
        >
          🌌 {traceMode === "forward" ? "→ Forward" : "← Reverse"}
        </button>
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

    {/* ───────────── GRID (dims + renderSlot) ───────────── */}
    {Array.from({ length: dims.T }).map((_, t) => (
      <div key={`time-${t}`} className="mb-6">
        <h3 className="text-lg font-semibold">Time Layer {t}</h3>

        {Array.from({ length: dims.Z }).map((__, z) => (
          <div key={`z-${z}`} className="mb-3">
            <h4 className="text-sm font-medium text-zinc-300 mb-1">Z Level {z}</h4>

            {Array.from({ length: dims.Y }).map((___, y) => (
              <div
                key={`row-${t}-${z}-${y}`}
                className="grid gap-2"
                style={{ gridTemplateColumns: `repeat(${dims.X}, minmax(100px, 1fr))` }}
              >
                {Array.from({ length: dims.X }).map((____, x) => renderSlot(x, y, z, t))}
              </div>
            ))}
          </div>
        ))}
      </div>
    ))}

{/* ───────────── HOVER PANEL ───────────── */}
{hoveredCell && (
  <div className="absolute top-0 right-0 p-4 z-50">
    {/* cast to any to satisfy unknown prop type of CellOverlayPanel */}
    <CellOverlayPanel {...({ cell: hoveredCell } as any)} />
  </div>
)}
</div>
);
}