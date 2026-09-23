import type { BoardroomRuntime } from "./boardroom.runtime";
import type {
  BoardroomCenterMetrics,
  BoardroomFrame,
  BoardroomInspectorTarget,
  BoardroomRuntimeRunSummary,
  BoardroomRuntimeSummary,
  BusinessPulse,
  BusinessWorkspace,
  Department,
  DepartmentFloors,
  DepartmentKey,
  Seat,
  SeatState,
  DepartmentFloorState,
  RuntimeRunStatus,
} from "./boardroom.domain";

function fmtMoney(v: number, currencySymbol = "£") {
  return `${currencySymbol}${v.toLocaleString("en-GB")}`;
}

function deriveSeatState(openTasks: number, blockedTasks: number): SeatState {
  if (blockedTasks >= 3) return "blocked";
  if (blockedTasks >= 1 || openTasks >= 8) return "warning";
  return "healthy";
}

function deriveCenterHealth(pulse: BusinessPulse): string {
  if (pulse.risk.cash === "high" || pulse.risk.operations === "high") {
    return "Critical";
  }
  if (
    pulse.risk.cash === "medium" ||
    pulse.risk.stock === "medium" ||
    pulse.risk.demand === "medium"
  ) {
    return "Watch";
  }
  return "Stable";
}

function normalizeRunStatus(status?: string | null): RuntimeRunStatus | string {
  if (!status) return "queued";
  return status;
}

function getRunOperatorId(run: BoardroomRuntimeRunSummary): string | undefined {
  return run.agent_id ?? run.agentId ?? run.operator_id ?? run.operatorId;
}

function getRunUpdatedAt(run: BoardroomRuntimeRunSummary): string {
  return (
    run.updated_at ??
    run.updatedAt ??
    run.completed_at ??
    run.completedAt ??
    run.started_at ??
    run.startedAt ??
    run.created_at ??
    run.createdAt ??
    ""
  );
}

function normalizeRuntime(
  runtime?: BoardroomRuntime | BoardroomRuntimeSummary,
): BoardroomRuntimeSummary | undefined {
  if (!runtime) return undefined;

  return {
    ...(runtime.node ? { node: runtime.node } : {}),
    ...(runtime.approvals ? { approvals: runtime.approvals } : {}),
    runs: Array.isArray(runtime.runs)
      ? runtime.runs.map((run) => ({
          ...run,
          status: normalizeRunStatus(run.status),
        }))
      : [],
  };
}

function buildDepartmentAgentRuntimeMap(
  runtime?: BoardroomRuntimeSummary,
): Map<
  string,
  {
    queuedCount: number;
    runningCount: number;
    waitingApprovalCount: number;
    failedCount: number;
    completedCount: number;
    latestStatus?: RuntimeRunStatus | string;
    latestUpdatedAt?: string;
  }
> {
  const map = new Map<
    string,
    {
      queuedCount: number;
      runningCount: number;
      waitingApprovalCount: number;
      failedCount: number;
      completedCount: number;
      latestStatus?: RuntimeRunStatus | string;
      latestUpdatedAt?: string;
    }
  >();

  const runs = runtime?.runs ?? [];

  for (const run of runs) {
    const operatorId = getRunOperatorId(run);
    if (!operatorId) continue;

    const entry = map.get(operatorId) ?? {
      queuedCount: 0,
      runningCount: 0,
      waitingApprovalCount: 0,
      failedCount: 0,
      completedCount: 0,
      latestStatus: undefined,
      latestUpdatedAt: undefined,
    };

    const status = normalizeRunStatus(run.status);

    if (status === "queued") entry.queuedCount += 1;
    else if (status === "running") entry.runningCount += 1;
    else if (status === "waiting_approval") entry.waitingApprovalCount += 1;
    else if (status === "failed") entry.failedCount += 1;
    else if (status === "completed") entry.completedCount += 1;

    const currentUpdatedAt = getRunUpdatedAt(run);
    const previousUpdatedAt = entry.latestUpdatedAt ?? "";

    if (!previousUpdatedAt || currentUpdatedAt > previousUpdatedAt) {
      entry.latestUpdatedAt = currentUpdatedAt;
      entry.latestStatus = status;
    }

    map.set(operatorId, entry);
  }

  return map;
}

