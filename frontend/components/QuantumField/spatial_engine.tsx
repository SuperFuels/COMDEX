import React, { useMemo } from "react";
import * as THREE from "three";
import { useThree } from "@react-three/fiber";

interface SpatialEngineProps {
  showGrid?: boolean;
  showPolar?: boolean;
  showNested?: boolean;
  gridSize?: number;
  ringCount?: number;
  nestedLevels?: number;
}

export const SpatialEngine: React.FC<SpatialEngineProps> = ({
  showGrid = true,
  showPolar = false,
  showNested = false,
  gridSize = 100,
  ringCount = 6,
  nestedLevels = 3,
}) => {
  const { scene } = useThree();

  // 🧱 Grid Layout (Cartesian)
  const gridHelper = useMemo(() => {
    return new THREE.GridHelper(gridSize, gridSize / 2, 0x888888, 0x444444);
  }, [gridSize]);

  // 🌀 Polar Layout
  const polarGroup = useMemo(() => {
    const group = new THREE.Group();
    const segments = 64;
    for (let r = 1; r <= ringCount; r++) {
      const curve = new THREE.EllipseCurve(
        0,
        0,
        r * 2,
        r * 2,
        0,
        2 * Math.PI,
        false,
        0
      );
      const points = curve.getPoints(segments);
      const geometry = new THREE.BufferGeometry().setFromPoints(
        points.map((p) => new THREE.Vector3(p.x, 0, p.y))
      );
      const material = new THREE.LineBasicMaterial({ color: 0x444488 });
      const ellipse = new THREE.LineLoop(geometry, material);
      group.add(ellipse);
    }
    return group;
  }, [ringCount]);

  // 🧬 Nested Axes View (3D layers)
  const nestedAxes = useMemo(() => {
    const group = new THREE.Group();
    for (let i = 1; i <= nestedLevels; i++) {
      const axes = new THREE.AxesHelper(i * 2);
      axes.position.y = i * 0.5;
      group.add(axes);
    }
    return group;
  }, [nestedLevels]);

  return (
    <>
      {showGrid && <primitive object={gridHelper} />}
      {showPolar && <primitive object={polarGroup} />}
      {showNested && <primitive object={nestedAxes} />}
    </>
  );
};