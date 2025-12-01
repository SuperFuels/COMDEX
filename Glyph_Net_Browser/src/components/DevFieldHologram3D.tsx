// Glyph_Net_Browser/src/components/DevFieldHologram3D.tsx
'use client';

import React, { useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Line as DreiLine } from '@react-three/drei';
import * as THREE from 'three';

// Drei's <Line> types are noisy in this setup, so wrap as any
const Line = (props: any) => <DreiLine {...props} />;

type GhxNode = { id: string; data: any };
type GhxEdge = { id: string; source: string; target: string; kind?: string };

export type GhxPacket = {
  ghx_version: string;
  origin: string;
  container_id: string;
  nodes: GhxNode[];
  edges: GhxEdge[];
  metadata?: Record<string, any>;
};

export interface DevFieldHologram3DProps {
  packet: GhxPacket | null;
  /** 'world' = card pinned to its grid tile, 'focus' = card pulled to centre */
  focusMode?: 'world' | 'focus';
  /** Optional callback when the card is clicked */
  onToggleFocus?: () => void;
}

/** simple deterministic hash → grid cell for container_id */
function containerSlot(id: string): { gx: number; gz: number } {
  let h = 0;
  for (let i = 0; i < id.length; i++) {
    h = (h * 31 + id.charCodeAt(i)) | 0;
  }
  const gx = ((h >> 1) % 7) - 3; // -3..3
  const gz = ((h >> 4) % 7) - 3;
  return { gx, gz };
}

/** pull ψ–κ–T-ish signature + some normalised scalars out of metadata */
/** pull ψ–κ–T-ish signature + some normalised scalars out of metadata */
function getPsiSignature(packet: GhxPacket | null) {
  const meta = ((packet && packet.metadata) || {}) as any;
  const sig = meta.psi_kappa_tau_signature || {};
  const nodeCount = meta.node_count ?? (packet?.nodes?.length ?? 0);

  const psi = typeof sig.psi === 'number' ? sig.psi : 0;
  const kappa = typeof sig.kappa === 'number' ? sig.kappa : 0;
  const tau = typeof sig.tau === 'number' ? sig.tau : 0;

  const rank = typeof sig.rank === 'number' ? sig.rank : 1;

  // avoid mixing ?? and || — do it explicitly
  let energy: number;
  if (typeof sig.energy === 'number') {
    energy = sig.energy;
  } else {
    const sum = psi + kappa + tau;
    energy = sum !== 0 ? sum : nodeCount;
  }

  const entropy =
    typeof sig.entropy === 'number'
      ? sig.entropy
      : Math.log2(nodeCount + 1);

  // Normalised-ish scalars we can feed into sizes / glow
  const complexity = Math.min(1, nodeCount / 64); // 0..1
  const energyNorm = Math.min(1, energy / 100.0); // 0..1
  const entropyNorm = Math.min(1, entropy / 8.0); // 0..1

  return {
    rank,
    energy,
    entropy,
    complexity,
    energyNorm,
    entropyNorm,
    nodeCount,
  };
}

/** holographic floor grid (slightly brighter blue lines) */
function HoloFloor() {
  const gridSize = 120;
  const divisions = 60;
  return (
    <gridHelper
      args={[
        gridSize,
        divisions,
        new THREE.Color('#1e293b'), // axis-ish
        new THREE.Color('#1d4ed8'), // brighter blue grid lines
      ]}
      position={[0, 0, 0]}
    />
  );
}

/** Simple camera rig that glides between world + focus positions */
function CameraRig({ focusMode }: { focusMode: 'world' | 'focus' }) {
  const { camera } = useThree();

  useFrame(() => {
    const targetPos =
      focusMode === 'focus'
        ? new THREE.Vector3(0, 4, 10) // closer in
        : new THREE.Vector3(0, 8, 18); // default orbit distance

    camera.position.lerp(targetPos, 0.05);

    const lookAtTarget =
      focusMode === 'focus'
        ? new THREE.Vector3(0, 3, 0)
        : new THREE.Vector3(0, 0, 0);

    camera.lookAt(lookAtTarget);
  });

  return null;
}

