"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

type QFCFrame = {
  kappa?: number;
  curv?: number;
  alpha?: number;
  flags?: { nec_violation?: boolean; nec_strength?: number };
};

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const num = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

export default function QFCDemoGravity({ frame }: { frame: QFCFrame | null }) {
  const well = useRef<THREE.Mesh>(null);
  const rings = useRef<THREE.Group>(null);

  const ringGeoms = useMemo(() => {
    return Array.from({ length: 7 }).map((_, i) => new THREE.TorusGeometry(2.2 + i * 0.9, 0.03, 10, 180));
  }, []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const k = clamp01(num(frame?.kappa, 0.25));
    const c = clamp01(num(frame?.curv, 0.18));
    const a = clamp01(num(frame?.alpha, 0.12));

    if (well.current) {
      well.current.rotation.y = t * (0.25 + 0.6 * a);
      well.current.scale.setScalar(0.95 + 0.25 * (k + c));
    }
    if (rings.current) {
      rings.current.rotation.y = t * (0.08 + 0.18 * a);
      rings.current.rotation.x = -Math.PI / 2 + 0.06 * Math.sin(t * (0.7 + k));
    }
  });

  const kappa = clamp01(num(frame?.kappa, 0.25));
  const curv = clamp01(num(frame?.curv, 0.18));
  const intensity = clamp01(0.25 + 0.9 * (kappa + curv) * 0.5);

  return (
    <group>
      {/* “gravity well” */}
      <mesh ref={well} position={[0, 0.2, 0]}>
        <sphereGeometry args={[1.15, 48, 48]} />
        <meshStandardMaterial
          color={"#38bdf8"}
          emissive={"#0ea5e9"}
          emissiveIntensity={0.35 + 0.9 * intensity}
          metalness={0.4}
          roughness={0.25}
        />
      </mesh>

      {/* rings */}
      <group ref={rings} position={[0, -0.3, 0]}>
        {ringGeoms.map((g, i) => (
          <mesh key={i} geometry={g} rotation={[0, 0, (i * Math.PI) / 16]}>
            <meshBasicMaterial color={"#e2e8f0"} transparent opacity={0.08 + 0.06 * intensity} />
          </mesh>
        ))}
      </group>

      {/* subtle “lens sheet” */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.85, 0]}>
        <circleGeometry args={[8.5, 64]} />
        <meshBasicMaterial color={"#0ea5e9"} transparent opacity={0.05 + 0.08 * intensity} />
      </mesh>
    </group>
  );
}