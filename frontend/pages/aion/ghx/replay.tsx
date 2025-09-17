// frontend/pages/aion/ghx/replay.tsx
"use client";

import React, { useEffect, useState } from "react";
import GHXReplaySlider from "@/components/Hologram/GHXReplaySlider";
import { Card, CardContent } from "@/components/ui/card";

/** Minimal local shape so we don't depend on "@/types/ghx_types" */
type GHXPacket = {
  /** Array of frames; each frame is an array of glyph-like records */
  light_field: any[];
  rendered_at?: string;
  projection_id?: string;
};

/** Very lightweight visual for a frame (no three.js dependency) */
function SimpleGlyphPanel({ glyphs }: { glyphs: any[] }) {
  return (
    <div className="grid grid-cols-10 gap-2">
      {glyphs?.map((g, i) => (
        <div
          key={g?.glyph_id ?? i}
          className="px-2 py-1 rounded bg-zinc-900/70 border border-zinc-700 text-center"
          title={g?.glyph_id ?? ""}
        >
          <span className="text-lg">
            {g?.symbol ?? g?.glyph ?? "?"}
          </span>
        </div>
      ))}
      {(!glyphs || glyphs.length === 0) && (
        <div className="text-sm text-zinc-400 col-span-full text-center py-6">
          No glyphs in this frame.
        </div>
      )}
    </div>
  );
}

export default function GHXReplayPage() {
  const [projection, setProjection] = useState<GHXPacket | null>(null);
  const [frameIndex, setFrameIndex] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/ghx/seed_projection.ghx.json");
        const data: GHXPacket = await res.json();
        setProjection(data ?? { light_field: [] });
        setFrameIndex(0);
      } catch {
        setProjection({ light_field: [] });
      }
    })();
  }, []);

  const currentGlyphs = Array.isArray(projection?.light_field)
    ? (projection!.light_field[frameIndex] ?? [])
    : [];

  return (
    <Card className="w-full min-h-screen bg-black text-white">
      <CardContent className="w-full min-h-screen flex flex-col gap-4 p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg text-purple-400 font-semibold">
            🌌 GHX Replay Projection
          </h2>
          {projection?.projection_id && (
            <span className="text-xs text-zinc-400">
              ID: {projection.projection_id}
            </span>
          )}
        </div>

        {/* Frame preview */}
        <div className="flex-1 rounded-lg border border-zinc-800 p-4 bg-zinc-950/60">
          <SimpleGlyphPanel glyphs={currentGlyphs} />
        </div>

        {/* Scrubber */}
        <div className="mt-2">
          <GHXReplaySlider
            projection={projection}
            onFrameSelect={(i) => setFrameIndex(i)}
            onPlayToggle={() => {/* optional hook-up */}}
          />
        </div>
      </CardContent>
    </Card>
  );
}