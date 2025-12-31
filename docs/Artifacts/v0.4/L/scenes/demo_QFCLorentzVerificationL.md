"use client";

import { useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const lSeriesShader = {
  uniforms: {
    uTime: { value: 0 },
    uBoost: { value: 0.0 }, // Current boost being visualized
    uIsCollapsed: { value: 0.0 }, // 0.0 = Raw, 1.0 = Scaled (L2 Collapse)
    uCeff: { value: 0.7071 },
  },
  vertexShader: `
    varying float vIntensity;
    uniform float uTime;
    uniform float uBoost;
    uniform float uIsCollapsed;
    uniform float uCeff;

    void main() {
      // TUCVP L-Series Parameters
      float gamma = 1.0 / sqrt(1.0 - pow(uBoost / uCeff, 2.0));
      
      // Coordinate Transformation
      float t = uTime;
      float t_scaled = mix(t, t * gamma, uIsCollapsed);
      
      // Soliton Dynamics: Initial center -70, drifting right
      float x_lab = position.x;
      float v_sol = 0.3; // Effective soliton velocity
      
      // Coordinate Shear: x' = gamma * (x - v*t)
      float x_boosted = gamma * (x_lab - (uBoost * t));
      float x_final = mix(x_boosted, x_boosted / gamma, uIsCollapsed);
      
      // Gaussian Pulse: 55 * exp(-0.06 * (x - x_center)^2)
      // We simulate the reflection at x = -20
      float x_target = -70.0 + (v_sol * t_scaled);
      if (x_target > -20.0) x_target = -20.0 - (x_target + 20.0); // Simple reflection
      
      float u = 55.0 * exp(-0.06 * pow(x_final - x_target, 2.0));
      
      vIntensity = u / 55.0; // Normalized for display
      
      vec3 pos = position;
      pos.z += u * 0.1; // Extrude the pulse
      
      gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    void main() {
      vec3 colorLab = vec3(0.4, 0.6, 1.0); // Lab Blue
      vec3 colorBoost = vec3(1.0, 0.4, 0.2); // Boost Orange
      
      gl_FragColor = vec4(mix(colorLab, colorBoost, vIntensity), vIntensity + 0.1);
    }
  `
};

export default function QFCLorentzVerificationL() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const materialRefs = useRef<THREE.ShaderMaterial[]>([]);
  
  const boosts = [0.0, 0.1, 0.2, 0.3, 0.4];
  const grid = useMemo(() => new THREE.PlaneGeometry(100, 2, 200, 1), []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime() % 10;
    materialRefs.current.forEach((mat, i) => {
      if (mat) {
        mat.uniforms.uTime.value = t;
        mat.uniforms.uIsCollapsed.value = isCollapsed ? 1.0 : 0.0;
      }
    });
  });

  return (
    <div className="w-full h-full bg-[#050507] relative flex flex-col items-center justify-center font-mono">
      {/* L-Series Verification Header */}
      <div className="absolute top-8 left-8 z-10 p-4 border border-orange-900/40 bg-black/90 backdrop-blur-md">
        <p className="text-orange-500 font-bold border-b border-orange-900/50 pb-1 mb-2">L_LOCK_v0.4_20251230T202443Z_L</p>
        <div className="text-[10px] space-y-1 text-gray-400">
          <p>L2_COLLAPSE_SIGMA: 1.740e-02 [PASS]</p>
          <p>L3_SCATTERING_R: 1.000 (REFLECTION)</p>
          <p>DELTA_P (L1c): -2.868e-03</p>
        </div>
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="mt-4 px-3 py-1 bg-orange-600 text-white text-[9px] hover:bg-orange-500 transition-colors uppercase"
        >
          Toggle Scaling Collapse
        </button>
      </div>

      {boosts.map((b, i) => (
        <mesh key={i} geometry={grid} position={[0, (i - 2) * 2, 0]}>
          <shaderMaterial 
            ref={el => materialRefs.current[i] = el!} 
            {...lSeriesShader} 
            uniforms={{...lSeriesShader.uniforms, uBoost: { value: b * 0.7071 }}}
            transparent 
          />
        </mesh>
      ))}

      {/* Static Barrier at x = -20 */}
      <div className="absolute left-[30%] w-1 h-32 bg-white/10 border-l border-white/20">
        <span className="absolute -top-6 text-[8px] text-gray-500 transform -translate-x-1/2">BARRIER_X_20</span>
      </div>
    </div>
  );
}