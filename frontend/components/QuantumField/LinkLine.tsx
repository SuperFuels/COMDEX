// 📁 frontend/components/QuantumField/LinkLine.tsx
import React, { useMemo } from "react";
import * as THREE from "three";
import { rerouteBeam } from "@/components/QuantumField/beam_rerouter";

type LinkLineProps = {
  source: { position: [number, number, number] };
  target: { position: [number, number, number] };
  focusPoint?: [number, number, number];
  isDream?: boolean;
};

export const LinkLine: React.FC<LinkLineProps> = ({
  source,
  target,
  focusPoint,
  isDream = false,
}) => {
  const line = useMemo(() => {
    const pathPoints = rerouteBeam(source.position, target.position, focusPoint)
      .map((p) => new THREE.Vector3(...p));

    const geometry = new THREE.BufferGeometry().setFromPoints(pathPoints);
    const material = new THREE.LineBasicMaterial({
      color: isDream ? "#d946ef" : "#aaa",
      linewidth: 1,
      transparent: true,
      opacity: isDream ? 0.4 : 0.8,
    });

    return new THREE.Line(geometry, material);
  }, [source.position, target.position, focusPoint, isDream]);

  return <primitive object={line} />;
};