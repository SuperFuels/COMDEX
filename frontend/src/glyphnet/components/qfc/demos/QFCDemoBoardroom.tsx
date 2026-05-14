"use client";

import { useMemo } from "react";
import * as THREE from "three";
import { Line, Text } from "@react-three/drei";
import type { BoardroomModel } from "../../boardroom/boardroom.types";
import { BOARDROOM_DEMO_MODEL } from "../../boardroom/boardroom.mock";

const DreiLine: any = Line;
const DreiText: any = Text;

function toneColor(state?: string) {
  if (state === "healthy") return "#22c55e";
  if (state === "warning") return "#f59e0b";
  if (state === "blocked") return "#ef4444";
  if (state === "escalated") return "#f97316";
  return "#38bdf8";
}

function flowColor(state?: string) {
  if (state === "blocked") return "#ef4444";
  if (state === "warning") return "#f59e0b";
  return "#7dd3fc";
}

type SeatPoint = {
  x: number;
  y: number;
  z: number;
  angle: number;
};

function WorkerAgent({
  label,
  owner,
  color,
}: {
  label: string;
  owner: string;
  color: string;
}) {
  return (
    <group>
      <mesh position={[0, 0.02, 0]}>
        <boxGeometry args={[0.42, 0.05, 0.42]} />
        <meshStandardMaterial color="#10203d" metalness={0.22} roughness={0.72} />
      </mesh>

      <mesh position={[0, 0.045, 0]}>
        <boxGeometry args={[0.28, 0.012, 0.28]} />
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.22} />
      </mesh>

      <mesh position={[-0.07, 0.09, 0.02]}>
        <boxGeometry args={[0.08, 0.045, 0.11]} />
        <meshStandardMaterial color="#dbe7f5" roughness={0.72} />
      </mesh>
      <mesh position={[0.07, 0.09, 0.02]}>
        <boxGeometry args={[0.08, 0.045, 0.11]} />
        <meshStandardMaterial color="#dbe7f5" roughness={0.72} />
      </mesh>

      <mesh position={[-0.07, 0.17, 0.01]}>
        <capsuleGeometry args={[0.024, 0.11, 4, 8]} />
        <meshStandardMaterial color="#edf4fb" roughness={0.76} />
      </mesh>
      <mesh position={[0.07, 0.17, 0.01]}>
        <capsuleGeometry args={[0.024, 0.11, 4, 8]} />
        <meshStandardMaterial color="#edf4fb" roughness={0.76} />
      </mesh>

      <mesh position={[0, 0.34, 0]}>
        <sphereGeometry args={[0.16, 24, 24]} />
        <meshStandardMaterial color="#e9f1fb" metalness={0.08} roughness={0.62} />
      </mesh>

      <mesh position={[0, 0.3, 0.1]}>
        <circleGeometry args={[0.055, 20]} />
        <meshBasicMaterial color="#0f172a" transparent opacity={0.28} />
      </mesh>

      <mesh position={[0, 0.48, 0]}>
        <cylinderGeometry args={[0.05, 0.055, 0.09, 20]} />
        <meshStandardMaterial color="#111827" metalness={0.2} roughness={0.6} />
      </mesh>

      <mesh position={[-0.2, 0.33, 0]} rotation={[0, 0, 0.45]}>
        <capsuleGeometry args={[0.03, 0.16, 4, 8]} />
        <meshStandardMaterial color="#e9f1fb" roughness={0.72} />
      </mesh>
      <mesh position={[0.2, 0.33, 0]} rotation={[0, 0, -0.45]}>
        <capsuleGeometry args={[0.03, 0.16, 4, 8]} />
        <meshStandardMaterial color="#e9f1fb" roughness={0.72} />
      </mesh>

      <mesh position={[0, 0.66, 0]}>
        <boxGeometry args={[0.3, 0.24, 0.22]} />
        <meshStandardMaterial color="#f3f7fc" metalness={0.08} roughness={0.6} />
      </mesh>

      <mesh position={[-0.18, 0.66, 0]}>
        <sphereGeometry args={[0.07, 18, 18]} />
        <meshStandardMaterial color="#d7e7fb" roughness={0.65} />
      </mesh>
      <mesh position={[0.18, 0.66, 0]}>
        <sphereGeometry args={[0.07, 18, 18]} />
        <meshStandardMaterial color="#d7e7fb" roughness={0.65} />
      </mesh>

      <mesh position={[0, 0.66, 0.112]}>
        <planeGeometry args={[0.17, 0.09]} />
        <meshBasicMaterial color="#0b1220" />
      </mesh>

      <mesh position={[-0.04, 0.66, 0.118]}>
        <circleGeometry args={[0.015, 16]} />
        <meshBasicMaterial color="#67e8f9" />
      </mesh>
      <mesh position={[0.04, 0.66, 0.118]}>
        <circleGeometry args={[0.015, 16]} />
        <meshBasicMaterial color="#67e8f9" />
      </mesh>

      <mesh position={[0, 0.628, 0.118]}>
        <torusGeometry args={[0.017, 0.0035, 8, 20, Math.PI]} />
        <meshBasicMaterial color="#67e8f9" />
      </mesh>

      <DreiText
        position={[0, 0.35, 0.165]}
        fontSize={0.052}
        color="#2563eb"
        anchorX="center"
        anchorY="middle"
        maxWidth={0.22}
      >
        AI
      </DreiText>

      <DreiText
        position={[0, 0.9, 0]}
        fontSize={0.11}
        color="#f8fafc"
        anchorX="center"
        anchorY="middle"
        maxWidth={1.2}
      >
        {label}
      </DreiText>

      <DreiText
        position={[0, 0.81, 0]}
        fontSize={0.06}
        color="#cbd5e1"
        anchorX="center"
        anchorY="middle"
        maxWidth={1.2}
      >
        {owner}
      </DreiText>

      <mesh position={[0, 0.26, 0.16]}>
        <circleGeometry args={[0.02, 20]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  );
}

