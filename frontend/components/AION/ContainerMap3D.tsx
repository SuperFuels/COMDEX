// File: frontend/components/AION/ContainerMap3D.tsx

import React, { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import WormholeRenderer from "./WormholeRenderer";

interface ContainerInfo {
  id: string;
  name: string;
  in_memory: boolean;
  connected: string[];
  glyph?: string;
  region?: string;
}

interface ContainerMap3DProps {
  containers?: ContainerInfo[];
  activeId?: string;
  layout?: "ring" | "grid" | "sphere";
  onTeleport?: (id: string) => void;
}

const getPosition = (
  index: number,
  total: number,
  layout: "ring" | "grid" | "sphere"
): [number, number, number] => {
  if (layout === "grid") {
    const size = Math.ceil(Math.sqrt(total));
    const x = index % size;
    const z = Math.floor(index / size);
    return [x * 2 - size, 0, z * 2 - size];
  }
  if (layout === "sphere") {
    const phi = Math.acos(-1 + (2 * index) / total);
    const theta = Math.sqrt(total * Math.PI) * phi;
    const r = 6;
    return [
      r * Math.cos(theta) * Math.sin(phi),
      r * Math.sin(theta) * Math.sin(phi),
      r * Math.cos(phi),
    ];
  }
  // Default ring layout
  const angle = (index / total) * Math.PI * 2;
  const radius = 6;
  const height = (index % 3) * 2;
  return [Math.cos(angle) * radius, height, Math.sin(angle) * radius];
};

function ContainerNode({
  container,
  position,
  active,
  onClick,
}: {
  container: ContainerInfo;
  position: [number, number, number];
  active: boolean;
  onClick: (id: string) => void;
}) {
  const meshRef = useRef<any>();

  useFrame(() => {
    if (meshRef.current && active) {
      meshRef.current.rotation.y += 0.01;
    }
  });

  const color = active ? "#4fc3f7" : container.in_memory ? "#8bc34a" : "#666";

  return (
    <mesh position={position} ref={meshRef} onClick={() => onClick(container.id)}>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color={color} />
      <Html distanceFactor={8} style={{ fontSize: "0.7rem", textAlign: "center" }}>
        <div>{container.name}</div>
        {container.glyph && <div style={{ color: "#ccc" }}>{container.glyph}</div>}
      </Html>
    </mesh>
  );
}

export default function ContainerMap3D({
  containers = [],
  activeId,
  layout = "ring",
  onTeleport,
}: ContainerMap3DProps) {
  const positions = useMemo(() => {
    const posMap: Record<string, [number, number, number]> = {};
    if (Array.isArray(containers)) {
      containers.forEach((c, i) => {
        posMap[c.id] = getPosition(i, containers.length, layout);
      });
    }
    return posMap;
  }, [containers, layout]);

  return (
    <div className="w-full h-[600px] border rounded bg-black">
      <Canvas camera={{ position: [0, 10, 15], fov: 60 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 10, 5]} intensity={0.7} />
        <OrbitControls />

        {containers.map((container) => (
          <ContainerNode
            key={container.id}
            container={container}
            position={positions[container.id]}
            active={container.id === activeId}
            onClick={onTeleport || (() => {})}
          />
        ))}

        {containers.flatMap((container) =>
          (container.connected || []).map((link) => {
            const from = positions[container.id];
            const to = positions[link];
            if (!from || !to) return null;

            return (
              <WormholeRenderer
                key={`${container.id}->${link}`}
                from={from}
                to={to}
                color="#66f"
                thickness={0.025}
                glyph="↔"
                mode="glow"
                pulse
                pulseFlow
              />
            );
          })
        )}
      </Canvas>
    </div>
  );
}
