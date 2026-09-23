"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Line, Text } from "@react-three/drei";
import * as THREE from "three";
import { DEMO_PULSE } from "./boardroom.domain.mock";
import type {
  BoardroomInspectorTarget,
  BusinessPulse,
  DepartmentFloorFlow,
  FinanceFloorState,
  HRFloorState,
  MarketingFloorState,
  OperationsFloorState,
  SalesFloorState,
  Seat,
  SupportFloorState,
} from "./boardroom.domain";
import { seatStateColor } from "./boardroom.world.constants";

const DreiText: any = Text;
const DreiLine: any = Line;

type ChannelInput = {
  key: string;
  label: string;
  subtitle: string;
  value: string;
  x: number;
  y: number;
  z: number;
  accent: string;
  seatId: string;
};

type FlowZone =
  | "sales"
  | "operations"
  | "finance"
  | "support"
  | "hr"
  | "marketing";

function fmtMoney(v: number) {
  return `£${v.toLocaleString("en-GB")}`;
}

function fmtPct(v: number) {
  return `${v}%`;
}

function getFlowStageLabel(
  flow: DepartmentFloorFlow,
  stages: Array<{ id: string; label: string }>,
  side: "from" | "to",
) {
  const stageId = side === "from" ? flow.fromStageId : flow.toStageId;
  return stages.find((stage) => stage.id === stageId)?.label ?? stageId;
}

function flowTone(flow: DepartmentFloorFlow) {
  if (flow.exception || (flow.blockedCount ?? 0) > 0) return "#ef4444";
  if (flow.bottleneck) return "#f59e0b";
  return seatStateColor(flow.state);
}

function flowOverlayValue(flow: DepartmentFloorFlow) {
  const parts: string[] = [`${flow.count}`];

  if (typeof flow.value === "number") {
    parts.push(fmtMoney(flow.value));
  }

  if (typeof flow.cycleTimeDays === "number") {
    parts.push(`${flow.cycleTimeDays}d`);
  }

  if ((flow.blockedCount ?? 0) > 0) {
    parts.push(`${flow.blockedCount} blocked`);
  }

  return parts.join(" · ");
}

function FlowOverlayCard({
  position,
  label,
  value,
  tone,
  active = false,
  onClick,
}: {
  position: [number, number, number];
  label: string;
  value: string;
  tone: string;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <group
      position={position}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
    >
      <mesh>
        <boxGeometry args={[3.1, 0.8, 1.05]} />
        <meshStandardMaterial color="#ffffff" roughness={0.94} />
      </mesh>

      <mesh position={[0, 0.42, 0]}>
        <boxGeometry args={[3.1, 0.04, 1.05]} />
        <meshBasicMaterial color={tone} transparent opacity={active ? 0.3 : 0.14} />
      </mesh>

      {active ? (
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[3.22, 0.88, 1.13]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.12} />
        </mesh>
      ) : null}

      <group position={[0, 0.02, 0.6]}>
        <DreiText
          position={[0, 0.14, 0]}
          fontSize={0.1}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
          maxWidth={2.7}
        >
          {label}
        </DreiText>

        <DreiText
          position={[0, -0.12, 0]}
          fontSize={0.13}
          color={tone}
          anchorX="center"
          anchorY="middle"
          maxWidth={2.7}
        >
          {value}
        </DreiText>
      </group>
    </group>
  );
}

function HandoffPulse({
  start,
  end,
  color = "#3b82f6",
  phase = 0,
}: {
  start: [number, number, number];
  end: [number, number, number];
  color?: string;
  phase?: number;
}) {
  const ref = useRef<THREE.Group>(null);

  useFrame(({ clock }) => {
    const t = (Math.sin(clock.elapsedTime * 1.45 + phase) + 1) / 2;
    const x = THREE.MathUtils.lerp(start[0], end[0], t);
    const y = THREE.MathUtils.lerp(start[1], end[1], t);
    const z = THREE.MathUtils.lerp(start[2], end[2], t);

    if (ref.current) {
      ref.current.position.set(x, y, z);
    }
  });

  return (
    <group ref={ref}>
      <mesh>
        <boxGeometry args={[0.42, 0.14, 0.22]} />
        <meshBasicMaterial color={color} />
      </mesh>
      <mesh position={[0.24, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
        <coneGeometry args={[0.12, 0.22, 3]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>
  );
}

function FlowExceptionRoute({
  points,
  color,
}: {
  points: [number, number, number][];
  color: string;
}) {
  return (
    <DreiLine
      points={points.map((p) => new THREE.Vector3(p[0], p[1], p[2]))}
      color={color}
      lineWidth={1.5}
      transparent
      opacity={0.72}
    />
  );
}


function FacingLabel({
  title,
  subtitle,
  value,
  color = "#0f172a",
  accent = "#1a8aff",
  y = 0,
  z = 0.95,
  titleSize = 0.26,
}: {
  title: string;
  subtitle?: string;
  value?: string;
  color?: string;
  accent?: string;
  y?: number;
  z?: number;
  titleSize?: number;
}) {
  return (
    <group position={[0, y, z]}>
      <DreiText
        position={[0, 0.34, 0]}
        fontSize={titleSize}
        color={color}
        anchorX="center"
        anchorY="middle"
        fontWeight={800}
      >
        {title}
      </DreiText>

      {subtitle ? (
        <DreiText
          position={[0, 0.04, 0]}
          fontSize={0.11}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
          maxWidth={4}
        >
          {subtitle}
        </DreiText>
      ) : null}

      {value ? (
        <DreiText
          position={[0, -0.26, 0]}
          fontSize={0.12}
          color={accent}
          anchorX="center"
          anchorY="middle"
          maxWidth={4}
        >
          {value}
        </DreiText>
      ) : null}
    </group>
  );
}

function FactoryBase() {
  return (
    <group position={[8, -0.78, 0]}>
      <mesh receiveShadow>
        <boxGeometry args={[102, 0.18, 28]} />
        <meshStandardMaterial color="#dfe7f1" roughness={0.96} metalness={0.02} />
      </mesh>

      <mesh position={[0, -0.12, 0]}>
        <boxGeometry args={[102.6, 0.04, 28.6]} />
        <meshBasicMaterial color="#cfd9e6" transparent opacity={0.55} />
      </mesh>
    </group>
  );
}

function ConveyorSegment({
  x,
  z = 0,
  width = 8.2,
  rotationY = 0,
}: {
  x: number;
  z?: number;
  width?: number;
  rotationY?: number;
}) {
  return (
    <group position={[x, -0.16, z]} rotation={[0, rotationY, 0]}>
      <mesh>
        <boxGeometry args={[width, 0.18, 1.5]} />
        <meshStandardMaterial color="#b9c7d8" roughness={0.88} />
      </mesh>

      <mesh position={[0, 0.04, 0]}>
        <boxGeometry args={[width - 0.34, 0.05, 0.88]} />
        <meshStandardMaterial color="#374151" roughness={0.58} />
      </mesh>

      <mesh position={[0, 0.075, 0]}>
        <boxGeometry args={[width - 0.56, 0.016, 0.5]} />
        <meshBasicMaterial color="#9ca3af" />
      </mesh>

      <mesh position={[-width / 2 + 0.42, -0.02, 0]}>
        <cylinderGeometry args={[0.26, 0.26, 0.98, 24]} />
        <meshStandardMaterial color="#d7dee9" roughness={0.86} />
      </mesh>

      <mesh position={[width / 2 - 0.42, -0.02, 0]}>
        <cylinderGeometry args={[0.26, 0.26, 0.98, 24]} />
        <meshStandardMaterial color="#d7dee9" roughness={0.86} />
      </mesh>

      <mesh position={[-width / 2 + 0.42, -0.64, 0]}>
        <boxGeometry args={[0.12, 1.02, 0.12]} />
        <meshStandardMaterial color="#9aa9bc" roughness={0.9} />
      </mesh>

      <mesh position={[width / 2 - 0.42, -0.64, 0]}>
        <boxGeometry args={[0.12, 1.02, 0.12]} />
        <meshStandardMaterial color="#9aa9bc" roughness={0.9} />
      </mesh>
    </group>
  );
}


function SalesStageColumn({
  label,
  count,
  value,
  accent,
  active = false,
  x,
  z = 0,
  height = 1,
}: {
  label: string;
  count: number | string;
  value?: string;
  accent: string;
  active?: boolean;
  x: number;
  z?: number;
  height?: number;
}) {
  const towerHeight = 0.9 + height * 0.22;

  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 0.05, 0]}>
        <boxGeometry args={[1.95, 0.18, 1.45]} />
        <meshStandardMaterial color="#e9eff6" roughness={0.96} />
      </mesh>

      <mesh position={[0, towerHeight / 2 + 0.12, 0]}>
        <boxGeometry args={[1.34, towerHeight, 0.96]} />
        <meshStandardMaterial color="#ffffff" roughness={0.92} metalness={0.02} />
      </mesh>

      <mesh position={[0, towerHeight + 0.15, 0]}>
        <boxGeometry args={[1.34, 0.06, 0.96]} />
        <meshBasicMaterial color={accent} transparent opacity={active ? 0.34 : 0.18} />
      </mesh>

      <mesh position={[0, 0.22, 0]}>
        <boxGeometry args={[1.54, 0.12, 1.18]} />
        <meshStandardMaterial color="#dfe7f1" roughness={0.95} />
      </mesh>

      {active ? (
        <mesh position={[0, towerHeight / 2 + 0.12, 0]}>
          <boxGeometry args={[1.44, towerHeight + 0.12, 1.06]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.12} />
        </mesh>
      ) : null}

      <group position={[0, 0.28, 0.74]}>
        <DreiText
          position={[0, 0.32, 0]}
          fontSize={0.11}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          {label}
        </DreiText>

        <DreiText
          position={[0, 0.02, 0]}
          fontSize={0.24}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          {`${count}`}
        </DreiText>

        {value ? (
          <DreiText
            position={[0, -0.28, 0]}
            fontSize={0.095}
            color={accent}
            anchorX="center"
            anchorY="middle"
            maxWidth={1.8}
          >
            {value}
          </DreiText>
        ) : null}
      </group>
    </group>
  );
}

