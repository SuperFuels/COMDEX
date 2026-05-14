"use client";

import React, { useMemo, useRef, useState, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import { Html as DreiHtml } from "@react-three/drei";
import * as THREE from "three";

/**
 * VOL-F: VACUUM LANDSCAPE / SCALE FACTOR RESONANCE
 * Logic: Scale Factor a(t) oscillation + Curvature peaking
 * Soul: Fresnel Shell + Volumetric Point Lattice
 */

const PINNED_METRICS = {
  a_min: 0.88466,
  lambda_eq: 0.99999997,
  lambda_spread: 2.23e-15,
  anti_corr: 0.947,
};

const VacuumShader = {
  uniforms: {
    uTime: { value: 0 },
    uScaleFactor: { value: 1.0 },
    uCurvatureIntensity: { value: 0.0 },
    uBrightness: { value: 1.0 },
  },
  vertexShader: `
    varying float vIntensity;
    varying vec3 vNormal;
    varying vec3 vViewPosition;

    uniform float uScaleFactor;
    uniform float uCurvatureIntensity;
    uniform float uTime;

    void main() {
      // Scale position based on a(t)
      vec3 pos = position * uScaleFactor;

      // Spacetime warping: Curvature "pinches" the vertices inward
      float pinch = uCurvatureIntensity * exp(-length(pos) * 0.5);
      pos *= (1.0 - pinch * 0.15);

      // Micro-fluctuations (Vacuum noise)
      pos += sin(pos * 6.0 + uTime * 2.0) * 0.008;

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      vViewPosition = -mvPosition.xyz;
      vNormal = normalize(normalMatrix * normal);
      
      // Pass intensity for fragment logic
      vIntensity = uCurvatureIntensity;

      gl_Position = projectionMatrix * mvPosition;
      gl_PointSize = 2.0 + (uCurvatureIntensity * 3.0);
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    uniform float uBrightness;

    void main() {
      // Fresnel effect for the "Bridge" boundary
      vec3 normal = normalize(vNormal);
      vec3 viewDir = normalize(vViewPosition);
      float fresnel = pow(1.0 - dot(normal, viewDir), 3.0);

      // Palette: Deep Violet -> Electric Cyan -> Singularity White
      vec3 violet = vec3(0.3, 0.1, 0.8);
      vec3 cyan   = vec3(0.0, 0.9, 1.0);
      vec3 white  = vec3(0.95, 0.95, 1.0);

      // Color shifts based on current Curvature (a_min proximity)
      vec3 base = mix(violet * 0.5, cyan, vIntensity);
      vec3 finalColor = mix(base, white, pow(vIntensity, 3.0) + fresnel * 0.5);

      float alpha = clamp(0.2 + (vIntensity * 0.6) + (fresnel * 0.2), 0.0, 0.9);
      
      gl_FragColor = vec4(finalColor * uBrightness, alpha);
    }
  `,
};

export default function QFCVacuumLandscapeF({ frame }: { frame?: any }) {
  const matRef = useRef<THREE.ShaderMaterial>(null);
  const tRef = useRef(0);
  const [hud, setHud] = useState({ e: 0, s: 0, a: PINNED_METRICS.a_min, sync: 0 });

  // Generate a high-density point cloud shell
  const geometry = useMemo(() => new THREE.IcosahedronGeometry(5, 6), []);
  useEffect(() => () => geometry.dispose(), [geometry]);

  useFrame((_state, dtRaw) => {
    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;
    const t = tRef.current;

    // Scale Factor a(t) oscillation around a_min
    const a_min = PINNED_METRICS.a_min;
    const a_t = a_min + (1.0 - a_min) * (0.5 + 0.5 * Math.cos(t * 0.8));
    
    // Curvature logic: Intensity peaks when a(t) is at its floor
    const curvature = Math.pow(1.0 - (a_t - a_min) / (1.0 - a_min), 3.0);

    const mat = matRef.current;
    if (mat) {
      mat.uniforms.uTime.value = t;
      mat.uniforms.uScaleFactor.value = a_t;
      mat.uniforms.uCurvatureIntensity.value = curvature;
      mat.uniforms.uBrightness.value = 1.0 + 0.05 * Math.sin(t * 0.6);
    }

    // HUD Update (Throttle)
    if (t % 0.15 < 0.02) {
      setHud({
        e: 0.5 + 0.5 * Math.sin(t * 0.8),
        s: (0.5 - 0.5 * Math.sin(t * 0.8)) * PINNED_METRICS.anti_corr,
        a: a_t,
        sync: Math.min(1, t / 20)
      });
    }
  });

  return (
    <group>
      <DreiHtml fullscreen transform={false} zIndexRange={[100, 0]}>
        <div className="pointer-events-none w-full h-full font-mono text-white">
          {/* Top Left: Deterministic Metrics */}
          <div className="absolute top-10 left-10 p-5 bg-black/60 backdrop-blur-xl border border-white/10 rounded w-80">
            <div className="text-cyan-400 text-[10px] tracking-[0.3em] font-bold border-b border-white/10 pb-2 mb-4">
              VACUUM_LANDSCAPE_F
            </div>
            <div className="space-y-3 text-[10px]">
              <div className="flex justify-between text-slate-400">
                <span>SCALE_FACTOR a(t):</span>
                <span className="text-white">{hud.a.toFixed(5)}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>NECK_FLOOR (a_min):</span>
                <span className="text-cyan-400">{PINNED_METRICS.a_min}</span>
              </div>
              <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-cyan-400" 
                  style={{ width: `${((1 - (hud.a - 0.88466) / (1 - 0.88466))) * 100}%` }} 
                />
              </div>
            </div>
          </div>

          {/* Bottom Right: Anti-Correlation Gages */}
          <div className="absolute bottom-10 right-10 p-5 bg-black/60 backdrop-blur-xl border border-white/10 rounded w-72">
             <div className="text-[9px] text-slate-500 mb-4 tracking-widest uppercase italic">Entropy/Energy Feedback</div>
             <div className="space-y-4">
                <div className="space-y-1">
                  <div className="flex justify-between text-[9px]"><span>ENERGY_FLUX (E)</span><span>{hud.e.toFixed(3)}</span></div>
                  <div className="h-0.5 w-full bg-white/10"><div className="h-full bg-orange-400" style={{ width: `${hud.e * 100}%` }} /></div>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-[9px]"><span>ENTROPY_FLUX (S)</span><span>{hud.s.toFixed(3)}</span></div>
                  <div className="h-0.5 w-full bg-white/10"><div className="h-full bg-cyan-400" style={{ width: `${hud.s * 100}%` }} /></div>
                </div>
             </div>
          </div>
        </div>
      </DreiHtml>

      {/* Main Spacetime Lattice (Points) */}
      <points geometry={geometry}>
        <shaderMaterial
          ref={matRef}
          {...VacuumShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </points>

      {/* Secondary Internal Mesh (Wireframe for structure) */}
      <mesh geometry={geometry}>
        <shaderMaterial
          {...VacuumShader}
          uniforms={matRef.current?.uniforms || VacuumShader.uniforms}
          wireframe
          transparent
          opacity={0.15}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Singularity Pulse Light */}
      <pointLight position={[0, 0, 0]} intensity={1.5} color="#00f2ff" distance={15} />
      <ambientLight intensity={0.2} />
    </group>
  );
}