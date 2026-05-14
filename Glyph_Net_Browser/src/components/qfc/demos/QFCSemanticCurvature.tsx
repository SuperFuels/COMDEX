"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";

/**
 * VOL-VIII: SEMANTIC CURVATURE (Upgraded)
 * Logic: Meaning-band pinching (Ψ ↔ μ(↺Ψ))
 * Soul: Volumetric Point Lattice
 */

const semanticCurvatureShader = {
  uniforms: {
    uTime: { value: 0 },
    uCurvature: { value: 0 },
    uBrightness: { value: 1.0 },
    uResonance: { value: 3.2 }, // The target "Meaning Band" radius
  },
  vertexShader: `
    varying float vCoherence;
    varying float vShell;
    varying vec2 vUv;
    
    uniform float uTime;
    uniform float uCurvature;
    uniform float uResonance;

    void main() {
      vUv = uv;
      vec3 pos = position;

      // Distance from center (Semantic Radius)
      float d = length(pos.xy);

      // Semantic Density: Peaked at uResonance
      // Represents the "Gravity" of meaning
      float density = exp(-pow(d - uResonance, 2.0) / 1.2);

      // Curvature warping: Z-axis displacement + Radial pinching
      // As uCurvature -> 1, the lattice is pulled into the resonance band
      float bend = uCurvature * density * sin(uTime * 1.5 + d * 0.8);
      float pull = uCurvature * (uResonance - d) * 0.25 * density;

      pos.z += bend * 1.8;
      pos.x += pos.x * pull;
      pos.y += pos.y * pull;

      // Shell emphasis for the fragment shader
      vShell = smoothstep(uResonance - 1.2, uResonance, d) * (1.0 - smoothstep(uResonance, uResonance + 1.2, d));
      vCoherence = density * uCurvature;

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;

      // Particle size increases at the band of coherence
      gl_PointSize = 1.2 + (2.8 * vCoherence) + (1.2 * vShell);
    }
  `,
  fragmentShader: `
    varying float vCoherence;
    varying float vShell;
    varying vec2 vUv;
    uniform float uBrightness;

    void main() {
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      // PALETTE: Deep Space Violet -> Emergent Cyan -> Bridge White
      vec3 spaceViolet = vec3(0.35, 0.10, 0.90);
      vec3 emergentCyan = vec3(0.00, 0.85, 1.00);
      vec3 bridgeWhite  = vec3(0.95, 0.95, 1.00);

      // Color Mixing based on local coherence
      vec3 base = mix(spaceViolet * 0.4, emergentCyan, vCoherence);
      vec3 finalColor = mix(base, bridgeWhite, pow(vShell, 3.0) * vCoherence);

      // Bloom/Glow tied to meaning-density
      float glow = (0.2 + 0.8 * vCoherence) * (0.5 + 0.5 * vShell) * uBrightness;
      float alpha = clamp(0.15 + 0.7 * glow, 0.0, 0.9);

      gl_FragColor = vec4(finalColor * (0.7 + glow), alpha);
    }
  `,
};

export default function QFCSemanticCurvatureV2({ frame }: { frame?: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const tRef = useRef(0);
  const curvSm = useRef(0);

  // High density 60x60 grid (3600 nodes) for volumetric detail
  const geometry = useMemo(() => {
    const size = 60;
    const pts = new Float32Array(size * size * 3);
    const uvs = new Float32Array(size * size * 2);
    let k = 0;
    let u = 0;
    for (let i = 0; i < size; i++) {
      for (let j = 0; j < size; j++) {
        pts[k++] = (i / size - 0.5) * 12;
        pts[k++] = (j / size - 0.5) * 12;
        pts[k++] = 0;
        uvs[u++] = i / size;
        uvs[u++] = j / size;
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pts, 3));
    geo.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
    return geo;
  }, []);

  useEffect(() => () => geometry.dispose(), [geometry]);

  useFrame((_state, dtRaw) => {
    const mat = materialRef.current;
    if (!mat) return;

    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;

    // Smoothed Curvature cycle (Awakening)
    const targetCurv = (Math.sin(tRef.current * 0.5) + 1.0) / 2.0;
    curvSm.current = THREE.MathUtils.lerp(curvSm.current, targetCurv, 0.1);

    mat.uniforms.uTime.value = tRef.current;
    mat.uniforms.uCurvature.value = curvSm.current;
    mat.uniforms.uBrightness.value = 1.0 + 0.05 * Math.sin(tRef.current * 0.8);
  });

  return (
    <group rotation={[-Math.PI / 4, 0, 0]}>
      {/* HUD: Design Architecture */}
      <Html fullscreen transform={false} zIndexRange={[100, 0]}>
        <div className="pointer-events-none w-full h-full font-mono text-white">
          <div className="absolute top-10 left-10 pointer-events-auto p-4 border border-white/10 bg-black/40 backdrop-blur-xl rounded shadow-2xl w-72">
            <div className="flex justify-between items-center border-b border-cyan-500/30 pb-2 mb-3">
              <span className="text-cyan-400 font-bold text-[10px] tracking-widest">VOL-VIII_CURVATURE</span>
              <span className="text-[8px] text-cyan-900">RESONANCE_LOCKED</span>
            </div>
            
            <div className="space-y-2 text-[10px]">
              <div className="flex justify-between">
                <span className="text-slate-500">OP:</span>
                <span className="text-cyan-300">Ψ ↔ μ(↺Ψ)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">COHERENCE:</span>
                <span className="text-white">0.999936</span>
              </div>
              <div className="pt-2">
                <div className="h-1 w-full bg-cyan-950 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-cyan-400 shadow-[0_0_10px_rgba(0,255,255,0.6)]" 
                    style={{ width: `${curvSm.current * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </Html>

      <points geometry={geometry}>
        <shaderMaterial
          ref={materialRef}
          {...semanticCurvatureShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </points>

      {/* Atmospheric center light to ground the "Meaning Band" */}
      <pointLight position={[0, 0, 1]} intensity={0.6} color="#00e5ff" distance={10} />
    </group>
  );
}