function SalesBot({
  x,
  z,
  label,
  role,
  active = false,
}: {
  x: number;
  z: number;
  label: string;
  role: string;
  active?: boolean;
}) {
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 0.08, 0]}>
        <boxGeometry args={[0.9, 0.12, 0.9]} />
        <meshStandardMaterial color="#dfe7f1" roughness={0.96} />
      </mesh>

      <mesh position={[0, 0.58, 0]}>
        <boxGeometry args={[0.34, 0.84, 0.34]} />
        <meshStandardMaterial color="#f7f9fc" roughness={0.72} />
      </mesh>

      <mesh position={[0, 1.12, 0]}>
        <boxGeometry args={[0.32, 0.26, 0.26]} />
        <meshStandardMaterial color="#ffffff" roughness={0.66} />
      </mesh>

      <mesh position={[0, 1.12, 0.14]}>
        <planeGeometry args={[0.17, 0.09]} />
        <meshBasicMaterial color="#0b2545" />
      </mesh>

      <mesh position={[-0.035, 1.12, 0.145]}>
        <circleGeometry args={[0.012, 16]} />
        <meshBasicMaterial color="#22c55e" />
      </mesh>

      <mesh position={[0.035, 1.12, 0.145]}>
        <circleGeometry args={[0.012, 16]} />
        <meshBasicMaterial color="#22c55e" />
      </mesh>

      {active ? (
        <mesh position={[0, 0.5, 0]}>
          <torusGeometry args={[0.34, 0.035, 16, 40]} />
          <meshBasicMaterial color="#1a8aff" />
        </mesh>
      ) : null}

      <group position={[0, 0.12, 0.54]}>
        <DreiText
          position={[0, 0.18, 0]}
          fontSize={0.09}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={700}
        >
          {label}
        </DreiText>

        <DreiText
          position={[0, 0.01, 0]}
          fontSize={0.075}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          {role}
        </DreiText>
      </group>
    </group>
  );
}

function OperationsJobToken({
  x,
  z,
  tint = "#f59e0b",
}: {
  x: number;
  z: number;
  tint?: string;
}) {
  return (
    <group position={[x, 0.16, z]}>
      <mesh>
        <boxGeometry args={[0.34, 0.22, 0.24]} />
        <meshStandardMaterial color="#ffffff" roughness={0.9} />
      </mesh>
      <mesh position={[0, 0.12, 0]}>
        <boxGeometry args={[0.34, 0.03, 0.24]} />
        <meshBasicMaterial color={tint} transparent opacity={0.75} />
      </mesh>
    </group>
  );
}

function OperationsCrewPod({
  x,
  z,
  label,
  load,
  tint = "#1a8aff",
  active = false,
}: {
  x: number;
  z: number;
  label: string;
  load: string;
  tint?: string;
  active?: boolean;
}) {
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 0.08, 0]}>
        <boxGeometry args={[1.2, 0.16, 1]} />
        <meshStandardMaterial color="#dfe7f1" roughness={0.95} />
      </mesh>

      <mesh position={[0, 0.3, 0]}>
        <boxGeometry args={[0.86, 0.28, 0.62]} />
        <meshStandardMaterial color="#ffffff" roughness={0.92} />
      </mesh>

      <mesh position={[0, 0.47, 0]}>
        <boxGeometry args={[0.86, 0.04, 0.62]} />
        <meshBasicMaterial color={tint} transparent opacity={active ? 0.3 : 0.16} />
      </mesh>

      <mesh position={[-0.25, 0.52, 0]}>
        <cylinderGeometry args={[0.12, 0.12, 0.08, 20]} />
        <meshStandardMaterial color="#f8fafc" roughness={0.82} />
      </mesh>

      <mesh position={[0.25, 0.52, 0]}>
        <cylinderGeometry args={[0.12, 0.12, 0.08, 20]} />
        <meshStandardMaterial color="#f8fafc" roughness={0.82} />
      </mesh>

      <group position={[0, 0.04, 0.56]}>
        <DreiText
          position={[0, 0.16, 0]}
          fontSize={0.085}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={700}
        >
          {label}
        </DreiText>

        <DreiText
          position={[0, -0.02, 0]}
          fontSize={0.075}
          color={tint}
          anchorX="center"
          anchorY="middle"
        >
          {load}
        </DreiText>
      </group>
    </group>
  );
}

function OperationsStageColumn({
  label,
  count,
  value,
  accent,
  active = false,
  x,
  z = 0,
  height = 1,
}: {
  label: string;
  count: number | string;
  value?: string;
  accent: string;
  active?: boolean;
  x: number;
  z?: number;
  height?: number;
}) {
  const towerHeight = 1 + height * 0.28;

  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 0.05, 0]}>
        <boxGeometry args={[1.7, 0.18, 1.26]} />
        <meshStandardMaterial color="#eef3f8" roughness={0.96} />
      </mesh>

      <mesh position={[0, towerHeight / 2 + 0.14, 0]}>
        <boxGeometry args={[1.34, towerHeight, 0.94]} />
        <meshStandardMaterial color="#ffffff" roughness={0.93} />
      </mesh>

      <mesh position={[0, towerHeight + 0.17, 0]}>
        <boxGeometry args={[1.34, 0.05, 0.94]} />
        <meshBasicMaterial color={accent} transparent opacity={active ? 0.34 : 0.18} />
      </mesh>

      {active ? (
        <mesh position={[0, towerHeight / 2 + 0.14, 0]}>
          <boxGeometry args={[1.46, towerHeight + 0.08, 1.06]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.12} />
        </mesh>
      ) : null}

      <group position={[0, 0.26, 0.7]}>
        <DreiText
          position={[0, 0.34, 0]}
          fontSize={0.1}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          {label}
        </DreiText>

        <DreiText
          position={[0, 0.04, 0]}
          fontSize={0.22}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          {`${count}`}
        </DreiText>

        {value ? (
          <DreiText
            position={[0, -0.24, 0]}
            fontSize={0.09}
            color={accent}
            anchorX="center"
            anchorY="middle"
            maxWidth={1.8}
          >
            {value}
          </DreiText>
        ) : null}
      </group>
    </group>
  );
}

function OperationsBot({
  x,
  z,
  label,
  role,
  active = false,
  tint = "#1a8aff",
}: {
  x: number;
  z: number;
  label: string;
  role: string;
  active?: boolean;
  tint?: string;
}) {
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 0.08, 0]}>
        <boxGeometry args={[0.94, 0.14, 0.94]} />
        <meshStandardMaterial color="#dfe7f1" roughness={0.96} />
      </mesh>

      <mesh position={[0, 0.58, 0]}>
        <boxGeometry args={[0.36, 0.82, 0.36]} />
        <meshStandardMaterial color="#f7f9fc" roughness={0.72} />
      </mesh>

      <mesh position={[0, 1.12, 0]}>
        <boxGeometry args={[0.3, 0.24, 0.24]} />
        <meshStandardMaterial color="#ffffff" roughness={0.66} />
      </mesh>

      <mesh position={[0, 1.12, 0.125]}>
        <planeGeometry args={[0.16, 0.08]} />
        <meshBasicMaterial color="#0b2545" />
      </mesh>

      <mesh position={[-0.03, 1.12, 0.13]}>
        <circleGeometry args={[0.012, 16]} />
        <meshBasicMaterial color={tint} />
      </mesh>

      <mesh position={[0.03, 1.12, 0.13]}>
        <circleGeometry args={[0.012, 16]} />
        <meshBasicMaterial color={tint} />
      </mesh>

      {active ? (
        <mesh position={[0, 0.5, 0]}>
          <torusGeometry args={[0.34, 0.035, 16, 40]} />
          <meshBasicMaterial color="#1a8aff" />
        </mesh>
      ) : null}

      <group position={[0, 0.08, 0.58]}>
        <DreiText
          position={[0, 0.18, 0]}
          fontSize={0.09}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={700}
        >
          {label}
        </DreiText>

        <DreiText
          position={[0, 0, 0]}
          fontSize={0.075}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          {role}
        </DreiText>
      </group>
    </group>
  );
}

function FinanceStageColumn({
  label,
  count,
  value,
  accent,
  active = false,
  x,
  z = 0,
}: {
  label: string;
  count: number | string;
  value?: string;
  accent: string;
  active?: boolean;
  x: number;
  z?: number;
}) {
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 0.05, 0]}>
        <cylinderGeometry args={[1.05, 1.05, 0.12, 32]} />
        <meshStandardMaterial color="#eef3f8" roughness={0.96} />
      </mesh>

      <mesh position={[0, 0.11, 0]}>
        <cylinderGeometry args={[0.82, 0.82, 0.04, 32]} />
        <meshBasicMaterial
          color={accent}
          transparent
          opacity={active ? 0.28 : 0.14}
        />
      </mesh>

      {active ? (
        <mesh position={[0, 0.14, 0]}>
          <torusGeometry args={[1.1, 0.04, 16, 40]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.2} />
        </mesh>
      ) : null}

      <group position={[0, 0.02, 1.02]}>
        <DreiText
          position={[0, 0.2, 0]}
          fontSize={0.1}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          {label}
        </DreiText>

        <DreiText
          position={[0, -0.02, 0]}
          fontSize={0.22}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          {`${count}`}
        </DreiText>

        {value ? (
          <DreiText
            position={[0, -0.24, 0]}
            fontSize={0.085}
            color={accent}
            anchorX="center"
            anchorY="middle"
            maxWidth={1.9}
          >
            {value}
          </DreiText>
        ) : null}
      </group>
    </group>
  );
}

