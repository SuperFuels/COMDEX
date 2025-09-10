// ✅ File: frontend/components/QuantumField/Memory/goal_nodes_renderer.tsx

import React from "react";
import { Html } from "@react-three/drei";
import * as THREE from "three";

export interface GoalNode {
  id: string;
  position: [number, number, number];
  label: string;
  type: "goal" | "strategy" | "milestone";
  status?: "complete" | "in-progress" | "pending";
  color?: string;
}

const statusColorMap: Record<string, string> = {
  complete: "#00ff00",
  "in-progress": "#ffaa00",
  pending: "#ffffff",
};

export const GoalNodeRenderer: React.FC<{ node: GoalNode }> = ({ node }) => {
  const color = node.color || statusColorMap[node.status || "pending"];

  return (
    <group position={node.position as [number, number, number]}>
      <mesh>
        <sphereGeometry args={[0.15, 32, 32]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.6} />
      </mesh>
      <Html distanceFactor={10} className="text-xs text-white text-center">
        <div className="bg-black/80 px-2 py-1 rounded-md">
          {node.type.toUpperCase()}: {node.label}
        </div>
      </Html>
    </group>
  );
};

export const GoalNodesLayer: React.FC<{ nodes: GoalNode[] }> = ({ nodes }) => {
  return (
    <>
      {nodes.map((node) => (
        <GoalNodeRenderer key={node.id} node={node} />
      ))}
    </>
  );
};