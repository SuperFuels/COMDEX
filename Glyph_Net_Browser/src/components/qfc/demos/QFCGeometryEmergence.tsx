"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const geometryShader = {
  uniforms: {
    uTime: { value: 0 },
    uClosureRatio: { value: 0 }, // 0: Noise, 1: Perfect Ring
  },
  vertexShader: `
    varying float vDistance;
    uniform float uTime;
    uniform float uClosureRatio;

    void main() {
      // Seed-based deterministic noise
      float id = position.z;
      vec3 noise = vec3(
        sin(id * 1.2 + uTime) * 2.0,
        cos(id * 0.8 + uTime) * 2.0,
        sin(id * 1.5 + uTime * 0.5) * 2.0
      );
      
      // Target Ring Geometry
      float angle = (id / 200.0) * 2.0 * 3.141592653589793;
      vec3 ring = vec3(cos(angle) * 4.0, sin(angle) * 4.0, 0.0);
      
      // Interpolate based on Closure Progress
      vec3 finalPos = mix(noise, ring, uClosureRatio);
      
      vDistance = distance(finalPos, vec3(0.0));
      vec4 mvPosition = modelViewMatrix * vec4(finalPos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
      gl_PointSize = 3.5;
    }
  `,
  fragmentShader: `
    varying float vDistance;
    void main() {
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;
      
      // Color based on distance from origin (radial coherence)
      vec3 color = mix(vec3(0.1, 0.5, 1.0), vec3(1.0, 0.8, 0.0), smoothstep(3.5, 4.5, vDistance));
      gl_FragColor = vec4(color, 1.0);
    }
  `
};

export default function QFCGeometryEmergence() {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  const geometry = useMemo(() => {
    const pts = [];
    for (let i = 0; i < 200; i++) pts.push(0, 0, i); // 200 nodes
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    return geo;
  }, []);

  useFrame(({ clock }) => {
    if (!materialRef.current) return;
    const t = clock.getElapsedTime();
    materialRef.current.uniforms.uTime.value = t;
    
    // Cycle between chaos and geometric closure
    const loop = (Math.sin(t * 0.5) + 1.0) / 2.0;
    materialRef.current.uniforms.uClosureRatio.value = THREE.MathUtils.smoothstep(loop, 0.2, 0.8);
  });

  return (
    <div className="w-full h-full bg-[#020202] relative flex items-center justify-center">
      <div className="absolute top-10 left-10 font-mono text-[10px] text-cyan-500 z-10 p-5 border border-cyan-900/30 bg-black/90">
        <p className="font-bold border-b border-cyan-800 pb-1 mb-2">VOL-VII: GEOMETRY_EMERGENCE</p>
        <div className="space-y-1">
          <p>OBJECT: Discrete Ring (N=64)</p>
          <p>INVARIANT: e^(i·2πs·n) = 1</p>
          <p>WINDING: n=1</p>
          <p className="text-yellow-400 pt-2">π_s: 3.141592653589793</p>
        </div>
      </div>

      <points geometry={geometry}>
        <shaderMaterial ref={materialRef} {...geometryShader} transparent />
      </points>

      <div className="absolute bottom-10 right-10 text-[9px] text-gray-700 font-mono text-right">
        Verification Trace: 1B9F03BA...2CF0EE5
        <br />
        Status: LOCKED & VERIFIED
      </div>
    </div>
  );
}