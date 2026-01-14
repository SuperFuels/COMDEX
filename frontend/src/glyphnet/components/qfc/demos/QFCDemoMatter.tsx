"use client";

import { useMemo, useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const n = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

const vertexShader = `
  varying vec2 vUv;
  varying float vDistortion;
  uniform float uTime;
  uniform float uChi;
  uniform float uCurv;
  uniform float uSigma;
  uniform float uGate01;

  void main() {
    vUv = uv;
    vec3 pos = position;

    // cheaper than distance(pos.xz, vec2(0.0))
    float dist = length(pos.xz);

    // Gate-driven "selection":
    float gateTight = mix(1.55, 0.75, uGate01);
    float gateDepth = mix(0.70, 1.25, uGate01);

    float pinchFactor = exp(-pow(dist, 2.0) / (0.5 + pow(uChi, 2.0) * 8.0 * gateTight));

    pos.y -= pinchFactor * uChi * 6.5 * gateDepth;
    pos.y -= uCurv * 4.0 * exp(-dist * 0.15) * (0.85 + 0.35 * uGate01);

    float rippleFreq = dist * (1.5 + uSigma * 2.0) - uTime * (2.0 + 0.6 * (1.0 - uGate01));
    float rippleAmp  = (0.15 * uSigma) * (0.65 + 0.35 * (1.0 - uGate01));
    pos.y += sin(rippleFreq) * rippleAmp;

    vDistortion = pinchFactor * uChi;

    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_PointSize = (8.0 + (pinchFactor * 25.0 * uChi) * (0.75 + 0.35 * uGate01)) * (1.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const fragmentShader = `
  varying float vDistortion;
  uniform float uAlpha;
  uniform float uGate01;

  void main() {
    vec3 cold = vec3(0.05, 0.15, 0.45);
    vec3 flux = vec3(0.0, 0.8, 1.0);
    vec3 hot  = vec3(1.0, 0.9, 0.3);

    float d = vDistortion;
    float hotBias = mix(0.85, 1.10, uGate01);
    float d2 = clamp(d * hotBias, 0.0, 1.0);

    vec3 color = mix(cold, flux, smoothstep(0.1, 0.5, d2));
    color = mix(color, hot,  smoothstep(0.4, 0.9, d2));

    float a = mix(0.18, 0.90, d2) * uAlpha * (0.85 + 0.25 * uGate01);
    gl_FragColor = vec4(color, a);
  }
`;

export default function QFCDemoMatter({ frame }: { frame: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  // ✅ stable time accumulator (FPS-drop safe)
  const tRef = useRef(0);

  // ✅ smooth topology gate (prevents epoch stepping)
  const gateSm = useRef(1.0);

  const geometry = useMemo(() => new THREE.PlaneGeometry(24, 24, 160, 160), []);

  // ✅ stable uniforms object (do NOT recreate each render)
  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uChi: { value: 0.25 },
      uCurv: { value: 0.1 },
      uSigma: { value: 0.45 },
      uAlpha: { value: 0.8 },
      uGate01: { value: 1.0 },
    }),
    [],
  );

  // ✅ cleanup
  useEffect(() => {
    return () => {
      geometry.dispose();
    };
  }, [geometry]);

  useFrame((state, dtRaw) => {
    const mat = materialRef.current;
    if (!mat) return;

    // ✅ dt clamp pattern (use everywhere)
    const dtc = Math.min(dtRaw, 1 / 30);

    // ✅ stable time
    tRef.current += dtc;
    const t = tRef.current;

    // use stable time for shader evolution (instead of clock.getElapsedTime())
    uniforms.uTime.value = t;

    const chi = clamp01(n(frame?.chi, 0.25));
    const curv = n(frame?.curv, 0.1);
    const sigma = clamp01(n(frame?.sigma, 0.45));
    const alpha = clamp01(n(frame?.alpha, 0.8));

    // ✅ topology gate plumbing (prefers injected topo_gate01, then topology.gate, then sigma)
    const targetGate = clamp01(n(frame?.topo_gate01, n(frame?.topology?.gate, sigma)));

    // ✅ smooth gate using dtc
    const gateLerp = 1 - Math.exp(-dtc * 10.0);
    gateSm.current = gateSm.current + (targetGate - gateSm.current) * gateLerp;

    uniforms.uChi.value = chi;
    uniforms.uCurv.value = curv;
    uniforms.uSigma.value = sigma;
    uniforms.uAlpha.value = alpha;
    uniforms.uGate01.value = gateSm.current;
  });

  return (
    <group rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.5, 0]}>
      <points geometry={geometry}>
        <shaderMaterial
          ref={materialRef}
          vertexShader={vertexShader}
          fragmentShader={fragmentShader}
          uniforms={uniforms}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
    </group>
  );
}