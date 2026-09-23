import type { BoardroomRuntime } from "./boardroom.runtime";

export type SeatState = "healthy" | "warning" | "blocked" | "escalated";
export type RiskLevel = "low" | "medium" | "high";

export type BoardroomViewMode =
  | "boardroom"
  | "dashboard"
  | "operations_flow"
  | "marketing_stream"
  | "brand_foundation"
  | "live_agents";

export type DepartmentKey =
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

export type GoalStatus = "on_track" | "at_risk" | "off_track";
export type TaskState = "todo" | "in_progress" | "blocked" | "done";
export type TaskPriority = "low" | "medium" | "high";

export type RuntimeRunStatus =
  | "queued"
  | "running"
  | "waiting_approval"
  | "failed"
  | "completed"
  | "cancelled";

export type WorkflowExecutionMode =
  | "draft_then_approval"
  | "draft_only"
  | "manual_only";

export type RuntimeTriggerSource =
  | "manual"
  | "schedule"
  | "kpi"
  | "system";

export type BusinessWorkspace = {
  id: string;
  slug: string;
  name: string;
  currency: string;
  timezone?: string;
  industry?: string;
};

export type BusinessFunction = {
  id: string;
  departmentId: string;
  key: string;
  name: string;
  description?: string;
  isEnabled: boolean;
};

export type Department = {
  id: string;
  key: DepartmentKey;
  name: string;
  owner?: string;
  functions: BusinessFunction[];
};

export type Goal = {
  id: string;
  title: string;
  ownerSeatId: string;
  status: GoalStatus;
  dueAt?: string;
};

export type KPI = {
  id: string;
  seatId: string;
  label: string;
  value: number | string;
  unit?: string;
  target?: number | string;
  warningThreshold?: number;
  criticalThreshold?: number;
};

export type Task = {
  id: string;
  seatId: string;
  title: string;
  state: TaskState;
  priority: TaskPriority;
  dueAt?: string;
};

export type Seat = {
  id: string;
  departmentKey: DepartmentKey;
  label: string;
  shortLabel?: string;
  owner?: string;
  state: SeatState;
  openTasks: number;
  blockedTasks: number;
  dueToday: number;
  goals: Goal[];
  kpis: KPI[];
  tasks: Task[];
};

export type BusinessPulse = {
  cash: {
    onHand: number;
    incoming30d: number;
    outgoing30d: number;
    runwayDays: number;
  };
  sales: {
    revenue: number;
    orders: number;
    conversionRate: number;
    sellThroughRate: number;
  };
  stock: {
    units: number;
    value: number;
    daysCover: number;
    slowStockValue: number;
    inTransitValue: number;
  };
  ops: {
    backlog: number;
    fulfilmentRate: number;
    blockedJobs: number;
    avgTurnaroundDays: number;
  };
  finance: {
    creditorDays: number;
    debtorDays: number;
    grossMarginPct: number;
  };
  risk: {
    cash: RiskLevel;
    stock: RiskLevel;
    demand: RiskLevel;
    operations: RiskLevel;
  };
};

export type BoardroomCenterMetrics = {
  revenue: string;
  cash: string;
  pipeline: string;
  profit: string;
  health: string;
};

export type BoardroomRuntimeStepSummary = {
  id?: string;
  step_id?: string;
  stepId?: string;
  kind?: string;
  key?: string;
  label?: string;
  status?: string;
  output?: Record<string, unknown>;
  output_payload?: Record<string, unknown>;
  error?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  startedAt?: string | null;
  completed_at?: string | null;
  completedAt?: string | null;
};

export type BoardroomRuntimeApprovalSummary = {
  id: string;
  workflow_run_id?: string;
  workflowRunId?: string;
  operator_id?: string;
  agent_id?: string;
  department_key?: DepartmentKey;
  title: string;
  summary?: string;
  status: string;
  requested_at?: string;
  requestedAt?: string;
  resolved_at?: string | null;
  resolvedAt?: string | null;
  resolved_by?: string | null;
  resolvedBy?: string | null;
  resolution_note?: string | null;
  resolutionNote?: string | null;
};

export type BoardroomRuntimeRunSummary = {
  id: string;

  department_key: DepartmentKey;

  workflow_id?: string;
  workflowId?: string;
  workflow_key?: string;
  workflowKey?: string;

  workflow_name?: string;
  workflowName?: string;
  workflow_label?: string;
  workflowLabel?: string;

  operator_id?: string;
  operatorId?: string;
  agent_id?: string;
  agentId?: string;

  trigger_kind?: string;
  triggerKind?: string;
  trigger_source?: RuntimeTriggerSource | string;
  triggerSource?: RuntimeTriggerSource | string;

  execution_mode?: WorkflowExecutionMode | string;
  executionMode?: WorkflowExecutionMode | string;

  status: RuntimeRunStatus | string;

  current_step_index?: number;
  currentStepIndex?: number;
  current_step_id?: string | null;
  currentStepId?: string | null;
  current_step_key?: string | null;
  currentStepKey?: string | null;
  current_step_label?: string | null;
  currentStepLabel?: string | null;

  context?: Record<string, unknown>;
  input_payload?: Record<string, unknown>;
  inputPayload?: Record<string, unknown>;
  result_payload?: Record<string, unknown>;
  resultPayload?: Record<string, unknown>;

  approval_request_id?: string | null;
  approvalRequestId?: string | null;
  failure_reason?: string | null;
  failureReason?: string | null;
  error_message?: string | null;
  errorMessage?: string | null;

  headline?: string;
  summary?: string;
  connector_keys?: string[];
  connectorKeys?: string[];
  output_count?: number;
  outputCount?: number;

  created_at?: string;
  createdAt?: string;
  updated_at?: string;
  updatedAt?: string;
  started_at?: string | null;
  startedAt?: string | null;
  completed_at?: string | null;
  completedAt?: string | null;
  failed_at?: string | null;
  failedAt?: string | null;

  step_runs?: BoardroomRuntimeStepSummary[];
  steps?: BoardroomRuntimeStepSummary[];
};

