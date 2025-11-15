'use client';

import { Suspense, lazy } from 'react';

// local lazy import (same folder)
const ContainerMap2D = lazy(() => import('./ContainerMap2D'));

export default function Map2DPage() {
  return (
    <div className="p-4">
      <Suspense fallback={<div style={{ padding: 12 }}>Loading 2D…</div>}>
        <ContainerMap2D />
      </Suspense>
    </div>
  );
}