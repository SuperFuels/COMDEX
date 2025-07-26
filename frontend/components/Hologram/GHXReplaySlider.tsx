"use client";

import { useState, useEffect } from "react";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { GHXPacket } from "@/types/ghx_types";

type Props = {
  projection: GHXPacket | null;
  onFrameSelect: (frameIndex: number) => void;
  onPlayToggle?: (playing: boolean) => void;
};

export default function GHXReplaySlider({ projection, onFrameSelect, onPlayToggle }: Props) {
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);

  const totalFrames = projection?.light_field.length || 0;

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (playing && totalFrames > 0) {
      interval = setInterval(() => {
        setFrame((prev) => {
          const next = (prev + 1) % totalFrames;
          onFrameSelect(next);
          return next;
        });
      }, 800);
    }
    return () => clearInterval(interval);
  }, [playing, totalFrames]);

  const handleChange = (val: number[]) => {
    setFrame(val[0]);
    onFrameSelect(val[0]);
  };

  const handleToggle = () => {
    const next = !playing;
    setPlaying(next);
    if (onPlayToggle) onPlayToggle(next);
  };

  if (!projection || totalFrames === 0) return null;

  return (
    <div className="flex flex-col items-center w-full gap-2 px-4 py-2 bg-black/30 rounded-lg">
      <div className="flex items-center w-full gap-4">
        <Button onClick={handleToggle} variant="ghost" size="sm">
          {playing ? "⏸ Pause" : "▶️ Play"}
        </Button>
        <Slider
          min={0}
          max={totalFrames - 1}
          step={1}
          value={[frame]}
          onValueChange={handleChange}
          className="w-full"
        />
      </div>
      <span className="text-xs text-white/70">Frame {frame + 1} / {totalFrames}</span>
    </div>
  );
}