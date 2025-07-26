import React, { useEffect, useRef, useState } from 'react';
import { ForceGraph2D } from 'react-force-graph';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

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

export default function EntanglementGraphPage() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [filter, setFilter] = useState('');
  const fgRef = useRef<any>();

  // ✅ Load static seed_entangled.dc.json container
  useEffect(() => {
    fetch('/containers/seed_entangled.dc.json')
      .then(res => res.json())
      .then(data => {
        const nodes = data.glyphs.map((g: any) => ({
          id: g.id,
          label: g.label || g.glyph,
          glyph: g.glyph
        }));
        const links: any[] = [];
        data.glyphs.forEach((g: any) => {
          if (g.entangled) {
            g.entangled.forEach((targetId: string) => {
              links.push({ source: g.id, target: targetId });
            });
          }
        });
        setGraphData({ nodes, links });
      });
  }, []);

  const filtered = filter
    ? {
        nodes: graphData.nodes.filter((n) => n.glyph.toLowerCase().includes(filter.toLowerCase())),
        links: graphData.links.filter((l) =>
          graphData.nodes.find((n) => n.id === l.source && n.glyph.toLowerCase().includes(filter.toLowerCase())) ||
          graphData.nodes.find((n) => n.id === l.target && n.glyph.toLowerCase().includes(filter.toLowerCase()))
        )
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
              onClick={() => fgRef.current?.zoomToFit(400)}
              className="bg-purple-700 hover:bg-purple-600 text-xs px-3 py-1"
            >
              🎯 Fit View
            </Button>
          </div>
        </div>
        <ForceGraph2D
          ref={fgRef}
          graphData={filtered}
          nodeLabel={(node: Node) => node.label}
          nodeCanvasObject={(node: Node & { x?: number; y?: number }, ctx: CanvasRenderingContext2D) => {
            const label = node.label;
            ctx.font = '10px Sans-Serif';
            ctx.fillStyle = '#00ffcc';
            ctx.beginPath();
            ctx.arc(node.x!, node.y!, 6, 0, 2 * Math.PI, false);
            ctx.fill();
            ctx.fillText(label, node.x! + 8, node.y! + 3);
          }}
          linkColor={() => '#8888ff'}
          backgroundColor="#000000"
        />
      </CardContent>
    </Card>
  );
}