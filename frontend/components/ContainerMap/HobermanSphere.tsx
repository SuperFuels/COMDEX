import * as THREE from 'three';
import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { a, useSpring } from '@react-spring/three';
import { Text } from '@react-three/drei';

interface HobermanSphereProps {
  position: [number, number, number];
  expanded: boolean;
}

export default function HobermanSphere({ position, expanded }: HobermanSphereProps) {
  const groupRef = useRef<THREE.Group>(null);
  const innerRingRef = useRef<THREE.Group>(null);
  const middleRingRef = useRef<THREE.Group>(null);
  const outerRingRef = useRef<THREE.Group>(null);

  const springs = useSpring({
    armLength: expanded ? 3.2 : 0.6,
    coreScale: expanded ? 2.4 : 0.4,
    emissiveIntensity: expanded ? 1.4 : 0.2,
    config: { mass: 1, tension: 190, friction: 20 },
  });

  // Animate gyroscopes
  useFrame(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.01;
      groupRef.current.rotation.x += 0.003;
    }
    if (innerRingRef.current) innerRingRef.current.rotation.x += 0.015;
    if (middleRingRef.current) middleRingRef.current.rotation.y += 0.01;
    if (outerRingRef.current) outerRingRef.current.rotation.z += 0.007;
  });

  const armAngles = useMemo(() => {
    const count = 18;
    return Array.from({ length: count }, (_, i) => (i / count) * Math.PI * 2);
  }, []);

  return (
    <group ref={groupRef} position={position}>
      {/* Core */}
      <a.mesh scale={springs.coreScale}>
        <sphereGeometry args={[1, 32, 32]} />
        <a.meshStandardMaterial
          color={expanded ? '#00f0ff' : '#8888ff'}
          emissive="#00f0ff"
          emissiveIntensity={springs.emissiveIntensity}
          transparent
          opacity={0.8}
        />
      </a.mesh>

      {/* Central symbolic glyph */}
      <Text position={[0, 0, 0.1]} fontSize={0.35} color="#ffffff" anchorX="center" anchorY="middle">
        ⬁
      </Text>

      {/* Gyroscopic rings */}
      <group ref={innerRingRef}>
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[1.8, 0.05, 16, 100]} />
          <meshStandardMaterial color="#00caff" emissive="#00f0ff" emissiveIntensity={0.4} />
        </mesh>
      </group>
      <group ref={middleRingRef}>
        <mesh rotation={[0, Math.PI / 2, 0]}>
          <torusGeometry args={[2.4, 0.05, 16, 100]} />
          <meshStandardMaterial color="#007aff" emissive="#00f0ff" emissiveIntensity={0.3} />
        </mesh>
      </group>
      <group ref={outerRingRef}>
        <mesh rotation={[0, 0, Math.PI / 2]}>
          <torusGeometry args={[3.0, 0.05, 16, 100]} />
          <meshStandardMaterial color="#0044ff" emissive="#00f0ff" emissiveIntensity={0.2} />
        </mesh>
      </group>

      {/* Mechanical arm deployment */}
      {armAngles.map((angle, i) => (
        <group key={i} rotation={[0, angle, 0]}>
          <a.mesh position={springs.armLength.to((l) => [l, 0, 0])}>
            <cylinderGeometry args={[0.05, 0.05, 1.8, 6]} />
            <meshStandardMaterial color="#00f0ff" />
          </a.mesh>
          <a.mesh position={springs.armLength.to((l) => [l + 1.1, 0, 0])}>
            <sphereGeometry args={[0.12, 16, 16]} />
            <meshStandardMaterial color="#ffffff" emissive="#00f0ff" emissiveIntensity={0.8} />
          </a.mesh>
        </group>
      ))}
    </group>
  );
}