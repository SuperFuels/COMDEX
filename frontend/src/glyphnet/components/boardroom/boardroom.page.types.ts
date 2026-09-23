import type { BoardroomFrame } from "./boardroom.domain";

export type BoardroomApiResponse = Omit<
  BoardroomFrame,
  "activeZone" | "selectedSeatId"
> & {
  active_zone?: string;
  selected_seat_id?: string | null;
  metadata?: Record<string, unknown>;
};

export type JsonRecord = Record<string, unknown>;

export type ApprovalItem = {
  id: string;
  workflow_run_id: string;
  operator_id: string;
  department_key: string;
  title: string;
  summary: string;
  payload: JsonRecord;
  status: string;
  requested_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_note: string | null;
};

export type StepRun = {
  id: string;
  step_id: string;
  kind: string;
  status: string;
  output: JsonRecord;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
};

export type WorkflowRun = {
  id: string;
  workflow_id: string;
  workflow_name: string;
  operator_id: string;
  department_key: string;
  trigger_kind: string;
  execution_mode: string;
  status: string;
  current_step_index: number;
  context: JsonRecord;
  step_runs: StepRun[];
  approval_request_id: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

export type ApiListResponse<T> = {
  ok?: boolean;
  items?: T[];
};

export type DashboardDepartmentKey =
  | "marketing"
  | "sales"
  | "finance"
  | "operations"
  | "support"
  | "hr";

export type AgentRuntimeCard = {
  id: string;
  label: string;
  role: string;
  departmentKey: DashboardDepartmentKey;
  displayTag?: string;
  state: string;
  workload: number;
  assignedCount?: number;
  throughput?: number;
  conversionPct?: number;
  revenue?: number;
  runtimeStatus?: string;
  queuedCount: number;
  runningCount: number;
  waitingApprovalCount: number;
  failedCount: number;
  completedCount: number;
  totalRuns: number;
  latestRun: WorkflowRun | null;
  runs: WorkflowRun[];
};