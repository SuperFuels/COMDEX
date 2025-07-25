// File: frontend/components/ContainerMap/HobermanSphereController.tsx

import React, { useEffect, useState } from 'react';
import HobermanSphere from './HobermanSphere';

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