'use client';

import { Suspense, lazy } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';

// lazy-load the local 3D map component
const ContainerMap3D = lazy(() => import('./ContainerMap3D'));

export default function Map3DPage() {
  return (
    <div className="w-full h-full" style={{ height: 'calc(100vh - 120px)' }}>
      <Suspense fallback={<div style={{ padding: 12, color: '#aaa' }}>Loading 3D…</div>}>
        <Canvas camera={{ position: [8, 6, 8], fov: 50 }}>
          {/* Lights/scene content are inside ContainerMap3D already */}
          <ContainerMap3D />
          <OrbitControls enableDamping />
        </Canvas>
      </Suspense>
    </div>
  );
}