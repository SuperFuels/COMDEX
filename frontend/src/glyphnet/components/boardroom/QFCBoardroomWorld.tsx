"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Text, Line, Html, useTexture } from "@react-three/drei";
import { useMemo, useRef, useState } from "react";
import { seatStateColor } from "./boardroom.world.constants";
import OperationsFlowWorld from "./boardroom.world.operations-flow";
import * as THREE from "three";
import {
  DEMO_FLOORS,
  DEMO_PULSE,
  DEMO_SEATS,
} from "./boardroom.domain.mock";
import type {
  BoardroomInspectorTarget,
  BoardroomViewMode,
  BusinessPulse,
  RiskLevel,
  Seat,
  SalesFloorState,
  FinanceFloorState,
  OperationsFloorState,
  SupportFloorState,
  HRFloorState,
  MarketingFloorState,
  DepartmentFloorAgent,
  DepartmentFloorStage,
} from "./boardroom.domain";
import type {
  BoardroomRuntime,
  RuntimeWorkflowRun,
  WorkflowRunStatus,
} from "./boardroom.runtime";


const DreiText: any = Text;
const DreiLine: any = Line;

export type BoardroomWorldZone =
  | "coo"
  | "marketing"
  | "sales"
  | "operations"
  | "hr"
  | "support"
  | "finance"
  | "ceo"
  | "aion"
  | "openai";

type BoardroomWorldProps = {
  frame: {
    boardroomFrame?: {
      pulse?: BusinessPulse;
      seats?: Seat[];
      floors?: {
        sales?: SalesFloorState;
        finance?: FinanceFloorState;
        operations?: OperationsFloorState;
        support?: SupportFloorState;
        hr?: HRFloorState;
        marketing?: MarketingFloorState;
      };
      runtime?: BoardroomRuntime;
    };
    boardroom?: {
      seats?: Seat[];
      runtime?: BoardroomRuntime;
    };
    pulse?: BusinessPulse;
  };
  viewMode: BoardroomViewMode;
  activeZone: BoardroomWorldZone;
  selectedSeatId: string | null;
  selectedInspectorTarget: BoardroomInspectorTarget | null;
  onViewModeChange: (mode: BoardroomViewMode) => void;
  onActiveZoneChange: (zone: BoardroomWorldZone) => void;
  onSeatSelect: (seatId: string, zone: BoardroomWorldZone) => void;
  onInspectorTargetChange: (target: BoardroomInspectorTarget | null) => void;
  onCanvasClear: () => void;
};

type ZoneConfig = {
  label: string;
  position: [number, number, number];
  camera: [number, number, number];
  target: [number, number, number];
  tint: string;
  scale?: number;
};


function runtimeStatusColor(status?: WorkflowRunStatus) {
  switch (status) {
    case "running":
      return "#1a8aff";
    case "waiting_approval":
      return "#f59e0b";
    case "failed":
      return "#ef4444";
    case "completed":
      return "#22c55e";
    case "queued":
      return "#64748b";
    case "cancelled":
      return "#94a3b8";
    default:
      return "#8b5cf6";
  }
}

function runtimeStatusLabel(status?: WorkflowRunStatus) {
  switch (status) {
    case "running":
      return "RUNNING";
    case "waiting_approval":
      return "WAITING";
    case "failed":
      return "FAILED";
    case "completed":
      return "DONE";
    case "queued":
      return "QUEUED";
    case "cancelled":
      return "STOPPED";
    default:
      return undefined;
  }
}

function getRuntimeCurrentStepLabel(run?: RuntimeWorkflowRun | null) {
  if (!run) return "—";

  const candidate =
    (run as any).currentStepLabel ??
    (run as any).current_step_label ??
    (run as any).currentStep ??
    (run as any).current_step ??
    (run as any).step_label ??
    (run as any).stepLabel;

  if (typeof candidate === "string" && candidate.trim()) {
    return candidate;
  }

  return "—";
}

function runtimeStatusPriority(status?: WorkflowRunStatus) {
  switch (status) {
    case "running":
      return 6;
    case "waiting_approval":
      return 5;
    case "failed":
      return 4;
    case "queued":
      return 3;
    case "completed":
      return 2;
    case "cancelled":
      return 1;
    default:
      return 0;
  }
}

const RING_RADIUS = 12.5;
const DEG = Math.PI / 180;

function polar(radius: number, angleDeg: number): [number, number, number] {
  const a = angleDeg * DEG;
  return [Math.cos(a) * radius, 0, Math.sin(a) * radius];
}

const ZONES: Record<BoardroomWorldZone, ZoneConfig> = {
  coo: {
    label: "COO Core",
    position: [0, 0, 0],
    camera: [0, 7.2, 12.8],
    target: [0, 0, 0],
    tint: "#1a8aff",
    scale: 1.05,
  },
  marketing: {
    label: "Marketing",
    position: polar(RING_RADIUS, -90),
    camera: [0, 6.3, -2.8],
    target: polar(RING_RADIUS, -90),
    tint: "#1a8aff",
    scale: 1.35,
  },
  sales: {
    label: "Sales",
    position: polar(RING_RADIUS, -30),
    camera: [10.8, 6.2, 4.2],
    target: polar(RING_RADIUS, -30),
    tint: "#1a8aff",
    scale: 1.45,
  },
  operations: {
    label: "Operations",
    position: polar(RING_RADIUS, 30),
    camera: [10.8, 6.2, 16.4],
    target: polar(RING_RADIUS, 30),
    tint: "#1a8aff",
    scale: 1.45,
  },
  hr: {
    label: "HR",
    position: polar(RING_RADIUS, 90),
    camera: [0, 6.2, 24.2],
    target: polar(RING_RADIUS, 90),
    tint: "#1a8aff",
    scale: 1.35,
  },
  support: {
    label: "Support",
    position: polar(RING_RADIUS, 150),
    camera: [-10.8, 6.2, 16.4],
    target: polar(RING_RADIUS, 150),
    tint: "#1a8aff",
    scale: 1.45,
  },
  finance: {
    label: "Finance",
    position: polar(RING_RADIUS, 210),
    camera: [-13.6, 7.2, 1.8],
    target: polar(RING_RADIUS, 210),
    tint: "#1a8aff",
    scale: 1.45,
  },
  ceo: {
    label: "CEO",
    position: [-6.4, 0, -21.5],
    camera: [-6.4, 5.8, -12.2],
    target: [-6.4, 0, -21.5],
    tint: "#60a5fa",
    scale: 1.1,
  },
  aion: {
    label: "AION",
    position: [0, 0, -24],
    camera: [0, 5.8, -14.4],
    target: [0, 0, -24],
    tint: "#8b5cf6",
    scale: 1.12,
  },
  openai: {
    label: "OpenAI",
    position: [6.4, 0, -21.5],
    camera: [6.4, 5.8, -12.2],
    target: [6.4, 0, -21.5],
    tint: "#22c55e",
    scale: 1.1,
  },
};

function fmtMoney(v: number) {
  return `£${v.toLocaleString("en-GB")}`;
}

function fmtPct(v: number) {
  return `${v}%`;
}

function fmtAny(value: string | number | undefined, unit?: string) {
  if (value == null) return "—";
  if (typeof value === "number") return `${value}${unit ?? ""}`;
  return `${value}${unit ?? ""}`;
}

function riskColor(level: RiskLevel) {
  if (level === "high") return "#ef4444";
  if (level === "medium") return "#f59e0b";
  return "#22c55e";
}

function zoneToSeatId(zone: BoardroomWorldZone): string | null {
  switch (zone) {
    case "ceo":
      return "seat_ceo";
    case "coo":
      return "seat_coo";
    case "marketing":
      return "seat_marketing";
    case "sales":
      return "seat_sales";
    case "finance":
      return "seat_finance";
    case "operations":
      return "seat_ops";
    case "support":
      return "seat_support";
    case "hr":
      return "seat_hr";
    default:
      return null;
  }
}

function getIndexedPosition(
  index: number,
  positions: [number, number, number][],
): [number, number, number] | null {
  return positions[index] ?? null;
}

function getStagePositionByIndex(
  stageId: string,
  stages: DepartmentFloorStage[],
  positions: [number, number, number][],
): [number, number, number] | null {
  const index = stages.findIndex((s) => s.id === stageId);
  if (index < 0) return null;
  return getIndexedPosition(index, positions);
}

function getAgentPositionByIndex(
  agentId: string,
  agents: DepartmentFloorAgent[],
  positions: [number, number, number][],
): [number, number, number] | null {
  const index = agents.findIndex((a) => a.id === agentId);
  if (index < 0) return null;
  return getIndexedPosition(index, positions);
}

function isFinanceStageTarget(
  target: BoardroomInspectorTarget | null,
  stageId: string,
) {
  return target?.kind === "finance_stage" && target.stageId === stageId;
}

function isFinanceAgentTarget(
  target: BoardroomInspectorTarget | null,
  agentId: string,
) {
  return target?.kind === "finance_agent" && target.agentId === agentId;
}

function isOperationsStageTarget(
  target: BoardroomInspectorTarget | null,
  stageId: string,
) {
  return target?.kind === "operations_stage" && target.stageId === stageId;
}

function isOperationsAgentTarget(
  target: BoardroomInspectorTarget | null,
  agentId: string,
) {
  return target?.kind === "operations_agent" && target.agentId === agentId;
}

function isSalesFlowTarget(
  target: BoardroomInspectorTarget | null,
  flowId: string,
) {
  return target?.kind === "sales_flow" && target.flowId === flowId;
}

function isFinanceFlowTarget(
  target: BoardroomInspectorTarget | null,
  flowId: string,
) {
  return target?.kind === "finance_flow" && target.flowId === flowId;
}

function isOperationsFlowTarget(
  target: BoardroomInspectorTarget | null,
  flowId: string,
) {
  return target?.kind === "operations_flow" && target.flowId === flowId;
}

function isSupportFlowTarget(
  target: BoardroomInspectorTarget | null,
  flowId: string,
) {
  return target?.kind === "support_flow" && target.flowId === flowId;
}

function isHrFlowTarget(
  target: BoardroomInspectorTarget | null,
  flowId: string,
) {
  return target?.kind === "hr_flow" && target.flowId === flowId;
}

function isMarketingFlowTarget(
  target: BoardroomInspectorTarget | null,
  flowId: string,
) {
  return target?.kind === "marketing_flow" && target.flowId === flowId;
}

function isSupportStageTarget(
  target: BoardroomInspectorTarget | null,
  stageId: string,
) {
  return target?.kind === "support_stage" && target.stageId === stageId;
}

function isSupportAgentTarget(
  target: BoardroomInspectorTarget | null,
  agentId: string,
) {
  return target?.kind === "support_agent" && target.agentId === agentId;
}

function isHrStageTarget(
  target: BoardroomInspectorTarget | null,
  stageId: string,
) {
  return target?.kind === "hr_stage" && target.stageId === stageId;
}

function isHrAgentTarget(
  target: BoardroomInspectorTarget | null,
  agentId: string,
) {
  return target?.kind === "hr_agent" && target.agentId === agentId;
}

function isMarketingStageTarget(
  target: BoardroomInspectorTarget | null,
  stageId: string,
) {
  return target?.kind === "marketing_stage" && target.stageId === stageId;
}

function isMarketingAgentTarget(
  target: BoardroomInspectorTarget | null,
  agentId: string,
) {
  return target?.kind === "marketing_agent" && target.agentId === agentId;
}

