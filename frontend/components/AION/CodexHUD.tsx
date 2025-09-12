import React, { useEffect, useState } from 'react';
import useWebSocket from '@/hooks/useWebSocket';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Play, Pause, Download, Eye, EyeOff } from 'lucide-react';
import { playGlyphNarration } from "@/components/ui/hologram_audio";
import axios from "axios";
import { useGlyphReplay } from "@/hooks/useGlyphReplay";
import { ReplayHUD } from "@/components/CodexHUD/ReplayHUD";
import { ReplayListPanel } from "@/components/CodexHUD/ReplayListPanel";
import { useCollapseMetrics } from "@/hooks/useCollapseMetrics";
import { useWaveTelemetry } from "@/hooks/useWaveTelemetry";
import { GHXVisualizerField } from '@/components/Hologram/ghx_visualizer_field';

interface GlyphDetail {
  energy?: number;
  ethics_risk?: number;
  delay?: number;
  opportunity_loss?: number;
  coord?: string;
  container?: string;
  operator?: string;
  entangled_from?: string;
  qglyph_id?: string;
  qglyph_paths?: [string, string];
  collapsed_path?: string;
  bias_score?: number;
  observer_trace?: string;
}

interface SuggestedRewrite {
  new_glyph: string;
  goal_match_score?: number;
  rewrite_success_prob?: number;
  reason?: string;
}

interface GlyphEvent {
  glyph: string;
  action: string;
  source: string;
  timestamp: number;
  cost?: number;
  trace_id?: string;
  trigger_type?: string;
  sqi?: boolean;
  detail?: GlyphDetail;
  context?: string;
  token?: string;
  identity?: string;
  luxpush?: boolean;
  type?: string;
  replay_trace?: boolean;
  collapse_trace?: boolean;
  entangled_identity?: boolean;
  suggested_rewrite?: SuggestedRewrite;

  // 🧠 Prediction metadata
  beamSource?: "PredictionBeam" | "DreamBeam" | "TranquilityBeam" | "GHX" | string;
  confidence?: number;
  entropy?: number;
  predicted?: boolean;
}

interface TickEvent {
  type: 'dimension_tick';
  container: string;
  timestamp: number;
}

interface GIPEvent {
  type: 'gip_event';
  payload: GlyphEvent;
}

type LogEntry =
  | { type: 'glyph'; data: GlyphEvent; action: string; source?: string }
  | { type: 'lean_theorem_executed'; action: string; source?: string };

type SoulLawEvent = {
  rule: string;
  passed: boolean;
  reason?: string;
};

type EntanglementEvent = {
  container: string;
  glyph: string;
  status: 'linked' | 'unlinked';
};

// ✅ Update type
type EventLog =
  | { type: 'glyph'; data: GlyphEvent }
  | { type: 'gip'; data: GlyphEvent }
  | { type: 'tick'; data: TickEvent }
  | { type: 'soullaw'; data: SoulLawEvent }
  | { type: 'entanglement'; data: EntanglementEvent }
  | { type: 'lean_theorem_executed'; action: string; source?: string };

// ✅ Add type guard
function hasAction(log: EventLog): log is (EventLog & { action: string }) {
  return "action" in log && typeof (log as any).action === "string";
}

const COST_WARNING_THRESHOLD = 7;

const OPERATOR_LABELS: Record<string, string> = {
  '⊕': 'AND',
  '↔': 'EQUIVALENCE',
  '→': 'TRIGGER',
  '⟲': 'MUTATE',
  '∇': 'COMPRESS',
  '⧖': 'DELAY',
  '✦': 'MILESTONE',
  '⟦ Theorem ⟧': 'LEAN THEOREM',
  '⬁': 'MUTATION',
  '⮁': 'SELF-REWRITE',
  '🧬': 'DNA TRIGGER',
  '🧭': 'GOAL TRIGGER',
  '🪞': 'REFLECTION',
  '⚖️': 'SOUL VERDICT'
};

const OPERATOR_COLORS: Record<string, string> = {
  '⊕': 'text-pink-400',
  '↔': 'text-purple-300',
  '→': 'text-green-400',
  '⟲': 'text-orange-300',
  '∇': 'text-blue-300',
  '⧖': 'text-yellow-500',
  '✦': 'text-cyan-300',
  '⟦ Theorem ⟧': 'text-sky-400',
  '⬁': 'text-pink-400',
  '⮁': 'text-pink-600',
  '🧬': 'text-green-400',
  '🧭': 'text-cyan-200',
  '🪞': 'text-gray-300',
  '⚖️': 'text-red-500'
};

