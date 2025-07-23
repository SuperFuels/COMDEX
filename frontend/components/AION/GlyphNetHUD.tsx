'use client';

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
  meta?: {
    container?: string;
    priority?: string;
    [key: string]: any;
  };
}

export default function GlyphNetHUD() {
  const [events, setEvents] = useState<GlyphEvent[]>([]);
  const [filter, setFilter] = useState('');
  const [connected, setConnected] = useState(false);

  const wsUrl = '/ws/glyphnet';

  const { socket } = useWebSocket(
    wsUrl,
    (data) => {
      if (data?.glyph) {
        setEvents((prev) => [data as GlyphEvent, ...prev.slice(0, 100)]);
      }
    },
    [],
    () => {
      setConnected(true);
      // Optional default filter
      socket?.send(JSON.stringify({ subscribe: { symbol: '↔' } }));
    },
    () => setConnected(false)
  );

  const filteredEvents = events.filter((e) =>
    e.glyph?.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <Card className="w-full max-h-[450px] bg-black text-white border border-purple-700 shadow-lg rounded-xl p-2 mt-4">
      <CardContent>
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-lg font-bold text-purple-400">↔ GlyphNet HUD</h2>
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

        <ScrollArea className="h-[320px] pr-2">
          {filteredEvents.map((entry, index) => {
            const key = `${entry.glyph}-${entry.timestamp || index}`;
            const container = entry.meta?.container || 'unknown';
            const priority = entry.meta?.priority;

            return (
              <div key={key} className="border-b border-white/10 py-1">
                <div className="text-sm font-mono text-purple-300">
                  ⟦ {entry.glyph} ⟧ → <span className="text-green-400">{entry.action}</span>
                  {priority && (
                    <Badge className="ml-2" variant="outline">
                      🏷️ {priority}
                    </Badge>
                  )}
                  {container && (
                    <Badge className="ml-2" variant="outline">
                      🧱 {container}
                    </Badge>
                  )}
                </div>
                <div className="text-xs text-white/60 flex justify-between">
                  <span>{entry.source || 'Unknown Source'}</span>
                  <span>
                    {entry.timestamp
                      ? new Date(entry.timestamp * 1000).toLocaleTimeString()
                      : 'Unknown Time'}
                  </span>
                </div>
              </div>
            );
          })}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}