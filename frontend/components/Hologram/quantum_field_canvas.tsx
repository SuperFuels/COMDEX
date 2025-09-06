// File: frontend/components/QuantumField/QuantumFieldCanvas.tsx

import React, { useRef, useEffect, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import { Card } from "@/components/ui/card";
import { QWaveBeam } from "@/components/QuantumField/beam_renderer";

const [beamData, setBeamData] = useState<any | null>(null);

useEffect(() => {
  fetch("/api/test-mixed-beams")
    .then((res) => res.json())
    .then(setBeamData)
    .catch(console.error);
}, []);

// Types
export interface GlyphNode {
  id: string;
  label: string;
  position: [number, number, number];
  containerId?: string;
  predicted?: boolean;
  color?: string;
  trailId?: string;
  goalMatchScore?: number;
  rewriteSuccessProb?: number;
  entropy?: number;
  tick?: number;
  collapse_state?: string;
}

interface Link {
  source: string;
  target: string;
  type?: "entangled" | "teleport" | "logic";
  tick?: number;
}

interface QuantumFieldCanvasProps {
  nodes: GlyphNode[];
  links: Link[];
  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (targetContainerId: string) => void;
}

// 🎨 Link color by type
const getLinkColor = (type?: string): string => {
  switch (type) {
    case "entangled":
      return "#ff66ff";
    case "teleport":
      return "#00ffff";
    case "logic":
      return "#66ff66";
    default:
      return "#8888ff";
  }
};

// 🌐 Individual glyph node
const Node = ({
  node,
  onTeleport,
}: {
  node: GlyphNode;
  onTeleport?: (id: string) => void;
}) => {
  const ref = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const pulseRef = useRef(0);

  useFrame(() => {
    if (ref.current && node.predicted) {
      pulseRef.current += 0.05;
      const scale = 1 + 0.1 * Math.sin(pulseRef.current);
      ref.current.scale.set(scale, scale, scale);
    }
    if (ref.current && hovered) {
      ref.current.rotation.y += 0.01;
    }
  });

  return (
    <mesh
      ref={ref}
      position={node.position}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
      onClick={() => node.containerId && onTeleport?.(node.containerId)}
    >
      <sphereGeometry args={[0.3, 32, 32]} />
      <meshStandardMaterial
        color={node.color || (node.predicted ? "#00ffff" : "#ffffff")}
        emissive={node.predicted ? "#00ffff" : "#000000"}
        emissiveIntensity={node.predicted ? 1.5 : 0}
      />
      <Html>
        <Card className="p-2 rounded-xl shadow-lg text-xs text-center bg-white/80 backdrop-blur">
          <p className="font-bold">{node.label}</p>
          {node.predicted && (
            <p className="text-yellow-500 font-semibold">Predicted</p>
          )}
          {node.trailId && (
            <p className="text-pink-500">Trail: {node.trailId}</p>
          )}
          {typeof node.goalMatchScore === "number" && (
            <p className="text-green-600">
              🎯 Goal: {Math.round(node.goalMatchScore * 100)}%
            </p>
          )}
          {typeof node.rewriteSuccessProb === "number" && (
            <p className="text-blue-600">
              🔁 Rewrite: {Math.round(node.rewriteSuccessProb * 100)}%
            </p>
          )}
          {typeof node.entropy === "number" && (
            <p className="text-red-600">
              ♾ Entropy: {node.entropy.toFixed(2)}
            </p>
          )}
          {node.collapse_state && (
            <p className="text-gray-500">Collapse: {node.collapse_state}</p>
          )}
        </Card>
      </Html>
    </mesh>
  );
};

// 🔗 Visual link line
const LinkLine = ({
  source,
  target,
  type,
}: {
  source: GlyphNode;
  target: GlyphNode;
  type?: string;
}) => {
  const points = [
    new THREE.Vector3(...source.position),
    new THREE.Vector3(...target.position),
  ];
  const geometry = new THREE.BufferGeometry().setFromPoints(points);

  return (
    <line geometry={geometry}>
      <lineBasicMaterial attach="material" color={getLinkColor(type)} linewidth={2} />
    </line>
  );
};

// 🧠 Main QFC Component
const QuantumFieldCanvas: React.FC<QuantumFieldCanvasProps> = ({
  nodes,
  links,
  tickFilter,
  showCollapsed = true,
  onTeleport,
}) => {
  const getNodeById = (id: string) => nodes.find((n) => n.id === id);

  const filteredNodes = nodes.filter((node) => {
    const matchTick = tickFilter === undefined || node.tick === tickFilter;
    const matchCollapse =
      showCollapsed || node.collapse_state !== "collapsed";
    return matchTick && matchCollapse;
  });

  const filteredLinks = links.filter((link) => {
    const matchTick = tickFilter === undefined || link.tick === tickFilter;
    return matchTick;
  });

  return (
    <div className="h-full w-full">
      <Canvas camera={{ position: [0, 0, 10], fov: 50 }}>
        <ambientLight intensity={0.7} />
        <pointLight position={[10, 10, 10]} />
        <OrbitControls enableZoom enablePan enableRotate />

        {/* 🔗 Render filtered links */}
        {filteredLinks.map((link, i) => {
          const source = getNodeById(link.source);
          const target = getNodeById(link.target);
          if (!source || !target) return null;
          return (
            <LinkLine
              key={i}
              source={source}
              target={target}
              type={link.type}
            />
          );
        })}

        {/* 💫 Render QWaveBeams between nodes */}
        {filteredLinks.map((link, i) => {
          const source = getNodeById(link.source);
          const target = getNodeById(link.target);
          if (!source || !target) return null;

          return (
            <QWaveBeam
              key={`beam-${i}`}
              source={source.position}
              target={target.position}
              prediction={source.predicted || target.predicted}
              collapseState={source.collapse_state || target.collapse_state}
              sqiScore={
                source.goalMatchScore ??
                source.rewriteSuccessProb ??
                target.goalMatchScore ??
                target.rewriteSuccessProb ??
                0
              }
              show={true}
            />
          );
        })}

        {/* 🌈 Render glyphs from beamData if present */}
        {beamData?.glyphs?.map((glyph: BeamGlyphNode) => (
          <Node key={`beam-glyph-${glyph.id}`} node={glyph} onTeleport={onTeleport} />
        ))}

        {/* 🚀 Render mixed QWave beams from beamData */}
        {beamData?.beams?.map((beam: any) => (
          <QWaveBeam
            key={`mixed-beam-${beam.id}`}
            source={beam.source}
            target={beam.target}
            prediction={beam.predicted}
            collapseState={beam.collapse_state}
            sqiScore={beam.sqiScore || 0}
            show={true}
          />
        ))}

        {/* ⚛ Render filtered nodes */}
        {filteredNodes.map((node) => (
          <Node key={node.id} node={node} onTeleport={onTeleport} />
        ))}
      </Canvas>

        {/* ⚛ Render filtered nodes */}
        {filteredNodes.map((node) => (
          <Node key={node.id} node={node} onTeleport={onTeleport} />
        ))}
      </Canvas>
    </div>
  );
};

export default QuantumFieldCanvas;

// 🧲 Loader Wrapper
import { snapToPolarGrid } from "@/components/QuantumField/polar_snap"; // ⬅️ ADD THIS IMPORT
export const QuantumFieldCanvasLoader: React.FC<{
  containerId: string;
  tickFilter?: number;
  showCollapsed?: boolean;
  onTeleport?: (id: string) => void;
}> = ({ containerId, tickFilter, showCollapsed, onTeleport }) => {
  const [data, setData] = useState<{ nodes: GlyphNode[]; links: Link[] }>({
    nodes: [],
    links: [],
  });

  useEffect(() => {
    fetch(`/api/qfc_view/${containerId}`)
      .then((res) => res.json())
      .then((json) => {
        const nodes = json.nodes;
        const links = json.links;

        // 🧭 Snap to polar grid around first node (if exists)
        const centerId = nodes[0]?.id;
        const snappedNodes = centerId
          ? snapToPolarGrid(nodes, centerId)
          : nodes;

        setData({ nodes: snappedNodes, links });
      });
  }, [containerId]);

  return (
    <QuantumFieldCanvas
      {...data}
      tickFilter={tickFilter}
      showCollapsed={showCollapsed}
      onTeleport={onTeleport}
    />
  );
};