function OverseerAgent({
  label,
  sublabel,
  accent,
  bodyColor,
  visorColor,
  scale = 1,
}: {
  label: string;
  sublabel: string;
  accent: string;
  bodyColor: string;
  visorColor: string;
  scale?: number;
}) {
  return (
    <group scale={scale}>
      <mesh position={[0, 0.04, 0]}>
        <cylinderGeometry args={[0.26, 0.32, 0.08, 28]} />
        <meshStandardMaterial color="#0f172a" metalness={0.28} roughness={0.72} />
      </mesh>

      <mesh position={[0, 0.12, 0]}>
        <boxGeometry args={[0.42, 0.03, 0.42]} />
        <meshBasicMaterial color={accent} transparent opacity={0.18} />
      </mesh>

      <mesh position={[-0.08, 0.22, 0.02]}>
        <capsuleGeometry args={[0.026, 0.16, 4, 8]} />
        <meshStandardMaterial color={bodyColor} roughness={0.7} />
      </mesh>
      <mesh position={[0.08, 0.22, 0.02]}>
        <capsuleGeometry args={[0.026, 0.16, 4, 8]} />
        <meshStandardMaterial color={bodyColor} roughness={0.7} />
      </mesh>

      <mesh position={[0, 0.42, 0]}>
        <sphereGeometry args={[0.2, 24, 24]} />
        <meshStandardMaterial color={bodyColor} metalness={0.12} roughness={0.58} />
      </mesh>

      <mesh position={[0, 0.42, 0.125]}>
        <planeGeometry args={[0.2, 0.12]} />
        <meshBasicMaterial color={visorColor} />
      </mesh>

      <mesh position={[-0.05, 0.42, 0.13]}>
        <circleGeometry args={[0.018, 18]} />
        <meshBasicMaterial color="#67e8f9" />
      </mesh>
      <mesh position={[0.05, 0.42, 0.13]}>
        <circleGeometry args={[0.018, 18]} />
        <meshBasicMaterial color="#67e8f9" />
      </mesh>

      <mesh position={[0, 0.28, 0]}>
        <capsuleGeometry args={[0.05, 0.3, 4, 8]} />
        <meshStandardMaterial color={bodyColor} roughness={0.66} />
      </mesh>

      <mesh position={[-0.2, 0.33, 0]} rotation={[0, 0, 0.28]}>
        <capsuleGeometry args={[0.028, 0.18, 4, 8]} />
        <meshStandardMaterial color={bodyColor} roughness={0.72} />
      </mesh>
      <mesh position={[0.2, 0.33, 0]} rotation={[0, 0, -0.28]}>
        <capsuleGeometry args={[0.028, 0.18, 4, 8]} />
        <meshStandardMaterial color={bodyColor} roughness={0.72} />
      </mesh>

      <mesh position={[0, 0.3, 0.155]}>
        <circleGeometry args={[0.028, 20]} />
        <meshBasicMaterial color={accent} />
      </mesh>

      <DreiText
        position={[0, 0.76, 0]}
        fontSize={0.12}
        color="#f8fafc"
        anchorX="center"
        anchorY="middle"
      >
        {label}
      </DreiText>

      <DreiText
        position={[0, 0.66, 0]}
        fontSize={0.06}
        color="#cbd5e1"
        anchorX="center"
        anchorY="middle"
      >
        {sublabel}
      </DreiText>
    </group>
  );
}

