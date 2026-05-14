// ReplayTrails.tsx
import * as React from "react";
import * as THREE from "three";

export interface ReplayTrailsProps {
  frames: any[];
  index: number;
}

/**
 * Minimal, dependency-free trail renderer for replay links.
 * Safe to use inside any <Canvas> tree.
 */
export default function ReplayTrails({ frames, index }: ReplayTrailsProps) {
  type Pt = [number, number, number];

  const frame = Array.isArray(frames) ? frames[index] : undefined;
  const links: any[] = Array.isArray(frame?.links) ? frame!.links : [];
  if (!links.length) return null;

  const toPoints = (trail: any): Pt[] =>
    Array.isArray(trail?.points)
      ? (trail.points as Pt[])
      : Array.isArray(trail)
      ? (trail as Pt[])
      : [];

  const colorFor = (t?: string) =>
    t === "breakthrough"
      ? "#22c55e"
      : t === "deadend"
      ? "#ef4444"
      : t === "collapsed"
      ? "#94a3b8"
      : "#f59e0b";

  return (
    <>
      {links.map((lnk: any, i: number) => {
        const pts = toPoints(lnk?.trail);
        if (!pts.length) return null;

        const geom = new THREE.BufferGeometry().setFromPoints(
          pts.map(([x, y, z]) => new THREE.Vector3(x, y, z))
        );

        return (
          <line key={`replay-trail-${i}`}>
            <primitive object={geom} attach="geometry" />
            <lineBasicMaterial
              attach="material"
              color={colorFor(lnk?.collapseState)}
              transparent
              opacity={0.85}
            />
          </line>
        );
      })}
    </>
  );
}