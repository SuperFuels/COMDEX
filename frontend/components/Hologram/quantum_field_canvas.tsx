import React, { useRef, useEffect, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import { Card } from "@/components/ui/card";

interface GlyphNode {
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
}

interface Link {
  source: string;
  target: string;
  type?: "entangled" | "teleport" | "logic";
}

interface QuantumFieldCanvasProps {
  nodes: GlyphNode[];
  links: Link[];
  onTeleport?: (targetContainerId: string) => void;
}

// 🎨 Color links by type
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

const Node = ({ node, onTeleport }: { node: GlyphNode; onTeleport?: (id: string) => void }) => {
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
        </Card>
      </Html>
    </mesh>
  );
};

const LinkLine = ({ source, target, type }: { source: GlyphNode; target: GlyphNode; type?: string }) => {
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

const QuantumFieldCanvas: React.FC<QuantumFieldCanvasProps> = ({ nodes, links, onTeleport }) => {
  const getNodeById = (id: string) => nodes.find((n) => n.id === id);

  return (
    <div className="h-full w-full">
      <Canvas camera={{ position: [0, 0, 10], fov: 50 }}>
        <ambientLight intensity={0.7} />
        <pointLight position={[10, 10, 10]} />
        <OrbitControls enableZoom enablePan enableRotate />

        {/* 🔗 Render links */}
        {links.map((link, i) => {
          const source = getNodeById(link.source);
          const target = getNodeById(link.target);
          if (!source || !target) return null;
          return (
            <LinkLine key={i} source={source} target={target} type={link.type} />
          );
        })}

        {/* ⚛ Render nodes */}
        {nodes.map((node) => (
          <Node key={node.id} node={node} onTeleport={onTeleport} />
        ))}
      </Canvas>
    </div>
  );
};

export default QuantumFieldCanvas;

// ✅ Wrapper to load data from API
export const QuantumFieldCanvasLoader: React.FC<{ containerId: string; onTeleport?: (id: string) => void }> = ({
  containerId,
  onTeleport,
}) => {
  const [data, setData] = useState<{ nodes: GlyphNode[]; links: Link[] }>({
    nodes: [],
    links: [],
  });

  useEffect(() => {
    fetch(`/api/qfc_view/${containerId}`)
      .then((res) => res.json())
      .then((json) => setData(json));
  }, [containerId]);

  return <QuantumFieldCanvas {...data} onTeleport={onTeleport} />;
};