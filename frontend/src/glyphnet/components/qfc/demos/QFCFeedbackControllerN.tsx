"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

const nSeriesShader = {
  uniforms: {
    uTime: { value: 0 },
    uMode: { value: 0 },
    uNoiseSigma: { value: 0.0 },
    uFidelity: { value: 1.0 },
  },
  vertexShader: `
    varying float vIntensity;
    varying vec2 vUv;
    varying float vDist;
    uniform float uTime;
    uniform float uMode;
    uniform float uNoiseSigma;

    float rand(vec2 co){
      return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
    }

    void main() {
      vUv = uv;
      vec3 pos = position;

      // Base Wave (u field) logic from N-Series
      float wave = sin(pos.x * 0.2 + uTime * 3.0) * cos(pos.y * 0.2 + uTime * 2.0);
      
      // Mode 1: Noise Injection (N6/N7)
      if (uMode == 1.0) {
        float noise = (rand(pos.xy + uTime) - 0.5) * uNoiseSigma * 15.0;
        wave += noise;
      }

      // Mode 4: Runaway / Backreaction (N9)
      if (uMode == 4.0) {
        wave *= exp(sin(uTime * 0.5) * 1.5);
        pos.z += sin(pos.x * 0.5) * 4.0;
      }

      pos.z += wave * 2.5;
      vIntensity = wave;
      vDist = length(pos.xy);

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;

      // Dynamic point sizing like the Wormhole
      gl_PointSize = 1.8 + (abs(wave) * 4.0);
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying vec2 vUv;
    varying float vDist;
    uniform float uMode;
    uniform float uFidelity;

    void main() {
      // WORMHOLE PALETTE GUIDE:
      vec3 topColor = vec3(0.0, 0.85, 1.0);    // Electric Cyan
      vec3 bottomColor = vec3(0.4, 0.15, 1.0); // Deep Purple
      vec3 bridgeColor = vec3(0.85, 0.85, 1.0); // White-Blue Glow

      vec3 color;
      float alpha = 0.6;

      if (uMode == 2.0) { // Echo Recovery (N5) - Split Logic
        if (vUv.x < 0.5) {
          color = mix(vec3(0.1), bottomColor, abs(vIntensity)); 
        } else {
          color = mix(topColor, bridgeColor, vIntensity);
        }
      } else if (uMode == 3.0) { // Thermal Rephase (N15)
        vec3 heat = vec3(1.0, 0.3, 0.2);
        color = mix(heat, topColor, uFidelity) * abs(vIntensity);
      } else if (uMode == 4.0) { // Runaway
        color = mix(bottomColor, vec3(1.0, 0.1, 0.1), abs(vIntensity));
      } else { // Standard Mode
        color = mix(bottomColor, topColor, vUv.y);
        color = mix(color, bridgeColor, pow(abs(vIntensity), 3.0));
      }

      // Circular point rendering from Wormhole
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      gl_FragColor = vec4(color, alpha + (abs(vIntensity) * 0.4));
    }
  `
};

type ModeKey = "STABLE" | "NOISE" | "ECHO" | "REPHASE" | "RUNAWAY";

export default function QFCWormholeStyledController() {
  const [mode, setMode] = useState<ModeKey>("STABLE");
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const tRef = useRef(0);

  const modes = useMemo(() => ({
    STABLE: { id: 0, sigma: 0.0, fidelity: 1.0, label: "N20 Unified Equilibrium" },
    NOISE: { id: 1, sigma: 0.0631, fidelity: 0.9, label: "N6 Noise Robustness" },
    ECHO: { id: 2, sigma: 0.0, fidelity: 1.0, label: "N5 Echo Recovery" },
    REPHASE: { id: 3, sigma: 0.0, fidelity: 0.816, label: "N15 Thermal Rephase" },
    RUNAWAY: { id: 4, sigma: 0.5, fidelity: 0.1, label: "N9 Backreaction Runaway" }
  }), []);

  // Geometry: Using a high-density plane for points
  const geometry = useMemo(() => new THREE.PlaneGeometry(60, 60, 160, 160), []);
  useEffect(() => () => geometry.dispose(), [geometry]);

  useFrame((_state, dtRaw) => {
    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;

    if (materialRef.current) {
      const mat = materialRef.current;
      const current = modes[mode];
      mat.uniforms.uTime.value = tRef.current;
      mat.uniforms.uMode.value = current.id;
      mat.uniforms.uNoiseSigma.value = current.sigma;
      mat.uniforms.uFidelity.value = current.fidelity;
    }
  });

  return (
    <group>
      {/* HUD: Retaining the Cyan-Grid styling you love */}
      <Html fullscreen transform={false} zIndexRange={[100, 0]}>
        <div className="w-full h-full pointer-events-none font-mono text-white">
          <div className="absolute top-6 left-6 pointer-events-auto p-5 border border-cyan-500/30 bg-black/80 backdrop-blur-md w-80 shadow-[0_0_15px_rgba(0,180,255,0.2)]">
            <div className="flex justify-between items-center border-b border-cyan-500/30 pb-2 mb-4">
              <span className="text-cyan-400 font-bold text-xs tracking-[0.2em]">N_CORE_V.WORM</span>
              <span className="text-[9px] text-cyan-800">STABLE_FLOW_2026</span>
            </div>

            <div className="space-y-2 text-[10px]">
              <div className="flex justify-between">
                <span className="text-gray-500">SYSTEM_STATE:</span>
                <span className="text-cyan-300 uppercase">{mode}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">COHERENCE:</span>
                <span className="text-white">{(modes[mode].fidelity * 100).toFixed(1)}%</span>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-2">
              {(Object.keys(modes) as ModeKey[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`py-2 text-[9px] border transition-all ${
                    mode === m 
                      ? 'bg-cyan-500/20 border-cyan-400 text-white shadow-[0_0_10px_rgba(0,255,255,0.3)]' 
                      : 'border-cyan-900/40 text-cyan-900 hover:border-cyan-600'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Html>

      {/* Visual Scene: Point Cloud with Additive Blending */}
      <points geometry={geometry} rotation={[-Math.PI / 2.5, 0, 0]} position={[0, -2, 0]}>
        <shaderMaterial
          ref={materialRef}
          {...nSeriesShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </points>

      <ambientLight intensity={0.5} />
      <pointLight position={[0, 5, 5]} intensity={1} color="#00d2ff" />
    </group>
  );
}