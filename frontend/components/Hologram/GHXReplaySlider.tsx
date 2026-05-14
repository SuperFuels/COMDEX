"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";

// Minimal types needed for this component
type GHXFrame = {
  entangled_links?: any; // we’ll normalize this to [] if it’s not an array
  [key: string]: any;
};

type GHXProjection = {
  light_field?: any; // may or may not be an array, we guard below
};

type Props = {
  projection: GHXProjection | null;
  // make glyph / links optional so callers can ignore them
  onFrameSelect: (
    frameIndex: number,
    glyph?: GHXFrame,
    entangledLinks?: any[]
  ) => void;
  onPlayToggle?: (playing: boolean) => void;
};

export default function GHXReplaySlider({
  projection,
  onFrameSelect,
  onPlayToggle,
}: Props) {
  // 🔐 Normalize frames to a *real* array, no matter what comes in
  const frames = useMemo<GHXFrame[]>(() => {
    const raw = projection?.light_field;

    if (!raw) return [];
    if (Array.isArray(raw)) return raw as GHXFrame[];

    // Fallback if API ever wraps frames differently
    if (Array.isArray((raw as any).frames)) {
      return (raw as any).frames as GHXFrame[];
    }

    return [];
  }, [projection]);

  const totalFrames = frames.length;

  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, totalFrames, frames]);

  const emitFrameSelect = (frameIndex: number) => {
    const glyph = frames[frameIndex];
    if (!glyph) return;

    const linksRaw = (glyph as any).entangled_links;
    const entangledLinks = Array.isArray(linksRaw) ? linksRaw : [];

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

  if (totalFrames === 0) return null;

  return (
    <div className="flex flex-col items-center w-full gap-2 px-4 py-2 bg-black/30 rounded-lg">
      <div className="flex items-center w-full gap-4">
        <Button
          onClick={handleToggle}
          className="h-8 px-3 border border-input bg-background hover:bg-accent hover:text-accent-foreground"
        >
          {playing ? "⏸ Pause" : "▶️ Play"}
        </Button>

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