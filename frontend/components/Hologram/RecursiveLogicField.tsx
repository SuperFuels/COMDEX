import React, { useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

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
  const meshRef = React.useRef<THREE.Mesh>(null);

  // Pulse animation
  useFrame(({ clock }) => {
    if (meshRef.current) {
      const scale = 1 + 0.1 * Math.sin(clock.getElapsedTime() * 2);
      meshRef.current.scale.set(scale, scale, scale);
    }
  });

  const color = node.color || `hsl(${node.depth * 50}, 100%, 70%)`;

  return (
    <mesh ref={meshRef} position={[0, 0, 0]}>
      <sphereGeometry args={[0.4, 32, 32]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} />
    </mesh>
  );
}

function RecursiveBranch({ node, origin = new THREE.Vector3(0, 0, 0), level = 0 }: { node: GlyphNode; origin?: THREE.Vector3; level?: number }) {
  const radius = 3 + level * 2;
  const angleStep = (Math.PI * 2) / (node.children?.length || 1);

  return (
    <>
      <GlyphSphere node={node} />
      {node.children?.map((child, i) => {
        const angle = i * angleStep;
        const x = origin.x + radius * Math.cos(angle);
        const y = origin.y + radius * Math.sin(angle);
        const z = origin.z - level * 2;
        const childPos = new THREE.Vector3(x, y, z);

        return (
          <group position={childPos} key={child.id}>
            <line>
              <bufferGeometry>
                <bufferAttribute
                  attach="attributes-position"
                  array={new Float32Array([0, 0, 0, ...origin.toArray()])}
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