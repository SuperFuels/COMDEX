// Glyph_Net_Browser/src/components/GHXVisualizerField.tsx
'use client';

import React, { useMemo } from "react";
import type { GhxPacket } from "./DevFieldHologram3D";

interface GHXVisualizerFieldProps {
  packet: GhxPacket | null;
  height?: number;
  // match DevFieldHologram3DScene: "field" | "crystal"
  layout?: "field" | "crystal";
}

/**
 * Very small 2D sketch of the GHX graph:
 * - "field"   → fan/arc layout (matches 3D field card)
 * - "crystal" → lattice-style layout (matches 3D crystal card)
 * - edges as faint lines
 */
export function GHXVisualizerField({
  packet,
  height = 140,
  layout = "field",
}: GHXVisualizerFieldProps) {
  if (!packet || !packet.nodes || packet.nodes.length === 0) {
    return (
      <div
        style={{
          borderRadius: 8,
          border: "1px dashed #e5e7eb",
          padding: 8,
          fontSize: 11,
          color: "#9ca3af",
          textAlign: "center",
        }}
      >
        {/* no GHX graph yet… */}
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

    if (layout === "crystal") {
      // lattice-ish layout (3×N grid) to echo the 3D crystal slab
      const cols = 3;
      const rows = Math.ceil(n / cols);

      const spanX = width * 0.55;
      const spanY = h * 0.45;

      const cellX = cols > 1 ? spanX / (cols - 1) : 0;
      const cellY = rows > 1 ? spanY / (rows - 1) : 0;

      nodes.forEach((node, i) => {
        const c = i % cols;
        const r = Math.floor(i / cols);
        const x = cx - spanX / 2 + c * cellX;
        const y = cy - spanY / 2 + r * cellY;
        map.set(node.id, { x, y });
      });

      return map;
    }

    // "field" layout – fan / arc
    const radius = Math.min(width, h) * 0.32;
    const arc = Math.PI * 1.0; // 180°
    const start = -arc / 2;

    nodes.forEach((node, i) => {
      const t = n === 1 ? 0 : i / (n - 1);
      const angle = start + arc * t;
      const x = cx + Math.cos(angle) * radius;
      const y = cy + Math.sin(angle) * radius * 0.7;
      map.set(node.id, { x, y });
    });

    return map;
  }, [nodes, h, layout]);

  return (
    <div
      style={{
        borderRadius: 8,
        border: "1px solid #e5e7eb",
        background: "#0b1120",
        padding: 6,
      }}
    >
      <svg
        width="100%"
        height={h}
        viewBox={`0 0 ${width} ${h}`}
        style={{ display: "block" }}
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
        {edges.map((e: any) => {
          const srcId = e.source ?? e.src;
          const dstId = e.target ?? e.dst;
          if (!srcId || !dstId) return null;

          const a = positions.get(srcId);
          const b = positions.get(dstId);
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
              fill={isRoot ? "#facc15" : "#e0f2fe"}
              stroke="#0f172a"
              strokeWidth={0.6}
            />
          );
        })}
      </svg>
    </div>
  );
}