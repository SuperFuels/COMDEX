"use client";

import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { useMemoryBridge } from "@/hooks/useMemoryBridge";

type GlyphPositionMap = Record<string, THREE.Vector3>;

interface MemoryBridgeBeamsProps {
  /** container id needed by useMemoryBridge */
  containerId: string;
  /** map of glyph symbol -> world position */
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
  const groupRef = useRef<THREE.Group>(null);

  // 🔌 hook requires containerId
  const { activeBridges = [] } = useMemoryBridge(containerId) || { activeBridges: [] };

  // keep refs to animate individual beams
  const beamRefs = useRef<THREE.Mesh[]>([]);

  // material parameters (each mesh gets its own instance from JSX)
  const materialParams = useMemo(
    () => ({
      color: new THREE.Color(bridgeColor),
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    }),
    [bridgeColor]
  );

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    beamRefs.current.forEach((beam, i) => {
      if (!beam) return;
      // gentle stretch
      const s = 1.0 + 0.2 * Math.sin(t * 2 + i);
      beam.scale.set(1, s, 1);
      // pulse opacity
      const mat = beam.material as THREE.MeshBasicMaterial;
      if (mat) mat.opacity = 0.5 + 0.3 * Math.sin(t * 3 + i);
    });
  });

  return (
    <group ref={groupRef}>
      {activeBridges.map((bridge: { from: string; to: string }, i: number) => {
        const from = glyphPositions[bridge.from];
        const to = glyphPositions[bridge.to];
        if (!from || !to) return null;

        // orientation for a cylinder aligned from "from" → "to"
        const mid = new THREE.Vector3().addVectors(from, to).multiplyScalar(0.5);
        const dir = new THREE.Vector3().subVectors(to, from);
        const length = dir.length();
        const quat = new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 1, 0), // cylinder's up axis
          dir.clone().normalize()
        );

        return (
          <mesh
            key={`bridge-${i}`}
            ref={(el) => {
              if (el) beamRefs.current[i] = el;
            }}
            position={mid}
            quaternion={quat}
          >
            <cylinderGeometry args={[beamWidth, beamWidth, length, 12]} />
            <meshBasicMaterial {...materialParams} />
          </mesh>
        );
      })}
    </group>
  );
}