"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

type QFCFrame = { sigma?: number; alpha?: number; coupling_score?: number };
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const num = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

export default function QFCDemoTunnel({ frame }: { frame: QFCFrame | null }) {
  const group = useRef<THREE.Group>(null);
  const beam = useRef<THREE.Mesh>(null);

  const rings = useMemo(() => {
    return Array.from({ length: 44 }).map((_, i) => ({
      z: -i * 1.0,
      r: 2.2 + 0.25 * Math.sin(i * 0.35),
    }));
  }, []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const s = clamp01(num(frame?.sigma, 0.55));
    const a = clamp01(num(frame?.alpha, 0.12));

    if (group.current) {
      group.current.rotation.z = 0.15 * Math.sin(t * (0.25 + 0.4 * s));
      group.current.rotation.y = t * (0.12 + 0.25 * a);
    }
    if (beam.current) {
      beam.current.position.z = -8 - 10 * ((t * (0.45 + 0.8 * s)) % 1);
      beam.current.scale.set(0.45 + 0.9 * a, 0.45 + 0.9 * a, 1);
    }
  });

  const sigma = clamp01(num(frame?.sigma, 0.55));
  const alpha = clamp01(num(frame?.alpha, 0.12));
  const glow = 0.15 + 0.85 * clamp01(alpha + 0.35 * sigma);

  return (
    <group ref={group} position={[0, 0.0, 6]}>
      {/* ring tunnel */}
      {rings.map((r, i) => (
        <mesh key={i} position={[0, 0, r.z]}>
          <torusGeometry args={[r.r, 0.04, 8, 96]} />
          <meshBasicMaterial color={"#fbbf24"} transparent opacity={0.05 + 0.05 * glow} />
        </mesh>
      ))}

      {/* photon beam “pulse” */}
      <mesh ref={beam} position={[0, 0, -8]}>
        <cylinderGeometry args={[0.35, 0.35, 4.2, 18, 1, true]} />
        <meshBasicMaterial color={"#fde68a"} transparent opacity={0.10 + 0.25 * glow} />
      </mesh>
    </group>
  );
}