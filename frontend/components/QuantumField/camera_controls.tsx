// File: frontend/components/QuantumField/camera_controls.tsx

import { useThree, useFrame } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import * as THREE from "three";

/**
 * 🎥 CameraControls provides rotation, zoom, gaze tracking, and observer anchoring for the QFC.
 */
export const CameraControls = () => {
  const { camera, gl } = useThree();
  const observerRef = useRef<THREE.Object3D>(new THREE.Object3D());

  // ⏱ Animate rotation or zoom if needed
  useFrame(() => {
    // Example: Slowly orbit around Z axis
    observerRef.current.rotation.y += 0.001;
    camera.lookAt(observerRef.current.position);
  });

  // 🧲 Attach orbit controls manually if needed
  useEffect(() => {
    const controls = new (require("three/examples/jsm/controls/OrbitControls").OrbitControls)(
      camera,
      gl.domElement
    );
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;
    controls.rotateSpeed = 0.3;
    controls.zoomSpeed = 0.5;
    controls.panSpeed = 0.4;
    controls.maxDistance = 100;
    controls.minDistance = 1;
    controls.target.set(0, 0, 0);
    controls.update();

    return () => controls.dispose();
  }, [camera, gl]);

  return <primitive object={observerRef.current} />;
};