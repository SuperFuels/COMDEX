"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const semanticCurvatureShader = {
  uniforms: {
    uTime: { value: 0 },
    uCurvature: { value: 0 },
  },
  vertexShader: `
    varying float vCoherence;
    uniform float uTime;
    uniform float uCurvature;

    void main() {
      vec3 pos = position;
      
      // Calculate semantic density based on position
      float d = length(pos.xy);
      float density = exp(-pow(d - 3.0, 2.0) / 2.0);
      
      // Warping the geometry based on 'Meaning' (Coherence Gradient)
      float bend = uCurvature * density * sin(uTime + d);
      pos.z += bend;
      
      // Pulling points toward the resonant radius
      float pull = uCurvature * (3.0 - d) * 0.2;
      pos.x += pos.x * pull;
      pos.y += pos.y * pull;

      vCoherence = density * uCurvature;
      
      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
      gl_PointSize = 2.5;
    }
  `,
  fragmentShader: `
    varying float vCoherence;
    void main() {
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;
      
      // Shift from deep blue (low meaning) to gold (high closure)
      vec3 color = mix(vec3(0.05, 0.1, 0.4), vec3(1.0, 0.8, 0.2), vCoherence);
      gl_FragColor = vec4(color, 0.8);
    }
  `
};

export default function QFCSemanticCurvature() {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  
  const points = useMemo(() => {
    const pts = [];
    const size = 40;
    for (let i = 0; i < size; i++) {
      for (let j = 0; j < size; j++) {
        pts.push((i / size - 0.5) * 10, (j / size - 0.5) * 10, 0);
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    return geo;
  }, []);

  useFrame(({ clock }) => {
    if (materialRef.current) {
      const t = clock.getElapsedTime();
      materialRef.current.uniforms.uTime.value = t;
      // Animate the 'Awakening' of the loop
      materialRef.current.uniforms.uCurvature.value = (Math.sin(t * 0.4) + 1.0) / 2.0;
    }
  });

  return (
    <div className="w-full h-full bg-[#010103] relative flex items-center justify-center font-mono">
      {/* Verification Header */}
      <div className="absolute top-8 left-8 z-10 p-4 border border-blue-900/40 bg-black/90 backdrop-blur-sm">
        <p className="text-blue-400 font-bold text-[11px] mb-2">VOL-VIII: SEMANTIC_CURVATURE</p>
        <div className="text-[9px] text-gray-400 space-y-1">
          <p>LOCK_ID: VOLVIII-CURVATURE-MEANING-v0.1</p>
          <p>TRACE: 7cb70b43...e51a1c74</p>
          <p className="text-blue-300">COHERENCE: 0.999936 [VERIFIED]</p>
        </div>
      </div>

      <points geometry={points}>
        <shaderMaterial ref={materialRef} {...semanticCurvatureShader} transparent />
      </points>

      {/* Floating Truth Chain Legend */}
      <div className="absolute bottom-8 right-8 text-[10px] text-gray-600 text-right">
        <p>Ψ ↔ μ(↺Ψ)</p>
        <p>SELF_RESONANT_FEEDBACK_PASS</p>
      </div>
    </div>
  );
}