// File: frontend/components/holography/quantum_field_canvas.tsx

import React, { useRef, useEffect, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface GlyphNode {
  id: string;
  label: string;
  position: [number, number, number];
  containerId?: string;
  predicted?: boolean;
  color?: string;
  trailId?: string;
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

const Node = ({ node, onTeleport }: { node: GlyphNode; onTeleport?: (id: string) => void }) => {
  const ref = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  useFrame(() => {
    if (ref.current && hovered) {
      ref.current.rotation.y += 0.02;
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
      <meshStandardMaterial color={node.color || (node.predicted ? "#00ffff" : "#ffffff")} />
      <Html>
        <Card className="p-2 rounded-xl shadow-md text-xs text-center">
          <p>{node.label}</p>
          {node.predicted && <p className="text-xs text-yellow-400">Predicted</p>}
          {node.trailId && <p className="text-xs text-pink-400">Trail: {node.trailId}</p>}
        </Card>
      </Html>
    </mesh>
  );
};

const LinkLine = ({ source, target }: { source: GlyphNode; target: GlyphNode }) => {
  const points = [
    new THREE.Vector3(...source.position),
    new THREE.Vector3(...target.position),
  ];
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  return (
    <line geometry={geometry}>
      <lineBasicMaterial attach="material" color="#8888ff" linewidth={2} />
    </line>
  );
};

const QuantumFieldCanvas: React.FC<QuantumFieldCanvasProps> = ({ nodes, links, onTeleport }) => {
  const getNodeById = (id: string) => nodes.find((n) => n.id === id);

  return (
    <div className="h-full w-full">
      <Canvas camera={{ position: [0, 0, 10], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} />
        <OrbitControls enableZoom enablePan enableRotate />

        {links.map((link, i) => {
          const source = getNodeById(link.source);
          const target = getNodeById(link.target);
          if (!source || !target) return null;
          return <LinkLine key={i} source={source} target={target} />;
        })}

        {nodes.map((node) => (
          <Node key={node.id} node={node} onTeleport={onTeleport} />
        ))}
      </Canvas>
    </div>
  );
};

export default QuantumFieldCanvas;