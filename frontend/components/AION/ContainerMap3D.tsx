import React, { useRef, useEffect, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";

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
  onTeleport?: (id: string) => void;
}

const getPosition = (index: number, total: number): [number, number, number] => {
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

  const color = active ? "#4fc3f7" : container.in_memory ? "#8bc34a" : "#aaa";

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
  onTeleport,
}: ContainerMap3DProps) {
  const positions = useMemo(() => {
    const posMap: Record<string, [number, number, number]> = {};
    if (Array.isArray(containers)) {
      containers.forEach((c, i) => {
        posMap[c.id] = getPosition(i, containers.length);
      });
    }
    return posMap;
  }, [containers]);

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

        {containers.flatMap((source) =>
          source.connected.map((targetId) => {
            const from = positions[source.id];
            const to = positions[targetId];
            if (!from || !to) return null;
            const mid: [number, number, number] = [
              (from[0] + to[0]) / 2,
              (from[1] + to[1]) / 2,
              (from[2] + to[2]) / 2,
            ];
            return (
              <mesh key={`${source.id}->${targetId}`} position={mid}>
                <cylinderGeometry args={[0.02, 0.02, 1]} />
                <meshStandardMaterial color="#999" />
              </mesh>
            );
          })
        )}
      </Canvas>
    </div>
  );
}