function CameraRig({
  activeZone,
}: {
  activeZone: BoardroomWorldZone;
}) {
  const { camera } = useThree();
  const controlsRef = useRef<any>(null);

  const animatingRef = useRef(true);
  const lastZoneRef = useRef<BoardroomWorldZone>(activeZone);

  const desired = ZONES[activeZone];

  const targetCamera = useMemo(
    () => new THREE.Vector3(...desired.camera),
    [desired.camera],
  );
  const targetLookAt = useMemo(
    () => new THREE.Vector3(...desired.target),
    [desired.target],
  );

  useFrame(() => {
    if (lastZoneRef.current !== activeZone) {
      lastZoneRef.current = activeZone;
      animatingRef.current = true;
    }

    if (!controlsRef.current) return;

    if (animatingRef.current) {
      camera.position.lerp(targetCamera, 0.08);
      controlsRef.current.target.lerp(targetLookAt, 0.1);
      controlsRef.current.update();

      const camDone = camera.position.distanceTo(targetCamera) < 0.08;
      const targetDone =
        controlsRef.current.target.distanceTo(targetLookAt) < 0.08;

      if (camDone && targetDone) {
        camera.position.copy(targetCamera);
        controlsRef.current.target.copy(targetLookAt);
        controlsRef.current.update();
        animatingRef.current = false;
      }
    }
  });

  return (
    <OrbitControls
      ref={controlsRef}
      makeDefault
      enableDamping
      dampingFactor={0.08}
      rotateSpeed={0.45}
      zoomSpeed={1}
      panSpeed={1.6}
      screenSpacePanning
      enablePan
      minDistance={10}
      maxDistance={260}
      minPolarAngle={Math.PI / 6}
      maxPolarAngle={Math.PI / 2.1}
      target={desired.target}
      mouseButtons={{
        LEFT: THREE.MOUSE.PAN,
        MIDDLE: THREE.MOUSE.DOLLY,
        RIGHT: THREE.MOUSE.ROTATE,
      }}
    />
  );
}

function ExecutiveBillboard({
  position,
  imageUrl = "/brand/hq-billboard.png",
}: {
  position: [number, number, number];
  imageUrl?: string;
}) {
  const texture = useTexture(imageUrl);

  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.colorSpace = THREE.SRGBColorSpace;

  const arcRadius = 9.6;
  const arcAngle = Math.PI / 2.55;
  const panelHeight = 4.4;

  return (
    <group position={position} rotation={[0, Math.PI, 0]}>
      <mesh position={[0, 2.25, 0.28]}>
        <cylinderGeometry args={[0.14, 0.14, 4.3, 24]} />
        <meshStandardMaterial color="#c8d4e6" roughness={0.82} />
      </mesh>

      <mesh position={[0, 2.9, 2.95]} rotation={[0, Math.PI, 0]}>
        <cylinderGeometry
          args={[
            arcRadius,
            arcRadius,
            panelHeight,
            72,
            1,
            true,
            -arcAngle / 2,
            arcAngle,
          ]}
        />
        <meshStandardMaterial
          color="#f8fbff"
          transparent
          opacity={0.96}
          side={THREE.DoubleSide}
          metalness={0.04}
          roughness={0.88}
        />
      </mesh>

      <mesh position={[0, 2.9, 2.84]} rotation={[0, Math.PI, 0]}>
        <cylinderGeometry
          args={[
            arcRadius - 0.06,
            arcRadius - 0.06,
            panelHeight - 0.18,
            72,
            1,
            true,
            -arcAngle / 2,
            arcAngle,
          ]}
        />
        <meshBasicMaterial
          color="#1a8aff"
          transparent
          opacity={0.04}
          side={THREE.DoubleSide}
        />
      </mesh>

      <mesh position={[0, 2.9, 2.72]} rotation={[0, Math.PI, 0]}>
        <cylinderGeometry
          args={[
            arcRadius - 0.14,
            arcRadius - 0.14,
            3.55,
            72,
            1,
            true,
            -arcAngle / 2,
            arcAngle,
          ]}
        />
        <meshBasicMaterial
          map={texture}
          transparent
          opacity={1}
          side={THREE.DoubleSide}
        />
      </mesh>

      <mesh position={[0, 5.16, 2.95]}>
        <boxGeometry args={[5.4, 0.14, 0.26]} />
        <meshStandardMaterial color="#d8e3f0" roughness={0.84} />
      </mesh>

      <mesh position={[0, 0.66, 2.95]}>
        <boxGeometry args={[5.4, 0.14, 0.26]} />
        <meshStandardMaterial color="#d8e3f0" roughness={0.84} />
      </mesh>
    </group>
  );
}

function PulseChip({
  x,
  y,
  label,
  value,
  accent,
}: {
  x: number;
  y: number;
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <group position={[x, 0.05, y]}>
      <DreiText
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.14}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        {label}
      </DreiText>

      <DreiText
        position={[0, 0, 0.32]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.22}
        color={accent ?? "#0f172a"}
        anchorX="center"
        anchorY="middle"
      >
        {value}
      </DreiText>
    </group>
  );
}

function CooPulseOverlay({
  position,
  pulse,
}: {
  position: [number, number, number];
  pulse: BusinessPulse;
}) {
  return (
    <group position={position}>
      <PulseChip x={-1.35} y={-0.72} label="Cash" value={fmtMoney(pulse.cash.onHand)} />
      <PulseChip x={0} y={-0.72} label="Revenue" value={fmtMoney(pulse.sales.revenue)} />
      <PulseChip x={1.35} y={-0.72} label="GM" value={fmtPct(pulse.finance.grossMarginPct)} />
      <PulseChip x={-1.35} y={0.05} label="Stock Value" value={fmtMoney(pulse.stock.value)} />
      <PulseChip x={0} y={0.05} label="Days Cover" value={`${pulse.stock.daysCover}d`} />
      <PulseChip x={1.35} y={0.05} label="Backlog" value={`${pulse.ops.backlog}`} />
      <PulseChip x={-1.35} y={0.82} label="Creditor Days" value={`${pulse.finance.creditorDays}d`} />
      <PulseChip x={0} y={0.82} label="Debtor Days" value={`${pulse.finance.debtorDays}d`} />
      <PulseChip
        x={1.35}
        y={0.82}
        label="Cash Risk"
        value={pulse.risk.cash.toUpperCase()}
        accent={riskColor(pulse.risk.cash)}
      />
    </group>
  );
}

function HexFloor({
  label,
  position,
  tint,
  active,
  onClick,
  scale = 1,
  dark = false,
  state,
}: {
  label: string;
  position: [number, number, number];
  tint: string;
  active: boolean;
  onClick?: () => void;
  scale?: number;
  dark?: boolean;
  state?: string;
}) {
  const outerColor = dark ? "#14223c" : "#d7dee9";
  const innerColor = dark ? "#21345a" : "#edf2f8";
  const textColor = dark ? "#f8fafc" : "#1f2937";
  const statusColor = seatStateColor(state);

  return (
    <group position={position} scale={scale}>
      <mesh
        position={[0, -0.18, 0]}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.();
        }}
      >
        <cylinderGeometry args={[4.4, 4.4, 0.2, 6]} />
        <meshStandardMaterial color={outerColor} metalness={0.08} roughness={0.92} />
      </mesh>

      <mesh position={[0, -0.05, 0]}>
        <cylinderGeometry args={[3.55, 3.55, 0.06, 6]} />
        <meshStandardMaterial color={innerColor} metalness={0.03} roughness={0.95} />
      </mesh>

      <mesh position={[0, -0.005, 0]}>
        <cylinderGeometry args={[3.62, 3.62, 0.014, 6]} />
        <meshBasicMaterial color={tint} transparent opacity={active ? 0.24 : 0.1} />
      </mesh>

      <mesh position={[0, 0.01, 0]}>
        <cylinderGeometry args={[2.15, 2.15, 0.02, 6]} />
        <meshBasicMaterial color="#1a8aff" transparent opacity={0.05} />
      </mesh>

      <mesh position={[0, 0.03, 2.45]}>
        <circleGeometry args={[0.22, 24]} />
        <meshBasicMaterial color={statusColor} />
      </mesh>

      <DreiText
        position={[0, 1.35, 0]}
        fontSize={0.42}
        color={textColor}
        anchorX="center"
        anchorY="middle"
      >
        {label}
      </DreiText>

      {state ? (
        <DreiText
          position={[0, 0.28, 2.46]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={0.15}
          color={statusColor}
          anchorX="center"
          anchorY="middle"
        >
          {state.toUpperCase()}
        </DreiText>
      ) : null}
    </group>
  );
}

