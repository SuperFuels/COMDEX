import React from 'react';

type Coord = { x: number; y: number };
type Link = { from: Coord; to: Coord; id: string };

interface EntanglementLinksProps {
  links: Link[]; // Array of entangled connections with pixel coords
  width?: number;
  height?: number;
}

export default function EntanglementLinks({ links, width = 400, height = 300 }: EntanglementLinksProps) {
  return (
    <svg
      width={width}
      height={height}
      style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
    >
      {links.map(({ from, to, id }) => (
        <line
          key={id}
          x1={from.x}
          y1={from.y}
          x2={to.x}
          y2={to.y}
          stroke="purple"
          strokeWidth={2}
          strokeOpacity={0.7}
          strokeDasharray="4 4" // dashed line to represent entanglement
        />
      ))}
    </svg>
  );
}