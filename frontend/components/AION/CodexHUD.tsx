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
  detail?: {
    energy?: number;
    ethics_risk?: number;
    delay?: number;
    opportunity_loss?: number;
  };
}

export default function CodexHUD() {
  const [events, setEvents] = useState<GlyphEvent[]>([]);
  const [filter, setFilter] = useState('');

  const { connected } = useWebSocket(
    'ws://localhost:8000/ws/codex',
    (data) => {
      if (data?.type === 'glyph_execution') {
        setEvents((prev) => [data.payload, ...prev.slice(0, 100)]);
      }
    },
    ['glyph_execution']
  );

  const filteredEvents = events.filter((e) =>
    e.glyph.toLowerCase().includes(filter.toLowerCase())
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
          {filteredEvents.map((log, index) => (
            <div key={index} className="border-b border-white/10 py-1">
              <div className="text-sm font-mono text-blue-300">
                ⟦ {log.glyph} ⟧ → <span className="text-green-400">{log.action}</span>
              </div>

              <div className="text-xs text-white/60 flex justify-between">
                <span>{log.source}</span>
                <span>{new Date(log.timestamp * 1000).toLocaleTimeString()}</span>
              </div>

              {log.cost !== undefined && (
                <div className="text-xs text-white/70 mt-1">
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
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}