function normalizeDepartmentFloor<K extends DepartmentKey>(
  floor: DepartmentFloorState<K> | undefined,
  runtime?: BoardroomRuntimeSummary,
): DepartmentFloorState<K> | undefined {
  if (!floor) return undefined;

  const agentRuntimeMap = buildDepartmentAgentRuntimeMap(runtime);

  return {
    ...floor,
    agents: floor.agents.map((agent) => {
      const runtimeState = agentRuntimeMap.get(agent.id);

      return {
        ...agent,
        displayTag: agent.displayTag ?? "AGENT",
        runtimeStatus: agent.runtimeStatus ?? runtimeState?.latestStatus,
        queuedCount: agent.queuedCount ?? runtimeState?.queuedCount ?? 0,
        runningCount: agent.runningCount ?? runtimeState?.runningCount ?? 0,
        waitingApprovalCount:
          agent.waitingApprovalCount ?? runtimeState?.waitingApprovalCount ?? 0,
        failedCount: agent.failedCount ?? runtimeState?.failedCount ?? 0,
        completedCount: agent.completedCount ?? runtimeState?.completedCount ?? 0,
      };
    }),
    stages: floor.stages.map((stage) => ({
      ...stage,
      state: stage.state ?? "healthy",
    })),
    flows: floor.flows.map((flow) => ({
      ...flow,
      state: flow.state ?? "healthy",
    })),
  };
}

function normalizeFloorStates(
  floors?: DepartmentFloors,
  runtime?: BoardroomRuntimeSummary,
): DepartmentFloors | undefined {
  if (!floors) return undefined;

  return {
    sales: normalizeDepartmentFloor(floors.sales, runtime),
    finance: normalizeDepartmentFloor(floors.finance, runtime),
    operations: normalizeDepartmentFloor(floors.operations, runtime),
    support: normalizeDepartmentFloor(floors.support, runtime),
    hr: normalizeDepartmentFloor(floors.hr, runtime),
    marketing: normalizeDepartmentFloor(floors.marketing, runtime),
  };
}

export function buildBoardroomCenterMetrics(
  pulse: BusinessPulse,
): BoardroomCenterMetrics {
  return {
    revenue: fmtMoney(pulse.sales.revenue),
    cash: fmtMoney(pulse.cash.onHand),
    pipeline: fmtMoney(pulse.cash.incoming30d),
    profit: `${pulse.finance.grossMarginPct}%`,
    health: deriveCenterHealth(pulse),
  };
}

export function buildBoardroomFrame(args: {
  workspace: BusinessWorkspace;
  departments: Department[];
  seats: Seat[];
  pulse: BusinessPulse;
  floors?: DepartmentFloors;
  runtime?: BoardroomRuntime;
  activeZone: DepartmentKey;
  selectedSeatId?: string;
  selectedInspectorTarget?: BoardroomInspectorTarget;
}): BoardroomFrame {
  const normalizedRuntime = normalizeRuntime(args.runtime);

  return {
    workspace: args.workspace,
    departments: args.departments,
    seats: args.seats.map((seat) => ({
      ...seat,
      state: deriveSeatState(seat.openTasks, seat.blockedTasks),
    })),
    pulse: args.pulse,
    center: buildBoardroomCenterMetrics(args.pulse),
    activeZone: args.activeZone,
    selectedSeatId: args.selectedSeatId,
    selectedInspectorTarget: args.selectedInspectorTarget,
    floors: normalizeFloorStates(args.floors, normalizedRuntime),
    runtime: args.runtime,
  };
}