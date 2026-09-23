import type { BoardroomInspectorTarget } from "./boardroom.domain";

export const RING_RADIUS = 12.5;
export const DEG = Math.PI / 180;

export function polar(radius: number, angleDeg: number): [number, number, number] {
  const a = angleDeg * DEG;
  return [Math.cos(a) * radius, 0, Math.sin(a) * radius];
}

export function zoneToSeatId(zone: string): string | null {
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

export function seatStateColor(state?: string) {
  if (state === "blocked") return "#ef4444";
  if (state === "warning") return "#f59e0b";
  if (state === "escalated") return "#f97316";
  return "#22c55e";
}

export function isFinanceStageTarget(
  target: BoardroomInspectorTarget | null,
  stageId: string,
) {
  return target?.kind === "finance_stage" && target.stageId === stageId;
}

export function isFinanceAgentTarget(
  target: BoardroomInspectorTarget | null,
  agentId: string,
) {
  return target?.kind === "finance_agent" && target.agentId === agentId;
}

export function isOperationsStageTarget(
  target: BoardroomInspectorTarget | null,
  stageId: string,
) {
  return target?.kind === "operations_stage" && target.stageId === stageId;
}

export function isOperationsAgentTarget(
  target: BoardroomInspectorTarget | null,
  agentId: string,
) {
  return target?.kind === "operations_agent" && target.agentId === agentId;
}

export function isSupportStageTarget(
  target: BoardroomInspectorTarget | null,
  stageId: string,
) {
  return target?.kind === "support_stage" && target.stageId === stageId;
}

export function isSupportAgentTarget(
  target: BoardroomInspectorTarget | null,
  agentId: string,
) {
  return target?.kind === "support_agent" && target.agentId === agentId;
}

export function isHrStageTarget(
  target: BoardroomInspectorTarget | null,
  stageId: string,
) {
  return target?.kind === "hr_stage" && target.stageId === stageId;
}

export function isHrAgentTarget(
  target: BoardroomInspectorTarget | null,
  agentId: string,
) {
  return target?.kind === "hr_agent" && target.agentId === agentId;
}

export function isMarketingStageTarget(
  target: BoardroomInspectorTarget | null,
  stageId: string,
) {
  return target?.kind === "marketing_stage" && target.stageId === stageId;
}

export function isMarketingAgentTarget(
  target: BoardroomInspectorTarget | null,
  agentId: string,
) {
  return target?.kind === "marketing_agent" && target.agentId === agentId;
}