function handleHoverNarration(glyph: string, action?: string, isMutated?: boolean) {
  if (glyph === '⮁') {
    playGlyphNarration("Self-rewriting mutation triggered.");
  } else if (glyph === '⬁') {
    playGlyphNarration("Genetic mutation executed.");
  } else if (glyph === '↔') {
    playGlyphNarration("Entangled glyph link activated.");
  } else if (glyph === '⚖️') {
    playGlyphNarration("SoulLaw verdict incoming.");
  } else if (glyph === '🧬') {
    playGlyphNarration("DNA trigger activated.");
  } else if (glyph === '🧭') {
    playGlyphNarration("Goal trigger reached.");
  } else if (glyph === '🪞') {
    playGlyphNarration("Reflective memory invoked.");
  } else {
    playGlyphNarration(`Glyph ${glyph} triggered ${action || 'an event'}.`);
  }
}

function extractOperator(glyph: string): string | null {
  if (glyph === '⟦ Theorem ⟧') return '⟦ Theorem ⟧';
  const matches = Object.keys(OPERATOR_LABELS).filter((op) => glyph.includes(op));
  return matches.length > 0 ? matches[0] : null;
}

function operatorName(op: string | null): string {
  return op ? OPERATOR_LABELS[op] || '' : '';
}

async function fetchScroll(glyph: string): Promise<string> {
  try {
    const res = await fetch('/api/build_scroll', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ glyph })
    });
    const data = await res.json();
    return data?.scroll || 'No scroll generated.';
  } catch (e) {
    return '⚠️ Failed to load scroll.';
  }
}

interface CodexHUDProps {
  onReplayToggle?: (state: boolean) => void;
  onTraceOverlayToggle?: (state: boolean) => void;
  onLayoutToggle?: () => void;
  onExport?: () => void;
  containerId?: string;
}

