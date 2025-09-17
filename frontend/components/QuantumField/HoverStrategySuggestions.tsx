// 🧠 HoverStrategySuggestions.tsx
import React from "react";
import { Html } from "@react-three/drei";
import { pull_to_field } from "@/utils/pull_to_field";
import useWebSocket from "@/hooks/useWebSocket";
import type { GlyphNode } from "@/types/qfc"; // ✅ bring in the expected type

interface StrategySuggestion {
  nodeId: string;
  position: [number, number, number];
  label: string;
  tranquilityScore: number;
  goalDelta: number;
  reason?: string;
  emotion?: string;
  containerId?: string;
}

interface HoverStrategySuggestionsProps {
  suggestions: StrategySuggestion[];
  visible: boolean;
  onPull?: (strategy: StrategySuggestion) => void;
}

const emotionColorMap: Record<string, string> = {
  curiosity: "bg-blue-600",
  insight: "bg-yellow-600",
  joy: "bg-pink-500",
  fear: "bg-gray-700",
  frustration: "bg-red-600",
  surprise: "bg-indigo-600",
};

const goalDeltaColor = (delta: number) => {
  if (delta > 0.7) return "text-green-300";
  if (delta > 0.4) return "text-yellow-200";
  return "text-red-300";
};

// 🔁 Adapter: StrategySuggestion -> GlyphNode (adds the required `id`)
const toGlyphNode = (s: StrategySuggestion): GlyphNode => ({
  ...(s as unknown as Omit<GlyphNode, "id">),
  id: s.nodeId,
});

const HoverStrategySuggestions: React.FC<HoverStrategySuggestionsProps> = ({
  suggestions,
  visible,
  onPull,
}) => {
  if (!visible || suggestions.length === 0) return null;

  // 🛰️ Setup WebSocket connection based on first containerId
  const containerIdFromList = suggestions?.[0]?.containerId || "default.dc.json";
  const { emit } = useWebSocket(`/qfc/${containerIdFromList}`, () => {});

  return (
    <>
      {suggestions.map((suggestion, i) => {
        const {
          nodeId,
          label,
          tranquilityScore,
          goalDelta,
          position,
          reason,
          emotion,
          containerId,
        } = suggestion;

        const emotionClass =
          emotionColorMap[emotion?.toLowerCase() || ""] || "bg-yellow-500";

        return (
          <Html
            key={`strategy-${nodeId}-${i}`}
            position={[position[0], position[1] + 1.8, position[2]]}
            center
            distanceFactor={10}
          >
            <div
              className={`p-2 text-xs rounded shadow ${emotionClass} text-white animate-fadeInScale max-w-[200px] text-center transition-transform duration-300`}
              style={{ animation: "fadeInScale 0.4s ease-out" }}
            >
              <div className="font-semibold text-sm">🟡 Almost Worked</div>
              <div className="truncate">{label}</div>

              <div className="text-[10px] mt-1 opacity-90 leading-tight">
                🌿 Tranquility:{" "}
                <span className="text-emerald-200">
                  {tranquilityScore.toFixed(2)}
                </span>
                <br />
                🎯 Goal Δ:{" "}
                <span className={goalDeltaColor(goalDelta)}>
                  {goalDelta.toFixed(2)}
                </span>
              </div>

              {reason && (
                <div className="text-[10px] italic mt-1 opacity-80">
                  {reason}
                </div>
              )}

              {/* 📥 Optional pull button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onPull?.(suggestion);
                  // ✅ convert to GlyphNode to satisfy pull_to_field typing
                  const node = toGlyphNode(suggestion);
                  pull_to_field(node, containerId || "default.dc.json", emit);
                }}
                className="mt-2 text-[10px] px-2 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded shadow w-full"
              >
                📥 Pull Strategy
              </button>
            </div>
          </Html>
        );
      })}
    </>
  );
};

export default HoverStrategySuggestions;