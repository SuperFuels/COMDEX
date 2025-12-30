"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const telemetryAuditShader = {
  uniforms: {
    uTime: { value: 0 },
    uFinalCoherence: { value: 0.9463 },
    uVerified: { value: 1.0 }, // Static 1.0 based on PASS log
  },
  vertexShader: `
    varying float vAlpha;
    varying vec3 vColor;
    uniform float uTime;

    void main() {
      vec3 pos = position;
      
      // Lane logic (0-3 for the 4 event types)
      float lane = floor(pos.y / 2.0);
      
      // Horizontal flow representing JSONL Trace
      pos.x = mod(pos.x + uTime * 2.5, 20.0) - 10.0;
      
      // Vertical feedback oscillation
      float wave = sin(pos.x * 0.5 + uTime * 2.0) * 0.1;
      pos.y += wave;

      // Color mapping to event types
      if (lane == 0.0) vColor = vec3(1.0, 0.8, 0.0); // law_weight
      else if (lane == 1.0) vColor = vec3(0.0, 1.0, 1.0); // wave_step
      else if (lane == 2.0) vColor = vec3(1.0, 0.0, 0.5); // energy
      else vColor = vec3(0.5, 0.0, 1.0); // feedback_apply

      vAlpha = smoothstep(-10.0, -8.0, pos.x) * (1.0 - smoothstep(8.0, 10.0, pos.x));
      
      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
      gl_PointSize = 3.5;
    }
  `,
  fragmentShader: `
    varying float vAlpha;
    varying vec3 vColor;

    void main() {
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;
      gl_FragColor = vec4(vColor, vAlpha);
    }
  `
};

export default function QFCTelemetryAuditV3() {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  
  const points = useMemo(() => {
    const pts = [];
    for (let lane = 0; lane < 4; lane++) {
      for (let i = 0; i < 40; i++) { // 40 steps from log
        pts.push((i / 2) - 10, lane * 2.2 - 3.3, 0);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    return geo;
  }, []);

  useFrame(({ clock }) => {
    if (materialRef.current) {
      materialRef.current.uniforms.uTime.value = clock.getElapsedTime();
    }
  });

  return (
    <div className="w-full h-full bg-[#030305] relative flex flex-col items-center justify-center font-mono">
      {/* Determinism Header */}
      <div className="absolute top-6 left-6 z-10 border border-emerald-500/30 bg-black/80 p-4 text-[10px] text-emerald-400 backdrop-blur-md">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
          <span className="font-bold">VOL5 DETERMINISM: PASS</span>
        </div>
        <p className="text-gray-400">TRACE: 67b3c4c4...b7446218</p>
        <p className="text-gray-400">EVENTS: 160 | STEPS: 40</p>
      </div>

      {/* Metrics Overlay */}
      <div className="absolute top-6 right-6 z-10 text-right text-[10px] space-y-1 text-cyan-300">
        <p>E_FINAL: 0.98018</p>
        <p>C_FINAL: 0.94630</p>
        <p>λ_MEAN: 0.99519</p>
      </div>

      <points geometry={points}>
        <shaderMaterial 
          ref={materialRef} 
          {...telemetryAuditShader} 
          transparent 
          blending={THREE.AdditiveBlending} 
        />
      </points>

      {/* Ground Truth Label */}
      <div className="absolute bottom-6 text-[9px] text-gray-600 tracking-widest uppercase">
        Artifact Trace Replay • Tessaris Symatics Series
      </div>
    </div>
  );
}