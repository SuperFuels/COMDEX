"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html as DreiHtml } from "@react-three/drei";
import * as THREE from "three";

const h2TemporalShader = {
  uniforms: {
    uTime: { value: 0 },
    uDrift: { value: 9.2014e-5 },
    uAsymmetry: { value: 0.13947 },
  },
  vertexShader: `
    varying float vEntropy;
    uniform float uTime;
    uniform float uDrift;

    void main() {
      vec3 pos = position;
      float t = uTime * 2.0;

      // Dual Field Oscillations (Phi and Psi)
      float phi = sin(0.5 * t + pos.x) * exp(-0.05 * t);
      float psi = cos(0.5 * t + pos.y) * exp(-0.05 * t);

      // The "Total" state interaction
      float total = phi + psi;

      // Temporal Drift: Points "ascend" based on entropy increase
      pos.z += (uTime * uDrift * 500.0) + (total * 0.5);

      vEntropy = abs(total);

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
      gl_PointSize = 2.0;
    }
  `,
  fragmentShader: `
    varying float vEntropy;

    void main() {
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      // Color shifts from field-cyan to entropy-gold
      vec3 color = mix(vec3(0.0, 0.8, 1.0), vec3(1.0, 0.7, 0.0), vEntropy);
      gl_FragColor = vec4(color, 0.7);
    }
  `,
};

export default function QFCEmergentTimeH2() {
  const materialRef = useRef<THREE.ShaderMaterial | null>(null);

  // ✅ dt clamp + stable time (standard)
  const tRef = useRef(0);

  // ✅ clone uniforms once (stable)
  const uniforms = useMemo(
    () => THREE.UniformsUtils.clone(h2TemporalShader.uniforms),
    []
  );

  const geometry = useMemo(() => {
    const pts: number[] = [];
    const size = 60;

    for (let i = 0; i < size; i++) {
      for (let j = 0; j < size; j++) {
        pts.push((i / size - 0.5) * 15, (j / size - 0.5) * 15, 0);
      }
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    return geo;
  }, []);

  useFrame((_state, dtRaw) => {
    const dtc = Math.min(dtRaw, 1 / 30);
    tRef.current += dtc;

    // loop cycle preserved
    uniforms.uTime.value = tRef.current % 20;
  });

  return (
    <group>
      {/* 3D points field */}
      <points geometry={geometry}>
        <shaderMaterial
          ref={materialRef}
          uniforms={uniforms}
          vertexShader={h2TemporalShader.vertexShader}
          fragmentShader={h2TemporalShader.fragmentShader}
          transparent
          depthWrite={false}
          blending={THREE.NormalBlending}
        />
      </points>

      {/* HUD overlay (DOM) - must be Html inside Canvas */}
      <DreiHtml fullscreen transform={false} zIndexRange={[10, 0]}>
        <div className="w-full h-full pointer-events-none font-mono">
          <div className="absolute top-8 left-8 z-10 p-4 border border-yellow-900/40 bg-black/90 text-[10px] pointer-events-auto">
            <p className="text-yellow-500 font-bold border-b border-yellow-900/50 pb-1 mb-2">
              H2_ARROW_OF_TIME_V0_4
            </p>
            <div className="space-y-1 text-gray-400">
              <p>CLASSIFICATION: ⏳ EMERGENT FORWARD</p>
              <p>DRIFT_MEAN: 9.2014e-05</p>
              <p>MI_ASYMMETRY: 0.13948</p>
              <p className="text-white">STATUS: LOCKED (5a271385a)</p>
            </div>
          </div>

          {/* Central Arrow Representation */}
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[1px] h-32 bg-gradient-to-t from-transparent via-yellow-500 to-white opacity-40" />

          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-[9px] text-gray-600 tracking-widest">
            REPRO: python backend/photon_algebra/tests/haev_test_H2_arrow_of_time_emergence.py
          </div>
        </div>
      </DreiHtml>
    </group>
  );
}