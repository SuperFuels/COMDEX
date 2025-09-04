import React, { useEffect, useRef, useState } from "react";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { playGlyphNarration } from "@/utils/hologram_audio";
import { cn } from "@/lib/utils";
import { MODULATION_METADATA, ModulationStrategy } from "@/symbolic/modulation_meta"; // ✅ Add modulation metadata

interface GHXTimelineProps {
  glyphs: {
    glyph_id: string;
    symbol: string;
    timestamp: string;
    cost?: number;
    entangled?: string[];
    collapse_trace?: boolean;
    modulation_strategy?: string;
    coherence_score?: number;
  }[];
  onSelectGlyph?: (glyph: any) => void;
}

export default function GHXTimeline({ glyphs, onSelectGlyph }: GHXTimelineProps) {
  const [index, setIndex] = useState(0);
  const [hovered, setHovered] = useState<number | null>(null);
  const currentGlyph = glyphs[index] || null;
  const sliderRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (hovered !== null && glyphs[hovered]) {
      playGlyphNarration(glyphs[hovered].symbol);
    }
  }, [hovered]);

  useEffect(() => {
    if (onSelectGlyph && currentGlyph) {
      onSelectGlyph(currentGlyph);
    }
  }, [index]);

  const getCoherenceShade = (score?: number) => {
    if (score === undefined) return "";
    if (score >= 0.9) return "bg-green-700";
    if (score >= 0.6) return "bg-yellow-700";
    if (score >= 0.3) return "bg-orange-700";
    return "bg-red-700";
  };

  return (
    <div className="w-full px-4 py-2 bg-black/80 rounded-md">
      <div className="text-xs text-white mb-2">
        Replay Step: {index + 1} / {glyphs.length}
      </div>

      <Slider
        min={0}
        max={glyphs.length - 1}
        step={1}
        value={[index]}
        onValueChange={([i]) => setIndex(i)}
        className="w-full"
      />

      <div className="flex flex-wrap gap-2 mt-3">
        {glyphs.map((g, i) => {
          const modulationStrategy = g.modulation_strategy as ModulationStrategy;
          const meta = modulationStrategy ? MODULATION_METADATA[modulationStrategy] : null;
          const coherenceClass = getCoherenceShade(g.coherence_score);

          return (
            <div
              key={g.glyph_id}
              className={cn(
                "text-sm px-2 py-1 rounded cursor-pointer border border-white/10 transition-all duration-200",
                index === i ? "bg-purple-600 text-white" : coherenceClass || "bg-gray-700 text-gray-300",
                g.coherence_score !== undefined && g.coherence_score < 0.3 && "blur-[1px] skew-x-1"
              )}
              onClick={() => setIndex(i)}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              {g.symbol}
              {g.collapse_trace && <Badge className="ml-1 text-[10px] bg-yellow-500">⧖</Badge>}
              {g.entangled?.length > 0 && <Badge className="ml-1 text-[10px] bg-fuchsia-500">↔</Badge>}
              {g.cost && (
                <Badge className="ml-1 text-[10px] bg-blue-600">
                  {g.cost.toFixed(2)}
                </Badge>
              )}
              {modulationStrategy && (
                <div className="text-[10px] mt-1 text-gray-300">
                  {meta?.emoji || ""} {meta?.short || modulationStrategy}
                </div>
              )}
              {g.coherence_score !== undefined && (
                <div className="text-[10px] text-white/70">
                  🧬 {Math.round(g.coherence_score * 100)}% coherence
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}