"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

type QFCFrame = { coupling_score?: number; alpha?: number };
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const num = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

export default function QFCDemoConnect({ frame }: { frame: QFCFrame | null }) {
  const nodesRef = useRef<THREE.Group>(null);
  const linesRef = useRef<THREE.LineSegments>(null);

  const { nodes, lineGeom } = useMemo(() => {
    const nodes = Array.from({ length: 8 }).map((_, i) => ({
      a: i * 0.9,
      r: 4.5 + (i % 3) * 0.7,
      y: -0.2 + (i % 4) * 0.25,
    }));

    // dynamic line geometry (positions updated each frame)
    const g = new THREE.BufferGeometry();
    const pos = new Float32Array(8 * 3 * 2); // 8 segments (a->b), 2 endpoints
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    return { nodes, lineGeom: g };
  }, []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const coupling = clamp01(num(frame?.coupling_score, 0.55));
    const a = clamp01(num(frame?.alpha, 0.12));

    const points: THREE.Vector3[] = nodes.map((n) => {
      const ang = n.a + t * (0.25 + 0.55 * coupling);
      return new THREE.Vector3(
        Math.cos(ang) * n.r,
        n.y + 0.25 * Math.sin(t * (0.8 + a) + n.a),
        Math.sin(ang) * n.r
      );
    });

    if (nodesRef.current) {
      nodesRef.current.rotation.y = t * (0.06 + 0.18 * coupling);
    }

    // Update line segments
    const attr = lineGeom.getAttribute("position") as THREE.BufferAttribute;
    let idx = 0;
    for (let i = 0; i < points.length; i++) {
      const a = points[i];
      const b = points[(i + 2) % points.length];
      attr.setXYZ(idx++, a.x, a.y, a.z);
      attr.setXYZ(idx++, b.x, b.y, b.z);
    }
    attr.needsUpdate = true;
    lineGeom.computeBoundingSphere();

    // Update node mesh positions
    if (nodesRef.current) {
      const kids = nodesRef.current.children;
      for (let i = 0; i < kids.length && i < points.length; i++) {
        kids[i].position.copy(points[i]);
        const s = 0.18 + 0.55 * coupling;
        kids[i].scale.setScalar(s);
      }
    }
  });

  const coupling = clamp01(num(frame?.coupling_score, 0.55));
  const opacity = 0.10 + 0.35 * coupling;

  return (
    <group>
      <lineSegments ref={linesRef} geometry={lineGeom}>
        <lineBasicMaterial color={"#22d3ee"} transparent opacity={opacity} />
      </lineSegments>

      <group ref={nodesRef}>
        {nodes.map((_, i) => (
          <mesh key={i}>
            <sphereGeometry args={[0.22, 18, 18]} />
            <meshStandardMaterial
              color={"#22d3ee"}
              emissive={"#0ea5e9"}
              emissiveIntensity={0.15 + 0.85 * coupling}
              roughness={0.25}
              metalness={0.25}
            />
          </mesh>
        ))}
      </group>
    </group>
  );
}