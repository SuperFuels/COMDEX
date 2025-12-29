import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const vertexShader = `
  varying vec2 vUv;
  varying float vDistortion;
  uniform float uTime;
  uniform float uChi;
  uniform float uCurv;
  uniform float uSigma;

  void main() {
    vUv = uv;
    vec3 pos = position;

    // MT01 Soliton Calculation
    float dist = distance(pos.xz, vec2(0.0));
    
    // EXAGGERATED PINCH: The uChi effect is now squared for high-impact visual feedback
    float pinchFactor = exp(-pow(dist, 2.0) / (0.5 + pow(uChi, 2.0) * 8.0));
    
    // GEOMETRIC WARP: High uChi pulls the lattice deep into the Y-axis
    pos.y -= pinchFactor * uChi * 6.5; 
    pos.y -= uCurv * 4.0 * exp(-dist * 0.15); // Deepen gravity well based on curvature

    // COHERENCE RIPPLES: Sigma controls the frequency of the background flux
    pos.y += sin(dist * (1.5 + uSigma * 2.0) - uTime * 2.0) * (0.15 * uSigma);

    vDistortion = pinchFactor * uChi; // Pass displacement magnitude to fragment shader
    
    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_PointSize = (8.0 + (pinchFactor * 25.0 * uChi)) * (1.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const fragmentShader = `
  varying float vDistortion;
  uniform float uAlpha;

  void main() {
    // HEAT MAP COLORING: Transitions from cold space to hot matter emergence
    // Level 1: Deep Blue (Vacuum)
    // Level 2: Cyan/Teal (Information Flux)
    // Level 3: Gold/White (Matter Soliton Peak)
    vec3 cold = vec3(0.05, 0.15, 0.45);
    vec3 flux = vec3(0.0, 0.8, 1.0);
    vec3 hot = vec3(1.0, 0.9, 0.3);

    vec3 color = mix(cold, flux, smoothstep(0.1, 0.5, vDistortion));
    color = mix(color, hot, smoothstep(0.4, 0.9, vDistortion));

    float alpha = mix(0.2, 0.9, vDistortion) * uAlpha;
    gl_FragColor = vec4(color, alpha);
  }
`;

export default function QFCDemoMatter({ frame }: { frame: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);

  // High-density lattice for smooth displacement visuals
  const geometry = useMemo(() => new THREE.PlaneGeometry(24, 24, 160, 160), []);

  useFrame(({ clock }) => {
    if (!materialRef.current) return;
    materialRef.current.uniforms.uTime.value = clock.getElapsedTime();
    materialRef.current.uniforms.uChi.value = frame?.chi ?? 0.25;
    materialRef.current.uniforms.uCurv.value = frame?.curv ?? 0.1;
    materialRef.current.uniforms.uSigma.value = frame?.sigma ?? 0.45;
    materialRef.current.uniforms.uAlpha.value = frame?.alpha ?? 0.8;
  });

  const uniforms = useMemo(() => ({
    uTime: { value: 0 },
    uChi: { value: 0.25 },
    uCurv: { value: 0.1 },
    uSigma: { value: 0.45 },
    uAlpha: { value: 0.8 }
  }), []);

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