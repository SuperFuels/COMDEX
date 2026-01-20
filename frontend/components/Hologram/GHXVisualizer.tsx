// File: frontend/components/Hologram/GHXVisualizer.tsx
"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import axios from "axios";
import { Canvas, useFrame } from "@react-three/fiber";
import { Html as DreiHtml, OrbitControls } from "@react-three/drei";
import useWebSocket from "@/hooks/useWebSocket"; // default import
import { useCollapseMetrics } from "@/hooks/useCollapseMetrics";
import { useRouter } from "next/router";

// If you DO have this file locally, keep this import.
// Otherwise, the inline stub below will be used.
import GHXSignatureTrail from "./GHXSignatureTrail";

declare global {
  interface Window {
    GHX_ON_TELEPORT?: (cid: string) => void;
  }
}

// -------------------- Optional stubs (replace with real ones any time) --------------------
const GHXReplaySelector: React.FC<{ trace: any[]; onSelect: (i: number) => void }> = () => null;
const GHXTeleportTrail: React.FC<{ trail: any[] }> = () => null;
const GHXAnchorMemory: React.FC<{ anchors: any[] }> = () => null;
const SymbolicTeleportPath: React.FC<{ path: any[] }> = () => null;
const DreamGhostEntry: React.FC<{ position: [number, number, number]; label?: string }> = () => null;
const InnovationOverlay: React.FC = () => null;
const EntanglementTracer: React.FC<{ glyphs: any[] }> = () => null;
const LightLinks: React.FC<{ glyphs: any[] }> = () => null;
// ------------------------------------------------------------------------------------------

// Nav arrows (debug)
export function drawLinkArrows(containerLinks: Record<string, any>) {
  Object.entries(containerLinks).forEach(([source, nav]) => {
    Object.entries(nav as Record<string, string>).forEach(([direction, target]) => {
      console.log(`🎨 Draw arrow: ${source} → ${target} (${direction})`);
    });
  });
}

// ---------- Agent identity color palette ----------
const agentColors: Record<string, string> = {
  local: "#4ade80",
  remote: "#60a5fa",
  collaborator: "#f472b6",
  system: "#facc15",
};
const getAgentColor = (agentId?: string) =>
  (agentId && agentColors[agentId]) || "#a855f7";

