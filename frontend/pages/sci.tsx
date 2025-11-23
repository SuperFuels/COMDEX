// frontend/pages/sci.tsx
'use client';

import dynamic from "next/dynamic";

const IDE = dynamic(() => import("../sci/pages/IDE"), { ssr: false });

export default function SciPage() {
  return <IDE />;
}