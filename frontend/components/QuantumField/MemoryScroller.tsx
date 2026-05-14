import React, { useState } from "react";
import { pull_to_field } from "@/utils/pull_to_field";
import useWebSocket from "@/hooks/useWebSocket";

interface MemoryScrollerProps {
  memoryItems: any[];
  onPreviewQWave?: (id: string) => void;
}

const emotionColors: Record<string, string> = {
  curiosity: "bg-gradient-to-br from-blue-600 to-blue-800",
  insight: "bg-gradient-to-br from-yellow-500 to-yellow-700",
  frustration: "bg-gradient-to-br from-red-600 to-red-800",
  joy: "bg-gradient-to-br from-pink-500 to-pink-700",
  fear: "bg-gradient-to-br from-gray-600 to-gray-800",
  surprise: "bg-gradient-to-br from-indigo-500 to-indigo-700",
};

const MemoryScroller: React.FC<MemoryScrollerProps> = ({
  memoryItems,
  onPreviewQWave,
}) => {
  const [removedItems, setRemovedItems] = useState<Set<string>>(new Set());

  // ✅ Dynamically get containerId from memoryItems
  const containerId = memoryItems?.[0]?.containerId || "default.dc.json";
  const { emit } = useWebSocket(`/qfc/${containerId}`, () => {});

  return (
    <div className="absolute bottom-0 left-0 w-full flex gap-3 flex-wrap overflow-x-auto bg-black/80 p-3 z-50">
      {memoryItems.map((item, i) => {
        if (removedItems.has(item.id)) return null;

        const label = item.label || item.id || `item-${i}`;
        const score = item.tranquilityScore ?? null;
        const summary =
          item.summary || item.memorySummary || item.intent || "No summary";
        const containerId = item.containerId || "default.dc.json";
        const hasEntanglement = !!item.entanglement || item.entangled === true;
        const emotion = item.emotion?.toLowerCase?.();
        const emotionClass = emotionColors[emotion] || "bg-emerald-700";

        return (
          <div
            key={`memory-${i}`}
            className={`${emotionClass} text-white px-3 py-2 rounded shadow flex flex-col items-start min-w-[160px] relative hover:scale-[1.03] transition-all duration-200 cursor-pointer`}
            title={summary}
            onClick={() => onPreviewQWave?.(item.id)}
          >
            <div className="text-sm font-semibold truncate max-w-full">
              {label}
            </div>

            {/* 🧬 Entanglement marker */}
            {hasEntanglement && (
              <div className="text-xs text-purple-300 mt-1">🧬 Entangled</div>
            )}

            {/* 🌿 Tranquility Score */}
            {typeof score === "number" && (
              <div className="text-xs text-yellow-300 mt-1">
                🌿 Score: <strong>{score.toFixed(2)}</strong>
              </div>
            )}

            {/* 📥 Pull-to-Field */}
            <button
              onClick={(e) => {
                e.stopPropagation(); // Prevent triggering QWave preview
                pull_to_field(item, containerId, emit);
                setRemovedItems((prev) => new Set(prev).add(item.id));
              }}
              className="text-xs px-2 py-1 mt-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded shadow w-full text-center"
            >
              📥 Pull
            </button>
          </div>
        );
      })}
    </div>
  );
};

export default MemoryScroller;