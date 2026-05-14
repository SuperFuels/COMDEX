import React, { useState } from "react";
import QuantumFieldCanvas from "@/components/Hologram/quantum_field_canvas";

interface Props {
  realData: { nodes: any[]; links: any[] };
  predictedData: { nodes: any[]; links: any[] };
  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (id: string) => void;
}

const SplitScreenView: React.FC<Props> = ({
  realData,
  predictedData,
  tickFilter,
  showCollapsed,
  onTeleport,
}) => {
  const [viewMode, setViewMode] = useState<"split" | "overlay" | "real">("split");

  return (
    <div className="relative w-full h-full">
      {/* 🌗 View Mode Controls */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-50 space-x-2">
        <button
          className="bg-slate-800 text-white px-3 py-1 text-xs rounded hover:bg-slate-700"
          onClick={() => setViewMode("split")}
        >
          🌓 Split View
        </button>
        <button
          className="bg-slate-800 text-white px-3 py-1 text-xs rounded hover:bg-slate-700"
          onClick={() => setViewMode("overlay")}
        >
          🔮 Overlay
        </button>
        <button
          className="bg-slate-800 text-white px-3 py-1 text-xs rounded hover:bg-slate-700"
          onClick={() => setViewMode("real")}
        >
          🌐 Reality Only
        </button>
      </div>

      {/* 🖼️ Split Layout */}
      {viewMode === "split" && (
        <div className="flex h-full">
          <div className="w-1/2 border-r border-white/20">
            <QuantumFieldCanvas
              nodes={realData.nodes}
              links={realData.links}
              tickFilter={tickFilter}
              showCollapsed={showCollapsed}
              onTeleport={onTeleport}
            />
          </div>
          <div className="w-1/2">
            <QuantumFieldCanvas
              nodes={predictedData.nodes}
              links={predictedData.links}
              tickFilter={tickFilter}
              showCollapsed={showCollapsed}
              onTeleport={onTeleport}
              predictedMode
            />
          </div>
        </div>
      )}

      {/* 🔮 Overlay Layout */}
      {viewMode === "overlay" && (
        <QuantumFieldCanvas
          nodes={realData.nodes}
          links={realData.links}
          tickFilter={tickFilter}
          showCollapsed={showCollapsed}
          onTeleport={onTeleport}
          predictedOverlay={predictedData}
        />
      )}

      {/* 🌐 Reality Only */}
      {viewMode === "real" && (
        <QuantumFieldCanvas
          nodes={realData.nodes}
          links={realData.links}
          tickFilter={tickFilter}
          showCollapsed={showCollapsed}
          onTeleport={onTeleport}
        />
      )}
    </div>
  );
};

export default SplitScreenView;