// ---------- Hover metadata helpers ----------
const fetchHoverGHX = async (cid: string) => {
  try {
    const res = await fetch(`/sqi/ghx/hover/${cid}`);
    if (!res.ok) throw new Error(`GHX hover request failed: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("GHX hover fetch error:", err);
    return null;
  }
};

// ---------- Local glyph loader / partitioner ----------
function useGHXGlyphs() {
  const [holograms, setHolograms] = useState<any[]>([]);
  const [echoes, setEchoes] = useState<any[]>([]);
  const [dreams, setDreams] = useState<any[]>([]);

  useEffect(() => {
    (window as any).GHX_ON_TELEPORT = async (cid: string) => {
      try {
        const res = await axios.post("/api/teleport", { container_id: cid });
        console.log("🛬 Teleport:", res.data?.container ?? cid);
      } catch (err) {
        console.error("❌ Teleport failed:", err);
      }
    };

    // Replay list
    axios
      .get("/api/replay/list?include_metadata=true&sort_by_time=true")
      .then((res) => {
        const allGlyphs: any[] = res.data?.result || [];
        const H: any[] = [];
        const E: any[] = [];
        const D: any[] = [];

        for (const g of allGlyphs) {
          const isEcho = g.metadata?.memoryEcho || g.metadata?.source === "memory";
          const isDream = g.metadata?.predictive || g.metadata?.dream;
          const isAtom = g.metadata?.container_kind === "atom";

          const glyphObj = {
            id: g.id,
            glyph: g.content,
            position: [
              Math.random() * 6 - 3,
              Math.random() * 4 - 2,
              Math.random() * 4 - 2,
            ] as [number, number, number],
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
            isAtom,
            electronCount: g.metadata?.electronCount || 0,
            electrons: g.metadata?.electrons || [],
            container_id: g.metadata?.container_id || g.id,
          };

          if (isDream) D.push(glyphObj);
          else if (isEcho) E.push(glyphObj);
          else H.push(glyphObj);
        }

        setHolograms(H);
        setEchoes(E);
        setDreams(D);
      });
  }, []);

  return { holograms, echoes, dreams, setHolograms };
}

// ---------- Electron shells (inline minimal version) ----------
type Electron = {
  id: string;
  label?: string;
  meta?: { linkContainerId?: string; previewImage?: string };
};
type ElectronShell = { radius: number; speed: number; electrons: Electron[] };

function buildElectronShells(total: number, electronsMeta?: Electron[]): ElectronShell[] {
  const capacities = [2, 8, 18];
  const shells: ElectronShell[] = [];
  let remaining = total;
  let idx = 0;

  for (let i = 0; i < capacities.length && remaining > 0; i++) {
    const take = Math.min(remaining, capacities[i]);
    const electrons: Electron[] = [];
    for (let j = 0; j < take; j++) {
      electrons.push(electronsMeta?.[idx] ?? { id: `e${i}-${j}` });
      idx++;
    }
    shells.push({ radius: 0.9 + i * 0.45, speed: 0.6 + i * 0.25, electrons });
    remaining -= take;
  }
  return shells;
}

const ElectronShells: React.FC<{
  center: [number, number, number];
  shells: ElectronShell[];
  onTeleport?: (containerId: string) => void;
}> = ({ center, shells, onTeleport }) => {
  // loosen type to avoid @types/three vs three mismatch
  const groupsRef = useRef<any[]>([]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    groupsRef.current.forEach((g, i) => {
      if (g) {
        (g as THREE.Group).rotation.y = t * (shells[i]?.speed ?? 0);
      }
    });
  });

  return (
    <>
        {shells.map((sh, si) => (
          <group
            key={`shell-${si}`}
            ref={(el: any) => {
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
                  if (targetId && onTeleport) onTeleport(targetId);
                }}
              >
                <sphereGeometry args={[0.05, 16, 16]} />
                <meshStandardMaterial emissive="#77bbff" emissiveIntensity={1} color="#113355" />

                {/* Tooltip */}
                {e.label && (
                  <DreiHtml distanceFactor={10}>
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
                  </DreiHtml>
                )}
              </mesh>
            );
          })}
        </group>
      ))}
    </>
  );
};

// ---------- QEntropy spiral ----------
const QEntropySpiral: React.FC = () => {
  // loosen ref type to avoid three/@types mismatch
  const ref = useRef<any>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const angle = t * 1.5;
    const radius = 1.5 + 0.2 * Math.sin(t * 2);

    if (ref.current) {
      ref.current.position.set(
        radius * Math.cos(angle),
        0.5 * Math.sin(angle * 2),
        radius * Math.sin(angle)
      );
      ref.current.rotation.y = angle;
      ref.current.scale.setScalar(1 + 0.2 * Math.sin(t * 4));
    }
  });

  return (
    <mesh ref={ref as any}>
      <torusGeometry args={[0.25, 0.1, 16, 100]} />
      <meshStandardMaterial
        color="#88ccff"
        emissive="#2299ff"
        emissiveIntensity={1.2}
      />
      <DreiHtml center>
        <div
          style={{
            color: "#88ccff",
            fontSize: "1.1em",
            textShadow: "0 0 6px #2299ff",
          }}
        >
          🌀
        </div>
      </DreiHtml>
    </mesh>
  );
};

// ---------- Glyph Hologram ----------
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
  permission?: "hidden" | "read-only" | "editable" | "full";
  onClick?: () => void;
  onTeleport?: (cid: string) => void;
  onHover?: (id: string | null) => void;
  collapsed?: boolean;
  collapseTime?: number;
  phase?: string;

  // atom extras
  isAtom?: boolean;
  electronCount?: number;
  electrons?: Electron[];
};

const getPhaseColor = (phase: string) => ({
  dream: "#6666ff",
  prediction: "#88ccff",
  mutation: "#ff6666",
  collapse: "#ffcc00",
} as Record<string, string>)[phase] ?? "#cccccc";

const getCollapseHeatColor = (collapseTime: number) => {
  const age = Date.now() - collapseTime;
  if (age < 5000) return "#ff3300";
  if (age < 10000) return "#ffaa00";
  if (age < 20000) return "#ffff66";
  return "#cccccc";
};

const GlyphHologram: React.FC<GlyphHologramProps> = ({
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
  permission = "editable",
  onClick,
  onHover,
  collapsed,
  collapseTime,
  phase,
}) => {
  // loosen ref type to dodge three/@types mismatch
  const meshRef = useRef<any>(null);
  const [hovered, setHovered] = useState(false);
  const [hoverCid, setHoverCid] = useState<string | null>(null);
  const [hoverMeta, setHoverMeta] = useState<any>(null);

  const isMutation = glyph === "⬁";

  useFrame(({ clock }) => {
    const m = meshRef.current;
    if (!m) return;

    const t = clock.getElapsedTime();

    if (isMutation && m.material) {
      const pulse = 1 + 0.3 * Math.sin(t * 4);
      m.material.emissiveIntensity = pulse;
      m.scale.set(pulse, pulse, pulse);
    }

    if (predictive) {
      m.position.y += Math.sin(t * 2) * 0.002;
      if (m.material) {
        m.material.opacity = 0.4 + 0.2 * Math.sin(t * 1.5);
      }
    }
  });

  if (permission === "hidden") return null;

  const emissiveColor = memoryEcho ? "#222222" : predictive ? "#2299ff" : getAgentColor(agent_id);
  const opacity = permission === "read-only" ? 0.25 : memoryEcho ? 0.35 : predictive ? 0.5 : 1;

  const signatureStatus = hoverMeta?.signature_block?.verified;
  const signatureBadge = signatureStatus === true ? "✅" : signatureStatus === false ? "❌" : "⧖";
  const signatureColor =
    signatureStatus === true ? "#00ff88" : signatureStatus === false ? "#ff3366" : "#cccccc";

  return (
    <group>
      <mesh
        ref={meshRef as any}
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

        {/* 🔒 Lock */}
        {locked && (
          <DreiHtml center>
            <div
              style={{
                fontSize: "1.5em",
                color: "#ff3333",
                textShadow: "0 0 8px #ff0000",
                marginTop: "-20px",
              }}
            >
              🔒
            </div>
          </DreiHtml>
        )}

        {/* 🔏 Signature */}
        {hovered && hoverMeta?.signature_block && (
          <DreiHtml center>
            <div
              style={{
                fontSize: "1.4em",
                color: signatureColor,
                textShadow: `0 0 6px ${signatureColor}`,
                marginTop: "-32px",
              }}
            >
              {signatureBadge}
            </div>
          </DreiHtml>
        )}
      </mesh>

      {/* 🧠 Hover metadata */}
      {hovered && hoverCid && hoverMeta && (
        <DreiHtml center distanceFactor={12}>
          <div
            style={{
              padding: "8px 10px",
              background: "rgba(10,10,20,0.85)",
              color: "#dfe6ff",
              border: "1px solid rgba(120,140,255,0.35)",
              borderRadius: 8,
              maxWidth: 360,
              fontSize: 12,
              boxShadow: "0 4px 18px rgba(0,0,0,0.35)",
              backdropFilter: "blur(4px)",
              whiteSpace: "pre-wrap",
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: 6 }}>
              {hoverMeta.container_id ?? hoverCid} — GHX (collapsed:{" "}
              {String(hoverMeta.collapsed ?? false)})
            </div>
            <code style={{ display: "block", maxHeight: 180, overflow: "auto" }}>
              {JSON.stringify(hoverMeta, null, 2)}
            </code>
          </div>
        </DreiHtml>
      )}

      {/* 🔤 Label + extras */}
      <DreiHtml center>
        <div
          style={{
            color: emissiveColor,
            fontSize: memoryEcho || predictive ? "0.9em" : "1.2em",
            opacity,
            textAlign: "center",
            maxWidth: "150px",
            filter: permission === "read-only" ? "blur(1px)" : "none",
          }}
        >
          {glyph}
          {agent_id && <div style={{ fontSize: "0.7em", color: emissiveColor }}>🧑‍🚀 {agent_id}</div>}
          {reasoning_chain && (
            <div style={{ fontSize: "0.7em", color: "#88ccff", marginTop: "4px" }}>
              💭 {reasoning_chain.slice(0, 40)}…
            </div>
          )}
          {isMutation && <div style={{ fontSize: "0.8em", color: "#ff6666" }}>⬁</div>}
          {hovered && predictive && prediction_path.length > 0 && (
            <div
              style={{
                marginTop: "6px",
                padding: "4px",
                background: "rgba(20,20,40,0.9)",
                color: "#88ccff",
                fontSize: "0.7em",
                borderRadius: "4px",
              }}
            >
              🔮 Predicted Path:
              <br />
              {prediction_path.slice(0, 3).map((p, i) => (
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
            <div style={{ fontSize: "0.7em", color: "#ffaa00", marginTop: "4px" }}>🔒 Read-Only</div>
          )}
        </div>
      </DreiHtml>

      {/* 📍 Anchor guide */}
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
                array={
                  new Float32Array([
                    ...position,
                    position[0],
                    position[1] - 1.5,
                    position[2],
                  ])
                }
                itemSize={3}
              />
            </bufferGeometry>
            <lineBasicMaterial color="yellow" />
          </line>
        </>
      )}

      {/* Phase ring */}
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

      {/* Collapse heat shell */}
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
    </group>
  );
};

// ------------------------------------------------------------------------------------------------

export default function GHXVisualizer() {
  const router = useRouter();

  // Live metrics HUD
  const { latestCollapse, latestDecoherence, collapseHistory, decoherenceHistory } = useCollapseMetrics();

  const { holograms, echoes, dreams, setHolograms } = useGHXGlyphs();
  const [selectedGlyph, setSelectedGlyph] = useState<any | null>(null);
  const [trace, setTrace] = useState<any[]>([]);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const currentCid =
    (typeof window !== "undefined" && (window as any).GHX_CURRENT_CONTAINER_ID) || "unknown";

  // WebSocket updates
  useWebSocket("/ws/brain-map", (data: any) => {
    const withAtomFlags = (glyph: any) => ({
      ...glyph,
      isAtom: glyph?.type === "atom" || glyph?.isAtom,
      electronCount: glyph?.electrons?.length || glyph?.electronCount || 0,
    });

    if (data.type === "glyph_reasoning") {
      setHolograms((prev) =>
        prev.map((h) => (h.id === data.glyph ? withAtomFlags({ ...h, reasoning_chain: data.reasoning }) : h))
      );
    }

    if (data.type === "node_update") {
      setHolograms((prev) =>
        prev.map((h) =>
          h.id === data.node.id ? withAtomFlags({ ...h, entangled: data.node.entangled_ids || h.entangled }) : h
        )
      );
    }

    if (data.type === "anchor_update") {
      setHolograms((prev) =>
        prev.map((h) => (h.id === data.glyph_id ? withAtomFlags({ ...h, anchor: data.anchor }) : h))
      );
    }

    if (data.type === "entanglement_lock_acquired") {
      setHolograms((prev) => prev.map((h) => (h.id === data.glyph_id ? withAtomFlags({ ...h, locked: true }) : h)));
    }
    if (data.type === "entanglement_lock_released") {
      setHolograms((prev) => prev.map((h) => (h.id === data.glyph_id ? withAtomFlags({ ...h, locked: false }) : h)));
    }

    if (data.type === "glyph_permission_update") {
      setHolograms((prev) =>
        prev.map((h) =>
          h.agent_id === data.agent_id
            ? withAtomFlags({ ...h, permission: data.permissions.includes("kg_edit") ? "editable" : "read-only" })
            : h
        )
      );
    }

    if (data.type === "agent_joined") {
      agentColors[data.agent.agent_id || data.agent.name] = data.agent.color;
    }
  });

  const averageCoherence =
    decoherenceHistory.length > 0
      ? decoherenceHistory.reduce((sum, v) => sum + v, 0) / decoherenceHistory.length
      : null;

  const snrStatus: "low" | "ok" | undefined =
    typeof averageCoherence === "number" && averageCoherence < 0.5 ? "low" : "ok";

  return (
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
            predictive
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
            memoryEcho
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
            onTeleport={(containerId: string) => router.push(`/container/${containerId}`)}
            onClick={() => setSelectedGlyph(g)}
            onHover={setHoveredNodeId}
          />
        ))}

        {/* ⚛ Electron shells for atoms (dreams + holos) */}
        {holograms.concat(dreams).map((g) =>
          g.isAtom && (g.electrons?.length || g.electronCount) ? (
            <ElectronShells
              key={`electrons-${g.id}`}
              center={g.position}
              shells={buildElectronShells(g.electronCount || 3, g.electrons)}
              onTeleport={(cid) => window?.GHX_ON_TELEPORT?.(cid)}
            />
          ) : null
        )}

        {/* Replays / trails / overlays (stubs) */}
        {trace.length > 0 && <GHXReplaySelector trace={trace} onSelect={(idx) => setSelectedGlyph(trace[idx])} />}
        {selectedGlyph?.teleportTrail && <GHXTeleportTrail trail={selectedGlyph.teleportTrail} />}
        {selectedGlyph?.anchorMemory && <GHXAnchorMemory anchors={selectedGlyph.anchorMemory} />}
        {selectedGlyph?.symbolicPath && <SymbolicTeleportPath path={selectedGlyph.symbolicPath} />}
        {selectedGlyph?.ghostEntry && <DreamGhostEntry position={selectedGlyph.ghostEntry} label="👻 Ghost Entry" />}

        <EntanglementTracer glyphs={[...holograms, ...echoes, ...dreams]} />
        <LightLinks glyphs={[...holograms, ...dreams]} />

        <QEntropySpiral />
        {GHXSignatureTrail && <GHXSignatureTrail identity={"AION-000X"} radius={2.2} />}
        <OrbitControls />
      </Canvas>

      {/* 📡 Telemetry overlay */}
      <div className="absolute bottom-4 right-4 text-xs p-2 bg-black/60 rounded-lg shadow-lg text-white z-50">
        <div>📉 Collapse Rate: <strong>{latestCollapse != null ? `${latestCollapse}/s` : "—"}</strong></div>
        <div>
          📡 Avg Coherence:{" "}
          <strong>{averageCoherence != null ? averageCoherence.toFixed(2) : "—"}</strong>
        </div>
        <div>💥 Beam Emissions: <strong>{collapseHistory.length}</strong></div>

        {averageCoherence != null && averageCoherence < 0.5 && (
          <div className="text-red-500 animate-pulse mt-1">⚠️ Low Coherence Detected</div>
        )}
        {snrStatus === "low" && <div className="text-yellow-400 mt-1 animate-pulse">⚠️ SNR Anomaly</div>}
      </div>

      <InnovationOverlay />
    </>
  );
}