"use client";

import React, { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";

interface TrailSegment {
  points: [number, number, number][];
  type: "deadend" | "breakthrough";
  label?: string;
  dashed?: boolean;
  opacity?: number;
  lineWidth?: number; // kept for API parity (THREE uses "linewidth")
}

interface BreakthroughDeadendTrailProps {
  segments: TrailSegment[];
  visible?: boolean;
}

const colorMap: Record<TrailSegment["type"], string> = {
  deadend: "#ef4444",       // red
  breakthrough: "#10b981",  // emerald
};

/** Low-level polyline using core three.js <line>. No drei dependency. */
function Polyline({
  points,
  color,
  dashed = false,
  opacity = 1,
  lineWidth = 1,
}: {
  points: [number, number, number][];
  color: string;
  dashed?: boolean;
  opacity?: number;
  lineWidth?: number;
}) {
  const geomRef = useRef<THREE.BufferGeometry>(null);
  const lineRef = useRef<THREE.Line | null>(null);

  const positions = useMemo(() => new Float32Array(points.flat()), [points]);

  useEffect(() => {
    const geom = geomRef.current;
    if (!geom) return;

    geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geom.computeBoundingSphere?.();

    // For dashed lines, distances must be computed *after* positions change
    if (dashed && lineRef.current?.computeLineDistances) {
      lineRef.current.computeLineDistances();
    }
  }, [positions, dashed]);

  return (
    <line
      // Use a callback ref to avoid TS inferring the SVG <line> ref type
      ref={(obj) => {
        lineRef.current = (obj as unknown as THREE.Line) || null;
      }}
    >
      <bufferGeometry ref={geomRef} />
      {dashed ? (
        <lineDashedMaterial
          color={color}
          transparent
          opacity={opacity}
          linewidth={lineWidth}
          dashSize={0.25}
          gapSize={0.15}
        />
      ) : (
        <lineBasicMaterial
          color={color}
          transparent
          opacity={opacity}
          linewidth={lineWidth}
        />
      )}
    </line>
  );
}

export default function BreakthroughDeadendTrail({
  segments,
  visible = true,
}: BreakthroughDeadendTrailProps) {
  if (!visible || !segments?.length) return null;

  return (
    <>
      {segments.map((seg, i) => (
        <Polyline
          key={`trail-${i}`}
          points={seg.points}
          color={colorMap[seg.type] || "#999"}
          dashed={!!seg.dashed}
          opacity={seg.opacity ?? 1}
          lineWidth={seg.lineWidth ?? 1.5}
        />
      ))}
    </>
  );
}