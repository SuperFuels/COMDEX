"use client";

import { useState, useEffect } from "react";
import { playGlyphNarration } from "@/components/ui/hologram_audio";
import GHXTimeline from "@/components/Hologram/GHXTimeline";
import { useCanvasRecorder } from "@/hooks/useCanvasRecorder";
import { useCollapseMetrics } from "@/hooks/useCollapseMetrics";
import CollapseGraph from "@/components/Hologram/CollapseGraph";
// import DecoherenceGraph from "@/components/Hologram/DecoherenceGraph";
import { WaveScopePanel } from "@/components/WaveScope/WaveScopePanel";
import {
  MODULATION_METADATA,
  ModulationStrategy,
} from "@/lib/glyphwave/modulationMetadata";
import useCollapseTrace from "@/hooks/useCollapseTrace";

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

const CollapseGraphAny = CollapseGraph as unknown as React.FC<any>;

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
  const [showWaveScope, setShowWaveScope] = useState(false);
  const [showCollapsed, setShowCollapsed] = useState(true);

  // --- collapse trace data (normalize everything to arrays/objects) ---
  const { data, loading } = useCollapseTrace(showCollapsed);
  const safeTicks: number[] = Array.isArray(data?.ticks) ? data!.ticks : [];
  const safeGrouped: Record<string | number, any[]> =
    data && data.grouped_beams && typeof data.grouped_beams === "object"
      ? (data.grouped_beams as Record<string | number, any[]>)
      : {};

  const [tickIndex, setTickIndex] = useState(0);
  const clampedTickIndex =
    safeTicks.length === 0
      ? 0
      : Math.min(Math.max(tickIndex, 0), safeTicks.length - 1);

  const currentTick = safeTicks[clampedTickIndex] ?? 0;
  const rawCurrentBeams = safeGrouped[currentTick] as any;
  const currentBeams: any[] = Array.isArray(rawCurrentBeams)
    ? rawCurrentBeams
    : [];
  const liveTick = safeTicks[clampedTickIndex] ?? null;

  // --- collapse metrics (normalize) ---
  const collapseMetrics =
    useCollapseMetrics() || ({
      collapseHistory: [],
      decoherenceHistory: [],
      latestCollapse: null,
      latestDecoherence: null,
    } as any);

  const collapseHistory: any[] = Array.isArray(
    collapseMetrics.collapseHistory
  )
    ? collapseMetrics.collapseHistory
    : [];
  const decoherenceHistory: number[] = Array.isArray(
    collapseMetrics.decoherenceHistory
  )
    ? collapseMetrics.decoherenceHistory
    : [];
  const collapseRate: number | null =
    typeof collapseMetrics.latestCollapse === "number"
      ? collapseMetrics.latestCollapse
      : null;
  const decoherenceRate: number | null =
    typeof collapseMetrics.latestDecoherence === "number"
      ? collapseMetrics.latestDecoherence
      : null;

  // --- recorder (safe no-ops if hook fails) ---
  const recorder =
    useCanvasRecorder() || ({
      isRecording: false,
      startRecording: () => {},
      stopRecording: () => {},
      downloadRecording: () => {},
      downloadUrl: null,
    } as any);

  const {
    isRecording,
    startRecording,
    stopRecording,
    downloadRecording,
    downloadUrl,
  } = recorder;

  // --- rendered glyphs normalization ---
  const safeRenderedGlyphs: any[] = Array.isArray(renderedGlyphs)
    ? renderedGlyphs
    : [];

  // 🧠 latest glyph + modulation strategy
  const latestGlyph = safeRenderedGlyphs[safeRenderedGlyphs.length - 1];
  const modulationStrategy = latestGlyph
    ?.modulation_strategy as ModulationStrategy | undefined;
  const modulationMeta = modulationStrategy
    ? MODULATION_METADATA[modulationStrategy]
    : null;

  // 🔁 HUD toggle effects
  useEffect(() => {
    onReplayToggle?.(replayMode);
  }, [replayMode, onReplayToggle]);

  useEffect(() => {
    onTraceOverlayToggle?.(traceOverlay);
  }, [traceOverlay, onTraceOverlayToggle]);

  // 🔊 Initial narration
  useEffect(() => {
    playGlyphNarration("↔");
  }, []);

  // 📉 Decoherence trend logic
  let decoherenceTrend = "➖";
  if (decoherenceHistory.length >= 2) {
    const prev = decoherenceHistory[decoherenceHistory.length - 2] || 0;
    const curr = decoherenceHistory[decoherenceHistory.length - 1] || 0;
    const delta = prev - curr;
    if (Math.abs(delta) > 0.0001) {
      decoherenceTrend = delta > 0 ? "📈" : "📉";
    }
  }

  // 🔏 Signature badge
  let signatureBadge: JSX.Element | null = null;
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

  return (
    <div className="absolute top-4 right-4 bg-black/60 text-white p-4 rounded-xl shadow-xl w-80 z-50 backdrop-blur-md">
      {/* Header + signature */}
      <div className="flex items-center mb-2">
        <h2 className="text-lg font-bold">🧠 Hologram HUD</h2>
        {signatureBadge}
      </div>

      <div className="text-sm space-y-1">
        {/* Metadata */}
        <div>
          <span className="text-gray-300">Projection ID:</span>
          <div className="break-all">{projectionId || "—"}</div>
        </div>
        <div>
          <span className="text-gray-300">Rendered At:</span>
          <div>{renderedAt || "—"}</div>
        </div>
        {signature?.timestamp && (
          <div className="text-xs text-gray-400 italic mt-1">
            Signed at: {new Date(signature.timestamp).toLocaleString()}
          </div>
        )}

        {/* Glyph counts */}
        <div>
          <span className="text-gray-300">Glyphs Triggered:</span>{" "}
          <span className="text-green-400 font-bold">{triggeredGlyphs}</span>
          {" / "}
          <span>{totalGlyphs}</span>
        </div>

        {/* Modulation strategy */}
        {modulationStrategy && modulationMeta && (
          <div className="mt-2 p-2 rounded bg-gray-800/50 border border-cyan-500 text-xs text-white">
            <div className="flex items-center justify-between">
              <span>
                🧩 <strong>Modulation:</strong> {modulationStrategy}
              </span>
              <span className="text-cyan-400">
                {modulationMeta.icon} {modulationMeta.description}
              </span>
            </div>
            <div className="text-xs text-gray-300 mt-1">
              Security: {modulationMeta.security_score} • Penalty:{" "}
              {modulationMeta.coherence_penalty}
            </div>
          </div>
        )}

        {/* Caption */}
        {currentCaption && (
          <div className="mt-2 p-2 bg-purple-800/50 rounded text-xs italic border border-purple-400/30">
            <span className="text-purple-300">📜 Caption:</span>{" "}
            {currentCaption}
          </div>
        )}

        {/* Collapse + decoherence metrics */}
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

            {/* Graphs */}
            <div className="mt-2 space-y-2">
              <CollapseGraphAny data={collapseHistory} />
              {/* <DecoherenceGraph data={decoherenceHistory} /> */}
            </div>

            {/* WaveScope toggle */}
            <div className="mt-2 flex justify-center">
              <button
                onClick={() => setShowWaveScope(!showWaveScope)}
                className="px-3 py-1 rounded bg-blue-800 hover:bg-blue-700 text-xs text-white border border-blue-500"
              >
                {showWaveScope ? "Hide WaveScope 🔽" : "Show WaveScope 🔼"}
              </button>
            </div>

            {showWaveScope && projectionId && (
              <div className="mt-4">
                <WaveScopePanel containerId={projectionId} />
              </div>
            )}
          </>
        )}

        {/* Replay / trace toggles */}
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

        {/* Replay slider */}
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

        {/* Export + layout */}
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

        {/* Recording controls */}
        <div className="mt-3">
          <div className="flex justify-between items-center">
            <button
              onClick={() =>
                isRecording
                  ? stopRecording()
                  : startRecording(document.querySelector("canvas") as HTMLCanvasElement)
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
                onClick={() => downloadRecording()}
                className="px-3 py-1 text-xs bg-blue-500 hover:bg-blue-600 rounded shadow"
              >
                💾 Save Video
              </button>
            )}
          </div>

          {/* Tick navigation */}
          {safeTicks.length > 0 && (
            <div className="flex items-center space-x-3 mt-2 text-xs text-white">
              <button
                className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded"
                onClick={() =>
                  setTickIndex((prev) => Math.max(prev - 1, 0))
                }
                disabled={clampedTickIndex === 0}
              >
                ⏮ Prev
              </button>
              <span className="px-2">
                Tick {clampedTickIndex + 1} / {safeTicks.length} (#{currentTick})
              </span>
              <button
                className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded"
                onClick={() =>
                  setTickIndex((prev) =>
                    Math.min(prev + 1, safeTicks.length - 1)
                  )
                }
                disabled={clampedTickIndex >= safeTicks.length - 1}
              >
                Next ⏭
              </button>
            </div>
          )}

          {/* Beams at tick */}
          {currentBeams.length > 0 ? (
            <div className="mt-2 text-xs text-yellow-300 max-h-32 overflow-y-auto">
              <strong>Beams at Tick #{currentTick}:</strong>
              <ul className="list-disc pl-4">
                {currentBeams.map((beam: any) => (
                  <li key={beam.glyph_id || beam.symbol}>
                    {beam.symbol} ({(beam.glyph_id || "").slice(0, 6)}) —{" "}
                    {beam.collapse_state}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="mt-2 text-xs text-gray-400 italic">
              No beams at this tick.
            </div>
          )}

          {/* GHX Timeline */}
          <div className="pt-3">
            {replayMode ? (
              <GHXTimeline
                glyphs={
                  Array.isArray(data?.all_beams) ? data!.all_beams : []
                }
                showCollapsed={showCollapsed}
                onToggleCollapse={setShowCollapsed}
                onSelectGlyph={(glyph) => {
                  setCurrentGlyph?.(glyph);
                }}
              />
            ) : (
              safeRenderedGlyphs.length > 0 &&
              setCurrentGlyph && (
                <GHXTimeline
                  glyphs={safeRenderedGlyphs}
                  onSelectGlyph={setCurrentGlyph}
                />
              )
            )}

            {liveTick !== null && (
              <div className="text-xs text-green-300 mt-1">
                Live Tick: {liveTick}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}