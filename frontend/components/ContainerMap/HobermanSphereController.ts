// File: frontend/components/ContainerMap/HobermanSphereController.tsx

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import React from 'react';

// ✅ Clean dynamic import + type
const DynamicHobermanSphere = dynamic(() => import('./HobermanSphere'), {
  ssr: false,
}) as React.ComponentType<{
  position: [number, number, number];
  expanded: boolean;
}>;

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
    <DynamicHobermanSphere
      position={position}
      expanded={expanded}
    />
  );
}

export default HobermanSphereController;