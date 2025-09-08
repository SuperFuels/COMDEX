import React, { useEffect, useRef, useState } from "react";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { playGlyphNarration } from "@/utils/hologram_audio";
import { cn } from "@/lib/utils";
import { MODULATION_METADATA, ModulationStrategy } from "@/symbolic/modulation_meta";

interface GlyphType {
  glyph_id: string;
  symbol: string;
  timestamp: string;
  cost?: number;
  entangled?: string[];
  collapse_trace?: boolean;
  modulation_strategy?: string;
  coherence_score?: number;
  tick?: number;
  collapse_state?: string;
  sqi_score?: number;
  tick_duration_ms?: number;
}

interface GHXTimelineProps {
  glyphs: GlyphType[];
  onSelectGlyph?: (glyph: any) => void;
  showCollapsed?: boolean;
  onToggleCollapse?: (val: boolean) => void;
}

function groupGlyphsByTick(glyphs: GlyphType[]) {
  const grouped: Record<number, GlyphType[]> = {};
  for (const g of glyphs) {
    const tick = g.tick ?? 0;
    if (!grouped[tick]) grouped[tick] = [];
    grouped[tick].push(g);
  }
  return grouped;
}

export default function GHXTimeline({
  glyphs,
  onSelectGlyph,
  showCollapsed = true,
  onToggleCollapse,
}: GHXTimelineProps) {
  const [tickIndex, setTickIndex] = useState<number>(0);
  const [hovered, setHovered] = useState<number | null>(null);

  const filteredGlyphs = showCollapsed
    ? glyphs
    : glyphs.filter((g) => g.collapse_state !== "collapsed");

  const groupedBeams = groupGlyphsByTick(filteredGlyphs);
  const ticks = Object.keys(groupedBeams)
    .map(Number)
    .sort((a, b) => a - b);
  const currentTick = ticks[tickIndex] ?? 0;
  const currentBeams = groupedBeams[currentTick] || [];

  const sliderRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (hovered !== null && currentBeams[hovered]) {
      playGlyphNarration(currentBeams[hovered].symbol);
    }
  }, [hovered, currentBeams]);

  useEffect(() => {
    if (onSelectGlyph && currentBeams.length > 0) {
      onSelectGlyph(currentBeams[0]);
    }
  }, [tickIndex]);

  const getCoherenceShade = (score?: number) => {
    if (score === undefined) return "";
    if (score >= 0.9) return "bg-green-700";
    if (score >= 0.6) return "bg-yellow-700";
    if (score >= 0.3) return "bg-orange-700";
    return "bg-red-700";
  };

  return (
    <div className="w-full px-4 py-2 bg-black/80 rounded-md">
      <div className="flex items-center mb-3">
        <label className="text-white text-sm mr-2">Show Collapsed</label>
        <input
          type="checkbox"
          checked={showCollapsed}
          onChange={(e) => onToggleCollapse?.(e.target.checked)}
          className="scale-125"
        />
      </div>

      <div className="text-xs text-white mb-2">
        Tick: {tickIndex + 1} / {ticks.length} — Beams: {currentBeams.length}
      </div>

      <Slider
        min={0}
        max={ticks.length - 1}
        step={1}
        value={[tickIndex]}
        onValueChange={([i]) => setTickIndex(i)}
        className="w-full"
      />

      <div className="flex flex-wrap gap-2 mt-3">
        {currentBeams.map((g, i) => {
          const modulationStrategy = g.modulation_strategy as ModulationStrategy;
          const meta = modulationStrategy ? MODULATION_METADATA[modulationStrategy] : null;
          const coherenceClass = getCoherenceShade(g.coherence_score);

          return (
            <div
              key={g.glyph_id}
              className={cn(
                "text-sm px-2 py-1 rounded cursor-pointer border border-white/10 transition-all duration-200",
                coherenceClass || "bg-gray-700 text-gray-300",
                g.coherence_score !== undefined && g.coherence_score < 0.3 && "blur-[1px] skew-x-1"
              )}
              onClick={() => onSelectGlyph?.(g)}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              {g.symbol}

              {g.collapse_trace && (
                <Badge className="ml-1 text-[10px] bg-yellow-500">⧖</Badge>
              )}
              {g.entangled?.length > 0 && (
                <Badge className="ml-1 text-[10px] bg-fuchsia-500">↔</Badge>
              )}
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
              {g.sqi_score !== undefined && (
                <div className="text-[10px] text-white/70">
                  🔮 SQI: {g.sqi_score.toFixed(2)}
                </div>
              )}
              {g.tick_duration_ms !== undefined && (
                <div className="text-[10px] text-white/70">
                  ⏱️ {g.tick_duration_ms.toFixed(1)} ms
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}