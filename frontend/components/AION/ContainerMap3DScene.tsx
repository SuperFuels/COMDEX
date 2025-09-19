'use client';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import ContainerMap3D from '@/components/AION/ContainerMap3D';

export default function ContainerMap3DScene() {
  return (
    <div style={{ width: '100%', height: '100vh', background: '#000' }}>
      <Canvas camera={{ position: [0, 0, 15], fov: 50 }}>
        <OrbitControls />
        <ContainerMap3D />
      </Canvas>
    </div>
  );
}