/** single standing hologram frame + etched nodes for one packet */
function HologramCard({
  packet,
  focusMode,
  onToggleFocus,
}: {
  packet: GhxPacket;
  focusMode: 'world' | 'focus';
  onToggleFocus?: () => void;
}) {
  const nodes = packet.nodes ?? [];
  const edges = packet.edges ?? [];

  const { gx, gz } = containerSlot(packet.container_id || 'default');
  const tileSpacing = 10;

  const psi = getPsiSignature(packet);
  const baseRadius = 1.4 + psi.complexity * 0.8; // bigger program → wider fan
  const nodeScale = 0.1 + psi.energyNorm * 0.1; // 0.10–0.20
  const cardGlow = 0.12 + psi.entropyNorm * 0.18; // 0.12–0.30 opacity

  // world vs focus position
  const worldPos = new THREE.Vector3(gx * tileSpacing, 2.8, gz * tileSpacing);
  const focusPos = new THREE.Vector3(0, 3, 0);
  const pos = focusMode === 'focus' ? focusPos : worldPos;

  // take a subset so giant ASTs don't just become noise
  const layoutNodes = useMemo(() => nodes.slice(0, 64), [nodes]);

  // layout nodes in a fan / arc
  const nodePositions = useMemo(() => {
    const map = new Map<string, THREE.Vector3>();
    const n = layoutNodes.length;
    if (!n) return map;

    const radius = baseRadius;
    const arc = Math.PI * 1.0; // 180°
    const start = -arc / 2;

    layoutNodes.forEach((node, i) => {
      const t = n === 1 ? 0 : i / (n - 1);
      const angle = start + arc * t;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius * 0.7;
      map.set(node.id, new THREE.Vector3(x, y, 0.04)); // float slightly in front of the glass
    });

    return map;
  }, [layoutNodes, baseRadius]);

  return (
    <group
      position={pos.toArray()}
      // clicking the card toggles world/focus mode
      onClick={(e) => {
        e.stopPropagation();
        onToggleFocus && onToggleFocus();
      }}
    >
      {/* frame plane, standing up on Z axis */}
      <mesh position={[0, 0, 0]}>
        <planeGeometry args={[7, 3.6]} />
        <meshBasicMaterial color="#0ea5e9" transparent opacity={cardGlow} />
      </mesh>

      {/* outer border */}
      <mesh position={[0, 0, 0.01]}>
        <planeGeometry args={[7.1, 3.7]} />
        <meshBasicMaterial
          color="#e5f0ff"
          wireframe
          transparent
          opacity={0.95}
        />
      </mesh>

      {/* subtle inner etched grid */}
      <group position={[0, 0, 0.02]}>
        {/* verticals */}
        {[...Array(5)].map((_, i) => {
          const x = -3.5 + (7 / 6) * (i + 1);
          const p1 = new THREE.Vector3(x, -1.8, 0);
          const p2 = new THREE.Vector3(x, 1.8, 0);
          return (
            <Line
              key={`v-${i}`}
              points={[p1, p2]}
              color="#64748b"
              transparent
              opacity={0.25}
              lineWidth={1}
            />
          );
        })}
        {/* horizontals */}
        {[...Array(3)].map((_, i) => {
          const y = -1.8 + (3.6 / 4) * (i + 1);
          const p1 = new THREE.Vector3(-3.5, y, 0);
          const p2 = new THREE.Vector3(3.5, y, 0);
          return (
            <Line
              key={`h-${i}`}
              points={[p1, p2]}
              color="#64748b"
              transparent
              opacity={0.25}
              lineWidth={1}
            />
          );
        })}
      </group>

      {/* edges as faint cyan lines */}
      {edges.map((e) => {
        const a = nodePositions.get(e.source);
        const b = nodePositions.get(e.target);
        if (!a || !b) return null;

        return (
          <Line
            key={e.id}
            points={[a, b]}
            color="#38bdf8"
            transparent
            opacity={0.35}
            lineWidth={1}
          />
        );
      })}

      {/* nodes: glowing orbs scaled by energy */}
      {layoutNodes.map((node, idx) => {
        const p = nodePositions.get(node.id);
        if (!p) return null;
        const isRoot = idx === 0;
        const r = nodeScale * (isRoot ? 1.6 : 1.0);

        return (
          <group key={node.id} position={p.toArray()}>
            <mesh>
              <sphereGeometry args={[r, 18, 18]} />
              <meshStandardMaterial
                color={isRoot ? '#fefce8' : '#e0f2fe'}
                emissive={isRoot ? '#facc15' : '#38bdf8'}
                emissiveIntensity={isRoot ? 3 : 2}
                transparent
                opacity={isRoot ? 1 : 0.95}
              />
            </mesh>
          </group>
        );
      })}

      {/* container "anchor" on floor below card */}
      <mesh position={[0, -2.2, 0]}>
        <cylinderGeometry args={[0.16, 0.16, 0.24, 24]} />
        <meshStandardMaterial
          color="#38bdf8"
          emissive="#38bdf8"
          emissiveIntensity={3}
        />
      </mesh>
    </group>
  );
}

export function DevFieldHologram3DScene({
  packet,
  focusMode = 'world',
  onToggleFocus,
}: DevFieldHologram3DProps) {
  return (
    <div style={{ width: '100%', height: '100%', background: '#020617' }}>
      <Canvas camera={{ position: [0, 8, 18], fov: 55 }}>
        <color attach="background" args={['#020617']} />
        <ambientLight intensity={0.55} />
        <directionalLight position={[12, 12, 6]} intensity={1.3} />

        <HoloFloor />

        {/* Smooth camera glide between world + focus modes */}
        <CameraRig focusMode={focusMode} />

        {packet && (
          <HologramCard
            packet={packet}
            focusMode={focusMode}
            onToggleFocus={onToggleFocus}
          />
        )}

        <OrbitControls
          enablePan
          enableZoom
          enableRotate
          maxPolarAngle={Math.PI * 0.95}
          minDistance={6}
          maxDistance={60}
        />
      </Canvas>
    </div>
  );
}