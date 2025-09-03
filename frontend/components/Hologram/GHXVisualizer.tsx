import { Canvas, useFrame } from '@react-three/fiber';
import { Html, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import GHXSignatureTrail from './GHXSignatureTrail';
import axios from 'axios';
import useWebSocket from '../../hooks/useWebSocket';
import React, { useMemo, useRef, useState, useEffect } from "react";
import { ElectronShells, buildElectronShells, ElectronOrbit } from "@/components/GHX/atoms/electronOrbit";
import { GHXReplaySelector } from '@/components/GHX/GHXReplaySelector';
import { GHXTeleportTrail } from '@/components/GHX/GHXTeleportTrail';
import { GHXAnchorMemory } from '@/components/GHX/GHXAnchorMemory';
import { SymbolicTeleportPath } from '@/components/GHX/SymbolicTeleportPath';
import { DreamGhostEntry } from '@/components/GHX/DreamGhostEntry';
import { getSignatureStatusBadge } from "@/utils/ghx_signature_utils";

declare global {
  interface Window {
    GHX_ON_TELEPORT?: (cid: string) => void;
  }
}
// ✅ GHXVisualizer Arrows Stub (Nav Map Visualization)
export function drawLinkArrows(containerLinks: Record<string, any>) {
  Object.entries(containerLinks).forEach(([source, nav]) => {
    Object.entries(nav).forEach(([direction, target]) => {
      console.log(`🎨 Draw arrow: ${source} → ${target} (${direction})`);
      // TODO: Render directional arrow in GHX canvas
    });
  });
}
// 🔗 HOV backend-baked metadata (per-hover)
  const [hoverCid, setHoverCid] = useState<string | null>(null);
  const [hoverMeta, setHoverMeta] = useState<any>(null);
// --- HOV hover fetch helper (backend ↔ frontend) ---
const fetchHoverGHX = async (cid: string) => {
  try {
    const res = await fetch(`/sqi/ghx/hover/${cid}`);
    if (!res.ok) throw new Error(`GHX hover request failed: ${res.status}`);
    return await res.json(); // baked GHX/metadata payload
  } catch (err) {
    console.error("GHX hover fetch error:", err);
    return null;
  }
};

const [setHoveredNodeId] = useState<string | null>(null);

const setCollapse = async (cid: string, collapsed: boolean, opts?: {mode?: string; snapshot_rate?: number; density?: string}) => {
  const q = new URLSearchParams({ collapsed: String(collapsed) });
  if (opts?.mode) q.set("mode", opts.mode);
  if (typeof opts?.snapshot_rate === "number") q.set("snapshot_rate", String(opts.snapshot_rate));
  if (opts?.density) q.set("density", opts.density);
  const res = await fetch(`/sqi/ghx/collapse/${cid}?${q.toString()}`, { method: "POST" });
  if (!res.ok) throw new Error(`collapse failed: ${res.status}`);
  return res.json();
};

// ✅ Agent Identity Colors (Dynamic Palette)
const agentColors: Record<string, string> = {
  local: "#4ade80",        // green
  remote: "#60a5fa",       // blue
  collaborator: "#f472b6", // pink
  system: "#facc15",       // yellow
};
const getAgentColor = (agentId?: string) =>
  agentId && agentColors[agentId] ? agentColors[agentId] : "#a855f7"; // default purple

const useGHXGlyphs = () => {
  const [holograms, setHolograms] = useState<any[]>([]);
  const [echoes, setEchoes] = useState<any[]>([]);
  const [dreams, setDreams] = useState<any[]>([]);

  const handleTeleport = (targetId: string) => {
    if (!targetId) return;
    // Replace with your teleport system
    window?.dispatchEvent(new CustomEvent("teleport", { detail: { targetId } }));
  };

useEffect(() => {
  (window as any).GHX_ON_TELEPORT = async (cid: string) => {
    console.log("🚀 Teleporting to:", cid);
    try {
      const res = await axios.post("/api/teleport", { container_id: cid });
      console.log("🛬 Teleport complete:", res.data.container);
      // Optional: update UI with new container
    } catch (err) {
      console.error("❌ Teleport failed:", err);
    }
  };

  // 🔁 Fetch replay glyphs
  axios.get("/api/replay/list?include_metadata=true&sort_by_time=true").then(res => {
    const allGlyphs = res.data.result || [];
    const holograms: any[] = [];
    const echoes: any[] = [];
    const dreams: any[] = [];

    for (const g of allGlyphs) {
      const isEcho = g.metadata?.memoryEcho || g.metadata?.source === "memory";
      const isDream = g.metadata?.predictive || g.metadata?.dream;
      const isAtom = g.metadata?.container_kind === "atom";

      const glyphObj = {
        id: g.id,
        glyph: g.content,
        position: [Math.random() * 6 - 3, Math.random() * 4 - 2, Math.random() * 4 - 2],
        memoryEcho: isEcho,
        predictive: isDream,
        entangled_with: g.metadata?.entangled_ids || [],
        entangled: g.metadata?.entangled_ids || [],
        reasoning_chain: g.metadata?.reasoning_chain || null,
        prediction_path: g.metadata?.predicted_path || [],
        snapshot_id: g.metadata?.snapshot_id || null,
        anchor: g.metadata?.anchor || null,
        agent_id: g.metadata?.agent_id || "system",
        locked: false,
        permission: g.metadata?.permission || "editable",
        isAtom: isAtom,
        electronCount: g.metadata?.electronCount || 0,
        electrons: g.metadata?.electrons || []
      };

      if (isDream) dreams.push(glyphObj);
      else if (isEcho) echoes.push(glyphObj);
      else holograms.push(glyphObj);
    }

    setHolograms(holograms);
    setEchoes(echoes);
    setDreams(dreams);
  });
}, []);

  return { holograms, echoes, dreams, setHolograms };
};
type GlyphHologramProps = {
  cid: string;
  glyph: string;
  position: [number, number, number];
  memoryEcho?: boolean;
  predictive?: boolean;
  reasoning_chain?: string | null;
  prediction_path?: string[];
  anchor?: { type: string; env_obj_id: string } | null;
  agent_id?: string;
  locked?: boolean;
  permission: "hidden" | "read-only" | "editable" | "full";
  onClick?: () => void;
  onTeleport?: (cid: string) => void;
  onHover?: (id: string | null) => void;
  collapsed?: boolean;
  collapseTime?: number;
  phase?: string;
};

const GlyphHologram = ({
  cid,
  glyph,
  position,
  memoryEcho,
  predictive,
  reasoning_chain,
  prediction_path = [],
  anchor,
  agent_id,
  locked,
  permission,
  onClick,
  onTeleport,
  onHover,
  collapsed,
  collapseTime,
  phase,
}: GlyphHologramProps) => {
  const meshRef = useRef<any>();
  const [hovered, setHovered] = useState(false);

  const isMutation = glyph === "⬁";

  useFrame(({ clock }) => {
    if (meshRef.current) {
      const t = clock.getElapsedTime();
      if (isMutation) {
        const pulse = 1 + 0.3 * Math.sin(t * 4);
        meshRef.current.material.emissiveIntensity = pulse;
        meshRef.current.scale.set(pulse, pulse, pulse);
      }
      if (predictive) {
        meshRef.current.position.y += Math.sin(t * 2) * 0.002;
        meshRef.current.material.opacity = 0.4 + 0.2 * Math.sin(t * 1.5);
      }
    }
  });

  if (permission === "hidden") return null;

  const emissiveColor = memoryEcho ? "#222222" : predictive ? "#2299ff" : getAgentColor(agent_id);
  const opacity = permission === "read-only" ? 0.25 : (memoryEcho ? 0.35 : predictive ? 0.5 : 1);

  const signatureStatus = hoverMeta?.signature_block?.verified;
  const signatureBadge = signatureStatus === true ? "✅" : signatureStatus === false ? "❌" : "⧖";
  const signatureColor = signatureStatus === true ? "#00ff88" : signatureStatus === false ? "#ff3366" : "#cccccc";

  return (
    <group>
      {/* ◉ Main Glyph */}
      <mesh
        ref={meshRef}
        position={position}
        onClick={permission !== "read-only" ? onClick : undefined}
        onPointerOver={async (e) => {
          e.stopPropagation();
          setHovered(true);
          onHover?.(cid);
          if (cid) {
            setHoverCid(cid);
            const baked = await fetchHoverGHX(cid);
            if (baked) setHoverMeta(baked);
          }
        }}
        onPointerOut={(e) => {
          e.stopPropagation();
          setHovered(false);
          onHover?.(null);
          setHoverCid(null);
          setHoverMeta(null);
        }}
      >
        <sphereGeometry args={[0.4, 32, 32]} />
        <meshStandardMaterial
          emissive={emissiveColor}
          emissiveIntensity={memoryEcho ? 0.3 : predictive ? 0.8 : 1.5}
          transparent
          opacity={opacity}
          color={memoryEcho ? "#111111" : predictive ? "#113355" : isMutation ? "#220000" : "black"}
        />

        {/* 🔒 Lock Icon */}
        {locked && (
          <Html center>
            <div style={{
              fontSize: "1.5em",
              color: "#ff3333",
              textShadow: "0 0 8px #ff0000",
              marginTop: "-20px"
            }}>🔒</div>
          </Html>
        )}

        {/* 🔏 Signature Status Badge */}
        {hovered && hoverMeta?.signature_block && (
          <Html center>
            <div style={{
              fontSize: "1.4em",
              color: signatureColor,
              textShadow: `0 0 6px ${signatureColor}`,
              marginTop: "-32px",
            }}>{signatureBadge}</div>
          </Html>
        )}
      </mesh>

        {/* 🧠 Hover Metadata */}
        {hovered && hoverCid && hoverMeta && (
          <Html center distanceFactor={12}>
            <div style={{
              padding: "8px 10px",
              background: "rgba(10,10,20,0.85)",
              color: "#dfe6ff",
              border: "1px solid rgba(120,140,255,0.35)",
              borderRadius: 8,
              maxWidth: 360,
              fontSize: 12,
              boxShadow: "0 4px 18px rgba(0,0,0,0.35)",
              backdropFilter: "blur(4px)",
              whiteSpace: "pre-wrap"
            }}>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>
                {hoverMeta.container_id ?? hoverCid} — GHX (collapsed: {String(hoverMeta.collapsed ?? false)})
              </div>
              <code style={{ display: "block", maxHeight: 180, overflow: "auto" }}>
                {JSON.stringify(hoverMeta, null, 2)}
              </code>
            </div>
          </Html>
        )}

        {/* 🔤 Glyph Label */}
        <Html center>
          <div style={{
            color: emissiveColor,
            fontSize: memoryEcho || predictive ? "0.9em" : "1.2em",
            opacity,
            textAlign: "center",
            maxWidth: "150px",
            filter: permission === "read-only" ? "blur(1px)" : "none"
          }}>
            {glyph}
            {agent_id && <div style={{ fontSize: "0.7em", color: emissiveColor }}>🧑‍🚀 {agent_id}</div>}
            {reasoning_chain && <div style={{ fontSize: "0.7em", color: "#88ccff", marginTop: "4px" }}>💭 {reasoning_chain.slice(0, 40)}...</div>}
            {isMutation && <div style={{ fontSize: "0.8em", color: "#ff6666" }}>⬁</div>}
            {hovered && predictive && prediction_path.length > 0 && (
              <div style={{
                marginTop: "6px",
                padding: "4px",
                background: "rgba(20,20,40,0.9)",
                color: "#88ccff",
                fontSize: "0.7em",
                borderRadius: "4px"
              }}>
                🔮 Predicted Path:<br />
                {prediction_path.slice(0, 3).map((p: string, i: number) => (
                  <div key={i}>⧖ {p}</div>
                ))}
                {prediction_path.length > 3 && "..."}
              </div>
            )}
            {anchor && (
              <div style={{ fontSize: "0.7em", color: "#ffff66", marginTop: "4px" }}>
                📍 {anchor.type} → {anchor.env_obj_id}
              </div>
            )}
            {permission === "read-only" && (
              <div style={{ fontSize: "0.7em", color: "#ffaa00", marginTop: "4px" }}>
                🔒 Read-Only
              </div>
            )}
          </div>
        </Html>
      </mesh>

      {/* 📍 Anchor Visual Line */}
      {anchor && (
        <>
          <mesh position={[position[0], position[1] - 1.5, position[2]]}>
            <boxGeometry args={[0.2, 0.2, 0.2]} />
            <meshBasicMaterial color="yellow" />
          </mesh>
          <line>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                count={2}
                array={new Float32Array([
                  ...position,
                  position[0], position[1] - 1.5, position[2]
                ])}
                itemSize={3}
              />
            </bufferGeometry>
            <lineBasicMaterial color="yellow" linewidth={2} />
          </line>
        </>
      )}

      {/* 🌈 D01a: Phase Gradient Ring */}
      {phase && (
        <mesh position={position}>
          <ringGeometry args={[0.5, 0.7, 32]} />
          <meshBasicMaterial
            transparent
            opacity={0.3}
            color={getPhaseColor(phase)}
            side={2}
          />
        </mesh>
      )}

      {/* 🔥 D01c: Collapse Heatmap Shell */}
      {collapsed && collapseTime && (
        <mesh position={position}>
          <sphereGeometry args={[0.55, 32, 32]} />
          <meshBasicMaterial
            color={getCollapseHeatColor(collapseTime)}
            transparent
            opacity={0.25}
          />
        </mesh>
      )}

      {/* ⚡ D01b: Entanglement Lines → handled globally via LightLinker */}
    </group>
  );
};

// 🧠 Helpers for overlays
function getPhaseColor(phase: string) {
  switch (phase) {
    case "dream": return "#6666ff";
    case "prediction": return "#88ccff";
    case "mutation": return "#ff6666";
    case "collapse": return "#ffcc00";
    default: return "#cccccc";
  }
}

function getCollapseHeatColor(collapseTime: number) {
  const age = Date.now() - collapseTime;
  if (age < 5000) return "#ff3300";
  if (age < 10000) return "#ffaa00";
  if (age < 20000) return "#ffff66";
  return "#cccccc";
}
// ===== Electron Shells for Atom Containers =========================================

type Electron = {
  id: string;
  label?: string;
  meta?: {
    linkContainerId?: string;
    previewImage?: string;
  };
};

type ElectronShell = {
  radius: number;
  speed: number;
  electrons: Electron[];
};

function buildElectronShells(total: number, electronsMeta?: Electron[]): ElectronShell[] {
  const capacities = [2, 8, 18];
  const shells: ElectronShell[] = [];
  let remaining = total;
  let baseR = 0.9;
  let baseSpeed = 0.6;
  let index = 0;

  for (let i = 0; i < capacities.length && remaining > 0; i++) {
    const take = Math.min(remaining, capacities[i]);
    const electrons: Electron[] = [];

    for (let j = 0; j < take; j++) {
      electrons.push(
        electronsMeta?.[index] || {
          id: `e${i}-${j}`,
        }
      );
      index++;
    }

    shells.push({
      radius: baseR + i * 0.45,
      speed: baseSpeed + i * 0.25,
      electrons,
    });
    remaining -= take;
  }
  return shells;
}

const ElectronShells = ({
  center,
  shells,
  onTeleport,
}: {
  center: [number, number, number];
  shells: ElectronShell[];
  onTeleport?: (containerId: string) => void;
}) => {
  const groupsRef = useRef<THREE.Group[]>([]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    groupsRef.current.forEach((g, i) => {
      if (!g) return;
      g.rotation.y = t * shells[i].speed;
    });
  });

  return (
    <>
      {shells.map((sh, si) => (
        <group
          key={`shell-${si}`}
          ref={(el) => {
            if (el) groupsRef.current[si] = el;
          }}
          position={center}
        >
          {/* Orbit ring */}
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[sh.radius, 0.01, 8, 64]} />
            <meshBasicMaterial color="#4466aa" transparent opacity={0.2} />
          </mesh>

          {/* Electrons */}
          {sh.electrons.map((e, idx) => {
            const angle = (idx / Math.max(1, sh.electrons.length)) * Math.PI * 2;
            const x = sh.radius * Math.cos(angle);
            const z = sh.radius * Math.sin(angle);

            return (
              <mesh
                key={e.id}
                position={[center[0] + x, center[1], center[2] + z]}
                onClick={(ev) => {
                  ev.stopPropagation();
                  const targetId = e.meta?.linkContainerId;
                  if (targetId && onTeleport) {
                    onTeleport(targetId);
                  }
                }}
              >
                <sphereGeometry args={[0.05, 16, 16]} />
                <meshStandardMaterial emissive="#77bbff" emissiveIntensity={1} color="#113355" />

                {/* Tooltip */}
                {e.label && (
                  <Html distanceFactor={10}>
                    <div className="electron-tooltip">
                      {e.meta?.previewImage && (
                        <img
                          src={e.meta.previewImage}
                          alt="preview"
                          style={{ width: 64, borderRadius: 4, marginBottom: 4 }}
                        />
                      )}
                      <div>{e.label}</div>
                    </div>
                  </Html>
                )}
              </mesh>
            );
          })}
        </group>
      ))}
    </>
  );
};
const QEntropySpiral = () => {
  const meshRef = useRef<any>();
  useFrame(({ clock }) => {
    if (meshRef.current) {
      const t = clock.getElapsedTime();
      const angle = t * 1.5;
      const radius = 1.5 + 0.2 * Math.sin(t * 2);
      meshRef.current.position.set(
        radius * Math.cos(angle),
        0.5 * Math.sin(angle * 2),
        radius * Math.sin(angle)
      );
      meshRef.current.rotation.y = angle;
      meshRef.current.scale.setScalar(1 + 0.2 * Math.sin(t * 4));
    }
  });
  return (
    <mesh ref={meshRef}>
      <torusGeometry args={[0.25, 0.1, 16, 100]} />
      <meshStandardMaterial color="#88ccff" emissive="#2299ff" emissiveIntensity={1.2} />
      <Html center>
        <div style={{ color: "#88ccff", fontSize: "1.1em", textShadow: "0 0 6px #2299ff" }}>🌀</div>
      </Html>
    </mesh>
  );
};


  const { holograms, echoes, dreams, setHolograms } = useGHXGlyphs();
  const [selectedGlyph, setSelectedGlyph] = useState<any | null>(null);
  const [trace, setTrace] = useState<any[]>([]);

  // ✅ fallback container id for hover calls if a glyph lacks one
  const currentCid =
    (typeof window !== "undefined" && (window as any).GHX_CURRENT_CONTAINER_ID) || "unknown";

  useWebSocket("/ws/brain-map", (data) => {
    const withAtomFlags = (glyph: any) => ({
      ...glyph,
      isAtom: glyph?.type === "atom",
      electronCount: glyph?.electrons?.length || 0,
    });

    if (data.type === "glyph_reasoning") {
      setHolograms((prev) =>
        prev.map((h) =>
          h.id === data.glyph
            ? withAtomFlags({ ...h, reasoning_chain: data.reasoning })
            : h
        )
      );
    }

    if (data.type === "node_update") {
      setHolograms((prev) =>
        prev.map((h) =>
          h.id === data.node.id
            ? withAtomFlags({ ...h, entangled: data.node.entangled_ids || h.entangled })
            : h
        )
      );
    }

    if (data.type === "anchor_update") {
      setHolograms((prev) =>
        prev.map((h) =>
          h.id === data.glyph_id
            ? withAtomFlags({ ...h, anchor: data.anchor })
            : h
        )
      );
    }

    if (data.type === "entanglement_lock_acquired") {
      setHolograms((prev) =>
        prev.map((h) =>
          h.id === data.glyph_id ? withAtomFlags({ ...h, locked: true }) : h
        )
      );
    }

    if (data.type === "entanglement_lock_released") {
      setHolograms((prev) =>
        prev.map((h) =>
          h.id === data.glyph_id ? withAtomFlags({ ...h, locked: false }) : h
        )
      );
    }

    // 🔑 Permission updates
    if (data.type === "glyph_permission_update") {
      setHolograms((prev) =>
        prev.map((h) =>
          h.agent_id === data.agent_id
            ? withAtomFlags({
                ...h,
                permission: data.permissions.includes("kg_edit")
                  ? "editable"
                  : "read-only",
              })
            : h
        )
      );
    }

    // 🌐 Agent color updates
    if (data.type === "agent_joined") {
      agentColors[data.agent.agent_id || data.agent.name] = data.agent.color;
    }
  });