function MiniBot({
  position,
  tint = "#22c55e",
  label,
  role,
  workload,
  displayTag,
  active = false,
  runtimeStatus,
  runtimeCount,
  onClick,
}: {
  position: [number, number, number];
  tint?: string;
  label?: string;
  role?: string;
  workload?: number;
  displayTag?: string;
  active?: boolean;
  runtimeStatus?: WorkflowRunStatus;
  runtimeCount?: number;
  onClick?: () => void;
}) {
  const pulseRef = useRef<THREE.Mesh>(null);
  const haloRef = useRef<THREE.Mesh>(null);
  const statusHaloRef = useRef<THREE.Mesh>(null);

  const statusColor = runtimeStatusColor(runtimeStatus);
  const statusLabel = runtimeStatusLabel(runtimeStatus);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    const basePulseSpeed =
      runtimeStatus === "running"
        ? 4
        : runtimeStatus === "waiting_approval"
          ? 2.2
          : runtimeStatus === "failed"
            ? 1.4
            : 2.8;

    const pulseScale = 1 + Math.sin(t * basePulseSpeed) * 0.06;
    const haloScale = 1 + Math.sin(t * 2.2) * 0.04;
    const statusHaloScale =
      1 +
      Math.sin(
        t *
          (runtimeStatus === "running"
            ? 3.8
            : runtimeStatus === "waiting_approval"
              ? 2.6
              : 1.8),
      ) *
        0.08;

    if (pulseRef.current) {
      pulseRef.current.scale.setScalar(pulseScale);
      const material = pulseRef.current.material as THREE.MeshBasicMaterial;
      material.opacity = 0.18 + ((Math.sin(t * basePulseSpeed) + 1) / 2) * 0.18;
    }

    if (haloRef.current) {
      haloRef.current.scale.setScalar(haloScale);
    }

    if (statusHaloRef.current) {
      statusHaloRef.current.scale.setScalar(statusHaloScale);
      const material = statusHaloRef.current.material as THREE.MeshBasicMaterial;
      material.opacity =
        runtimeStatus === "failed"
          ? 0.26
          : runtimeStatus === "waiting_approval"
            ? 0.22
            : runtimeStatus === "running"
              ? 0.2
              : 0.16;
    }
  });

  return (
    <group position={position}>
      <mesh ref={haloRef} position={[0, 0.06, 0]}>
        <torusGeometry args={[0.34, 0.018, 16, 48]} />
        <meshBasicMaterial color="#69e2ff" transparent opacity={0.45} />
      </mesh>

      <mesh
        ref={pulseRef}
        position={[0, 0.07, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        <ringGeometry args={[0.34, 0.47, 40]} />
        <meshBasicMaterial
          color="#8b5cf6"
          transparent
          opacity={0.18}
          side={THREE.DoubleSide}
        />
      </mesh>

      {runtimeStatus ? (
        <mesh
          ref={statusHaloRef}
          position={[0, 0.075, 0]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          <ringGeometry args={[0.5, 0.67, 48]} />
          <meshBasicMaterial
            color={statusColor}
            transparent
            opacity={0.18}
            side={THREE.DoubleSide}
          />
        </mesh>
      ) : null}

      <mesh
        position={[0, 0.48, 0]}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.();
        }}
      >
        <boxGeometry args={[0.28, 0.86, 0.28]} />
        <meshStandardMaterial
          color="#d9f3ff"
          emissive="#4cc9ff"
          emissiveIntensity={0.18}
          roughness={0.3}
          metalness={0.15}
          transparent
          opacity={0.92}
        />
      </mesh>

      <mesh position={[0, 0.02, 0]}>
        <boxGeometry args={[0.48, 0.05, 0.48]} />
        <meshStandardMaterial
          color="#9fb7d9"
          emissive="#1a8aff"
          emissiveIntensity={0.08}
          roughness={0.5}
          metalness={0.12}
        />
      </mesh>

      <mesh position={[0, 1.02, 0]}>
        <boxGeometry args={[0.28, 0.24, 0.22]} />
        <meshStandardMaterial
          color="#eef8ff"
          emissive="#7c3aed"
          emissiveIntensity={0.12}
          roughness={0.24}
          metalness={0.18}
          transparent
          opacity={0.95}
        />
      </mesh>

      <mesh position={[0, 1.02, 0.115]}>
        <planeGeometry args={[0.14, 0.07]} />
        <meshBasicMaterial color="#0b2545" />
      </mesh>

      <mesh position={[-0.03, 1.02, 0.12]}>
        <circleGeometry args={[0.01, 16]} />
        <meshBasicMaterial color={tint} />
      </mesh>

      <mesh position={[0.03, 1.02, 0.12]}>
        <circleGeometry args={[0.01, 16]} />
        <meshBasicMaterial color={tint} />
      </mesh>

      {active ? (
        <>
          <mesh position={[0, 0.52, 0]}>
            <torusGeometry args={[0.3, 0.035, 16, 40]} />
            <meshBasicMaterial color="#69e2ff" />
          </mesh>
          <mesh position={[0, 0.52, 0]}>
            <torusGeometry args={[0.38, 0.018, 16, 40]} />
            <meshBasicMaterial color="#8b5cf6" transparent opacity={0.7} />
          </mesh>
        </>
      ) : null}

      {displayTag ? (
        <group position={[0, 1.76, 0]}>
          <mesh>
            <boxGeometry args={[0.52, 0.16, 0.04]} />
            <meshBasicMaterial color="#dff6ff" transparent opacity={0.95} />
          </mesh>
          <DreiText
            position={[0, 0, 0.03]}
            fontSize={0.07}
            color="#0f4ea8"
            anchorX="center"
            anchorY="middle"
          >
            {displayTag}
          </DreiText>
        </group>
      ) : null}

      {statusLabel ? (
        <group position={[0, 1.94, 0]}>
          <mesh>
            <boxGeometry args={[0.72, 0.16, 0.04]} />
            <meshBasicMaterial color={statusColor} transparent opacity={0.12} />
          </mesh>
          <DreiText
            position={[0, 0, 0.03]}
            fontSize={0.065}
            color={statusColor}
            anchorX="center"
            anchorY="middle"
          >
            {statusLabel}
          </DreiText>
        </group>
      ) : null}

      {typeof runtimeCount === "number" && runtimeCount > 0 ? (
        <group position={[0.44, 1.1, 0]}>
          <mesh>
            <sphereGeometry args={[0.11, 18, 18]} />
            <meshBasicMaterial color={statusColor} />
          </mesh>
          <DreiText
            position={[0, 0, 0.08]}
            fontSize={0.075}
            color="#ffffff"
            anchorX="center"
            anchorY="middle"
          >
            {`${runtimeCount}`}
          </DreiText>
        </group>
      ) : null}

      {label ? (
        <DreiText
          position={[0, 1.36, 0]}
          fontSize={0.12}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
        >
          {label}
        </DreiText>
      ) : null}

      {role ? (
        <DreiText
          position={[0, 1.54, 0]}
          fontSize={0.085}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
          maxWidth={1.4}
        >
          {role}
        </DreiText>
      ) : null}

      {typeof workload === "number" ? (
        <DreiText
          position={[0, 1.68, 0]}
          fontSize={0.08}
          color="#0f4ea8"
          anchorX="center"
          anchorY="middle"
        >
          {`Load ${workload}`}
        </DreiText>
      ) : null}
    </group>
  );
}

function HumanWorker({
  position,
  tint = "#1a8aff",
  label,
  role,
  workload,
  active = false,
  onClick,
}: {
  position: [number, number, number];
  tint?: string;
  label?: string;
  role?: string;
  workload?: number;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <group position={position}>
      <mesh
        position={[0, 0.04, 0]}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.();
        }}
      >
        <boxGeometry args={[0.52, 0.06, 0.52]} />
        <meshStandardMaterial color="#cfd9e6" roughness={0.9} />
      </mesh>

      <mesh position={[0, 0.5, 0]}>
        <capsuleGeometry args={[0.12, 0.34, 6, 10]} />
        <meshStandardMaterial color="#ffffff" roughness={0.72} />
      </mesh>

      <mesh position={[0, 0.98, 0]}>
        <sphereGeometry args={[0.14, 20, 20]} />
        <meshStandardMaterial color="#f3d2b6" roughness={0.88} />
      </mesh>

      <mesh position={[0, 0.66, 0.13]}>
        <planeGeometry args={[0.18, 0.12]} />
        <meshBasicMaterial color={tint} />
      </mesh>

      <mesh position={[-0.05, 0.48, 0]}>
        <boxGeometry args={[0.05, 0.26, 0.05]} />
        <meshStandardMaterial color="#dbe7f3" roughness={0.88} />
      </mesh>

      <mesh position={[0.05, 0.48, 0]}>
        <boxGeometry args={[0.05, 0.26, 0.05]} />
        <meshStandardMaterial color="#dbe7f3" roughness={0.88} />
      </mesh>

      <mesh position={[-0.06, 0.16, 0]}>
        <boxGeometry args={[0.05, 0.24, 0.05]} />
        <meshStandardMaterial color="#dbe7f3" roughness={0.88} />
      </mesh>

      <mesh position={[0.06, 0.16, 0]}>
        <boxGeometry args={[0.05, 0.24, 0.05]} />
        <meshStandardMaterial color="#dbe7f3" roughness={0.88} />
      </mesh>

      {active ? (
        <>
          <mesh position={[0, 0.5, 0]}>
            <torusGeometry args={[0.34, 0.03, 16, 40]} />
            <meshBasicMaterial color="#1a8aff" />
          </mesh>
          <mesh position={[0, 0.5, 0]}>
            <torusGeometry args={[0.42, 0.012, 16, 40]} />
            <meshBasicMaterial color="#1a8aff" transparent opacity={0.35} />
          </mesh>
        </>
      ) : null}

      {label ? (
        <DreiText
          position={[0, 1.42, 0]}
          fontSize={0.11}
          color="#0f172a"
          anchorX="center"
          anchorY="middle"
          fontWeight={700}
        >
          {label}
        </DreiText>
      ) : null}

      {role ? (
        <DreiText
          position={[0, 1.58, 0]}
          fontSize={0.075}
          color="#64748b"
          anchorX="center"
          anchorY="middle"
          maxWidth={1.5}
        >
          {role}
        </DreiText>
      ) : null}

      {typeof workload === "number" ? (
        <DreiText
          position={[0, 1.72, 0]}
          fontSize={0.072}
          color={tint}
          anchorX="center"
          anchorY="middle"
        >
          {`Load ${workload}`}
        </DreiText>
      ) : null}
    </group>
  );
}

function WorkforceUnit({
  position,
  tint,
  label,
  role,
  workload,
  displayTag,
  active = false,
  runtimeStatus,
  runtimeCount,
  onClick,
}: {
  position: [number, number, number];
  tint: string;
  label?: string;
  role?: string;
  workload?: number;
  displayTag?: string;
  active?: boolean;
  runtimeStatus?: WorkflowRunStatus;
  runtimeCount?: number;
  onClick?: () => void;
}) {
  const normalizedTag = (displayTag ?? "").trim().toUpperCase();
  const isAi = normalizedTag === "AGENT";

  if (isAi) {
    return (
      <MiniBot
        position={position}
        tint={tint}
        label={label}
        role={role}
        workload={workload}
        displayTag={normalizedTag}
        active={active}
        runtimeStatus={runtimeStatus}
        runtimeCount={runtimeCount}
        onClick={onClick}
      />
    );
  }

  return (
    <HumanWorker
      position={position}
      tint={tint}
      label={label}
      role={role}
      workload={workload}
      active={active}
      onClick={onClick}
    />
  );
}

function MetricPad({
  position,
  label,
  value,
  accent = "#1a8aff",
}: {
  position: [number, number, number];
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <group position={position}>
      <mesh position={[0, 0.06, 0]}>
        <boxGeometry args={[1.95, 0.12, 1.15]} />
        <meshStandardMaterial color="#ffffff" roughness={0.94} metalness={0.02} />
      </mesh>
      <mesh position={[0, 0.125, 0]}>
        <boxGeometry args={[1.95, 0.01, 1.15]} />
        <meshBasicMaterial color={accent} transparent opacity={0.14} />
      </mesh>
      <DreiText
        position={[0, 0.16, -0.16]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.14}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        {label}
      </DreiText>
      <DreiText
        position={[0, 0.16, 0.18]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.22}
        color="#0f172a"
        anchorX="center"
        anchorY="middle"
      >
        {value}
      </DreiText>
    </group>
  );
}


