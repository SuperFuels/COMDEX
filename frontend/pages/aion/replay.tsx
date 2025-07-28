// frontend/pages/aion/replay.tsx

import React, { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import useWebSocket from '@/hooks/useWebSocket';

// Dynamically import 3D graph
const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), { ssr: false });

// @ts-ignore
import * as THREE from 'three';

interface Node {
  id: string;
  label: string;
  glyph: string;
  tick?: number;
  entangled?: string[];
}

interface Link {
  source: string;
  target: string;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
}

export default function ReplayEntanglementPage() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [filter, setFilter] = useState('');
  const [mode, setMode] = useState<'replay' | 'live'>('replay');
  const [step, setStep] = useState(0);
  const allGlyphsRef = useRef<any[]>([]);
  const fgRef = useRef<any>();

  // 🛰️ WebSocket Live + Replay Mode Listener
  useWebSocket(
    '/ws/codex',
    (data) => {
      if (mode === 'live' && data?.type === 'glyph_execution') {
        const glyph = data.payload?.glyph;
        const from = data.payload?.detail?.entangled_from;
        const id = `${glyph}-${data.payload.timestamp}`;
        const sourceId = from || 'root';

        setGraphData((prev) => {
          const nodes = [...prev.nodes];
          const links = [...prev.links];

          if (!nodes.find((n) => n.id === id)) {
            nodes.push({ id, label: glyph, glyph, tick: data.payload?.tick });
          }
          if (from && !nodes.find((n) => n.id === sourceId)) {
            nodes.push({ id: sourceId, label: from, glyph: from });
          }
          if (from && !links.find((l) => l.source === sourceId && l.target === id)) {
            links.push({ source: sourceId, target: id });
          }

          return { nodes, links };
        });
      }

      // 🎞️ Glyph Replay WebSocket Event
      if (data?.type === 'glyph_replay') {
        const { glyphs, links, tick_range } = data.payload;
        allGlyphsRef.current = glyphs;
        setGraphData({ nodes: glyphs, links });
        console.log(`🎞️ Replay tick range: ${tick_range.start} → ${tick_range.end}`);
        setStep(glyphs.length); // Jump to final replay state
      }
    },
    ['glyph_execution', 'glyph_replay']
  );

  // 🧪 Replay mode loader
  useEffect(() => {
    if (mode !== 'replay') return;
    fetch('/containers/seed_entangled.dc.json')
      .then((res) => res.json())
      .then((data) => {
        allGlyphsRef.current = data.glyphs;
        setStep(1);
      });
  }, [mode]);

  // 🧪 Step through glyphs in replay
  useEffect(() => {
    if (mode !== 'replay' || step <= 0) return;
    const glyphs = allGlyphsRef.current.slice(0, step);
    const nodes = glyphs.map((g: any) => ({
      id: g.id,
      label: g.label,
      glyph: g.glyph,
      tick: g.tick,
      entangled: g.entangled || [],
    }));
    const links: Link[] = [];
    glyphs.forEach((g: any) => {
      if (g.entangled) {
        g.entangled.forEach((targetId: string) => {
          links.push({ source: g.id, target: targetId });
        });
      }
    });
    setGraphData({ nodes, links });
  }, [step, mode]);

  // 🔍 Glyph filter
  const filtered = filter
    ? {
        nodes: graphData.nodes.filter((n) => n.glyph.toLowerCase().includes(filter.toLowerCase())),
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
          <h2 className="text-purple-400 text-lg font-bold">🌌 Entanglement Graph 3D</h2>
          <div className="flex gap-2 items-center">
            <Input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter glyphs..."
              className="bg-gray-900 border-gray-700 text-white text-sm"
            />
            <Button
              onClick={() => fgRef.current?.zoomToFit(400)}
              className="bg-purple-700 hover:bg-purple-600 text-xs px-3 py-1"
            >
              🎯 Fit View
            </Button>
            <Button
              onClick={() => setMode(mode === 'replay' ? 'live' : 'replay')}
              className="bg-blue-700 hover:bg-blue-600 text-xs px-3 py-1"
            >
              🔄 {mode === 'replay' ? 'Switch to Live' : 'Switch to Replay'}
            </Button>
            {mode === 'replay' && (
              <Button
                onClick={() => setStep((s) => Math.min(s + 1, allGlyphsRef.current.length))}
                className="bg-green-700 hover:bg-green-600 text-xs px-3 py-1"
              >
                ⏭️ Step
              </Button>
            )}
          </div>
        </div>
        <ForceGraph3D
          ref={fgRef}
          graphData={filtered}
          backgroundColor="#000000"
          nodeLabel={(node: any) => `${node.label} (${node.glyph}) • Tick: ${node.tick || '-'}`}
          nodeAutoColorBy="glyph"
          linkColor={() => 'rgba(200, 200, 255, 0.6)'}
          nodeThreeObjectExtend={true}
          nodeThreeObject={(node: any) => {
            const spriteCanvas = document.createElement('canvas');
            spriteCanvas.width = 256;
            spriteCanvas.height = 64;
            const ctx = spriteCanvas.getContext('2d')!;
            ctx.font = '28px Orbitron';
            ctx.fillStyle = 'cyan';
            ctx.textAlign = 'center';
            ctx.fillText(node.glyph, 128, 40);
            const texture = new THREE.CanvasTexture(spriteCanvas);
            const spriteMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true });
            const sprite = new THREE.Sprite(spriteMaterial);
            sprite.scale.set(40, 10, 1);
            return sprite;
          }}
        />
      </CardContent>
    </Card>
  );
}