import { useRouter } from "next/router";
import { ElectronShells, buildElectronShells } from "./atoms/electronOrbit";

const router = useRouter();

<>
  <Canvas camera={{ position: [0, 0, 10], fov: 60 }}>
    <ambientLight intensity={0.4} />
    <pointLight position={[10, 10, 10]} intensity={1} />

    {/* 🌙 Dreams */}
    {dreams.map((g) => (
      <GlyphHologram
        key={`dream-${g.id}`}
        cid={g.container_id || g.cid || currentCid}
        {...g}
        predictive={true}
        isAtom={g.isAtom}
        electronCount={g.electronCount}
        electrons={g.electrons}
        onTeleport={(containerId: string) => router.push(`/container/${containerId}`)}
        onClick={() => setSelectedGlyph(g)}
        onHover={setHoveredNodeId}
      />
    ))}

    {/* 🔁 Echoes */}
    {echoes.map((g) => (
      <GlyphHologram
        key={`echo-${g.id}`}
        cid={g.container_id || g.cid || currentCid}
        {...g}
        memoryEcho={true}
        isAtom={g.isAtom}
        electronCount={g.electronCount}
        electrons={g.electrons}
        onTeleport={(containerId: string) => router.push(`/container/${containerId}`)}
        onClick={() => setSelectedGlyph(g)}
        onHover={setHoveredNodeId}
      />
    ))}

    {/* 🧬 Holograms */}
    {holograms.map((g) => (
      <GlyphHologram
        key={g.id}
        cid={g.container_id || g.cid || currentCid}
        {...g}
        memoryEcho={false}
        isAtom={g.isAtom}
        electronCount={g.electronCount}
        electrons={g.electrons}
        onTeleport={(containerId: string) => router.push(`/container/${containerId}`)}
        onClick={() => setSelectedGlyph(g)}
        onHover={setHoveredNodeId}
      />
    ))}

    {/* ⚛ ElectronShells for atoms */}
    {holograms.concat(dreams).map((g) =>
      g.isAtom && g.electrons ? (
        <ElectronShells
          key={`electrons-${g.id}`}
          center={g.position}
          shells={buildElectronShells(g.electronCount || 3, g.electrons)}
          onTeleport={(cid) => {
            if (cid) {
              console.log("🧬 Teleporting to:", cid);
              window?.GHX_ON_TELEPORT?.(cid);
            }
          }}
        />
      ) : null
    )}

    {/* 🔁 C07 – GHX Replay Selector */}
    {trace.length > 0 && (
      <GHXReplaySelector trace={trace} onSelect={(idx) => setSelectedGlyph(trace[idx])} />
    )}

    {/* 🌐 C08 – GHX Teleport Trail */}
    {selectedGlyph?.teleportTrail && (
      <GHXTeleportTrail trail={selectedGlyph.teleportTrail} />
    )}

    {/* 📍 C09 – GHX Anchor Memory Replay */}
    {selectedGlyph?.anchorMemory && (
      <GHXAnchorMemory anchors={selectedGlyph.anchorMemory} />
    )}

    {/* 🌀 C10 – Symbolic Teleport Visualizer */}
    {selectedGlyph?.symbolicPath && (
      <SymbolicTeleportPath path={selectedGlyph.symbolicPath} />
    )}

    {/* 👻 D01 – DreamOS Ghost Entry */}
    {selectedGlyph?.ghostEntry && (
      <DreamGhostEntry position={selectedGlyph.ghostEntry} label="👻 Ghost Entry" />
    )}

    {/* 🔗 D01b – Entanglement Links */}
    <EntanglementTracer glyphs={[...holograms, ...echoes, ...dreams]} />

    {/* 🌈 D01a – LightLinks Phase Overlay */}
    <LightLinks glyphs={[...holograms, ...dreams]} />

    {/* ♾️ SQI Visuals */}
    <QEntropySpiral />
    <GHXSignatureTrail identity={"AION-000X"} radius={2.2} />
    <OrbitControls />
  </Canvas>
</>