function FinanceContainer({
  position,
  active = false,
  onClick,
  cashOnHand,
  debtorDays,
}: {
  position: [number, number, number];
  active?: boolean;
  onClick?: () => void;
  cashOnHand: number;
  debtorDays: number;
}) {
  const invoices = Math.max(6, Math.round(cashOnHand / 380));
  const dueNow = Math.max(2, Math.round(invoices * 0.28));
  const overdue = Math.max(1, Math.round(debtorDays / 10));
  const settled = Math.max(1, Math.round(invoices * 0.62));

  return (
    <group
      position={position}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
    >
      <mesh position={[0, 0.05, 0]}>
        <boxGeometry args={[11.2, 0.24, 5.4]} />
        <meshStandardMaterial color="#e8eef6" roughness={0.96} />
      </mesh>

      <mesh position={[0, 0.28, 0]}>
        <boxGeometry args={[10.2, 0.22, 4.5]} />
        <meshStandardMaterial color="#ffffff" roughness={0.93} />
      </mesh>

      {active ? (
        <mesh position={[0, 0.42, 0]}>
          <boxGeometry args={[10.42, 0.05, 4.72]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.18} />
        </mesh>
      ) : null}

      {/* bank body */}
      <mesh position={[0, 1.05, -1.35]}>
        <boxGeometry args={[7.6, 1.5, 1.3]} />
        <meshStandardMaterial color="#f8fbff" roughness={0.94} />
      </mesh>

      <mesh position={[0, 2.0, -1.35]}>
        <boxGeometry args={[7.9, 0.5, 1.35]} />
        <meshStandardMaterial color="#eef3f8" roughness={0.9} />
      </mesh>

      <mesh position={[0, 2.34, -1.35]}>
        <boxGeometry args={[8.15, 0.08, 1.4]} />
        <meshBasicMaterial color="#d4af37" transparent opacity={0.9} />
      </mesh>

      <mesh position={[0, 2.42, -1.28]}>
        <boxGeometry args={[7.8, 0.08, 0.12]} />
        <meshBasicMaterial color="#d4af37" transparent opacity={0.9} />
      </mesh>

      <group position={[0, 1.6, -0.55]}>
        <DreiText
          fontSize={0.34}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          Finance Bank
        </DreiText>

        <DreiText
          position={[0, -0.3, 0]}
          fontSize={0.12}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          invoice · collect · settle · cash control
        </DreiText>

        <DreiText
          position={[0, -0.62, 0]}
          fontSize={0.16}
          color="#15803d"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          {fmtMoney(cashOnHand)} cash in bank
        </DreiText>
      </group>

      {/* central cash pad */}
      <mesh position={[0, 0.08, 1.82]}>
        <cylinderGeometry args={[2.05, 2.05, 0.12, 40]} />
        <meshStandardMaterial color="#ecfdf5" roughness={0.94} />
      </mesh>

      <group position={[0, 0.12, 1.82]}>
        <DreiText
          position={[0, 0.16, 0]}
          fontSize={0.11}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          cash in the bank
        </DreiText>

        <DreiText
          position={[0, -0.14, 0]}
          fontSize={0.24}
          color="#15803d"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          {fmtMoney(cashOnHand)}
        </DreiText>
      </group>

      {/* rear standing signs */}
      <FinanceSnapshotSheet
        x={-2.7}
        z={0.45}
        title="Cash"
        lines={["bank balance", fmtMoney(cashOnHand), "live liquidity"]}
      />
      <FinanceSnapshotSheet
        x={-0.9}
        z={0.45}
        title="Debtors"
        lines={["ageing", `${debtorDays} days`, "collections"]}
      />
      <FinanceSnapshotSheet
        x={0.9}
        z={0.45}
        title="Stock"
        lines={["inventory", "snapshot", "working capital"]}
      />
      <FinanceSnapshotSheet
        x={2.7}
        z={0.45}
        title="Costs"
        lines={["subs + spend", "equipment", "outgoings"]}
      />

      {/* floor circles instead of blocks */}
      <FinanceStageColumn
        x={-3.3}
        z={2.8}
        label="Invoices"
        count={invoices}
        value="raised"
        accent="#1a8aff"
        active={active}
      />
      <FinanceStageColumn
        x={-1.1}
        z={2.8}
        label="Due Now"
        count={dueNow}
        value="chase today"
        accent="#f59e0b"
        active={active}
      />
      <FinanceStageColumn
        x={1.1}
        z={2.8}
        label="Settled"
        count={settled}
        value="cash received"
        accent="#22c55e"
        active={active}
      />
      <FinanceStageColumn
        x={3.3}
        z={2.8}
        label="Overdue"
        count={overdue}
        value="at risk"
        accent="#ef4444"
        active={active}
      />
    </group>
  );
}

function FinanceSnapshotSheet({
  x,
  z,
  title,
  lines,
  tint = "#d4af37",
}: {
  x: number;
  z: number;
  title: string;
  lines: string[];
  tint?: string;
}) {
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 1.45, 0]}>
        <boxGeometry args={[1.15, 2.65, 0.18]} />
        <meshStandardMaterial color="#f8fbff" roughness={0.94} />
      </mesh>

      <mesh position={[0, 2.72, 0.02]}>
        <boxGeometry args={[1.15, 0.08, 0.08]} />
        <meshBasicMaterial color={tint} transparent opacity={0.85} />
      </mesh>

      <group position={[0, 2.18, 0.12]}>
        <DreiText
          position={[0, 0.2, 0]}
          fontSize={0.11}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
          maxWidth={0.95}
        >
          {title}
        </DreiText>

        {lines.map((line, i) => (
          <DreiText
            key={i}
            position={[0, -0.08 - i * 0.18, 0]}
            fontSize={0.07}
            color="#64748b"
            anchorX="center"
            anchorY="middle"
            maxWidth={0.92}
          >
            {line}
          </DreiText>
        ))}
      </group>
    </group>
  );
}

function SupportStageColumn({
  label,
  count,
  value,
  accent,
  active = false,
  x,
  z = 0,
  height = 1,
}: {
  label: string;
  count: number | string;
  value?: string;
  accent: string;
  active?: boolean;
  x: number;
  z?: number;
  height?: number;
}) {
  const towerHeight = 0.95 + height * 0.24;

  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 0.05, 0]}>
        <boxGeometry args={[1.75, 0.18, 1.24]} />
        <meshStandardMaterial color="#eef3f8" roughness={0.96} />
      </mesh>

      <mesh position={[0, towerHeight / 2 + 0.14, 0]}>
        <boxGeometry args={[1.34, towerHeight, 0.92]} />
        <meshStandardMaterial color="#ffffff" roughness={0.93} />
      </mesh>

      <mesh position={[0, towerHeight + 0.17, 0]}>
        <boxGeometry args={[1.34, 0.05, 0.92]} />
        <meshBasicMaterial color={accent} transparent opacity={active ? 0.34 : 0.18} />
      </mesh>

      {active ? (
        <mesh position={[0, towerHeight / 2 + 0.14, 0]}>
          <boxGeometry args={[1.46, towerHeight + 0.08, 1.04]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.12} />
        </mesh>
      ) : null}

      <group position={[0, 0.26, 0.7]}>
        <DreiText
          position={[0, 0.34, 0]}
          fontSize={0.1}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          {label}
        </DreiText>

        <DreiText
          position={[0, 0.04, 0]}
          fontSize={0.22}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          {`${count}`}
        </DreiText>

        {value ? (
          <DreiText
            position={[0, -0.24, 0]}
            fontSize={0.09}
            color={accent}
            anchorX="center"
            anchorY="middle"
            maxWidth={1.9}
          >
            {value}
          </DreiText>
        ) : null}
      </group>
    </group>
  );
}

function SupportAgent({
  x,
  z,
  label,
  role,
  active = false,
  tint = "#22c55e",
}: {
  x: number;
  z: number;
  label: string;
  role: string;
  active?: boolean;
  tint?: string;
}) {
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 0.08, 0]}>
        <boxGeometry args={[0.94, 0.14, 0.94]} />
        <meshStandardMaterial color="#dfe7f1" roughness={0.96} />
      </mesh>

      <mesh position={[0, 0.58, 0]}>
        <boxGeometry args={[0.36, 0.82, 0.36]} />
        <meshStandardMaterial color="#f7f9fc" roughness={0.72} />
      </mesh>

      <mesh position={[0, 1.12, 0]}>
        <boxGeometry args={[0.3, 0.24, 0.24]} />
        <meshStandardMaterial color="#ffffff" roughness={0.66} />
      </mesh>

      <mesh position={[0, 1.12, 0.125]}>
        <planeGeometry args={[0.16, 0.08]} />
        <meshBasicMaterial color="#0b2545" />
      </mesh>

      <mesh position={[-0.03, 1.12, 0.13]}>
        <circleGeometry args={[0.012, 16]} />
        <meshBasicMaterial color={tint} />
      </mesh>

      <mesh position={[0.03, 1.12, 0.13]}>
        <circleGeometry args={[0.012, 16]} />
        <meshBasicMaterial color={tint} />
      </mesh>

      {active ? (
        <mesh position={[0, 0.5, 0]}>
          <torusGeometry args={[0.34, 0.035, 16, 40]} />
          <meshBasicMaterial color="#1a8aff" />
        </mesh>
      ) : null}

      <group position={[0, 0.08, 0.58]}>
        <DreiText
          position={[0, 0.18, 0]}
          fontSize={0.09}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={700}
        >
          {label}
        </DreiText>

        <DreiText
          position={[0, 0, 0]}
          fontSize={0.075}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          {role}
        </DreiText>
      </group>
    </group>
  );
}

