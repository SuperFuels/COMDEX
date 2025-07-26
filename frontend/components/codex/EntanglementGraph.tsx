import React from 'react';
import { ForceGraph2D } from 'react-force-graph';

export interface EntangledNode {
  id: string;
  label: string;
  glyph: string;
}

export interface EntangledLink {
  source: string;
  target: string;
  label?: string;
}

interface EntanglementGraphProps {
  nodes: EntangledNode[];
  links: EntangledLink[];
}

export default function EntanglementGraph({ nodes, links }: EntanglementGraphProps) {
  return (
    <div className="w-full h-[400px] bg-black border border-purple-700 rounded-lg mt-4">
      <ForceGraph2D
        graphData={{ nodes, links }}
        nodeAutoColorBy="glyph"
        nodeLabel={(n: any) => `${n.label} (${n.glyph})`}
        linkDirectionalArrowLength={6}
        linkCurvature={0.25}
        linkColor={() => 'rgba(200, 200, 255, 0.5)'}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.label || node.id;
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          ctx.fillStyle = 'white';
          ctx.beginPath();
          ctx.arc(node.x!, node.y!, 5, 0, 2 * Math.PI, false);
          ctx.fill();
          ctx.fillText(label, node.x! + 6, node.y! + 4);
        }}
      />
    </div>
  );
}