import React, { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { animated, useSpring } from "@react-spring/three";
import { Html } from "@react-three/drei";

type BeamProps = {
  source: THREE.Vector3;
  target: THREE.Vector3;
  logicType?: "collapse" | "mutate" | "push" | "replay";
  entropy?: number;
  cost?: number;
  pulseSpeed?: number;
  showLabel?: boolean;
  onClick?: () => void;
};

const logicColors: Record<string, string> = {
  collapse: "#ff0055",
  mutate: "#00ddff",
  push: "#ffaa00",
  replay: "#cc00ff",
};

function computeGradientColor(entropy?: number, cost?: number, type?: string): string {
  if (type && logicColors[type]) return logicColors[type];
  const hue = (entropy ?? 0.5) * 240 - (cost ?? 0) * 40;
  const clamped = Math.max(0, Math.min(300, hue));
  return `hsl(${clamped}, 100%, 55%)`;
}

export const QGlyphFusionBeam: React.FC<BeamProps> = ({
  source,
  target,
  logicType,
  entropy,
  cost,
  pulseSpeed = 1,
  showLabel = true,
  onClick,
}) => {
  const beamRef = useRef<THREE.Mesh>(null!);
  const materialRef = useRef<THREE.MeshBasicMaterial>(null!);

  const color = useMemo(
    () => computeGradientColor(entropy, cost, logicType),
    [entropy, cost, logicType]
  );

  const direction = useMemo(() => {
    const dir = new THREE.Vector3().subVectors(target, source);
    return {
      length: dir.length(),
      rotation: new THREE.Euler().setFromQuaternion(
        new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          dir.clone().normalize()
        )
      ),
    };
  }, [source, target]);

  // ✅ useSpring tuple form: [springValues, api]
  const [spring, api] = useSpring(() => ({
    scale: [1, 1, 1] as [number, number, number],
    config: { duration: 800 },
  }));

  // Drive the pulsing animation with the api to avoid tuple typing errors
  useEffect(() => {
    api.stop();
    if (pulseSpeed > 0) {
      api.start({
        to: async (next) => {
          // simple breathing loop
          // eslint-disable-next-line no-constant-condition
          while (true) {
            await next({ scale: [1.25, 1, 1.25] as [number, number, number] });
            await next({ scale: [1, 1, 1] as [number, number, number] });
          }
        },
        config: { duration: Math.max(1, 1500 / pulseSpeed) },
      });
    } else {
      api.start({ to: { scale: [1, 1, 1] as [number, number, number] } });
    }
  }, [pulseSpeed, api]);

  useFrame(() => {
    if (materialRef.current) {
      materialRef.current.color.set(color);
      materialRef.current.opacity = 0.5 + 0.4 * Math.sin(Date.now() * 0.005 * Math.max(0.01, pulseSpeed));
    }
  });

  return (
    <>
      <animated.mesh
        ref={beamRef}
        position={source.clone().add(target).multiplyScalar(0.5)}
        rotation={direction.rotation}
        scale={spring.scale}
        onClick={onClick}
      >
        <cylinderGeometry args={[0.03, 0.03, direction.length, 8]} />
        <meshBasicMaterial
          ref={materialRef}
          transparent
          opacity={0.8}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </animated.mesh>

      {showLabel && (
        <Html position={source.clone().add(target).multiplyScalar(0.5)} center distanceFactor={10}>
          <div
            style={{
              background: "rgba(0,0,0,0.6)",
              color: "#fff",
              padding: "4px 8px",
              fontSize: "0.75rem",
              borderRadius: "4px",
              pointerEvents: "none",
              whiteSpace: "nowrap",
            }}
          >
            {logicType || "beam"}
          </div>
        </Html>
      )}
    </>
  );
};