function SupportContainer({
  position,
  active = false,
  onClick,
  retainedPct,
  demandRisk,
}: {
  position: [number, number, number];
  active?: boolean;
  onClick?: () => void;
  retainedPct: number;
  demandRisk: string;
}) {
  const openTickets = Math.max(6, Math.round((100 - retainedPct) * 0.22));
  const queued = Math.max(4, Math.round(openTickets * 0.7));
  const resolved = Math.max(8, Math.round(retainedPct * 0.12));
  const escalated = Math.max(1, Math.round(openTickets * 0.22));

  const riskTone =
    demandRisk.toLowerCase() === "low"
      ? "#22c55e"
      : demandRisk.toLowerCase() === "medium"
        ? "#f59e0b"
        : "#ef4444";

  return (
    <group
      position={position}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
    >
      <mesh position={[0, 0.05, 0]}>
        <boxGeometry args={[10.8, 0.24, 5.2]} />
        <meshStandardMaterial color="#e8eef6" roughness={0.96} />
      </mesh>

      <mesh position={[0, 0.28, 0]}>
        <boxGeometry args={[9.8, 0.22, 4.32]} />
        <meshStandardMaterial color="#ffffff" roughness={0.93} />
      </mesh>

      {active ? (
        <mesh position={[0, 0.42, 0]}>
          <boxGeometry args={[10.02, 0.05, 4.54]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.18} />
        </mesh>
      ) : null}

      {/* rear wall */}
      <mesh position={[0, 1.1, -1.35]}>
        <boxGeometry args={[7.4, 1.4, 1.2]} />
        <meshStandardMaterial color="#f8fbff" roughness={0.94} />
      </mesh>

      <mesh position={[0, 2.0, -1.35]}>
        <boxGeometry args={[7.7, 0.48, 1.28]} />
        <meshStandardMaterial color="#eef3f8" roughness={0.9} />
      </mesh>

      <mesh position={[0, 2.32, -1.35]}>
        <boxGeometry args={[7.95, 0.08, 1.34]} />
        <meshBasicMaterial color="#22c55e" transparent opacity={0.85} />
      </mesh>

      {/* title */}
      <group position={[0, 1.58, -0.62]}>
        <DreiText
          fontSize={0.36}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          Support Hub
        </DreiText>

        <DreiText
          position={[0, -0.3, 0]}
          fontSize={0.12}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          triage · resolve · escalate · retain
        </DreiText>

        <DreiText
          position={[0, -0.62, 0]}
          fontSize={0.15}
          color="#22c55e"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          {`${retainedPct}% retained`}
        </DreiText>
      </group>

      {/* low floor stage pads */}
      <SupportStageColumn
        x={-3.25}
        z={2.85}
        label="Open"
        count={openTickets}
        value="new tickets"
        accent="#1a8aff"
        active={active}
      />
      <SupportStageColumn
        x={-1.05}
        z={2.85}
        label="Queued"
        count={queued}
        value="awaiting reply"
        accent="#f59e0b"
        active={active}
      />
      <SupportStageColumn
        x={1.15}
        z={2.85}
        label="Resolved"
        count={resolved}
        value="closed fast"
        accent="#22c55e"
        active={active}
      />
      <SupportStageColumn
        x={3.35}
        z={2.85}
        label="Escalated"
        count={escalated}
        value="needs intervention"
        accent="#ef4444"
        active={active}
      />

      {/* retention / health pad */}
      <mesh position={[0, 0.08, 1.55]}>
        <cylinderGeometry args={[2.1, 2.1, 0.12, 40]} />
        <meshStandardMaterial color="#ecfdf5" roughness={0.94} />
      </mesh>

      <group position={[0, 0.12, 1.55]}>
        <DreiText
          position={[0, 0.16, 0]}
          fontSize={0.11}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          customer health
        </DreiText>

        <DreiText
          position={[0, -0.14, 0]}
          fontSize={0.21}
          color="#22c55e"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          {`${retainedPct}%`}
        </DreiText>
      </group>

      {/* support agents */}
      <SupportAgent x={-2.25} z={0.55} label="Inbox Bot" role="triage" active={active} tint="#1a8aff" />
      <SupportAgent x={-0.75} z={0.55} label="Agent" role="resolution" active={active} tint="#f59e0b" />
      <SupportAgent x={0.75} z={0.55} label="Care" role="retention" active={active} tint="#22c55e" />
      <SupportAgent x={2.25} z={0.55} label="Escalation" role="complex case" active={active} tint="#ef4444" />

      {/* flow lines */}
      <DreiLine
        points={[
          new THREE.Vector3(-2.1, 0.3, 2.05),
          new THREE.Vector3(-0.2, 0.3, 2.05),
          new THREE.Vector3(1.9, 0.3, 2.05),
        ]}
        color="#3b82f6"
        lineWidth={1}
        transparent
        opacity={0.45}
      />

      <DreiLine
        points={[
          new THREE.Vector3(1.8, 0.3, 2.05),
          new THREE.Vector3(3.0, 0.3, 2.35),
        ]}
        color="#ef4444"
        lineWidth={1}
        transparent
        opacity={0.45}
      />

      {/* demand risk */}
      <group position={[0, 0.15, 3.15]}>
        <DreiText
          position={[0, 0.12, 0]}
          fontSize={0.1}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          demand risk
        </DreiText>
        <DreiText
          position={[0, -0.12, 0]}
          fontSize={0.16}
          color={riskTone}
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          {demandRisk.toUpperCase()}
        </DreiText>
      </group>
    </group>
  );
}


