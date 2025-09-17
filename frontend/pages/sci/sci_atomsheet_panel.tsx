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
  validated?: boolean;
  result?: string;
  codexlang_render?: string;
  mutationNotes?: string[];
}

// 🌐 Config
const DEV_MODE = process.env.NODE_ENV !== "production";
const BASE_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const AUTH_TOKEN = "valid_token";

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

// Utility to render CodexLang to human-readable string (placeholder)
const tryInterpret = (logic: string) => `⟦${logic}⟧`;

export default function SCIAtomSheetPanel() {
  const router = useRouter();

  const [cells, setCells] = useState<GlyphCell[]>([]);
  const [sheetFile, setSheetFile] = useState("example_sheet.sqs.json");
  const [rawMode, setRawMode] = useState(false);
  const [hoveredCell, setHoveredCell] = useState<GlyphCell | null>(null);
  const [lightconeTrace, setLightconeTrace] = useState<any[]>([]);
  const [traceMode, setTraceMode] = useState<"forward" | "reverse">("forward");

  // ──────────────────────────────
  // Update sheet file from query param
  // ──────────────────────────────
  useEffect(() => {
    const fileParam = router.query.file;
    if (typeof fileParam === "string") {
      setSheetFile(fileParam);
    }
  }, [router.query.file]);

  // ──────────────────────────────
  // Fetch AtomSheet (live or dev fallback)
  // ──────────────────────────────
  const fetchSheet = async () => {
    if (!DEV_MODE) {
      try {
        const res = await fetch(`${BASE_API_URL}/atomsheet?file=${sheetFile}`, {
          headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
        });
        const data = await res.json();
        setCells(
          (data.cells || []).map((cell: GlyphCell) => ({
            ...cell,
            codexlang_render: tryInterpret(cell.logic),
          }))
        );
      } catch (err) {
        console.error("❌ Failed to fetch AtomSheet:", err);
        setCells([]);
      }
    } else {
      // Dev fallback
      setCells(
        exampleSheet.cells.map((cell) => ({
          ...cell,
          codexlang_render: tryInterpret(cell.logic),
        }))
      );
    }
  };

  useEffect(() => {
    fetchSheet();
  }, [sheetFile]);

  // ──────────────────────────────
  // Fetch LightCone QFC / HUD projection
  // ──────────────────────────────
  const fetchLightConeQFC = async (entryId: string, direction: "forward" | "reverse") => {
    try {
      const res = await fetch(
        `${BASE_API_URL}/lightcone?file=${sheetFile}&entry_id=${entryId}&direction=${direction}`,
        { headers: { Authorization: `Bearer ${AUTH_TOKEN}` } }
      );
      const data = await res.json();
      return data.trace || [];
    } catch (err) {
      console.error(`❌ Failed to fetch LightCone QFC nodes for ${entryId}:`, err);
      return [];
    }
  };

  const updateLiveHUD = async (cellId: string) => {
    try {
      const lightconeNodes = await fetchLightConeQFC(cellId, traceMode);
      // Optionally fetch entanglement / prediction fork updates
      let entangledUpdates: any[] = [];
      try {
        const res = await fetch(
          `${BASE_API_URL}/qfc_entanglement?cell_id=${cellId}&file=${sheetFile}`,
          { headers: { Authorization: `Bearer ${AUTH_TOKEN}` } }
        );
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
      const res = await fetch(`${BASE_API_URL}/qfc_entangled?cell_id=${cellId}`, {
        headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
      });
      const data = await res.json();
      return data.updates || [];
    } catch (err) {
      console.error(`❌ Failed to fetch entangled QFC for ${cellId}:`, err);
      return [];
    }
  };

  // ──────────────────────────────
  // Build 4D grid from loaded cells
  // ──────────────────────────────
  const maxX = Math.max(...cells.map((c) => c.position?.[0] ?? 0), 0);
  const maxY = Math.max(...cells.map((c) => c.position?.[1] ?? 0), 0);
  const maxZ = Math.max(...cells.map((c) => c.position?.[2] ?? 0), 0);
  const maxT = Math.max(...cells.map((c) => c.position?.[3] ?? 0), 0);

  const grid: (GlyphCell | null)[][][][] = Array.from({ length: maxT + 1 }, () =>
    Array.from({ length: maxZ + 1 }, () =>
      Array.from({ length: maxY + 1 }, () =>
        Array.from({ length: maxX + 1 }, () => null)
      )
    )
  );

  cells.forEach((cell) => {
    const [x, y, z, t] = cell.position;
    if (grid?.[t]?.[z]?.[y]) grid[t][z][y][x] = cell;
  });

  if (cells.length === 0)
    return <div className="p-6 text-red-500">Error loading sheet</div>;

  // ──────────────────────────────
  // (Render section begins below)
  // ──────────────────────────────

return (
  <div className="p-6 relative">
    {/* ───────────── HEADER ───────────── */}
    <div className="flex justify-between items-center mb-4">
      <h2 className="text-2xl font-bold">🧠 Symbolic AtomSheet Viewer</h2>
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
      <LiveQpuCpuPanel containerId={sheetFile} />
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
                          if (cell?.id) updateLiveHUD(cell.id);
                        }}
                        onMouseLeave={() => {
                          setHoveredCell(null);
                          setLightconeTrace([]);
                        }}
                        onDragStart={(e: React.DragEvent<HTMLDivElement>) =>
                          cell && e.dataTransfer.setData("cell", JSON.stringify(cell))
                        }
                      >
                        <CardContent className="w-full h-full">
                          {cell ? (
                            <div className="flex flex-col justify-between h-full text-xs">
                              <div className="font-mono text-sm break-words">
                                {rawMode ? cell.logic : cell.codexlang_render}
                              </div>
                              <div className="flex justify-between text-[10px] pt-1">
                                <EmotionSQIPanel emotion={cell.emotion} sqi={cell.sqi_score} />
                                {cell.prediction && (
                                  <span className="text-yellow-300">🔮 {cell.prediction}</span>
                                )}
                              </div>
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