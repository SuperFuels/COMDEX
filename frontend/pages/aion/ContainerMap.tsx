'use client';

import React from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';

export interface ContainerMap3DProps {
  containers: {
    id: string;
    name: string;
    in_memory: boolean;
    connected: string[];
    glyph?: string;
    region?: string;
  }[];
}

const ContainerNode = ({
  position,
  label,
}: {
  position: [number, number, number];
  label: string;
}) => {
  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshStandardMaterial color="purple" />
      </mesh>

      {/* Label via Html to avoid Drei Text typings */}
      <group position={[0, 1, 0]}>
        <Html center distanceFactor={10}>
          <div
            style={{
              color: '#fff',
              fontSize: '12px',
              fontFamily: 'monospace',
              textShadow: '0 0 4px rgba(0,0,0,.75)',
              whiteSpace: 'nowrap',
            }}
          >
            {label}
          </div>
        </Html>
      </group>
    </group>
  );
};

export default function ContainerMap3D({ containers }: ContainerMap3DProps) {
  const radius = 5;
  const angleStep = (2 * Math.PI) / Math.max(containers.length, 1);

  return (
    <Canvas camera={{ position: [0, 0, 15], fov: 50 }}>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} />
      <OrbitControls />

      {containers.map((container, index) => {
        const angle = index * angleStep;
        const x = radius * Math.cos(angle);
        const z = radius * Math.sin(angle);
        return (
          <ContainerNode
            key={container.id}
            position={[x, 0, z]}
            label={container.glyph || container.name}
          />
        );
      })}
    </Canvas>
  );
}