function OperationsContainer({
  position,
  active = false,
  onClick,
  backlog,
  blockedJobs,
  turnaround,
  fulfilmentRate,
  capacityUsed,
}: {
  position: [number, number, number];
  active?: boolean;
  onClick?: () => void;
  backlog: number;
  blockedJobs: number;
  turnaround: number;
  fulfilmentRate: number;
  capacityUsed: number;
}) {
  const scheduled = Math.max(1, Math.round(backlog * 0.72));
  const assigned = Math.max(1, Math.round(scheduled * 0.82));
  const inProgress = Math.max(1, Math.round(assigned * 0.78));
  const completed = Math.max(1, Math.round((inProgress - blockedJobs) * (fulfilmentRate / 100)));
  const blocked = Math.max(1, blockedJobs);

  return (
    <group
      position={position}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
    >
      <mesh position={[0, 0.05, 0]}>
        <boxGeometry args={[11.4, 0.24, 5.6]} />
        <meshStandardMaterial color="#e8eef6" roughness={0.96} />
      </mesh>

      <mesh position={[0, 0.28, 0]}>
        <boxGeometry args={[10.4, 0.22, 4.72]} />
        <meshStandardMaterial color="#ffffff" roughness={0.93} />
      </mesh>

      <mesh position={[0, 0.42, 0]}>
        <boxGeometry args={[10.4, 0.04, 4.72]} />
        <meshBasicMaterial color="#f59e0b" transparent opacity={active ? 0.32 : 0.16} />
      </mesh>

      {active ? (
        <mesh position={[0, 0.47, 0]}>
          <boxGeometry args={[10.6, 0.05, 4.92]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.18} />
        </mesh>
      ) : null}

      <mesh position={[0, 1.32, -2.28]}>
        <boxGeometry args={[8.6, 2.2, 0.18]} />
        <meshStandardMaterial color="#f8fbff" roughness={0.94} />
      </mesh>

      <mesh position={[0, 2.36, -2.22]}>
        <boxGeometry args={[8.6, 0.08, 0.08]} />
        <meshBasicMaterial color="#f59e0b" transparent opacity={0.32} />
      </mesh>

      <group position={[0, 1.28, -2.05]}>
        <DreiText
          position={[0, 0.56, 0]}
          fontSize={0.38}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          Operations Unit
        </DreiText>

        <DreiText
          position={[0, 0.16, 0]}
          fontSize={0.13}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          schedule · dispatch · fulfil · complete
        </DreiText>

        <DreiText
          position={[0, -0.22, 0]}
          fontSize={0.14}
          color="#f59e0b"
          anchorX="center"
          anchorY="middle"
        >
          {`${fulfilmentRate}% fulfilment · ${turnaround}d turnaround`}
        </DreiText>
      </group>

      <OperationsStageColumn
        x={-3.45}
        label="Backlog"
        count={backlog}
        value="awaiting slot"
        accent="#f59e0b"
        active={active}
        height={6.8}
      />
      <OperationsStageColumn
        x={-1.15}
        label="Scheduled"
        count={scheduled}
        value="time booked"
        accent="#1a8aff"
        active={active}
        height={5.6}
      />
      <OperationsStageColumn
        x={1.15}
        label="Assigned"
        count={assigned}
        value="crew allocated"
        accent="#8b5cf6"
        active={active}
        height={4.8}
      />
      <OperationsStageColumn
        x={3.45}
        label="Complete"
        count={completed}
        value="to finance"
        accent="#22c55e"
        active={active}
        height={3.2}
      />

      <OperationsStageColumn
        x={3.45}
        z={-1.9}
        label="Blocked"
        count={blocked}
        value="issue / rework"
        accent="#ef4444"
        active={active}
        height={2.8}
      />

      <ConveyorSegment x={0} z={1.35} width={8.1} />

      <group position={[0, 0.36, 1.36]}>
        <mesh position={[-2.45, 0, 0]}>
          <boxGeometry args={[0.84, 0.1, 0.16]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>
        <mesh position={[-1.94, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.18, 0.32, 3]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>

        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[0.84, 0.1, 0.16]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>
        <mesh position={[0.5, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.18, 0.32, 3]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>

        <mesh position={[2.45, 0, 0]}>
          <boxGeometry args={[0.84, 0.1, 0.16]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>
        <mesh position={[2.95, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.18, 0.32, 3]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>
      </group>

      <DreiLine
        points={[
          new THREE.Vector3(2.9, 0.36, 1.1),
          new THREE.Vector3(3.45, 0.36, 0.18),
          new THREE.Vector3(3.45, 0.36, -1.28),
        ]}
        color="#ef4444"
        lineWidth={1}
        transparent
        opacity={0.5}
      />

      <OperationsCrewPod x={-2.5} z={-2.25} label="Crew A" load="78% load" tint="#1a8aff" active={active} />
      <OperationsCrewPod x={0} z={-2.25} label="Crew B" load="64% load" tint="#8b5cf6" active={active} />
      <OperationsCrewPod x={2.5} z={-2.25} label="Crew C" load="91% load" tint="#22c55e" active={active} />

      <OperationsBot x={-2.8} z={-3.2} label="Scheduler" role="slotting" active={active} tint="#1a8aff" />
      <OperationsBot x={-0.9} z={-3.2} label="Dispatch" role="assignment" active={active} tint="#8b5cf6" />
      <OperationsBot x={1.0} z={-3.2} label="Fulfilment" role="delivery" active={active} tint="#22c55e" />
      <OperationsBot x={2.9} z={-3.2} label="Rework" role="issue fix" active={active} tint="#ef4444" />

      <OperationsJobToken x={-3.35} z={1.15} tint="#f59e0b" />
      <OperationsJobToken x={-2.7} z={1.15} tint="#f59e0b" />
      <OperationsJobToken x={-1.0} z={1.15} tint="#1a8aff" />
      <OperationsJobToken x={-0.35} z={1.15} tint="#1a8aff" />
      <OperationsJobToken x={1.05} z={1.15} tint="#8b5cf6" />
      <OperationsJobToken x={1.7} z={1.15} tint="#8b5cf6" />
      <OperationsJobToken x={3.1} z={1.15} tint="#22c55e" />

      <group position={[0, 0.18, 0.05]}>
        <DreiText
          position={[0, 0.12, 0]}
          fontSize={0.11}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          capacity used
        </DreiText>
        <DreiText
          position={[0, -0.14, 0]}
          fontSize={0.18}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          {`${capacityUsed}%`}
        </DreiText>
      </group>
    </group>
  );
}

function SalesContainer({
  position,
  active = false,
  onClick,
  conversionRate,
  orders,
}: {
  position: [number, number, number];
  active?: boolean;
  onClick?: () => void;
  conversionRate: number;
  orders: number;
}) {
  const qualified = Math.max(1, Math.round(orders * 0.34));
  const quoted = Math.max(1, Math.round(qualified * 0.52));
  const followup = Math.max(1, Math.round(quoted * 0.46));
  const won = Math.max(1, Math.round((quoted + followup) * (conversionRate / 100)));
  const stale = Math.max(1, followup - won);

  return (
    <group
      position={position}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
    >
      {/* main platform */}
      <mesh position={[0, 0.05, 0]}>
        <boxGeometry args={[10.2, 0.24, 4.9]} />
        <meshStandardMaterial color="#e8eef6" roughness={0.96} />
      </mesh>

      <mesh position={[0, 0.26, 0]}>
        <boxGeometry args={[9.25, 0.18, 4.05]} />
        <meshStandardMaterial color="#ffffff" roughness={0.93} />
      </mesh>

      <mesh position={[0, 0.38, 0]}>
        <boxGeometry args={[9.25, 0.04, 4.05]} />
        <meshBasicMaterial color="#22c55e" transparent opacity={active ? 0.3 : 0.15} />
      </mesh>

      {active ? (
        <mesh position={[0, 0.43, 0]}>
          <boxGeometry args={[9.42, 0.05, 4.22]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.18} />
        </mesh>
      ) : null}

      {/* rear title wall moved back behind towers */}
      <mesh position={[0, 1.2, -2.05]}>
        <boxGeometry args={[7.2, 1.95, 0.18]} />
        <meshStandardMaterial color="#f8fbff" roughness={0.94} />
      </mesh>

      <mesh position={[0, 2.12, -2.0]}>
        <boxGeometry args={[7.2, 0.08, 0.08]} />
        <meshBasicMaterial color="#22c55e" transparent opacity={0.3} />
      </mesh>

      <group position={[0, 1.18, -1.86]}>
        <DreiText
          position={[0, 0.5, 0]}
          fontSize={0.38}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          Sales Unit
        </DreiText>

        <DreiText
          position={[0, 0.12, 0]}
          fontSize={0.14}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          qualify · quote · follow-up · close
        </DreiText>

        <DreiText
          position={[0, -0.24, 0]}
          fontSize={0.15}
          color="#22c55e"
          anchorX="center"
          anchorY="middle"
        >
          {`${fmtPct(conversionRate)} close rate`}
        </DreiText>
      </group>

      {/* stage towers - taller */}
      <SalesStageColumn
        x={-3.2}
        label="Inbound"
        count={orders}
        value="new leads"
        accent="#1a8aff"
        active={active}
        height={7}
      />
      <SalesStageColumn
        x={-1.1}
        label="Qualified"
        count={qualified}
        value="fit checked"
        accent="#22c55e"
        active={active}
        height={5.2}
      />
      <SalesStageColumn
        x={1.1}
        label="Quoted"
        count={quoted}
        value="awaiting reply"
        accent="#f59e0b"
        active={active}
        height={4}
      />
      <SalesStageColumn
        x={3.2}
        label="Won"
        count={won}
        value="ready for ops"
        accent="#10b981"
        active={active}
        height={2.9}
      />

      <SalesStageColumn
        x={3.2}
        z={-1.7}
        label="Stale"
        count={stale}
        value="needs follow-up"
        accent="#ef4444"
        active={active}
        height={2.6}
      />

      {/* agent row */}
      <SalesBot x={-3.1} z={-1.95} label="Inbound Bot" role="triage" active={active} />
      <SalesBot x={-1.05} z={-1.95} label="Qualifier" role="fit + scope" active={active} />
      <SalesBot x={1.05} z={-1.95} label="Closer" role="quote to win" active={active} />
      <SalesBot x={3.1} z={-1.95} label="Follow-up" role="stale recovery" active={active} />

      {/* internal conveyor */}
      <ConveyorSegment x={0} z={1.15} width={7.2} />

      {/* stage flow arrows */}
      <group position={[0, 0.34, 1.18]}>
        <mesh position={[-2.15, 0, 0]}>
          <boxGeometry args={[0.8, 0.09, 0.16]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>
        <mesh position={[-1.67, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.18, 0.32, 3]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>

        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[0.8, 0.09, 0.16]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>
        <mesh position={[0.48, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.18, 0.32, 3]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>

        <mesh position={[2.15, 0, 0]}>
          <boxGeometry args={[0.8, 0.09, 0.16]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>
        <mesh position={[2.63, 0, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.18, 0.32, 3]} />
          <meshBasicMaterial color="#3b82f6" />
        </mesh>
      </group>

      {/* stale branch */}
      <DreiLine
        points={[
          new THREE.Vector3(2.6, 0.34, 0.9),
          new THREE.Vector3(3.1, 0.34, 0.1),
          new THREE.Vector3(3.1, 0.34, -1.1),
        ]}
        color="#ef4444"
        lineWidth={1}
        transparent
        opacity={0.5}
      />
    </group>
  );
}

function FunnelFrame({
  position,
  active = false,
  onClick,
}: {
  position: [number, number, number];
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <group position={position}>
      <mesh
        position={[0, 1.5, 0]}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.();
        }}
      >
        <cylinderGeometry args={[2.15, 0.78, 2.95, 32, 1, true]} />
        <meshStandardMaterial
          color="#7dd3fc"
          transparent
          opacity={0.42}
          roughness={0.32}
          metalness={0.02}
          side={THREE.DoubleSide}
        />
      </mesh>

      <mesh position={[0, 2.84, 0]}>
        <cylinderGeometry args={[2.18, 2.18, 0.09, 32]} />
        <meshBasicMaterial color="#67e8f9" transparent opacity={0.62} />
      </mesh>

      <mesh position={[0, 0.26, 0]}>
        <cylinderGeometry args={[0.52, 0.52, 0.1, 24]} />
        <meshBasicMaterial color="#6366f1" transparent opacity={0.82} />
      </mesh>

      {active ? (
        <mesh position={[0, 2.92, 0]}>
          <torusGeometry args={[2.28, 0.06, 18, 56]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.55} />
        </mesh>
      ) : null}

      <mesh position={[0, 3.82, 0]} rotation={[0, 0, -Math.PI / 2]}>
        <coneGeometry args={[0.42, 1.1, 3]} />
        <meshBasicMaterial color="#3b82f6" />
      </mesh>

      <mesh position={[0, 4.64, 0]}>
        <boxGeometry args={[0.22, 1.45, 0.22]} />
        <meshBasicMaterial color="#3b82f6" />
      </mesh>

      <DreiText
        position={[0, 6.08, 0.1]}
        fontSize={0.6}
        color="#0f172a"
        anchorX="center"
        anchorY="middle"
        fontWeight={800}
      >
        Traffic
      </DreiText>

      <DreiText
        position={[0, 5.34, 0.1]}
        fontSize={0.18}
        color="#475569"
        anchorX="center"
        anchorY="middle"
      >
        multi-channel intake
      </DreiText>
    </group>
  );
}

function ChannelSourceBox({
  channel,
  active = false,
  onClick,
}: {
  channel: ChannelInput;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <group position={[channel.x, channel.y, channel.z]}>
      <mesh
        onClick={(e) => {
          e.stopPropagation();
          onClick?.();
        }}
      >
        <boxGeometry args={[2.9, 1.2, 1.8]} />
        <meshStandardMaterial color="#ffffff" roughness={0.94} />
      </mesh>

      <mesh position={[0, 0.62, 0]}>
        <boxGeometry args={[2.9, 0.05, 1.8]} />
        <meshBasicMaterial
          color={channel.accent}
          transparent
          opacity={active ? 0.32 : 0.16}
        />
      </mesh>

      <mesh position={[0, -0.72, 0]}>
        <boxGeometry args={[2.55, 0.12, 1.35]} />
        <meshStandardMaterial color="#e8eef6" roughness={0.96} />
      </mesh>

      <mesh position={[1.52, -0.05, 0]}>
        <boxGeometry args={[0.12, 0.42, 0.5]} />
        <meshStandardMaterial color="#dbe7f3" roughness={0.88} />
      </mesh>

      <mesh position={[1.66, -0.05, 0]}>
        <boxGeometry args={[0.18, 0.28, 0.36]} />
        <meshStandardMaterial color="#c7d6e6" roughness={0.88} />
      </mesh>

      {active ? (
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[3.04, 1.3, 1.94]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.13} />
        </mesh>
      ) : null}

      <FacingLabel
        title={channel.label}
        subtitle={channel.subtitle}
        value={channel.value}
        accent={channel.accent}
        y={-0.02}
        z={0.98}
      />
    </group>
  );
}

function FlowLeakCallout({
  x,
  z,
  label,
  value,
  tone = "#ef4444",
}: {
  x: number;
  z: number;
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <group position={[x, 0.26, z]}>
      <mesh>
        <boxGeometry args={[2.72, 0.72, 0.96]} />
        <meshStandardMaterial color="#ffffff" roughness={0.94} />
      </mesh>

      <mesh position={[0, 0.38, 0]}>
        <boxGeometry args={[2.72, 0.03, 0.96]} />
        <meshBasicMaterial color={tone} transparent opacity={0.14} />
      </mesh>

      <group position={[0, 0.02, 0.55]}>
        <DreiText
          position={[0, 0.16, 0]}
          fontSize={0.1}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          {label}
        </DreiText>

        <DreiText
          position={[0, -0.1, 0]}
          fontSize={0.14}
          color={tone}
          anchorX="center"
          anchorY="middle"
        >
          {value}
        </DreiText>
      </group>
    </group>
  );
}

function MarketingFlywheel({
  position,
  active = false,
  onClick,
  pulseValue,
  scale = 1,
}: {
  position: [number, number, number];
  active?: boolean;
  onClick?: () => void;
  pulseValue?: string;
  scale?: number;
}) {
  const wheelRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const spokesRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (wheelRef.current) wheelRef.current.rotation.z += delta * 0.6;
    if (ringRef.current) ringRef.current.rotation.z -= delta * 0.22;
    if (spokesRef.current) spokesRef.current.rotation.z += delta * 0.6;
  });

  return (
    <group
      position={position}
      scale={scale}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
    >
      {active ? (
        <mesh position={[0, 0.12, 0.04]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[2.9, 0.1, 20, 80]} />
          <meshBasicMaterial color="#1a8aff" transparent opacity={0.8} />
        </mesh>
      ) : null}

      <mesh position={[0, -1.15, 0]}>
        <boxGeometry args={[5.4, 0.36, 2.5]} />
        <meshStandardMaterial color="#d9e7f5" roughness={0.92} />
      </mesh>

      <mesh position={[0, -0.92, 0]}>
        <boxGeometry args={[4.7, 0.08, 2.08]} />
        <meshBasicMaterial color="#b8d4f2" transparent opacity={0.22} />
      </mesh>

      <mesh position={[-0.1, -0.14, -0.08]}>
        <boxGeometry args={[1.8, 1.48, 1.22]} />
        <meshStandardMaterial color="#c7d6e6" roughness={0.9} />
      </mesh>

      <mesh position={[0, 0.1, 0.08]} rotation={[0, Math.PI / 2, 0]}>
        <cylinderGeometry args={[0.16, 0.16, 1.2, 20]} />
        <meshStandardMaterial color="#b9cadb" roughness={0.82} />
      </mesh>

      <mesh ref={wheelRef} position={[0, 0.15, 0.15]}>
        <cylinderGeometry args={[2.25, 2.25, 0.52, 48]} />
        <meshStandardMaterial color="#eef4fb" roughness={0.82} metalness={0.08} />
      </mesh>

      <mesh position={[0, 0.15, 0.15]}>
        <cylinderGeometry args={[2.32, 2.32, 0.1, 48]} />
        <meshBasicMaterial color="#d9e8f7" transparent opacity={0.75} />
      </mesh>

      <mesh ref={ringRef} position={[0, 0.15, 0.44]}>
        <torusGeometry args={[1.56, 0.18, 18, 60]} />
        <meshStandardMaterial color="#dbe7f3" roughness={0.76} metalness={0.06} />
      </mesh>

      <mesh position={[0, 0.15, 0.56]}>
        <cylinderGeometry args={[0.52, 0.52, 0.78, 24]} />
        <meshStandardMaterial color="#bfd7f2" roughness={0.72} />
      </mesh>

      <group ref={spokesRef} position={[0, 0.15, 0.52]}>
        {[0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2].map((r, i) => (
          <mesh key={i} rotation={[0, 0, r]}>
            <boxGeometry args={[2.45, 0.18, 0.12]} />
            <meshStandardMaterial color="#d7e4f1" roughness={0.86} />
          </mesh>
        ))}
      </group>

      <mesh position={[2.95, 0.08, 0.15]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.2, 0.2, 1.55, 20]} />
        <meshStandardMaterial color="#c7d6e6" roughness={0.88} />
      </mesh>

      <mesh position={[3.9, 0.08, 0.15]} rotation={[0, 0, -Math.PI / 2]}>
        <coneGeometry args={[0.36, 0.86, 4]} />
        <meshBasicMaterial color="#3b82f6" />
      </mesh>

      <mesh position={[-1.35, -1.42, 0]}>
        <boxGeometry args={[0.28, 0.2, 0.6]} />
        <meshStandardMaterial color="#c7d6e6" roughness={0.9} />
      </mesh>

      <mesh position={[1.35, -1.42, 0]}>
        <boxGeometry args={[0.28, 0.2, 0.6]} />
        <meshStandardMaterial color="#c7d6e6" roughness={0.9} />
      </mesh>

      <group position={[0, 3.15, 0.2]}>
        <DreiText
          fontSize={0.56}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          Marketing Engine
        </DreiText>

        <DreiText
          position={[0, -0.54, 0]}
          fontSize={0.15}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          campaigns · content · channel mix
        </DreiText>

        {pulseValue ? (
          <DreiText
            position={[0, -1.02, 0]}
            fontSize={0.15}
            color="#1a8aff"
            anchorX="center"
            anchorY="middle"
          >
            {pulseValue}
          </DreiText>
        ) : null}
      </group>
    </group>
  );
}

function Lemming({
  position,
  tint = "#2563eb",
}: {
  position: [number, number, number];
  tint?: string;
}) {
  return (
    <group position={position}>
      <mesh position={[0, 0.18, 0]}>
        <capsuleGeometry args={[0.08, 0.18, 4, 8]} />
        <meshStandardMaterial color="#60a5fa" roughness={0.84} />
      </mesh>

      <mesh position={[0, 0.42, 0]}>
        <sphereGeometry args={[0.09, 16, 16]} />
        <meshStandardMaterial color="#2563eb" roughness={0.82} />
      </mesh>

      <mesh position={[0, 0.42, 0.075]}>
        <planeGeometry args={[0.08, 0.04]} />
        <meshBasicMaterial color="#eff6ff" />
      </mesh>

      <mesh position={[-0.02, 0.42, 0.08]}>
        <circleGeometry args={[0.008, 12]} />
        <meshBasicMaterial color={tint} />
      </mesh>

      <mesh position={[0.02, 0.42, 0.08]}>
        <circleGeometry args={[0.008, 12]} />
        <meshBasicMaterial color={tint} />
      </mesh>

      <mesh position={[-0.035, 0.02, 0]}>
        <boxGeometry args={[0.03, 0.16, 0.03]} />
        <meshStandardMaterial color="#93c5fd" roughness={0.9} />
      </mesh>

      <mesh position={[0.035, 0.02, 0]}>
        <boxGeometry args={[0.03, 0.16, 0.03]} />
        <meshStandardMaterial color="#93c5fd" roughness={0.9} />
      </mesh>
    </group>
  );
}

function LemmingTrafficRunner({
  start,
  end,
  phase = 0,
  tint = "#2563eb",
}: {
  start: [number, number, number];
  end: [number, number, number];
  phase?: number;
  tint?: string;
}) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame(({ clock }) => {
    const t = (Math.sin(clock.elapsedTime * 1.35 + phase) + 1) / 2;
    const x = THREE.MathUtils.lerp(start[0], end[0], t);
    const y = THREE.MathUtils.lerp(start[1], end[1], t) + Math.sin(t * Math.PI) * 0.06;
    const z = THREE.MathUtils.lerp(start[2], end[2], t);

    if (groupRef.current) {
      groupRef.current.position.set(x, y, z);
      groupRef.current.rotation.y = Math.atan2(end[0] - start[0], end[2] - start[2]);
    }
  });

  return (
    <group ref={groupRef}>
      <Lemming position={[0, 0, 0]} tint={tint} />
    </group>
  );
}

function FallingLemming({
  start,
  depth = 2.4,
  phase = 0,
}: {
  start: [number, number, number];
  depth?: number;
  phase?: number;
}) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame(({ clock }) => {
    const t = (Math.sin(clock.elapsedTime * 1.1 + phase) + 1) / 2;
    const y = start[1] - t * depth;
    const x = start[0] + Math.sin(clock.elapsedTime * 1.8 + phase) * 0.06;
    const z = start[2];

    if (groupRef.current) {
      groupRef.current.position.set(x, y, z);
      groupRef.current.rotation.z = t * 1.2;
    }
  });

  return (
    <group ref={groupRef}>
      <Lemming position={[0, 0, 0]} tint="#ef4444" />
    </group>
  );
}

function TrafficLemmings({
  channelInputs,
  engineX,
  engineY,
  funnelX,
  funnelY,
  salesX,
  conversionRate,
}: {
  channelInputs: ChannelInput[];
  engineX: number;
  engineY: number;
  funnelX: number;
  funnelY: number;
  salesX: number;
  conversionRate: number;
}) {
  const channelRunners = useMemo(
    () =>
      channelInputs.map((channel, i) => ({
        key: channel.key,
        start: [channel.x + 1.85, channel.y - 0.55, channel.z] as [number, number, number],
        end: [engineX - 3.2, engineY - 0.15, channel.z * 0.28] as [number, number, number],
        phase: i * 0.55,
      })),
    [channelInputs, engineX, engineY],
  );

  const engineToFunnel = useMemo(
    () => [-0.48, -0.2, 0.14, 0.42].map((z, i) => ({ z, phase: i * 0.5 })),
    [],
  );

  const convertedCount = Math.max(1, Math.round((conversionRate / 100) * 5));
  const convertedOffsets = useMemo(
    () =>
      Array.from({ length: convertedCount }).map((_, i) => ({
        z: (i - (convertedCount - 1) / 2) * 0.22,
        phase: i * 0.7,
      })),
    [convertedCount],
  );

  const lostCount = Math.max(2, 5 - convertedCount);
  const lostOffsets = useMemo(
    () =>
      Array.from({ length: lostCount }).map((_, i) => ({
        x: funnelX - 0.3 + (i - (lostCount - 1) / 2) * 0.3,
        z: (i - (lostCount - 1) / 2) * 0.24,
        phase: i * 0.85,
      })),
    [funnelX, lostCount],
  );

  return (
    <>
      {channelRunners.map((entry) => (
        <LemmingTrafficRunner
          key={`channel-${entry.key}`}
          start={entry.start}
          end={entry.end}
          phase={entry.phase}
          tint="#2563eb"
        />
      ))}

      {engineToFunnel.map((entry, i) => (
        <LemmingTrafficRunner
          key={`engine-funnel-${i}`}
          start={[engineX + 3.9, engineY, entry.z]}
          end={[funnelX - 0.28, funnelY + 3.75, entry.z * 0.42]}
          phase={entry.phase}
          tint="#2563eb"
        />
      ))}

      {convertedOffsets.map((entry, i) => (
        <LemmingTrafficRunner
          key={`converted-${i}`}
          start={[funnelX + 0.18, funnelY + 0.64, entry.z]}
          end={[salesX - 2.55, 0.3, entry.z]}
          phase={entry.phase}
          tint="#22c55e"
        />
      ))}

      {lostOffsets.map((entry, i) => (
        <FallingLemming
          key={`lost-${i}`}
          start={[entry.x, funnelY + 0.88, entry.z]}
          depth={2.8}
          phase={entry.phase}
        />
      ))}
    </>
  );
}

function HrSupportOverlay({
  position,
  hrFloor,
  active = false,
  selectedInspectorTarget,
  onStageClick,
  onAgentClick,
}: {
  position: [number, number, number];
  hrFloor?: HRFloorState;
  active?: boolean;
  selectedInspectorTarget?: BoardroomInspectorTarget | null;
  onStageClick?: (stageId: string) => void;
  onAgentClick?: (agentId: string) => void;
}) {
  const stages = hrFloor?.stages ?? [];
  const agents = hrFloor?.agents ?? [];

  const stageA = stages[0];
  const stageB = stages[1];
  const stageC = stages[2];

  const agentA = agents[0];
  const agentB = agents[1];
  const agentC = agents[2];

  return (
    <group position={position}>
      <mesh position={[0, 0.05, 0]}>
        <boxGeometry args={[9.6, 0.2, 3.4]} />
        <meshStandardMaterial color="#e8eef6" roughness={0.96} />
      </mesh>

      <mesh position={[0, 0.24, 0]}>
        <boxGeometry args={[8.8, 0.18, 2.7]} />
        <meshStandardMaterial color="#ffffff" roughness={0.93} />
      </mesh>

      <mesh position={[0, 0.36, 0]}>
        <boxGeometry args={[8.8, 0.04, 2.7]} />
        <meshBasicMaterial color="#8b5cf6" transparent opacity={active ? 0.28 : 0.14} />
      </mesh>

      <group position={[0, 0.2, -1.45]}>
        <DreiText
          position={[0, 0.22, 0]}
          fontSize={0.18}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={800}
        >
          HR / Admin Overlay
        </DreiText>

        <DreiText
          position={[0, 0, 0]}
          fontSize={0.09}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
        >
          onboarding · documents · compliance
        </DreiText>
      </group>

      {[stageA, stageB, stageC].map((stage, index) => {
        if (!stage) return null;
        const x = -2.6 + index * 2.6;
        const isActive =
          selectedInspectorTarget?.kind === "hr_stage" &&
          "stageId" in selectedInspectorTarget &&
          selectedInspectorTarget.stageId === stage.id;

        return (
          <group key={stage.id} position={[x, 0, -0.1]}>
            <mesh
              position={[0, 0.1, 0]}
              onClick={(e) => {
                e.stopPropagation();
                onStageClick?.(stage.id);
              }}
            >
              <cylinderGeometry args={[0.7, 0.7, 0.12, 24]} />
              <meshStandardMaterial color="#ffffff" roughness={0.92} />
            </mesh>

            <mesh position={[0, 0.16, 0]}>
              <cylinderGeometry args={[0.7, 0.7, 0.02, 24]} />
              <meshBasicMaterial
                color={seatStateColor(stage.state)}
                transparent
                opacity={isActive ? 0.28 : 0.14}
              />
            </mesh>

            {isActive ? (
              <mesh position={[0, 0.18, 0]}>
                <torusGeometry args={[0.78, 0.03, 16, 40]} />
                <meshBasicMaterial color="#1a8aff" />
              </mesh>
            ) : null}

            <group position={[0, 0.18, 0.72]}>
              <DreiText
                position={[0, 0.12, 0]}
                fontSize={0.09}
                color="#64748b"
                anchorX="center"
                anchorY="middle"
                maxWidth={1.4}
              >
                {stage.label}
              </DreiText>
              <DreiText
                position={[0, -0.08, 0]}
                fontSize={0.16}
                color="#0f172a"
                anchorX="center"
                anchorY="middle"
              >
                {`${stage.count}`}
              </DreiText>
            </group>
          </group>
        );
      })}

      {[agentA, agentB, agentC].map((agent, index) => {
        if (!agent) return null;
        const x = -2.6 + index * 2.6;
        const isActive =
          selectedInspectorTarget?.kind === "hr_agent" &&
          "agentId" in selectedInspectorTarget &&
          selectedInspectorTarget.agentId === agent.id;

        return (
          <group
            key={agent.id}
            position={[x, 0, 0.95]}
            onClick={(e) => {
              e.stopPropagation();
              onAgentClick?.(agent.id);
            }}
          >
            <mesh position={[0, 0.08, 0]}>
              <boxGeometry args={[0.88, 0.12, 0.88]} />
              <meshStandardMaterial color="#dfe7f1" roughness={0.96} />
            </mesh>

            <mesh position={[0, 0.54, 0]}>
              <boxGeometry args={[0.32, 0.72, 0.32]} />
              <meshStandardMaterial color="#f7f9fc" roughness={0.72} />
            </mesh>

            <mesh position={[0, 1, 0]}>
              <boxGeometry args={[0.28, 0.22, 0.22]} />
              <meshStandardMaterial color="#ffffff" roughness={0.66} />
            </mesh>

            <mesh position={[0, 1, 0.115]}>
              <planeGeometry args={[0.14, 0.07]} />
              <meshBasicMaterial color="#0b2545" />
            </mesh>

            <mesh position={[-0.03, 1, 0.12]}>
              <circleGeometry args={[0.01, 16]} />
              <meshBasicMaterial color="#8b5cf6" />
            </mesh>

            <mesh position={[0.03, 1, 0.12]}>
              <circleGeometry args={[0.01, 16]} />
              <meshBasicMaterial color="#8b5cf6" />
            </mesh>

            {isActive ? (
              <mesh position={[0, 0.5, 0]}>
                <torusGeometry args={[0.3, 0.03, 16, 40]} />
                <meshBasicMaterial color="#1a8aff" />
              </mesh>
            ) : null}

            <group position={[0, 0.1, 0.58]}>
              <DreiText
                position={[0, 0.14, 0]}
                fontSize={0.08}
                color="#0f172a"
                anchorX="center"
                anchorY="middle"
                fontWeight={700}
              >
                {agent.label}
              </DreiText>
              <DreiText
                position={[0, -0.02, 0]}
                fontSize={0.065}
                color="#64748b"
                anchorX="center"
                anchorY="middle"
                maxWidth={1.3}
              >
                {agent.role}
              </DreiText>
            </group>
          </group>
        );
      })}
    </group>
  );
}

export default function OperationsFlowWorld({
  pulse,
  seats = [],
  salesFloor,
  operationsFloor,
  financeFloor,
  supportFloor,
  hrFloor,
  marketingFloor,
  selectedSeatId,
  selectedInspectorTarget,
  onActiveZoneChange,
  onSeatSelect,
  onInspectorTargetChange,
}: {
  pulse?: BusinessPulse;
  seats?: Seat[];
  salesFloor?: SalesFloorState;
  operationsFloor?: OperationsFloorState;
  financeFloor?: FinanceFloorState;
  supportFloor?: SupportFloorState;
  hrFloor?: HRFloorState;
  marketingFloor?: MarketingFloorState;
  selectedSeatId?: string | null;
  selectedInspectorTarget?: BoardroomInspectorTarget | null;
  onActiveZoneChange?: (zone: FlowZone) => void;
  onSeatSelect?: (seatId: string, zone: FlowZone) => void;
  onInspectorTargetChange?: (target: BoardroomInspectorTarget | null) => void;
}) {
  const safePulse: BusinessPulse = pulse ?? DEMO_PULSE;
  const safeSeats = Array.isArray(seats) ? seats : [];
  const seatMap = new Map(
    safeSeats.map((seat) => [seat.departmentKey, seat]),
  );

  const marketingSeat = seatMap.get("marketing");
  const salesSeat = seatMap.get("sales");
  const operationsSeat = seatMap.get("operations");
  const financeSeat = seatMap.get("finance");
  const supportSeat = seatMap.get("support");

  const engineX = -16;
  const engineY = 2.6;
  const funnelX = -5.2;
  const funnelY = 0.25;
  const salesX = 8;
  const operationsX = 20;
  const financeX = 32;
  const supportX = 44;

  const selectSeat = (seatId: string, zone: FlowZone) => {
    onActiveZoneChange?.(zone);
    onSeatSelect?.(seatId, zone);
    onInspectorTargetChange?.({ kind: "seat", seatId });
  };

  const selectFlow = (flow: DepartmentFloorFlow, zone: FlowZone) => {
    const seatId =
      zone === "marketing"
        ? "seat_marketing"
        : zone === "sales"
          ? "seat_sales"
          : zone === "operations"
            ? "seat_ops"
            : zone === "finance"
              ? "seat_finance"
              : "seat_support";

    onActiveZoneChange?.(zone);
    onSeatSelect?.(seatId, zone);
    onInspectorTargetChange?.({
      kind:
        zone === "marketing"
          ? "marketing_flow"
          : zone === "sales"
            ? "sales_flow"
            : zone === "operations"
              ? "operations_flow"
              : zone === "finance"
                ? "finance_flow"
                : "support_flow",
      flowId: flow.id,
    } as BoardroomInspectorTarget);
  };

  const selectStage = (
    stageId: string,
    zone: FlowZone,
    kind: "marketing_stage" | "sales_stage" | "operations_stage" | "finance_stage" | "support_stage" | "hr_stage",
  ) => {
    const seatId =
      zone === "marketing"
        ? "seat_marketing"
        : zone === "sales"
          ? "seat_sales"
          : zone === "operations"
            ? "seat_ops"
            : zone === "finance"
              ? "seat_finance"
              : "seat_support";

    onActiveZoneChange?.(zone);
    onSeatSelect?.(seatId, zone);
    onInspectorTargetChange?.({ kind, stageId } as BoardroomInspectorTarget);
  };

  const selectAgent = (
    agentId: string,
    zone: FlowZone,
    kind: "marketing_agent" | "sales_agent" | "operations_agent" | "finance_agent" | "support_agent" | "hr_agent",
  ) => {
    const seatId =
      zone === "marketing"
        ? "seat_marketing"
        : zone === "sales"
          ? "seat_sales"
          : zone === "operations"
            ? "seat_ops"
            : zone === "finance"
              ? "seat_finance"
              : "seat_support";

    onActiveZoneChange?.(zone);
    onSeatSelect?.(seatId, zone);
    onInspectorTargetChange?.({ kind, agentId } as BoardroomInspectorTarget);
  };

  const isFlowActive = (kind: BoardroomInspectorTarget["kind"], flowId: string) =>
    selectedInspectorTarget?.kind === kind &&
    "flowId" in selectedInspectorTarget &&
    selectedInspectorTarget.flowId === flowId;

  const isStageActive = (kind: BoardroomInspectorTarget["kind"], stageId: string) =>
    selectedInspectorTarget?.kind === kind &&
    "stageId" in selectedInspectorTarget &&
    selectedInspectorTarget.stageId === stageId;

  const isAgentActive = (kind: BoardroomInspectorTarget["kind"], agentId: string) =>
    selectedInspectorTarget?.kind === kind &&
    "agentId" in selectedInspectorTarget &&
    selectedInspectorTarget.agentId === agentId;

  const inputs: ChannelInput[] = [
    {
      key: "meta",
      label: "Meta Ads",
      subtitle: "Paid social",
      x: engineX - 10.5,
      y: 4.25,
      z: -5.2,
      accent: "#1a8aff",
      value: "traffic feed",
      seatId: "seat_marketing",
    },
    {
      key: "tiktok",
      label: "TikTok",
      subtitle: "Organic + paid",
      x: engineX - 6.4,
      y: 4.25,
      z: -5.2,
      accent: "#8b5cf6",
      value: "content feed",
      seatId: "seat_marketing",
    },
    {
      key: "website",
      label: "Website",
      subtitle: "Direct + SEO",
      x: engineX - 2.3,
      y: 4.25,
      z: -5.2,
      accent: "#22c55e",
      value: "site visits",
      seatId: "seat_marketing",
    },
    {
      key: "email",
      label: "Email",
      subtitle: "Lifecycle + nurture",
      x: engineX + 1.8,
      y: 4.25,
      z: -5.2,
      accent: "#f59e0b",
      value: "nurture feed",
      seatId: "seat_marketing",
    },
    {
      key: "referrals",
      label: "Referrals",
      subtitle: "Word of mouth",
      x: engineX + 5.9,
      y: 4.25,
      z: -5.2,
      accent: "#10b981",
      value: "warm leads",
      seatId: "seat_marketing",
    },
    {
      key: "marketplace",
      label: "Marketplace",
      subtitle: "External channels",
      x: engineX + 10.0,
      y: 4.25,
      z: -5.2,
      accent: "#06b6d4",
      value: "channel feed",
      seatId: "seat_marketing",
    },
  ];

  return (
    <group position={[0, 0, 4]}>
      <FactoryBase />

      {inputs.map((channel) => (
        <group key={channel.key}>
          <ChannelSourceBox
            channel={channel}
            active={selectedSeatId === "seat_marketing"}
            onClick={() => selectSeat("seat_marketing", "marketing")}
          />
          <ConveyorSegment
            x={channel.x + 3.1}
            z={channel.z}
            width={2.8}
          />
        </group>
      ))}

      <MarketingFlywheel
        position={[engineX, engineY, 0]}
        scale={1.1}
        active={selectedSeatId === "seat_marketing"}
        onClick={() => selectSeat("seat_marketing", "marketing")}
        pulseValue={`${safePulse.sales.orders} input events`}
      />

      <FunnelFrame
        position={[funnelX, funnelY, 0]}
        active={selectedSeatId === "seat_marketing"}
        onClick={() => selectSeat("seat_marketing", "marketing")}
      />

      <TrafficLemmings
        channelInputs={inputs}
        engineX={engineX}
        engineY={engineY}
        funnelX={funnelX}
        funnelY={funnelY}
        salesX={salesX}
        conversionRate={safePulse.sales.conversionRate}
      />

      <SalesContainer
        position={[salesX, 0, 0]}
        active={selectedSeatId === "seat_sales"}
        onClick={() => selectSeat("seat_sales", "sales")}
        conversionRate={safePulse.sales.conversionRate}
        orders={safePulse.sales.orders}
      />

      <OperationsContainer
        position={[operationsX, 0, 0]}
        active={selectedSeatId === "seat_ops"}
        onClick={() => selectSeat("seat_ops", "operations")}
        backlog={safePulse.ops.backlog}
        blockedJobs={safePulse.ops.blockedJobs}
        turnaround={safePulse.ops.avgTurnaroundDays ?? 3}
        fulfilmentRate={safePulse.ops.fulfilmentRate ?? 92}
        capacityUsed={76}
      />

      <FinanceContainer
        position={[financeX, 0, 0]}
        active={selectedSeatId === "seat_finance"}
        onClick={() => selectSeat("seat_finance", "finance")}
        cashOnHand={safePulse.cash.onHand}
        debtorDays={safePulse.finance.debtorDays}
      />

      <SupportContainer
        position={[supportX, 0, 0]}
        active={selectedSeatId === "seat_support"}
        onClick={() => selectSeat("seat_support", "support")}
        retainedPct={safePulse.sales.sellThroughRate}
        demandRisk={safePulse.risk.demand}
      />

      <HrSupportOverlay
        position={[supportX - 0.5, 0, 6.2]}
        hrFloor={hrFloor}
        active={selectedSeatId === "seat_hr"}
        selectedInspectorTarget={selectedInspectorTarget}
        onStageClick={(stageId) => {
          onActiveZoneChange?.("hr");
          onSeatSelect?.("seat_hr", "hr");
          onInspectorTargetChange?.({
            kind: "hr_stage",
            stageId,
          });
        }}
        onAgentClick={(agentId) => {
          onActiveZoneChange?.("hr");
          onSeatSelect?.("seat_hr", "hr");
          onInspectorTargetChange?.({
            kind: "hr_agent",
            agentId,
          });
        }}
      />

      <ConveyorSegment x={salesX} />
      <ConveyorSegment x={operationsX} />
      <ConveyorSegment x={financeX} />
      <ConveyorSegment x={supportX - 4.5} width={6.6} />

      <HandoffPulse start={[12.1, 0.22, 0]} end={[13.9, 0.22, 0]} color="#3b82f6" phase={0} />
      <HandoffPulse start={[24.1, 0.22, 0]} end={[25.9, 0.22, 0]} color="#3b82f6" phase={0.9} />
      <HandoffPulse start={[36.1, 0.22, 0]} end={[37.9, 0.22, 0]} color="#3b82f6" phase={1.8} />

      <DreiLine
        points={[
          new THREE.Vector3(engineX + 4.25, engineY + 0.1, 0),
          new THREE.Vector3(funnelX - 2.3, engineY + 0.1, 0),
          new THREE.Vector3(funnelX - 2.3, funnelY + 3.6, 0),
          new THREE.Vector3(funnelX, funnelY + 3.6, 0),
        ]}
        color="#3b82f6"
        lineWidth={2}
        transparent
        opacity={0.58}
      />

      <DreiLine
        points={[
          new THREE.Vector3(funnelX + 0.88, funnelY + 0.5, 0),
          new THREE.Vector3(salesX - 2.6, 0.22, 0),
        ]}
        color="#3b82f6"
        lineWidth={2}
        transparent
        opacity={0.55}
      />

      {inputs.map((channel) => (
        <DreiLine
          key={`feed-line-${channel.key}`}
          points={[
            new THREE.Vector3(channel.x + 1.45, channel.y - 0.05, channel.z),
            new THREE.Vector3(engineX - 3.4, engineY - 0.1, channel.z * 0.22),
          ]}
          color={channel.accent}
          lineWidth={1.15}
          transparent
          opacity={0.38}
        />
      ))}

      {(marketingFloor?.flows ?? []).slice(0, 2).map((flow, index) => {
        const fromLabel = getFlowStageLabel(flow, marketingFloor?.stages ?? [], "from");
        const toLabel = getFlowStageLabel(flow, marketingFloor?.stages ?? [], "to");
        const active = isFlowActive("marketing_flow", flow.id);

        return (
          <FlowOverlayCard
            key={`marketing-flow-${flow.id}`}
            position={[engineX - 1.8 + index * 3.6, 0.26, 7.2]}
            label={`${fromLabel} → ${toLabel}`}
            value={flowOverlayValue(flow)}
            tone={flowTone(flow)}
            active={active}
            onClick={() => selectFlow(flow, "marketing")}
          />
        );
      })}

      {(salesFloor?.flows ?? []).slice(0, 2).map((flow, index) => {
        const fromLabel = getFlowStageLabel(flow, salesFloor?.stages ?? [], "from");
        const toLabel = getFlowStageLabel(flow, salesFloor?.stages ?? [], "to");
        const active = isFlowActive("sales_flow", flow.id);

        return (
          <FlowOverlayCard
            key={`sales-flow-${flow.id}`}
            position={[salesX - 1.8 + index * 3.6, 0.26, 3.15]}
            label={`${fromLabel} → ${toLabel}`}
            value={flowOverlayValue(flow)}
            tone={flowTone(flow)}
            active={active}
            onClick={() => selectFlow(flow, "sales")}
          />
        );
      })}

      {(operationsFloor?.flows ?? []).slice(0, 2).map((flow, index) => {
        const fromLabel = getFlowStageLabel(flow, operationsFloor?.stages ?? [], "from");
        const toLabel = getFlowStageLabel(flow, operationsFloor?.stages ?? [], "to");
        const active = isFlowActive("operations_flow", flow.id);

        return (
          <FlowOverlayCard
            key={`operations-flow-${flow.id}`}
            position={[operationsX - 1.8 + index * 3.6, 0.26, 3.15]}
            label={`${fromLabel} → ${toLabel}`}
            value={flowOverlayValue(flow)}
            tone={flowTone(flow)}
            active={active}
            onClick={() => selectFlow(flow, "operations")}
          />
        );
      })}

      {(financeFloor?.flows ?? []).slice(0, 2).map((flow, index) => {
        const fromLabel = getFlowStageLabel(flow, financeFloor?.stages ?? [], "from");
        const toLabel = getFlowStageLabel(flow, financeFloor?.stages ?? [], "to");
        const active = isFlowActive("finance_flow", flow.id);

        return (
          <FlowOverlayCard
            key={`finance-flow-${flow.id}`}
            position={[financeX - 1.8 + index * 3.6, 0.26, 3.15]}
            label={`${fromLabel} → ${toLabel}`}
            value={flowOverlayValue(flow)}
            tone={flowTone(flow)}
            active={active}
            onClick={() => selectFlow(flow, "finance")}
          />
        );
      })}

      {(supportFloor?.flows ?? []).slice(0, 2).map((flow, index) => {
        const fromLabel = getFlowStageLabel(flow, supportFloor?.stages ?? [], "from");
        const toLabel = getFlowStageLabel(flow, supportFloor?.stages ?? [], "to");
        const active = isFlowActive("support_flow", flow.id);

        return (
          <FlowOverlayCard
            key={`support-flow-${flow.id}`}
            position={[supportX - 1.8 + index * 3.6, 0.26, 3.15]}
            label={`${fromLabel} → ${toLabel}`}
            value={flowOverlayValue(flow)}
            tone={flowTone(flow)}
            active={active}
            onClick={() => selectFlow(flow, "support")}
          />
        );
      })}

            {(salesFloor?.flows ?? [])
        .filter((flow) => flow.exception || (flow.blockedCount ?? 0) > 0 || flow.bottleneck)
        .slice(0, 1)
        .map((flow) => (
          <FlowExceptionRoute
            key={`sales-exception-${flow.id}`}
            color={flowTone(flow)}
            points={[
              [salesX + 2.9, 0.28, 0.7],
              [salesX + 3.8, 0.28, 1.8],
              [salesX + 4.8, 0.28, 2.6],
            ]}
          />
        ))}

      {(operationsFloor?.flows ?? [])
        .filter((flow) => flow.exception || (flow.blockedCount ?? 0) > 0 || flow.bottleneck)
        .slice(0, 1)
        .map((flow) => (
          <FlowExceptionRoute
            key={`operations-exception-${flow.id}`}
            color={flowTone(flow)}
            points={[
              [operationsX + 2.9, 0.28, 0.7],
              [operationsX + 3.9, 0.28, 1.8],
              [operationsX + 4.9, 0.28, 2.6],
            ]}
          />
        ))}

      {(financeFloor?.flows ?? [])
        .filter((flow) => flow.exception || (flow.blockedCount ?? 0) > 0 || flow.bottleneck)
        .slice(0, 1)
        .map((flow) => (
          <FlowExceptionRoute
            key={`finance-exception-${flow.id}`}
            color={flowTone(flow)}
            points={[
              [financeX + 2.4, 0.28, 0.7],
              [financeX + 3.3, 0.28, 1.8],
              [financeX + 4.1, 0.28, 2.6],
            ]}
          />
        ))}

      {(supportFloor?.flows ?? [])
        .filter((flow) => flow.exception || (flow.blockedCount ?? 0) > 0 || flow.bottleneck)
        .slice(0, 1)
        .map((flow) => (
          <FlowExceptionRoute
            key={`support-exception-${flow.id}`}
            color={flowTone(flow)}
            points={[
              [supportX + 2.1, 0.28, 0.7],
              [supportX + 3.0, 0.28, 1.8],
              [supportX + 3.9, 0.28, 2.6],
            ]}
          />
        ))}



      <DreiLine
        points={[
          new THREE.Vector3(engineX - 6.5, 0.16, 0),
          new THREE.Vector3(supportX + 2.3, 0.16, 0),
        ]}
        color="#94a3b8"
        lineWidth={1}
        transparent
        opacity={0.22}
      />
    </group>
  );
}