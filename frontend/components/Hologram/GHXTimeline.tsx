import React, { useEffect, useRef, useState } from "react";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { playGlyphNarration } from "@/utils/hologram_audio";
import { cn } from "@/lib/utils";

interface GHXTimelineProps {
  glyphs: {
    glyph_id: string;
    symbol: string;
    timestamp: string;
    cost?: number;
    entangled?: string[];
    collapse_trace?: boolean;
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
        {glyphs.map((g, i) => (
          <div
            key={g.glyph_id}
            className={cn(
              "text-sm px-2 py-1 rounded cursor-pointer",
              index === i ? "bg-purple-600 text-white" : "bg-gray-700 text-gray-300"
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
          </div>
        ))}
      </div>
    </div>
  );
}