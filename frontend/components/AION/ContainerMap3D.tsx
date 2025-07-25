import React, { useRef, useMemo, useState, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import WormholeRenderer from "./WormholeRenderer";
import GlyphSprite from "./GlyphSprite";

interface ContainerInfo {
  id: string;
  name: string;
  in_memory: boolean;
  connected: string[];
  glyph?: string;
  region?: string;
  logic_depth?: number;
  runtime_tick?: number;
  memory_count?: number;
}

interface ContainerMap3DProps {
  containers?: ContainerInfo[];
  activeId?: string;
  layout?: "ring" | "grid" | "sphere";
  onTeleport?: (id: string) => void;
}

const dummyContainers: ContainerInfo[] = [
  { id: "A", name: "Alpha", in_memory: true, connected: ["B"], glyph: "🌐", logic_depth: 2 },
  { id: "B", name: "Beta", in_memory: false, connected: ["A", "C"], glyph: "💠", logic_depth: 5 },
  { id: "C", name: "Gamma", in_memory: true, connected: ["B"], glyph: "✨", logic_depth: 8 },
];

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
  const angle = (index / total) * Math.PI * 2;
  const radius = 6;
  const height = (index % 3) * 2;
  return [Math.cos(angle) * radius, height, Math.sin(angle) * radius];
};

function HolodeckCube({
  container,
  position,
  active,
  linked,
  onClick,
  onHover,
  symbolicScale,
}: {
  container: ContainerInfo;
  position: [number, number, number];
  active: boolean;
  linked: boolean;
  onClick: (id: string) => void;
  onHover: (id: string | null) => void;
  symbolicScale: boolean;
}) {
  const ref = useRef<any>();
  const scaleFactor = symbolicScale ? (1 + (container.logic_depth || 0) / 10) : 1;
  const color = active
    ? "#4fc3f7"
    : linked
    ? "#ff9800"
    : container.in_memory
    ? "#8bc34a"
    : "#555";

  useFrame(() => {
    if (ref.current && active) {
      ref.current.rotation.y += 0.005;
    }
  });

  return (
    <group
      ref={ref}
      position={position}
      scale={[scaleFactor, scaleFactor, scaleFactor]}
      onClick={() => onClick(container.id)}
      onPointerOver={() => onHover(container.id)}
      onPointerOut={() => onHover(null)}
    >
      {/* Transparent box */}
      <mesh>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial
          color={color}
          transparent
          opacity={0.1}
          emissive={color}
          emissiveIntensity={1.5}
        />
      </mesh>

      {/* Edge glow lines */}
      <lineSegments>
        <edgesGeometry args={[new THREE.BoxGeometry(1, 1, 1)]} />
        <lineBasicMaterial color={color} linewidth={2} />
      </lineSegments>

      {/* Floating inner sphere */}
      <mesh position={[0, 0.2, 0]}>
        <sphereGeometry args={[0.2, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={3}
          transparent
          opacity={0.5}
        />
      </mesh>

      {/* Floating HUD terminal */}
      <Html distanceFactor={10} style={{ pointerEvents: "none" }}>
        <div style={{ fontSize: "0.7rem", color: "#00f0ff", textAlign: "center" }}>
          <div>{container.name}</div>
          <div style={{ opacity: 0.6 }}>{container.in_memory ? "🧠 In-Memory" : "💾 Loaded"}</div>
          {container.glyph && <div style={{ fontSize: "1.2rem" }}>{container.glyph}</div>}
          {symbolicScale && (
            <div style={{ fontSize: "0.6rem", opacity: 0.7 }}>
              Logic: {container.logic_depth || 0}, Tick: {container.runtime_tick || 0}, Mem: {container.memory_count || 0}
            </div>
          )}
        </div>
      </Html>

      {/* Optional Glyph Sprite */}
      {container.glyph && <GlyphSprite position={position} glyph={container.glyph} />}
    </group>
  );
}

export default function ContainerMap3D({
  containers,
  activeId,
  layout = "ring",
  onTeleport,
}: ContainerMap3DProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [realContainers, setRealContainers] = useState<ContainerInfo[]>([]);
  const [symbolicScale, setSymbolicScale] = useState<boolean>(true);

  useEffect(() => {
    if (!containers || containers.length === 0) {
      setRealContainers(dummyContainers);
    } else {
      setRealContainers(containers);
    }
  }, [containers]);

  const positions = useMemo(() => {
    const posMap: Record<string, [number, number, number]> = {};
    realContainers.forEach((c, i) => {
      posMap[c.id] = getPosition(i, realContainers.length, layout);
    });
    return posMap;
  }, [realContainers, layout]);

  const isLinked = (id: string) =>
    hoveredId && realContainers.some((c) => c.id === hoveredId && c.connected.includes(id));

  const sortedContainers = useMemo(() => {
    return [...realContainers].sort((a, b) => (b.logic_depth || 0) - (a.logic_depth || 0));
  }, [realContainers]);

  return (
    <>
      <OrbitControls />
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1.2} />

      <Html position={[-4, 3, 0]}>
        <div style={{ background: "#0008", padding: "4px 8px", borderRadius: 8, fontSize: "0.7rem", color: "#fff" }}>
          <label>
            <input
              type="checkbox"
              checked={symbolicScale}
              onChange={() => setSymbolicScale(!symbolicScale)}
            />
            Symbolic Scale
          </label>
        </div>
      </Html>

      {sortedContainers.map((container) => (
        <HolodeckCube
          key={container.id}
          container={container}
          position={positions[container.id]}
          active={container.id === activeId}
          linked={!!isLinked(container.id)}
          onClick={onTeleport || (() => {})}
          onHover={setHoveredId}
          symbolicScale={symbolicScale}
        />
      ))}

      {realContainers.flatMap((container) =>
        (container.connected || []).map((link) => {
          const from = positions[container.id];
          const to = positions[link];
          if (!from || !to) return null;

          return (
            <WormholeRenderer
              key={`${container.id}->${link}`}
              from={from}
              to={to}
              color="#f69"
              thickness={0.025}
              glyph="↔"
              mode="glow"
              pulse
              pulseFlow
            />
          );
        })
      )}
    </>
  );
}