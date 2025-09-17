"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

// Minimal types needed for this component
type GHXFrame = {
  entangled_links?: any[];
  // other frame fields are ignored by this control
  [key: string]: any;
};

type GHXProjection = {
  light_field: GHXFrame[];
};

type Props = {
  projection: GHXProjection | null;
  onFrameSelect: (frameIndex: number, glyph: GHXFrame, entangledLinks?: any[]) => void;
  onPlayToggle?: (playing: boolean) => void;
};

export default function GHXReplaySlider({ projection, onFrameSelect, onPlayToggle }: Props) {
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);

  const totalFrames = projection?.light_field.length ?? 0;

  // 🔄 Auto-play progression
  useEffect(() => {
    if (!playing || totalFrames === 0) return;

    const id = window.setInterval(() => {
      setFrame((prev) => {
        const next = (prev + 1) % totalFrames;
        emitFrameSelect(next);
        return next;
      });
    }, 800);

    return () => window.clearInterval(id);
  }, [playing, totalFrames]);

  const emitFrameSelect = (frameIndex: number) => {
    if (!projection) return;
    const glyph = projection.light_field[frameIndex];
    const entangledLinks = glyph?.entangled_links ?? [];
    onFrameSelect(frameIndex, glyph, entangledLinks);
  };

  const handleRangeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const frameIndex = Number(e.target.value);
    setFrame(frameIndex);
    emitFrameSelect(frameIndex);
  };

  const handleToggle = () => {
    const next = !playing;
    setPlaying(next);
    onPlayToggle?.(next);
  };

  if (!projection || totalFrames === 0) return null;

  return (
    <div className="flex flex-col items-center w-full gap-2 px-4 py-2 bg-black/30 rounded-lg">
      <div className="flex items-center w-full gap-4">
        {/* Our Button type doesn't support variant/size; style with classes */}
        <Button
          onClick={handleToggle}
          className="h-8 px-3 border border-input bg-background hover:bg-accent hover:text-accent-foreground"
        >
          {playing ? "⏸ Pause" : "▶️ Play"}
        </Button>

        {/* Native range input instead of @/components/ui/slider */}
        <input
          type="range"
          min={0}
          max={Math.max(0, totalFrames - 1)}
          step={1}
          value={frame}
          onChange={handleRangeChange}
          className="w-full accent-cyan-400"
          aria-label="Replay frame"
        />
      </div>

      <span className="text-xs text-white/70">
        Frame {frame + 1} / {totalFrames}
      </span>
    </div>
  );
}