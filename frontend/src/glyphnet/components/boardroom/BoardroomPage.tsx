"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import BoardroomInspector from "./BoardroomInspector";
import { BOARDROOM_DEMO_MODEL } from "./boardroom.mock";
import FounderReviewPanel from "./FounderReviewPanel";
import BusinessDashboard from "./BusinessDashboard";
import type { BoardroomRuntime } from "./boardroom.runtime";
import MarketingStreamPage from "./MarketingStreamPage";
import BrandFoundationPage from "./BrandFoundationPage";
import LiveAgentRunReplay from "./LiveAgentRunReplay";
import type {
  BoardroomFrame,
  BoardroomInspectorTarget,
  BoardroomViewMode,
  Department,
  DepartmentFloorAgent,
  DepartmentFloorFlow,
  DepartmentFloorStage,
  SalesFloorState,
  FinanceFloorState,
  OperationsFloorState,
  SupportFloorState,
  HRFloorState,
  MarketingFloorState,
  Seat,
  BusinessPulse,
  BoardroomCenterMetrics,
  BusinessWorkspace,
  DepartmentFloors,
  WorkflowExecutionMode,
} from "./boardroom.domain";
import QFCBoardroomWorld, {
  type BoardroomWorldZone,
} from "./QFCBoardroomWorld";
import { buildBoardroomFrame } from "./boardroom.frame";
import {
  DEMO_FLOORS,
  DEMO_PULSE,
  DEMO_SEATS,
  DEMO_WORKSPACE,
  DEMO_DEPARTMENTS,
  DEMO_RUNTIME,
} from "./boardroom.domain.mock";

import {
  WORKSPACE_ID,
  MARKETING_OPERATOR_ID,
  DASHBOARD_DEPARTMENT_CONFIG,
  DASHBOARD_DEPARTMENT_ZONES,
} from "./boardroom.page.constants";

import {
  readJson,
  zoneLabel,
  prettifyStatus,
  formatTime,
  getCurrentStepLabel,
  getMarketingStatusTone,
  departmentToAgentTarget,
  getRunSortTime,
  getStepLabelFromRun,
} from "./boardroom.page.utils";

import type {
  AgentRuntimeCard,
  ApiListResponse,
  ApprovalItem,
  BoardroomApiResponse,
  DashboardDepartmentKey,
  JsonRecord,
  StepRun,
  WorkflowRun,
} from "./boardroom.page.types";

import MarketingRuntimeCard from "./MarketingRuntimeCard";
import BoardroomLiveAgentsSurface from "./BoardroomLiveAgentsSurface";


function zoneToSeatId(zone: BoardroomWorldZone): string | null {
  switch (zone) {
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
    case "coo":
      return "seat_coo";
    case "ceo":
      return "seat_ceo";
    default:
      return null;
  }
}

function zoneToDepartmentKey(zone: BoardroomWorldZone): DashboardDepartmentKey | undefined {
  if (
    zone === "marketing" ||
    zone === "sales" ||
    zone === "finance" ||
    zone === "operations" ||
    zone === "support" ||
    zone === "hr"
  ) {
    return zone;
  }
  return undefined;
}

function isAgentTargetKind(kind?: BoardroomInspectorTarget["kind"]) {
  return (
    kind === "sales_agent" ||
    kind === "finance_agent" ||
    kind === "operations_agent" ||
    kind === "support_agent" ||
    kind === "hr_agent" ||
    kind === "marketing_agent"
  );
}

