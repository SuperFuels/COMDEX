import React, { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Html } from "@react-three/drei";

type Viz = {
  glyph?: string;
  color?: string;
  orbit?: { radius: number; speed: number };
  emissive?: number;
};

type Props = {
  id: string;
  viz: Viz;
  active?: boolean;
  childrenAtoms?: Array<{ id: string; viz: Viz }>;
};

export default function AtomNode3D({
  id,
  viz,
  active,
  childrenAtoms = [],
}: Props) {
  // keep ref loose to dodge the @types/three mismatch
  const group = useRef<any>(null);

  // use plain hex/string instead of THREE.Color instance
  const color = viz?.color || "#999";
  const speed = viz?.orbit?.speed ?? 0.3;
  const r = viz?.orbit?.radius ?? 1.4;

  useFrame((_, dt) => {
    if (group.current && active) {
      group.current.rotation.y += speed * dt;
    }
  });

  return (
    <group ref={group as any}>
      {/* nucleus */}
      <mesh>
        <sphereGeometry args={[0.4, 32, 32]} />
        <meshStandardMaterial
          color={color as any}
          emissive={color as any}
          emissiveIntensity={viz?.emissive ?? 1.0}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* electron orbits */}
      {[0, Math.PI / 3, -Math.PI / 3].map((rot, i) => (
        <mesh key={i} rotation={[rot, rot, 0]}>
          <torusGeometry args={[r, 0.02, 8, 128]} />
          <meshBasicMaterial
            color={color as any}
            opacity={0.6}
            transparent
          />
        </mesh>
      ))}

      {/* label */}
      <Html distanceFactor={12}>
        <div
          style={{
            color: "#cfe",
            background: "#0008",
            padding: "2px 6px",
            borderRadius: 6,
          }}
        >
          {id}
        </div>
      </Html>

      {/* children */}
      {childrenAtoms.map((c, i) => (
        <group
          key={c.id}
          position={[
            Math.cos((i * 2 * Math.PI) / childrenAtoms.length) * 2.5,
            0.4,
            Math.sin((i * 2 * Math.PI) / childrenAtoms.length) * 2.5,
          ]}
        >
          <AtomNode3D id={c.id} viz={c.viz} />
        </group>
      ))}
    </group>
  );
}