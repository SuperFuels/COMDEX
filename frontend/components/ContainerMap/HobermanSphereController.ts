import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

// ✅ Dynamically import HobermanSphere to avoid SSR issues with three.js
const HobermanSphere = dynamic(() => import('./HobermanSphere'), {
  ssr: false,
  loading: () => null,
});

interface HobermanSphereControllerProps {
  containerMetadata: Record<string, any>;
  position: [number, number, number];
}

export function HobermanSphereController({
  containerMetadata,
  position,
}: HobermanSphereControllerProps) {
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const shouldExpand = containerMetadata?.symbolic_mode === 'expansion';
    setExpanded(shouldExpand);
  }, [containerMetadata]);

  return (
    <HobermanSphere
      position={position}
      expanded={expanded}
    />
  );
}

export default HobermanSphereController;