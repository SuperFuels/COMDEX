import dynamic from 'next/dynamic';

const Scene = dynamic(() => import('@/components/AION/ContainerMap3DScene'), {
  ssr: false,
  loading: () => <div style={{ padding: 12, color: '#aaa' }}>Loading 3D…</div>,
});

export default function Page() {
  return <Scene />;
}