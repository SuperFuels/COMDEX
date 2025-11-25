"use client";

import React from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three"; // ok to keep, only used inside, not in props

type Vec3 = [number, number, number];

interface GlyphNode {
  id: string;
  label: string;
  depth: number;
  children?: GlyphNode[];
  color?: string;
}

interface RecursiveLogicFieldProps {
  root: GlyphNode;
}

function GlyphSphere({ node }: { node: GlyphNode }) {
  // loosen type to dodge @types/three mismatch
  const meshRef = React.useRef<any>(null);

  useFrame(({ clock }) => {
    if (meshRef.current) {
      const scale = 1 + 0.1 * Math.sin(clock.getElapsedTime() * 2);
      meshRef.current.scale.set(scale, scale, scale);
    }
  });

  const color = node.color || `hsl(${node.depth * 50}, 100%, 70%)`;

  return (
    <mesh
      ref={(n: any) => {
        meshRef.current = n;
      }}
      position={[0, 0, 0]}
    >
      <sphereGeometry args={[0.4, 32, 32]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} />
    </mesh>
  );
}

function RecursiveBranch({
  node,
  origin = [0, 0, 0],
  level = 0,
}: {
  node: GlyphNode;
  origin?: Vec3;
  level?: number;
}) {
  const radius = 3 + level * 2;
  const angleStep = (Math.PI * 2) / (node.children?.length || 1);

  return (
    <>
      <GlyphSphere node={node} />
      {node.children?.map((child, i) => {
        const angle = i * angleStep;
        const x = origin[0] + radius * Math.cos(angle);
        const y = origin[1] + radius * Math.sin(angle);
        const z = origin[2] - level * 2;
        const childPos: Vec3 = [x, y, z];

        return (
          <group position={childPos} key={child.id}>
            <line>
              <bufferGeometry>
                <bufferAttribute
                  attach="attributes-position"
                  array={new Float32Array([
                    0, 0, 0,
                    origin[0], origin[1], origin[2],
                  ])}
                  count={2}
                  itemSize={3}
                />
              </bufferGeometry>
              <lineBasicMaterial color="white" />
            </line>
            <RecursiveBranch node={child} origin={childPos} level={level + 1} />
          </group>
        );
      })}
    </>
  );
}

export default function RecursiveLogicField({ root }: RecursiveLogicFieldProps) {
  return (
    <div className="w-full h-screen bg-black">
      <Canvas camera={{ position: [0, 0, 15], fov: 60 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} />
        <RecursiveBranch node={root} />
        <OrbitControls />
      </Canvas>
    </div>
  );
}