function MarketingOperatorSummary({
  position,
  label,
  operatorId,
  status,
  activeTaskCount,
  queued,
  running,
  waitingApproval,
  failed,
  completed,
  currentStep,
  approvalTitle,
  onOpenStream,
}: {
  position: [number, number, number];
  label: string;
  operatorId: string;
  status?: WorkflowRunStatus | "idle";
  activeTaskCount: number;
  queued: number;
  running: number;
  waitingApproval: number;
  failed: number;
  completed: number;
  currentStep?: string;
  approvalTitle?: string;
  onOpenStream?: () => void;
}) {
  const tone = runtimeStatusColor(
    status && status !== "idle" ? (status as WorkflowRunStatus) : undefined,
  );

  const badge = runtimeStatusLabel(
    status && status !== "idle" ? (status as WorkflowRunStatus) : undefined,
  );

  return (
    <group position={position}>
      <mesh position={[0, 0.08, 0]}>
        <boxGeometry args={[5.8, 0.14, 1.6]} />
        <meshStandardMaterial color="#ffffff" roughness={0.94} metalness={0.02} />
      </mesh>

      <mesh position={[0, 0.155, 0]}>
        <boxGeometry args={[5.8, 0.01, 1.6]} />
        <meshBasicMaterial color="#1a8aff" transparent opacity={0.08} />
      </mesh>

      <DreiText
        position={[-2.15, 0.17, -0.42]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.13}
        color="#64748b"
        anchorX="left"
        anchorY="middle"
      >
        {"LIVE OPERATOR"}
      </DreiText>

      <DreiText
        position={[-2.15, 0.17, -0.12]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.22}
        color="#0f172a"
        anchorX="left"
        anchorY="middle"
      >
        {label}
      </DreiText>

      <DreiText
        position={[-2.15, 0.17, 0.14]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.1}
        color="#64748b"
        anchorX="left"
        anchorY="middle"
      >
        {operatorId}
      </DreiText>

      <mesh position={[1.82, 0.165, -0.2]}>
        <boxGeometry args={[1.1, 0.01, 0.34]} />
        <meshBasicMaterial color={tone} transparent opacity={0.16} />
      </mesh>

      <DreiText
        position={[1.82, 0.17, -0.2]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.11}
        color={tone}
        anchorX="center"
        anchorY="middle"
      >
        {badge ?? "IDLE"}
      </DreiText>

      <DreiText
        position={[-0.35, 0.17, -0.48]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.09}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        {"Queued"}
      </DreiText>
      <DreiText
        position={[-0.35, 0.17, -0.2]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.18}
        color="#475569"
        anchorX="center"
        anchorY="middle"
      >
        {`${queued}`}
      </DreiText>

      <DreiText
        position={[0.4, 0.17, -0.48]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.09}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        {"Running"}
      </DreiText>
      <DreiText
        position={[0.4, 0.17, -0.2]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.18}
        color="#1a8aff"
        anchorX="center"
        anchorY="middle"
      >
        {`${running}`}
      </DreiText>

      <DreiText
        position={[1.15, 0.17, -0.48]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.09}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        {"Waiting"}
      </DreiText>
      <DreiText
        position={[1.15, 0.17, -0.2]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.18}
        color="#f59e0b"
        anchorX="center"
        anchorY="middle"
      >
        {`${waitingApproval}`}
      </DreiText>

      <DreiText
        position={[1.9, 0.17, 0.42]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.09}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        {"Done"}
      </DreiText>
      <DreiText
        position={[1.9, 0.17, 0.7]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.18}
        color="#22c55e"
        anchorX="center"
        anchorY="middle"
      >
        {`${completed}`}
      </DreiText>

      <DreiText
        position={[1.15, 0.17, 0.42]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.09}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        {"Failed"}
      </DreiText>
      <DreiText
        position={[1.15, 0.17, 0.7]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.18}
        color="#ef4444"
        anchorX="center"
        anchorY="middle"
      >
        {`${failed}`}
      </DreiText>

      <DreiText
        position={[0.15, 0.17, 0.42]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.09}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        {"Active Tasks"}
      </DreiText>
      <DreiText
        position={[0.15, 0.17, 0.7]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.18}
        color="#8b5cf6"
        anchorX="center"
        anchorY="middle"
      >
        {`${activeTaskCount}`}
      </DreiText>

      <DreiText
        position={[-2.15, 0.17, 0.48]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.09}
        color="#64748b"
        anchorX="left"
        anchorY="middle"
      >
        {`Step: ${currentStep ?? "—"}`}
      </DreiText>

      {approvalTitle ? (
        <DreiText
          position={[-2.15, 0.17, 0.74]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={0.09}
          color="#b45309"
          anchorX="left"
          anchorY="middle"
          maxWidth={3.1}
        >
          {`Approval: ${approvalTitle}`}
        </DreiText>
      ) : null}

      {onOpenStream ? (
        <Html position={[2.1, 0.2, 0.38]} center transform occlude>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpenStream();
            }}
            style={{
              borderRadius: 999,
              border: "1px solid rgba(26,138,255,0.35)",
              background: "rgba(26,138,255,0.1)",
              color: "#0f4ea8",
              padding: "6px 10px",
              fontSize: 11,
              fontWeight: 700,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            Open stream
          </button>
        </Html>
      ) : null}
    </group>
  );
}

function StageNode({
  position,
  stage,
  active = false,
  onClick,
}: {
  position: [number, number, number];
  stage: DepartmentFloorStage;
  active?: boolean;
  onClick?: () => void;
}) {
  const color = seatStateColor(stage.state);

  return (
    <group position={position}>
      <mesh
        position={[0, 0.08, 0]}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.();
        }}
      >
        <cylinderGeometry args={[0.72, 0.72, 0.12, 24]} />
        <meshStandardMaterial color="#ffffff" roughness={0.92} metalness={0.03} />
      </mesh>

      <mesh position={[0, 0.145, 0]}>
        <cylinderGeometry args={[0.72, 0.72, 0.01, 24]} />
        <meshBasicMaterial color={color} transparent opacity={active ? 0.28 : 0.14} />
      </mesh>

      <mesh position={[0, 0.16, 0.55]}>
        <circleGeometry args={[0.09, 20]} />
        <meshBasicMaterial color={color} />
      </mesh>

      {active ? (
        <mesh position={[0, 0.17, 0]}>
          <torusGeometry args={[0.8, 0.035, 16, 48]} />
          <meshBasicMaterial color="#1a8aff" />
        </mesh>
      ) : null}

      <DreiText
        position={[0, 0.2, -0.08]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.12}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        {stage.label}
      </DreiText>

      <DreiText
        position={[0, 0.2, 0.16]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.22}
        color="#0f172a"
        anchorX="center"
        anchorY="middle"
      >
        {`${stage.count}`}
      </DreiText>

      {typeof stage.value === "number" ? (
        <DreiText
          position={[0, 0.2, 0.4]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={0.095}
          color="#0f4ea8"
          anchorX="center"
          anchorY="middle"
        >
          {fmtMoney(stage.value)}
        </DreiText>
      ) : null}
    </group>
  );
}

function FlowLink({
  from,
  to,
  flow,
  active = false,
  onClick,
}: {
  from: [number, number, number];
  to: [number, number, number];
  flow: DepartmentFloorStage | DepartmentFloorAgent | any;
  active?: boolean;
  onClick?: () => void;
}) {
  const baseColor =
    flow.exception || (flow.blockedCount ?? 0) > 0
      ? "#ef4444"
      : flow.bottleneck
        ? "#f59e0b"
        : seatStateColor(flow.state);

  const lineWidth =
    active
      ? 4
      : flow.bottleneck
        ? 3
        : 1 + Math.min((flow.count ?? 0) / 20, 3);

  const midX = (from[0] + to[0]) / 2;
  const midZ = (from[2] + to[2]) / 2;

  return (
    <group
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
    >
      <DreiLine
        points={[
          new THREE.Vector3(from[0], 0.1, from[2]),
          new THREE.Vector3(to[0], 0.1, to[2]),
        ]}
        color={baseColor}
        lineWidth={lineWidth}
        transparent
        opacity={active ? 0.95 : flow.exception || flow.bottleneck ? 0.8 : 0.5}
      />

      <mesh position={[midX, 0.11, midZ]}>
        <circleGeometry args={[active ? 0.2 : 0.15, 20]} />
        <meshBasicMaterial
          color={active ? "#1a8aff" : baseColor}
          transparent
          opacity={active ? 0.25 : 0.12}
        />
      </mesh>

      <DreiText
        position={[midX, 0.18, midZ]}
        rotation={[-Math.PI / 2, 0, 0]}
        fontSize={0.09}
        color="#334155"
        anchorX="center"
        anchorY="middle"
      >
        {`${flow.count ?? 0}`}
      </DreiText>

      {flow.blockedCount ? (
        <DreiText
          position={[midX, 0.18, midZ + 0.22]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={0.075}
          color="#ef4444"
          anchorX="center"
          anchorY="middle"
        >
          {`${flow.blockedCount} blocked`}
        </DreiText>
      ) : null}
    </group>
  );
}

function SalesFloor({
  position,
  seat,
  floor,
  selectedInspectorTarget,
  onInspectorTargetChange,
}: {
  position: [number, number, number];
  seat?: Seat;
  floor?: SalesFloorState;
  selectedInspectorTarget: BoardroomInspectorTarget | null;
  onInspectorTargetChange: (target: BoardroomInspectorTarget) => void;
}) {
  const getKpi = (label: string) =>
    seat?.kpis?.find((k) => k.label.toLowerCase() === label.toLowerCase());

  const closeRate = getKpi("Close Rate");
  const orders = getKpi("Orders");
  const sellThrough = getKpi("Sell Through");
  const staleDealsKpi = getKpi("Stale Deals");
  const activeTasks = seat?.tasks?.filter((t) => t.state !== "done").length ?? 0;

  const stagePositions: [number, number, number][] = [
    [-3.7, 0, -0.05],
    [-1.2, 0, -0.6],
    [1.3, 0, -0.25],
    [3.75, 0, -0.85],
    [3.55, 0, 1.2],
  ];

  const agentPositions: [number, number, number][] = [
    [-2.35, 0, 2.2],
    [0, 0, 2.55],
    [2.35, 0, 2.15],
    [3.5, 0, 2.0],
  ];

  const agents = floor?.agents ?? [];
  const stages = floor?.stages ?? [];
  const flows = floor?.flows ?? [];

  const staleDeals =
    typeof staleDealsKpi?.value === "number"
      ? staleDealsKpi.value
      : floor?.stages?.find((s) => s.label.toLowerCase() === "stale")?.count ?? 0;

  return (
    <group position={position}>
      <MetricPad
        position={[-2.7, 0, -2.55]}
        label="Close Rate"
        value={fmtAny(closeRate?.value, closeRate?.unit)}
      />
      <MetricPad
        position={[0, 0, -2.65]}
        label="Orders"
        value={fmtAny(orders?.value, orders?.unit)}
        accent="#22c55e"
      />
      <MetricPad
        position={[2.7, 0, -2.55]}
        label="Sell Through"
        value={fmtAny(sellThrough?.value, sellThrough?.unit)}
        accent="#f59e0b"
      />

      <MetricPad
        position={[-1.35, 0, 4.05]}
        label="Stale Deals"
        value={`${staleDeals}`}
        accent="#ef4444"
      />
      <MetricPad
        position={[1.35, 0, 4.05]}
        label="Active Tasks"
        value={`${activeTasks}`}
        accent="#8b5cf6"
      />

      {stages.map((stage) => {
        const p = getStagePositionByIndex(stage.id, stages, stagePositions);
        if (!p) return null;

        const isActive =
          selectedInspectorTarget?.kind === "sales_stage" &&
          selectedInspectorTarget.stageId === stage.id;

        return (
          <StageNode
            key={stage.id}
            position={p}
            stage={stage}
            active={isActive}
            onClick={() =>
              onInspectorTargetChange({
                kind: "sales_stage",
                stageId: stage.id,
              })
            }
          />
        );
      })}

      {flows.map((flow) => {
        const from = getStagePositionByIndex(flow.fromStageId, stages, stagePositions);
        const to = getStagePositionByIndex(flow.toStageId, stages, stagePositions);
        if (!from || !to) return null;

        return (
          <FlowLink
            key={flow.id}
            from={from}
            to={to}
            flow={flow}
            active={isSalesFlowTarget(selectedInspectorTarget, flow.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "sales_flow",
                flowId: flow.id,
              })
            }
          />
        );
      })}

      {agents.map((agent) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        const isActive =
          selectedInspectorTarget?.kind === "sales_agent" &&
          selectedInspectorTarget.agentId === agent.id;

        return (
          <WorkforceUnit
            key={agent.id}
            position={[p[0], 0.15, p[2]]}
            tint={seatStateColor(agent.state)}
            label={agent.label}
            role={agent.role}
            workload={agent.workload}
            displayTag={agent.displayTag}
            active={isActive}
            onClick={() =>
              onInspectorTargetChange({
                kind: "sales_agent",
                agentId: agent.id,
              })
            }
          />
        );
      })}

      {agents.map((agent, index) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        const hub = getIndexedPosition(
          Math.min(index, Math.max(stages.length - 1, 0)),
          stagePositions,
        );
        if (!hub) return null;

        return (
          <DreiLine
            key={`agent-line-${agent.id}`}
            points={[
              new THREE.Vector3(hub[0], 0.08, hub[2] + 0.15),
              new THREE.Vector3(p[0], 0.08, p[2] - 0.35),
            ]}
            color={seatStateColor(agent.state)}
            lineWidth={1}
            transparent
            opacity={0.4}
          />
        );
      })}
    </group>
  );
}

