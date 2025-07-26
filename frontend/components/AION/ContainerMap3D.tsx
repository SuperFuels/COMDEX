import React, { useRef, useMemo, useState, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import axios from "axios";
import WormholeRenderer from "./WormholeRenderer";
import GlyphSprite from "./GlyphSprite";
import RuntimeGlyphTrace from "@/components/codex/RuntimeGlyphTrace";
import HobermanSphere from "../ContainerMap/HobermanSphere";
import SymbolicExpansionSphere from "../ContainerMap/SymbolicExpansionSphere";

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
  symbolic_mode?: string;
  soul_locked?: boolean;
}

interface ContainerMap3DProps {
  containers?: ContainerInfo[];
  layout?: "ring" | "grid" | "sphere";
  activeId?: string;
  onTeleport?: (id: string) => void;
}

const fetchContainersAPI = "/api/containers";

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

  const scaleFactor = useMemo(() => {
    const base = symbolicScale ? 1 + (container.logic_depth || 0) / 10 : 1;
    const tickPulse = container.runtime_tick ? Math.sin(container.runtime_tick / 4) * 0.1 : 0;
    return base + tickPulse;
  }, [container.logic_depth, container.runtime_tick, symbolicScale]);

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

  const shouldGlow = container.glyph === "↔";
  const shouldTrail = ["↔", "🧬", "⧖"].includes(container.glyph || "");

  return (
    <group
      ref={ref}
      position={position}
      scale={[scaleFactor, scaleFactor, scaleFactor]}
      onClick={() => onClick(container.id)}
      onPointerOver={() => onHover(container.id)}
      onPointerOut={() => onHover(null)}
    >
      <mesh visible={!container.soul_locked}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial
          color={color}
          transparent
          opacity={0.1}
          emissive={color}
          emissiveIntensity={1.5}
        />
      </mesh>

      <lineSegments>
        <edgesGeometry args={[new THREE.BoxGeometry(1, 1, 1)]} />
        <lineBasicMaterial color={shouldGlow ? "#aa00ff" : color} linewidth={2} />
      </lineSegments>

      {shouldTrail && (
        <mesh position={[0, 0.5, 0]}>
          <torusGeometry args={[0.4, 0.03, 8, 32]} />
          <meshStandardMaterial
            color="#ffffff"
            emissive="#00f0ff"
            emissiveIntensity={1}
            transparent
            opacity={0.4}
          />
        </mesh>
      )}

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

      <Html distanceFactor={10} style={{ pointerEvents: "none" }}>
        <div style={{ fontSize: "0.7rem", color: "#00f0ff", textAlign: "center" }}>
          <div>{container.name}</div>
          <div style={{ opacity: 0.6 }}>
            {container.in_memory ? "🧠 In-Memory" : "💾 Loaded"}
          </div>
          {container.glyph && <div style={{ fontSize: "1.2rem" }}>{container.glyph}</div>}
          {symbolicScale && (
            <div style={{ fontSize: "0.6rem", opacity: 0.7 }}>
              Logic: {container.logic_depth || 0}, Tick: {container.runtime_tick || 0}, Mem:{" "}
              {container.memory_count || 0}
            </div>
          )}
        </div>
      </Html>

      {container.glyph && <GlyphSprite position={position} glyph={container.glyph} />}
    </group>
  );
}

export default function ContainerMap3D({
  containers,
  layout = "ring",
  activeId,
  onTeleport,
}: ContainerMap3DProps) {
  const [realContainers, setRealContainers] = useState<ContainerInfo[]>([]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [symbolicScale, setSymbolicScale] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (containers) {
      setRealContainers(containers);
      setLoading(false);
    } else {
      axios
        .get(fetchContainersAPI)
        .then((response) => {
          setRealContainers(response.data.containers);
          setLoading(false);
          setError(null);
        })
        .catch((err) => {
          setError("Failed to load containers.");
          setLoading(false);
          console.error(err);
        });
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

  if (loading) {
    return (
      <Html position={[0, 0, 0]}>
        <div style={{ color: "#00f0ff" }}>Loading containers...</div>
      </Html>
    );
  }

  if (error) {
    return (
      <Html position={[0, 0, 0]}>
        <div style={{ color: "red" }}>{error}</div>
      </Html>
    );
  }

  return (
    <>
      <OrbitControls />
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1.2} />

      <Html position={[-4, 3, 0]}>
        <div
          style={{
            background: "#0008",
            padding: "4px 8px",
            borderRadius: 8,
            fontSize: "0.7rem",
            color: "#fff",
          }}
        >
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

      <Html position={[4.5, 3, 0]} transform>
        <div style={{ width: 340 }}>
          <RuntimeGlyphTrace />
        </div>
      </Html>

      {sortedContainers.map((container) => {
        const pos = positions[container.id];
        return (
          <React.Fragment key={container.id}>
            {container.symbolic_mode === "expansion" && (
              <SymbolicExpansionSphere
                containerId={container.id}
                expandedLogic={{ logic_tree: { depth: container.logic_depth || 1 } }}
                runtimeTick={container.runtime_tick}
                glyphOverlay={[container.glyph || ""]}
                isEntangled={container.glyph === "↔"}
                isCollapsed={container.glyph === "⧖"}
                mode="depth"
              />
            )}

            <HobermanSphere
              position={pos}
              containerId={container.id}
              active={container.id === activeId}
              glyph={container.glyph}
              logicDepth={container.logic_depth}
              runtimeTick={container.runtime_tick}
            />

            <HolodeckCube
              container={container}
              position={pos}
              active={container.id === activeId}
              linked={!!isLinked(container.id)}
              onClick={onTeleport || (() => {})}
              onHover={setHoveredId}
              symbolicScale={symbolicScale}
            />
          </React.Fragment>
        );
      })}

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