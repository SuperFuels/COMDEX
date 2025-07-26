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

type EventLog =
  | { type: 'glyph'; data: GlyphEvent }
  | { type: 'tick'; data: TickEvent }
  | { type: 'gip'; data: GlyphEvent };

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
};

function extractOperator(glyph: string): string | null {
  if (glyph === '⟦ Theorem ⟧') return '⟦ Theorem ⟧';
  return Object.keys(OPERATOR_LABELS).find((op) => glyph.includes(op)) || null;
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

  const totalGlyphs = events.filter(e => e.type === 'glyph' || e.type === 'gip').length;
  const triggeredGlyphs = events.filter(e => (e.type === 'glyph' || e.type === 'gip') && e.data.action).length;

  useEffect(() => {
    playGlyphNarration(`Loaded ${totalGlyphs} glyphs, ${triggeredGlyphs} triggered.`);
  }, [totalGlyphs, triggeredGlyphs]);

  const handleReplayToggle = () => {
    const newVal = !isReplay;
    setIsReplay(newVal);
    onReplayToggle?.(newVal);
    playGlyphNarration(newVal ? "Replay started" : "Replay paused");
  };

  const handleTraceOverlayToggle = () => {
    const newVal = !showTrace;
    setShowTrace(newVal);
    onTraceOverlayToggle?.(newVal);
    playGlyphNarration(newVal ? "Trace overlay on" : "Trace overlay off");
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

  const handleHoverNarration = (glyph: string, action?: string) => {
    playGlyphNarration(`Glyph ${glyph} triggered ${action || 'an event'}.`);
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
        }
      }
    },
    ['glyph_execution', 'dimension_tick']
  );

  useWebSocket(
    gipWsUrl,
    (data) => {
      if (!isReplay && data?.type === 'gip_event') {
        setEvents((prev) => [{ type: 'gip', data: data.payload }, ...prev.slice(0, 100)]);
      }
    },
    ['gip_event']
  );

  const filteredEvents = events.filter((e) =>
    e.type === 'glyph' || e.type === 'gip'
      ? e.data.glyph?.toLowerCase().includes(filter.toLowerCase())
      : true
  );

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
    <Card className="w-full max-h-[450px] bg-black text-white border border-green-700 shadow-lg rounded-xl p-2 mt-4">
      <CardContent>
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-lg font-bold text-green-400">🧠 Codex Runtime HUD</h2>
          <span className="text-sm">
            Codex: {codexConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
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
              className="text-xs px-3 py-1 h-8 bg-gray-700 hover:bg-gray-600"
              onClick={handleTraceOverlayToggle}
            >
              🔍 Trace: {showTrace ? 'On' : 'Off'}
            </Button>
          </div>
        </div>

        <div className="text-xs text-purple-300 mt-2">
          🧠 Replay features enabled:
          <ul className="list-disc pl-4 space-y-1 mt-1">
            <li>↔ Entangled Glyphs</li>
            <li>⧖ Delay Badge</li>
            <li>🪞 Mirror Trails</li>
            <li>🛰️ GlyphPush Events</li>
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
                </div>
              );
            }

            const log = entry.data;
            const isCostly = log.cost !== undefined && log.cost > COST_WARNING_THRESHOLD;
            const costColor =
              log.cost === undefined ? '' :
              log.cost > 9 ? 'text-red-500' :
              log.cost > 7 ? 'text-orange-400' :
              log.cost > 4 ? 'text-yellow-300' : 'text-green-300';

            const operator = extractOperator(log.glyph);
            const operatorLabel = operatorName(operator);
            const operatorColor = operator ? OPERATOR_COLORS[operator] || 'text-white' : 'text-white';
            const isLeanGlyph = operator === '⟦ Theorem ⟧' || log.type === 'lean_theorem_executed';
            const isEntangled = log.glyph.includes('↔') || log.detail?.entangled_from;

            const key = `${log.glyph}-${log.timestamp || index}`;

            return (
              <div
                key={key}
                className={`border-b border-white/10 py-1 ${isEntangled ? 'bg-purple-900/10' : ''} hover:bg-slate-800 cursor-pointer`}
                onMouseEnter={() => handleHoverNarration(log.glyph, log.action)}
              >
                <div className={`text-sm font-mono ${operatorColor}`}>
                  ⟦ {log.glyph} ⟧ → <span className="text-green-400">{log.action}</span>

                  {isLeanGlyph && <Badge className="ml-2" variant="outline">📘 Lean Theorem</Badge>}
                  {operator && !isLeanGlyph && <Badge className="ml-2" variant="outline">{`${operator} ${operatorLabel}`}</Badge>}
                  {log.trigger_type && <Badge className="ml-2" variant="secondary">🕒 {log.trigger_type}</Badge>}
                  {log.replay_trace && <Badge className="ml-2" variant="outline">🛰️ Replay</Badge>}
                  {log.collapse_trace && <Badge className="ml-2" variant="outline">📦 Collapse Trace</Badge>}
                  {log.entangled_identity && <Badge className="ml-2" variant="outline">↔ Identity Link</Badge>}
                  {log.trace_id && <Badge className="ml-2" variant="outline">🧩 Trace ID</Badge>}
                  {log.sqi && <Badge className="ml-2" variant="outline">🌌 SQI</Badge>}
                  {isEntangled && <Badge className="ml-2" variant="outline">↔ Entangled</Badge>}
                  {log.luxpush && <Badge className="ml-2" variant="outline">🛰️ GlyphPush</Badge>}
                  {log.context && <Badge className="ml-2" variant="outline">🧠 Context Preview</Badge>}
                  {isCostly && <Badge className="ml-2" variant="destructive">⚠️ High Cost</Badge>}
                  {log.token && log.identity && <Badge className="ml-2" variant="outline">🔐 {log.identity}</Badge>}

                  <Button className="ml-2 text-xs px-2 py-0 h-6 bg-transparent hover:bg-white/10 border border-white/10" onClick={() => toggleScroll(log.glyph)}>
                    🧾 {scrolls[log.glyph] ? 'Hide' : 'Show'} Scroll
                  </Button>

                  <Button className="ml-2 text-xs px-2 py-0 h-6 bg-transparent hover:bg-white/10 border border-white/10" onClick={() => toggleContext(log.glyph)}>
                    🔍 {contextShown[log.glyph] ? 'Hide' : 'Show'} Context
                  </Button>
                </div>

                <div className="text-xs text-white/60 flex justify-between">
                  <span>{log.source || 'Unknown Source'}</span>
                  <span>{log.timestamp ? new Date(log.timestamp * 1000).toLocaleTimeString() : 'Unknown Time'}</span>
                </div>

                {log.cost !== undefined && (
                  <div className={`text-xs mt-1 ${costColor}`}>
                    💰 Estimated Cost: <b>{log.cost.toFixed(2)}</b>
                    {log.detail && (
                      <div className="flex gap-2 mt-1 flex-wrap">
                        {log.detail.energy !== undefined && (<Badge variant="outline">🔋 Energy: {log.detail.energy}</Badge>)}
                        {log.detail.ethics_risk !== undefined && (<Badge variant="outline">⚖️ Risk: {log.detail.ethics_risk}</Badge>)}
                        {log.detail.delay !== undefined && (<Badge variant="outline">⌛ Delay: {log.detail.delay}</Badge>)}
                        {log.detail.opportunity_loss !== undefined && (<Badge variant="outline">📉 Loss: {log.detail.opportunity_loss}</Badge>)}
                        {log.detail.coord && (<Badge variant="outline">📍 Coord: {log.detail.coord}</Badge>)}
                        {log.detail.container && (<Badge variant="outline">🧱 Container: {log.detail.container}</Badge>)}
                        {log.detail.entangled_from && (<Badge variant="outline">🪞 Forked from: {log.detail.entangled_from}</Badge>)}
                        {log.detail.qglyph_id && (<Badge variant="outline">🧬 QGlyph ID: {log.detail.qglyph_id}</Badge>)}
                        {log.detail.qglyph_paths && (<Badge variant="outline">↔ Paths: {log.detail.qglyph_paths[0]} / {log.detail.qglyph_paths[1]}</Badge>)}
                        {log.detail.bias_score !== undefined && (<Badge variant="outline">🎯 Bias Score: {log.detail.bias_score}</Badge>)}
                        {log.detail.observer_trace && (<Badge variant="outline">👁️ Trace: {log.detail.observer_trace}</Badge>)}
                        {log.detail.collapsed_path && (<Badge variant="outline">🪞 Forked Path: {log.detail.collapsed_path}</Badge>)}
                      </div>
                    )}
                  </div>
                )}

                {scrolls[log.glyph] && (
                  <pre className="bg-gray-800 text-green-300 text-xs mt-2 p-2 rounded max-h-40 overflow-auto whitespace-pre-wrap border border-green-800">
                    {scrolls[log.glyph]}
                  </pre>
                )}

                {contextShown[log.glyph] && log.context && (
                  <pre className="bg-gray-900 text-purple-300 text-xs mt-2 p-2 rounded max-h-32 overflow-auto whitespace-pre-wrap border border-purple-800">
                    {log.context}
                  </pre>
                )}
              </div>
            );
          })}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}