function FinanceFloor({
  position,
  seat,
  floor,
  selectedInspectorTarget,
  onInspectorTargetChange,
}: {
  position: [number, number, number];
  seat?: Seat;
  floor?: FinanceFloorState;
  selectedInspectorTarget: BoardroomInspectorTarget | null;
  onInspectorTargetChange: (target: BoardroomInspectorTarget) => void;
}) {
  const getKpi = (label: string) =>
    seat?.kpis?.find((k) => k.label.toLowerCase() === label.toLowerCase());

  const cashOnHand = getKpi("Cash On Hand");
  const debtorDays = getKpi("Debtor Days");
  const creditorDays = getKpi("Creditor Days");
  const grossMargin = getKpi("Gross Margin");
  const netCash30d = getKpi("30d Net Cash");

  const stagePositions: [number, number, number][] = [
    [-3.7, 0, -0.15],
    [-1.25, 0, -0.55],
    [1.35, 0, -0.15],
    [3.7, 0, -0.7],
    [3.35, 0, 1.25],
  ];

  const agentPositions: [number, number, number][] = [
    [-1.95, 0, 1.95],
    [0, 0, 2.25],
    [1.95, 0, 1.9],
    [3.45, 0, 2.0],
  ];

  const agents = floor?.agents ?? [];
  const stages = floor?.stages ?? [];
  const flows = floor?.flows ?? [];

  return (
    <group position={position}>
      <MetricPad
        position={[-2.35, 0, -2.2]}
        label="Cash"
        value={fmtAny(cashOnHand?.value, cashOnHand?.unit)}
        accent="#22c55e"
      />
      <MetricPad
        position={[0, 0, -2.3]}
        label="Debtor Days"
        value={fmtAny(debtorDays?.value, debtorDays?.unit)}
        accent="#f59e0b"
      />
      <MetricPad
        position={[2.35, 0, -2.2]}
        label="Creditor Days"
        value={fmtAny(creditorDays?.value, creditorDays?.unit)}
        accent="#1a8aff"
      />

      <MetricPad
        position={[-1.2, 0, 3.15]}
        label="Gross Margin"
        value={fmtAny(grossMargin?.value, grossMargin?.unit)}
        accent="#8b5cf6"
      />
      <MetricPad
        position={[1.2, 0, 3.15]}
        label="30d Net Cash"
        value={fmtAny(netCash30d?.value, netCash30d?.unit)}
        accent="#ef4444"
      />

      {stages.map((stage) => {
        const p = getStagePositionByIndex(stage.id, stages, stagePositions);
        if (!p) return null;

        return (
          <StageNode
            key={stage.id}
            position={p}
            stage={stage}
            active={isFinanceStageTarget(selectedInspectorTarget, stage.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "finance_stage",
                stageId: stage.id,
              })
            }
          />
        );
      })}

      {flows.map((flow) => {
        const from = getStagePositionByIndex(flow.fromStageId, stages, stagePositions);
        const to = getStagePositionByIndex(flow.toStageId, stages, stagePositions);
        if (!from || !to) return null;

        return (
          <FlowLink
            key={flow.id}
            from={from}
            to={to}
            flow={flow}
            active={isFinanceFlowTarget(selectedInspectorTarget, flow.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "finance_flow",
                flowId: flow.id,
              })
            }
          />
        );
      })}

      {agents.map((agent) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        return (
          <WorkforceUnit
            key={agent.id}
            position={[p[0], 0.15, p[2]]}
            tint={seatStateColor(agent.state)}
            label={agent.label}
            role={agent.role}
            workload={agent.workload}
            displayTag={agent.displayTag}
            active={isFinanceAgentTarget(selectedInspectorTarget, agent.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "finance_agent",
                agentId: agent.id,
              })
            }
          />
        );
      })}

      {agents.map((agent, index) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        const hub = getIndexedPosition(
          Math.min(index, Math.max(stages.length - 1, 0)),
          stagePositions,
        );
        if (!hub) return null;

        return (
          <DreiLine
            key={`finance-agent-line-${agent.id}`}
            points={[
              new THREE.Vector3(hub[0], 0.08, hub[2] + 0.15),
              new THREE.Vector3(p[0], 0.08, p[2] - 0.35),
            ]}
            color={seatStateColor(agent.state)}
            lineWidth={1}
            transparent
            opacity={0.4}
          />
        );
      })}
    </group>
  );
}

function OperationsFloor({
  position,
  seat,
  floor,
  selectedInspectorTarget,
  onInspectorTargetChange,
}: {
  position: [number, number, number];
  seat?: Seat;
  floor?: OperationsFloorState;
  selectedInspectorTarget: BoardroomInspectorTarget | null;
  onInspectorTargetChange: (target: BoardroomInspectorTarget) => void;
}) {
  const getKpi = (label: string) =>
    seat?.kpis?.find((k) => k.label.toLowerCase() === label.toLowerCase());

  const backlog = getKpi("Backlog");
  const blockedJobs = getKpi("Blocked Jobs");
  const turnaround = getKpi("Turnaround");
  const fulfilment = getKpi("Fulfilment");
  const capacityUsed = getKpi("Capacity Used");

  const stagePositions: [number, number, number][] = [
    [-3.7, 0, -0.15],
    [-1.25, 0, -0.55],
    [1.35, 0, -0.15],
    [3.7, 0, -0.7],
    [3.35, 0, 1.25],
  ];

  const agentPositions: [number, number, number][] = [
    [-1.95, 0, 1.95],
    [0, 0, 2.25],
    [1.95, 0, 1.9],
    [3.45, 0, 2.0],
  ];

  const agents = floor?.agents ?? [];
  const stages = floor?.stages ?? [];
  const flows = floor?.flows ?? [];

  return (
    <group position={position}>
      <MetricPad
        position={[-2.35, 0, -2.2]}
        label="Backlog"
        value={fmtAny(backlog?.value, backlog?.unit)}
        accent="#f59e0b"
      />
      <MetricPad
        position={[0, 0, -2.3]}
        label="Blocked Jobs"
        value={fmtAny(blockedJobs?.value, blockedJobs?.unit)}
        accent="#ef4444"
      />
      <MetricPad
        position={[2.35, 0, -2.2]}
        label="Turnaround"
        value={fmtAny(turnaround?.value, turnaround?.unit)}
        accent="#1a8aff"
      />

      <MetricPad
        position={[-1.2, 0, 3.15]}
        label="Fulfilment"
        value={fmtAny(fulfilment?.value, fulfilment?.unit)}
        accent="#22c55e"
      />
      <MetricPad
        position={[1.2, 0, 3.15]}
        label="Capacity Used"
        value={fmtAny(capacityUsed?.value, capacityUsed?.unit)}
        accent="#8b5cf6"
      />

      {stages.map((stage) => {
        const p = getStagePositionByIndex(stage.id, stages, stagePositions);
        if (!p) return null;

        return (
          <StageNode
            key={stage.id}
            position={p}
            stage={stage}
            active={isOperationsStageTarget(selectedInspectorTarget, stage.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "operations_stage",
                stageId: stage.id,
              })
            }
          />
        );
      })}

      {flows.map((flow) => {
        const from = getStagePositionByIndex(flow.fromStageId, stages, stagePositions);
        const to = getStagePositionByIndex(flow.toStageId, stages, stagePositions);
        if (!from || !to) return null;

        return (
          <FlowLink
            key={flow.id}
            from={from}
            to={to}
            flow={flow}
            active={isOperationsFlowTarget(selectedInspectorTarget, flow.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "operations_flow",
                flowId: flow.id,
              })
            }
          />
        );
      })}

      {agents.map((agent) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        return (
          <WorkforceUnit
            key={agent.id}
            position={[p[0], 0.15, p[2]]}
            tint={seatStateColor(agent.state)}
            label={agent.label}
            role={agent.role}
            workload={agent.workload}
            displayTag={agent.displayTag}
            active={isOperationsAgentTarget(selectedInspectorTarget, agent.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "operations_agent",
                agentId: agent.id,
              })
            }
          />
        );
      })}

      {agents.map((agent, index) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        const hub = getIndexedPosition(
          Math.min(index, Math.max(stages.length - 1, 0)),
          stagePositions,
        );
        if (!hub) return null;

        return (
          <DreiLine
            key={`operations-agent-line-${agent.id}`}
            points={[
              new THREE.Vector3(hub[0], 0.08, hub[2] + 0.15),
              new THREE.Vector3(p[0], 0.08, p[2] - 0.35),
            ]}
            color={seatStateColor(agent.state)}
            lineWidth={1}
            transparent
            opacity={0.4}
          />
        );
      })}
    </group>
  );
}

function SupportFloor({
  position,
  seat,
  floor,
  selectedInspectorTarget,
  onInspectorTargetChange,
}: {
  position: [number, number, number];
  seat?: Seat;
  floor?: SupportFloorState;
  selectedInspectorTarget: BoardroomInspectorTarget | null;
  onInspectorTargetChange: (target: BoardroomInspectorTarget) => void;
}) {
  const getKpi = (label: string) =>
    seat?.kpis?.find((k) => k.label.toLowerCase() === label.toLowerCase());

  const sla = getKpi("SLA");
  const openTickets = getKpi("Open Tickets");
  const escalations = getKpi("Escalations");
  const activeTasks = seat?.tasks?.filter((t) => t.state !== "done").length ?? 0;
  const dueToday = seat?.dueToday ?? 0;

  const stagePositions: [number, number, number][] = [
    [-3.7, 0, -0.15],
    [-1.25, 0, -0.55],
    [1.35, 0, -0.15],
    [3.7, 0, -0.7],
    [3.35, 0, 1.25],
  ];

  const agentPositions: [number, number, number][] = [
    [-1.95, 0, 1.95],
    [0, 0, 2.25],
    [1.95, 0, 1.9],
    [3.45, 0, 2.0],
  ];

  const agents = floor?.agents ?? [];
  const stages = floor?.stages ?? [];
  const flows = floor?.flows ?? [];

  return (
    <group position={position}>
      <MetricPad
        position={[-2.35, 0, -2.2]}
        label="SLA"
        value={fmtAny(sla?.value, sla?.unit)}
        accent="#22c55e"
      />
      <MetricPad
        position={[0, 0, -2.3]}
        label="Open Tickets"
        value={fmtAny(openTickets?.value, openTickets?.unit)}
        accent="#1a8aff"
      />
      <MetricPad
        position={[2.35, 0, -2.2]}
        label="Escalations"
        value={fmtAny(escalations?.value, escalations?.unit)}
        accent="#ef4444"
      />

      <MetricPad
        position={[-1.2, 0, 3.15]}
        label="Active Tasks"
        value={`${activeTasks}`}
        accent="#8b5cf6"
      />
      <MetricPad
        position={[1.2, 0, 3.15]}
        label="Due Today"
        value={`${dueToday}`}
        accent="#f59e0b"
      />

      {stages.map((stage) => {
        const p = getStagePositionByIndex(stage.id, stages, stagePositions);
        if (!p) return null;

        return (
          <StageNode
            key={stage.id}
            position={p}
            stage={stage}
            active={isSupportStageTarget(selectedInspectorTarget, stage.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "support_stage",
                stageId: stage.id,
              })
            }
          />
        );
      })}

      {flows.map((flow) => {
        const from = getStagePositionByIndex(flow.fromStageId, stages, stagePositions);
        const to = getStagePositionByIndex(flow.toStageId, stages, stagePositions);
        if (!from || !to) return null;

        return (
          <FlowLink
            key={flow.id}
            from={from}
            to={to}
            flow={flow}
            active={isSupportFlowTarget(selectedInspectorTarget, flow.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "support_flow",
                flowId: flow.id,
              })
            }
          />
        );
      })}

      {agents.map((agent) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        return (
          <WorkforceUnit
            key={agent.id}
            position={[p[0], 0.15, p[2]]}
            tint={seatStateColor(agent.state)}
            label={agent.label}
            role={agent.role}
            workload={agent.workload}
            displayTag={agent.displayTag}
            active={isSupportAgentTarget(selectedInspectorTarget, agent.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "support_agent",
                agentId: agent.id,
              })
            }
          />
        );
      })}

      {agents.map((agent, index) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        const hub = getIndexedPosition(
          Math.min(index, Math.max(stages.length - 1, 0)),
          stagePositions,
        );
        if (!hub) return null;

        return (
          <DreiLine
            key={`support-agent-line-${agent.id}`}
            points={[
              new THREE.Vector3(hub[0], 0.08, hub[2] + 0.15),
              new THREE.Vector3(p[0], 0.08, p[2] - 0.35),
            ]}
            color={seatStateColor(agent.state)}
            lineWidth={1}
            transparent
            opacity={0.4}
          />
        );
      })}
    </group>
  );
}

