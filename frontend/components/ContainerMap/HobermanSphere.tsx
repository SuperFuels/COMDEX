// File: frontend/components/ContainerMap/HobermanSphere.tsx

import * as THREE from 'three';
import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { animated, useSpring } from '@react-spring/three';
import { Text } from '@react-three/drei';

interface HobermanSphereProps {
  position: [number, number, number];
  expanded: boolean;
}

function HobermanSphere({ position, expanded }: HobermanSphereProps) {
  const groupRef = useRef<THREE.Group>(null);

  const { armLength, coreScale, emissiveIntensity } = useSpring({
    armLength: expanded ? 2.8 : 0.6,
    coreScale: expanded ? 2.2 : 0.4,
    emissiveIntensity: expanded ? 1.2 : 0.2,
    config: { mass: 1, tension: 180, friction: 22 },
  });

  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.01;
      groupRef.current.rotation.x += 0.003;
    }
  });

  const armAngles = useMemo(() => {
    const count = 12;
    return Array.from({ length: count }, (_, i) => (i / count) * Math.PI * 2);
  }, []);

  return (
    <group ref={groupRef} position={position}>
      <animated.mesh scale={coreScale}>
        <icosahedronGeometry args={[1, 2]} />
        <animated.meshStandardMaterial
          color={expanded ? '#00f0ff' : '#8888ff'}
          wireframe
          emissive="#00f0ff"
          emissiveIntensity={emissiveIntensity}
        />
      </animated.mesh>

      {armAngles.map((angle, i) => (
        <animated.mesh
          key={i}
          position={[
            Math.cos(angle) * armLength.get(),
            0,
            Math.sin(angle) * armLength.get(),
          ]}
          rotation={[0, angle, 0]}
        >
          <cylinderGeometry args={[0.05, 0.05, 1.5, 6]} />
          <meshStandardMaterial color="#00f0ff" />
        </animated.mesh>
      ))}

      <Text
        position={[0, 0, 0.1]}
        fontSize={0.3}
        color="#ffffff"
        anchorX="center"
        anchorY="middle"
      >
        ⬁
      </Text>
    </group>
  );
}

export default HobermanSphere;