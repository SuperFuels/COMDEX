import React, { useEffect, useState } from 'react';
import useWebSocket from '@/hooks/useWebSocket';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Play, Pause, Download, Eye, EyeOff } from 'lucide-react';
import { playGlyphNarration } from "@/utils/hologram_audio";
import axios from "axios";
import { useGlyphReplay } from "@/hooks/useGlyphReplay";
import { ReplayHUD } from "@/components/CodexHUD/ReplayHUD";
import { ReplayListPanel } from "@/components/CodexHUD/ReplayListPanel";
import { useCollapseMetrics } from "@/hooks/useCollapseMetrics";
import { useWaveTelemetry } from "@/hooks/useWaveTelemetry";

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

  // 🧠 Prediction metadata (NEW)
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

// ✅ Update type
type EventLog =
  | { type: 'glyph'; data: GlyphEvent }
  | { type: 'gip'; data: GlyphEvent }
  | { type: 'tick'; data: TickEvent }
  | { type: 'soullaw'; data: SoulLawEvent }
  | { type: 'entanglement'; data: EntanglementEvent }
  | { type: 'lean_theorem_executed'; action: string; source?: string };

// ✅ Add type guard (if needed)
function hasAction(log: EventLog): log is { action: string } {
  return 'action' in log && typeof log.action === 'string';
}

// ✅ Use in rendering
const isLeanGlyph =
  operator === '⟦ Theorem ⟧' || log.type === 'lean_theorem_executed';

<span className="text-green-400">
  {hasAction(log) ? log.action : ''}
</span>

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
  '⬁': 'MUTATION',          // DNA mutation
  '⮁': 'SELF-REWRITE',      // full self-rewriting
  '🧬': 'DNA TRIGGER',       // codon-based trigger
  '🧭': 'GOAL TRIGGER',      // milestone → goal
  '🪞': 'REFLECTION',        // memory mirroring
  '⚖️': 'SOUL VERDICT'       // symbolic SoulLaw trigger
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
  '⬁': 'text-pink-400',        // mutation color
  '⮁': 'text-pink-600',        // deeper pink for full rewrite
  '🧬': 'text-green-400',       // DNA
  '🧭': 'text-cyan-200',        // goal marker
  '🪞': 'text-gray-300',        // reflection logic
  '⚖️': 'text-red-500'         // SoulLaw violation
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
}

interface SoulLawEvent {
  rule: string;
  passed: boolean;
  reason?: string;
}

interface EntanglementEvent {
  container: string;
  glyph: string;
  status: 'linked' | 'unlinked';
}

