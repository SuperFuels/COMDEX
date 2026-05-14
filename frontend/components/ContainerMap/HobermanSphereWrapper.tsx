'use client';
import dynamic from 'next/dynamic';
import React from 'react';

const HobermanSphere = dynamic(() => import('./HobermanSphere'), {
  ssr: false,
}) as React.ComponentType<{
  position: [number, number, number];
  containerId: string;
}>;

interface Props {
  position: [number, number, number];
  containerId: string;
}

const HobermanSphereWrapper: React.FC<Props> = ({ position, containerId }) => {
  return <HobermanSphere position={position} containerId={containerId} />;
};

export default HobermanSphereWrapper;