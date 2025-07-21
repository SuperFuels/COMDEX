// File: frontend/components/AION/WormholeEffectMaterial.ts

import * as THREE from "three";

export function createGlowMaterial(color: string = "#66f", pulse: boolean = true): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    uniforms: {
      time: { value: 0 },
      glowColor: { value: new THREE.Color(color) },
    },
    vertexShader: `
      uniform float time;
      varying float vPulse;

      void main() {
        vPulse = sin(time * 3.0 + position.y * 5.0) * 0.3 + 0.7;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 glowColor;
      varying float vPulse;

      void main() {
        float alpha = vPulse;
        gl_FragColor = vec4(glowColor, alpha);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
}