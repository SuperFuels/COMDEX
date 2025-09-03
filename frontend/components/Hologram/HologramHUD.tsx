"use client";

import { useState, useEffect } from "react";
import { playGlyphNarration } from "@/utils/hologram_audio";
import GHXTimeline from "@/components/Hologram/GHXTimeline";
import useCanvasRecorder from "@/hooks/useCanvasRecorder";
import useWebSocket from "@/utils/useWebSocket";
import useCollapseMetrics from "@/hooks/useCollapseMetrics";
import CollapseGraph from "@/components/Hologram/CollapseGraph";
import { WaveScopePanel } from "@/components/WaveScope/WaveScopePanel"; 
import { useCollapseMetrics } from "@/hooks/useCollapseMetrics";

type HUDProps = {
  projectionId?: string;
  renderedAt?: string;
  totalGlyphs?: number;
  triggeredGlyphs?: number;
  onReplayToggle?: (enabled: boolean) => void;
  onTraceOverlayToggle?: (enabled: boolean) => void;
  onExport?: () => void;
  onLayoutToggle?: () => void;
  renderedGlyphs?: any[];
  setCurrentGlyph?: (glyph: any) => void;
  currentCaption?: string;
  signature?: {
    sig: string;
    signed_by: string;
    timestamp: string;
  };
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
  renderedGlyphs = [],
  setCurrentGlyph,
  currentCaption = "",
  signature,
}: HUDProps) {
  const [replayMode, setReplayMode] = useState(false);
  const [traceOverlay, setTraceOverlay] = useState(false);
  const [replayProgress, setReplayProgress] = useState(0);
  const [showWaveScope, setShowWaveScope] = useState(false); // ✅ NEW TOGGLE

  const {
    collapseHistory,
    decoherenceHistory,
    latestCollapse: collapseRate,
    latestDecoherence: decoherenceRate,
  } = useCollapseMetrics();

  const {
    isRecording,
    startRecording,
    stopRecording,
    downloadRecording,
    downloadUrl,
  } = useCanvasRecorder();

  useEffect(() => {
    if (onReplayToggle) onReplayToggle(replayMode);
  }, [replayMode]);

  useEffect(() => {
    if (onTraceOverlayToggle) onTraceOverlayToggle(traceOverlay);
  }, [traceOverlay]);

  useEffect(() => {
    playGlyphNarration("↔");
  }, []);

  let decoherenceTrend = "➖";
  if (decoherenceHistory.length >= 2) {
    const prev = decoherenceHistory[decoherenceHistory.length - 2];
    const curr = decoherenceHistory[decoherenceHistory.length - 1];
    const delta = prev - curr;
    if (Math.abs(delta) > 0.0001) {
      decoherenceTrend = delta > 0 ? "📈" : "📉";
    }
  }

  // ✅ Signature Badge Logic
  let signatureBadge = null;
  if (signature?.sig && signature?.signed_by) {
    signatureBadge = (
      <span className="ml-2 px-2 py-1 text-xs rounded-xl bg-green-700 text-white">
        🔏 Vault Signed
      </span>
    );
  } else if (signature && !signature?.sig) {
    signatureBadge = (
      <span className="ml-2 px-2 py-1 text-xs rounded-xl bg-red-700 text-white">
        🚫 Invalid Signature
      </span>
    );
  } else {
    signatureBadge = (
      <span className="ml-2 px-2 py-1 text-xs rounded-xl bg-yellow-500 text-black">
        ❌ Unsigned
      </span>
    );
  }

  // ✅ Symbolic Collapse + Decoherence Metrics HUD
  const metricsDisplay = (
    <div className="mt-2 px-3 py-1 bg-black bg-opacity-30 rounded-xl text-white text-xs flex items-center space-x-4">
      <span>
        🧠 Collapse/sec:{" "}
        {collapseRate !== null ? collapseRate.toFixed(2) : "–"}
      </span>
      <span>
        🧠 Decoherence:{" "}
        {decoherenceRate !== null ? decoherenceRate.toFixed(4) : "–"}{" "}
        {decoherenceTrend}
      </span>
    </div>
  );
}

  return (
    <div className="absolute top-4 right-4 bg-black/60 text-white p-4 rounded-xl shadow-xl w-80 z-50 backdrop-blur-md">
      <div className="flex items-center mb-2">
        <h2 className="text-lg font-bold">🧠 Hologram HUD</h2>
        {signatureBadge}
      </div>

      <div className="text-sm space-y-1">
        <div>
          <span className="text-gray-300">Projection ID:</span>
          <div className="break-all">{projectionId || "—"}</div>
        </div>
        <div>
          <span className="text-gray-300">Rendered At:</span>
          <div>{renderedAt || "—"}</div>
        </div>

        {/* ✅ Optional Signature Metadata */}
        {signature?.timestamp && (
          <div className="text-xs text-gray-400 italic mt-1">
            Signed at: {new Date(signature.timestamp).toLocaleString()}
          </div>
        )}

        <div>
          <span className="text-gray-300">Glyphs Triggered:</span>{" "}
          <span className="text-green-400 font-bold">{triggeredGlyphs}</span>
          {" / "}
          <span>{totalGlyphs}</span>
        </div>

        {/* 📜 Current Caption Display */}
        {currentCaption && (
          <div className="mt-2 p-2 bg-purple-800/50 rounded text-xs italic border border-purple-400/30">
            <span className="text-purple-300">📜 Caption:</span>{" "}
            {currentCaption}
          </div>
        )}

        {/* 📉 Collapse + Decoherence Live Metrics */}
        {collapseRate !== null && decoherenceRate !== null && (
          <>
            <div className="mt-2 p-2 bg-black/30 rounded text-xs border border-blue-400/30 space-y-1">
              <div>
                <span className="text-blue-300">⚡ Collapse/sec:</span>{" "}
                <span className="text-white font-mono">
                  {collapseRate.toFixed(2)}
                </span>
              </div>
              <div>
                <span className="text-purple-300">☢️ Decoherence:</span>{" "}
                <span className="text-white font-mono">
                  {decoherenceRate.toFixed(3)} {decoherenceTrend}
                </span>
              </div>
            </div>

            <div className="text-xs text-green-300 font-mono mt-2 border border-green-700 rounded p-2 bg-black/50">
              <div className="flex justify-between">
                <div>
                  🧠 <strong>Collapse Rate:</strong> {collapseRate.toFixed(2)} / sec
                </div>
                <div>
                  🌀 <strong>Decoherence:</strong>{" "}
                  {(decoherenceRate * 100).toFixed(1)}% {decoherenceTrend}
                </div>
              </div>
            </div>

            <div className="mt-2 space-y-2">
              <CollapseGraph data={collapseHistory} />
              <DecoherenceGraph data={decoherenceHistory} />
            </div>

            {/* 🔘 Toggle WaveScope */}
            <div className="mt-2 flex justify-center">
              <button
                onClick={() => setShowWaveScope(!showWaveScope)}
                className="px-3 py-1 rounded bg-blue-800 hover:bg-blue-700 text-xs text-white border border-blue-500"
              >
                {showWaveScope ? "Hide WaveScope 🔽" : "Show WaveScope 🔼"}
              </button>
            </div>

            {/* 🌀 WaveScope Panel */}
            {showWaveScope && projectionId && (
              <div className="mt-4">
                <WaveScopePanel containerId={projectionId} />
              </div>
            )}
          </>
        )}

        {/* 🧠 Replay & Overlay */}
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

        {/* 🎥 Recording Controls */}
        <div className="flex justify-between items-center mt-3">
          <button
            onClick={() =>
              isRecording
                ? stopRecording()
                : startRecording(document.querySelector("canvas")!)
            }
            className={`px-3 py-1 text-xs rounded shadow ${
              isRecording
                ? "bg-red-500 hover:bg-red-600"
                : "bg-green-500 hover:bg-green-600"
            }`}
          >
            {isRecording ? "⏹ Stop Recording" : "🎥 Start Recording"}
          </button>
          {downloadUrl && (
            <button
              onClick={downloadRecording}
              className="px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600 rounded shadow"
            >
              💾 Save Video
            </button>
          )}
        </div>

        {/* 🎞️ GHX Timeline Replay */}
        {renderedGlyphs.length > 0 && setCurrentGlyph && (
          <div className="pt-3">
            <GHXTimeline
              glyphs={renderedGlyphs}
              onSelectGlyph={setCurrentGlyph}
            />
          </div>
        )}
      </div>
    </div>
  );
}