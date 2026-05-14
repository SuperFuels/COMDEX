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
  // loosen refs to 'any' and use callback refs
  const geomRef = useRef<any>(null);
  const lineRef = useRef<any>(null);

  const positions = useMemo(() => new Float32Array(points.flat()), [points]);

  useEffect(() => {
    const geom: THREE.BufferGeometry | null = geomRef.current;
    if (!geom) return;

    geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geom.computeBoundingSphere?.();

    if (dashed && lineRef.current?.computeLineDistances) {
      (lineRef.current as THREE.Line).computeLineDistances();
    }
  }, [positions, dashed]);

  return (
    <line
      ref={(obj: any) => {
        lineRef.current = obj || null;
      }}
    >
      <bufferGeometry
        ref={(node: any) => {
          geomRef.current = node;
        }}
      />
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