function HrFloor({
  position,
  seat,
  floor,
  selectedInspectorTarget,
  onInspectorTargetChange,
}: {
  position: [number, number, number];
  seat?: Seat;
  floor?: HRFloorState;
  selectedInspectorTarget: BoardroomInspectorTarget | null;
  onInspectorTargetChange: (target: BoardroomInspectorTarget) => void;
}) {
  const getKpi = (label: string) =>
    seat?.kpis?.find((k) => k.label.toLowerCase() === label.toLowerCase());

  const openAdminActions = getKpi("Open Admin Actions");
  const avgResponse = getKpi("Avg Response");
  const compliance = getKpi("Compliance");
  const activeTasks = seat?.tasks?.filter((t) => t.state !== "done").length ?? 0;
  const dueToday = seat?.dueToday ?? 0;

  const stagePositions: [number, number, number][] = [
    [-3.7, 0, -0.15],
    [-1.25, 0, -0.55],
    [1.35, 0, -0.15],
    [3.7, 0, -0.7],
    [3.35, 0, 1.25],
  ];

  const agentPositions: [number, number, number][] = [
    [-1.95, 0, 1.95],
    [0, 0, 2.25],
    [1.95, 0, 1.9],
    [3.45, 0, 2.0],
  ];

  const agents = floor?.agents ?? [];
  const stages = floor?.stages ?? [];
  const flows = floor?.flows ?? [];

  return (
    <group position={position}>
      <MetricPad
        position={[-2.35, 0, -2.2]}
        label="Open Actions"
        value={fmtAny(openAdminActions?.value, openAdminActions?.unit)}
        accent="#1a8aff"
      />
      <MetricPad
        position={[0, 0, -2.3]}
        label="Avg Response"
        value={fmtAny(avgResponse?.value, avgResponse?.unit)}
        accent="#22c55e"
      />
      <MetricPad
        position={[2.35, 0, -2.2]}
        label="Compliance"
        value={fmtAny(compliance?.value, compliance?.unit)}
        accent="#8b5cf6"
      />

      <MetricPad
        position={[-1.2, 0, 3.15]}
        label="Active Tasks"
        value={`${activeTasks}`}
        accent="#f59e0b"
      />
      <MetricPad
        position={[1.2, 0, 3.15]}
        label="Due Today"
        value={`${dueToday}`}
        accent="#ef4444"
      />

      {stages.map((stage) => {
        const p = getStagePositionByIndex(stage.id, stages, stagePositions);
        if (!p) return null;

        return (
          <StageNode
            key={stage.id}
            position={p}
            stage={stage}
            active={isHrStageTarget(selectedInspectorTarget, stage.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "hr_stage",
                stageId: stage.id,
              })
            }
          />
        );
      })}

      {flows.map((flow) => {
        const from = getStagePositionByIndex(flow.fromStageId, stages, stagePositions);
        const to = getStagePositionByIndex(flow.toStageId, stages, stagePositions);
        if (!from || !to) return null;

        return (
          <FlowLink
            key={flow.id}
            from={from}
            to={to}
            flow={flow}
            active={isHrFlowTarget(selectedInspectorTarget, flow.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "hr_flow",
                flowId: flow.id,
              })
            }
          />
        );
      })}

      {agents.map((agent) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        return (
          <WorkforceUnit
            key={agent.id}
            position={[p[0], 0.15, p[2]]}
            tint={seatStateColor(agent.state)}
            label={agent.label}
            role={agent.role}
            workload={agent.workload}
            displayTag={agent.displayTag}
            active={isHrAgentTarget(selectedInspectorTarget, agent.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "hr_agent",
                agentId: agent.id,
              })
            }
          />
        );
      })}

      {agents.map((agent, index) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        const hub = getIndexedPosition(
          Math.min(index, Math.max(stages.length - 1, 0)),
          stagePositions,
        );
        if (!hub) return null;

        return (
          <DreiLine
            key={`hr-agent-line-${agent.id}`}
            points={[
              new THREE.Vector3(hub[0], 0.08, hub[2] + 0.15),
              new THREE.Vector3(p[0], 0.08, p[2] - 0.35),
            ]}
            color={seatStateColor(agent.state)}
            lineWidth={1}
            transparent
            opacity={0.4}
          />
        );
      })}
    </group>
  );
}

function MarketingFloor({
  position,
  seat,
  floor,
  selectedInspectorTarget,
  onInspectorTargetChange,
  onOpenMarketingStream,
  laneCounts,
  runtimeByAgentId,
  operatorSummary,
}: {
  position: [number, number, number];
  seat?: Seat;
  floor?: MarketingFloorState;
  selectedInspectorTarget: BoardroomInspectorTarget | null;
  onInspectorTargetChange: (target: BoardroomInspectorTarget) => void;
  onOpenMarketingStream?: () => void;
  laneCounts?: {
    queued: number;
    running: number;
    waitingApproval: number;
    failed: number;
    completed: number;
  };
  runtimeByAgentId?: Record<
    string,
    {
      status?: WorkflowRunStatus;
      count: number;
    }
  >;
  operatorSummary?: {
    label: string;
    operatorId: string;
    status?: WorkflowRunStatus | "idle";
    activeTaskCount: number;
    currentStep?: string;
    approvalTitle?: string;
  };
}) {
  const getKpi = (label: string) =>
    seat?.kpis?.find((k) => k.label.toLowerCase() === label.toLowerCase());

  const leadVolume = getKpi("Lead Volume");
  const cac = getKpi("CAC");
  const ctr = getKpi("CTR");
  const qualifiedLeads = getKpi("Qualified Leads");
  const activeTasks = seat?.tasks?.filter((t) => t.state !== "done").length ?? 0;

  const stagePositions: [number, number, number][] = [
    [-3.7, 0, -0.15],
    [-1.25, 0, -0.55],
    [1.35, 0, -0.15],
    [3.7, 0, -0.7],
    [3.35, 0, 1.25],
  ];

  const agentPositions: [number, number, number][] = [
    [-1.95, 0, 1.95],
    [0, 0, 2.25],
    [1.95, 0, 1.9],
    [3.45, 0, 2.0],
  ];

  const agents = floor?.agents ?? [];
  const stages = floor?.stages ?? [];
  const flows = floor?.flows ?? [];

  const lanes = laneCounts ?? {
    queued: 0,
    running: 0,
    waitingApproval: 0,
    failed: 0,
    completed: 0,
  };

  return (
    <group position={position}>
      {operatorSummary ? (
        <MarketingOperatorSummary
          position={[0, 0, -4.1]}
          label={operatorSummary.label}
          operatorId={operatorSummary.operatorId}
          status={operatorSummary.status}
          activeTaskCount={operatorSummary.activeTaskCount}
          queued={lanes.queued}
          running={lanes.running}
          waitingApproval={lanes.waitingApproval}
          failed={lanes.failed}
          completed={lanes.completed}
          currentStep={operatorSummary.currentStep}
          approvalTitle={operatorSummary.approvalTitle}
          onOpenStream={onOpenMarketingStream}
        />
      ) : null}

      <MetricPad
        position={[-2.35, 0, -2.7]}
        label="Lead Volume"
        value={fmtAny(leadVolume?.value, leadVolume?.unit)}
        accent="#22c55e"
      />
      <MetricPad
        position={[0, 0, -2.8]}
        label="CAC"
        value={fmtAny(cac?.value, cac?.unit)}
        accent="#ef4444"
      />
      <MetricPad
        position={[2.35, 0, -2.7]}
        label="CTR"
        value={fmtAny(ctr?.value, ctr?.unit)}
        accent="#1a8aff"
      />

      <MetricPad
        position={[-1.2, 0, 3.0]}
        label="Qualified Leads"
        value={fmtAny(qualifiedLeads?.value, qualifiedLeads?.unit)}
        accent="#8b5cf6"
      />
      <MetricPad
        position={[1.2, 0, 3.0]}
        label="Active Tasks"
        value={`${activeTasks}`}
        accent="#f59e0b"
      />

      {stages.map((stage) => {
        const p = getStagePositionByIndex(stage.id, stages, stagePositions);
        if (!p) return null;

        return (
          <StageNode
            key={stage.id}
            position={p}
            stage={stage}
            active={isMarketingStageTarget(selectedInspectorTarget, stage.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "marketing_stage",
                stageId: stage.id,
              })
            }
          />
        );
      })}

      {flows.map((flow) => {
        const from = getStagePositionByIndex(flow.fromStageId, stages, stagePositions);
        const to = getStagePositionByIndex(flow.toStageId, stages, stagePositions);
        if (!from || !to) return null;

        return (
          <FlowLink
            key={flow.id}
            from={from}
            to={to}
            flow={flow}
            active={isMarketingFlowTarget(selectedInspectorTarget, flow.id)}
            onClick={() =>
              onInspectorTargetChange({
                kind: "marketing_flow",
                flowId: flow.id,
              })
            }
          />
        );
      })}

      {agents.map((agent) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        const runtimeMeta = runtimeByAgentId?.[agent.id];

        return (
          <WorkforceUnit
            key={agent.id}
            position={[p[0], 0.15, p[2]]}
            tint={seatStateColor(agent.state)}
            label={agent.label}
            role={agent.role}
            workload={agent.workload}
            displayTag={agent.displayTag}
            active={isMarketingAgentTarget(selectedInspectorTarget, agent.id)}
            runtimeStatus={runtimeMeta?.status}
            runtimeCount={runtimeMeta?.count}
            onClick={() =>
              onInspectorTargetChange({
                kind: "marketing_agent",
                agentId: agent.id,
              })
            }
          />
        );
      })}

      {agents.map((agent, index) => {
        const p = getAgentPositionByIndex(agent.id, agents, agentPositions);
        if (!p) return null;

        const hub = getIndexedPosition(
          Math.min(index, Math.max(stages.length - 1, 0)),
          stagePositions,
        );
        if (!hub) return null;

        return (
          <DreiLine
            key={`marketing-agent-line-${agent.id}`}
            points={[
              new THREE.Vector3(hub[0], 0.08, hub[2] + 0.15),
              new THREE.Vector3(p[0], 0.08, p[2] - 0.35),
            ]}
            color={seatStateColor(agent.state)}
            lineWidth={1}
            transparent
            opacity={0.4}
          />
        );
      })}
    </group>
  );
}

