import React, { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Html, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import GHXSignatureTrail from './GHXSignatureTrail';
import axios from 'axios';
import useWebSocket from '../../hooks/useWebSocket';

// ✅ GHXVisualizer Arrows Stub (Nav Map Visualization)
export function drawLinkArrows(containerLinks: Record<string, any>) {
  Object.entries(containerLinks).forEach(([source, nav]) => {
    Object.entries(nav).forEach(([direction, target]) => {
      console.log(`🎨 Draw arrow: ${source} → ${target} (${direction})`);
      // TODO: Render directional arrow in GHX canvas
    });
  });
}

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

  useEffect(() => {
    axios.get("/api/replay/list?include_metadata=true&sort_by_time=true").then(res => {
      const allGlyphs = res.data.result || [];
      const holograms: any[] = [];
      const echoes: any[] = [];
      const dreams: any[] = [];

      for (const g of allGlyphs) {
        const isEcho = g.metadata?.memoryEcho || g.metadata?.source === "memory";
        const isDream = g.metadata?.predictive || g.metadata?.dream;
        const glyphObj = {
          id: g.id,
          glyph: g.content,
          position: [Math.random() * 6 - 3, Math.random() * 4 - 2, Math.random() * 4 - 2],
          memoryEcho: isEcho,
          predictive: isDream,
          entangled: g.metadata?.entangled_ids || [],
          reasoning_chain: g.metadata?.reasoning_chain || null,
          prediction_path: g.metadata?.predicted_path || [],
          snapshot_id: g.metadata?.snapshot_id || null,
          anchor: g.metadata?.anchor || null,
          agent_id: g.metadata?.agent_id || "system",
          locked: false,
          permission: g.metadata?.permission || "editable"
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

const GlyphHologram = ({
  glyph, position, memoryEcho, predictive, reasoning_chain, prediction_path,
  anchor, agent_id, locked, permission, onClick
}: any) => {
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

  // 🚫 Restricted Mode: Hide unauthorized glyphs
  if (permission === "hidden") return null;
  const emissiveColor = memoryEcho ? "#222222" : predictive ? "#2299ff" : getAgentColor(agent_id);
  const opacity = permission === "read-only" ? 0.25 : (memoryEcho ? 0.35 : predictive ? 0.5 : 1);

  return (
    <group>
      <mesh
        ref={meshRef}
        position={position}
        onClick={permission !== "read-only" ? onClick : undefined}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[0.4, 32, 32]} />
        <meshStandardMaterial
          emissive={emissiveColor}
          emissiveIntensity={memoryEcho ? 0.3 : predictive ? 0.8 : 1.5}
          transparent
          opacity={opacity}
          color={memoryEcho ? "#111111" : predictive ? "#113355" : isMutation ? "#220000" : "black"}
        />

        {/* 🔒 Lock Overlay */}
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

        {/* 🧑‍🚀 Agent + Reasoning UI */}
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
            {agent_id && (
              <div style={{ fontSize: "0.7em", color: emissiveColor }}>
                🧑‍🚀 {agent_id}
              </div>
            )}
            {reasoning_chain && (
              <div style={{ fontSize: "0.7em", color: "#88ccff", marginTop: "4px" }}>
                💭 {reasoning_chain.slice(0, 40)}...
              </div>
            )}
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

      {/* ✅ Anchor marker visualization */}
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
    </group>
  );
};

const LightLinks = ({ glyphs }: any) => {
  const lines: any[] = [];
  glyphs.forEach((g: any) => {
    if (g.entangled) {
      g.entangled.forEach((targetId: string) => {
        const target = glyphs.find((other: any) => other.id === targetId);
        if (target) lines.push([g.position, target.position]);
      });
    }
  });
  return (
    <>
      {lines.map((line, idx) => (
        <line key={idx}>
          <bufferGeometry attach="geometry">
            <bufferAttribute
              attach="attributes-position"
              count={2}
              array={new Float32Array([...line[0], ...line[1]])}
              itemSize={3}
            />
          </bufferGeometry>
          <lineBasicMaterial color="violet" linewidth={2} />
        </line>
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
      meshRef.current.position.set(radius * Math.cos(angle), 0.5 * Math.sin(angle * 2), radius * Math.sin(angle));
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

export default function GHXVisualizer() {
  const { holograms, echoes, dreams, setHolograms } = useGHXGlyphs();
  const [selectedGlyph, setSelectedGlyph] = useState<any | null>(null);
  const [trace, setTrace] = useState<any[]>([]);

  useWebSocket("/ws/brain-map", (data) => {
    if (data.type === "glyph_reasoning") {
      setHolograms((prev) =>
        prev.map((h) => (h.id === data.glyph ? { ...h, reasoning_chain: data.reasoning } : h))
      );
    }
    if (data.type === "node_update") {
      setHolograms((prev) =>
        prev.map((h) =>
          h.id === data.node.id
            ? { ...h, entangled: data.node.entangled_ids || h.entangled }
            : h
        )
      );
    }
    if (data.type === "anchor_update") {
      setHolograms((prev) =>
        prev.map((h) =>
          h.id === data.glyph_id ? { ...h, anchor: data.anchor } : h
        )
      );
    }
    if (data.type === "entanglement_lock_acquired") {
      setHolograms((prev) =>
        prev.map((h) => (h.id === data.glyph_id ? { ...h, locked: true } : h))
      );
    }
    if (data.type === "entanglement_lock_released") {
      setHolograms((prev) =>
        prev.map((h) => (h.id === data.glyph_id ? { ...h, locked: false } : h))
      );
    }
    // 🔑 Permission updates
    if (data.type === "glyph_permission_update") {
      setHolograms((prev) =>
        prev.map((h) =>
          h.agent_id === data.agent_id
            ? { ...h, permission: data.permissions.includes("kg_edit") ? "editable" : "read-only" }
            : h
        )
      );
    }
    // 🌐 Agent color updates
    if (data.type === "agent_joined") {
      agentColors[data.agent.agent_id || data.agent.name] = data.agent.color;
    }
  });

  useEffect(() => {
    if (selectedGlyph?.snapshot_id) {
      axios.get(`/api/glyphnet/command/trace?snapshot_id=${selectedGlyph.snapshot_id}`)
        .then(res => setTrace(res.data.traces || []))
        .catch(() => setTrace([]));
    } else {
      setTrace([]);
    }
  }, [selectedGlyph]);

  return (
    <>
      <Canvas camera={{ position: [0, 0, 10], fov: 60 }}>
        <ambientLight intensity={0.4} />
        <pointLight position={[10, 10, 10]} intensity={1} />

        {dreams.map((g) => (
          <GlyphHologram key={`dream-${g.id}`} {...g} predictive={true} onClick={() => setSelectedGlyph(g)} />
        ))}
        {echoes.map((g) => (
          <GlyphHologram key={`echo-${g.id}`} {...g} memoryEcho={true} onClick={() => setSelectedGlyph(g)} />
        ))}
        {holograms.map((g) => (
          <GlyphHologram key={g.id} {...g} memoryEcho={false} onClick={() => setSelectedGlyph(g)} />
        ))}

        <LightLinks glyphs={[...holograms, ...dreams]} />
        <QEntropySpiral />
        <GHXSignatureTrail identity={"AION-000X"} radius={2.2} />
        <OrbitControls />
      </Canvas>

      {/* ✅ Timeline Identity Strip */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, width: "100%", display: "flex",
        flexDirection: "row", background: "rgba(10,10,20,0.7)", padding: "4px"
      }}>
        {[...holograms, ...dreams, ...echoes].slice(0, 20).map((g) => (
          <div key={g.id} style={{
            width: "18px",
            height: "18px",
            background: getAgentColor(g.agent_id),
            borderRadius: "50%",
            margin: "0 2px",
            border: "1px solid #444"
          }} title={`${g.agent_id} (${g.permission})`} />
        ))}
      </div>

      {/* ✅ Introspection Modal */}
      {selectedGlyph && (
        <div style={{
          position: "fixed", top: 0, left: 0, width: "100%", height: "100%",
          background: "rgba(0,0,0,0.8)", color: "white", display: "flex",
          flexDirection: "column", justifyContent: "center", alignItems: "center", zIndex: 1000
        }}>
          <div style={{
            background: "#1a1a2e", padding: "20px", borderRadius: "8px", maxWidth: "700px", textAlign: "center"
          }}>
            <h2>🔍 Glyph Introspection</h2>
            <p><strong>Glyph:</strong> {selectedGlyph.glyph}</p>
            {selectedGlyph.reasoning_chain && <p><strong>Reasoning:</strong> {selectedGlyph.reasoning_chain}</p>}
            {selectedGlyph.prediction_path?.length > 0 && (
              <div>
                <strong>Predicted Path:</strong>
                <ul style={{ textAlign: "left" }}>
                  {selectedGlyph.prediction_path.map((p: string, i: number) => (
                    <li key={i}>⧖ {p}</li>
                  ))}
                </ul>
              </div>
            )}
            {selectedGlyph.anchor && (
              <p><strong>Anchor:</strong> {selectedGlyph.anchor.type} ({selectedGlyph.anchor.env_obj_id})</p>
            )}
            {trace.length > 0 && (
              <div style={{ marginTop: "10px", textAlign: "left", maxHeight: "200px", overflowY: "auto" }}>
                <strong>Execution Trace (Tick History):</strong>
                <ul>
                  {trace.map((t, idx) => (
                    <li key={idx}>[{t.timestamp}] {t.event}: {JSON.stringify(t.data)}</li>
                  ))}
                </ul>
              </div>
            )}
            <button onClick={() => setSelectedGlyph(null)} style={{ marginTop: "15px", padding: "8px 16px" }}>Close</button>
          </div>
        </div>
      )}
    </>
  );
}