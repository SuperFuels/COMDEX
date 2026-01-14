import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const vol0AxiomShader = {
  uniforms: {
    uTime: { value: 0 },
    uCollapse: { value: 0 }, // Toggle for mu (measure)
    uInvariantErr: { value: 0.0 },
  },
  vertexShader: `
    varying float vCoherence;
    uniform float uTime;
    uniform float uCollapse;

    void main() {
      vec3 pos = position;

      // S0/E0 Symmetry: Commutative Orbit
      float angle = uTime * 2.0;
      float radius = 2.5 * (1.0 - uCollapse * 0.9); // Shrink to point on collapse

      // Swap positions (a + b -> b + a)
      float x = cos(angle + pos.z) * radius;
      float y = sin(angle + pos.z) * radius;

      pos.x += x;
      pos.y += y;

      vCoherence = 1.0 - uCollapse;

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_Position = projectionMatrix * mvPosition;
      gl_PointSize = uCollapse > 0.5 ? 4.0 : 2.0;
    }
  `,
  fragmentShader: `
    varying float vCoherence;

    void main() {
      // Invariant state is White/Silver; Collapsed state is Focused Purple
      vec3 invariantColor = vec3(0.9, 0.9, 1.0);
      vec3 collapsedColor = vec3(0.6, 0.2, 1.0);

      vec3 finalColor = mix(collapsedColor, invariantColor, vCoherence);

      float r = distance(gl_PointCoord, vec2(0.5));
      if (r > 0.5) discard;

      gl_FragColor = vec4(finalColor, 0.8);
    }
  `,
};

type Props = {
  frame?: any; // keep loose to match other demos’ pattern
};

export default function QFCAxiomStability({ frame }: Props) {
  const materialRef = useRef<THREE.ShaderMaterial | null>(null);

  const geometry = useMemo(() => {
    const pts = new Float32Array(500 * 3);
    for (let i = 0; i < 500; i++) {
      pts[i * 3] = (Math.random() - 0.5) * 0.5;
      pts[i * 3 + 1] = (Math.random() - 0.5) * 0.5;
      pts[i * 3 + 2] = Math.random() * Math.PI * 2; // Phase/Order seed
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pts, 3));
    return geo;
  }, []);

  useFrame(({ clock }, dtRaw) => {
    const mat = materialRef.current;
    if (!mat) return;

    const dtc = Math.min(dtRaw, 1 / 30);
    const t = clock.getElapsedTime();
    mat.uniforms.uTime.value = t;

    // If a frame is provided, let sigma influence “collapse tendency” (keeps behavior consistent w/ HUD knobs)
    const sigma = Number(frame?.sigma ?? frame?.topo_gate01 ?? 0);
    const sigma01 = Number.isFinite(sigma) ? Math.max(0, Math.min(1, sigma)) : 0;

    // Base cycle between Symmetry (Rewrite) and Collapse (Measure)
    const cycle = (Math.sin(t * 0.5) + 1.0) / 2.0; // 0..1
    const isCollapsed = cycle > 0.7;

    // Blend: sigma pushes collapse a bit earlier/stronger but keeps the same “feel”
    const target = isCollapsed ? 1.0 : 0.0;
    const biasedTarget = THREE.MathUtils.lerp(target, 1.0, sigma01 * 0.35);

    mat.uniforms.uCollapse.value = THREE.MathUtils.lerp(
      mat.uniforms.uCollapse.value,
      biasedTarget,
      1.0 - Math.exp(-dtc * 6.0),
    );
  });

  return (
    <group>
      {/* Points */}
      <points geometry={geometry}>
        <shaderMaterial
          ref={materialRef}
          // keep shader object stable
          uniforms={vol0AxiomShader.uniforms}
          vertexShader={vol0AxiomShader.vertexShader}
          fragmentShader={vol0AxiomShader.fragmentShader}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>

      {/* Optional subtle “grid plane” in 3D (instead of DOM overlay) */}
      <mesh rotation-x={-Math.PI / 2} position={[0, -2.2, 0]}>
        <planeGeometry args={[20, 20, 1, 1]} />
        <meshBasicMaterial
          color={new THREE.Color(0.2, 0.2, 0.25)}
          transparent
          opacity={0.06}
        />
      </mesh>
    </group>
  );
}