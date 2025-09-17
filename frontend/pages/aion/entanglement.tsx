'use client';

import React, { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import type { EntangledNode, EntangledLink } from '@/components/codex/EntanglementGraph';

// Dynamically import the graph so it only runs client-side
const EntanglementGraph = dynamic(
  () => import('@/components/codex/EntanglementGraph'),
  { ssr: false }
);

interface Glyph {
  id: string;
  glyph: string;
  label?: string;
  entangled?: string[];
}

export default function EntanglementGraphPage() {
  const [glyphs, setGlyphs] = useState<Glyph[]>([]);
  const [graphData, setGraphData] = useState<{ nodes: EntangledNode[]; links: EntangledLink[] }>({
    nodes: [],
    links: [],
  });
  const [filter, setFilter] = useState('');
  const [liveMode, setLiveMode] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [step, setStep] = useState(0);
  const [wsRef, setWsRef] = useState<WebSocket | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Load collapse trace on mount
  useEffect(() => {
    fetch('/containers/seed_entangled.dc.json')
      .then((res) => res.json())
      .then((data) => {
        const g: Glyph[] = data.glyphs || [];
        setGlyphs(g);
        setStep(0);
        injectGlyphs(g.slice(0, 1));
      })
      .catch(() => {
        // ignore seed failure for now
      });
  }, []);

  // Live WebSocket Mode
  useEffect(() => {
    if (!liveMode) {
      wsRef?.close();
      setWsRef(null);
      return;
    }

    const ws = new WebSocket('ws://localhost:8000/ws/glyphnet');
    setWsRef(ws);
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'glyph') {
          injectGlyphs([msg.payload as Glyph], true);
        }
      } catch (err) {
        console.error('Invalid glyph message:', err);
      }
    };
    return () => ws.close();
  }, [liveMode]);

  // Replay mode autoplay
  useEffect(() => {
    if (!playing) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }
    intervalRef.current = setInterval(() => {
      stepForward();
    }, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [playing, step]); // step in deps keeps consistent progression

  const injectGlyphs = (glyphSlice: Glyph[], live = false) => {
    const nodeMap = new Map(graphData.nodes.map((n) => [n.id, n]));
    const linkSet = new Set(graphData.links.map((l) => `${l.source}-${l.target}`));
    const newNodes = [...graphData.nodes];
    const newLinks = [...graphData.links];

    for (const g of glyphSlice) {
      if (!nodeMap.has(g.id)) {
        newNodes.push({ id: g.id, label: g.label || g.glyph, glyph: g.glyph });
      }
      if (Array.isArray(g.entangled)) {
        for (const target of g.entangled) {
          const key = `${g.id}-${target}`;
          if (!linkSet.has(key)) {
            newLinks.push({ source: g.id, target, label: live ? 'Live' : undefined });
            linkSet.add(key);
          }
        }
      }
    }
    setGraphData({ nodes: newNodes, links: newLinks });
  };

  const stepForward = () => {
    if (step < glyphs.length) {
      const next = glyphs[step];
      injectGlyphs([next]);
      setStep((s) => s + 1);
    } else {
      setPlaying(false);
    }
  };

  const filtered =
    filter.trim().length > 0
      ? {
          nodes: graphData.nodes.filter((n) =>
            n.glyph.toLowerCase().includes(filter.toLowerCase())
          ),
          links: graphData.links.filter(
            (l) =>
              graphData.nodes.find(
                (n) => n.id === l.source && n.glyph.toLowerCase().includes(filter.toLowerCase())
              ) ||
              graphData.nodes.find(
                (n) => n.id === l.target && n.glyph.toLowerCase().includes(filter.toLowerCase())
              )
          ),
        }
      : graphData;

  return (
    <Card className="w-full h-[90vh] bg-black text-white mt-4">
      <CardContent className="w-full h-full p-2">
        <div className="flex justify-between items-center mb-2">
          <h2 className="text-green-400 text-lg font-bold">↔ Entanglement Graph</h2>
          <div className="flex gap-2 items-center">
            <Input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter glyphs..."
              className="bg-gray-900 border-gray-700 text-white text-sm"
            />
            <Button
              onClick={() => setStep(0)}
              className="text-xs bg-gray-700 hover:bg-gray-600"
            >
              ⏮️ Reset
            </Button>
            <Button
              onClick={stepForward}
              className="text-xs bg-gray-700 hover:bg-gray-600"
            >
              ⏭️ Step
            </Button>
            <Button
              onClick={() => setPlaying((p) => !p)}
              className="text-xs bg-purple-700 hover:bg-purple-600"
            >
              {playing ? '⏸️ Pause' : '▶️ Play'}
            </Button>
            <Button
              onClick={() => setLiveMode((v) => !v)}
              className={`text-xs ${
                liveMode
                  ? 'bg-red-600 hover:bg-red-500'
                  : 'bg-blue-600 hover:bg-blue-500'
              }`}
            >
              {liveMode ? '⛔ Stop Live' : '🛰️ Live'}
            </Button>
          </div>
        </div>
        <EntanglementGraph nodes={filtered.nodes} links={filtered.links} />
      </CardContent>
    </Card>
  );
}