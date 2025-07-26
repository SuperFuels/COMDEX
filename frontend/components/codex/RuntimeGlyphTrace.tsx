import React, { useState, useEffect } from 'react';
import useWebSocket from '@/hooks/useWebSocket';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

type TraceEntry = {
  tick: number;
  glyph: string;
  coord: string;
  containerId: string;
  event: 'inflate' | 'collapse' | 'entangle' | 'mutate';
  timestamp: number;
};

const glyphEventMap: Record<string, TraceEntry['event']> = {
  '⧖': 'inflate',
  '↔': 'entangle',
  '⬁': 'mutate',
  '⛒': 'collapse'
};

const eventColor: Record<TraceEntry['event'], string> = {
  inflate: 'text-green-400',
  collapse: 'text-gray-500 italic',
  entangle: 'text-purple-400 font-bold',
  mutate: 'text-yellow-300'
};

export default function RuntimeGlyphTrace() {
  const [trace, setTrace] = useState<TraceEntry[]>([]);

  useWebSocket('/ws/codex', (event: MessageEvent) => {
    try {
      const msg = JSON.parse(event.data);

      // 🔍 Main glyph execution trace
      if (msg.type === 'glyph_execution') {
        const { glyph, coord, tick, containerId, timestamp } = msg.data;
        const matched = glyph.split('').find((g: string) => g in glyphEventMap);
        if (!matched) return;

        const newEntry: TraceEntry = {
          tick,
          glyph,
          coord,
          containerId,
          timestamp,
          event: glyphEventMap[matched]
        };

        setTrace(prev => [newEntry, ...prev].slice(0, 100));

        // ⧖ Hoberman Sphere trigger
        if (matched === '⧖') {
          window.dispatchEvent(new CustomEvent('inflate-hoberman', {
            detail: { containerId, coord }
          }));
        }

        // ↔ Entanglement WebSocket sync trigger
        if (matched === '↔') {
          window.dispatchEvent(new CustomEvent('entangle-graph-update', {
            detail: { containerId, coord }
          }));
        }
      }

      // Optional: Future entanglement status broadcast
      if (msg.type === 'entanglement_status') {
        // You could add logic here to update a separate entanglement status display
        // console.log("↔ Entanglement status received:", msg.data);
      }

    } catch (e) {
      console.warn('Invalid glyph trace payload:', e);
    }
  });

  return (
    <div className="w-full max-h-80 overflow-auto border border-neutral-700 rounded-md p-2 mt-4 bg-black/40">
      <h2 className="text-xl font-mono text-blue-300 mb-2">🧬 Runtime Glyph Trace</h2>
      {trace.length === 0 && (
        <div className="text-sm text-neutral-400">No glyph activity detected yet...</div>
      )}
      <ul className="space-y-1 font-mono text-sm">
        {trace.map((entry, idx) => (
          <motion.li
            key={idx}
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className={cn('flex justify-between items-center', eventColor[entry.event])}
          >
            <span>
              <b>{entry.glyph}</b> at <code>{entry.coord}</code> →{' '}
              {entry.event === 'entangle' && <span className="ml-1">↔ Entangled</span>}
              {entry.event === 'inflate' && <span className="ml-1">⧖ Inflation</span>}
              {entry.event === 'mutate' && <span className="ml-1">⬁ Mutation</span>}
              {entry.event === 'collapse' && <span className="ml-1">⛒ Collapse</span>}
            </span>
            <span className="text-neutral-400">t{entry.tick}</span>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}