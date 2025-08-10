import React, { useRef, useMemo } from "react";
import { animated, useSpring } from "@react-spring/three";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import type { AtomModel, Vec3, ContainerInfo } from "@/types/atom";

interface AtomContainerProps {
  key?: string; // usually not needed unless in a map
  position?: Vec3;
  atom: AtomModel;
  container?: ContainerInfo; // 👈 optional container info
}

const AtomContainer: React.FC<AtomContainerProps> = ({
  position,
  atom,
  container,
}) => {
  const groupRef = useRef<THREE.Group>(null);

  // Destructure props for easier access
  const { viz = {}, id, containerId } = atom;
  const {
    glyph,
    active = false,
    logicDepth = 0,
    runtimeTick = 0,
    soulLocked = false,
    position: vizPos,
  } = viz;

  /** ===== Scale Animation (Hoberman-style expansion) ===== **/
  const targetScale =
    soulLocked || logicDepth === 0 ? 0.001 : 0.4 + logicDepth * 0.12;

  const { scale } = useSpring({
    scale: targetScale,
    config: { mass: 2, tension: 200, friction: 25 },
  });

  const animatedScale = scale.to((s) => [s, s, s]) as unknown as Vec3;

  /** ===== Color logic based on glyph type ===== **/
  const glowColor = useMemo(() => {
    const colors: Record<string, string> = {
      "↔": "#9933ff", // entanglement
      "⧖": "#00e0ff", // time
      "🧬": "#66ff99", // DNA/mutation
    };
    return colors[glyph ?? ""] ?? "#88a";
  }, [glyph]);

  /** ===== Spin animation ===== **/
  useFrame(() => {
    if (!groupRef.current) return;
    if (active) groupRef.current.rotation.y += 0.01;
    if (runtimeTick % 2 === 1) groupRef.current.rotation.x += 0.002;
  });

  return (
    <animated.group
      ref={groupRef}
      position={position ?? vizPos ?? [0, 0, 0]}
      scale={animatedScale}
    >
      {/* === Core Atom Mesh === */}
      <mesh>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial
          color={glowColor}
          emissive={glowColor}
          emissiveIntensity={0.9}
          metalness={0.1}
          roughness={0.5}
          transparent
          opacity={0.18}
        />
      </mesh>

      {/* === Halo === */}
      <mesh>
        <sphereGeometry args={[1.35, 32, 32]} />
        <meshStandardMaterial
          color={glowColor}
          emissive={glowColor}
          emissiveIntensity={0.4}
          transparent
          opacity={0.06}
        />
      </mesh>

      {/* === Entanglement Ring (↔) === */}
      {glyph === "↔" && (
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[1.5, 1.7, 64]} />
          <meshBasicMaterial
            color="#cc66ff"
            transparent
            opacity={0.4}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}

      {/* === Label === */}
      <Html distanceFactor={12}>
        <div
          style={{
            fontSize: "0.6rem",
            color: "#ccc",
            textAlign: "center",
            marginTop: "4px",
            background: "#0008",
            padding: "2px 6px",
            borderRadius: 6,
          }}
        >
          {container?.name ?? containerId} • {id}
        </div>
      </Html>
    </animated.group>
  );
};

export default AtomContainer;