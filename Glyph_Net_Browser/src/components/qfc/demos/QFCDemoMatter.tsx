"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

type QFCFrame = { chi?: number; sigma?: number; alpha?: number };
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const num = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

export default function QFCDemoMatter({ frame }: { frame: QFCFrame | null }) {
  const cloud = useRef<THREE.Points>(null);

  const geom = useMemo(() => {
    const COUNT = 2600;
    const g = new THREE.BufferGeometry();
    const pos = new Float32Array(COUNT * 3);
    const seed = new Float32Array(COUNT);

    for (let i = 0; i < COUNT; i++) {
      pos[i * 3 + 0] = (Math.random() - 0.5) * 18;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 8 + 1.5;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 18;
      seed[i] = Math.random();
    }

    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("seed", new THREE.BufferAttribute(seed, 1));
    return g;
  }, []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const chi = clamp01(num(frame?.chi, 0.25));
    const sigma = clamp01(num(frame?.sigma, 0.45));

    if (!cloud.current) return;
    cloud.current.rotation.y = t * (0.06 + 0.12 * chi);
    cloud.current.rotation.x = 0.05 * Math.sin(t * (0.4 + sigma));
    cloud.current.position.y = 0.10 * Math.sin(t * (0.7 + chi));
  });

  const chi = clamp01(num(frame?.chi, 0.25));
  const alpha = clamp01(num(frame?.alpha, 0.12));
  const density = clamp01(0.25 + 0.85 * chi);

  return (
    <group>
      <points ref={cloud} geometry={geom}>
        <pointsMaterial
          size={0.055 + 0.06 * density}
          color={"#e2e8f0"}
          transparent
          opacity={0.18 + 0.35 * density}
          depthWrite={false}
        />
      </points>

      {/* “slice plane” */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.6, 0]}>
        <circleGeometry args={[8.5, 64]} />
        <meshBasicMaterial color={"#94a3b8"} transparent opacity={0.03 + 0.05 * alpha} />
      </mesh>
    </group>
  );
}