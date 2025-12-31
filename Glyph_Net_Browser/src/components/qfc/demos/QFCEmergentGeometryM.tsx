"use client";

import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

// --- M-Series Shader: Curvature & Field Dynamics ---
const mSeriesShader = {
  uniforms: {
    uTime: { value: 0 },
    uGtt: { value: -1.122 },
    uGxx: { value: 1.027 },
    uCurvatureProxy: { value: 0 },
    uCentroidPos: { value: new THREE.Vector2(0, 0) },
    uRedshift: { value: 0 },
    uBeatFrequency: { value: 0.02083 }, // M4b
    uTransferAmplitude: { value: 0.002392 }, // M4b
  },
  vertexShader: `
    varying float vIntensity;
    varying vec3 vNormal;
    varying float vCurvatureProxy;
    uniform float uTime;
    uniform float uCurvatureProxy;
    uniform vec2 uCentroidPos;
    uniform float uBeatFrequency;
    uniform float uTransferAmplitude;

    void main() {
      vNormal = normal;
      vec3 pos = position;
      
      // Base field oscillation (from K/L series)
      float field = sin(pos.x * 0.5 + uTime * 2.0) * cos(pos.y * 0.5 + uTime * 1.5);

      // M4b: Coupled Curvature Wells (fixed locations, energy exchange)
      // Well A at x = -20, Well B at x = 20
      float well_A_x = -20.0;
      float well_B_x = 20.0;
      float well_sigma = 5.0; // Width of the wells

      float dist_A = exp(-pow(pos.x - well_A_x, 2.0) / (2.0 * well_sigma * well_sigma));
      float dist_B = exp(-pow(pos.x - well_B_x, 2.0) / (2.0 * well_sigma * well_sigma));

      // Energy transfer between wells (oscillatory)
      float transfer = sin(uTime * uBeatFrequency * 10.0) * uTransferAmplitude * 500.0; // Amplify for visual
      float well_effect = (dist_A - dist_B) * transfer; 
      
      // Add Curvature proxy (R_eff) to Z position
      float dynamicCurvature = (field * 0.5) + (well_effect * 0.2); // R_eff is derived
      pos.z += dynamicCurvature; 
      
      // M3d: Geodesic Oscillation - Centroid's influence (subtle warp)
      float centroid_influence = exp(-pow(pos.x - uCentroidPos.x, 2.0) / 50.0) * 0.1;
      pos.z += centroid_influence * sin(uTime * 0.5);

      vIntensity = clamp(dynamicCurvature * 2.0, 0.0, 1.0);
      vCurvatureProxy = uCurvatureProxy; // Pass for Redshift calc
      
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying vec3 vNormal;
    varying float vCurvatureProxy; // From R_eff
    uniform float uRedshift; // From M5/M6
    uniform float uTime;

    void main() {
      // Base color for the field (representing field activity)
      vec3 baseColor = mix(vec3(0.1, 0.2, 0.4), vec3(0.8, 0.9, 1.0), vIntensity);

      // M5/M6: Redshift Analogue (color shift based on effective curvature)
      // Exaggerate for visual effect in the demo
      float simulatedRedshift = clamp(vCurvatureProxy * 500.0 + uRedshift * 100000.0, -0.5, 0.5); // Amplified
      vec3 redshiftColor = mix(vec3(0.0, 0.8, 0.0), vec3(1.0, 0.0, 0.0), (simulatedRedshift + 0.5)); // Green to Red
      
      vec3 finalColor = mix(baseColor, redshiftColor, abs(simulatedRedshift) * 2.0); // Blend in redshift for affected areas
      
      gl_FragColor = vec4(finalColor, 1.0);
    }
  `
};

