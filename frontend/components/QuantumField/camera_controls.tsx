// frontend/components/QuantumField/camera_controls.tsx

import { useThree, useFrame } from "@react-three/fiber";
import { useEffect, useRef } from "react";

/**
 * 🎥 CameraControls – plain OrbitControls, no auto-rotate / auto-recenter.
 */
export const CameraControls = () => {
  const { camera, gl } = useThree();
  const controlsRef = useRef<any>(null);

  useEffect(() => {
    const { OrbitControls } = require("three/examples/jsm/controls/OrbitControls");

    const controls = new OrbitControls(camera, gl.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;
    controls.rotateSpeed = 0.3;
    controls.zoomSpeed = 0.5;
    controls.panSpeed = 0.4;
    controls.maxDistance = 100;
    controls.minDistance = 1;
    controls.target.set(0, 0, 0); // only set once
    controls.update();

    controlsRef.current = controls;

    return () => {
      controls.dispose();
      controlsRef.current = null;
    };
  }, [camera, gl]);

  // Just let OrbitControls handle damping; no custom orbit / lookAt
  useFrame(() => {
    if (controlsRef.current) {
      controlsRef.current.update();
    }
  });

  return null;
};