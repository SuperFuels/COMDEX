// frontend/pages/aion/codex-hud.tsx
'use client';

import dynamic from 'next/dynamic';

const GHXVisualizerField = dynamic(() => import('@/components/Hologram/ghx_visualizer_field'), { ssr: false });
const CodexHUD = dynamic(() => import('@/components/AION/CodexHUD'), { ssr: false });

export default function CodexHudPage() {
  return (
    <div className="h-screen grid md:grid-cols-2 gap-2 p-2 bg-black">
      <div className="border border-neutral-800 rounded-lg overflow-hidden">
        <GHXVisualizerField containerId="default" />
      </div>
      <div className="border border-neutral-800 rounded-lg overflow-hidden">
        <CodexHUD />
      </div>
    </div>
  );
}