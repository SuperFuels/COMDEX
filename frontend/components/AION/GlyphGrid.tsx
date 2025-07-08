import React, { useState, useEffect, useRef } from "react";
import useWebSocket from "@/hooks/useWebSocket";
import GlyphInspector from "./GlyphInspector";

export interface GlyphGridProps {
  cubes: { [coord: string]: { glyph?: string; [key: string]: any } };
  onGlyphClick?: (coord: string, data: any) => void;
}

const GlyphGrid: React.FC<GlyphGridProps> = ({ cubes, onGlyphClick }) => {
  const [zLevel, setZLevel] = useState(0);
  const [glyphData, setGlyphData] = useState(cubes);
  const [selectedCoord, setSelectedCoord] = useState<string | null>(null);
  const [selectedData, setSelectedData] = useState<any>(null);
  const [zoom, setZoom] = useState(1);

  const gridRef = useRef<HTMLDivElement>(null);

  const { connected } = useWebSocket(
    "wss://comdex-api-swift-area-459514-d1-uc.a.run.app/ws/containers",
    (incoming) => {
      if (incoming?.cubes) {
        setGlyphData(incoming.cubes);
      }
    }
  );

  useEffect(() => {
    if (!connected) {
      const interval = setInterval(async () => {
        try {
          const res = await fetch("/api/aion/containers");
          const data = await res.json();
          if (data?.cubes) setGlyphData(data.cubes);
        } catch (err) {
          console.warn("Polling failed:", err);
        }
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [connected]);

  const filtered = Object.entries(glyphData).filter(([coord]) => {
    const [, , z] = coord.split(",").map(Number);
    return z === zLevel;
  });

  const maxX = Math.max(...filtered.map(([k]) => parseInt(k.split(",")[0], 10)), 0);
  const maxY = Math.max(...filtered.map(([k]) => parseInt(k.split(",")[1], 10)), 0);

  const getGlyphColor = (glyph: string) => {
    if (!glyph) return "bg-white";
    if (glyph === "⚙") return "bg-yellow-200";
    if (glyph === "🧠") return "bg-purple-200";
    if (glyph === "🔒") return "bg-red-200";
    if (glyph === "🌐") return "bg-blue-200";
    return "bg-gray-100";
  };

  const renderCell = (x: number, y: number) => {
    const key = `${x},${y},${zLevel}`;
    const data = glyphData[key] || {};
    const glyph = data.glyph || "";
    const color = getGlyphColor(glyph);

    return (
      <div
        key={key}
        id={`cell-${key}`}
        onClick={() => {
          onGlyphClick?.(key, data);
          setSelectedCoord(key);
          setSelectedData(data);
        }}
        className={`w-6 h-6 border text-xs text-center cursor-pointer flex items-center justify-center hover:scale-105 transition transform ${color}`}
        title={`(${x},${y},${zLevel})`}
      >
        {glyph}
      </div>
    );
  };

  const handleMinimapClick = (x: number, y: number) => {
    const cell = document.getElementById(`cell-${x},${y},${zLevel}`);
    cell?.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
  };

  return (
    <div className="p-2 relative">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-3">
          <div>
            <label className="mr-1 text-sm">Z-Level:</label>
            <select
              className="border p-1 rounded text-sm"
              value={zLevel}
              onChange={(e) => setZLevel(parseInt(e.target.value))}
            >
              {[...Array(5)].map((_, i) => (
                <option key={i} value={i}>
                  {i}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mr-1 text-sm">Zoom:</label>
            <select
              className="border p-1 rounded text-sm"
              value={zoom}
              onChange={(e) => setZoom(Number(e.target.value))}
            >
              <option value={0.5}>50%</option>
              <option value={1}>100%</option>
              <option value={2}>200%</option>
            </select>
          </div>
        </div>
        <div className="text-xs text-gray-500">
          {connected ? "🟢 Live (WebSocket)" : "🟡 Polling fallback"}
        </div>
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

      {/* Minimap */}
      <div className="absolute bottom-2 right-2 bg-white border p-1 shadow-md">
        <div className="grid gap-[1px]" style={{ gridTemplateColumns: `repeat(${maxX + 1}, 1fr)` }}>
          {Array.from({ length: (maxX + 1) * (maxY + 1) }).map((_, i) => {
            const x = i % (maxX + 1);
            const y = Math.floor(i / (maxX + 1));
            const key = `${x},${y},${zLevel}`;
            const glyph = glyphData[key]?.glyph || "";
            const color = getGlyphColor(glyph);
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