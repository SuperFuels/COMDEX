// 📁 CodexHUD.tsx
// Visual HUD for CodexCore glyph execution, cost, and tick feedback

import React, { useEffect, useState } from 'react';
import useWebSocket from '@/hooks/useWebSocket';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface GlyphEvent {
  glyph: string;
  action: string;
  source: string;
  timestamp: number;
  cost?: number;
  trace_id?: string;
  trigger_type?: string;
  sqi?: boolean;
  detail?: {
    energy?: number;
    ethics_risk?: number;
    delay?: number;
    opportunity_loss?: number;
    coord?: string;
    container?: string;
    operator?: string;
  };
}

interface TickEvent {
  type: 'dimension_tick';
  container: string;
  timestamp: number;
}

type EventLog = { type: 'glyph'; data: GlyphEvent } | { type: 'tick'; data: TickEvent };

const COST_WARNING_THRESHOLD = 7;

const OPERATOR_LABELS: Record<string, string> = {
  '⊕': 'AND',
  '↔': 'EQUIVALENCE',
  '→': 'TRIGGER',
  '⟲': 'MUTATE',
  '∇': 'COMPRESS',
  '⧖': 'DELAY',
  '✦': 'MILESTONE'
};

const OPERATOR_COLORS: Record<string, string> = {
  '⊕': 'text-pink-400',
  '↔': 'text-purple-300',
  '→': 'text-green-400',
  '⟲': 'text-orange-300',
  '∇': 'text-blue-300',
  '⧖': 'text-yellow-500',
  '✦': 'text-cyan-300'
};

function extractOperator(glyph: string): string | null {
  return Object.keys(OPERATOR_LABELS).find((op) => glyph.includes(op)) || null;
}

function operatorName(op: string | null): string {
  return op ? OPERATOR_LABELS[op] || '' : '';
}

export default function CodexHUD() {
  const [events, setEvents] = useState<EventLog[]>([]);
  const [filter, setFilter] = useState('');

  const wsUrl = "/ws/codex"

  const { connected } = useWebSocket(
    wsUrl,
    (data) => {
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
    },
    ['glyph_execution', 'dimension_tick']
  );

  const filteredEvents = events.filter((e) =>
    e.type === 'glyph'
      ? e.data.glyph?.toLowerCase().includes(filter.toLowerCase())
      : true
  );

  return (
    <Card className="w-full max-h-[350px] bg-black text-white border border-green-700 shadow-lg rounded-xl p-2 mt-4">
      <CardContent>
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-lg font-bold text-green-400">🧠 Codex Runtime HUD</h2>
          <span className="text-sm">
            WebSocket: {connected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
        </div>

        <Input
          placeholder="🔍 Filter glyphs..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="mb-3 bg-gray-900 border-gray-700 text-white text-sm"
        />

        <ScrollArea className="h-[240px] pr-2">
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

            const key = `${log.glyph}-${log.timestamp || index}`;

            return (
              <div key={key} className="border-b border-white/10 py-1">
                <div className={`text-sm font-mono ${operatorColor}`}>
                  ⟦ {log.glyph} ⟧ → <span className="text-green-400">{log.action}</span>

                  {operator && (
                    <Badge variant="outline" className="ml-2">{operator} {operatorLabel}</Badge>
                  )}

                  {log.trigger_type && (
                    <Badge variant="secondary" className="ml-2">🕒 {log.trigger_type}</Badge>
                  )}

                  {log.trace_id && (
                    <Badge variant="outline" className="ml-2">🧩 Trace ID</Badge>
                  )}

                  {log.sqi && (
                    <Badge variant="outline" className="ml-2">🌌 SQI</Badge>
                  )}

                  {isCostly && (
                    <Badge variant="destructive" className="ml-2">⚠️ High Cost</Badge>
                  )}
                </div>

                <div className="text-xs text-white/60 flex justify-between">
                  <span>{log.source || 'Unknown Source'}</span>
                  <span>
                    {log.timestamp ? new Date(log.timestamp * 1000).toLocaleTimeString() : 'Unknown Time'}
                  </span>
                </div>

                {log.cost !== undefined && (
                  <div className={`text-xs mt-1 ${costColor}`}>
                    💰 Estimated Cost: <b>{log.cost.toFixed(2)}</b>
                    {log.detail && (
                      <div className="flex gap-2 mt-1 flex-wrap">
                        {log.detail.energy !== undefined && (
                          <Badge variant="outline">🔋 Energy: {log.detail.energy}</Badge>
                        )}
                        {log.detail.ethics_risk !== undefined && (
                          <Badge variant="outline">⚖️ Risk: {log.detail.ethics_risk}</Badge>
                        )}
                        {log.detail.delay !== undefined && (
                          <Badge variant="outline">⌛ Delay: {log.detail.delay}</Badge>
                        )}
                        {log.detail.opportunity_loss !== undefined && (
                          <Badge variant="outline">📉 Loss: {log.detail.opportunity_loss}</Badge>
                        )}
                        {log.detail.coord && (
                          <Badge variant="outline">📍 Coord: {log.detail.coord}</Badge>
                        )}
                        {log.detail.container && (
                          <Badge variant="outline">🧱 Container: {log.detail.container}</Badge>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}