export default function BoardroomPage() {
  const model = BOARDROOM_DEMO_MODEL;

  const [viewMode, setViewMode] = useState<BoardroomViewMode>("boardroom");
  const [selectedSeatId, setSelectedSeatId] = useState<string | null>("seat_coo");
  const [activeZone, setActiveZone] = useState<BoardroomWorldZone>("coo");
  const [leftPanelMode, setLeftPanelMode] =
    useState<"inspector" | "founder_review">("inspector");
  const [selectedInspectorTarget, setSelectedInspectorTarget] =
    useState<BoardroomInspectorTarget | null>({
      kind: "seat",
      seatId: "seat_coo",
    });

  const [liveBoardroom, setLiveBoardroom] = useState<BoardroomApiResponse | null>(null);
  const [loadingBoardroom, setLoadingBoardroom] = useState(true);
  const [boardroomError, setBoardroomError] = useState<string | null>(null);

  const [marketingRuns, setMarketingRuns] = useState<WorkflowRun[]>([]);
  const [marketingApprovals, setMarketingApprovals] = useState<ApprovalItem[]>([]);

  const [departmentRuns, setDepartmentRuns] = useState<
    Partial<Record<DashboardDepartmentKey, WorkflowRun[]>>
  >({});

  const [departmentApprovals, setDepartmentApprovals] = useState<
    Partial<Record<DashboardDepartmentKey, ApprovalItem[]>>
  >({});

  const [loadingMarketingRuntime, setLoadingMarketingRuntime] = useState(true);
  const [marketingRuntimeError, setMarketingRuntimeError] = useState<string | null>(null);
  const [launchingMarketing, setLaunchingMarketing] = useState(false);
  const [launchMarketingError, setLaunchMarketingError] = useState<string | null>(null);
  const [selectedLiveAgent, setSelectedLiveAgent] = useState<AgentRuntimeCard | null>(null);

  function openMarketingContext() {
    setLeftPanelMode("inspector");
    setActiveZone("marketing");
    setSelectedSeatId("seat_marketing");
    setSelectedInspectorTarget({
      kind: "marketing_agent",
      agentId: "agent_marketing_operator_v1",
    });
  }

  function openLiveAgents() {
    setLeftPanelMode("inspector");
    setViewMode("live_agents");
  }

  function openAgentModal(agent: AgentRuntimeCard) {
    setSelectedLiveAgent(agent);
  }

  function closeAgentModal() {
    setSelectedLiveAgent(null);
  }

  function openAgentInInspector(agent: AgentRuntimeCard) {
    setLeftPanelMode("inspector");
    setActiveZone(agent.departmentKey);
    setViewMode("boardroom");

    const seatId = zoneToSeatId(agent.departmentKey);
    setSelectedSeatId(seatId);
    setSelectedInspectorTarget(
      departmentToAgentTarget(agent.departmentKey, agent.id),
    );
    setSelectedLiveAgent(null);
  }

  function openMarketingStream() {
    openMarketingContext();
    setViewMode("marketing_stream");
  }

  function openBrandFoundation() {
    openMarketingContext();
    setViewMode("brand_foundation");
  }

  function openDepartmentDashboard(zone: DashboardDepartmentKey) {
    setLeftPanelMode("inspector");
    setViewMode("dashboard");
    setActiveZone(zone);

    const seatId = zoneToSeatId(zone);
    setSelectedSeatId(seatId);

    if (seatId) {
      setSelectedInspectorTarget({
        kind: "seat",
        seatId,
      });
    } else {
      setSelectedInspectorTarget(null);
    }
  }

  async function loadDepartmentRuntime(departmentKey: DashboardDepartmentKey) {
    const [runsJson, approvalsJson] = await Promise.all([
      readJson<ApiListResponse<WorkflowRun>>(
        `/api/local-node/runs?department_key=${departmentKey}&limit=20`,
      ),
      readJson<ApiListResponse<ApprovalItem>>(
        `/api/local-node/approvals?department_key=${departmentKey}&limit=20`,
      ),
    ]);

    setDepartmentRuns((prev) => ({
      ...prev,
      [departmentKey]: runsJson.items ?? [],
    }));

    setDepartmentApprovals((prev) => ({
      ...prev,
      [departmentKey]: approvalsJson.items ?? [],
    }));
  }

  async function launchMarketingWorkflow() {
    try {
      setLaunchingMarketing(true);
      setLaunchMarketingError(null);

      await readJson(`/api/local-node/workflows/launch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow_definition_id: "workflow_marketing_content_draft_v1",
          agent_definition_id: "agent_marketing_operator_v1",
          context: {
            brief: "Draft a Costa Conexion marketing post",
            objective: "Generate local business enquiries",
            target_audience: "Local businesses in Almeria",
          },
        }),
      });

      const [runsJson, approvalsJson] = await Promise.all([
        readJson<ApiListResponse<WorkflowRun>>(
          `/api/local-node/runs?department_key=marketing&limit=20`,
        ),
        readJson<ApiListResponse<ApprovalItem>>(
          `/api/local-node/approvals?department_key=marketing&limit=20`,
        ),
      ]);

      setMarketingRuns(runsJson.items ?? []);
      setMarketingApprovals(approvalsJson.items ?? []);
      openMarketingContext();
    } catch (err) {
      setLaunchMarketingError(
        err instanceof Error ? err.message : "Failed to launch marketing workflow",
      );
    } finally {
      setLaunchingMarketing(false);
    }
  }

  const activeDashboardDepartment = useMemo<DashboardDepartmentKey>(() => {
    return zoneToDepartmentKey(activeZone) ?? "marketing";
  }, [activeZone]);

  const activeDashboardConfig = useMemo(() => {
    return DASHBOARD_DEPARTMENT_CONFIG[activeDashboardDepartment];
  }, [activeDashboardDepartment]);

  const renderDepartmentSwitch = () => (
    <div
      style={{
        display: "flex",
        gap: 8,
        flexWrap: "wrap",
        marginTop: 8,
      }}
    >
      {DASHBOARD_DEPARTMENT_ZONES.map((zone) => {
        const active = activeDashboardDepartment === zone;

        return (
          <button
            key={zone}
            type="button"
            onClick={() => openDepartmentDashboard(zone)}
            style={{
              borderRadius: 999,
              border: active
                ? "1px solid rgba(26,138,255,0.55)"
                : "1px solid rgba(191,206,224,0.9)",
              background: active
                ? "rgba(26,138,255,0.14)"
                : "rgba(255,255,255,0.78)",
              color: active ? "#0f4ea8" : "#1f2937",
              padding: "8px 12px",
              fontSize: 12,
              cursor: "pointer",
              backdropFilter: "blur(6px)",
              fontWeight: 700,
              textTransform: "capitalize",
            }}
          >
            {zone}
          </button>
        );
      })}
    </div>
  );

  const hydratedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function loadInitialBoardroom() {
      setLoadingBoardroom(true);
      setBoardroomError(null);

      try {
        const data = await readJson<BoardroomApiResponse>(
          `/api/aion/business/boardroom/${WORKSPACE_ID}`,
        );

        if (cancelled) return;

        setLiveBoardroom(data);

        if (!hydratedRef.current) {
          hydratedRef.current = true;
          setActiveZone((data.active_zone as BoardroomWorldZone) || "coo");
          setSelectedSeatId(data.selected_seat_id ?? "seat_coo");
          setSelectedInspectorTarget(
            data.selected_seat_id
              ? {
                  kind: "seat",
                  seatId: data.selected_seat_id,
                }
              : null,
          );
        }
      } catch (err) {
        if (cancelled) return;
        setBoardroomError(
          err instanceof Error ? err.message : "Failed to load live boardroom",
        );
      } finally {
        if (!cancelled) {
          setLoadingBoardroom(false);
        }
      }
    }

    void loadInitialBoardroom();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!hydratedRef.current) return;

    let cancelled = false;

    async function loadFrame() {
      try {
        setBoardroomError(null);

        const data = await readJson<BoardroomApiResponse>(
          `/api/aion/business/boardroom/frame`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              workspace_id: WORKSPACE_ID,
              active_zone: activeZone,
              selected_seat_id: selectedSeatId ?? undefined,
            }),
          },
        );

        if (cancelled) return;
        setLiveBoardroom(data);
      } catch (err) {
        if (cancelled) return;
        setBoardroomError(
          err instanceof Error ? err.message : "Failed to refresh boardroom frame",
        );
      }
    }

    void loadFrame();

    return () => {
      cancelled = true;
    };
  }, [activeZone, selectedSeatId]);

  useEffect(() => {
    let cancelled = false;

    async function loadMarketingRuntime() {
      const firstLoad = marketingRuns.length === 0 && marketingApprovals.length === 0;
      if (firstLoad) setLoadingMarketingRuntime(true);
      setMarketingRuntimeError(null);

      try {
        const [runsJson, approvalsJson] = await Promise.all([
          readJson<ApiListResponse<WorkflowRun>>(
            `/api/local-node/runs?department_key=marketing&limit=20`,
          ),
          readJson<ApiListResponse<ApprovalItem>>(
            `/api/local-node/approvals?department_key=marketing&limit=20`,
          ),
        ]);

        if (cancelled) return;

        setMarketingRuns(runsJson.items ?? []);
        setMarketingApprovals(approvalsJson.items ?? []);
      } catch (err) {
        if (cancelled) return;
        setMarketingRuntimeError(
          err instanceof Error ? err.message : "Failed to load marketing runtime",
        );
      } finally {
        if (!cancelled) {
          setLoadingMarketingRuntime(false);
        }
      }
    }

    void loadMarketingRuntime();
    const timer = window.setInterval(() => {
      void loadMarketingRuntime();
    }, 10000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [marketingRuns.length, marketingApprovals.length]);

  const liveWorkspace: BusinessWorkspace = liveBoardroom?.workspace ?? DEMO_WORKSPACE;
  const liveDepartments: Department[] = liveBoardroom?.departments ?? DEMO_DEPARTMENTS;
  const liveSeats: Seat[] = liveBoardroom?.seats ?? DEMO_SEATS;
  const livePulse: BusinessPulse = liveBoardroom?.pulse ?? DEMO_PULSE;
  const liveFloors: DepartmentFloors = liveBoardroom?.floors ?? DEMO_FLOORS;
  const liveRuntime: BoardroomRuntime = useMemo(() => {
    const fallback = liveBoardroom?.runtime ?? DEMO_RUNTIME;
    const fallbackRuns = Array.isArray(fallback?.runs) ? fallback.runs : [];
    const fallbackApprovals = Array.isArray(fallback?.approvals) ? fallback.approvals : [];

    const toWorkflowExecutionMode = (value?: string): WorkflowExecutionMode => {
      if (value === "draft_with_approval") return "draft_then_approval";
      if (value === "draft_only") return "draft_only";
      return "manual_only";
    };

    const toRuntimeTriggerSource = (
      value?: string,
    ): "manual" | "schedule" | "kpi" | "system" => {
      if (value === "manual") return "manual";
      if (value === "schedule") return "schedule";
      if (value === "kpi") return "kpi";
      return "system";
    };

    const mappedRuns = marketingRuns.map((run) => ({
      id: run.id,
      department_key: run.department_key as any,
      agent_id: run.operator_id,
      workflow_key: run.workflow_id,
      workflow_label: run.workflow_name,
      execution_mode: toWorkflowExecutionMode(run.execution_mode),
      status: run.status as any,
      trigger_source: toRuntimeTriggerSource(run.trigger_kind),
      createdAt: run.created_at,
      startedAt: run.step_runs?.find((s) => s.started_at)?.started_at ?? undefined,
      completedAt: run.completed_at ?? undefined,
      failedAt: run.status === "failed" ? run.updated_at : undefined,
      headline: run.workflow_name,
      summary: run.failure_reason ?? undefined,
      currentStepKey:
        run.step_runs && run.step_runs.length > 0
          ? run.step_runs[Math.min(run.current_step_index, run.step_runs.length - 1)]?.kind
          : undefined,
      approvalRequestId: run.approval_request_id ?? undefined,
      connectorKeys: [],
      outputCount: run.step_runs?.filter((s) => s.status === "completed").length ?? 0,
      steps: (run.step_runs ?? []).map((step) => ({
        id: step.id,
        runId: run.id,
        key: step.step_id,
        label: step.kind,
        status: step.status as any,
        startedAt: step.started_at ?? undefined,
        completedAt: step.completed_at ?? undefined,
        errorMessage: step.error ?? undefined,
      })),
    }));

    const mappedApprovals = marketingApprovals.map((approval) => ({
      id: approval.id,
      runId: approval.workflow_run_id,
      title: approval.title,
      status: approval.status as any,
      requestedAt: approval.requested_at,
      decidedAt: approval.resolved_at ?? undefined,
      decidedBy: approval.resolved_by ?? undefined,
    }));

    return {
      node: fallback?.node ?? {
        status: "offline",
        mode: "local_first",
        lastHeartbeatAt: undefined,
      },
      approvals: [...fallbackApprovals, ...mappedApprovals],
      runs: [
        ...fallbackRuns.filter((run) => run.department_key !== "marketing"),
        ...mappedRuns,
      ],
    };
  }, [liveBoardroom?.runtime, marketingRuns, marketingApprovals]);
  const liveCenter: BoardroomCenterMetrics = liveBoardroom?.center ?? {
    revenue: "—",
    cash: "—",
    pipeline: "—",
    profit: "—",
    health: "—",
  };

  const frame = useMemo(() => {
    const boardroomFrame = buildBoardroomFrame({
      workspace: liveWorkspace,
      departments: liveDepartments,
      seats: liveSeats,
      pulse: livePulse,
      floors: liveFloors,
      runtime: liveRuntime,
      activeZone,
      selectedSeatId: selectedSeatId ?? undefined,
      selectedInspectorTarget: selectedInspectorTarget ?? undefined,
    });

    return {
      t: Date.now(),
      mode: viewMode,
      workspaceId: boardroomFrame.workspace.slug,
      boardroom: {
        ...model,
        selectedSeatId: selectedSeatId ?? undefined,
        activeZone,
        viewMode,
        workspace: boardroomFrame.workspace,
        departments: boardroomFrame.departments,
        seats: boardroomFrame.seats,
        center: liveCenter,
        floors: boardroomFrame.floors,
        runtime: boardroomFrame.runtime,
        selectedInspectorTarget: boardroomFrame.selectedInspectorTarget,
      },
      pulse: boardroomFrame.pulse,
      boardroomFrame: {
        ...boardroomFrame,
        center: liveCenter,
      },
      alpha: 0.82,
      sigma: 0.74,
      kappa: 0.63,
      chi: 0.58,
      topo_gate01: 1,
    };
  }, [
    model,
    viewMode,
    selectedSeatId,
    activeZone,
    selectedInspectorTarget,
    liveWorkspace,
    liveDepartments,
    liveSeats,
    livePulse,
    liveFloors,
    liveRuntime,
    liveCenter,
  ]);

  const seats: Seat[] = frame.boardroomFrame?.seats ?? DEMO_SEATS;

  const selectedInspectorSeat: Seat | null = useMemo(() => {
    if (!selectedSeatId) return null;
    return seats.find((s) => s.id === selectedSeatId) ?? null;
  }, [seats, selectedSeatId]);

  const salesFloor: SalesFloorState | undefined = useMemo(() => {
    return frame.boardroomFrame?.floors?.sales;
  }, [frame]);

  const financeFloor: FinanceFloorState | undefined = useMemo(() => {
    return frame.boardroomFrame?.floors?.finance;
  }, [frame]);

  const operationsFloor: OperationsFloorState | undefined = useMemo(() => {
    return frame.boardroomFrame?.floors?.operations;
  }, [frame]);

  const supportFloor: SupportFloorState | undefined = useMemo(() => {
    return frame.boardroomFrame?.floors?.support;
  }, [frame]);

  const hrFloor: HRFloorState | undefined = useMemo(() => {
    return frame.boardroomFrame?.floors?.hr;
  }, [frame]);

  const marketingFloor: MarketingFloorState | undefined = useMemo(() => {
    return frame.boardroomFrame?.floors?.marketing;
  }, [frame]);

  const allFloorAgents = useMemo(() => {
    const out: AgentRuntimeCard[] = [];

    const pushAgents = (
      departmentKey: DashboardDepartmentKey,
      agents?: DepartmentFloorAgent[],
    ) => {
      for (const agent of agents ?? []) {
        const runsForDepartment = departmentRuns[departmentKey] ?? [];

        const agentRuns = runsForDepartment
          .filter((run) => run.operator_id === agent.id || (run as any).agent_id === agent.id)
          .sort((a, b) => getRunSortTime(b) - getRunSortTime(a));

        const queuedCount =
          agent.queuedCount ?? agentRuns.filter((run) => run.status === "queued").length;
        const runningCount =
          agent.runningCount ?? agentRuns.filter((run) => run.status === "running").length;
        const waitingApprovalCount =
          agent.waitingApprovalCount ??
          agentRuns.filter((run) => run.status === "waiting_approval").length;
        const failedCount =
          agent.failedCount ?? agentRuns.filter((run) => run.status === "failed").length;
        const completedCount =
          agent.completedCount ?? agentRuns.filter((run) => run.status === "completed").length;

        const runtimeStatus =
          agent.runtimeStatus ??
          (runningCount > 0
            ? "running"
            : waitingApprovalCount > 0
              ? "waiting_approval"
              : failedCount > 0
                ? "failed"
                : queuedCount > 0
                  ? "queued"
                  : completedCount > 0
                    ? "completed"
                    : "idle");

        out.push({
          id: agent.id,
          label: agent.label,
          role: agent.role,
          departmentKey,
          displayTag: agent.displayTag,
          state: agent.state,
          workload: agent.workload,
          assignedCount: agent.assignedCount,
          throughput: agent.throughput,
          conversionPct: agent.conversionPct,
          revenue: agent.revenue,
          runtimeStatus,
          queuedCount,
          runningCount,
          waitingApprovalCount,
          failedCount,
          completedCount,
          totalRuns: agentRuns.length,
          latestRun: agentRuns[0] ?? null,
          runs: agentRuns,
        });
      }
    };

    pushAgents("marketing", marketingFloor?.agents);
    pushAgents("sales", salesFloor?.agents);
    pushAgents("finance", financeFloor?.agents);
    pushAgents("operations", operationsFloor?.agents);
    pushAgents("support", supportFloor?.agents);
    pushAgents("hr", hrFloor?.agents);

    return out.sort((a, b) => {
      const aActive = a.runningCount + a.waitingApprovalCount + a.queuedCount;
      const bActive = b.runningCount + b.waitingApprovalCount + b.queuedCount;

      if (bActive !== aActive) return bActive - aActive;
      return a.label.localeCompare(b.label);
    });
  }, [
    marketingFloor,
    salesFloor,
    financeFloor,
    operationsFloor,
    supportFloor,
    hrFloor,
    marketingRuns,
  ]);

  const liveActiveAgents = useMemo(() => {
    return allFloorAgents.filter(
      (agent) =>
        agent.runningCount > 0 ||
        agent.waitingApprovalCount > 0 ||
        agent.queuedCount > 0 ||
        agent.failedCount > 0,
    );
  }, [allFloorAgents]);

  const selectedSalesStage: DepartmentFloorStage | null = useMemo(() => {
    if (
      !salesFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "sales_stage"
    ) {
      return null;
    }

    return (
      salesFloor.stages.find((stage) => stage.id === selectedInspectorTarget.stageId) ??
      null
    );
  }, [salesFloor, selectedInspectorTarget]);

  const selectedSalesAgent: DepartmentFloorAgent | null = useMemo(() => {
    if (
      !salesFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "sales_agent"
    ) {
      return null;
    }

    return (
      salesFloor.agents.find((agent) => agent.id === selectedInspectorTarget.agentId) ??
      null
    );
  }, [salesFloor, selectedInspectorTarget]);

  const selectedFinanceStage: DepartmentFloorStage | null = useMemo(() => {
    if (
      !financeFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "finance_stage"
    ) {
      return null;
    }

    return (
      financeFloor.stages.find((stage) => stage.id === selectedInspectorTarget.stageId) ??
      null
    );
  }, [financeFloor, selectedInspectorTarget]);

  const selectedFinanceAgent: DepartmentFloorAgent | null = useMemo(() => {
    if (
      !financeFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "finance_agent"
    ) {
      return null;
    }

    return (
      financeFloor.agents.find((agent) => agent.id === selectedInspectorTarget.agentId) ??
      null
    );
  }, [financeFloor, selectedInspectorTarget]);

  const selectedOperationsStage: DepartmentFloorStage | null = useMemo(() => {
    if (
      !operationsFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "operations_stage"
    ) {
      return null;
    }

    return (
      operationsFloor.stages.find(
        (stage) => stage.id === selectedInspectorTarget.stageId,
      ) ?? null
    );
  }, [operationsFloor, selectedInspectorTarget]);

  const selectedOperationsAgent: DepartmentFloorAgent | null = useMemo(() => {
    if (
      !operationsFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "operations_agent"
    ) {
      return null;
    }

    return (
      operationsFloor.agents.find(
        (agent) => agent.id === selectedInspectorTarget.agentId,
      ) ?? null
    );
  }, [operationsFloor, selectedInspectorTarget]);

  const selectedSupportStage: DepartmentFloorStage | null = useMemo(() => {
    if (
      !supportFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "support_stage"
    ) {
      return null;
    }

    return (
      supportFloor.stages.find(
        (stage) => stage.id === selectedInspectorTarget.stageId,
      ) ?? null
    );
  }, [supportFloor, selectedInspectorTarget]);

  const selectedSupportAgent: DepartmentFloorAgent | null = useMemo(() => {
    if (
      !supportFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "support_agent"
    ) {
      return null;
    }

    return (
      supportFloor.agents.find(
        (agent) => agent.id === selectedInspectorTarget.agentId,
      ) ?? null
    );
  }, [supportFloor, selectedInspectorTarget]);

  const selectedHrStage: DepartmentFloorStage | null = useMemo(() => {
    if (
      !hrFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "hr_stage"
    ) {
      return null;
    }

    return (
      hrFloor.stages.find(
        (stage) => stage.id === selectedInspectorTarget.stageId,
      ) ?? null
    );
  }, [hrFloor, selectedInspectorTarget]);

  const selectedHrAgent: DepartmentFloorAgent | null = useMemo(() => {
    if (
      !hrFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "hr_agent"
    ) {
      return null;
    }

    return (
      hrFloor.agents.find(
        (agent) => agent.id === selectedInspectorTarget.agentId,
      ) ?? null
    );
  }, [hrFloor, selectedInspectorTarget]);

  const selectedMarketingStage: DepartmentFloorStage | null = useMemo(() => {
    if (
      !marketingFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "marketing_stage"
    ) {
      return null;
    }

    return (
      marketingFloor.stages.find(
        (stage) => stage.id === selectedInspectorTarget.stageId,
      ) ?? null
    );
  }, [marketingFloor, selectedInspectorTarget]);

  const selectedMarketingAgent: DepartmentFloorAgent | null = useMemo(() => {
    if (
      !marketingFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "marketing_agent"
    ) {
      return null;
    }

    return (
      marketingFloor.agents.find(
        (agent) => agent.id === selectedInspectorTarget.agentId,
      ) ?? null
    );
  }, [marketingFloor, selectedInspectorTarget]);

  const selectedSalesFlow: DepartmentFloorFlow | null = useMemo(() => {
    if (
      !salesFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "sales_flow"
    ) {
      return null;
    }

    return (
      salesFloor.flows.find((flow) => flow.id === selectedInspectorTarget.flowId) ??
      null
    );
  }, [salesFloor, selectedInspectorTarget]);

  const selectedFinanceFlow: DepartmentFloorFlow | null = useMemo(() => {
    if (
      !financeFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "finance_flow"
    ) {
      return null;
    }

    return (
      financeFloor.flows.find((flow) => flow.id === selectedInspectorTarget.flowId) ??
      null
    );
  }, [financeFloor, selectedInspectorTarget]);

  const selectedOperationsFlow: DepartmentFloorFlow | null = useMemo(() => {
    if (
      !operationsFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "operations_flow"
    ) {
      return null;
    }

    return (
      operationsFloor.flows.find((flow) => flow.id === selectedInspectorTarget.flowId) ??
      null
    );
  }, [operationsFloor, selectedInspectorTarget]);

  const selectedSupportFlow: DepartmentFloorFlow | null = useMemo(() => {
    if (
      !supportFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "support_flow"
    ) {
      return null;
    }

    return (
      supportFloor.flows.find((flow) => flow.id === selectedInspectorTarget.flowId) ??
      null
    );
  }, [supportFloor, selectedInspectorTarget]);

  const selectedHrFlow: DepartmentFloorFlow | null = useMemo(() => {
    if (
      !hrFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "hr_flow"
    ) {
      return null;
    }

    return (
      hrFloor.flows.find((flow) => flow.id === selectedInspectorTarget.flowId) ??
      null
    );
  }, [hrFloor, selectedInspectorTarget]);

  const selectedMarketingFlow: DepartmentFloorFlow | null = useMemo(() => {
    if (
      !marketingFloor ||
      !selectedInspectorTarget ||
      selectedInspectorTarget.kind !== "marketing_flow"
    ) {
      return null;
    }

    return (
      marketingFloor.flows.find((flow) => flow.id === selectedInspectorTarget.flowId) ??
      null
    );
  }, [marketingFloor, selectedInspectorTarget]);

  const latestMarketingRun = useMemo(() => {
    if (marketingRuns.length === 0) return null;

    return [...marketingRuns].sort((a, b) => {
      return (
        new Date(b.updated_at || b.created_at).getTime() -
        new Date(a.updated_at || a.created_at).getTime()
      );
    })[0] ?? null;
  }, [marketingRuns]);

  const activeMarketingRun = useMemo(() => {
    const active = marketingRuns.find(
      (run) => run.status === "running" || run.status === "waiting_approval",
    );
    return active ?? latestMarketingRun;
  }, [latestMarketingRun, marketingRuns]);

  const queueCount = useMemo(
    () => marketingRuns.filter((run) => run.status === "queued").length,
    [marketingRuns],
  );

  const runningCount = useMemo(
    () => marketingRuns.filter((run) => run.status === "running").length,
    [marketingRuns],
  );

  const waitingApprovalCount = useMemo(
    () => marketingRuns.filter((run) => run.status === "waiting_approval").length,
    [marketingRuns],
  );

  const failedCount = useMemo(
    () => marketingRuns.filter((run) => run.status === "failed").length,
    [marketingRuns],
  );

  const completedCount = useMemo(
    () => marketingRuns.filter((run) => run.status === "completed").length,
    [marketingRuns],
  );

  const pendingMarketingApprovals = useMemo(
    () => marketingApprovals.filter((approval) => approval.status === "pending"),
    [marketingApprovals],
  );

  const selectedMarketingApproval = useMemo(() => {
    if (!activeMarketingRun) return null;
    return (
      pendingMarketingApprovals.find(
        (approval) => approval.workflow_run_id === activeMarketingRun.id,
      ) ?? null
    );
  }, [activeMarketingRun, pendingMarketingApprovals]);

  const marketingOperatorStatus = useMemo(() => {
    if (runningCount > 0) return "running";
    if (waitingApprovalCount > 0) return "waiting_approval";
    if (failedCount > 0) return "failed";
    if (completedCount > 0) return "completed";
    if (queueCount > 0) return "queued";
    return "idle";
  }, [completedCount, failedCount, queueCount, runningCount, waitingApprovalCount]);

  const marketingStatusTone = useMemo(
    () => getMarketingStatusTone(marketingOperatorStatus),
    [marketingOperatorStatus],
  );

  const showMarketingRuntimeCard =
    activeZone === "marketing" ||
    selectedInspectorTarget?.kind === "marketing_agent" ||
    selectedInspectorTarget?.kind === "marketing_stage" ||
    selectedInspectorTarget?.kind === "marketing_flow" ||
    selectedSeatId === "seat_marketing";

  const inspectorTitle = useMemo(() => {
    if (!selectedInspectorTarget) return "No selection";

    if (selectedInspectorTarget.kind === "seat") {
      return selectedInspectorSeat?.label ?? "Seat";
    }

    if (selectedInspectorTarget.kind === "sales_stage") {
      return selectedSalesStage?.label ?? "Sales Stage";
    }

    if (selectedInspectorTarget.kind === "sales_agent") {
      return selectedSalesAgent?.label ?? "Sales Agent";
    }

    if (selectedInspectorTarget.kind === "finance_stage") {
      return selectedFinanceStage?.label ?? "Finance Stage";
    }

    if (selectedInspectorTarget.kind === "finance_agent") {
      return selectedFinanceAgent?.label ?? "Finance Agent";
    }

    if (selectedInspectorTarget.kind === "operations_stage") {
      return selectedOperationsStage?.label ?? "Operations Stage";
    }

    if (selectedInspectorTarget.kind === "operations_agent") {
      return selectedOperationsAgent?.label ?? "Operations Agent";
    }

    if (selectedInspectorTarget.kind === "support_stage") {
      return selectedSupportStage?.label ?? "Support Stage";
    }

    if (selectedInspectorTarget.kind === "support_agent") {
      return selectedSupportAgent?.label ?? "Support Agent";
    }

    if (selectedInspectorTarget.kind === "hr_stage") {
      return selectedHrStage?.label ?? "HR Stage";
    }

    if (selectedInspectorTarget.kind === "hr_agent") {
      return selectedHrAgent?.label ?? "HR Agent";
    }

    if (selectedInspectorTarget.kind === "marketing_stage") {
      return selectedMarketingStage?.label ?? "Marketing Stage";
    }

    if (selectedInspectorTarget.kind === "marketing_agent") {
      return selectedMarketingAgent?.label ?? "Marketing Agent";
    }

    if (selectedInspectorTarget.kind === "sales_flow") {
      return selectedSalesFlow?.label ?? "Sales Flow";
    }

    if (selectedInspectorTarget.kind === "finance_flow") {
      return selectedFinanceFlow?.label ?? "Finance Flow";
    }

    if (selectedInspectorTarget.kind === "operations_flow") {
      return selectedOperationsFlow?.label ?? "Operations Flow";
    }

    if (selectedInspectorTarget.kind === "support_flow") {
      return selectedSupportFlow?.label ?? "Support Flow";
    }

    if (selectedInspectorTarget.kind === "hr_flow") {
      return selectedHrFlow?.label ?? "HR Flow";
    }

    if (selectedInspectorTarget.kind === "marketing_flow") {
      return selectedMarketingFlow?.label ?? "Marketing Flow";
    }

    return "No selection";
  }, [
    selectedInspectorTarget,
    selectedInspectorSeat,
    selectedSalesStage,
    selectedSalesAgent,
    selectedFinanceStage,
    selectedFinanceAgent,
    selectedOperationsStage,
    selectedOperationsAgent,
    selectedSupportStage,
    selectedSupportAgent,
    selectedHrStage,
    selectedHrAgent,
    selectedMarketingStage,
    selectedMarketingAgent,
    selectedSalesFlow,
    selectedFinanceFlow,
    selectedOperationsFlow,
    selectedSupportFlow,
    selectedHrFlow,
    selectedMarketingFlow,
  ]);

  const center = frame.boardroomFrame?.center;

const renderModeSwitch = () => (
  <div
    style={{
      display: "flex",
      gap: 8,
      flexWrap: "wrap",
    }}
  >
    {(
      [
        "boardroom",
        "dashboard",
        "marketing_stream",
        "live_agents",
        "brand_foundation",
        "operations_flow",
      ] as const
    ).map((mode) => {
      const active = viewMode === mode;

      return (
        <button
          key={mode}
          type="button"
          onClick={() => setViewMode(mode)}
          style={{
            borderRadius: 999,
            border: active
              ? "1px solid rgba(26,138,255,0.55)"
              : "1px solid rgba(191,206,224,0.9)",
            background: active
              ? "rgba(26,138,255,0.14)"
              : "rgba(255,255,255,0.78)",
            color: active ? "#0f4ea8" : "#1f2937",
            padding: "8px 12px",
            fontSize: 12,
            cursor: "pointer",
            backdropFilter: "blur(6px)",
            fontWeight: 700,
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
);

const renderMarketingRuntimeCard = () => (
  <div
    style={{
      borderRadius: 16,
      border: "1px solid rgba(26,138,255,0.16)",
      background:
        "linear-gradient(180deg, rgba(255,255,255,0.95), rgba(248,250,252,0.95))",
      padding: 12,
      display: "grid",
      gap: 10,
    }}
  >
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 10,
      }}
    >
      <div>
        <div style={{ fontSize: 11, color: "#6b7280" }}>Live Marketing Operator</div>
        <div style={{ fontSize: 16, fontWeight: 800, color: "#111827", marginTop: 2 }}>
          {selectedMarketingAgent?.label ?? "Campaigns"}
        </div>
        <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
          {MARKETING_OPERATOR_ID}
        </div>
      </div>

      <div
        style={{
          borderRadius: 999,
          padding: "6px 10px",
          fontSize: 11,
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: 0.3,
          ...marketingStatusTone,
        }}
      >
        {prettifyStatus(marketingOperatorStatus)}
      </div>
    </div>

    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(2, minmax(0,1fr))",
        gap: 8,
      }}
    >
      {[
        ["Running", String(runningCount)],
        ["Awaiting approval", String(waitingApprovalCount)],
        ["Failed", String(failedCount)],
        ["Completed", String(completedCount)],
      ].map(([label, value]) => (
        <div
          key={label}
          style={{
            borderRadius: 12,
            border: "1px solid rgba(226,232,240,1)",
            background: "#ffffff",
            padding: "8px 10px",
          }}
        >
          <div style={{ fontSize: 10, color: "#6b7280", lineHeight: 1.1 }}>{label}</div>
          <div
            style={{
              fontSize: 15,
              fontWeight: 800,
              color: "#0f172a",
              marginTop: 4,
              lineHeight: 1.1,
            }}
          >
            {value}
          </div>
        </div>
      ))}
    </div>

    <div
      style={{
        borderRadius: 12,
        border: "1px solid rgba(226,232,240,1)",
        background: "#ffffff",
        padding: "10px 12px",
        display: "grid",
        gap: 6,
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 700, color: "#334155" }}>Selected run</div>
      <div style={{ fontSize: 13, fontWeight: 700, color: "#111827" }}>
        {activeMarketingRun?.workflow_name ?? "No active marketing run"}
      </div>
      <div style={{ fontSize: 12, color: "#64748b" }}>
        Step: {getCurrentStepLabel(activeMarketingRun)}
      </div>
      <div style={{ fontSize: 12, color: "#64748b" }}>
        Last update:{" "}
        {formatTime(activeMarketingRun?.updated_at ?? activeMarketingRun?.created_at)}
      </div>
      {selectedMarketingApproval ? (
        <div
          style={{
            marginTop: 2,
            fontSize: 12,
            color: "#b45309",
            fontWeight: 700,
          }}
        >
          Approval pending: {selectedMarketingApproval.title}
        </div>
      ) : null}
      {marketingRuntimeError ? (
        <div
          style={{
            marginTop: 2,
            fontSize: 12,
            color: "#b91c1c",
          }}
        >
          {marketingRuntimeError}
        </div>
      ) : null}
    </div>

    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <button
        type="button"
        onClick={launchMarketingWorkflow}
        disabled={launchingMarketing}
        style={{
          borderRadius: 12,
          border: "1px solid rgba(16,185,129,0.35)",
          background: launchingMarketing
            ? "rgba(226,232,240,0.9)"
            : "linear-gradient(180deg, #22c55e, #16a34a)",
          color: launchingMarketing ? "#475569" : "#ffffff",
          padding: "10px 12px",
          fontSize: 12,
          fontWeight: 800,
          cursor: launchingMarketing ? "not-allowed" : "pointer",
          boxShadow: launchingMarketing
            ? "none"
            : "0 8px 18px rgba(34,197,94,0.18)",
        }}
      >
        {launchingMarketing ? "Launching..." : "Launch workflow"}
      </button>

      <button
        type="button"
        onClick={openMarketingStream}
        style={{
          borderRadius: 12,
          border: "1px solid rgba(26,138,255,0.4)",
          background: "linear-gradient(180deg, #3394ff, #1a8aff)",
          color: "#ffffff",
          padding: "10px 12px",
          fontSize: 12,
          fontWeight: 800,
          cursor: "pointer",
          boxShadow: "0 8px 18px rgba(26,138,255,0.18)",
        }}
      >
        Open marketing stream
      </button>

      <button
        type="button"
        onClick={openBrandFoundation}
        style={{
          borderRadius: 12,
          border: "1px solid rgba(191,206,224,0.9)",
          background: "rgba(255,255,255,0.9)",
          color: "#1f2937",
          padding: "10px 12px",
          fontSize: 12,
          fontWeight: 700,
          cursor: "pointer",
        }}
      >
        Open brand foundation
      </button>
    </div>

    {launchMarketingError ? (
      <div
        style={{
          fontSize: 12,
          color: "#b91c1c",
        }}
      >
        {launchMarketingError}
      </div>
    ) : null}

    <div style={{ fontSize: 11, color: "#64748b" }}>
      {loadingMarketingRuntime
        ? "Loading execution-backed marketing runtime..."
        : "Marketing operator state is now tied to live workflow runtime."}
    </div>
  </div>
);

const renderInspectorPanel = () => (
  <div
    style={{
      borderRight: "1px solid rgba(148,163,184,0.18)",
      background:
        "linear-gradient(180deg, rgba(255,255,255,0.78), rgba(248,250,252,0.92))",
      backdropFilter: "blur(8px)",
      padding: 14,
      display: "flex",
      flexDirection: "column",
      gap: 12,
      minWidth: 0,
      minHeight: 0,
      overflow: "hidden",
    }}
  >
    <div>
      <div style={{ fontSize: 11, color: "#6b7280" }}>Boardroom</div>
      <div
        style={{
          fontSize: 18,
          fontWeight: 800,
          color: "#111827",
          marginTop: 2,
          lineHeight: 1.1,
        }}
      >
        {liveWorkspace.name}
      </div>
      <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
        {loadingBoardroom ? "Loading live boardroom..." : zoneLabel(activeZone, viewMode)}
      </div>
    </div>

    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(2, minmax(0,1fr))",
        gap: 8,
      }}
    >
      {[
        ["Revenue", center?.revenue ?? "—"],
        ["Cash", center?.cash ?? "—"],
        ["Pipeline", center?.pipeline ?? "—"],
        ["Profit", center?.profit ?? "—"],
      ].map(([label, value]) => (
        <div
          key={label}
          style={{
            borderRadius: 12,
            border: "1px solid rgba(226,232,240,1)",
            background: "rgba(255,255,255,0.9)",
            padding: "8px 10px",
          }}
        >
          <div style={{ fontSize: 11, color: "#6b7280", lineHeight: 1.1 }}>{label}</div>
          <div
            style={{
              fontSize: 13,
              fontWeight: 800,
              color: "#111827",
              marginTop: 3,
              lineHeight: 1.15,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {value}
          </div>
        </div>
      ))}
    </div>

    {showMarketingRuntimeCard ? renderMarketingRuntimeCard() : null}

    <div
      style={{
        borderRadius: 16,
        border: "1px solid rgba(148,163,184,0.18)",
        background: "rgba(255,255,255,0.86)",
        overflow: "hidden",
        minHeight: 0,
        flex: "1 1 auto",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          padding: "10px 12px",
          borderBottom: "1px solid rgba(226,232,240,0.9)",
          display: "flex",
          flexDirection: "column",
          gap: 10,
          flex: "0 0 auto",
        }}
      >
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={() => setLeftPanelMode("inspector")}
            style={{
              borderRadius: 999,
              border:
                leftPanelMode === "inspector"
                  ? "1px solid rgba(26,138,255,0.55)"
                  : "1px solid rgba(191,206,224,0.9)",
              background:
                leftPanelMode === "inspector"
                  ? "rgba(26,138,255,0.14)"
                  : "rgba(255,255,255,0.85)",
              color: leftPanelMode === "inspector" ? "#0f4ea8" : "#1f2937",
              padding: "7px 10px",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Inspector
          </button>

          <button
            type="button"
            onClick={() => setLeftPanelMode("founder_review")}
            style={{
              borderRadius: 999,
              border:
                leftPanelMode === "founder_review"
                  ? "1px solid rgba(26,138,255,0.55)"
                  : "1px solid rgba(191,206,224,0.9)",
              background:
                leftPanelMode === "founder_review"
                  ? "rgba(26,138,255,0.14)"
                  : "rgba(255,255,255,0.85)",
              color: leftPanelMode === "founder_review" ? "#0f4ea8" : "#1f2937",
              padding: "7px 10px",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Founder Review
          </button>
        </div>

        {leftPanelMode === "inspector" ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 8,
            }}
          >
            <div>
              <div style={{ fontSize: 12, color: "#6b7280" }}>Live Inspector</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: "#111827" }}>
                {inspectorTitle}
              </div>
            </div>

            {selectedInspectorTarget ? (
              <button
                type="button"
                onClick={() => {
                  setSelectedInspectorTarget(null);
                  setSelectedSeatId(null);
                }}
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 999,
                  border: "1px solid rgba(148,163,184,0.28)",
                  background: "#ffffff",
                  color: "#334155",
                  cursor: "pointer",
                  fontSize: 16,
                  lineHeight: "30px",
                  textAlign: "center",
                  flex: "0 0 auto",
                }}
                aria-label="Close inspector"
                title="Close"
              >
                ×
              </button>
            ) : null}
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 12, color: "#6b7280" }}>Founder Review</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#111827" }}>
              Queue + weekly review surface
            </div>
          </div>
        )}
      </div>

      <div
        style={{
          minHeight: 0,
          flex: "1 1 auto",
          overflowY: "auto",
          overflowX: "hidden",
          padding: 12,
        }}
      >
        {leftPanelMode === "inspector" ? (
          <BoardroomInspector
            seat={selectedInspectorTarget?.kind === "seat" ? selectedInspectorSeat : null}
            salesFloor={salesFloor}
            financeFloor={financeFloor}
            operationsFloor={operationsFloor}
            supportFloor={supportFloor}
            hrFloor={hrFloor}
            marketingFloor={marketingFloor}
            salesStage={selectedSalesStage}
            salesAgent={selectedSalesAgent}
            financeStage={selectedFinanceStage}
            financeAgent={selectedFinanceAgent}
            operationsStage={selectedOperationsStage}
            operationsAgent={selectedOperationsAgent}
            supportStage={selectedSupportStage}
            supportAgent={selectedSupportAgent}
            hrStage={selectedHrStage}
            hrAgent={selectedHrAgent}
            marketingStage={selectedMarketingStage}
            marketingAgent={selectedMarketingAgent}
            salesFlow={selectedSalesFlow}
            financeFlow={selectedFinanceFlow}
            operationsFlow={selectedOperationsFlow}
            supportFlow={selectedSupportFlow}
            hrFlow={selectedHrFlow}
            marketingFlow={selectedMarketingFlow}
          />
        ) : (
          <FounderReviewPanel
            workspaceId={WORKSPACE_ID}
            roleId="ceo-core"
            businessType="service_business"
          />
        )}
      </div>
    </div>
  </div>
);

  const renderWorldSurface = () => (
    <div
      style={{
        position: "relative",
        minWidth: 0,
        minHeight: 0,
        overflow: "hidden",
        background:
          "radial-gradient(1200px 600px at 20% 10%, rgba(26,138,255,0.04), transparent 55%)," +
          "linear-gradient(180deg, rgba(255,255,255,0.4), rgba(255,255,255,0.15))",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 16,
          left: 16,
          right: 16,
          zIndex: 5,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 12,
          pointerEvents: "none",
          color: "#1f2937",
        }}
      >
        <div>
          <div style={{ fontSize: 12, fontWeight: 700 }}>
            {viewMode === "operations_flow"
              ? "Operations Flow"
              : activeZone === "coo"
                ? "COO Core"
                : `${activeZone.toUpperCase()} Floor`}
          </div>
          <div style={{ fontSize: 10, opacity: 0.75 }}>
            {viewMode === "operations_flow"
              ? "Linear business operating chain"
              : activeZone === "coo"
                ? "Central operating core"
                : "Departmental floor zone"}
          </div>
        </div>

        <div
          style={{
            padding: "6px 12px",
            borderRadius: 999,
            border: "1px solid rgba(26,138,255,0.35)",
            background: "rgba(255,255,255,0.78)",
            fontSize: 10,
            whiteSpace: "nowrap",
            color: "#0f4ea8",
            backdropFilter: "blur(6px)",
          }}
        >
          {viewMode === "operations_flow"
            ? "BUSINESS · OPERATIONS FLOW"
            : `BUSINESS · ${activeZone.toUpperCase()}`}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          top: 56,
          right: 16,
          zIndex: 6,
        }}
      >
        {renderModeSwitch()}
      </div>

      <QFCBoardroomWorld
        frame={frame}
        viewMode={viewMode}
        activeZone={activeZone}
        selectedSeatId={selectedSeatId}
        selectedInspectorTarget={selectedInspectorTarget}
        onViewModeChange={setViewMode}
        onActiveZoneChange={setActiveZone}
        onSeatSelect={(seatId, zone) => {
          setLeftPanelMode("inspector");

          if (zone === "marketing") {
            openMarketingContext();
            return;
          }

          setActiveZone(zone);
          setSelectedSeatId(seatId);
          setSelectedInspectorTarget({
            kind: "seat",
            seatId,
          });
        }}
        onInspectorTargetChange={(target) => {
          setLeftPanelMode("inspector");
          setSelectedInspectorTarget(target);

          if (!target) {
            setSelectedSeatId(null);
            return;
          }

          if (target.kind === "seat") {
            setSelectedSeatId(target.seatId);
            return;
          }

          if (
            target.kind === "sales_stage" ||
            target.kind === "sales_agent" ||
            target.kind === "sales_flow"
          ) {
            setSelectedSeatId("seat_sales");
            setActiveZone("sales");
            return;
          }

          if (
            target.kind === "finance_stage" ||
            target.kind === "finance_agent" ||
            target.kind === "finance_flow"
          ) {
            setSelectedSeatId("seat_finance");
            setActiveZone("finance");
            return;
          }

          if (
            target.kind === "operations_stage" ||
            target.kind === "operations_agent" ||
            target.kind === "operations_flow"
          ) {
            setSelectedSeatId("seat_ops");
            setActiveZone("operations");
            return;
          }

          if (
            target.kind === "support_stage" ||
            target.kind === "support_agent" ||
            target.kind === "support_flow"
          ) {
            setSelectedSeatId("seat_support");
            setActiveZone("support");
            return;
          }

          if (
            target.kind === "hr_stage" ||
            target.kind === "hr_agent" ||
            target.kind === "hr_flow"
          ) {
            setSelectedSeatId("seat_hr");
            setActiveZone("hr");
            return;
          }

          if (
            target.kind === "marketing_stage" ||
            target.kind === "marketing_agent" ||
            target.kind === "marketing_flow"
          ) {
            openMarketingContext();
            return;
          }

          setSelectedSeatId(null);
        }}
        onCanvasClear={() => {
          setSelectedSeatId(null);
          setSelectedInspectorTarget(null);
        }}
      />

      <div
        style={{
          position: "absolute",
          left: 18,
          bottom: 18,
          zIndex: 6,
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            padding: "8px 12px",
            borderRadius: 12,
            background: "rgba(255,255,255,0.78)",
            border: "1px solid rgba(148,163,184,0.18)",
            color: "#475569",
            fontSize: 12,
            backdropFilter: "blur(6px)",
          }}
        >
          {viewMode === "operations_flow"
            ? "Operations Flow scaffold is live. Next step is the real linear chain layout."
            : activeZone === "marketing" && !loadingMarketingRuntime
              ? `Marketing operator ${prettifyStatus(marketingOperatorStatus)} · ${runningCount} running · ${waitingApprovalCount} awaiting approval · ${failedCount} failed`
              : loadingBoardroom
                ? "Loading live Costa Conexion boardroom..."
                : "Live Costa Conexion boardroom is active. Click a floor, stage, or agent to inspect it."}
        </div>
      </div>
    </div>
  );

  const renderDashboardSurface = () => (
    <div
      style={{
        width: "100%",
        borderRadius: 22,
        overflow: "hidden",
        minHeight: 760,
        background:
          "radial-gradient(1200px 600px at 20% 10%, rgba(26,138,255,0.08), transparent 55%)," +
          "radial-gradient(1000px 500px at 80% 20%, rgba(244,26,255,0.04), transparent 55%)," +
          "linear-gradient(180deg, #f7f9fc, #edf2f8)",
        border: "1px solid rgba(148,163,184,0.22)",
        boxShadow: "0 18px 50px rgba(15,23,42,0.06)",
        display: "flex",
        flexDirection: "column",
        minWidth: 0,
      }}
    >
      <div
        style={{
          padding: "18px 20px 12px",
          borderBottom: "1px solid rgba(148,163,184,0.16)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div style={{ fontSize: 11, color: "#6b7280" }}>Boardroom</div>
          <div
            style={{
              fontSize: 22,
              fontWeight: 800,
              color: "#111827",
              marginTop: 2,
              lineHeight: 1.1,
            }}
          >
            {liveWorkspace.name}
          </div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
            {loadingBoardroom ? "Loading dashboard..." : "Dashboard Mode"}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 10,
            alignItems: "flex-end",
          }}
        >
          <div
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid rgba(26,138,255,0.35)",
              background: "rgba(255,255,255,0.78)",
              fontSize: 10,
              whiteSpace: "nowrap",
              color: "#0f4ea8",
              backdropFilter: "blur(6px)",
            }}
          >
            BUSINESS · DASHBOARD
          </div>
          {renderModeSwitch()}
          {renderDepartmentSwitch()}
        </div>
      </div>

      <div
        style={{
          padding: 20,
          overflowY: "auto",
          minHeight: 0,
          flex: "1 1 auto",
        }}
      >
        <BusinessDashboard
          key={`dashboard-${activeDashboardDepartment}`}
          workspaceId={WORKSPACE_ID}
          departmentKey={activeDashboardDepartment}
          operatorId={activeDashboardConfig.operatorId}
          workflowId={activeDashboardConfig.workflowId}
          activeZone={activeZone}
          onLaunchWorkflow={
            activeDashboardDepartment === "marketing" ? openMarketingStream : undefined
          }
          onSelectMarketing={
            activeDashboardDepartment === "marketing"
              ? () => {
                  openMarketingContext();
                  setViewMode("marketing_stream");
                }
              : undefined
          }
        />
      </div>
    </div>
  );

  const renderMarketingStreamSurface = () => (
    <div
      style={{
        width: "100%",
        borderRadius: 22,
        overflow: "hidden",
        minHeight: 760,
        background:
          "radial-gradient(1200px 600px at 20% 10%, rgba(26,138,255,0.08), transparent 55%)," +
          "radial-gradient(1000px 500px at 80% 20%, rgba(244,26,255,0.04), transparent 55%)," +
          "linear-gradient(180deg, #f7f9fc, #edf2f8)",
        border: "1px solid rgba(148,163,184,0.22)",
        boxShadow: "0 18px 50px rgba(15,23,42,0.06)",
        display: "flex",
        flexDirection: "column",
        minWidth: 0,
      }}
    >
      <div
        style={{
          padding: "18px 20px 12px",
          borderBottom: "1px solid rgba(148,163,184,0.16)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div style={{ fontSize: 11, color: "#6b7280" }}>Boardroom</div>
          <div
            style={{
              fontSize: 22,
              fontWeight: 800,
              color: "#111827",
              marginTop: 2,
              lineHeight: 1.1,
            }}
          >
            {liveWorkspace.name}
          </div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
            {loadingBoardroom ? "Loading marketing stream..." : "Marketing Stream"}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 10,
            alignItems: "flex-end",
          }}
        >
          <div
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid rgba(26,138,255,0.35)",
              background: "rgba(255,255,255,0.78)",
              fontSize: 10,
              whiteSpace: "nowrap",
              color: "#0f4ea8",
              backdropFilter: "blur(6px)",
            }}
          >
            BUSINESS · MARKETING STREAM
          </div>
          {renderModeSwitch()}
        </div>
      </div>

      <div
        style={{
          overflowY: "auto",
          minHeight: 0,
          flex: "1 1 auto",
        }}
      >
        <MarketingStreamPage
          workspaceId={WORKSPACE_ID}
          onBackToBoardroom={() => setViewMode("boardroom")}
          onBackToDashboard={() => setViewMode("dashboard")}
          onOpenBrandFoundation={openBrandFoundation}
        />
      </div>
    </div>
  );

const renderLiveAgentsSurface = () => (
  <div
    style={{
      width: "100%",
      borderRadius: 22,
      overflow: "hidden",
      minHeight: 760,
      background:
        "radial-gradient(1200px 600px at 20% 10%, rgba(26,138,255,0.08), transparent 55%)," +
        "radial-gradient(1000px 500px at 80% 20%, rgba(244,26,255,0.04), transparent 55%)," +
        "linear-gradient(180deg, #f7f9fc, #edf2f8)",
      border: "1px solid rgba(148,163,184,0.22)",
      boxShadow: "0 18px 50px rgba(15,23,42,0.06)",
      display: "flex",
      flexDirection: "column",
      minWidth: 0,
      position: "relative",
    }}
  >
    <div
      style={{
        padding: "18px 20px 12px",
        borderBottom: "1px solid rgba(148,163,184,0.16)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: 16,
        flexWrap: "wrap",
      }}
    >
      <div>
        <div style={{ fontSize: 11, color: "#6b7280" }}>Boardroom</div>
        <div
          style={{
            fontSize: 22,
            fontWeight: 800,
            color: "#111827",
            marginTop: 2,
            lineHeight: 1.1,
          }}
        >
          {liveWorkspace.name}
        </div>
        <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
          Live Active Agents
        </div>
        <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 6 }}>
          {loadingMarketingRuntime
            ? "Loading live runtime across departments..."
            : "Showing agents with queued, running, waiting approval, or failed runtime activity."}
        </div>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 10,
          alignItems: "flex-end",
        }}
      >
        <div
          style={{
            padding: "6px 12px",
            borderRadius: 999,
            border: "1px solid rgba(26,138,255,0.35)",
            background: "rgba(255,255,255,0.78)",
            fontSize: 10,
            whiteSpace: "nowrap",
            color: "#0f4ea8",
            backdropFilter: "blur(6px)",
          }}
        >
          BUSINESS · LIVE AGENTS
        </div>
        {renderModeSwitch()}
      </div>
    </div>

    <div
      style={{
        padding: 20,
        overflowY: "auto",
        minHeight: 0,
        flex: "1 1 auto",
        display: "grid",
        gap: 14,
      }}
    >
      {marketingRuntimeError ? (
        <div
          style={{
            borderRadius: 16,
            border: "1px solid rgba(254,202,202,1)",
            background: "rgba(254,242,242,1)",
            padding: 14,
            color: "#991b1b",
            fontSize: 13,
            display: "grid",
            gap: 4,
          }}
        >
          <div style={{ fontWeight: 800 }}>Live runtime unavailable</div>
          <div>{marketingRuntimeError}</div>
        </div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 10,
        }}
      >
        {[
          ["Active agents", String(liveActiveAgents.length)],
          [
            "Running runs",
            String(allFloorAgents.reduce((sum, agent) => sum + agent.runningCount, 0)),
          ],
          [
            "Waiting approvals",
            String(
              allFloorAgents.reduce(
                (sum, agent) => sum + agent.waitingApprovalCount,
                0,
              ),
            ),
          ],
          [
            "Queued runs",
            String(allFloorAgents.reduce((sum, agent) => sum + agent.queuedCount, 0)),
          ],
          [
            "Failed runs",
            String(allFloorAgents.reduce((sum, agent) => sum + agent.failedCount, 0)),
          ],
        ].map(([label, value]) => (
          <div
            key={label}
            style={{
              borderRadius: 14,
              border: "1px solid rgba(226,232,240,1)",
              background: "#ffffff",
              padding: "12px 14px",
            }}
          >
            <div style={{ fontSize: 11, color: "#6b7280" }}>{label}</div>
            <div
              style={{
                fontSize: 20,
                fontWeight: 800,
                color: "#111827",
                marginTop: 4,
              }}
            >
              {value}
            </div>
          </div>
        ))}
      </div>

      {liveActiveAgents.length === 0 ? (
        <div
          style={{
            borderRadius: 16,
            border: "1px solid rgba(226,232,240,1)",
            background: "#ffffff",
            padding: 16,
            color: "#64748b",
            fontSize: 13,
          }}
        >
          No active agents right now.
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 14,
          }}
        >
          {liveActiveAgents.map((agent) => {
            const tone = getMarketingStatusTone(agent.runtimeStatus);

            return (
              <button
                key={agent.id}
                type="button"
                onClick={() => openAgentModal(agent)}
                style={{
                  textAlign: "left",
                  borderRadius: 18,
                  border: "1px solid rgba(148,163,184,0.18)",
                  background: "rgba(255,255,255,0.94)",
                  padding: 14,
                  display: "grid",
                  gap: 10,
                  cursor: "pointer",
                  boxShadow: "0 10px 24px rgba(15,23,42,0.05)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    justifyContent: "space-between",
                    gap: 10,
                  }}
                >
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 800, color: "#111827" }}>
                      {agent.label}
                    </div>
                    <div style={{ fontSize: 12, color: "#64748b", marginTop: 3 }}>
                      {agent.role}
                    </div>
                    <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 3 }}>
                      {agent.departmentKey.toUpperCase()} · {agent.id}
                    </div>
                  </div>

                  <div
                    style={{
                      borderRadius: 999,
                      padding: "6px 10px",
                      fontSize: 11,
                      fontWeight: 800,
                      textTransform: "uppercase",
                      letterSpacing: 0.3,
                      ...tone,
                    }}
                  >
                    {prettifyStatus(agent.runtimeStatus)}
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0,1fr))",
                    gap: 8,
                  }}
                >
                  {[
                    ["Running", String(agent.runningCount)],
                    ["Waiting", String(agent.waitingApprovalCount)],
                    ["Queued", String(agent.queuedCount)],
                    ["Failed", String(agent.failedCount)],
                  ].map(([label, value]) => (
                    <div
                      key={label}
                      style={{
                        borderRadius: 12,
                        border: "1px solid rgba(226,232,240,1)",
                        background: "#f8fafc",
                        padding: "8px 10px",
                      }}
                    >
                      <div style={{ fontSize: 10, color: "#6b7280" }}>{label}</div>
                      <div
                        style={{
                          fontSize: 14,
                          fontWeight: 800,
                          color: "#111827",
                          marginTop: 4,
                        }}
                      >
                        {value}
                      </div>
                    </div>
                  ))}
                </div>

                <div
                  style={{
                    borderRadius: 12,
                    border: "1px solid rgba(226,232,240,1)",
                    background: "#ffffff",
                    padding: "10px 12px",
                    display: "grid",
                    gap: 4,
                  }}
                >
                  <div style={{ fontSize: 11, color: "#6b7280" }}>Current activity</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#111827" }}>
                    {agent.latestRun?.workflow_name ?? "No recent workflow"}
                  </div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>
                    Step: {getStepLabelFromRun(agent.latestRun)}
                  </div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>
                    Updated:{" "}
                    {formatTime(agent.latestRun?.updated_at ?? agent.latestRun?.created_at)}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>

    {selectedLiveAgent ? (
      <div
        onClick={closeAgentModal}
        style={{
          position: "absolute",
          inset: 0,
          background: "rgba(15,23,42,0.42)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
          zIndex: 20,
        }}
      >
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            width: "min(960px, 100%)",
            maxHeight: "85vh",
            overflowY: "auto",
            borderRadius: 22,
            background: "#ffffff",
            border: "1px solid rgba(226,232,240,1)",
            boxShadow: "0 24px 70px rgba(15,23,42,0.24)",
            padding: 20,
            display: "grid",
            gap: 16,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 12,
            }}
          >
            <div>
              <div style={{ fontSize: 12, color: "#6b7280" }}>Live Agent</div>
              <div style={{ fontSize: 24, fontWeight: 800, color: "#111827" }}>
                {selectedLiveAgent.label}
              </div>
              <div style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>
                {selectedLiveAgent.role} · {selectedLiveAgent.departmentKey.toUpperCase()} ·{" "}
                {selectedLiveAgent.id}
              </div>
            </div>

            <button
              type="button"
              onClick={closeAgentModal}
              style={{
                width: 36,
                height: 36,
                borderRadius: 999,
                border: "1px solid rgba(148,163,184,0.28)",
                background: "#ffffff",
                color: "#334155",
                cursor: "pointer",
                fontSize: 18,
                fontWeight: 700,
              }}
            >
              ×
            </button>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, minmax(0,1fr))",
              gap: 10,
            }}
          >
            {[
              ["Queued", String(selectedLiveAgent.queuedCount)],
              ["Running", String(selectedLiveAgent.runningCount)],
              ["Waiting", String(selectedLiveAgent.waitingApprovalCount)],
              ["Failed", String(selectedLiveAgent.failedCount)],
              ["Completed", String(selectedLiveAgent.completedCount)],
            ].map(([label, value]) => (
              <div
                key={label}
                style={{
                  borderRadius: 12,
                  border: "1px solid rgba(226,232,240,1)",
                  background: "#f8fafc",
                  padding: "10px 12px",
                }}
              >
                <div style={{ fontSize: 11, color: "#6b7280" }}>{label}</div>
                <div
                  style={{
                    fontSize: 16,
                    fontWeight: 800,
                    color: "#111827",
                    marginTop: 4,
                  }}
                >
                  {value}
                </div>
              </div>
            ))}
          </div>

          <div
            style={{
              borderRadius: 16,
              border: "1px solid rgba(226,232,240,1)",
              background: "#ffffff",
              padding: 14,
              display: "grid",
              gap: 10,
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 800, color: "#111827" }}>
              Current work
            </div>

            {selectedLiveAgent.latestRun ? (
              <>
                <div style={{ fontSize: 13, color: "#111827", fontWeight: 700 }}>
                  {selectedLiveAgent.latestRun.workflow_name}
                </div>
                <div style={{ fontSize: 12, color: "#64748b" }}>
                  Status: {prettifyStatus(selectedLiveAgent.latestRun.status)}
                </div>
                <div style={{ fontSize: 12, color: "#64748b" }}>
                  Step: {getStepLabelFromRun(selectedLiveAgent.latestRun)}
                </div>
                <div style={{ fontSize: 12, color: "#64748b" }}>
                  Last update:{" "}
                  {formatTime(
                    selectedLiveAgent.latestRun.updated_at ??
                      selectedLiveAgent.latestRun.created_at,
                  )}
                </div>
                {selectedLiveAgent.latestRun.failure_reason ? (
                  <div style={{ fontSize: 12, color: "#b91c1c", fontWeight: 700 }}>
                    Failure: {selectedLiveAgent.latestRun.failure_reason}
                  </div>
                ) : null}

                <LiveAgentRunReplay run={selectedLiveAgent.latestRun} />
              </>
            ) : (
              <div style={{ fontSize: 12, color: "#64748b" }}>No current run.</div>
            )}
          </div>

          <div
            style={{
              borderRadius: 16,
              border: "1px solid rgba(226,232,240,1)",
              background: "#ffffff",
              padding: 14,
              display: "grid",
              gap: 10,
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 800, color: "#111827" }}>
              Run history
            </div>

            {selectedLiveAgent.runs.length === 0 ? (
              <div style={{ fontSize: 12, color: "#64748b" }}>No run history yet.</div>
            ) : (
              <div style={{ display: "grid", gap: 8 }}>
                {selectedLiveAgent.runs.slice(0, 12).map((run) => (
                  <div
                    key={run.id}
                    style={{
                      borderRadius: 12,
                      border: "1px solid rgba(226,232,240,1)",
                      background: "#f8fafc",
                      padding: "10px 12px",
                      display: "grid",
                      gap: 6,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 8,
                        alignItems: "center",
                      }}
                    >
                      <div style={{ fontSize: 13, fontWeight: 700, color: "#111827" }}>
                        {run.workflow_name}
                      </div>
                      <div
                        style={{
                          fontSize: 11,
                          fontWeight: 800,
                          textTransform: "uppercase",
                          ...getMarketingStatusTone(run.status),
                          borderRadius: 999,
                          padding: "4px 8px",
                        }}
                      >
                        {prettifyStatus(run.status)}
                      </div>
                    </div>

                    <div style={{ fontSize: 12, color: "#64748b" }}>
                      Step: {getStepLabelFromRun(run)}
                    </div>
                    <div style={{ fontSize: 12, color: "#64748b" }}>
                      Created: {formatTime(run.created_at)} · Updated: {formatTime(run.updated_at)}
                    </div>

                    <LiveAgentRunReplay run={run} compact />
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={() => openAgentInInspector(selectedLiveAgent)}
              style={{
                borderRadius: 12,
                border: "1px solid rgba(26,138,255,0.4)",
                background: "linear-gradient(180deg, #3394ff, #1a8aff)",
                color: "#ffffff",
                padding: "10px 14px",
                fontSize: 12,
                fontWeight: 800,
                cursor: "pointer",
              }}
            >
              Open in boardroom inspector
            </button>

            <button
              type="button"
              onClick={closeAgentModal}
              style={{
                borderRadius: 12,
                border: "1px solid rgba(191,206,224,0.9)",
                background: "#ffffff",
                color: "#1f2937",
                padding: "10px 14px",
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    ) : null}
  </div>
);

  const renderBrandFoundationSurface = () => (
    <div
      style={{
        width: "100%",
        borderRadius: 22,
        overflow: "hidden",
        minHeight: 760,
        background:
          "radial-gradient(1200px 600px at 20% 10%, rgba(26,138,255,0.08), transparent 55%)," +
          "radial-gradient(1000px 500px at 80% 20%, rgba(244,26,255,0.04), transparent 55%)," +
          "linear-gradient(180deg, #f7f9fc, #edf2f8)",
        border: "1px solid rgba(148,163,184,0.22)",
        boxShadow: "0 18px 50px rgba(15,23,42,0.06)",
        display: "flex",
        flexDirection: "column",
        minWidth: 0,
      }}
    >
      <div
        style={{
          padding: "18px 20px 12px",
          borderBottom: "1px solid rgba(148,163,184,0.16)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div style={{ fontSize: 11, color: "#6b7280" }}>Boardroom</div>
          <div
            style={{
              fontSize: 22,
              fontWeight: 800,
              color: "#111827",
              marginTop: 2,
              lineHeight: 1.1,
            }}
          >
            {liveWorkspace.name}
          </div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
            {loadingBoardroom ? "Loading brand foundation..." : "Brand Foundation"}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 10,
            alignItems: "flex-end",
          }}
        >
          <div
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid rgba(26,138,255,0.35)",
              background: "rgba(255,255,255,0.78)",
              fontSize: 10,
              whiteSpace: "nowrap",
              color: "#0f4ea8",
              backdropFilter: "blur(6px)",
            }}
          >
            BUSINESS · BRAND FOUNDATION
          </div>
          {renderModeSwitch()}
        </div>
      </div>

      <div
        style={{
          overflowY: "auto",
          minHeight: 0,
          flex: "1 1 auto",
        }}
      >
        <BrandFoundationPage
          workspaceId={WORKSPACE_ID}
          onBackToMarketingStream={() => setViewMode("marketing_stream")}
          onBackToBoardroom={() => setViewMode("boardroom")}
          onBackToDashboard={() => setViewMode("dashboard")}
        />
      </div>
    </div>
  );

  return (
    <div
      style={{
        width: "100%",
        maxWidth: "1680px",
        margin: "0 auto",
        minHeight: "100%",
        display: "flex",
        flexDirection: "column",
        gap: 16,
        padding: "16px 20px 24px",
        background: "#f3f4f6",
        boxSizing: "border-box",
      }}
    >
      <div>
        <div style={{ fontSize: 12, color: "#6b7280" }}>Aion Business</div>
        <div style={{ fontSize: 32, fontWeight: 800, color: "#111827" }}>
          Boardroom World
        </div>
      </div>

      {boardroomError ? (
        <div
          style={{
            borderRadius: 14,
            border: "1px solid rgba(254,202,202,1)",
            background: "rgba(254,242,242,1)",
            color: "#991b1b",
            padding: "12px 14px",
            fontSize: 13,
          }}
        >
          {boardroomError}
        </div>
      ) : null}

      {viewMode === "dashboard" ? (
        renderDashboardSurface()
      ) : viewMode === "marketing_stream" ? (
        renderMarketingStreamSurface()
      ) : viewMode === "brand_foundation" ? (
        renderBrandFoundationSurface()
      ) : viewMode === "live_agents" ? (
        renderLiveAgentsSurface()
      ) : (
        <div
          style={{
            width: "100%",
            borderRadius: 22,
            overflow: "hidden",
            minHeight: 760,
            height: "calc(100vh - 140px)",
            background:
              "radial-gradient(1200px 600px at 20% 10%, rgba(26,138,255,0.08), transparent 55%)," +
              "radial-gradient(1000px 500px at 80% 20%, rgba(244,26,255,0.04), transparent 55%)," +
              "linear-gradient(180deg, #f7f9fc, #edf2f8)",
            border: "1px solid rgba(148,163,184,0.22)",
            boxShadow: "0 18px 50px rgba(15,23,42,0.06)",
            display: "grid",
            gridTemplateColumns: "420px minmax(0, 1fr)",
          }}
        >
          {renderInspectorPanel()}
          {renderWorldSurface()}
        </div>
      )}
    </div>
  );
}