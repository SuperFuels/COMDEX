// frontend/pages/aion/quantum-field.tsx
'use client';

import React from 'react';
import dynamic from 'next/dynamic';
import { QFCFocusProvider } from '@/components/QuantumField/qfc_focus_context';
import type { GetServerSideProps } from "next";

export const getServerSideProps: GetServerSideProps = async () => {
  return { props: {} };
};
// Use the loader, not the raw canvas, and disable SSR
const QuantumFieldCanvasLoader = dynamic(
  () => import('@/components/Hologram/QuantumFieldCanvasLoader'),
  { ssr: false }
);

export default function QuantumFieldPage() {
  return (
    <div className="w-screen h-screen bg-black">
      <QFCFocusProvider>
        <QuantumFieldCanvasLoader containerId="default" />
      </QFCFocusProvider>
    </div>
  );
}