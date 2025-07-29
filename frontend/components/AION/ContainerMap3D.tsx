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
import WarpDriveNavigator from "@/components/AION/WarpDriveNavigator"; // ✅ Warp Drive Integration
import {
  BlackHoleRenderer,
  DNASpiralRenderer,
  DodecahedronRenderer,
  FractalCrystalRenderer,
  IcosahedronRenderer,
  MemoryPearlRenderer,
  MirrorContainerRenderer,
  OctahedronRenderer,
  QuantumOrdRenderer,
  TesseractRenderer,
  TorusRenderer,
  VortexRenderer,
  TetrahedronRenderer
} from "@/components/AION/renderers";

// ✅ GHXVisualizer directional arrows stub
export function drawLinkArrows(containerLinks: Record<string, any>) {
  Object.entries(containerLinks).forEach(([source, nav]) => {
    Object.entries(nav).forEach(([direction, target]) => {
      console.log(`🎨 Draw arrow: ${source} → ${target} (${direction})`);
      // TODO: Render directional arrow in GHX canvas
    });
  });
}

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

// ✅ Warp Drive Zones
const defaultZones = [
  { id: "hq", name: "Tessaris HQ", position: [0, 0, 0], layer: "inner" as const },
  { id: "qwaves", name: "Quantum Waves", position: [20, 10, -15], layer: "outer" as const },
  { id: "deep-lab", name: "Deep Lab 7", position: [-25, -5, 30], layer: "deep" as const },
  { id: "aion-home", name: "AION Home", position: [15, 20, 25], layer: "outer" as const },
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

  // ✅ NEW: Dynamic container renderer for SEC, HSC, and all 13 symbolic container types
  const renderContainerVisual = (
    container: ContainerInfo,
    pos: [number, number, number],
    activeId: string | undefined,
    isLinked: (id: string) => boolean,
    onTeleport: ((id: string) => void) | undefined,
    setHoveredId: (id: string | null) => void,
    symbolicScale: boolean
  ) => {
    switch (container.symbolic_mode) {
      // ✅ SEC (Symbolic Expansion Container)
      case "expansion":
        return (
          <SymbolicExpansionSphere
            key={`${container.id}-expansion`}
            containerId={container.id}
            expandedLogic={{ logic_tree: { depth: container.logic_depth || 1 } }}
            runtimeTick={container.runtime_tick}
            glyphOverlay={[container.glyph || ""]}
            isEntangled={container.glyph === "↔"}
            isCollapsed={container.glyph === "⧖"}
            mode="depth"
          />
        );

      // ✅ HSC (Hoberman Sphere Container)
      case "hoberman":
        return (
          <HobermanSphere
            key={`${container.id}-hoberman`}
            position={pos}
            containerId={container.id}
            active={container.id === activeId}
            glyph={container.glyph}
            logicDepth={container.logic_depth}
            runtimeTick={container.runtime_tick}
          />
        );

      // ✅ 13 New Symbolic Container Types
  // ✅ The 13 symbolic container types
      case "black_hole":
        return <BlackHoleRenderer key={container.id} position={pos} container={container} />;
      case "dna_spiral":
        return <DNASpiralRenderer key={container.id} position={pos} container={container} />;
      case "dodecahedron":
        return <DodecahedronRenderer key={container.id} position={pos} container={container} />;
      case "fractal_crystal":
        return <FractalCrystalRenderer key={container.id} position={pos} container={container} />;
      case "icosahedron":
        return <IcosahedronRenderer key={container.id} position={pos} container={container} />;
      case "memory_pearl":
        return <MemoryPearlRenderer key={container.id} position={pos} container={container} />;
      case "mirror_container":
        return <MirrorContainerRenderer key={container.id} position={pos} container={container} />;
      case "octahedron":
        return <OctahedronRenderer key={container.id} position={pos} container={container} />;
      case "quantum_ord":
        return <QuantumOrdRenderer key={container.id} position={pos} container={container} />;
      case "tesseract":
        return <TesseractRenderer key={container.id} position={pos} container={container} />;
      case "torus":
        return <TorusRenderer key={container.id} position={pos} container={container} />;
      case "vortex":
        return <VortexRenderer key={container.id} position={pos} container={container} />;
      case "tetrahedron":
        return <TetrahedronRenderer key={container.id} position={pos} container={container} />;


      // 🧊 Default fallback HolodeckCube (if no symbolic_mode match)
      default:
        return (
          <HolodeckCube
            key={`${container.id}-cube`}
            container={container}
            position={pos}
            active={container.id === activeId}
            linked={!!isLinked(container.id)}
            onClick={onTeleport || (() => {})}
            onHover={setHoveredId}
            symbolicScale={symbolicScale}
          />
        );
    }
  };

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
  const [activeZone, setActiveZone] = useState<string | null>("hq");
  const [selectedZone, setSelectedZone] = useState<string>("hq"); // default zone

  // ✅ Fetch containers, filtered by WarpDrive zone if provided
  useEffect(() => {
    if (containers) {
      setRealContainers(containers);
      setLoading(false);
    } else {
      // Default: fetch all containers first
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

  // ✅ NEW: Listen for zone warp and fetch containers for that zone
  useEffect(() => {
    if (!selectedZone) return;
    setLoading(true);
    axios
      .get(`/api/aion/containers/zone/${selectedZone}`)
      .then((response) => {
        setRealContainers(response.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch zone containers", err);
        setLoading(false);
      });
  }, [selectedZone]);

  // Zone filter for Warp Drive
  const zoneFilteredContainers = useMemo(() => {
    if (!activeZone) return realContainers;
    return realContainers.filter((c) => !c.region || c.region === activeZone);
  }, [realContainers, activeZone]);

  const positions = useMemo(() => {
    const posMap: Record<string, [number, number, number]> = {};
    zoneFilteredContainers.forEach((c, i) => {
      posMap[c.id] = getPosition(i, zoneFilteredContainers.length, layout);
    });
    return posMap;
  }, [zoneFilteredContainers, layout]);

  const isLinked = (id: string) =>
    hoveredId && zoneFilteredContainers.some((c) => c.id === hoveredId && c.connected.includes(id));

  const sortedContainers = useMemo(() => {
    return [...zoneFilteredContainers].sort((a, b) => (b.logic_depth || 0) - (a.logic_depth || 0));
  }, [zoneFilteredContainers]);

  // ✅ GHX directional arrows
  useEffect(() => {
    const linkMap: Record<string, any> = {};
    zoneFilteredContainers.forEach((c) => {
      linkMap[c.id] = c.connected.reduce((acc: any, linkId: string) => {
        acc["linked"] = linkId;
        return acc;
      }, {});
    });
    drawLinkArrows(linkMap);
  }, [zoneFilteredContainers]);

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

    {/* ✅ Warp Drive Navigator HUD */}
      <WarpDriveNavigator 
        zones={defaultZones} 
        onWarpComplete={(z) => setActiveZone(z)} 
      />

      {/* ✅ Symbolic Scale HUD */}
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

      {/* ✅ Dynamic Container Renderer */}
      {sortedContainers.map((container) => {
        const pos = positions[container.id];
        return (
          <React.Fragment key={container.id}>
            {renderContainerVisual(container, pos, activeId, isLinked, onTeleport, setHoveredId, symbolicScale)}
          </React.Fragment>
        );
      })}

      {/* ✅ Wormhole Rendering */}
      {zoneFilteredContainers.flatMap((container) =>
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