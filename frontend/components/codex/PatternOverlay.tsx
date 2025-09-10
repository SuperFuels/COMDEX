import React from "react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";

interface PatternMatch {
  pattern_id: string;
  name: string;
  glyphs: string[];
  type: string;
  prediction?: string[];
  sqi_score?: number;
  source_container?: string;
  trigger_logic?: string;
}

interface PatternOverlayProps {
  patterns: PatternMatch[];
  onSelect?: (pattern: PatternMatch) => void;
}

const PatternOverlay: React.FC<PatternOverlayProps> = ({ patterns, onSelect }) => {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  if (!patterns || patterns.length === 0) return null;

  return (
    <div className="absolute top-2 left-2 bg-black/80 text-white border border-indigo-600 rounded-lg p-2 z-40 w-[300px] max-h-[80vh]">
      <div className="font-bold text-indigo-300 mb-2">🧩 Pattern Matches</div>
      <ScrollArea className="h-[65vh] pr-2">
        {patterns.map((p) => (
          <div
            key={p.pattern_id}
            className={cn(
              "mb-2 p-2 rounded-md transition cursor-pointer hover:bg-indigo-800",
              hoveredId === p.pattern_id && "bg-indigo-700"
            )}
            onMouseEnter={() => setHoveredId(p.pattern_id)}
            onMouseLeave={() => setHoveredId(null)}
            onClick={() => onSelect?.(p)}
          >
            <div className="text-sm font-semibold text-indigo-200">{p.name}</div>
            <div className="text-xs text-gray-300 mb-1">{p.type}</div>
            <div className="flex flex-wrap gap-1 mb-1">
              {p.glyphs.map((g, idx) => (
                <span
                  key={`${p.pattern_id}-glyph-${idx}`}
                  className="bg-slate-700 text-white text-xs px-2 py-0.5 rounded shadow"
                >
                  {g}
                </span>
              ))}
            </div>
            {p.prediction && (
              <div className="text-xs text-purple-300 mt-1">
                🔮 Prediction: {p.prediction.join(", ")}
              </div>
            )}
            {p.sqi_score != null && (
              <div className="text-xs text-green-300 mt-1">
                SQI Score: {p.sqi_score.toFixed(2)}
              </div>
            )}
            {p.trigger_logic && (
              <div className="text-xs text-yellow-200 mt-1 italic">
                ⚙ Trigger: {p.trigger_logic}
              </div>
            )}
            {p.source_container && (
              <div className="text-xs text-gray-400 mt-1">
                📦 Source: <span className="text-white">{p.source_container}</span>
              </div>
            )}
          </div>
        ))}
      </ScrollArea>
    </div>
  );
};

export default PatternOverlay;