export type BoardroomRuntimeSummary = {
  node?: {
    status?: "online" | "offline" | "paused" | string;
    mode?: "local_first" | "hybrid" | "cloud" | string;
    lastHeartbeatAt?: string;
    last_heartbeat_at?: string;
  };
  approvals?: BoardroomRuntimeApprovalSummary[];
  runs: BoardroomRuntimeRunSummary[];
};

export type DepartmentFloorAgent<K extends DepartmentKey = DepartmentKey> = {
  id: string;
  departmentKey: K;
  entityType: "agent";
  label: string;
  role: string;
  state: SeatState;
  workload: number;
  displayTag?: string;
  throughput?: number;
  conversionPct?: number;
  revenue?: number;
  assignedCount?: number;
  runtimeStatus?: RuntimeRunStatus | string;
  queuedCount?: number;
  runningCount?: number;
  waitingApprovalCount?: number;
  failedCount?: number;
  completedCount?: number;
};

export type DepartmentFloorStage<K extends DepartmentKey = DepartmentKey> = {
  id: string;
  departmentKey: K;
  entityType: "stage";
  label: string;
  count: number;
  value?: number;
  state?: SeatState;
};

export type DepartmentFloorFlow<K extends DepartmentKey = DepartmentKey> = {
  id: string;
  departmentKey: K;
  fromStageId: string;
  toStageId: string;
  count: number;
  value?: number;
  state?: SeatState;
  label?: string;
  bottleneck?: boolean;
  exception?: boolean;
  blockedCount?: number;
  cycleTimeDays?: number;
};

export type DepartmentFloorState<K extends DepartmentKey> = {
  departmentKey: K;
  agents: DepartmentFloorAgent<K>[];
  stages: DepartmentFloorStage<K>[];
  flows: DepartmentFloorFlow<K>[];
};

export type SalesFloorState = DepartmentFloorState<"sales">;
export type FinanceFloorState = DepartmentFloorState<"finance">;
export type OperationsFloorState = DepartmentFloorState<"operations">;
export type SupportFloorState = DepartmentFloorState<"support">;
export type HRFloorState = DepartmentFloorState<"hr">;
export type MarketingFloorState = DepartmentFloorState<"marketing">;

export type DepartmentFloors = {
  sales?: SalesFloorState;
  finance?: FinanceFloorState;
  operations?: OperationsFloorState;
  support?: SupportFloorState;
  hr?: HRFloorState;
  marketing?: MarketingFloorState;
};

export type BoardroomInspectorTarget =
  | {
      kind: "seat";
      seatId: string;
    }
  | {
      kind: "sales_stage";
      stageId: string;
    }
  | {
      kind: "sales_agent";
      agentId: string;
    }
  | {
      kind: "sales_flow";
      flowId: string;
    }
  | {
      kind: "finance_stage";
      stageId: string;
    }
  | {
      kind: "finance_agent";
      agentId: string;
    }
  | {
      kind: "finance_flow";
      flowId: string;
    }
  | {
      kind: "operations_stage";
      stageId: string;
    }
  | {
      kind: "operations_agent";
      agentId: string;
    }
  | {
      kind: "operations_flow";
      flowId: string;
    }
  | {
      kind: "support_stage";
      stageId: string;
    }
  | {
      kind: "support_agent";
      agentId: string;
    }
  | {
      kind: "support_flow";
      flowId: string;
    }
  | {
      kind: "hr_stage";
      stageId: string;
    }
  | {
      kind: "hr_agent";
      agentId: string;
    }
  | {
      kind: "hr_flow";
      flowId: string;
    }
  | {
      kind: "marketing_stage";
      stageId: string;
    }
  | {
      kind: "marketing_agent";
      agentId: string;
    }
  | {
      kind: "marketing_flow";
      flowId: string;
    };

export type BoardroomFrame = {
  workspace: BusinessWorkspace;
  departments: Department[];
  seats: Seat[];
  pulse: BusinessPulse;
  center: BoardroomCenterMetrics;
  activeZone: DepartmentKey;
  selectedSeatId?: string;
  selectedInspectorTarget?: BoardroomInspectorTarget | null;
  floors?: DepartmentFloors;
  runtime?: BoardroomRuntime;
};