"use client";

import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import { useMemoryBridge } from "@/hooks/useMemoryBridge";

type GlyphPositionMap = Record<string, THREE.Vector3>;

interface MemoryBridgeBeamsProps {
  /** container id needed by useMemoryBridge */
  containerId: string;
  /** map of glyph id -> world position */
  glyphPositions: GlyphPositionMap;
  bridgeColor?: string;
  beamWidth?: number;
}

export default function MemoryBridgeBeams({
  containerId,
  glyphPositions,
  bridgeColor = "#66ffcc",
  beamWidth = 0.03,
}: MemoryBridgeBeamsProps) {
  // loose ref types to dodge @types/three vs three mismatch
  const groupRef = useRef<any>(null);
  const beamRefs = useRef<any[]>([]);

  const { activeBridges = [] } = useMemoryBridge(containerId) || { activeBridges: [] };

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    beamRefs.current.forEach((beam, i) => {
      if (!beam) return;
      const s = 1.0 + 0.2 * Math.sin(t * 2 + i);
      beam.scale.set(1, s, 1);
      const mat = beam.material as THREE.MeshBasicMaterial;
      if (mat) mat.opacity = 0.5 + 0.3 * Math.sin(t * 3 + i);
    });
  });

  return (
    <group
      ref={(el: any) => {
        groupRef.current = el;
      }}
    >
      {activeBridges.map((bridge: { from: string; to: string }, i: number) => {
        const from = glyphPositions[bridge.from];
        const to = glyphPositions[bridge.to];
        if (!from || !to) return null;

        const mid = new THREE.Vector3().addVectors(from, to).multiplyScalar(0.5);
        const dir = new THREE.Vector3().subVectors(to, from);
        const length = dir.length();
        const quat = new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          dir.clone().normalize()
        );

        return (
          <mesh
            key={`bridge-${i}`}
            ref={(el: any) => {
              if (el) beamRefs.current[i] = el;
            }}
            position={[mid.x, mid.y, mid.z]}
            quaternion={quat as any}
          >
            <cylinderGeometry args={[beamWidth, beamWidth, length, 12]} />
            <meshBasicMaterial
              color={bridgeColor}
              transparent
              opacity={0.6}
              blending={THREE.AdditiveBlending}
              depthWrite={false}
            />
          </mesh>
        );
      })}
    </group>
  );
}