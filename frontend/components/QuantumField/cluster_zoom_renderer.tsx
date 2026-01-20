// File: frontend/components/QuantumField/cluster_zoom_renderer.tsx

import React, { useState } from "react";
import * as THREE from "three";
import { useFrame, useThree } from "@react-three/fiber";
import { Html as DreiHtml } from "@react-three/drei";

export interface GlyphNode {
  id: string;
  position: [number, number, number];
}

export interface ClusterZoomRendererProps {
  nodes: GlyphNode[];
  radius?: number;
  onZoomed?: (ids: string[]) => void;
}

// 🔢 Utility: 3D Euclidean distance
const distance = (a: [number, number, number], b: [number, number, number]) => {
  const dx = a[0] - b[0];
  const dy = a[1] - b[1];
  const dz = a[2] - b[2];
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
};

// 🧠 Cluster Detection (based on radius)
const detectClusters = (
  nodes: GlyphNode[],
  radius: number = 2
): GlyphNode[][] => {
  const clusters: GlyphNode[][] = [];
  const visited = new Set<string>();

  for (const node of nodes) {
    if (visited.has(node.id)) continue;
    const cluster = nodes.filter(
      (other) => node.id !== other.id && distance(node.position, other.position) <= radius
    );
    if (cluster.length > 1) {
      cluster.push(node);
      cluster.forEach((n) => visited.add(n.id));
      clusters.push(cluster);
    }
  }

  return clusters;
};

const ClusterZoomRenderer: React.FC<ClusterZoomRendererProps> = ({
  nodes,
  radius = 2.5,
  onZoomed,
}) => {
  const { camera } = useThree();
  const [hoveredCluster, setHoveredCluster] = useState<GlyphNode[] | null>(null);
  const [lastDetected, setLastDetected] = useState<string[]>([]);

  const clusters = detectClusters(nodes, radius);

  useFrame(() => {
    const camPos: [number, number, number] = [
      camera.position.x,
      camera.position.y,
      camera.position.z,
    ];

    const zoomedCluster = nodes.filter(
      (node) => distance(node.position, camPos) <= radius
    );

    const zoomedIds = zoomedCluster.map((n) => n.id).sort();
    const lastIds = [...lastDetected].sort();

    const isSame =
      zoomedIds.length === lastIds.length &&
      zoomedIds.every((id, i) => id === lastIds[i]);

    if (!isSame && zoomedIds.length > 1) {
      setLastDetected(zoomedIds);
      onZoomed?.(zoomedIds);
    }
  });

  return (
    <>
      {clusters.map((cluster, i) => (
        <group
          key={`cluster-${i}`}
          onPointerOver={() => setHoveredCluster(cluster)}
          onPointerOut={() => setHoveredCluster(null)}
          onClick={() => onZoomed?.(cluster.map((n) => n.id))}
        >
          {cluster.map((node) => (
            <mesh
              key={`zoom-node-${node.id}`}
              position={node.position}
              scale={hoveredCluster === cluster ? [1.5, 1.5, 1.5] : [1, 1, 1]}
            >
              <sphereGeometry args={[0.32, 32, 32]} />
              <meshStandardMaterial
                color="#ffdd33"
                transparent
                opacity={0.15}
                emissive="#ffff00"
                emissiveIntensity={hoveredCluster === cluster ? 1.8 : 0.5}
              />
            </mesh>
          ))}

          {/* 🏷️ Cluster Label */}
          <DreiHtml>
            <div className="text-sm font-bold text-yellow-400 drop-shadow">
              🔍 Cluster ({cluster.length})
            </div>
          </DreiHtml>
        </group>
      ))}
    </>
  );
};

export default ClusterZoomRenderer;