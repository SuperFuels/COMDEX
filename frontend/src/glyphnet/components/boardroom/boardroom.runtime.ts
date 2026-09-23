import type { DepartmentKey } from "./boardroom.domain";

export type WorkflowExecutionMode =
  | "draft_only"
  | "draft_then_approval"
  | "manual_only";

export type WorkflowRunStatus =
  | "queued"
  | "running"
  | "waiting_approval"
  | "completed"
  | "failed"
  | "cancelled";

export type WorkflowStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "waiting_approval"
  | "skipped";

export type ApprovalStatus =
  | "pending"
  | "approved"
  | "rejected";

export type RuntimeStepRun = {
  id: string;
  runId: string;
  key: string;
  label: string;
  status: WorkflowStepStatus;
  startedAt?: string;
  completedAt?: string;
  errorMessage?: string;
};

export type RuntimeApprovalRequest = {
  id: string;
  runId: string;
  title: string;
  status: ApprovalStatus;
  requestedAt: string;
  decidedAt?: string;
  decidedBy?: string;
};

export type RuntimeWorkflowRun = {
  id: string;
  department_key: DepartmentKey;
  agent_id?: string;
  workflow_key: string;
  workflow_label: string;
  execution_mode: WorkflowExecutionMode;
  status: WorkflowRunStatus;
  trigger_source: "manual" | "schedule" | "kpi" | "system";
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  failedAt?: string;
  headline?: string;
  summary?: string;
  currentStepKey?: string;
  approvalRequestId?: string;
  connectorKeys?: string[];
  outputCount?: number;
  steps: RuntimeStepRun[];
};

export type BoardroomRuntime = {
  node: {
    status: "online" | "offline" | "paused";
    mode: "local_first" | "hybrid" | "cloud";
    lastHeartbeatAt?: string;
  };
  approvals: RuntimeApprovalRequest[];
  runs: RuntimeWorkflowRun[];
};