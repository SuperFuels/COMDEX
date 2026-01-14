"use client";

import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Line, Sphere, Float } from "@react-three/drei";
import * as THREE from "three";

/**
 * VOL-TOP: TOPOLOGICAL ENTANGLEMENT GRAPH
 * Logic: Node-Edge Adjacency + Chiral Inversion
 * Soul: Flux-linked tensors with smoothed gate transitions
 */

type TopoNode = { id: string; w?: number };
type TopoEdge = { a: string; b: string; w?: number };

type QFCTopology = {
  epoch: number;
  nodes: TopoNode[];
  edges: TopoEdge[];
  gate?: number; 
};

function hash01(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 10000) / 10000;
}

export default function QFCTopologyGraph({ frame }: { frame: any | null }) {
  const topo = (frame?.topology as QFCTopology | undefined);
  if (!topo || !topo.nodes?.length) return null;

  const chirality = (frame?.flags?.chirality ?? 1) === -1 ? -1 : 1;
  const theme = frame?.theme ?? {};
  
  const tRef = useRef(0);
  const gateSm = useRef(1.0);
  const [pulse, setPulse] = useState(0);

  // Materials & Colors
  const nodeColor = chirality === -1 ? theme.danger ?? "#ef4444" : theme.connect ?? "#22d3ee";
  const edgeColor = chirality === -1 ? "#ff1a1a" : theme.matter ?? "#94a3b8";

  // Gate Smoothing Logic
  const gateTarget = THREE.MathUtils.clamp(frame?.topo_gate01 ?? topo?.gate ?? 1, 0, 1);

  useFrame((_state, dtRaw) => {
    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;
    
    // Smooth gate transition (Metric closure)
    gateSm.current = THREE.MathUtils.lerp(gateSm.current, gateTarget, 0.1);
    
    if (tRef.current % 0.5 < 0.02) setPulse(tRef.current);
  });

  // Spatial Layout Calculation
  const { nodes, edges, posById } = useMemo(() => {
    const nodes = topo.nodes;
    const N = nodes.length;
    const radius = 6.5 + gateTarget * 1.5;
    const posById: Record<string, THREE.Vector3> = {};

    nodes.forEach((node, i) => {
      const angle = (i / N) * Math.PI * 2;
      const h1 = hash01(node.id);
      const h2 = hash01(node.id + "alt");
      
      // Ring layout with hash-based variance
      const x = Math.cos(angle) * (radius + (h1 - 0.5) * 2);
      const y = (h2 - 0.5) * 3 * gateTarget;
      const z = Math.sin(angle) * (radius + (h1 - 0.5) * 2);

      posById[node.id] = new THREE.Vector3(chirality * x, y, z);
    });

    return { nodes, edges: topo.edges, posById };
  }, [topo.epoch, chirality, gateTarget, topo.nodes.length]);

  return (
    <group>
      {/* Flux Edges */}
      {edges.map((edge, i) => {
        const start = posById[edge.a];
        const end = posById[edge.b];
        if (!start || !end) return null;

        const weight = edge.w ?? 1;
        const opacity = (0.1 + 0.5 * gateSm.current) * (0.8 + 0.2 * Math.sin(tRef.current * 2 + i));

        return (
          <Line
            key={`e-${i}-${topo.epoch}`}
            points={[start, end]}
            color={edgeColor}
            lineWidth={1.5 * weight * gateSm.current}
            transparent
            opacity={opacity}
            blending={THREE.AdditiveBlending}
          />
        );
      })}

      {/* Tensor Nodes */}
      {nodes.map((node, i) => {
        const pos = posById[node.id];
        const weight = node.w ?? 1;
        const radius = (0.2 + 0.15 * weight) * (0.9 + 0.1 * Math.sin(tRef.current * 3 + i));

        return (
          <Float 
            key={`n-${node.id}`} 
            position={pos.toArray()} 
            speed={2} 
            rotationIntensity={0.5} 
            floatIntensity={0.5}
          >
            <mesh>
              <sphereGeometry args={[radius, 32, 32]} />
              <meshStandardMaterial
                color={nodeColor}
                emissive={nodeColor}
                emissiveIntensity={chirality === -1 ? 2.5 : 0.8 * gateSm.current}
                metalness={0.8}
                roughness={0.2}
              />
              
              {/* Internal Halo for nodes */}
              <Sphere args={[radius * 1.4, 16, 16]}>
                <meshBasicMaterial 
                  color={nodeColor} 
                  transparent 
                  opacity={0.1 * gateSm.current} 
                  wireframe 
                />
              </Sphere>
            </mesh>
          </Float>
        );
      })}

      {/* Central Singularity Light */}
      <pointLight 
        intensity={2 * gateSm.current} 
        color={nodeColor} 
        distance={20} 
        decay={2}
      />
    </group>
  );
}