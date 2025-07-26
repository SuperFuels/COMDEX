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

  // 🛰️ WebSocket Live Mode
  useWebSocket(
    '/ws/codex',
    (data) => {
      if (mode !== 'live') return;
      if (data?.type === 'glyph_execution') {
        const glyph = data.payload?.glyph;
        const from = data.payload?.detail?.entangled_from;
        const id = `${glyph}-${data.payload.timestamp}`;
        const sourceId = from || 'root';

        setGraphData((prev) => {
          const nodes = [...prev.nodes];
          const links = [...prev.links];

          if (!nodes.find((n) => n.id === id)) {
            nodes.push({ id, label: glyph, glyph });
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
    },
    ['glyph_execution']
  );

  // 🧪 Replay mode loader
  useEffect(() => {
    if (mode !== 'replay') return;
    fetch('/containers/seed_entangled.dc.json')
      .then(res => res.json())
      .then(data => {
        allGlyphsRef.current = data.glyphs;
        setStep(1); // Start replay
      });
  }, [mode]);

  // 🧪 Step through glyphs one at a time
  useEffect(() => {
    if (mode !== 'replay' || step <= 0) return;
    const glyphs = allGlyphsRef.current.slice(0, step);
    const nodes = glyphs.map((g: any) => ({
      id: g.id,
      label: g.label,
      glyph: g.glyph
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

  const filtered = filter
    ? {
        nodes: graphData.nodes.filter(n => n.glyph.toLowerCase().includes(filter.toLowerCase())),
        links: graphData.links.filter(l =>
          graphData.nodes.find(n => n.id === l.source && n.glyph.toLowerCase().includes(filter.toLowerCase())) ||
          graphData.nodes.find(n => n.id === l.target && n.glyph.toLowerCase().includes(filter.toLowerCase()))
        )
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
          nodeLabel={(node: any) => `${node.label} (${node.glyph})`}
          nodeAutoColorBy="glyph"
          linkColor={() => 'rgba(200, 200, 255, 0.6)'}
          nodeThreeObjectExtend={true}
          nodeThreeObject={(node: any) => {
            const sprite = document.createElement('canvas');
            const size = 64;
            sprite.width = sprite.height = size;
            const ctx = sprite.getContext('2d')!;
            ctx.fillStyle = 'white';
            ctx.font = '24px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(node.glyph, size / 2, size / 2);
            const texture = new THREE.CanvasTexture(sprite);
            const material = new THREE.SpriteMaterial({ map: texture });
            return new THREE.Sprite(material);
          }}
        />
      </CardContent>
    </Card>
  );
}