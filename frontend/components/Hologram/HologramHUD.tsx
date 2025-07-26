"use client";

import { useState, useEffect } from "react";
import { playGlyphNarration } from "@/utils/hologram_audio";
import GHXTimeline from "@/components/Hologram/GHXTimeline";

type HUDProps = {
  projectionId?: string;
  renderedAt?: string;
  totalGlyphs?: number;
  triggeredGlyphs?: number;
  onReplayToggle?: (enabled: boolean) => void;
  onTraceOverlayToggle?: (enabled: boolean) => void;
  onExport?: () => void;
  onLayoutToggle?: () => void;

  // 🎯 NEW:
  renderedGlyphs?: any[]; // array of glyphs with .symbol at least
  setCurrentGlyph?: (glyph: any) => void;
};

export default function HologramHUD({
  projectionId,
  renderedAt,
  totalGlyphs = 0,
  triggeredGlyphs = 0,
  onReplayToggle,
  onTraceOverlayToggle,
  onExport,
  onLayoutToggle,

  // 🎯 NEW props
  renderedGlyphs = [],
  setCurrentGlyph,
}: HUDProps) {
  const [replayMode, setReplayMode] = useState(false);
  const [traceOverlay, setTraceOverlay] = useState(false);
  const [replayProgress, setReplayProgress] = useState(0);

  useEffect(() => {
    if (onReplayToggle) onReplayToggle(replayMode);
  }, [replayMode]);

  useEffect(() => {
    if (onTraceOverlayToggle) onTraceOverlay(traceOverlay);
  }, [traceOverlay]);

  // Optional: Narrate glyph trigger (static sample for now)
  useEffect(() => {
    playGlyphNarration("↔");
  }, []);

  return (
    <div className="absolute top-4 right-4 bg-black/60 text-white p-4 rounded-xl shadow-xl w-80 z-50 backdrop-blur-md">
      <h2 className="text-lg font-bold mb-2">🧠 Hologram HUD</h2>
      <div className="text-sm space-y-1">
        <div>
          <span className="text-gray-300">Projection ID:</span>
          <div className="break-all">{projectionId || "—"}</div>
        </div>
        <div>
          <span className="text-gray-300">Rendered At:</span>
          <div>{renderedAt || "—"}</div>
        </div>
        <div>
          <span className="text-gray-300">Glyphs Triggered:</span>{" "}
          <span className="text-green-400 font-bold">{triggeredGlyphs}</span>
          {" / "}
          <span>{totalGlyphs}</span>
        </div>

        <div className="flex justify-between items-center pt-2 border-t border-white/20 mt-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={replayMode}
              onChange={(e) => setReplayMode(e.target.checked)}
            />
            Replay Mode
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={traceOverlay}
              onChange={(e) => setTraceOverlay(e.target.checked)}
            />
            Collapse Trace
          </label>
        </div>

        {replayMode && (
          <div className="pt-2">
            <label className="text-xs text-gray-300">Replay Position</label>
            <input
              type="range"
              min={0}
              max={100}
              value={replayProgress}
              onChange={(e) => setReplayProgress(Number(e.target.value))}
              className="w-full"
            />
          </div>
        )}

        {/* 📀 Export + 🌌 Layout Toggle */}
        <div className="flex justify-between items-center mt-3">
          <button
            onClick={onExport}
            className="px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600 rounded shadow"
          >
            📀 Export GHX
          </button>
          <button
            onClick={onLayoutToggle}
            className="px-3 py-1 text-xs bg-purple-500 hover:bg-purple-600 rounded shadow"
          >
            🌌 Toggle Layout
          </button>
        </div>

        {/* 🎞️ GHX Timeline Replay */}
        {renderedGlyphs.length > 0 && setCurrentGlyph && (
          <div className="pt-3">
            <GHXTimeline glyphs={renderedGlyphs} onSelectGlyph={setCurrentGlyph} />
          </div>
        )}
      </div>
    </div>
  );
}