export default function CodexHUD({
  onReplayToggle,
  onTraceOverlayToggle,
  onLayoutToggle,
  onExport
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

  // ✅ Add collapse metrics hook here
  const {
    collapseHistory,
    decoherenceHistory,
    latestCollapse,
    latestDecoherence
  } = useCollapseMetrics();

  const totalGlyphs = events.filter(e => e.type === 'glyph' || e.type === 'gip').length;
  const triggeredGlyphs = events.filter(e => (e.type === 'glyph' || e.type === 'gip') && e.data.action).length;

  const { metrics } = useWaveTelemetry();

  const collapseRate = metrics.filter(m => m.event === "beam_emitted").length;

  const avgCoherence = (() => {
    const beamEvents = metrics.filter(m => m.meta?.coherence !== undefined);
    return beamEvents.length
      ? (beamEvents.reduce((sum, m) => sum + (m.meta.coherence || 0), 0) / beamEvents.length).toFixed(2)
      : "—";
  })();
  useEffect(() => {
    playGlyphNarration(`Loaded ${totalGlyphs} glyphs, ${triggeredGlyphs} triggered.`);
  }, [totalGlyphs, triggeredGlyphs]);

  const handleReplayToggle = () => {
    const newVal = !isReplay;
    setIsReplay(newVal);
    onReplayToggle?.(newVal);
    playGlyphNarration(newVal ? "Replay started" : "Replay paused");
  };

  const handleGazeToggle = () => {
    const newVal = !gazeMode;
    setGazeMode(newVal);
    onLayoutToggle?.();
    playGlyphNarration(newVal ? "Gaze mode enabled" : "Gaze mode disabled");
  };

  const handleExport = () => {
    playGlyphNarration("Exporting projection as GHX format.");
    onExport?.();
  };

  const handleHoverNarration = (glyph: string, action?: string, isMutated?: boolean) => {
    if (isMutated) {
      playGlyphNarration("Self-rewriting mutation detected.");
    } else {
      playGlyphNarration(`Glyph ${glyph} triggered ${action || 'an event'}.`);
    }
  };

  const wsUrl = "/ws/codex";
  const gipWsUrl = "/ws/glyphnet";

 const { connected: codexConnected } = useWebSocket(
    wsUrl,
    (data) => {
      if (!isReplay) {
        if (data?.type === 'glyph_execution') {
          setEvents((prev) => [{ type: 'glyph', data: data.payload }, ...prev.slice(0, 100)]);
        } else if (data?.type === 'dimension_tick') {
          const tick: TickEvent = {
            type: 'dimension_tick',
            container: data.container,
            timestamp: data.timestamp
          };
          setEvents((prev) => [{ type: 'tick', data: tick }, ...prev.slice(0, 100)]);
        } else if (data?.type === 'soullaw_event') {
          const event: EventLog = {
            type: 'soullaw',
            data: data.payload as SoulLawEvent
          };
          setEvents((prev) => [event, ...prev.slice(0, 100)]);
        }
      }
    },
    ['glyph_execution', 'dimension_tick', 'soullaw_event']
  );

  useWebSocket(
    gipWsUrl,
    (data) => {
      if (!isReplay) {
        if (data?.type === 'gip_event') {
          setEvents((prev) => [{ type: 'gip', data: data.payload }, ...prev.slice(0, 100)]);
        } else if (data?.type === 'entanglement_update') {
          const event: EventLog = {
            type: 'entanglement',
            data: data.payload as EntanglementEvent
          };
          setEvents((prev) => [event, ...prev.slice(0, 100)]);
        }
      }
    },
    ['gip_event', 'entanglement_update']
  );

  const filteredEvents = events.filter((e) => {
    if (e.type === 'glyph' || e.type === 'gip') {
      return e.data.glyph?.toLowerCase().includes(filter.toLowerCase());
    }
    return true; // allow soullaw, entanglement, etc. to pass
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
  <Card className="w-full max-h-[450px] bg-black text-white border border-green-700 shadow-lg rounded-xl p-2 mt-4 relative">
    <CardContent>

      <ReplayHUD latestTrace={latestTrace} />

      {showReplayPanel && (
        <ReplayListPanel replays={replays} onReplayClick={handleReplayClick} />
      )}

      <div className="flex justify-between items-center mb-2">
        <h2 className="text-lg font-bold text-green-400">🧠 Codex Runtime HUD</h2>
        <span className="text-sm">
          Codex: {codexConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </span>
      </div>

      <div className="absolute top-2 right-2 z-50">
        <Button onClick={() => setShowReplayPanel(!showReplayPanel)}>
          🧪 {showReplayPanel ? 'Hide Replay' : 'Show Replay'}
        </Button>
      </div>

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
            onClick={onTraceOverlayToggle}
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
      <div className="text-xs text-purple-300 mt-2">
        🧠 Replay features enabled:
        <ul className="list-disc pl-4 space-y-1 mt-1">
          <li>↔ Entangled Glyphs</li>
          <li>⧖ Delay Badge</li>
          <li>🪞 Mirror Trails</li>
          <li>🛰️ GlyphPush Events</li>
          <li>⬁ Mutation Badge</li>
          <li>🧬 DNA Trigger</li>
          <li>⮁ Self-Rewrite Trigger</li>
        </ul>
      </div>

      <ScrollArea className="h-[320px] pr-2 mt-2">
        {filteredEvents.map((entry, index) => {
          if (entry.type === 'tick') {
            const { container, timestamp } = entry.data;
            return (
              <div key={`tick-${container}-${timestamp}`} className="border-b border-white/10 py-1">
                <div className="text-sm text-cyan-300 font-mono">
                  🧱 Tick from <b>{container}</b> at{' '}
                  <span className="text-white">
                    {timestamp ? new Date(timestamp * 1000).toLocaleTimeString() : 'N/A'}
                  </span>
                </div>
              {/* 🔁 Suggested Rewrite Panel */}
              {glyph?.suggested_rewrite && (
                <div className="mt-1 ml-2 border border-dashed border-yellow-600 p-2 rounded bg-yellow-900/20 text-yellow-200 text-xs font-mono">
                  <div className="mb-1 font-bold text-yellow-300">🔁 Suggested Rewrite</div>
                  <div>
                    <b>New Glyph:</b> <code>{glyph.suggested_rewrite.new_glyph}</code>
                  </div>
                  <div>
                    <b>Goal Match Score:</b>{' '}
                    {glyph.suggested_rewrite.goal_match_score != null
                      ? glyph.suggested_rewrite.goal_match_score.toFixed(2)
                      : 'N/A'}
                  </div>
                  <div>
                    <b>Rewrite Success Probability:</b>{' '}
                    {glyph.suggested_rewrite.rewrite_success_prob != null
                      ? `${Math.round(glyph.suggested_rewrite.rewrite_success_prob * 100)}%`
                      : 'N/A'}
                  </div>
                  {glyph.suggested_rewrite.reason && (
                    <div>
                      <b>Reason:</b> <span>{glyph.suggested_rewrite.reason}</span>
                    </div>
                  )}
                </div>
              )}
              </div>
            );
          }

          const log = entry.data;

          if (!('glyph' in log)) return null; // skip non-GlyphEvents

        events.map((log, index) => {
  if (log.type !== 'glyph' || !log.data) return null;

  const glyphData = log.data as GlyphEvent;

  const isCostly = glyphData.cost !== undefined && glyphData.cost > COST_WARNING_THRESHOLD;
  const costColor =
    glyphData.cost === undefined ? '' :
    glyphData.cost > 9 ? 'text-red-500' :
    glyphData.cost > 7 ? 'text-orange-400' :
    glyphData.cost > 4 ? 'text-yellow-300' : 'text-green-300';

  const operator = extractOperator(glyphData.glyph);
  const operatorLabel = operatorName(operator);
  const operatorColor = operator ? OPERATOR_COLORS[operator] || 'text-white' : 'text-white';

  const isGlyphLog = log.type === 'glyph';
  const glyph = isGlyphLog ? log.data : null;

  const isLeanGlyph =
    operator === '⟦ Theorem ⟧' || log.type === 'lean_theorem_executed';

  const isEntangled =
    glyph?.glyph?.includes('↔') || glyph?.detail?.entangled_from;

  const isPredicted = glyph?.predicted;
  const beamLabel = glyph?.beamSource || '';
  const confidence = glyph?.confidence;
  const entropy = glyph?.entropy;

  const key = `${glyph?.glyph || 'unknown'}-${glyph?.timestamp || index}`;

  return (
    <div
      key={key}
      className={`border-b border-white/10 py-1 ${
        isEntangled ? 'bg-purple-900/10' : ''
      } hover:bg-slate-800 cursor-pointer`}
      onMouseEnter={() =>
        glyph?.glyph && handleHoverNarration(glyph.glyph, glyph.action)
      }
    >
      <div className={`text-sm font-mono ${operatorColor}`}>
        ⟦ {glyph?.glyph || '???'} ⟧ →{' '}
        {/* 🌟 Highlight symbolic operator if matched */}
        {['⧖', '↔', '⬁', '🧬', '🪞'].some((op) => glyph?.glyph?.includes(op)) && (
          <span className="ml-2 text-lg font-bold animate-pulse text-pink-400">
            {glyph.glyph.match(/[⧖↔⬁🧬🪞]/)?.[0]} Operator
          </span>
        )}
        <span className="text-green-400">{glyph?.action || log.action}</span>

        {/* 🔮 Beam Prediction Badge */}
        <span className={`text-xs ${operatorColor}`}>{operatorLabel}</span>

        {isPredicted && (
          <span className="ml-1 text-xs text-sky-400">
            🔮 {beamLabel || 'Predicted'}
            {typeof confidence === 'number' && (
              <span className="ml-1 text-purple-300">
                ({Math.round(confidence * 100)}%)
              </span>
            )}
            {typeof entropy === 'number' && (
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
        {glyph?.trigger_type && (
          <Badge className="ml-2" variant="secondary">
            🕒 {glyph.trigger_type}
          </Badge>
        )}
        {glyph?.replay_trace && (
          <Badge className="ml-2" variant="outline">
            🛰️ Replay
          </Badge>
        )}
        {glyph?.collapse_trace && (
          <Badge className="ml-2" variant="outline">
            📦 Collapse Trace
          </Badge>
        )}
        {glyph?.entangled_identity && (
          <Badge className="ml-2" variant="outline">
            ↔ Identity Link
          </Badge>
        )}
        {glyph?.trace_id && (
          <Badge className="ml-2" variant="outline">
            🧩 Trace ID
          </Badge>
        )}
        {glyph?.sqi && (
          <Badge className="ml-2" variant="outline">
            🌌 SQI
          </Badge>
        )}
        {isEntangled && (
          <Badge className="ml-2 bg-purple-800 border-purple-500 text-purple-100" variant="outline">
            ↔ Entangled Cluster
          </Badge>
        )}
        {glyph?.luxpush && (
          <Badge className="ml-2" variant="outline">
            🛰️ GlyphPush
          </Badge>
        )}
        {glyph?.context && (
          <Badge className="ml-2" variant="outline">
            🧠 Context Preview
          </Badge>
        )}
        {isCostly && (
          <Badge className="ml-2" variant="destructive">
            ⚠️ High Cost
          </Badge>
        )}
        {glyph?.token && glyph?.identity && (
          <Badge className="ml-2" variant="outline">
            🔐 {glyph.identity}
          </Badge>
        )}
        {glyph?.prediction_result && (
          <Badge className="ml-2" variant="outline">
            📈 Prediction: {glyph.prediction_result.outcome || 'N/A'} (
            {glyph.prediction_result.confidence != null
              ? `${Math.round(glyph.prediction_result.confidence * 100)}%`
              : '...'}
            )
          </Badge>
        )}

        {/* Buttons */}
        {glyph?.glyph && (
          <>
            <Button
              className="ml-2 text-xs px-2 py-0 h-6 bg-transparent hover:bg-white/10 border border-white/10"
              onClick={() => toggleScroll(glyph.glyph)}
            >
              🧾 {scrolls[glyph.glyph] ? 'Hide' : 'Show'} Scroll
            </Button>

            <Button
              className="ml-2 text-xs px-2 py-0 h-6 bg-transparent hover:bg-white/10 border border-white/10"
              onClick={() => toggleContext(glyph.glyph)}
            >
              🔍 {contextShown[glyph.glyph] ? 'Hide' : 'Show'} Context
            </Button>
          </>
        )}
      </div>

      <div className="text-xs text-white/60 flex justify-between">
        <span>{glyph?.source || log.source || 'Unknown Source'}</span>
        <span>
          {glyph?.timestamp
            ? new Date(glyph.timestamp * 1000).toLocaleTimeString()
            : 'Unknown Time'}
        </span>
      </div>
    </div>
  );