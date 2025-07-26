"use client";

import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import { useMemoryBridge } from "@/hooks/useMemoryBridge";

// Mocked or real glyph position map
type GlyphPositionMap = {
  [symbol: string]: THREE.Vector3;
};

interface MemoryBridgeBeamsProps {
  glyphPositions: GlyphPositionMap;
  bridgeColor?: string;
  beamWidth?: number;
}

export default function MemoryBridgeBeams({
  glyphPositions,
  bridgeColor = "#66ffcc",
  beamWidth = 0.03,
}: MemoryBridgeBeamsProps) {
  const groupRef = useRef<THREE.Group>(null);
  const { activeBridges } = useMemoryBridge();

  const beamRefs = useRef<THREE.Mesh[]>([]);

  // Create beam geometries and materials
  const beamMaterial = useMemo(() => {
    return new THREE.MeshBasicMaterial({
      color: bridgeColor,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
    });
  }, [bridgeColor]);

  useFrame(({ clock }) => {
    // Animate pulsing effect
    const t = clock.getElapsedTime();
    beamRefs.current.forEach((beam, i) => {
      const scale = 1.0 + 0.2 * Math.sin(t * 2 + i);
      beam.scale.setY(scale);
      beam.material.opacity = 0.5 + 0.3 * Math.sin(t * 3 + i);
    });
  });

  return (
    <group ref={groupRef}>
      {activeBridges.map((bridge, i) => {
        const from = glyphPositions[bridge.from];
        const to = glyphPositions[bridge.to];
        if (!from || !to) return null;

        const mid = new THREE.Vector3().addVectors(from, to).multiplyScalar(0.5);
        const dir = new THREE.Vector3().subVectors(to, from);
        const length = dir.length();
        const orientation = new THREE.Matrix4();
        orientation.lookAt(from, to, new THREE.Vector3(0, 1, 0));
        orientation.multiply(
          new THREE.Matrix4().makeRotationX(Math.PI / 2) // align cylinder
        );

        return (
          <mesh
            key={`bridge-${i}`}
            ref={(el) => {
              if (el) beamRefs.current[i] = el;
            }}
            position={mid}
            rotation={new THREE.Euler().setFromRotationMatrix(orientation)}
          >
            <cylinderGeometry args={[beamWidth, beamWidth, length, 8]} />
            <primitive object={beamMaterial} attach="material" />
          </mesh>
        );
      })}
    </group>
  );
}