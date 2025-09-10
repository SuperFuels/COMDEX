// File: frontend/components/QuantumField/PredictedLayerRenderer.tsx

import React, { useState } from "react";
import { Line } from "@react-three/drei";
import { Html } from "@react-three/drei";
import * as THREE from "three";

export interface PredictedNode {
  id: string;
  position: [number, number, number];
  delta?: number; // optional deviation from real node
  branch?: string; // optional prediction branch label
}

export interface PredictedLink {
  source: string;
  target: string;
}

interface Props {
  nodes: PredictedNode[];
  links: PredictedLink[];
  visible?: boolean;
}

const PredictedLayerRenderer: React.FC<Props> = ({ nodes, links, visible = true }) => {
  const nodeMap = Object.fromEntries(nodes.map((n) => [n.id, n.position]));

  if (!visible) return null;

  return (
    <group>
      {nodes.map((node) => (
        <mesh key={node.id} position={node.position}>
          <sphereGeometry args={[0.3, 24, 24]} />
          <meshStandardMaterial
            color="#00ccff"
            transparent
            opacity={0.3}
            emissive="#00ccff"
            emissiveIntensity={0.6}
            wireframe
          />
          {(node.delta != null || node.branch) && (
            <Html position={[node.position[0], node.position[1] + 0.8, node.position[2]]}>
              <div className="text-xs text-blue-300 bg-black/60 rounded px-2 py-1 shadow">
                {node.delta != null && <div>Δ {node.delta > 0 ? "+" : ""}{node.delta}</div>}
                {node.branch && <div>Branch: {node.branch}</div>}
              </div>
            </Html>
          )}
        </mesh>
      ))}

      {links.map((link, i) => {
        const start = nodeMap[link.source];
        const end = nodeMap[link.target];
        if (!start || !end) return null;
        return (
          <Line
            key={`predicted-link-${i}`}
            points={[new THREE.Vector3(...start), new THREE.Vector3(...end)]}
            color="#00ccff"
            lineWidth={1}
            dashed
            dashSize={0.3}
            gapSize={0.2}
            transparent
            opacity={0.4}
          />
        );
      })}
    </group>
  );
};

export default PredictedLayerRenderer;