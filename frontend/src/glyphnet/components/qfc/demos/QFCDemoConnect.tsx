"use client";

import { useMemo, useRef, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const n = (v: any, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

export default function QFCDemoConnect({ frame }: { frame: any }) {
  const nodesRef = useRef<THREE.Group>(null);
  const lineMaterialRef = useRef<THREE.ShaderMaterial>(null);

  // ✅ dt clamp + stable time accumulator
  const tRef = useRef(0);

  // ✅ smooth gate (prevents “epoch stepping” jitter)
  const gateSm = useRef(1.0);

  // Initialize nodes as "Information Hubs"
  const nodes = useMemo(() => {
    return Array.from({ length: 12 }).map((_, i) => ({
      id: i,
      phaseOffset: Math.random() * Math.PI * 2,
      basePos: new THREE.Vector3(
        (Math.random() - 0.5) * 12,
        (Math.random() - 0.5) * 6 + 1,
        (Math.random() - 0.5) * 12,
      ),
    }));
  }, []);

  // Custom Shader for "Entanglement Threads"
  const lineShader = useMemo(
    () => ({
      uniforms: {
        uTime: { value: 0 },
        uCoupling: { value: 0.5 },
        uAlpha: { value: 0.2 },
        uGate01: { value: 1.0 },
      },
      vertexShader: `
        varying float vProgress;
        uniform float uTime;
        uniform float uCoupling;
        uniform float uGate01;

        void main() {
          vProgress = uv.x;
          vec3 pos = position;

          // Subtle vibration: gate high => more coherent "thread tension"
          float vib = 0.035 + 0.030 * uGate01;
          pos.y += sin(pos.x * 2.0 + uTime * 3.0) * vib * uCoupling;

          gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
        }
      `,
      fragmentShader: `
        varying float vProgress;
        uniform float uTime;
        uniform float uCoupling;
        uniform float uAlpha;
        uniform float uGate01;

        void main() {
          // Gate-driven packet speed: gate high => faster, more "selective"
          float speed = 0.45 + 0.95 * uGate01;          // 0.45..1.40
          float phase = fract(vProgress - uTime * speed * (0.65 + 0.55 * uCoupling));
          float packet = smoothstep(0.45, 0.5, 1.0 - phase);

          vec3 base = vec3(0.0, 0.4, 0.6);
          vec3 hot  = vec3(0.2, 0.9, 1.0);
          vec3 color = mix(base, hot, packet);

          // Gate increases visibility/lock "confidence"
          float a = (0.08 + packet * 0.85) * uAlpha;
          a *= (0.25 + 0.75 * uCoupling);
          a *= (0.55 + 0.65 * uGate01);

          gl_FragColor = vec4(color, a);
        }
      `,
    }),
    [],
  );

  const lineGeom = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    const indices: number[] = [];
    const vertices: number[] = [];
    const uvs: number[] = [];

    // Connect each node to 2 neighbors to create a "Causal Loop"
    let vIdx = 0;
    for (let i = 0; i < nodes.length; i++) {
      for (let j = 1; j <= 2; j++) {
        vertices.push(0, 0, 0, 0, 0, 0); // Placeholder
        uvs.push(0, 0, 1, 0); // 0 at start, 1 at end for the shader packet
        indices.push(vIdx++, vIdx++);
      }
    }
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
    geometry.setIndex(indices);
    return geometry;
  }, [nodes]);

  // ✅ cleanup geometry on unmount
  useEffect(() => {
    return () => {
      lineGeom.dispose();
    };
  }, [lineGeom]);

  useFrame((_state, dtRaw) => {
    // ✅ dt clamp
    const dtc = Math.min(dtRaw, 1 / 30);

    // ✅ stable time accumulator
    tRef.current += dtc;
    const t = tRef.current;

    const coupling = clamp01(n(frame?.coupling_score, 0.5));
    const alpha = clamp01(n(frame?.alpha, 0.3));

    // ✅ topology gate plumbing (prefers injected topo_gate01, then topology.gate, then sigma)
    const targetGate = clamp01(
      n(frame?.topo_gate01, n(frame?.topology?.gate, n(frame?.sigma, 1))),
    );

    // ✅ smooth gate (use dtc)
    const gateLerp = 1 - Math.exp(-dtc * 10.0);
    gateSm.current = gateSm.current + (targetGate - gateSm.current) * gateLerp;
    const topoGate01 = gateSm.current;

    if (lineMaterialRef.current) {
      lineMaterialRef.current.uniforms.uTime.value = t;
      lineMaterialRef.current.uniforms.uCoupling.value = coupling;
      lineMaterialRef.current.uniforms.uAlpha.value = alpha;
      lineMaterialRef.current.uniforms.uGate01.value = topoGate01;
    }

    // Gate-driven behavior:
    const orbitTight = 1.0 - 0.55 * topoGate01; // 1.0..0.45
    const orbitSpeed = 0.42 + 0.28 * topoGate01; // 0.42..0.70
    const bobAmp = 0.55 * (0.85 - 0.45 * topoGate01); // calmer when gate high

    const currentPositions: THREE.Vector3[] = nodes.map((node) => {
      // Avoid new allocations from clone() every frame
      const p = new THREE.Vector3().copy(node.basePos);

      const radius = 1.6 * (1.0 - coupling * 0.45) * orbitTight;
      p.x += Math.cos(t * orbitSpeed + node.phaseOffset) * radius;
      p.z += Math.sin(t * orbitSpeed + node.phaseOffset) * radius;
      p.y += Math.sin(t * 0.8 + node.phaseOffset) * bobAmp;

      return p;
    });

    // Update Lines
    const posAttr = lineGeom.getAttribute("position") as THREE.BufferAttribute;
    let lIdx = 0;
    for (let i = 0; i < nodes.length; i++) {
      for (let j = 1; j <= 2; j++) {
        const next = (i + j) % nodes.length;
        const start = currentPositions[i];
        const end = currentPositions[next];
        posAttr.setXYZ(lIdx++, start.x, start.y, start.z);
        posAttr.setXYZ(lIdx++, end.x, end.y, end.z);
      }
    }
    posAttr.needsUpdate = true;

    // Update Node Meshes
    if (nodesRef.current) {
      nodesRef.current.children.forEach((child, i) => {
        child.position.copy(currentPositions[i]);

        // Gate increases "lock brightness" via size stability (less fluctuation)
        const baseScale = 0.22 + coupling * 0.42;
        const gateBoost = 0.90 + 0.25 * topoGate01;
        child.scale.setScalar(baseScale * gateBoost);
      });
    }
  });

  return (
    <group>
      <lineSegments geometry={lineGeom}>
        <shaderMaterial
          ref={lineMaterialRef}
          uniforms={lineShader.uniforms}
          vertexShader={lineShader.vertexShader}
          fragmentShader={lineShader.fragmentShader}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>

      <group ref={nodesRef}>
        {nodes.map((node) => (
          <mesh key={node.id}>
            <sphereGeometry args={[0.3, 16, 16]} />
            <meshBasicMaterial color="#22d3ee" transparent opacity={0.8} />
            {/* Inner "Nucleus" */}
            <mesh scale={0.5}>
              <sphereGeometry args={[0.3, 8, 8]} />
              <meshBasicMaterial color="#ffffff" />
            </mesh>
          </mesh>
        ))}
      </group>
    </group>
  );
}