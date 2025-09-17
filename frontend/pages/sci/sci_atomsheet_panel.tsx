// File: frontend/pages/sci/sci_atomsheet_panel.tsx
// 🎛 SCI AtomSheet Panel – B5.1 + C8: Modular Panel Plugins + Dev Test Fallbacks + Hover Overlay

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { CardContent } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";

// 🔌 Modular UI Plugins
import EmotionSQIPanel from "@/components/SQS/EmotionSQIPanel";
import { CellOverlayPanel } from "@/components/SQS/CellOverlayPanel";
import { SheetTraceViewer } from "@/components/SQS/SheetTraceViewer";

// 🧠 Type for cells
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

export default function SCIAtomSheetPanel() {
  const [cells, setCells] = useState<GlyphCell[]>([]);
  const [rawMode, setRawMode] = useState(false);
  const [sheetFile, setSheetFile] = useState("example_sheet.sqs.json");
  const [hoveredCell, setHoveredCell] = useState<GlyphCell | null>(null);
  const [lightconeTrace, setLightconeTrace] = useState<any[]>([]);
  const [traceMode, setTraceMode] = useState<"forward" | "reverse">("forward");

  const router = useRouter();

  export default function SCIAtomSheetPanel() {
  const [cells, setCells] = useState<GlyphCell[]>([]);
  const [rawMode, setRawMode] = useState(false);
  const [sheetFile, setSheetFile] = useState("example_sheet.sqs.json");
  const [hoveredCell, setHoveredCell] = useState<GlyphCell | null>(null);
  const [lightconeTrace, setLightconeTrace] = useState<any[]>([]);
  const [traceMode, setTraceMode] = useState<"forward" | "reverse">("forward");
  const router = useRouter();

  // 🔭 Fetch LightCone trace for QFC projection
  async function fetchLightConeQFC(entryId: string, direction: "forward" | "reverse") {
    try {
      const res = await fetch(`${BASE_API_URL}/lightcone_qfc?file=${sheetFile}&entry_id=${entryId}&direction=${direction}`, {
        headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
      });
      const data = await res.json();
      console.log("🌌 LightCone QFC nodes:", data.nodes);
      return data.nodes || [];
    } catch (err) {
      console.error("❌ Failed to fetch LightCone QFC nodes:", err);
      return [];
    }
  }

  // 🌐 Unified HUD updater for a single cell
  async function updateLiveHUD(cellId: string) {
    try {
      // 1️⃣ Fetch LightCone QFC trace
      const lightconeNodes = await fetchLightConeQFC(cellId, traceMode);

      // 2️⃣ Fetch entangled / prediction fork updates
      let entangledUpdates: any[] = [];
      try {
        const res = await fetch(`${BASE_API_URL}/qfc_entangled?cell_id=${cellId}&file=${sheetFile}`, {
          headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
        });
        const data = await res.json();
        entangledUpdates = data.updates || [];
      } catch (err) {
        console.warn(`⚠️ Failed to fetch entangled/fork updates for ${cellId}:`, err);
      }

      // 3️⃣ Merge into single HUD state
      setLightconeTrace([...lightconeNodes, ...entangledUpdates]);
      console.log(`📡 Live HUD updated for ${cellId}`, { lightconeNodes, entangledUpdates });
    } catch (err) {
      console.error(`❌ Failed to update live HUD for ${cellId}:`, err);
      setLightconeTrace([]);
    }
  }

  // 🔭 Fetch live entanglement & prediction forks for QFC HUD
  async function fetchEntangledQFC(cellId: string) {
    try {
      const res = await fetch(`${BASE_API_URL}/qfc_entanglement?cell_id=${cellId}`, {
        headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
      });
      const data = await res.json();
      console.log("🌈 QFC Entangled updates:", data);
      return data.updates || [];
    } catch (err) {
      console.error("❌ Failed to fetch QFC entanglement:", err);
      return [];
    }
  }

  useEffect(() => {
    const fileParam = router.query.file;
    if (typeof fileParam === "string") {
      setSheetFile(fileParam);
    }
  }, [router.query.file]);

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
        console.error("Failed to fetch AtomSheet:", err);
        setCells([]);
      }
    } else {
      setCells(
        exampleSheet.cells.map((cell) => ({
          ...cell,
          codexlang_render: tryInterpret(cell.logic),
        }))
      );
    }
  };

  // 🔭 Fetch LightCone trace for HUD projection
  async function fetchLightConeTrace(entryId: string, direction: "forward" | "reverse") {
    try {
      const res = await fetch(`${BASE_API_URL}/lightcone?entry_id=${entryId}&direction=${direction}`, {
        headers: { Authorization: `Bearer ${AUTH_TOKEN}` },
      });
      const data = await res.json();
      console.log("🌌 LightCone Trace:", data);
      setLightconeTrace(data || []);
    } catch (err) {
      console.error("❌ Failed to fetch LightCone trace:", err);
      setLightconeTrace([]);
    }
  }

  useEffect(() => {
    fetchSheet();
  }, [sheetFile]);

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

  return (
    <div className="p-6 relative">
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

      {lightconeTrace.length > 0 && (
        <div className="mb-4">
          <h4 className="text-md font-semibold">🌌 LightCone Trace</h4>
          <SheetTraceViewer trace={lightconeTrace} />
        </div>
      )}

      {grid.map((zLayers, t) => (
        <div key={`time-${t}`} className="mb-4">
          <h3 className="text-lg font-semibold">Time Layer {t}</h3>
          {zLayers.map((rows, z) => (
            <div key={`z-${z}`} className="mb-2">
              <h4 className="text-md font-medium">Z Level {z}</h4>
              <div
                className="grid gap-2"
                style={{
                  gridTemplateColumns: `repeat(${maxX + 1}, minmax(100px, 1fr))`,
                }}
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

                          if (cell?.id) {
                            // 🌐 Unified HUD update (LightCone + entangled/fork updates)
                            updateLiveHUD(cell.id);
                          }
                        }}
                        onMouseLeave={() => {
                          setHoveredCell(null);
                          setLightconeTrace([]); // Clear HUD when leaving cell
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
                                <EmotionSQIPanel
                                  emotion={cell.emotion}
                                  sqi={cell.sqi_score}
                                />
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

      {hoveredCell && (
        <div className="absolute top-0 right-0 p-4 z-50">
          <CellOverlayPanel cell={hoveredCell} />
        </div>
      )}
    </div>
  );
}

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