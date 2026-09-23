import type {
  BoardroomInspectorTarget,
  BoardroomViewMode,
} from "./boardroom.domain";
import type { BoardroomWorldZone } from "./QFCBoardroomWorld";
import type {
  DashboardDepartmentKey,
  WorkflowRun,
} from "./boardroom.page.types";

export async function readJson<T>(
  input: RequestInfo,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(input, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function zoneLabel(
  activeZone: BoardroomWorldZone,
  viewMode: BoardroomViewMode,
) {
  if (viewMode === "dashboard") return "Dashboard Mode";
  if (viewMode === "operations_flow") return "Operations Flow Mode";
  if (viewMode === "live_agents") return "Live Agents";
  if (activeZone === "coo") return "COO Core";
  return `${activeZone.toUpperCase()} Floor`;
}

export function prettifyStatus(value?: string | null) {
  if (!value) return "—";
  return value.replace(/_/g, " ");
}

export function formatTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function getCurrentStepLabel(run?: WorkflowRun | null) {
  if (!run) return "—";
  const step = run.step_runs[run.current_step_index];
  if (!step) return "—";
  return prettifyStatus(step.kind);
}

export function getStepLabelFromRun(run?: WorkflowRun | null) {
  if (!run) return "—";
  const stepRuns = run.step_runs ?? [];
  if (stepRuns.length === 0) return "—";

  const index = Math.min(run.current_step_index ?? 0, stepRuns.length - 1);
  const step = stepRuns[index];
  return step ? prettifyStatus(step.kind) : "—";
}

export function getMarketingStatusTone(status?: string | null) {
  if (status === "completed" || status === "approved" || status === "ready") {
    return {
      background: "rgba(16,185,129,0.12)",
      border: "1px solid rgba(16,185,129,0.28)",
      color: "#047857",
    };
  }

  if (status === "waiting_approval" || status === "pending") {
    return {
      background: "rgba(245,158,11,0.12)",
      border: "1px solid rgba(245,158,11,0.28)",
      color: "#b45309",
    };
  }

  if (status === "failed" || status === "rejected" || status === "blocked") {
    return {
      background: "rgba(239,68,68,0.12)",
      border: "1px solid rgba(239,68,68,0.28)",
      color: "#b91c1c",
    };
  }

  if (status === "running" || status === "in_progress") {
    return {
      background: "rgba(26,138,255,0.12)",
      border: "1px solid rgba(26,138,255,0.28)",
      color: "#0f4ea8",
    };
  }

  return {
    background: "rgba(100,116,139,0.10)",
    border: "1px solid rgba(148,163,184,0.24)",
    color: "#475569",
  };
}

export function zoneToDepartmentKey(
  zone: BoardroomWorldZone,
): DashboardDepartmentKey | undefined {
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

export function departmentToAgentTarget(
  departmentKey: DashboardDepartmentKey,
  agentId: string,
): BoardroomInspectorTarget {
  if (departmentKey === "sales") return { kind: "sales_agent", agentId };
  if (departmentKey === "finance") return { kind: "finance_agent", agentId };
  if (departmentKey === "operations") {
    return { kind: "operations_agent", agentId };
  }
  if (departmentKey === "support") return { kind: "support_agent", agentId };
  if (departmentKey === "hr") return { kind: "hr_agent", agentId };
  return { kind: "marketing_agent", agentId };
}

export function getRunSortTime(run: WorkflowRun) {
  return new Date(run.updated_at || run.created_at).getTime();
}