"use client";

import React, { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/* -------- Minimal local fallbacks so the file is self-contained -------- */

// tiny “narrate glyph” shim (no-op on the server)
const playGlyphNarration = (symbol: string) => {
  if (typeof window === "undefined") return;
  try {
    // keep silent by default; uncomment to hear speech:
    // window.speechSynthesis?.speak(new SpeechSynthesisUtterance(symbol));
  } catch {
    /* ignore */
  }
};

type ModulationStrategy = string;
const MODULATION_METADATA: Record<
  string,
  { emoji?: string; short?: string }
> = {
  secure: { emoji: "🔒", short: "Secure" },
  stealth: { emoji: "🕶️", short: "Stealth" },
  fast: { emoji: "⚡", short: "Fast" },
};

/* ------------------------------- Types --------------------------------- */

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
  onSelectGlyph?: (glyph: GlyphType) => void;
  showCollapsed?: boolean;
  onToggleCollapse?: (val: boolean) => void;
}

/* ------------------------------ Helpers -------------------------------- */

function groupGlyphsByTick(glyphs: GlyphType[]) {
  const grouped: Record<number, GlyphType[]> = {};
  for (const g of glyphs) {
    const tick = g.tick ?? 0;
    if (!grouped[tick]) grouped[tick] = [];
    grouped[tick].push(g);
  }
  return grouped;
}

const getCoherenceShade = (score?: number) => {
  if (score === undefined) return "";
  if (score >= 0.9) return "bg-green-700";
  if (score >= 0.6) return "bg-yellow-700";
  if (score >= 0.3) return "bg-orange-700";
  return "bg-red-700";
};

/* ----------------------------- Component ------------------------------- */

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
  const currentBeams: GlyphType[] = groupedBeams[currentTick] || [];

  // play a tiny narration when you hover a glyph
  useEffect(() => {
    if (hovered !== null && currentBeams[hovered]) {
      playGlyphNarration(currentBeams[hovered].symbol);
    }
  }, [hovered, currentBeams]);

  // auto-select first glyph on tick change
  useEffect(() => {
    if (onSelectGlyph && currentBeams.length > 0) {
      onSelectGlyph(currentBeams[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tickIndex]);

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

      {/* Native range input instead of a custom Slider */}
      <input
        type="range"
        min={0}
        max={Math.max(0, ticks.length - 1)}
        step={1}
        value={tickIndex}
        onChange={(e) => setTickIndex(Number(e.target.value))}
        className="w-full accent-cyan-400"
        aria-label="Timeline tick"
      />

      <div className="flex flex-wrap gap-2 mt-3">
        {currentBeams.map((g: GlyphType, i: number) => {
          const modulationStrategy = g.modulation_strategy as ModulationStrategy;
          const meta = modulationStrategy
            ? MODULATION_METADATA[modulationStrategy] ?? null
            : null;
          const coherenceClass = getCoherenceShade(g.coherence_score);

          return (
            <div
              key={g.glyph_id}
              className={cn(
                "text-sm px-2 py-1 rounded cursor-pointer border border-white/10 transition-all duration-200",
                coherenceClass || "bg-gray-700 text-gray-300",
                g.coherence_score !== undefined &&
                  g.coherence_score < 0.3 &&
                  "blur-[1px] skew-x-1"
              )}
              onClick={() => onSelectGlyph?.(g)}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              {g.symbol}

              {g.collapse_trace && (
                <Badge className="ml-1 text-[10px] bg-yellow-500">⧖</Badge>
              )}
              {g.entangled?.length ? (
                <Badge className="ml-1 text-[10px] bg-fuchsia-500">↔</Badge>
              ) : null}
              {typeof g.cost === "number" && (
                <Badge className="ml-1 text-[10px] bg-blue-600">
                  {g.cost.toFixed(2)}
                </Badge>
              )}

              {modulationStrategy && (
                <div className="text-[10px] mt-1 text-gray-300">
                  {meta?.emoji || ""} {meta?.short || modulationStrategy}
                </div>
              )}
              {typeof g.coherence_score === "number" && (
                <div className="text-[10px] text-white/70">
                  🧬 {Math.round(g.coherence_score * 100)}% coherence
                </div>
              )}
              {typeof g.sqi_score === "number" && (
                <div className="text-[10px] text-white/70">
                  🔮 SQI: {g.sqi_score.toFixed(2)}
                </div>
              )}
              {typeof g.tick_duration_ms === "number" && (
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