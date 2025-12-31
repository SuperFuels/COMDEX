"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const kSeriesShader = {
  uniforms: {
    uTime: { value: 0 },
    uCeff: { value: 0.7071 },
    uSync: { value: 0.9999 },
  },
  vertexShader: `
    varying float vIntensity;
    varying vec2 vUv;
    uniform float uTime;
    uniform float uCeff;

    void main() {
      vUv = uv;
      float x = position.x;
      float t_coord = position.y; // Using Y as the Time axis for the Spacetime Map
      
      // K3b: Gaussian Soliton Profile: u = exp(-0.02 * x^2)
      // Drifting with v = -0.0028
      float drift = -0.0028 * uTime * 20.0;
      float sol_x = x - drift;
      float u = exp(-0.02 * pow(sol_x, 2.0));
      
      // K1: Causal Mesh Constraint
      // Check if current X is within the Causal Cone of the origin
      float cone = uCeff * t_coord;
      bool inCone = abs(x) <= cone;
      
      vIntensity = u * (inCone ? 1.0 : 0.3);
      
      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying vec2 vUv;
    void main() {
      // Background "Mesh" lines
      float mesh = step(0.95, fract(vUv.x * 20.0)) + step(0.95, fract(vUv.y * 20.0));
      
      vec3 baseColor = vec3(0.05, 0.1, 0.2); // Deep Space
      vec3 solColor = vec3(0.0, 1.0, 0.8);  // Soliton Cyan
      
      vec3 finalColor = mix(baseColor, solColor, vIntensity);
      finalColor += mesh * 0.1; // Add the causal mesh grid
      
      gl_FragColor = vec4(finalColor, 1.0);
    }
  `
};

export default function QFCCausalSpacetimeK() {
  const meshRef = useRef<THREE.Mesh>(null);
  const planeGeo = useMemo(() => new THREE.PlaneGeometry(10, 10, 100, 100), []);

  useFrame(({ clock }) => {
    if (meshRef.current) {
      const material = meshRef.current.material as THREE.ShaderMaterial;
      material.uniforms.uTime.value = clock.getElapsedTime() % 10;
    }
  });

  return (
    <div className="w-full h-full bg-[#020204] relative flex items-center justify-center font-mono">
      {/* K-Series Telemetry Panel */}
      <div className="absolute top-8 left-8 z-10 p-4 border border-cyan-900/40 bg-black/90 text-[10px] backdrop-blur-md">
        <p className="text-cyan-400 font-bold border-b border-cyan-900/50 pb-1 mb-2">K_LOCK_v0.4_20251230T191749Z_K</p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-gray-400">
          <p>R_CAUSAL:</p><p className="text-white">1.0000</p>
          <p>R_SYNC:</p><p className="text-white">0.9999</p>
          <p>C_EFF:</p><p className="text-white">0.7071</p>
          <p>GAUSSIAN_SIGMA:</p><p className="text-white">0.02</p>
        </div>
      </div>

      <mesh ref={meshRef} geometry={planeGeo}>
        <shaderMaterial {...kSeriesShader} />
      </mesh>

      {/* Synchrony Matrix (Overlay) */}
      <div className="absolute bottom-8 right-8 w-32 h-32 border border-cyan-500/30 bg-cyan-500/10 flex items-center justify-center">
        <div className="text-[8px] text-cyan-400 text-center uppercase tracking-tighter">
          K4_SYNC_MATRIX<br/>[VERIFIED]
        </div>
      </div>
    </div>
  );
}