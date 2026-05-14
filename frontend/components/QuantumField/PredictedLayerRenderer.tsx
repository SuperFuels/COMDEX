// File: frontend/components/QuantumField/PredictedLayerRenderer.tsx
"use client";

import React, { useEffect, useMemo } from "react";
import { Html as DreiHtml } from "@react-three/drei";
import * as THREE from "three";

/* ----------------------------- Types ----------------------------- */

export interface PredictedNode {
  id: string;
  position: [number, number, number];
  delta?: number;   // deviation from real node
  branch?: string;  // prediction branch label
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

/* ----------------------- Simple dashed line ---------------------- */
/** A dashed WebGL line rendered via <primitive> to avoid SVG <line> typings. */
const DashedLine: React.FC<{
  from: [number, number, number];
  to: [number, number, number];
  color?: string;
  opacity?: number;
  dashSize?: number;
  gapSize?: number;
}> = ({ from, to, color = "#00ccff", opacity = 0.4, dashSize = 0.3, gapSize = 0.2 }) => {
  // Build geometry/material/line once per endpoints
  const line = useMemo(() => {
    const positions = new Float32Array([...from, ...to]);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    const material = new THREE.LineDashedMaterial({
      color: new THREE.Color(color),
      transparent: true,
      opacity,
      dashSize,
      gapSize,
    });

    const l = new THREE.Line(geometry, material);
    l.computeLineDistances(); // required for dashes to appear
    return l;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [from[0], from[1], from[2], to[0], to[1], to[2], color, opacity, dashSize, gapSize]);

  // Dispose when unmounted
  useEffect(() => {
    return () => {
      line.geometry.dispose();
      (line.material as THREE.Material).dispose();
    };
  }, [line]);

  return <primitive object={line} />;
};

/* ---------------------- Predicted layer view --------------------- */

const PredictedLayerRenderer: React.FC<Props> = ({ nodes, links, visible = true }) => {
  const nodeMap: Record<string, [number, number, number]> = useMemo(
    () => Object.fromEntries(nodes.map((n) => [n.id, n.position])),
    [nodes]
  );

  if (!visible) return null;

  return (
    <group>
      {/* Nodes */}
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
            <DreiHtml position={[node.position[0], node.position[1] + 0.8, node.position[2]]}>
              <div className="text-xs text-blue-300 bg-black/60 rounded px-2 py-1 shadow">
                {node.delta != null && (
                  <div>
                    Δ {node.delta > 0 ? "+" : ""}
                    {node.delta}
                  </div>
                )}
                {node.branch && <div>Branch: {node.branch}</div>}
              </div>
            </DreiHtml>
          )}
        </mesh>
      ))}

      {/* Links */}
      {links.map((link, i) => {
        const start = nodeMap[link.source];
        const end = nodeMap[link.target];
        if (!start || !end) return null;

        return (
          <DashedLine
            key={`predicted-link-${i}`}
            from={start}
            to={end}
            color="#00ccff"
            opacity={0.4}
            dashSize={0.3}
            gapSize={0.2}
          />
        );
      })}
    </group>
  );
};

export default PredictedLayerRenderer;