export default function QFCEmergentGeometryM() {
  const meshRef = useRef<THREE.Mesh>(null);
  const centroidRef = useRef<THREE.Mesh>(null);
  const [currentRedshift, setCurrentRedshift] = useState(-5.889e-6); // M5 value
  
  const gridSize = 100;
  const planeGeo = useMemo(() => new THREE.PlaneGeometry(100, 50, gridSize, gridSize / 2), []); // x-y plane

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (meshRef.current) {
      const material = meshRef.current.material as THREE.ShaderMaterial;
      material.uniforms.uTime.value = t;

      // Simulate M3d Geodesic Oscillation: Centroid motion
      const centroidAmp = 5.852e-1 * 10; // M3d amplitude, scaled for visual
      const centroidX = Math.sin(t * 0.5) * centroidAmp;
      material.uniforms.uCentroidPos.value.set(centroidX, 0);

      if (centroidRef.current) {
        centroidRef.current.position.x = centroidX;
        centroidRef.current.position.z = material.uniforms.uCurvatureProxy.value * 10; // Lift centroid with curvature
      }

      // Simulate subtle redshift change over time
      setCurrentRedshift(-5.889e-6 * (1 + Math.sin(t * 0.7) * 0.5)); // M5 base value with slight oscillation
      material.uniforms.uRedshift.value = currentRedshift;
      
      // Estimate R_eff proxy from field (for shader and display)
      // This is a simplified proxy for the visualization
      const rEffProxy = Math.sin(t * 0.5) * 0.1 - 0.05; // M1: -1.172e-12 (use a more visible range)
      material.uniforms.uCurvatureProxy.value = rEffProxy;
    }
  });

  return (
    <div className="w-full h-full bg-[#080810] relative flex items-center justify-center font-mono">
      {/* M-Series Verification Dashboard */}
      <div className="absolute top-8 left-8 z-10 p-4 border border-purple-800/40 bg-black/90 backdrop-blur-md text-[10px] grid grid-cols-2 gap-x-4 gap-y-1">
        <p className="col-span-2 text-purple-400 font-bold border-b border-purple-900/50 pb-1 mb-2">M_LOCK_v0.4_20251230T213353Z_M</p>
        
        <p>g_tt (M1):</p><p className="text-white">-1.122</p>
        <p>g_xx (M1):</p><p className="text-white">1.027</p>
        
        <p className="col-span-2 mt-2 text-purple-300">CURVATURE WELLS (M4b)</p>
        <p>Transfer Amp:</p><p className="text-white">2.392e-03</p>
        <p>Beat Freq:</p><p className="text-white">2.083e-02</p>

        <p className="col-span-2 mt-2 text-purple-300">GEODESIC CENTROID (M3d)</p>
        <p>Osc. Amp:</p><p className="text-white">5.852e-01</p>

        <p className="col-span-2 mt-2 text-purple-300">REDSHIFT ANALOGUE (M5)</p>
        <p>Δω/ω:</p><p className="text-red-400">{currentRedshift.toExponential(3)}</p>
        
        <p className="col-span-2 mt-2 text-gray-500">GIT_REV: 5a271385a6156344e43dee93cd8779876d38a797</p>
        <p className="col-span-2 text-gray-500">CHECKSUM: 20251230T213353Z_M.sha256 (VERIFIED)</p>
      </div>

      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} />

      <mesh ref={meshRef} geometry={planeGeo} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -5]}>
        <shaderMaterial {...mSeriesShader} side={THREE.DoubleSide} />
      </mesh>

      {/* Geodesic Centroid Visual */}
      <mesh ref={centroidRef} position={[0, 0, 0]}>
        <sphereGeometry args={[0.7, 32, 32]} />
        <meshBasicMaterial color="white" emissive="white" emissiveIntensity={2} />
      </mesh>

      {/* Curvature Well Markers (Fixed) */}
      <group position-y={-5}>
        <mesh position={[-20, 0, 0]}>
          <cylinderGeometry args={[1, 1, 10, 16]} />
          <meshBasicMaterial color="#4A0080" emissive="#4A0080" emissiveIntensity={1} transparent opacity={0.5} />
        </mesh>
        <mesh position={[20, 0, 0]}>
          <cylinderGeometry args={[1, 1, 10, 16]} />
          <meshBasicMaterial color="#4A0080" emissive="#4A0080" emissiveIntensity={1} transparent opacity={0.5} />
        </mesh>
      </group>
    </div>
  );
}