export default function QFCDemoBoardroom({
  frame,
}: {
  frame: any | null;
}) {
  const model: BoardroomModel =
    (frame?.boardroom as BoardroomModel | undefined) ?? BOARDROOM_DEMO_MODEL;

  const seatLayout = useMemo(() => {
    const count = Math.max(model.seats.length, 1);
    const radius = 3.55;

    return model.seats.map((seat, index) => {
      const angle = -Math.PI / 2 + (index / count) * Math.PI * 2;
      return {
        seat,
        point: {
          x: Math.cos(angle) * radius,
          y: 0.16,
          z: Math.sin(angle) * radius,
          angle,
        } satisfies SeatPoint,
      };
    });
  }, [model.seats]);

  return (
    <group position={[0, 0, 0]}>
      <mesh position={[0, -0.16, 0]}>
        <cylinderGeometry args={[2.45, 2.45, 0.02, 7]} />
        <meshBasicMaterial color="#020617" transparent opacity={0.18} />
      </mesh>

      <mesh position={[0, -0.08, 0]}>
        <cylinderGeometry args={[2.18, 2.18, 0.12, 7]} />
        <meshStandardMaterial
          color="#081120"
          metalness={0.26}
          roughness={0.82}
        />
      </mesh>

      <mesh position={[0, -0.005, 0]}>
        <cylinderGeometry args={[1.9, 1.9, 0.03, 7]} />
        <meshStandardMaterial
          color="#0b1730"
          metalness={0.16}
          roughness={0.72}
          transparent
          opacity={0.98}
        />
      </mesh>

      <mesh position={[0, 0.018, 0]}>
        <cylinderGeometry args={[1.22, 1.22, 0.012, 7]} />
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.08} />
      </mesh>

      <mesh position={[0, 0.06, 0]}>
        <cylinderGeometry args={[0.16, 0.16, 0.05, 32]} />
        <meshStandardMaterial
          color="#111827"
          metalness={0.3}
          roughness={0.45}
        />
      </mesh>

      <mesh position={[0, 0.11, 0]}>
        <sphereGeometry args={[0.06, 24, 24]} />
        <meshStandardMaterial
          color="#7dd3fc"
          emissive="#38bdf8"
          emissiveIntensity={0.85}
          metalness={0.15}
          roughness={0.25}
        />
      </mesh>

      <group position={[0, 0.03, 0]}>
        <DreiText
          position={[0, 0, -0.58]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={0.16}
          color="#94a3b8"
          anchorX="center"
          anchorY="middle"
        >
          Company State
        </DreiText>

        <DreiText
          position={[0, 0, -0.1]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={0.34}
          color="#e5e7eb"
          anchorX="center"
          anchorY="middle"
          maxWidth={3.2}
        >
          {model.label}
        </DreiText>

        <DreiText
          position={[0, 0, 0.45]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={0.2}
          color="#e5e7eb"
          anchorX="center"
          anchorY="middle"
          maxWidth={3.4}
        >
          {`Rev ${model.center.revenue} · Cash ${model.center.cash}`}
        </DreiText>

        <DreiText
          position={[0, 0, 0.82]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={0.2}
          color="#e5e7eb"
          anchorX="center"
          anchorY="middle"
          maxWidth={3.4}
        >
          {`Pipeline ${model.center.pipeline} · Profit ${model.center.profit}`}
        </DreiText>
      </group>

      {model.flows.map((flow) => {
        const fromNode = seatLayout.find((x) => x.seat.id === flow.from);
        const toNode = seatLayout.find((x) => x.seat.id === flow.to);
        if (!fromNode || !toNode) return null;

        return (
          <DreiLine
            key={flow.id}
            points={[
              new THREE.Vector3(fromNode.point.x, 0.18, fromNode.point.z),
              new THREE.Vector3(0, 0.1, 0),
              new THREE.Vector3(toNode.point.x, 0.18, toNode.point.z),
            ]}
            color={flowColor(flow.state)}
            lineWidth={1}
            transparent
            opacity={0.5}
          />
        );
      })}

      {seatLayout.map(({ seat, point }) => {
        const color = toneColor(seat.state);

        return (
          <group
            key={seat.id}
            position={[point.x, point.y, point.z]}
            rotation={[0, -point.angle + Math.PI / 2, 0]}
          >
            <WorkerAgent
              label={seat.shortLabel ?? seat.label}
              owner={seat.owner ?? seat.kind}
              color={color}
            />
          </group>
        );
      })}

      {/* Aion overseer */}
      <group position={[0, 0.22, -5.15]} rotation={[0, 0, 0]}>
        <OverseerAgent
          label="AION"
          sublabel="Overseer"
          accent="#8b5cf6"
          bodyColor="#f3f7fc"
          visorColor="#120f2d"
          scale={1.15}
        />
      </group>

      {/* OpenAI external advisor */}
      <group position={[4.95, 0.18, -4.25]} rotation={[0, -0.48, 0]}>
        <OverseerAgent
          label="OpenAI"
          sublabel="Advisor"
          accent="#22c55e"
          bodyColor="#dbeafe"
          visorColor="#052e2b"
          scale={0.96}
        />
      </group>

      {/* optional link lines from overseers to centre */}
      <DreiLine
        points={[
          new THREE.Vector3(0, 0.5, -5.15),
          new THREE.Vector3(0, 0.14, 0),
        ]}
        color="#8b5cf6"
        lineWidth={1}
        transparent
        opacity={0.3}
      />
      <DreiLine
        points={[
          new THREE.Vector3(4.95, 0.4, -4.25),
          new THREE.Vector3(0, 0.14, 0),
        ]}
        color="#22c55e"
        lineWidth={1}
        transparent
        opacity={0.24}
      />
    </group>
  );
}