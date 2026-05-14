"use client";

import { useMemo, useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const n = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

const finalWormholeShader = {
  uniforms: {
    uTime: { value: 0 },
    uKappa: { value: 0.6 },
    uAlpha: { value: 0.5 },
    uGate01: { value: 1.0 }, // ✅ topology gate (smoothed)
    uBrightness: { value: 1.05 },
  },
  vertexShader: `
    varying float vIntensity;
    varying float vSide;
    uniform float uTime;
    uniform float uKappa;
    uniform float uAlpha;
    uniform float uGate01;

    void main() {
      vec3 pos = position;
      float side = pos.z > 0.0 ? 1.0 : -1.0;
      vSide = side;

      float d = length(pos.xy);

      // Original throat, but gently widened by gate (0.90..1.25)
      float throat = (uKappa + uAlpha * 2.5) / (1.0 + pow(d * 1.5, 2.0));
      throat *= (0.90 + 0.35 * uGate01);

      pos.z -= side * throat * 3.0;

      // Keep original turbulence (no gate here to avoid jitter)
      if (d < 1.2) {
        float wave = sin(d * 8.0 - uTime * 6.0) * cos(pos.x * 2.0);
        pos.z += wave * 0.12 * uAlpha;
      }

      vIntensity = throat;

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;

      gl_PointSize = 1.6 + (throat * 3.0);
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying float vSide;
    uniform float uBrightness;
    uniform float uGate01;

    void main() {
      vec3 topColor = vec3(0.0, 0.85, 1.0);
      vec3 bottomColor = vec3(0.4, 0.15, 1.0);
      vec3 bridgeColor = vec3(0.85, 0.85, 1.0);

      vec3 baseColor = mix(bottomColor, topColor, (vSide + 1.0) / 2.0);
      vec3 finalColor = mix(baseColor, bridgeColor, pow(vIntensity, 4.0));

      // Original glow, with tiny gate lift (smooth, non-bursty)
      float glow = pow(vIntensity, 2.0) * uBrightness;
      glow *= (0.92 + 0.18 * uGate01);

      float alpha = clamp(0.2 + glow, 0.0, 1.0);

      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      gl_FragColor = vec4(finalColor * (0.85 + glow), alpha);
    }
  `,
};

export default function QFCDemoWormhole({ frame }: { frame: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  // ✅ dt clamp + stable time accumulator
  const tRef = useRef(0);

  // ✅ smooth gate so epoch changes don't “step”
  const gateSm = useRef(1);

  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(16, 16, 128, 128);
    const pos = geo.attributes.position.array as Float32Array;
    const count = pos.length / 3;

    const doublePos = new Float32Array(pos.length * 2);
    for (let i = 0; i < count; i++) {
      doublePos[i * 3] = pos[i * 3];
      doublePos[i * 3 + 1] = pos[i * 3 + 1];
      doublePos[i * 3 + 2] = 2.5;

      const offset = count * 3;
      doublePos[offset + i * 3] = pos[i * 3];
      doublePos[offset + i * 3 + 1] = pos[i * 3 + 1];
      doublePos[offset + i * 3 + 2] = -2.5;
    }

    const finalGeo = new THREE.BufferGeometry();
    finalGeo.setAttribute("position", new THREE.BufferAttribute(doublePos, 3));
    return finalGeo;
  }, []);

  // ✅ cleanup geometry on unmount
  useEffect(() => {
    return () => {
      geometry.dispose();
    };
  }, [geometry]);

  useFrame((_state, dtRaw) => {
    const mat = materialRef.current;
    if (!mat) return;

    // ✅ dt clamp pattern
    const dtc = Math.min(dtRaw, 1 / 30);

    // ✅ stable time (FPS-drop safe) — use this instead of clock.getElapsedTime()
    tRef.current += dtc;
    const t = tRef.current;

    mat.uniforms.uTime.value = t;

    const kappa = clamp01(n(frame?.kappa, 0.7));
    const alpha = clamp01(n(frame?.alpha, 0.6));

    // ✅ topology gate plumbing (prefers injected topo_gate01, then topology.gate, then sigma)
    const targetGate = clamp01(
      n(frame?.topo_gate01, n(frame?.topology?.gate, n(frame?.sigma, 1))),
    );

    // ✅ smooth just enough to avoid stepping (use dtc)
    const lerp = 1 - Math.exp(-dtc * 12.0);
    gateSm.current = gateSm.current + (targetGate - gateSm.current) * lerp;

    mat.uniforms.uKappa.value = kappa;
    mat.uniforms.uAlpha.value = alpha;
    mat.uniforms.uGate01.value = gateSm.current;

    // brightness stays stable; tiny lift from gate+alpha
    mat.uniforms.uBrightness.value = 0.98 + 0.10 * gateSm.current + 0.05 * alpha;
  });

  return (
    <group rotation={[-Math.PI / 4, 0, 0]} position={[0, 0.2, 0]}>
      <points geometry={geometry}>
        <shaderMaterial
          ref={materialRef}
          {...finalWormholeShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          toneMapped={false}
        />
      </points>

      <pointLight position={[0, 0, 0]} intensity={0.8} color="#ffffff" distance={3} />
    </group>
  );
}