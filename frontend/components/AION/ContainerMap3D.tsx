'use client';

import React, { useRef, useMemo, useState, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import axios from "axios";

import WormholeRenderer from "./WormholeRenderer";
import GlyphSprite from "./GlyphSprite";
import RuntimeGlyphTrace from "@/components/codex/RuntimeGlyphTrace";
import HobermanSphere from "../ContainerMap/HobermanSphere";
import SymbolicExpansionSphere from "../ContainerMap/SymbolicExpansionSphere";
import WarpDriveNavigator from "@/components/AION/WarpDriveNavigator";
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
  TetrahedronRenderer,
  AtomContainerRenderer,
} from "@/components/AION/renderers";

export function drawLinkArrows(containerLinks: Record<string, any>) {
  Object.entries(containerLinks).forEach(([source, nav]) => {
    Object.entries(nav).forEach(([direction, target]) => {
      console.log(`🎨 Draw arrow: ${source} → ${target} (${direction})`);
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

type EngineState = {
  stage?: string;
  engineStage?: string;
  fields: Record<string, number>;
  nested_containers?: { id: string; type: string; glyph: string }[];
  particles?: { x: number; y: number; z: number }[];
};

// If your API is under /api/aion/containers, keep it consistent:
const fetchContainersAPI = "/api/aion/containers";

const defaultZones = [
  { id: "hq", name: "Tessaris HQ", position: [0, 0, 0], layer: "inner" as const },
  { id: "qwaves", name: "Quantum Waves", position: [20, 10, -15], layer: "outer" as const },
  { id: "deep-lab", name: "Deep Lab 7", position: [-25, -5, 30], layer: "deep" as const },
  { id: "aion-home", name: "AION Home", position: [15, 20, 25], layer: "outer" as const },
];

export default function ContainerMap3D({
  containers,
  layout = "ring",
  activeId,
  onTeleport,
}: ContainerMap3DProps) {
  const [engineState, setEngineState] = useState<EngineState>({
    stage: "Idle",
    fields: { gravity: 0, magnetism: 0, wave_frequency: 0 },
    nested_containers: [],
    particles: [],
  });

  const [fieldValues, setFieldValues] = useState({ gravity: 0, magnetism: 0, wave_frequency: 0 });

  useEffect(() => {
    const interval = setInterval(() => {
      axios.get("/api/aion/engine/qwave/fields").then((res) => {
        setFieldValues(res.data.fields);
        setEngineState((prev) => ({ ...prev, engineStage: res.data.stage || "Idle" }));
      }).catch(() => {});
    }, 1000);
    return () => clearInterval(interval);
  }, []);

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
      const tickPulse = container.runtime_tick
        ? Math.sin(container.runtime_tick / 4) * 0.1
        : 0;
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
          {/* Work around three/@types-three version mismatch */}
          {/* eslint-disable-next-line @typescript-eslint/ban-ts-comment */}
          {/* @ts-ignore */}
          <edgesGeometry args={[new (THREE as any).BoxGeometry(1, 1, 1)]} />
          <lineBasicMaterial
            color={shouldGlow ? "#aa00ff" : color}
            linewidth={2}
          />
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
            {container.glyph && (
              <div style={{ fontSize: "1.2rem" }}>{container.glyph}</div>
            )}
            {symbolicScale && (
              <div style={{ fontSize: "0.6rem", opacity: 0.7 }}>
                Logic: {container.logic_depth || 0}, Tick:{" "}
                {container.runtime_tick || 0}, Mem:{" "}
                {container.memory_count || 0}
              </div>
            )}
          </div>
        </Html>

        {container.glyph && (
          <GlyphSprite position={position} glyph={container.glyph} />
        )}
      </group>
    );
  }

  function ProtonFieldParticles({ zone }: { zone: string | null }) {
    // NOTE: use `any` here to avoid three/@types-three type mismatches
    const group = useRef<any>(null);

    const [fields, setFields] = useState<{
      gravity: number;
      magnetism: number;
      wave_frequency: number;
    }>({
      gravity: 0,
      magnetism: 0,
      wave_frequency: 0,
    });

    const particles = useMemo(() => {
      const count = 200;
      const arr: { pos: THREE.Vector3; vel: THREE.Vector3 }[] = [];
      for (let i = 0; i < count; i++) {
        arr.push({
          pos: new THREE.Vector3(
            (Math.random() - 0.5) * 20,
            (Math.random() - 0.5) * 20,
            (Math.random() - 0.5) * 20
          ),
          vel: new THREE.Vector3(
            (Math.random() - 0.5) * 0.02,
            (Math.random() - 0.5) * 0.02,
            (Math.random() - 0.5) * 0.02
          ),
        });
      }
      return arr;
    }, [zone]);

    useEffect(() => {
      const interval = setInterval(() => {
        axios
          .get("/api/aion/engine/qwave/fields")
          .then((res) => {
            setFields(
              res.data.fields || {
                gravity: 0,
                magnetism: 0,
                wave_frequency: 0,
              }
            );
          })
          .catch(() => {});
      }, 1000);
      return () => clearInterval(interval);
    }, []);

    useFrame(({ clock }) => {
      particles.forEach((p) => {
        const gravityForce = p.pos
          .clone()
          .normalize()
          .multiplyScalar(-fields.gravity * 0.002);
        const magnetismForce = new THREE.Vector3(
          -p.pos.z,
          0,
          p.pos.x
        )
          .normalize()
          .multiplyScalar(fields.magnetism * 0.002);
        const waveForce =
          Math.sin(clock.elapsedTime * fields.wave_frequency) * 0.002;

        p.vel.add(gravityForce).add(magnetismForce);
        p.pos.add(p.vel.multiplyScalar(0.98));
        p.pos.y += waveForce;
      });

      if (group.current) {
        group.current.rotation.y += 0.0005;
      }
    });

    return (
      <group ref={group}>
        {particles.map((p, i) => (
          <mesh key={i} position={p.pos.toArray()}>
            <sphereGeometry args={[0.08, 8, 8]} />
            <meshStandardMaterial
              color={i % 2 === 0 ? "#00f0ff" : "#ff00ff"}
              emissive={i % 2 === 0 ? "#00f0ff" : "#ff00ff"}
              emissiveIntensity={2}
              transparent
              opacity={0.7}
            />
          </mesh>
        ))}
      </group>
    );
  }

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
      case "atom_container":
        return <AtomContainerRenderer key={container.id} position={pos} container={container} />;
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

  const [realContainers, setRealContainers] = useState<ContainerInfo[]>([]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [symbolicScale, setSymbolicScale] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeZone, setActiveZone] = useState<string | null>("hq");
  const [selectedZone, setSelectedZone] = useState<string>("hq");

  useEffect(() => {
    if (containers) {
      setRealContainers(containers);
      setLoading(false);
      return;
    }
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
  }, [containers]);

  useEffect(() => {
    if (!selectedZone) return;
    setLoading(true);
    axios
      .get(`/api/aion/containers/zone/${selectedZone}`)
      .then((response) => {
        setRealContainers(response.data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [selectedZone]);

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

  const isLinked: (id: string) => boolean = (id) =>
    !!hoveredId && zoneFilteredContainers.some(
      (c) => c.id === hoveredId && (c.connected ?? []).includes(id)
    );

  const sortedContainers = useMemo(
    () => [...zoneFilteredContainers].sort((a, b) => (b.logic_depth || 0) - (a.logic_depth || 0)),
    [zoneFilteredContainers]
  );

  useEffect(() => {
    const linkMap: Record<string, any> = {};
    zoneFilteredContainers.forEach((c) => {
      linkMap[c.id] = (c.connected ?? []).reduce((acc: any, linkId: string) => {
        acc.linked = linkId;
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

  const stage: string | undefined =
    (engineState as any)?.engineStage ?? engineState?.stage;

  const zonesForHud = defaultZones.map((z) => ({
    ...z,
    position: [z.position?.[0] ?? 0, z.position?.[1] ?? 0, z.position?.[2] ?? 0] as [number, number, number],
  }));

  return (
    <>
      {/* OrbitControls live in the Canvas wrapper */}
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1.2} />

      <ProtonFieldParticles zone={activeZone} />

      <WarpDriveNavigator
        zones={zonesForHud}
        onWarpComplete={(z) => setActiveZone(z)}
      />

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
            />{" "}
            Symbolic Scale
          </label>
        </div>
      </Html>

      <Html position={[4.5, 3, 0]} transform>
        <div style={{ width: 340 }}>
          <RuntimeGlyphTrace />
        </div>
      </Html>

      <Html position={[0, -3, 0]}>
        <div
          style={{
            background: "#000a",
            padding: "12px",
            borderRadius: "8px",
            width: "240px",
            color: "#fff",
            fontSize: "0.75rem",
          }}
        >
          <h4 style={{ margin: "0 0 8px 0", color: "#00f0ff" }}>⚛ QWave Fields</h4>

          <div
            style={{
              marginBottom: "10px",
              fontSize: "0.8rem",
              color: "#0ff",
              fontWeight: "bold",
            }}
          >
            Stage: {stage ?? "Initializing..."}
          </div>

          {(["gravity", "magnetism", "wave_frequency"] as const).map((field) => (
            <div key={field} style={{ marginBottom: "6px" }}>
              <label style={{ display: "block", marginBottom: "2px" }}>
                {field} ({fieldValues[field] !== undefined ? fieldValues[field].toFixed(2) : "0.00"})
              </label>
              <input
                type="range"
                min={-10}
                max={10}
                step={0.1}
                value={fieldValues[field] ?? 0}
                onChange={(e) => {
                  const val = parseFloat(e.target.value);
                  setFieldValues((prev) => ({ ...prev, [field]: val }));
                  axios.post("/api/aion/engine/qwave/fields", { field, value: val });
                }}
                style={{ width: "100%" }}
              />
            </div>
          ))}

          <button
            style={{
              width: "100%",
              marginTop: "8px",
              padding: "6px",
              background: "#00f0ff",
              color: "#000",
              fontWeight: "bold",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
            onClick={() => axios.post("/api/aion/engine/qwave/advance")}
          >
            🔄 Advance Stage
          </button>

          <button
            style={{
              width: "100%",
              marginTop: "6px",
              padding: "6px",
              background: "#444",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
            onClick={async () => {
              await axios.post("/api/aion/engine/qwave/save");
              const res = await axios.get("/api/aion/engine/qwave/state");
              setEngineState(res.data);
            }}
          >
            💾 Save State
          </button>
          <button
            style={{
              width: "100%",
              marginTop: "4px",
              padding: "6px",
              background: "#666",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
            onClick={async () => {
              await axios.post("/api/aion/engine/qwave/load");
              const res = await axios.get("/api/aion/engine/qwave/state");
              setEngineState(res.data);
            }}
          >
            ♻️ Load State
          </button>
        </div>
      </Html>

      {(engineState?.nested_containers ?? []).map((nested, i, arr) => {
        const angle = (i / Math.max(arr.length, 1)) * Math.PI * 2;
        const radius = 2;
        const pos: [number, number, number] = [
          Math.cos(angle) * radius,
          0,
          Math.sin(angle) * radius,
        ];

        const fakeContainer = {
          id: nested.id,
          name: nested.id,
          glyph: nested.glyph,
          logic_depth: 3,
          runtime_tick: Date.now() / 100,
          symbolic_mode: nested.type,
          in_memory: true,
          connected: [] as string[],
        };

        return (
          <group
            key={`nested-${nested.id}`}
            position={[0, 0, 0]}
            rotation={[0, (Date.now() / 1000) * 0.2 * (i + 1), 0]}
          >
            {renderContainerVisual(
              fakeContainer,
              pos,
              activeId,
              isLinked,
              onTeleport,
              setHoveredId,
              true
            )}

            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[pos[0], pos[1] - 0.5, pos[2]]}>
              <ringGeometry args={[1.2, 1.4, 64]} />
              <meshBasicMaterial color="#ffffff" transparent opacity={0.4} />
            </mesh>
          </group>
        );
      })}

      <group>
        {(engineState?.particles ?? []).map((p, idx) => (
          <mesh key={`particle-${idx}`} position={[p.x, p.y, p.z]}>
            <sphereGeometry args={[0.05, 8, 8]} />
            <meshStandardMaterial
              color="#00f0ff"
              emissive="#00f0ff"
              emissiveIntensity={2}
              transparent
              opacity={0.8}
            />
          </mesh>
        ))}
      </group>

      {sortedContainers.map((container) => {
        const pos = positions[container.id] as [number, number, number];
        return (
          <React.Fragment key={container.id}>
            {renderContainerVisual(
              container,
              pos,
              activeId,
              isLinked,
              onTeleport,
              setHoveredId,
              symbolicScale
            )}
          </React.Fragment>
        );
      })}

      {zoneFilteredContainers.flatMap((container) =>
        (container.connected ?? []).map((link) => {
          const from = positions[container.id] as [number, number, number] | undefined;
          const to = positions[link] as [number, number, number] | undefined;
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