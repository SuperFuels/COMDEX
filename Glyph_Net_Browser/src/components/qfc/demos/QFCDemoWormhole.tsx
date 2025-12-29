"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const finalWormholeShader = {
  uniforms: {
    uTime: { value: 0 },
    uKappa: { value: 0.6 },
    uAlpha: { value: 0.5 },
    uBrightness: { value: 1.05 }, // Dimmed to stabilize the white matter peak
  },
  vertexShader: `
    varying float vIntensity;
    varying float vSide;
    uniform float uTime;
    uniform float uKappa;
    uniform float uAlpha;

    void main() {
      vec3 pos = position;
      float side = pos.z > 0.0 ? 1.0 : -1.0;
      vSide = side;

      float d = length(pos.xy);
      
      // M1 Lorentzian Bridge: Creating the stable throat geometry
      float throat = (uKappa + uAlpha * 2.5) / (1.0 + pow(d * 1.5, 2.0));
      
      // Vertical displacement creating the "Pinch" effect
      pos.z -= side * throat * 3.0;

      // Subtle internal turbulence
      if (d < 1.2) {
        float wave = sin(d * 8.0 - uTime * 6.0) * cos(pos.x * 2.0);
        pos.z += wave * 0.12 * uAlpha;
      }

      vIntensity = throat;
      
      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
      
      // Point size modulation: dense at the bridge, sparse at edges
      gl_PointSize = 1.6 + (throat * 3.0);
    }
  `,
  fragmentShader: `
    varying float vIntensity;
    varying float vSide;
    uniform float uBrightness;

    void main() {
      // High-visibility palette
      vec3 topColor = vec3(0.0, 0.85, 1.0);    // Neon Cyan
      vec3 bottomColor = vec3(0.4, 0.15, 1.0); // Electric Purple
      vec3 bridgeColor = vec3(0.85, 0.85, 1.0); // Dimmed White (40% reduction)
      
      vec3 baseColor = mix(bottomColor, topColor, (vSide + 1.0) / 2.0);
      
      // Sharpened mixing to keep the white peak localized and not "blown out"
      vec3 finalColor = mix(baseColor, bridgeColor, pow(vIntensity, 4.0));
      
      // Balanced glow factor
      float glow = pow(vIntensity, 2.0) * uBrightness;
      float alpha = clamp(0.2 + glow, 0.0, 1.0);

      // Smooth circular particles
      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      gl_FragColor = vec4(finalColor * (0.85 + glow), alpha);
    }
  `
};

export default function QFCDemoWormhole({ frame }: { frame: any }) {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  
  // High-density lattice for the stable bridge visualization
  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(16, 16, 128, 128);
    const pos = geo.attributes.position.array as Float32Array;
    const count = pos.length / 3;
    
    const doublePos = new Float32Array(pos.length * 2);
    for (let i = 0; i < count; i++) {
        doublePos[i * 3] = pos[i * 3];
        doublePos[i * 3 + 1] = pos[i * 3 + 1];
        doublePos[i * 3 + 2] = 2.5; // Top Layer
        
        const offset = count * 3;
        doublePos[offset + i * 3] = pos[i * 3];
        doublePos[offset + i * 3 + 1] = pos[i * 3 + 1];
        doublePos[offset + i * 3 + 2] = -2.5; // Bottom Layer
    }
    const finalGeo = new THREE.BufferGeometry();
    finalGeo.setAttribute('position', new THREE.BufferAttribute(doublePos, 3));
    return finalGeo;
  }, []);

  useFrame(({ clock }) => {
    if (!materialRef.current) return;
    materialRef.current.uniforms.uTime.value = clock.getElapsedTime();
    materialRef.current.uniforms.uKappa.value = frame?.kappa ?? 0.7;
    materialRef.current.uniforms.uAlpha.value = frame?.alpha ?? 0.6;
    materialRef.current.uniforms.uBrightness.value = 1.05; 
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
        />
      </points>
      
      {/* Anchor Light: Tuned to provide subtle center depth */}
      <pointLight position={[0, 0, 0]} intensity={0.8} color="#ffffff" distance={3} />
    </group>
  );
}