export default function CodexHUD({
  onReplayToggle,
  onTraceOverlayToggle,
  onLayoutToggle,
  onExport,
  containerId
}: CodexHUDProps) {
  const [events, setEvents] = useState<EventLog[]>([]);
  const [filter, setFilter] = useState('');
  const [scrolls, setScrolls] = useState<Record<string, string>>({});
  const [contextShown, setContextShown] = useState<Record<string, boolean>>({});
  const [isReplay, setIsReplay] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [gazeMode, setGazeMode] = useState(false);
  const { replays, latestTrace, handleReplayClick } = useGlyphReplay();
  const [showReplayPanel, setShowReplayPanel] = useState(false);

  const [showGHX, setShowGHX] = useState(true);
  const [qkdLocked, setQkdLocked] = useState(false);
  const [lastPattern, setLastPattern] = useState<string | null>(null);
  const { collapseHistory, decoherenceHistory, latestCollapse, latestDecoherence } = useCollapseMetrics();

  const wsUrl = "/ws/codex";
  const gipWsUrl = "/ws/glyphnet";

  // ✅ WebSocket connection (Codex + QKD + Pattern events)
  const { connected: codexConnected } = useWebSocket(
    wsUrl,
    (data: any) => {
      if (!isReplay) {
        if (data?.type === "glyph_execution") {
          setEvents((prev) => [
            { type: "glyph", data: data.payload },
            ...prev.slice(0, 100),
          ]);
        } else if (data?.type === "dimension_tick") {
          const tick: TickEvent = {
            type: "dimension_tick",
            container: data.container,
            timestamp: data.timestamp,
          };
          setEvents((prev) => [{ type: "tick", data: tick }, ...prev.slice(0, 100)]);
        } else if (data?.type === "soullaw_event") {
          const event: EventLog = {
            type: "soullaw",
            data: data.payload as SoulLawEvent,
          };
          setEvents((prev) => [event, ...prev.slice(0, 100)]);
        } else if (data?.type === "qkd_status") {
          setQkdLocked(data.locked);
        } else if (data?.type === "pattern_match") {
          setLastPattern(data.pattern_id || "Unknown Pattern");
        }
      }
    },
    ["glyph_execution", "dimension_tick", "soullaw_event", "qkd_status", "pattern_match"]
  );

  // ✅ Use in rendering
  const renderLogs = events.map((log, index) => {
    const isLeanGlyph =
      (log.type === 'glyph' && log.data.detail?.operator === '⟦ Theorem ⟧') ||
      log.type === 'lean_theorem_executed';

    return (
      <div key={index} className="text-green-400">
        {hasAction(log) ? log.action : ''}
      </div>
    );
  });

  const totalGlyphs = events.filter(
    (e) => e.type === 'glyph' || e.type === 'gip'
  ).length;

  const triggeredGlyphs = events.filter(
    (e) =>
      (e.type === 'glyph' || e.type === 'gip') &&
      (e as any).data?.action
  ).length;

  const { metrics } = useWaveTelemetry();

  const collapseRate = metrics.filter((m) => m.event === 'beam_emitted').length;

  const avgCoherence = (() => {
    const beamEvents = metrics.filter((m) => m.meta?.coherence !== undefined);
    return beamEvents.length
      ? (
          beamEvents.reduce(
            (sum, m) => sum + (m.meta?.coherence || 0),
            0
          ) / beamEvents.length
        ).toFixed(2)
      : '—';
  })();

  useEffect(() => {
    playGlyphNarration(
      `Loaded ${totalGlyphs} glyphs, ${triggeredGlyphs} triggered.`
    );
  }, [totalGlyphs, triggeredGlyphs]);

  const handleReplayToggle = () => {
    const newVal = !isReplay;
    setIsReplay(newVal);
    onReplayToggle?.(newVal);
    playGlyphNarration(newVal ? 'Replay started' : 'Replay paused');
  };

  const handleGazeToggle = () => {
    const newVal = !gazeMode;
    setGazeMode(newVal);
    onLayoutToggle?.();
    playGlyphNarration(newVal ? 'Gaze mode enabled' : 'Gaze mode disabled');
  };

  const handleExport = () => {
    playGlyphNarration('Exporting projection as GHX format.');
    onExport?.();
  };

  useWebSocket(
    wsUrl,
    (data: any) => {
      if (!isReplay) {
        if (data?.type === 'glyph_execution') {
          setEvents((prev: EventLog[]) => [
            { type: 'glyph', data: data.payload },
            ...prev.slice(0, 100),
          ]);
        } else if (data?.type === 'dimension_tick') {
          const tick: TickEvent = {
            type: 'dimension_tick',
            container: data.container,
            timestamp: data.timestamp,
          };
          setEvents((prev: EventLog[]) => [
            { type: 'tick', data: tick },
            ...prev.slice(0, 100),
          ]);
        } else if (data?.type === 'soullaw_event') {
          setEvents((prev: EventLog[]) => [
            { type: 'soullaw', data: data.payload as SoulLawEvent },
            ...prev.slice(0, 100),
          ]);
        }
      }
    },
    ['glyph_execution', 'dimension_tick', 'soullaw_event']
  );

  useWebSocket(
    gipWsUrl,
    (data: any) => {
      if (!isReplay) {
        if (data?.type === 'gip_event') {
          setEvents((prev: EventLog[]) => [
            { type: 'gip', data: data.payload },
            ...prev.slice(0, 100),
          ]);
        } else if (data?.type === 'entanglement_update') {
          setEvents((prev: EventLog[]) => [
            { type: 'entanglement', data: data.payload as EntanglementEvent },
            ...prev.slice(0, 100),
          ]);
        }
      }
    },
    ['gip_event', 'entanglement_update']
  );

  const filteredEvents = events.filter((e) => {
    if (e.type === 'glyph' || e.type === 'gip') {
      return (e.data as GlyphEvent).glyph
        ?.toLowerCase()
        .includes(filter.toLowerCase());
    }
    return true;
  });

  const toggleScroll = async (glyph: string) => {
    if (scrolls[glyph]) {
      const newScrolls = { ...scrolls };
      delete newScrolls[glyph];
      setScrolls(newScrolls);
    } else {
      const scroll = await fetchScroll(glyph);
      setScrolls((prev) => ({ ...prev, [glyph]: scroll }));
    }
  };

  const toggleContext = (glyph: string) => {
    setContextShown((prev) => ({ ...prev, [glyph]: !prev[glyph] }));
  };

  return (
    <div className="relative w-full h-full">
      {/* ✅ GHX + Collapse + Pattern HUD Overlay */}
      <div className="flex items-center justify-between px-4 py-2 text-sm bg-white/5 border-b border-white/10">
        {/* 🧠 Collapse Metrics */}
        <div className="flex space-x-4 text-xs text-gray-300">
          <span>🧠 Collapse/sec: {collapseRate}</span>
          <span>⧖ Decoherence: {latestDecoherence}</span>
          <span>📈 Coherence: {avgCoherence}</span>
        </div>

        {/* 🔐 QKD Lock + 🧬 Pattern Match */}
        <div className="flex items-center space-x-2">
          <Badge
            variant="outline"
            className={qkdLocked ? "text-green-400" : "text-red-400"}
          >
            {qkdLocked ? "QKD: Locked" : "QKD: Unlocked"}
          </Badge>

          {lastPattern && (
            <Badge variant="secondary" className="text-purple-300">
              🧬 Pattern: {lastPattern}
            </Badge>
          )}
        </div>
      </div>

      <Card className="w-full max-h-[450px] bg-black text-white border border-green-700 shadow-lg rounded-xl p-2 mt-4 relative">
        <CardContent>
          <ReplayHUD latestTrace={latestTrace} />

          {showReplayPanel && (
            <ReplayListPanel replays={replays} onReplayClick={handleReplayClick} />
          )}

          <div className="flex justify-between items-center mb-2">
            <h2 className="text-lg font-bold text-green-400">🧠 Codex Runtime HUD</h2>
            <span className="text-sm">
              Codex: {typeof codexConnected !== "undefined"
                ? codexConnected ? '🟢 Connected' : '🔴 Disconnected'
                : "❓ Unknown"}
            </span>
          </div>

          <div className="absolute top-2 right-2 z-50">
            <Button onClick={() => setShowReplayPanel(!showReplayPanel)}>
              🧪 {showReplayPanel ? 'Hide Replay' : 'Show Replay'}
            </Button>
          </div>

          <Button
            className="ml-2 text-xs px-2 py-0 h-6 bg-transparent hover:bg-white/10 border border-white/10"
            onClick={() => setShowGHX(!showGHX)}
          >
            {showGHX ? '🛑 Hide GHX' : '🌌 Show GHX'}
          </Button>

          <div className="flex items-center justify-between mb-2 gap-2">
            <Input
              placeholder="🔍 Filter glyphs..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="bg-gray-900 border-gray-700 text-white text-sm"
            />
            <div className="flex gap-2">
              <Button
                className="text-xs px-3 py-1 h-8 bg-purple-800 hover:bg-purple-700"
                onClick={handleReplayToggle}
              >
                {isReplay ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                <span className="ml-1">{isReplay ? "Pause" : "Replay"}</span>
              </Button>
              <Button
                className="text-xs px-3 py-1 h-8 bg-cyan-800 hover:bg-cyan-700"
                onClick={handleExport}
              >
                📀 Export GHX
              </Button>
              <Button
                className="text-xs px-3 py-1 h-8 bg-pink-800 hover:bg-pink-700"
                onClick={handleGazeToggle}
              >
                👁️ Gaze Mode: {gazeMode ? 'On' : 'Off'}
              </Button>
              <Button
                className="text-xs px-3 py-1 h-8 bg-yellow-800 hover:bg-yellow-700"
                onClick={() => setShowReplayPanel(!showReplayPanel)}
              >
                🎞️ Replay List
              </Button>
              <Button
                className="text-xs px-3 py-1 h-8 bg-gray-700 hover:bg-gray-600"
                onClick={() => onTraceOverlayToggle?.(!showTrace)}
              >
                🔍 Trace: {showTrace ? 'On' : 'Off'}
              </Button>
            </div>
          </div>

          {latestCollapse != null && latestDecoherence != null && (
            <div className="text-xs text-green-300 font-mono mt-2 border border-green-700 rounded p-2 bg-black/50">
              <div className="flex justify-between">
                <div>
                  🧠 <strong>Collapse Rate:</strong> {latestCollapse.toFixed(2)} / sec
                </div>
                <div>
                  🌀 <strong>Decoherence:</strong> {(latestDecoherence * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          )}

          <div className="text-xs p-2 bg-black/50 rounded-lg shadow mt-2">
            <div>📉 Collapse Rate: <strong>{collapseRate}/s</strong></div>
            <div>📡 Avg Coherence: <strong>{avgCoherence}</strong></div>
            {parseFloat(avgCoherence) < 0.5 && avgCoherence !== "—" && (
              <div className="text-red-500 animate-pulse">⚠️ Low Coherence Detected</div>
            )}
          </div>

          {/* 🔮 Real-Time Beam Predictions */}
          <div className="text-xs mt-2 bg-slate-900/80 border border-indigo-600 rounded-lg p-2 font-mono text-indigo-200 shadow-md">
            <div className="mb-1 text-indigo-300 font-semibold">🔮 Beam Prediction Metrics</div>
            {events.slice(0, 5).map((entry, idx) => {
              if (entry.type !== 'glyph' && entry.type !== 'gip') return null;
              const g = entry.data as GlyphEvent;
              if (!g.predicted) return null;
              return (
                <div key={`beam-pred-${idx}`} className="text-xs flex justify-between border-b border-white/10 py-1">
                  <span className="truncate">
                    ⟦ {g.glyph} ⟧ → <span className="text-green-400">{g.action}</span>
                  </span>
                  <span>
                    ↯ {g.entropy?.toFixed(2) ?? '—'} | 🎯 {g.confidence != null ? `${Math.round(g.confidence * 100)}%` : '—'}
                  </span>
                </div>
              );
            })}
          </div>

          {/* ✅ Draggable Scroll Panel */}
          {Object.keys(scrolls).length > 0 && (
            <div className="mt-4 p-2 border border-white/10 rounded bg-slate-800">
              <h3 className="text-sm font-bold text-green-400 mb-2">🧾 Active Scrolls</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(scrolls).map(([glyph, scroll]) => (
                  <div
                    key={glyph}
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData("application/glyph-scroll", JSON.stringify({ glyph, scroll }));
                      e.dataTransfer.effectAllowed = "move";
                    }}
                    className="p-2 border border-white/10 rounded bg-slate-900 cursor-grab hover:bg-slate-700 w-[200px] overflow-hidden"
                  >
                    <div className="text-green-300 font-mono text-xs mb-1 truncate">🧾 {glyph}</div>
                    <pre className="text-white text-xs whitespace-pre-wrap max-h-[120px] overflow-auto">{scroll}</pre>
                  </div>
                ))}
              </div>
            </div>
          )}

<ScrollArea className="h-[320px] pr-2 mt-2">
  {filteredEvents.map((entry, index) => {
    if (entry.type === "tick") {
      const { container, timestamp } = entry.data as TickEvent;
      return (
        <div
          key={`tick-${container}-${timestamp}`}
          className="border-b border-white/10 py-1"
        >
          <div className="text-sm text-cyan-300 font-mono">
            🧱 Tick from <b>{container}</b> at{" "}
            <span className="text-white">
              {timestamp
                ? new Date(timestamp * 1000).toLocaleTimeString()
                : "N/A"}
            </span>
          </div>
        </div>
      );
    }

    if (
      entry.type !== "glyph" &&
      entry.type !== "gip" &&
      entry.type !== "lean_theorem_executed"
    ) {
      return null;
    }

    const glyphData = (entry as any).data as GlyphEvent;
    const isCostly =
      glyphData?.cost != null && glyphData.cost > COST_WARNING_THRESHOLD;
    const costColor =
      glyphData?.cost == null
        ? ""
        : glyphData.cost > 9
        ? "text-red-500"
        : glyphData.cost > 7
        ? "text-orange-400"
        : glyphData.cost > 4
        ? "text-yellow-300"
        : "text-green-300";

    const operator = glyphData?.glyph
      ? extractOperator(glyphData.glyph)
      : null;
    const operatorLabel = operatorName(operator);
    const operatorColor = operator
      ? OPERATOR_COLORS[operator] || "text-white"
      : "text-white";

    const isLeanGlyph =
      operator === "⟦ Theorem ⟧" || entry.type === "lean_theorem_executed";
    const isEntangled =
      glyphData?.glyph?.includes("↔") || glyphData?.detail?.entangled_from;
    const isPredicted = glyphData?.predicted;
    const beamLabel = glyphData?.beamSource || "";
    const confidence = glyphData?.confidence;
    const entropy = glyphData?.entropy;

    const key = `${glyphData?.glyph || "unknown"}-${
      glyphData?.timestamp || index
    }`;

    return (
      <div
        key={key}
        className={`border-b border-white/10 py-1 ${
          isEntangled ? "bg-purple-900/10" : ""
        } hover:bg-slate-800 cursor-pointer`}
        onMouseEnter={() =>
          glyphData?.glyph &&
          handleHoverNarration(glyphData.glyph, glyphData.action)
        }
      >
        <div className={`text-sm font-mono ${operatorColor}`}>
          ⟦ {glyphData?.glyph || "???"} ⟧ →{" "}
          <span className="text-green-400">{glyphData?.action}</span>
          <span className={`ml-2 text-xs ${operatorColor}`}>
            {operatorLabel}
          </span>

          {isPredicted && (
            <span className="ml-1 text-xs text-sky-400">
              🔮 {beamLabel || "Predicted"}
              {typeof confidence === "number" && (
                <span className="ml-1 text-purple-300">
                  ({Math.round(confidence * 100)}%)
                </span>
              )}
              {typeof entropy === "number" && (
                <span className="ml-1 text-yellow-400">
                  ↯ {entropy.toFixed(2)}
                </span>
              )}
            </span>
          )}

          {isLeanGlyph && (
            <Badge className="ml-2" variant="outline">
              📘 Lean Theorem
            </Badge>
          )}
          {operator && !isLeanGlyph && (
            <Badge className="ml-2" variant="outline">
              {`${operator} ${operatorLabel}`}
            </Badge>
          )}
          {glyphData?.trigger_type && (
            <Badge className="ml-2" variant="secondary">
              🕒 {glyphData.trigger_type}
            </Badge>
          )}
          {glyphData?.replay_trace && (
            <Badge className="ml-2" variant="outline">
              🛰️ Replay
            </Badge>
          )}
          {glyphData?.collapse_trace && (
            <Badge className="ml-2" variant="outline">
              📦 Collapse Trace
            </Badge>
          )}
          {glyphData?.entangled_identity && (
            <Badge className="ml-2" variant="outline">
              ↔ Identity Link
            </Badge>
          )}
          {glyphData?.trace_id && (
            <Badge className="ml-2" variant="outline">
              🧩 Trace ID
            </Badge>
          )}
          {glyphData?.sqi && (
            <Badge className="ml-2" variant="outline">
              🌌 SQI
            </Badge>
          )}
          {isEntangled && (
            <Badge
              className="ml-2 bg-purple-800 border-purple-500 text-purple-100"
              variant="outline"
            >
              ↔ Entangled Cluster
            </Badge>
          )}
          {glyphData?.luxpush && (
            <Badge className="ml-2" variant="outline">
              🛰️ GlyphPush
            </Badge>
          )}
          {glyphData?.context && (
            <Badge className="ml-2" variant="outline">
              🧠 Context Preview
            </Badge>
          )}
          {isCostly && (
            <Badge className="ml-2" variant="destructive">
              ⚠️ High Cost
            </Badge>
          )}
          {glyphData?.token && glyphData?.identity && (
            <Badge className="ml-2" variant="outline">
              🔐 {glyphData.identity}
            </Badge>
          )}
        </div>

        <div className="text-xs text-white/60 flex justify-between">
          <span>{glyphData?.source || "Unknown Source"}</span>
          <span>
            {glyphData?.timestamp
              ? new Date(glyphData.timestamp * 1000).toLocaleTimeString()
              : "Unknown Time"}
          </span>
        </div>

        {glyphData?.glyph && (
          <div className="mt-1 flex gap-2">
            <Button
              className="text-xs px-2 py-0 h-6 bg-transparent hover:bg-white/10 border border-white/10"
              onClick={() => toggleScroll(glyphData.glyph)}
            >
              🧾 {scrolls[glyphData.glyph] ? "Hide" : "Show"} Scroll
            </Button>

            <Button
              className="text-xs px-2 py-0 h-6 bg-transparent hover:bg-white/10 border border-white/10"
              onClick={() => toggleContext(glyphData.glyph)}
            >
              🔍 {contextShown[glyphData.glyph] ? "Hide" : "Show"} Context
            </Button>
          </div>
        )}
      </div>
    );
  })}
</ScrollArea>

</CardContent>
</Card>

{/* ✅ GHX Visualizer Field */}
{showGHX && (
  <div className="fixed bottom-0 left-0 w-full bg-black/80 z-50">
    <GHXVisualizerField containerId={containerId ?? ""} />
  </div>
)}
</div>
);
}