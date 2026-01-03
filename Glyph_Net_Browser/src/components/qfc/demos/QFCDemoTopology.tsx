"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";

import type { QFCFrame } from "../../QFCViewport";

type TopoNode = { id: string; w?: number };
type TopoEdge = { a: string; b: string; w?: number };

type QFCTopology = {
  epoch: number;
  nodes: TopoNode[];
  edges: TopoEdge[];
  gate?: number; // 0..1
};

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const n = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);

function hash01(s: string) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 10000) / 10000;
}

export default function QFCDemoTopology({ frame }: { frame: QFCFrame | null }) {
  // Stage C: read topology from frame (not inferred)
  const topo = (frame?.topology as unknown as QFCTopology | undefined) ?? undefined;

  const chirality: 1 | -1 = (frame?.flags?.chirality ?? 1) === -1 ? -1 : 1;
  const theme: any = frame?.theme ?? {};

  const nodeColor = new THREE.Color(theme.connect ?? "#22d3ee");
  const edgeColor = new THREE.Color(theme.matter ?? "#94a3b8");
  const mirrorTint = new THREE.Color(theme.danger ?? "#ef4444");

  // ✅ dt clamp + stable time + gate smoothing (standard)
  const tRef = useRef(0);
  const gateSm = useRef(1.0);

  // ✅ prefer plumbed gate if present
  const gateTarget = clamp01(Number((frame as any)?.topo_gate01 ?? topo?.gate ?? 1));

  useFrame((_state, dtRaw) => {
    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;

    const lerpK = 1 - Math.exp(-dtc * 10.0);
    gateSm.current = gateSm.current + (gateTarget - gateSm.current) * lerpK;
  });

  const gate = gateSm.current;

  // If no topology, render nothing (true Stage C)
  if (!topo || !topo.nodes?.length) return null;

  const edgeOpacity = 0.15 + 0.65 * gate;

  const { nodes, edges, posById } = useMemo(() => {
    const nodes = topo?.nodes ?? [];
    const edges = topo?.edges ?? [];

    // ring layout, stable by id/order
    const N = Math.max(1, nodes.length);
    const radiusBase = 6.5;
    const radius = radiusBase + gateTarget * 0.6; // base radius uses target gate (stable)

    const posById: Record<string, THREE.Vector3> = {};

    nodes.forEach((node, i) => {
      const t = (i / N) * Math.PI * 2;
      const wobble = (hash01(node.id) - 0.5) * 1.2;
      const y = (hash01(node.id + ":y") - 0.5) * 1.4;

      const x = Math.cos(t) * (radius + wobble);
      const z = Math.sin(t) * (radius + wobble);

      // chirality mirror: flip X
      posById[node.id] = new THREE.Vector3(chirality * x, y, z);
    });

    return { nodes, edges, posById };
  }, [
    topo?.epoch,
    chirality,
    gateTarget,
    topo?.nodes?.length,
    topo?.edges?.length,
  ]);

  const edgeStyle = (chirality === -1 ? mirrorTint : edgeColor).getStyle();
  const nodeStyle = (chirality === -1 ? mirrorTint : nodeColor).getStyle();

  return (
    <group>
      {/* edges */}
      {edges.map((e, i) => {
        const a = posById[e.a];
        const b = posById[e.b];
        if (!a || !b) return null;

        const w = Math.max(0.5, Math.min(2.5, n(e.w, 1)));

        return (
          <Line
            key={`e:${e.a}:${e.b}:${i}`}
            points={[a, b]}
            color={edgeStyle}
            lineWidth={1 + 0.8 * w}
            transparent
            opacity={edgeOpacity}
          />
        );
      })}

      {/* nodes */}
      {nodes.map((node) => {
        const p = posById[node.id];
        if (!p) return null;

        const w = Math.max(0.6, Math.min(2.0, n(node.w, 1)));
        const r = 0.18 + 0.12 * w + 0.08 * gate;

        return (
          <mesh key={`n:${node.id}`} position={p}>
            <sphereGeometry args={[r, 24, 18]} />
            <meshStandardMaterial
              color={nodeStyle}
              emissive={nodeStyle}
              emissiveIntensity={0.35 + 0.55 * gate}
              roughness={0.25}
              metalness={0.15}
              transparent
              opacity={0.95}
            />
          </mesh>
        );
      })}
    </group>
  );
}