'use client';
import dynamic from 'next/dynamic';

// direct import is fine (pure DOM) – no SSR hazards
const ContainerMap2D = dynamic(() => import('@/components/AION/ContainerMap2D'), {
  ssr: false,
  loading: () => <div style={{ padding: 12 }}>Loading 2D…</div>,
});

export default function Page() {
  return (
    <div className="p-4">
      <ContainerMap2D />
    </div>
  );
}