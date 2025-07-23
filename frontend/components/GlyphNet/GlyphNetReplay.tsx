'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

interface GlyphLog {
  timestamp: number;
  glyph: string;
  source: string;
  action: string;
  detail?: Record<string, any>;
}

export default function GlyphNetReplay() {
  const [logs, setLogs] = useState<GlyphLog[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/glyphnet/logs');
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (e) {
      console.error('Failed to fetch logs', e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <Card className="bg-black text-white border border-blue-700 shadow-lg rounded-xl mt-4 p-2">
      <CardContent>
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-lg font-bold text-blue-400">📜 GlyphNet Replay Log</h2>
          <Button onClick={fetchLogs} disabled={loading} className="text-xs bg-blue-700 hover:bg-blue-600">
            🔄 Refresh
          </Button>
        </div>

        <ScrollArea className="h-[350px] pr-2">
          {logs.length === 0 ? (
            <div className="text-sm text-white/60">No logs found.</div>
          ) : (
            logs.map((log, idx) => (
              <div key={idx} className="border-b border-white/10 py-1">
                <div className="text-sm font-mono">
                  ⟦ <span className="text-green-300">{log.glyph}</span> ⟧ →{' '}
                  <span className="text-cyan-400">{log.action}</span>
                </div>
                <div className="text-xs text-white/60 flex justify-between">
                  <span>📡 {log.source || 'Unknown'}</span>
                  <span>
                    {log.timestamp ? new Date(log.timestamp * 1000).toLocaleTimeString() : 'N/A'}
                  </span>
                </div>
                {log.detail && (
                  <div className="flex gap-2 flex-wrap mt-1">
                    {Object.entries(log.detail).map(([k, v]) => (
                      <Badge key={k} variant="outline" className="text-xs">
                        {k}: {String(v)}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}