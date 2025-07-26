// frontend/pages/aion/ghx/replay.tsx
"use client";

import React, { useEffect, useState } from "react";
import GHXVisualizer from "@/components/GHX/GHXVisualizer";
import GHXReplaySlider from "@/components/GHX/GHXReplaySlider";
import { GHXPacket } from "@/types/ghx_types";
import { Card, CardContent } from "@/components/ui/card";

export default function GHXReplayPage() {
  const [projection, setProjection] = useState<GHXPacket | null>(null);
  const [frameIndex, setFrameIndex] = useState(0);

  useEffect(() => {
    fetch("/ghx/seed_projection.ghx.json")
      .then((res) => res.json())
      .then((data) => {
        setProjection(data);
        setFrameIndex(0);
      });
  }, []);

  const currentGlyphs = projection?.light_field?.[frameIndex] || [];

  return (
    <Card className="w-full h-screen bg-black text-white">
      <CardContent className="w-full h-full flex flex-col gap-2 p-2">
        <h2 className="text-lg text-purple-400 font-semibold">🌌 GHX Replay Projection</h2>
        <div className="flex-1">
          <GHXVisualizer glyphs={currentGlyphs} />
        </div>
        <GHXReplaySlider
          projection={projection}
          onFrameSelect={(i) => setFrameIndex(i)}
        />
      </CardContent>
    </Card>
  );
}