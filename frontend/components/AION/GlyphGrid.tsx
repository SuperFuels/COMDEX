// frontend/components/GlyphGrid.tsx
import React, { useState, useEffect, useRef } from "react";
import useWebSocket from "@/hooks/useWebSocket";
import GlyphInspector from "./GlyphInspector";
import {
  TimerReset,
  Filter,
  RefreshCw,
  Save,
  XCircle,
  Download,
} from "lucide-react";

export interface GlyphGridProps {
  cubes: { [coord: string]: { glyph?: string; [key: string]: any } };
  tick: number;
  onGlyphClick?: (coord: string, data: any) => void;
  viewMode?: "top-down" | "3d-symbolic" | "glyph-logic";
}

const GlyphGrid: React.FC<GlyphGridProps> = ({
  cubes,
  tick,
  onGlyphClick,
  viewMode = "top-down",
}) => {
  const [zLevel, setZLevel] = useState(0);
  const [glyphData, setGlyphData] = useState(cubes);
  const [selectedCoord, setSelectedCoord] = useState<string | null>(null);
  const [selectedData, setSelectedData] = useState<any>(null);
  const [zoom, setZoom] = useState(1);
  const [previousGlyphs, setPreviousGlyphs] = useState<{ [coord: string]: string }>({});
  const [filter, setFilter] = useState({ glyph: "", minAge: 0, maxAge: 600 });
  const [hudStats, setHudStats] = useState({ total: 0, active: 0, decaying: 0, mutated: 0, denied: 0 });
  const [snapshots, setSnapshots] = useState<{ [name: string]: any }>({});
  const [selectedSnapshot, setSelectedSnapshot] = useState<string | null>(null);
  const [recentTriggers, setRecentTriggers] = useState<{ [coord: string]: { reason: string } }>({});
  const [zOptions, setZOptions] = useState<number[]>([0]);

  const gridRef = useRef<HTMLDivElement>(null);

  const { connected } = useWebSocket(
    "wss://comdex-api-swift-area-459514-d1-uc.a.run.app/ws/containers",
    (incoming) => {
      if (incoming?.cubes) {
        const allZs = new Set<number>();
        Object.keys(incoming.cubes).forEach((coord) => {
          const [, , z] = coord.split(",").map(Number);
          allZs.add(z);
        });
        setZOptions(Array.from(allZs).sort((a, b) => a - b));

        setPreviousGlyphs((prev) => {
          const updates: { [coord: string]: string } = {};
          for (const coord in incoming.cubes) {
            const newGlyph = incoming.cubes[coord]?.glyph;
            if (newGlyph !== prev[coord]) {
              updates[coord] = newGlyph;
            }
          }
          return { ...prev, ...updates };
        });
        setGlyphData(incoming.cubes);
      }
    }
  );

  useEffect(() => {
    const loadRecentTriggers = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/glyph-triggers/recent`);
        const json = await res.json();
        if (Array.isArray(json?.triggers)) {
          const mapped: { [coord: string]: { reason: string } } = {};
          json.triggers.forEach((t: any) => {
            if (t.coord) mapped[t.coord] = { reason: t.reason || "event" };
          });
          setRecentTriggers(mapped);
        }
      } catch (err) {
        console.warn("Trigger log load failed:", err);
      }
    };
    loadRecentTriggers();
    const interval = setInterval(loadRecentTriggers, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadSnapshot = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/aion/glyph-runtime/snapshot`);
      const json = await res.json();
      if (json?.cubes) {
        setGlyphData(json.cubes);
        setSnapshots((prev) => ({ ...prev, latest: json.cubes }));
        setSelectedSnapshot("latest");
      }
    } catch (err) {
      console.warn("Snapshot load failed:", err);
    }
  };

  const saveSnapshot = () => {
    const name = prompt("Enter a name for this snapshot:") || `tick-${tick}`;
    setSnapshots((prev) => ({ ...prev, [name]: glyphData }));
    alert(`Snapshot '${name}' saved.`);
  };

  const restoreSnapshot = (name: string) => {
    const snap = snapshots[name];
    if (snap) {
      setGlyphData(snap);
      setSelectedSnapshot(name);
    }
  };

  const exportSnapshot = () => {
    const dataStr = JSON.stringify(glyphData, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `glyph_runtime_snapshot_${tick}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filtered = Object.entries(glyphData).filter(([coord, data]) => {
    const [, , z] = coord.split(",").map(Number);
    const ageSec = data?.age_ms ? Math.floor(data.age_ms / 1000) : 0;
    return (
      z === zLevel &&
      (filter.glyph === "" || (data.glyph || "").includes(filter.glyph)) &&
      ageSec >= filter.minAge &&
      ageSec <= filter.maxAge
    );
  });

  const maxX = Math.max(...filtered.map(([k]) => parseInt(k.split(",")[0], 10)), 0);
  const maxY = Math.max(...filtered.map(([k]) => parseInt(k.split(",")[1], 10)), 0);

  const getGlyphColor = (
    glyph: string,
    age_ms: number | undefined,
    changed: boolean,
    denied?: boolean
  ) => {
    if (!glyph) return "bg-white";
    if (denied) return "bg-red-300 border-red-600 border-2";
    if (glyph === "⚙") return "bg-yellow-200";
    if (glyph === "🧠") return "bg-purple-200";
    if (glyph === "🔒") return "bg-red-200";
    if (glyph === "🌐") return "bg-blue-200";
    if (changed) return "bg-green-200 animate-pulse";
    if (age_ms && age_ms > 60000) return "bg-gray-300 opacity-70";
    return "bg-gray-100";
  };

  const renderCell = (x: number, y: number) => {
    const key = `${x},${y},${zLevel}`;
    const data = glyphData[key] || {};
    const glyph = data.glyph || "";
    const ageMs = data.age_ms || 0;
    const ageSec = Math.floor(ageMs / 1000);
    const changed = previousGlyphs[key] !== undefined && previousGlyphs[key] !== glyph;
    const denied = data?.denied === true;
    const triggered = recentTriggers[key];
    const color = getGlyphColor(glyph, ageMs, changed, denied);
    const percent = Math.min(ageSec / filter.maxAge, 1) * 100;

    const tooltip = data?.type || data?.tag || data?.value || data?.action
      ? `⟦ ${data?.type || "?"} | ${data?.tag || "?"} : ${data?.value || "?"} → ${data?.action || "?"} ⟧`
      : `(${x},${y},${zLevel}) | Glyph: ${glyph} | Age: ${ageSec}s`;

    return (
      <div
        key={key}
        id={`cell-${key}`}
        onClick={() => {
          onGlyphClick?.(key, data);
          setSelectedCoord(key);
          setSelectedData(data);
        }}
        className={`w-6 h-6 border text-xs text-center cursor-pointer flex flex-col items-center justify-center hover:scale-105 transition transform relative ${color}`}
        title={tooltip}
      >
        {triggered && (
          <div className="absolute inset-0 rounded-sm border-2 border-blue-500 animate-ping pointer-events-none z-10" />
        )}
        <div className="z-20">
          {denied ? <XCircle className="w-3 h-3 text-red-700" /> :
            viewMode === "glyph-logic"
              ? glyph
              : viewMode === "3d-symbolic"
              ? `⟦${glyph}⟧`
              : glyph}
        </div>
        <div className="w-full h-1 mt-[1px] bg-gray-200 z-20">
          <div className="h-1 bg-green-500" style={{ width: `${percent}%` }} />
        </div>
        {triggered && (
          <div className="absolute -top-5 left-1/2 transform -translate-x-1/2 text-[10px] px-1 py-[1px] bg-blue-100 text-blue-800 border border-blue-300 rounded shadow z-30">
            ↪ triggered {triggered.reason}
          </div>
        )}
      </div>
    );
  };

  const handleMinimapClick = (x: number, y: number) => {
    const cell = document.getElementById(`cell-${x},${y},${zLevel}`);
    if (cell) {
      cell.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
      cell.classList.add("ring-4", "ring-blue-400");
      setTimeout(() => cell.classList.remove("ring-4", "ring-blue-400"), 800);
    }
  };

  useEffect(() => {
    const stats = { total: 0, active: 0, decaying: 0, mutated: 0, denied: 0 };
    for (const [coord, data] of Object.entries(glyphData)) {
      if (!coord.endsWith(`,${zLevel}`)) continue;
      const age = data.age_ms || 0;
      stats.total++;
      if (age < 30000) stats.active++;
      if (age > 60000) stats.decaying++;
      if (data?.denied) stats.denied++;
      const glyph = data.glyph || "";
      if (previousGlyphs[coord] && previousGlyphs[coord] !== glyph) stats.mutated++;
    }
    setHudStats(stats);
  }, [glyphData, zLevel, previousGlyphs]);

  return (
    <div className="p-2 relative">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <label className="text-sm">Z-Level:</label>
          <select
            className="border p-1 rounded text-sm"
            value={zLevel}
            onChange={(e) => setZLevel(parseInt(e.target.value))}
          >
            {zOptions.map((z) => (
              <option key={z} value={z}>{z}</option>
            ))}
          </select>
          <label className="ml-2 text-sm">Zoom:</label>
          <select
            className="border p-1 rounded text-sm"
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
          >
            <option value={0.5}>50%</option>
            <option value={1}>100%</option>
            <option value={2}>200%</option>
          </select>
          <button onClick={loadSnapshot} className="ml-2 px-2 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded border">
            <TimerReset className="inline-block w-4 h-4 mr-1" /> Load Snapshot
          </button>
          <button onClick={saveSnapshot} className="ml-1 px-2 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded border">
            <Save className="inline-block w-4 h-4 mr-1" /> Save Snapshot
          </button>
          <button onClick={exportSnapshot} className="ml-1 px-2 py-1 bg-gray-100 hover:bg-gray-200 text-sm rounded border">
            <Download className="inline-block w-4 h-4 mr-1" /> Export JSON
          </button>
          <select
            className="ml-2 border p-1 rounded text-sm"
            value={selectedSnapshot || ""}
            onChange={(e) => restoreSnapshot(e.target.value)}
          >
            <option value="">⏪ Select Snapshot</option>
            {Object.keys(snapshots).map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
          <span className="text-xs text-gray-500 pl-2">⏱️ Tick: <span className="font-mono">{tick}</span></span>
        </div>
        <div className="text-xs text-gray-500">{connected ? "🟢 Live (WebSocket)" : "🟡 Polling fallback"}</div>
      </div>

      {/* Filter Panel */}
      <div className="flex items-center mb-2 space-x-2 text-sm">
        <Filter className="w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Glyph filter"
          className="border px-2 py-1 rounded w-28"
          value={filter.glyph}
          onChange={(e) => setFilter({ ...filter, glyph: e.target.value })}
        />
        <input
          type="number"
          placeholder="Min age"
          className="border px-2 py-1 rounded w-20"
          value={filter.minAge}
          onChange={(e) => setFilter({ ...filter, minAge: Number(e.target.value) })}
        />
        <input
          type="number"
          placeholder="Max age"
          className="border px-2 py-1 rounded w-20"
          value={filter.maxAge}
          onChange={(e) => setFilter({ ...filter, maxAge: Number(e.target.value) })}
        />
      </div>

      <div className="text-xs text-gray-700 mb-2">
        Total: {hudStats.total} | Active: {hudStats.active} | Decaying: {hudStats.decaying} | Mutated: {hudStats.mutated} | Denied: {hudStats.denied}
      </div>

      <div
        ref={gridRef}
        className="grid gap-1 overflow-auto border p-1"
        style={{
          gridTemplateColumns: `repeat(${maxX + 1}, 1fr)`,
          transform: `scale(${zoom})`,
          transformOrigin: "top left",
        }}
      >
        {Array.from({ length: (maxX + 1) * (maxY + 1) }).map((_, i) =>
          renderCell(i % (maxX + 1), Math.floor(i / (maxX + 1)))
        )}
      </div>

      <div className="absolute bottom-2 right-2 bg-white border p-1 shadow-md z-10">
        <div className="grid gap-[1px]" style={{ gridTemplateColumns: `repeat(${maxX + 1}, 1fr)` }}>
          {Array.from({ length: (maxX + 1) * (maxY + 1) }).map((_, i) => {
            const x = i % (maxX + 1);
            const y = Math.floor(i / (maxX + 1));
            const key = `${x},${y},${zLevel}`;
            const glyph = glyphData[key]?.glyph || "";
            const color = getGlyphColor(glyph, glyphData[key]?.age_ms, false);
            return (
              <div
                key={key}
                onClick={() => handleMinimapClick(x, y)}
                className={`w-2 h-2 cursor-pointer hover:opacity-80 ${color}`}
                title={key}
              />
            );
          })}
        </div>
      </div>

      {selectedCoord && selectedData && (
        <GlyphInspector
          coord={selectedCoord}
          data={selectedData}
          onClose={() => setSelectedCoord(null)}
        />
      )}
    </div>
  );
};

export default GlyphGrid;