import React, { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Float, Html } from "@react-three/drei";
import * as THREE from "three";

type ThoughtGlyph = {
  symbol: string;
  id: string;
  color?: string;
  pulse?: boolean;
  label?: string;
};

type Props = {
  thoughts: ThoughtGlyph[];
  orbitRadius?: number;
  avatarPosition?: [number, number, number];
};

const OrbitingGlyph: React.FC<{
  glyph: ThoughtGlyph;
  index: number;
  total: number;
  radius: number;
}> = ({ glyph, index, total, radius }) => {
  const ref = useRef<THREE.Group>(null!);
  const angleOffset = (index / Math.max(1, total)) * Math.PI * 2;

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const angle = angleOffset + t * 0.3;
    const x = Math.cos(angle) * radius;
    const z = Math.sin(angle) * radius;
    ref.current.position.set(x, 1.5, z);
    ref.current.rotation.y = -angle;
  });

  return (
    <group ref={ref}>
      <Float speed={glyph.pulse ? 2 : 0} floatIntensity={glyph.pulse ? 1.5 : 0.2}>
        <Html center distanceFactor={14}>
          <div
            style={{
              color: glyph.color || "#ffffff",
              fontSize: "16px",
              lineHeight: 1,
              fontWeight: 600,
              textShadow: "0 0 6px rgba(0,0,0,0.6)",
              userSelect: "none",
            }}
          >
            {glyph.symbol}
          </div>
        </Html>
      </Float>
    </group>
  );
};

const AvatarThoughtProjection: React.FC<Props> = ({
  thoughts,
  orbitRadius = 2.5,
  avatarPosition = [0, 0, 0],
}) => {
  return (
    <group position={avatarPosition}>
      {thoughts.map((glyph, idx) => (
        <OrbitingGlyph
          key={glyph.id}
          glyph={glyph}
          index={idx}
          total={thoughts.length}
          radius={orbitRadius}
        />
      ))}
    </group>
  );
};

export default AvatarThoughtProjection;