function ExecutiveBots() {
  return (
    <>
      <HumanWorker
        position={[-6.4, 0.15, -21.5]}
        tint="#60a5fa"
        label="CEO"
        role="Executive Lead"
      />

      <MiniBot
        position={[0, 0.15, -24]}
        tint="#8b5cf6"
        label="AION"
        role="System Intelligence"
        displayTag="AGENT"
        active
      />

      <MiniBot
        position={[6.4, 0.15, -21.5]}
        tint="#22c55e"
        label="OpenAI"
        role="Model Partner"
        displayTag="AGENT"
      />
    </>
  );
}

function RingGuide() {
  const lines = [
    ["coo", "marketing"],
    ["coo", "sales"],
    ["coo", "operations"],
    ["coo", "hr"],
    ["coo", "support"],
    ["coo", "finance"],
  ] as const;

  return (
    <>
      {lines.map(([a, b]) => (
        <DreiLine
          key={`${a}-${b}`}
          points={[
            new THREE.Vector3(...ZONES[a].position),
            new THREE.Vector3(...ZONES[b].position),
          ]}
          color="#8ea3bf"
          lineWidth={1}
          transparent
          opacity={0.26}
        />
      ))}
    </>
  );
}

function SalesFloatingCard({
  position,
  seat,
  floor,
  onClose,
}: {
  position: [number, number, number];
  seat?: Seat;
  floor?: SalesFloorState;
  onClose: () => void;
}) {
  const stageByIndex = (index: number) => floor?.stages?.[index];
  const agentByIndex = (index: number) => floor?.agents?.[index];

  const slides = [
    {
      id: "pipeline",
      title: "Sales Pipeline",
      lines: [
        `Pipeline: ${seat?.openTasks ?? "—"}`,
        `Functions: ${seat?.kpis?.find((k) => k.label === "Functions")?.value ?? "—"}`,
        `Revenue Streams: ${seat?.kpis?.find((k) => k.label === "Revenue Streams")?.value ?? "—"}`,
      ],
      tone: "#1a8aff",
    },
    {
      id: "stage-1",
      title: stageByIndex(0)?.label ?? "Stage 1",
      lines: [
        `Count: ${stageByIndex(0)?.count ?? "—"}`,
        `Value: ${typeof stageByIndex(0)?.value === "number" ? fmtMoney(stageByIndex(0)!.value!) : "—"}`,
        `State: ${stageByIndex(0)?.state ?? "—"}`,
      ],
      tone: "#22c55e",
    },
    {
      id: "stage-2",
      title: stageByIndex(1)?.label ?? "Stage 2",
      lines: [
        `Count: ${stageByIndex(1)?.count ?? "—"}`,
        `Value: ${typeof stageByIndex(1)?.value === "number" ? fmtMoney(stageByIndex(1)!.value!) : "—"}`,
        `State: ${stageByIndex(1)?.state ?? "—"}`,
      ],
      tone: "#1a8aff",
    },
    {
      id: "agent-1",
      title: agentByIndex(0)?.label ?? "Agent 1",
      lines: [
        `Role: ${agentByIndex(0)?.role ?? "—"}`,
        `Assigned: ${agentByIndex(0)?.assignedCount ?? "—"}`,
        `Throughput: ${agentByIndex(0)?.throughput ?? "—"}`,
      ],
      tone: "#f59e0b",
    },
    {
      id: "agent-2",
      title: agentByIndex(1)?.label ?? "Agent 2",
      lines: [
        `Role: ${agentByIndex(1)?.role ?? "—"}`,
        `Assigned: ${agentByIndex(1)?.assignedCount ?? "—"}`,
        `Throughput: ${agentByIndex(1)?.throughput ?? "—"}`,
      ],
      tone: "#ef4444",
    },
    {
      id: "summary",
      title: "Sales Summary",
      lines: [
        `Active Tasks: ${seat?.tasks?.filter((t) => t.state !== "done").length ?? "—"}`,
        `Stages: ${floor?.stages?.length ?? "—"}`,
        `Agents: ${floor?.agents?.length ?? "—"}`,
      ],
      tone: "#22c55e",
    },
  ];

  const [index, setIndex] = useState(0);
  const current = slides[index];

  return (
    <Html position={[position[0], position[1] + 3.4, position[2]]} center>
      <div
        style={{
          width: 320,
          borderRadius: 18,
          border: "1px solid rgba(26,138,255,0.28)",
          background: "rgba(255,255,255,0.96)",
          boxShadow: "0 18px 45px rgba(15,23,42,0.18)",
          overflow: "hidden",
          backdropFilter: "blur(8px)",
          pointerEvents: "auto",
        }}
      >
        <div
          style={{
            padding: "12px 14px",
            borderBottom: "1px solid rgba(226,232,240,1)",
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 10,
          }}
        >
          <div>
            <div style={{ fontSize: 11, color: "#64748b" }}>Sales Floor</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: "#0f172a" }}>
              {current.title}
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: current.tone,
                padding: "6px 10px",
                borderRadius: 999,
                background: "rgba(26,138,255,0.08)",
                border: "1px solid rgba(26,138,255,0.18)",
              }}
            >
              {index + 1} / {slides.length}
            </div>

            <button
              type="button"
              onClick={onClose}
              style={{
                width: 34,
                height: 34,
                borderRadius: 999,
                border: "1px solid rgba(148,163,184,0.22)",
                background: "#ffffff",
                color: "#334155",
                cursor: "pointer",
                fontSize: 18,
                lineHeight: "32px",
                textAlign: "center",
                fontWeight: 700,
              }}
              aria-label="Close sales card"
              title="Close"
            >
              ×
            </button>
          </div>
        </div>

        <div style={{ padding: 14, display: "grid", gap: 10 }}>
          {current.lines.map((line) => (
            <div
              key={line}
              style={{
                borderRadius: 12,
                background: "#f8fafc",
                border: "1px solid #e2e8f0",
                padding: "10px 12px",
                color: "#0f172a",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {line}
            </div>
          ))}
        </div>

        <div
          style={{
            padding: "12px 14px",
            borderTop: "1px solid rgba(226,232,240,1)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <button
            type="button"
            onClick={() =>
              setIndex((prev) => (prev - 1 + slides.length) % slides.length)
            }
            style={{
              width: 38,
              height: 38,
              borderRadius: 999,
              border: "1px solid rgba(148,163,184,0.28)",
              background: "#ffffff",
              color: "#0f172a",
              cursor: "pointer",
              fontSize: 18,
              fontWeight: 700,
            }}
          >
            ‹
          </button>

          <div style={{ fontSize: 12, color: "#64748b", fontWeight: 600 }}>
            {seat?.label ?? "Sales"}
          </div>

          <button
            type="button"
            onClick={() => setIndex((prev) => (prev + 1) % slides.length)}
            style={{
              width: 38,
              height: 38,
              borderRadius: 999,
              border: "1px solid rgba(148,163,184,0.28)",
              background: "#ffffff",
              color: "#0f172a",
              cursor: "pointer",
              fontSize: 18,
              fontWeight: 700,
            }}
          >
            ›
          </button>
        </div>
      </div>
    </Html>
  );
}

export default function QFCBoardroomWorld({
  frame,
  viewMode,
  activeZone,
  selectedSeatId,
  selectedInspectorTarget,
  onViewModeChange,
  onActiveZoneChange,
  onSeatSelect,
  onInspectorTargetChange,
  onCanvasClear,
}: BoardroomWorldProps) {
  const boardroomFrame = frame?.boardroomFrame;

  const pulse: BusinessPulse =
    boardroomFrame?.pulse ??
    frame?.pulse ??
    DEMO_PULSE;

  const seats: Seat[] =
    boardroomFrame?.seats ??
    frame?.boardroom?.seats ??
    DEMO_SEATS;

  const floors = boardroomFrame?.floors ?? DEMO_FLOORS;

  const runtimeRuns: RuntimeWorkflowRun[] = Array.isArray(boardroomFrame?.runtime?.runs)
    ? (boardroomFrame.runtime.runs as RuntimeWorkflowRun[])
    : Array.isArray(frame?.boardroom?.runtime?.runs)
      ? (frame.boardroom.runtime.runs as RuntimeWorkflowRun[])
      : [];

  const seatById = useMemo(
    () => new Map(seats.map((seat) => [seat.id, seat])),
    [seats],
  );

  const marketingRuns = useMemo(() => {
    return runtimeRuns.filter((run) => run.department_key === "marketing");
  }, [runtimeRuns]);

  const marketingLaneCounts = useMemo(() => {
    const marketingRuns = runtimeRuns.filter(
      (run) => run.department_key === "marketing",
    );

    return {
      queued: marketingRuns.filter((run) => run.status === "queued").length,
      running: marketingRuns.filter((run) => run.status === "running").length,
      waitingApproval: marketingRuns.filter(
        (run) => run.status === "waiting_approval",
      ).length,
      failed: marketingRuns.filter((run) => run.status === "failed").length,
      completed: marketingRuns.filter((run) => run.status === "completed").length,
    };
  }, [runtimeRuns]);

  const marketingApprovalTitle = useMemo(() => {
    const waitingRun = marketingRuns.find((run) => run.status === "waiting_approval");
    if (!waitingRun) return undefined;
    return waitingRun.workflow_label || waitingRun.workflow_key || "Approval pending";
  }, [marketingRuns]);

  const marketingRuntimeByAgentId = useMemo(() => {
    const priority: Record<WorkflowRunStatus, number> = {
      running: 6,
      waiting_approval: 5,
      failed: 4,
      queued: 3,
      completed: 2,
      cancelled: 1,
    };

    const out: Record<
      string,
      {
        status?: WorkflowRunStatus;
        count: number;
      }
    > = {};

    for (const run of marketingRuns) {
      if (!run.agent_id) continue;

      const existing = out[run.agent_id];

      if (!existing) {
        out[run.agent_id] = {
          status: run.status,
          count: 1,
        };
        continue;
      }

      out[run.agent_id] = {
        status:
          priority[run.status] > priority[existing.status ?? "cancelled"]
            ? run.status
            : existing.status,
        count: existing.count + 1,
      };
    }

    return out;
  }, [marketingRuns]);

  const marketingOperatorSummary = useMemo(() => {
    const sorted = [...marketingRuns].sort((a, b) => {
      const byPriority = runtimeStatusPriority(b.status) - runtimeStatusPriority(a.status);
      if (byPriority !== 0) return byPriority;

      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    });

    const primaryRun = sorted[0];

    return {
      label: "Marketing Agent v1",
      operatorId: "operator_marketing_v1",
      status: primaryRun?.status ?? "idle",
      activeTaskCount:
        marketingLaneCounts.running +
        marketingLaneCounts.waitingApproval +
        marketingLaneCounts.queued,
      currentStep: getRuntimeCurrentStepLabel(primaryRun),
      approvalTitle: marketingApprovalTitle,
    };
  }, [marketingApprovalTitle, marketingLaneCounts, marketingRuns]);

  const chips: BoardroomWorldZone[] = [
    "coo",
    "marketing",
    "sales",
    "operations",
    "hr",
    "support",
    "finance",
    "ceo",
    "aion",
    "openai",
  ];

  const zoneSeat = (zone: BoardroomWorldZone) => {
    const seatId = zoneToSeatId(zone);
    return seatId ? seatById.get(seatId) : undefined;
  };

  const isSelectedZone = (zone: BoardroomWorldZone) => {
    const seatId = zoneToSeatId(zone);
    return !!seatId && selectedSeatId === seatId;
  };

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        height: "100%",
      }}
    >
      <Canvas
        style={{ position: "absolute", inset: 0 }}
        camera={{ position: ZONES.coo.camera, fov: 40, near: 0.1, far: 300 }}
        onPointerMissed={() => onCanvasClear()}
      >
        <color attach="background" args={["#eef3f9"]} />
        <fog attach="fog" args={["#eef3f9", 45, 110]} />

        <ambientLight intensity={1.12} />
        <directionalLight position={[8, 14, 10]} intensity={1.15} />
        <directionalLight position={[-8, 8, -10]} intensity={0.45} />

        <gridHelper
          args={[
            80,
            80,
            new THREE.Color("#8fb8ea"),
            new THREE.Color("#c8ddf5"),
          ]}
          position={[0, -0.94, 0]}
        />

        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.96, 0]}>
          <planeGeometry args={[120, 120]} />
          <meshStandardMaterial color="#edf2f8" metalness={0.02} roughness={0.98} />
        </mesh>

        {viewMode === "boardroom" ? (
          <>
            <RingGuide />

            <HexFloor
              label="COO Core"
              position={ZONES.coo.position}
              tint={ZONES.coo.tint}
              active={activeZone === "coo" || isSelectedZone("coo")}
              onClick={() => {
                onActiveZoneChange("coo");
                onSeatSelect("seat_coo", "coo");
              }}
              scale={1.05}
              dark
              state={zoneSeat("coo")?.state}
            />

            {pulse ? <CooPulseOverlay position={ZONES.coo.position} pulse={pulse} /> : null}

            <HexFloor
              label="Marketing"
              position={ZONES.marketing.position}
              tint={ZONES.marketing.tint}
              active={activeZone === "marketing" || isSelectedZone("marketing")}
              onClick={() => {
                onInspectorTargetChange(null);
                onActiveZoneChange("marketing");
                onSeatSelect("seat_marketing", "marketing");
              }}
              scale={1.35}
              state={zoneSeat("marketing")?.state}
            />

            <MarketingFloor
              position={ZONES.marketing.position}
              seat={zoneSeat("marketing")}
              floor={floors?.marketing}
              selectedInspectorTarget={selectedInspectorTarget}
              onInspectorTargetChange={onInspectorTargetChange}
              onOpenMarketingStream={() => onViewModeChange("marketing_stream")}
              laneCounts={marketingLaneCounts}
              runtimeByAgentId={marketingRuntimeByAgentId}
              operatorSummary={marketingOperatorSummary}
            />

            <HexFloor
              label="Sales"
              position={ZONES.sales.position}
              tint={ZONES.sales.tint}
              active={activeZone === "sales" || isSelectedZone("sales")}
              onClick={() => {
                onInspectorTargetChange(null);
                onActiveZoneChange("sales");
                onSeatSelect("seat_sales", "sales");
              }}
              scale={1.48}
              state={zoneSeat("sales")?.state}
            />

            <SalesFloor
              position={ZONES.sales.position}
              seat={zoneSeat("sales")}
              floor={floors?.sales}
              selectedInspectorTarget={selectedInspectorTarget}
              onInspectorTargetChange={onInspectorTargetChange}
            />

            {selectedSeatId === "seat_sales" && (
              <SalesFloatingCard
                position={ZONES.sales.position}
                seat={zoneSeat("sales")}
                floor={floors?.sales}
                onClose={() => {
                  onInspectorTargetChange(null);
                  onCanvasClear();
                }}
              />
            )}

            <HexFloor
              label="Operations"
              position={ZONES.operations.position}
              tint={ZONES.operations.tint}
              active={activeZone === "operations" || isSelectedZone("operations")}
              onClick={() => {
                onInspectorTargetChange(null);
                onActiveZoneChange("operations");
                onSeatSelect("seat_ops", "operations");
              }}
              scale={1.48}
              state={zoneSeat("operations")?.state}
            />

            <OperationsFloor
              position={ZONES.operations.position}
              seat={zoneSeat("operations")}
              floor={floors?.operations}
              selectedInspectorTarget={selectedInspectorTarget}
              onInspectorTargetChange={onInspectorTargetChange}
            />

            <HexFloor
              label="HR"
              position={ZONES.hr.position}
              tint={ZONES.hr.tint}
              active={activeZone === "hr" || isSelectedZone("hr")}
              onClick={() => {
                onInspectorTargetChange(null);
                onActiveZoneChange("hr");
                onSeatSelect("seat_hr", "hr");
              }}
              scale={1.35}
              state={zoneSeat("hr")?.state}
            />

            <HrFloor
              position={ZONES.hr.position}
              seat={zoneSeat("hr")}
              floor={floors?.hr}
              selectedInspectorTarget={selectedInspectorTarget}
              onInspectorTargetChange={onInspectorTargetChange}
            />

            <HexFloor
              label="Support"
              position={ZONES.support.position}
              tint={ZONES.support.tint}
              active={activeZone === "support" || isSelectedZone("support")}
              onClick={() => {
                onInspectorTargetChange(null);
                onActiveZoneChange("support");
                onSeatSelect("seat_support", "support");
              }}
              scale={1.48}
              state={zoneSeat("support")?.state}
            />

            <SupportFloor
              position={ZONES.support.position}
              seat={zoneSeat("support")}
              floor={floors?.support}
              selectedInspectorTarget={selectedInspectorTarget}
              onInspectorTargetChange={onInspectorTargetChange}
            />

            <HexFloor
              label="Finance"
              position={ZONES.finance.position}
              tint={ZONES.finance.tint}
              active={activeZone === "finance" || isSelectedZone("finance")}
              onClick={() => {
                onInspectorTargetChange(null);
                onActiveZoneChange("finance");
                onSeatSelect("seat_finance", "finance");
              }}
              scale={1.48}
              state={zoneSeat("finance")?.state}
            />

            <FinanceFloor
              position={ZONES.finance.position}
              seat={zoneSeat("finance")}
              floor={floors?.finance}
              selectedInspectorTarget={selectedInspectorTarget}
              onInspectorTargetChange={onInspectorTargetChange}
            />

            <HexFloor
              label="CEO"
              position={ZONES.ceo.position}
              tint={ZONES.ceo.tint}
              active={activeZone === "ceo" || isSelectedZone("ceo")}
              onClick={() => {
                onActiveZoneChange("ceo");
                onSeatSelect("seat_ceo", "ceo");
              }}
              scale={1.05}
              state={zoneSeat("ceo")?.state}
            />

            <HexFloor
              label="AION"
              position={ZONES.aion.position}
              tint={ZONES.aion.tint}
              active={activeZone === "aion"}
              onClick={() => {
                onActiveZoneChange("aion");
                onCanvasClear();
              }}
              scale={1.08}
            />

            <HexFloor
              label="OpenAI"
              position={ZONES.openai.position}
              tint={ZONES.openai.tint}
              active={activeZone === "openai"}
              onClick={() => {
                onActiveZoneChange("openai");
                onCanvasClear();
              }}
              scale={1.05}
            />

            <ExecutiveBillboard position={[0, 0, -36]} />
            <ExecutiveBots />
          </>
        ) : viewMode === "operations_flow" ? (
          <OperationsFlowWorld
            pulse={pulse ?? DEMO_PULSE}
            seats={seats}
            salesFloor={floors?.sales}
            operationsFloor={floors?.operations}
            financeFloor={floors?.finance}
            supportFloor={floors?.support}
            hrFloor={floors?.hr}
            marketingFloor={floors?.marketing}
            selectedSeatId={selectedSeatId}
            selectedInspectorTarget={selectedInspectorTarget}
            onActiveZoneChange={onActiveZoneChange}
            onSeatSelect={onSeatSelect}
            onInspectorTargetChange={onInspectorTargetChange}
          />
        ) : null}

        <CameraRig activeZone={activeZone} />
      </Canvas>

      <div
        style={{
          position: "absolute",
          left: 14,
          bottom: 14,
          zIndex: 20,
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
          maxWidth: "85%",
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            pointerEvents: "auto",
          }}
        >
          {(
            [
              "boardroom",
              "dashboard",
              "marketing_stream",
              "brand_foundation",
              "live_agents",
              "operations_flow",
            ] as const
          ).map((mode) => {
            const active = viewMode === mode;

            return (
              <button
                key={mode}
                type="button"
                onClick={() => onViewModeChange(mode)}
                style={{
                  borderRadius: 999,
                  border: active
                    ? "1px solid rgba(26,138,255,0.55)"
                    : "1px solid rgba(191,206,224,0.9)",
                  background: active
                    ? "rgba(26,138,255,0.14)"
                    : "rgba(255,255,255,0.92)",
                  color: active ? "#0f4ea8" : "#1f2937",
                  padding: "8px 12px",
                  fontSize: 12,
                  cursor: "pointer",
                  backdropFilter: "blur(6px)",
                  fontWeight: 700,
                  pointerEvents: "auto",
                }}
              >
                {mode === "boardroom"
                  ? "Boardroom"
                  : mode === "dashboard"
                    ? "Dashboard"
                    : mode === "marketing_stream"
                      ? "Marketing Stream"
                      : mode === "brand_foundation"
                        ? "Brand Foundation"
                        : mode === "live_agents"
                          ? "Live Agents"
                          : "Operations Flow"}
              </button>
            );
          })}
        </div>

        {viewMode === "boardroom" ? (
          <div
            style={{
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
              pointerEvents: "auto",
            }}
          >
            {chips.map((zone) => {
              const isActive = activeZone === zone;

              return (
                <button
                  key={zone}
                  type="button"
                  onClick={() => {
                    onInspectorTargetChange(null);
                    onActiveZoneChange(zone);
                    const seatId = zoneToSeatId(zone);
                    if (seatId) onSeatSelect(seatId, zone);
                    else onCanvasClear();
                  }}
                  style={{
                    borderRadius: 999,
                    border: isActive
                      ? "1px solid rgba(26,138,255,0.55)"
                      : "1px solid rgba(191,206,224,0.9)",
                    background: isActive
                      ? "rgba(26,138,255,0.14)"
                      : "rgba(255,255,255,0.92)",
                    color: isActive ? "#0f4ea8" : "#1f2937",
                    padding: "8px 12px",
                    fontSize: 12,
                    cursor: "pointer",
                    backdropFilter: "blur(6px)",
                    pointerEvents: "auto",
                  }}
                >
                  {ZONES[zone].label}
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}