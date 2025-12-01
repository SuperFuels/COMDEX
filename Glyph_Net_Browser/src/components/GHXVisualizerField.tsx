'use client';

import React, { useMemo } from 'react';
import type { GhxPacket } from './DevFieldHologram3D';

interface GHXVisualizerFieldProps {
  packet: GhxPacket | null;
  height?: number;
}

/**
 * Very small 2D sketch of the GHX graph:
 * - nodes laid out on a circle
 * - edges as faint lines
 * - sized to live inside the right-hand inspector
 */
export function GHXVisualizerField({
  packet,
  height = 140,
}: GHXVisualizerFieldProps) {
  if (!packet || !packet.nodes || packet.nodes.length === 0) {
    return (
      <div
        style={{
          borderRadius: 8,
          border: '1px dashed #e5e7eb',
          padding: 8,
          fontSize: 11,
          color: '#9ca3af',
          textAlign: 'center',
        }}
      >
        // no GHX graph yet…
      </div>
    );
  }

  const nodes = packet.nodes;
  const edges = packet.edges ?? [];

  const width = 260;
  const h = height;

  const positions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    const n = nodes.length;
    if (!n) return map;

    const cx = width / 2;
    const cy = h / 2;
    const radius = Math.min(width, h) * 0.35 + Math.min(40, n * 2);

    nodes.forEach((node, i) => {
      const t = n === 1 ? 0 : i / n;
      const angle = t * Math.PI * 2 - Math.PI / 2; // start at top
      const x = cx + Math.cos(angle) * radius;
      const y = cy + Math.sin(angle) * radius;
      map.set(node.id, { x, y });
    });

    return map;
  }, [nodes, h]);

  return (
    <div
      style={{
        borderRadius: 8,
        border: '1px solid #e5e7eb',
        background: '#0b1120',
        padding: 6,
      }}
    >
      <svg
        width="100%"
        height={h}
        viewBox={`0 0 ${width} ${h}`}
        style={{ display: 'block' }}
      >
        {/* subtle background */}
        <defs>
          <radialGradient id="ghx-bg" cx="50%" cy="50%" r="70%">
            <stop offset="0%" stopColor="#020617" />
            <stop offset="100%" stopColor="#020617" />
          </radialGradient>
        </defs>
        <rect x={0} y={0} width={width} height={h} fill="url(#ghx-bg)" />

        {/* edges */}
        {edges.map((e) => {
          const a = positions.get(e.source);
          const b = positions.get(e.target);
          if (!a || !b) return null;
          return (
            <line
              key={e.id}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="#38bdf8"
              strokeWidth={0.7}
              strokeOpacity={0.35}
            />
          );
        })}

        {/* nodes */}
        {nodes.map((node, idx) => {
          const p = positions.get(node.id);
          if (!p) return null;
          const isRoot = idx === 0;
          return (
            <circle
              key={node.id}
              cx={p.x}
              cy={p.y}
              r={isRoot ? 5 : 3.2}
              fill={isRoot ? '#facc15' : '#e0f2fe'}
              stroke="#0f172a"
              strokeWidth={0.6}
            />
          );
        })}
      </svg>
    </div>
  );
}