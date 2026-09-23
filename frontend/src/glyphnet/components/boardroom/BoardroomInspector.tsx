"use client";

import { useEffect, useState } from "react";
import type {
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
} from "./boardroom.domain";

type ApprovalItem = {
  id: string;
  workflow_run_id: string;
  operator_id: string;
  department_key: string;
  title: string;
  summary: string;
  payload: Record<string, unknown>;
  status: string;
  requested_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_note: string | null;
};

type StepRun = {
  id: string;
  step_id: string;
  kind: string;
  status: string;
  output: Record<string, unknown>;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
};

type WorkflowRun = {
  id: string;
  workflow_id: string;
  workflow_name: string;
  operator_id: string;
  department_key: string;
  trigger_kind: string;
  execution_mode: string;
  status: string;
  current_step_index: number;
  context: Record<string, unknown>;
  step_runs: StepRun[];
  approval_request_id: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};

async function readJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const res = await fetch(input, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function formatDateTime(value?: string | null) {
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

function runStatusColor(status?: string) {
  if (status === "failed") return "#ef4444";
  if (status === "waiting_approval") return "#f59e0b";
  if (status === "running") return "#1a8aff";
  if (status === "queued") return "#6b7280";
  if (status === "completed") return "#22c55e";
  return "#6b7280";
}

function approvalStatusColor(status?: string) {
  if (status === "rejected") return "#ef4444";
  if (status === "approved") return "#22c55e";
  if (status === "pending") return "#f59e0b";
  return "#6b7280";
}

function prettifyStepKind(kind?: string) {
  if (!kind) return "—";
  return kind.replace(/_/g, " ");
}

function fmtKpiValue(value: number | string, unit?: string) {
  if (typeof value === "number") {
    return unit ? `${value}${unit}` : `${value}`;
  }
  return unit ? `${value}${unit}` : value;
}

function fmtMoney(v: number) {
  return `£${v.toLocaleString("en-GB")}`;
}

function goalStatusColor(status: string) {
  if (status === "off_track") return "#ef4444";
  if (status === "at_risk") return "#f59e0b";
  return "#22c55e";
}

function taskStateColor(state: string) {
  if (state === "blocked") return "#ef4444";
  if (state === "in_progress") return "#1a8aff";
  if (state === "done") return "#22c55e";
  return "#6b7280";
}

function stateColor(state?: string) {
  if (state === "blocked") return "#ef4444";
  if (state === "warning") return "#f59e0b";
  if (state === "escalated") return "#f97316";
  return "#22c55e";
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: 12,
        fontWeight: 700,
        color: "#111827",
        marginBottom: 6,
      }}
    >
      {children}
    </div>
  );
}

function EmptyCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        borderRadius: 12,
        border: "1px solid #e5e7eb",
        background: "#f9fafb",
        padding: "10px 12px",
        color: "#6b7280",
        fontSize: 13,
      }}
    >
      {children}
    </div>
  );
}

function StatMiniCard({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: React.ReactNode;
  valueColor?: string;
}) {
  return (
    <div
      style={{
        borderRadius: 12,
        border: "1px solid #e5e7eb",
        background: "#f9fafb",
        padding: "10px 12px",
      }}
    >
      <div style={{ color: "#6b7280", fontSize: 12 }}>{label}</div>
      <div
        style={{
          color: valueColor ?? "#111827",
          fontWeight: 700,
          fontSize: 16,
          marginTop: 4,
        }}
      >
        {value}
      </div>
    </div>
  );
}

function FlowList({
  flows,
  stages,
}: {
  flows: Array<{
    id: string;
    fromStageId: string;
    toStageId: string;
    count: number;
    value?: number;
    state?: string;
    bottleneck?: boolean;
    exception?: boolean;
    blockedCount?: number;
    cycleTimeDays?: number;
  }>;
  stages: DepartmentFloorStage[];
}) {
  if (!flows.length) {
    return <EmptyCard>No flow data loaded yet.</EmptyCard>;
  }

  return (
    <div style={{ display: "grid", gap: 8 }}>
      {flows.map((flow) => {
        const fromLabel =
          stages.find((s) => s.id === flow.fromStageId)?.label ?? flow.fromStageId;
        const toLabel =
          stages.find((s) => s.id === flow.toStageId)?.label ?? flow.toStageId;

        return (
          <div
            key={flow.id}
            style={{
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              padding: "10px 12px",
              display: "flex",
              justifyContent: "space-between",
              gap: 10,
              alignItems: "center",
            }}
          >
            <div style={{ display: "grid", gap: 2 }}>
              <span style={{ color: "#111827", fontSize: 13, fontWeight: 600 }}>
                {fromLabel} → {toLabel}
              </span>
              <span style={{ color: "#6b7280", fontSize: 12 }}>
                {[
                  typeof flow.value === "number" ? fmtMoney(flow.value) : null,
                  typeof flow.cycleTimeDays === "number" ? `${flow.cycleTimeDays}d cycle` : null,
                  (flow.blockedCount ?? 0) > 0 ? `${flow.blockedCount} blocked` : null,
                  flow.bottleneck ? "bottleneck" : null,
                  flow.exception ? "exception" : null,
                ]
                  .filter(Boolean)
                  .join(" · ") || "—"}
              </span>
            </div>
            <span
              style={{
                color: stateColor(flow.state),
                fontWeight: 700,
                fontSize: 13,
              }}
            >
              {flow.count}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function AgentList({
  agents,
}: {
  agents: DepartmentFloorAgent[];
}) {
  if (!agents.length) {
    return <EmptyCard>No agents loaded yet.</EmptyCard>;
  }

  return (
    <div style={{ display: "grid", gap: 8 }}>
      {agents.map((agent) => (
        <div
          key={agent.id}
          style={{
            borderRadius: 12,
            border: "1px solid #e5e7eb",
            background: "#f9fafb",
            padding: "10px 12px",
            display: "grid",
            gap: 4,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 10,
              alignItems: "center",
            }}
          >
            <span style={{ color: "#111827", fontSize: 13, fontWeight: 600 }}>
              {agent.label}
            </span>
            <span
              style={{
                color: stateColor(agent.state),
                fontWeight: 700,
                fontSize: 12,
              }}
            >
              {agent.state.toUpperCase()}
            </span>
          </div>

          <div style={{ color: "#6b7280", fontSize: 12 }}>
            {agent.displayTag ? `${agent.displayTag} · ` : ""}
            {agent.role}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: 8,
              marginTop: 2,
            }}
          >
            <div>
              <div style={{ color: "#94a3b8", fontSize: 11 }}>Load</div>
              <div style={{ color: "#111827", fontSize: 12, fontWeight: 700 }}>
                {agent.workload}
              </div>
            </div>
            <div>
              <div style={{ color: "#94a3b8", fontSize: 11 }}>Assigned</div>
              <div style={{ color: "#111827", fontSize: 12, fontWeight: 700 }}>
                {agent.assignedCount ?? "—"}
              </div>
            </div>
            <div>
              <div style={{ color: "#94a3b8", fontSize: 11 }}>
                {typeof agent.conversionPct === "number" ? "Conv." : "Throughput"}
              </div>
              <div style={{ color: "#111827", fontSize: 12, fontWeight: 700 }}>
                {typeof agent.conversionPct === "number"
                  ? `${agent.conversionPct}%`
                  : agent.throughput ?? "—"}
              </div>
            </div>
          </div>

          {typeof agent.revenue === "number" ? (
            <div style={{ color: "#0f4ea8", fontSize: 12, fontWeight: 700, marginTop: 2 }}>
              Revenue: {fmtMoney(agent.revenue)}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function RuntimeWorkflowCard({
  departmentKey,
  title = "S7 · Workflows / SOPs",
}: {
  departmentKey?: string;
  title?: string;
}) {
  const normalizedDepartment = (departmentKey ?? "").trim().toLowerCase();

  const workflowCards =
    !normalizedDepartment
      ? [
          {
            name: "Marketing Content Draft v1",
            mode: "draft_and_approval",
            approval: "required",
            provider: "runtime-configured",
            steps: [
              "Create brief",
              "Draft caption",
              "Draft carousel",
              "Attach connector context",
              "Pause for approval",
              "Complete run",
            ],
          },
          {
            name: "Sales Workflow Surface",
            mode: "pending",
            approval: "pending",
            provider: "pending",
            steps: ["Department workflow mapping pending"],
          },
          {
            name: "Finance Workflow Surface",
            mode: "pending",
            approval: "pending",
            provider: "pending",
            steps: ["Department workflow mapping pending"],
          },
          {
            name: "Operations Workflow Surface",
            mode: "pending",
            approval: "pending",
            provider: "pending",
            steps: ["Department workflow mapping pending"],
          },
          {
            name: "Support Workflow Surface",
            mode: "pending",
            approval: "pending",
            provider: "pending",
            steps: ["Department workflow mapping pending"],
          },
          {
            name: "HR Workflow Surface",
            mode: "pending",
            approval: "pending",
            provider: "pending",
            steps: ["Department workflow mapping pending"],
          },
        ]
      : normalizedDepartment === "marketing"
        ? [
            {
              name: "Marketing Content Draft v1",
              mode: "draft_and_approval",
              approval: "required",
              provider: "runtime-configured",
              steps: [
                "Create brief",
                "Draft caption",
                "Draft carousel",
                "Attach connector context",
                "Pause for approval",
                "Complete run",
              ],
            },
          ]
        : [
            {
              name: `${normalizedDepartment.toUpperCase()} Workflow Surface`,
              mode: "pending",
              approval: "pending",
              provider: "pending",
              steps: ["Department workflow mapping pending"],
            },
          ];

  return (
    <div>
      <SectionTitle>{title}</SectionTitle>
      <div style={{ display: "grid", gap: 10 }}>
        {workflowCards.map((workflow) => (
          <div
            key={workflow.name}
            style={{
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              padding: "12px 12px",
              display: "grid",
              gap: 8,
            }}
          >
            <div style={{ color: "#111827", fontSize: 13, fontWeight: 700 }}>
              {workflow.name}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                gap: 8,
              }}
            >
              <StatMiniCard label="Mode" value={workflow.mode} />
              <StatMiniCard label="Approval" value={workflow.approval} />
              <StatMiniCard label="Provider" value={workflow.provider} />
            </div>

            <div style={{ display: "grid", gap: 6 }}>
              {workflow.steps.map((step, index) => (
                <div
                  key={`${workflow.name}-${step}-${index}`}
                  style={{
                    borderRadius: 10,
                    border: "1px solid #e5e7eb",
                    background: "#ffffff",
                    padding: "8px 10px",
                    color: "#374151",
                    fontSize: 13,
                  }}
                >
                  {index + 1}. {step}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RuntimeEscalationCard({
  departmentKey,
  title = "S8 · Escalation Rules",
}: {
  departmentKey?: string;
  title?: string;
}) {
  const normalizedDepartment = (departmentKey ?? "").trim().toLowerCase();

  const items =
    !normalizedDepartment
      ? [
          {
            title: "Marketing Approval Gate",
            detail:
              "Public-facing marketing outputs must stop for approval before completion.",
          },
          {
            title: "Connector Safety",
            detail:
              "Unsafe connector/account usage escalates to the operator owner.",
          },
          {
            title: "Repeated Failure",
            detail: "Repeated failures escalate upward for review.",
          },
          {
            title: "Department Escalation",
            detail: "Blocked items escalate to the department owner.",
          },
        ]
      : normalizedDepartment === "marketing"
        ? [
            {
              title: "Approval Gate",
              detail:
                "Public-facing marketing outputs must stop for approval before completion.",
            },
            {
              title: "Connector Safety",
              detail:
                "Unsafe connector/account usage escalates to the operator owner.",
            },
            {
              title: "Retry Policy",
              detail:
                "Failed runs retry only under bounded policy with cooldown and dedupe protection.",
            },
            {
              title: "Ambiguity Handling",
              detail:
                "Unclear or low-confidence output remains draft-only and does not auto-complete publish paths.",
            },
          ]
        : [
            {
              title: "Department Escalation",
              detail: "Blocked items escalate to the department owner.",
            },
            {
              title: "Approval Requirement",
              detail:
                "Risky actions require explicit approval before continuation.",
            },
            {
              title: "Repeated Failure",
              detail: "Repeated failures escalate upward for review.",
            },
          ];

  return (
    <div>
      <SectionTitle>{title}</SectionTitle>
      <div style={{ display: "grid", gap: 8 }}>
        {items.map((item) => (
          <div
            key={item.title}
            style={{
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              padding: "10px 12px",
              display: "grid",
              gap: 4,
            }}
          >
            <div style={{ color: "#111827", fontSize: 13, fontWeight: 700 }}>
              {item.title}
            </div>
            <div style={{ color: "#6b7280", fontSize: 12 }}>{item.detail}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RuntimeToolsCard({
  departmentKey,
  title = "S9 · Connected Tools / Accounts",
}: {
  departmentKey?: string;
  title?: string;
}) {
  const normalizedDepartment = (departmentKey ?? "").trim().toLowerCase();

  const items =
    !normalizedDepartment
      ? [
          { label: "Marketing Operator", value: "operator_marketing_v1" },
          { label: "Marketing Workflow", value: "workflow_marketing_content_draft_v1" },
          { label: "Marketing Connector", value: "meta_facebook" },
          { label: "Approval Path", value: "business-runtime approval queue" },
          { label: "Execution Runtime", value: "workflow runtime" },
        ]
      : normalizedDepartment === "marketing"
        ? [
            { label: "Operator", value: "operator_marketing_v1" },
            { label: "Workflow", value: "workflow_marketing_content_draft_v1" },
            { label: "Connector", value: "meta_facebook" },
            { label: "Approval Path", value: "business-runtime approval queue" },
            { label: "Execution Runtime", value: "workflow runtime" },
          ]
        : [
            { label: "Runtime", value: `${normalizedDepartment}_runtime` },
            { label: "Mapping", value: "Tool/account mapping pending" },
          ];

  return (
    <div>
      <SectionTitle>{title}</SectionTitle>
      <div style={{ display: "grid", gap: 8 }}>
        {items.map((item) => (
          <div
            key={`${item.label}-${item.value}`}
            style={{
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              padding: "10px 12px",
              display: "flex",
              justifyContent: "space-between",
              gap: 10,
              alignItems: "center",
            }}
          >
            <span style={{ color: "#6b7280", fontSize: 12 }}>{item.label}</span>
            <span style={{ color: "#111827", fontSize: 13, fontWeight: 700 }}>
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
function MarketingRuntimePanels() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [brief, setBrief] = useState(
    "Draft a Facebook post and simple carousel for spring telecom upgrade offer.",
  );

async function refreshRuntime() {
  setLoading(true);
  setError(null);

  try {
    const [approvalsJson, runsJson] = await Promise.all([
      readJson<{ items?: ApprovalItem[] }>(
        `/api/local-node/approvals?department_key=marketing`,
      ),
      readJson<{ items?: WorkflowRun[] }>(
        `/api/local-node/runs?department_key=marketing&limit=5`,
      ),
    ]);

    setApprovals(approvalsJson.items ?? []);
    setRuns(runsJson.items ?? []);
  } catch (err) {
    setApprovals([]);
    setRuns([]);
    setError(err instanceof Error ? err.message : "Failed to load runtime panels");
  } finally {
    setLoading(false);
  }
}

useEffect(() => {
  void refreshRuntime();
}, []);

async function handleLaunch() {
  setBusy(true);
  setError(null);

  try {
    await readJson(`/api/local-node/workflows/launch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workflow_definition_id: "workflow_marketing_content_draft_v1",
        agent_definition_id: "agent_marketing_operator_v1",
        context: {
          brief,
          objective: "Generate local business enquiries",
          target_audience: "Local businesses in Almeria",
        },
      }),
    });

    await refreshRuntime();
  } catch (err) {
    setError(err instanceof Error ? err.message : "Launch failed");
  } finally {
    setBusy(false);
  }
}

  async function handleResolveApproval(approvalId: string, approve: boolean) {
    setBusy(true);
    setError(null);

    try {
      await readJson(`/api/local-node/approvals/${approvalId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approve,
          resolved_by: "kevin",
        }),
      });

      await refreshRuntime();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval resolution failed");
    } finally {
      setBusy(false);
    }
  }

  const pendingApprovals = approvals.filter((item) => item.status === "pending");
  const latestRun = runs[0] ?? null;

  return (
    <>
      <div>
        <SectionTitle>BO10 · Operator Inspector</SectionTitle>
        <div style={{ display: "grid", gap: 8 }}>
          <div
            style={{
              borderRadius: 12,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              padding: "12px",
              display: "grid",
              gap: 8,
            }}
          >
            <div style={{ color: "#111827", fontSize: 13, fontWeight: 700 }}>
              Marketing Operator v1
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 8,
              }}
            >
              <StatMiniCard label="Agent ID" value="agent_marketing_operator_v1" />
              <StatMiniCard label="Workflow ID" value="workflow_marketing_content_draft_v1" />
              <StatMiniCard label="Pending Approvals" value={pendingApprovals.length} />
              <StatMiniCard
                label="Latest Run Status"
                value={latestRun?.status ?? "—"}
                valueColor={runStatusColor(latestRun?.status)}
              />
            </div>
          </div>
        </div>
      </div>

      <div>
        <SectionTitle>BO9 · Launch Workflow</SectionTitle>
        <div
          style={{
            borderRadius: 12,
            border: "1px solid #e5e7eb",
            background: "#f9fafb",
            padding: "12px",
            display: "grid",
            gap: 8,
          }}
        >
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            rows={4}
            style={{
              width: "100%",
              resize: "vertical",
              borderRadius: 10,
              border: "1px solid #d1d5db",
              padding: "10px 12px",
              fontSize: 13,
              color: "#111827",
              background: "#ffffff",
              boxSizing: "border-box",
            }}
          />

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={() => void handleLaunch()}
              disabled={busy || loading}
              style={{
                borderRadius: 10,
                border: "1px solid #1a8aff",
                background: "#1a8aff",
                color: "#ffffff",
                padding: "9px 12px",
                fontSize: 13,
                fontWeight: 700,
                cursor: busy || loading ? "not-allowed" : "pointer",
                opacity: busy || loading ? 0.6 : 1,
              }}
            >
              Launch Marketing Workflow
            </button>

            <button
              type="button"
              onClick={() => void refreshRuntime()}
              disabled={busy}
              style={{
                borderRadius: 10,
                border: "1px solid #d1d5db",
                background: "#ffffff",
                color: "#111827",
                padding: "9px 12px",
                fontSize: 13,
                fontWeight: 700,
                cursor: busy ? "not-allowed" : "pointer",
                opacity: busy ? 0.6 : 1,
              }}
            >
              Refresh Runtime
            </button>
          </div>

          {error ? (
            <div
              style={{
                borderRadius: 10,
                border: "1px solid #fecaca",
                background: "#fef2f2",
                color: "#991b1b",
                padding: "8px 10px",
                fontSize: 12,
              }}
            >
              {error}
            </div>
          ) : null}
        </div>
      </div>

      <div>
        <SectionTitle>BO5 · Recent Runs</SectionTitle>
        {loading ? (
          <EmptyCard>Loading runs...</EmptyCard>
        ) : runs.length === 0 ? (
          <EmptyCard>No workflow runs yet.</EmptyCard>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {runs.map((run) => {
              const stepRuns = run.step_runs ?? [];
              const currentStep =
                stepRuns.length > 0
                  ? stepRuns[Math.min(run.current_step_index, stepRuns.length - 1)]
                  : null;

              return (
                <div
                  key={run.id}
                  style={{
                    borderRadius: 12,
                    border: "1px solid #e5e7eb",
                    background: "#f9fafb",
                    padding: "10px 12px",
                    display: "grid",
                    gap: 4,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 10,
                      alignItems: "center",
                    }}
                  >
                    <span style={{ color: "#111827", fontSize: 13, fontWeight: 700 }}>
                      {run.workflow_name}
                    </span>
                    <span
                      style={{
                        color: runStatusColor(run.status),
                        fontWeight: 700,
                        fontSize: 12,
                      }}
                    >
                      {run.status.toUpperCase()}
                    </span>
                  </div>

                  <div style={{ color: "#6b7280", fontSize: 12 }}>
                    {formatDateTime(run.created_at)} · {run.trigger_kind} · {run.execution_mode}
                  </div>

                  <div style={{ color: "#374151", fontSize: 12 }}>
                    Current step: {currentStep ? prettifyStepKind(currentStep.kind) : "—"}
                  </div>

                  {run.failure_reason ? (
                    <div style={{ color: "#ef4444", fontSize: 12, fontWeight: 600 }}>
                      Failure: {run.failure_reason}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div>
        <SectionTitle>BO4 · Pending Approvals</SectionTitle>
        {loading ? (
          <EmptyCard>Loading approvals...</EmptyCard>
        ) : pendingApprovals.length === 0 ? (
          <EmptyCard>No pending approvals.</EmptyCard>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {pendingApprovals.map((item) => (
              <div
                key={item.id}
                style={{
                  borderRadius: 12,
                  border: "1px solid #e5e7eb",
                  background: "#f9fafb",
                  padding: "10px 12px",
                  display: "grid",
                  gap: 6,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 10,
                    alignItems: "center",
                  }}
                >
                  <div style={{ color: "#111827", fontSize: 13, fontWeight: 700 }}>
                    {item.title}
                  </div>
                  <div
                    style={{
                      color: approvalStatusColor(item.status),
                      fontSize: 12,
                      fontWeight: 700,
                    }}
                  >
                    {item.status.toUpperCase()}
                  </div>
                </div>

                <div style={{ color: "#6b7280", fontSize: 12 }}>{item.summary}</div>
                <div style={{ color: "#6b7280", fontSize: 12 }}>
                  Requested: {formatDateTime(item.requested_at)}
                </div>

                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={() => void handleResolveApproval(item.id, true)}
                    disabled={busy}
                    style={{
                      borderRadius: 10,
                      border: "1px solid #22c55e",
                      background: "#22c55e",
                      color: "#ffffff",
                      padding: "8px 12px",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: busy ? "not-allowed" : "pointer",
                      opacity: busy ? 0.6 : 1,
                    }}
                  >
                    Approve
                  </button>

                  <button
                    type="button"
                    onClick={() => void handleResolveApproval(item.id, false)}
                    disabled={busy}
                    style={{
                      borderRadius: 10,
                      border: "1px solid #ef4444",
                      background: "#ffffff",
                      color: "#ef4444",
                      padding: "8px 12px",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: busy ? "not-allowed" : "pointer",
                      opacity: busy ? 0.6 : 1,
                    }}
                  >
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function SeatInspectorView({
  seat,
  salesFloor,
  financeFloor,
  operationsFloor,
  supportFloor,
  hrFloor,
  marketingFloor,
}: {
  seat: Seat;
  salesFloor?: SalesFloorState;
  financeFloor?: FinanceFloorState;
  operationsFloor?: OperationsFloorState;
  supportFloor?: SupportFloorState;
  hrFloor?: HRFloorState;
  marketingFloor?: MarketingFloorState;
}) {
  const isSales = seat.departmentKey === "sales";
  const isFinance = seat.departmentKey === "finance";
  const isOperations = seat.departmentKey === "operations";
  const isSupport = seat.departmentKey === "support";
  const isHr = seat.departmentKey === "hr";
  const isMarketing = seat.departmentKey === "marketing";

  const staleStage = salesFloor?.stages?.find((s) => s.label.toLowerCase() === "stale");
  const wonStage = salesFloor?.stages?.find((s) => s.label.toLowerCase() === "won");
  const proposalStage = salesFloor?.stages?.find((s) => s.label.toLowerCase() === "proposal");
  const newLeadsStage = salesFloor?.stages?.find((s) => s.label.toLowerCase() === "new leads");

  const invoicedStage = financeFloor?.stages?.find((s) => s.label.toLowerCase() === "invoiced");
  const dueStage = financeFloor?.stages?.find((s) => s.label.toLowerCase() === "due");
  const overdueStage = financeFloor?.stages?.find((s) => s.label.toLowerCase() === "overdue");
  const receivedStage = financeFloor?.stages?.find((s) => s.label.toLowerCase() === "received");
  const supplierStage = financeFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "supplier outflow",
  );

  const backlogStage = operationsFloor?.stages?.find((s) => s.label.toLowerCase() === "backlog");
  const scheduledStage = operationsFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "scheduled",
  );
  const inProgressOpsStage = operationsFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "in progress",
  );
  const blockedOpsStage = operationsFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "blocked",
  );
  const completedOpsStage = operationsFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "completed",
  );

  const openSupportStage = supportFloor?.stages?.find((s) => s.label.toLowerCase() === "open");
  const triagedSupportStage = supportFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "triaged",
  );
  const inProgressSupportStage = supportFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "in progress",
  );
  const escalatedSupportStage = supportFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "escalated",
  );
  const resolvedSupportStage = supportFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "resolved",
  );

  const openActionsHrStage = hrFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "open actions",
  );
  const reviewHrStage = hrFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "under review",
  );
  const missingDocsHrStage = hrFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "missing docs",
  );
  const onboardingHrStage = hrFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "onboarding",
  );
  const completedHrStage = hrFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "completed",
  );

  const plannedMarketingStage = marketingFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "planned",
  );
  const liveMarketingStage = marketingFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "live",
  );
  const testingMarketingStage = marketingFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "testing",
  );
  const wasteMarketingStage = marketingFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "waste",
  );
  const qualifiedMarketingStage = marketingFloor?.stages?.find(
    (s) => s.label.toLowerCase() === "qualified leads",
  );

  return (
    <>
      <div>
        <div style={{ fontSize: 12, color: "#6b7280" }}>Seat</div>
        <div style={{ fontSize: 22, fontWeight: 700, color: "#111827" }}>
          {seat.label}
        </div>
        <div style={{ fontSize: 13, color: "#4b5563", marginTop: 4 }}>
          {seat.owner ?? "Unassigned"} · {seat.departmentKey} · {seat.state}
        </div>
      </div>

      <div>
        <SectionTitle>Task Summary</SectionTitle>
        <div style={{ display: "grid", gap: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "#6b7280" }}>Open</span>
            <strong>{seat.openTasks}</strong>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "#6b7280" }}>Due today</span>
            <strong>{seat.dueToday}</strong>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: "#6b7280" }}>Blocked</span>
            <strong>{seat.blockedTasks}</strong>
          </div>
        </div>
      </div>

      <div>
        <SectionTitle>KPIs</SectionTitle>
        <div style={{ display: "grid", gap: 8 }}>
          {(seat.kpis ?? []).length > 0 ? (
            seat.kpis.map((kpi) => (
              <div
                key={kpi.id}
                style={{
                  borderRadius: 12,
                  border: "1px solid #e5e7eb",
                  background: "#f9fafb",
                  padding: "10px 12px",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 10,
                }}
              >
                <span style={{ color: "#6b7280", fontSize: 13 }}>{kpi.label}</span>
                <span style={{ color: "#111827", fontWeight: 700, fontSize: 13 }}>
                  {fmtKpiValue(kpi.value, kpi.unit)}
                </span>
              </div>
            ))
          ) : (
            <EmptyCard>No KPIs configured yet.</EmptyCard>
          )}
        </div>
      </div>

      {isSales && salesFloor ? (
        <>
          <div>
            <SectionTitle>Sales Floor Snapshot</SectionTitle>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 8,
              }}
            >
              <StatMiniCard label="New Leads" value={newLeadsStage?.count ?? "—"} />
              <StatMiniCard label="Proposal" value={proposalStage?.count ?? "—"} />
              <StatMiniCard
                label="Won Value"
                value={typeof wonStage?.value === "number" ? fmtMoney(wonStage.value) : "—"}
              />
              <StatMiniCard
                label="Stale Deals"
                value={staleStage?.count ?? "—"}
                valueColor={staleStage ? stateColor(staleStage.state) : "#111827"}
              />
            </div>
          </div>

          <div>
            <SectionTitle>Stage Flow</SectionTitle>
            <FlowList flows={salesFloor.flows ?? []} stages={salesFloor.stages ?? []} />
          </div>

          <div>
            <SectionTitle>Agent Workload</SectionTitle>
            <AgentList agents={salesFloor.agents ?? []} />
          </div>
        </>
      ) : null}

      {isFinance && financeFloor ? (
        <>
          <div>
            <SectionTitle>Finance Floor Snapshot</SectionTitle>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 8,
              }}
            >
              <StatMiniCard
                label="Invoiced"
                value={typeof invoicedStage?.value === "number" ? fmtMoney(invoicedStage.value) : "—"}
              />
              <StatMiniCard
                label="Due"
                value={typeof dueStage?.value === "number" ? fmtMoney(dueStage.value) : "—"}
              />
              <StatMiniCard
                label="Overdue"
                value={typeof overdueStage?.value === "number" ? fmtMoney(overdueStage.value) : "—"}
                valueColor={overdueStage ? stateColor(overdueStage.state) : "#111827"}
              />
              <StatMiniCard
                label="Received"
                value={typeof receivedStage?.value === "number" ? fmtMoney(receivedStage.value) : "—"}
              />
              <StatMiniCard
                label="Supplier Outflow"
                value={typeof supplierStage?.value === "number" ? fmtMoney(supplierStage.value) : "—"}
              />
              <StatMiniCard
                label="Collections Risk"
                value={overdueStage?.state?.toUpperCase() ?? "HEALTHY"}
                valueColor={stateColor(overdueStage?.state)}
              />
            </div>
          </div>

          <div>
            <SectionTitle>Cash Movement</SectionTitle>
            <FlowList flows={financeFloor.flows ?? []} stages={financeFloor.stages ?? []} />
          </div>

          <div>
            <SectionTitle>Finance Agents</SectionTitle>
            <AgentList agents={financeFloor.agents ?? []} />
          </div>
        </>
      ) : null}

      {isOperations && operationsFloor ? (
        <>
          <div>
            <SectionTitle>Operations Floor Snapshot</SectionTitle>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 8,
              }}
            >
              <StatMiniCard label="Backlog" value={backlogStage?.count ?? "—"} />
              <StatMiniCard label="Scheduled" value={scheduledStage?.count ?? "—"} />
              <StatMiniCard label="In Progress" value={inProgressOpsStage?.count ?? "—"} />
              <StatMiniCard
                label="Blocked"
                value={blockedOpsStage?.count ?? "—"}
                valueColor={blockedOpsStage ? stateColor(blockedOpsStage.state) : "#111827"}
              />
              <StatMiniCard label="Completed" value={completedOpsStage?.count ?? "—"} />
              <StatMiniCard
                label="Ops State"
                value={seat.state.toUpperCase()}
                valueColor={stateColor(seat.state)}
              />
            </div>
          </div>

          <div>
            <SectionTitle>Operations Flow</SectionTitle>
            <FlowList
              flows={operationsFloor.flows ?? []}
              stages={operationsFloor.stages ?? []}
            />
          </div>

          <div>
            <SectionTitle>Operations Agents</SectionTitle>
            <AgentList agents={operationsFloor.agents ?? []} />
          </div>
        </>
      ) : null}

      {isSupport && supportFloor ? (
        <>
          <div>
            <SectionTitle>Support Floor Snapshot</SectionTitle>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 8,
              }}
            >
              <StatMiniCard label="Open" value={openSupportStage?.count ?? "—"} />
              <StatMiniCard label="Triaged" value={triagedSupportStage?.count ?? "—"} />
              <StatMiniCard
                label="In Progress"
                value={inProgressSupportStage?.count ?? "—"}
              />
              <StatMiniCard
                label="Escalated"
                value={escalatedSupportStage?.count ?? "—"}
                valueColor={
                  escalatedSupportStage ? stateColor(escalatedSupportStage.state) : "#111827"
                }
              />
              <StatMiniCard label="Resolved" value={resolvedSupportStage?.count ?? "—"} />
              <StatMiniCard
                label="Support State"
                value={seat.state.toUpperCase()}
                valueColor={stateColor(seat.state)}
              />
            </div>
          </div>

          <div>
            <SectionTitle>Support Flow</SectionTitle>
            <FlowList flows={supportFloor.flows ?? []} stages={supportFloor.stages ?? []} />
          </div>

          <div>
            <SectionTitle>Support Agents</SectionTitle>
            <AgentList agents={supportFloor.agents ?? []} />
          </div>
        </>
      ) : null}

      {isHr && hrFloor ? (
        <>
          <div>
            <SectionTitle>HR Floor Snapshot</SectionTitle>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 8,
              }}
            >
              <StatMiniCard label="Open Actions" value={openActionsHrStage?.count ?? "—"} />
              <StatMiniCard label="Under Review" value={reviewHrStage?.count ?? "—"} />
              <StatMiniCard
                label="Missing Docs"
                value={missingDocsHrStage?.count ?? "—"}
                valueColor={missingDocsHrStage ? stateColor(missingDocsHrStage.state) : "#111827"}
              />
              <StatMiniCard label="Onboarding" value={onboardingHrStage?.count ?? "—"} />
              <StatMiniCard label="Completed" value={completedHrStage?.count ?? "—"} />
              <StatMiniCard
                label="HR State"
                value={seat.state.toUpperCase()}
                valueColor={stateColor(seat.state)}
              />
            </div>
          </div>

          <div>
            <SectionTitle>HR Flow</SectionTitle>
            <FlowList flows={hrFloor.flows ?? []} stages={hrFloor.stages ?? []} />
          </div>

          <div>
            <SectionTitle>HR Agents</SectionTitle>
            <AgentList agents={hrFloor.agents ?? []} />
          </div>
        </>
      ) : null}

      {isMarketing && marketingFloor ? (
        <>
          <div>
            <SectionTitle>Marketing Floor Snapshot</SectionTitle>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 8,
              }}
            >
              <StatMiniCard label="Planned" value={plannedMarketingStage?.count ?? "—"} />
              <StatMiniCard label="Live" value={liveMarketingStage?.count ?? "—"} />
              <StatMiniCard label="Testing" value={testingMarketingStage?.count ?? "—"} />
              <StatMiniCard
                label="Waste"
                value={wasteMarketingStage?.count ?? "—"}
                valueColor={wasteMarketingStage ? stateColor(wasteMarketingStage.state) : "#111827"}
              />
              <StatMiniCard
                label="Qualified Leads"
                value={qualifiedMarketingStage?.count ?? "—"}
              />
              <StatMiniCard
                label="Marketing State"
                value={seat.state.toUpperCase()}
                valueColor={stateColor(seat.state)}
              />
            </div>
          </div>

          <div>
            <SectionTitle>Marketing Flow</SectionTitle>
            <FlowList
              flows={marketingFloor.flows ?? []}
              stages={marketingFloor.stages ?? []}
            />
          </div>

          <div>
            <SectionTitle>Marketing Agents</SectionTitle>
            <AgentList agents={marketingFloor.agents ?? []} />
          </div>

          <RuntimeWorkflowCard departmentKey="marketing" />
          <RuntimeEscalationCard departmentKey="marketing" />
          <RuntimeToolsCard departmentKey="marketing" />
          <MarketingRuntimePanels />
        </>
      ) : null}

      <div>
        <SectionTitle>Goals</SectionTitle>
        <div style={{ display: "grid", gap: 8 }}>
          {(seat.goals ?? []).length > 0 ? (
            seat.goals.map((goal) => (
              <div
                key={goal.id}
                style={{
                  borderRadius: 12,
                  border: "1px solid #e5e7eb",
                  background: "#f9fafb",
                  padding: "10px 12px",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 10,
                  alignItems: "center",
                }}
              >
                <span style={{ color: "#111827", fontSize: 13 }}>{goal.title}</span>
                <span
                  style={{
                    color: goalStatusColor(goal.status),
                    fontWeight: 700,
                    fontSize: 12,
                  }}
                >
                  {goal.status.replace("_", " ").toUpperCase()}
                </span>
              </div>
            ))
          ) : (
            <EmptyCard>No goals assigned yet.</EmptyCard>
          )}
        </div>
      </div>

      <div>
        <SectionTitle>Active Tasks</SectionTitle>
        <div style={{ display: "grid", gap: 8 }}>
          {(seat.tasks ?? []).length > 0 ? (
            seat.tasks.map((task) => (
              <div
                key={task.id}
                style={{
                  borderRadius: 12,
                  border: "1px solid #e5e7eb",
                  background: "#f9fafb",
                  padding: "10px 12px",
                  display: "grid",
                  gap: 4,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 10,
                    alignItems: "center",
                  }}
                >
                  <span style={{ color: "#111827", fontSize: 13, fontWeight: 600 }}>
                    {task.title}
                  </span>
                  <span
                    style={{
                      color: taskStateColor(task.state),
                      fontWeight: 700,
                      fontSize: 12,
                    }}
                  >
                    {task.state.replace("_", " ").toUpperCase()}
                  </span>
                </div>
                <div style={{ color: "#6b7280", fontSize: 12 }}>
                  Priority: {task.priority.toUpperCase()}
                  {task.dueAt ? ` · Due ${task.dueAt}` : ""}
                </div>
              </div>
            ))
          ) : (
            <EmptyCard>No tasks loaded yet.</EmptyCard>
          )}
        </div>
      </div>
    </>
  );
}

function StageInspectorView({
  title,
  stage,
  stages,
  flows,
}: {
  title: string;
  stage: DepartmentFloorStage;
  stages: DepartmentFloorStage[];
  flows: Array<{
    id: string;
    fromStageId: string;
    toStageId: string;
    count: number;
    value?: number;
    state?: string;
  }>;
}) {
  const inbound = flows.filter((flow) => flow.toStageId === stage.id);
  const outbound = flows.filter((flow) => flow.fromStageId === stage.id);

  return (
    <>
      <div>
        <div style={{ fontSize: 12, color: "#6b7280" }}>{title}</div>
        <div style={{ fontSize: 22, fontWeight: 700, color: "#111827" }}>
          {stage.label}
        </div>
        <div style={{ fontSize: 13, color: "#4b5563", marginTop: 4 }}>
          {stage.departmentKey} · {stage.entityType} · {stage.state ?? "healthy"}
        </div>
      </div>

      <div>
        <SectionTitle>Stage Snapshot</SectionTitle>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 8,
          }}
        >
          <StatMiniCard label="Count" value={stage.count} />
          <StatMiniCard
            label="Value"
            value={typeof stage.value === "number" ? fmtMoney(stage.value) : "—"}
          />
          <StatMiniCard
            label="State"
            value={stage.state?.toUpperCase() ?? "HEALTHY"}
            valueColor={stateColor(stage.state)}
          />
          <StatMiniCard label="Type" value="STAGE" />
        </div>
      </div>

      <div>
        <SectionTitle>Inbound Flow</SectionTitle>
        <FlowList flows={inbound} stages={stages} />
      </div>

      <div>
        <SectionTitle>Outbound Flow</SectionTitle>
        <FlowList flows={outbound} stages={stages} />
      </div>

      <RuntimeWorkflowCard departmentKey={stage.departmentKey} />
      <RuntimeEscalationCard departmentKey={stage.departmentKey} />
      <RuntimeToolsCard departmentKey={stage.departmentKey} />
      {stage.departmentKey === "marketing" ? <MarketingRuntimePanels /> : null}
    </>
  );
}

function FlowInspectorView({
  title,
  flow,
  stages,
}: {
  title: string;
  flow: DepartmentFloorFlow;
  stages: DepartmentFloorStage[];
}) {
  const fromLabel =
    stages.find((s) => s.id === flow.fromStageId)?.label ?? flow.fromStageId;
  const toLabel =
    stages.find((s) => s.id === flow.toStageId)?.label ?? flow.toStageId;

  return (
    <>
      <div>
        <div style={{ fontSize: 12, color: "#6b7280" }}>{title}</div>
        <div style={{ fontSize: 22, fontWeight: 700, color: "#111827" }}>
          {fromLabel} → {toLabel}
        </div>
        <div style={{ fontSize: 13, color: "#4b5563", marginTop: 4 }}>
          {flow.departmentKey} · flow · {flow.state ?? "healthy"}
        </div>
      </div>

      <div>
        <SectionTitle>Flow Snapshot</SectionTitle>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 8,
          }}
        >
          <StatMiniCard label="From" value={fromLabel} />
          <StatMiniCard label="To" value={toLabel} />
          <StatMiniCard label="Count" value={flow.count} />
          <StatMiniCard
            label="Value"
            value={typeof flow.value === "number" ? fmtMoney(flow.value) : "—"}
          />
          <StatMiniCard
            label="Cycle Time"
            value={
              typeof flow.cycleTimeDays === "number" ? `${flow.cycleTimeDays}d` : "—"
            }
          />
          <StatMiniCard
            label="Blocked"
            value={flow.blockedCount ?? 0}
            valueColor={(flow.blockedCount ?? 0) > 0 ? "#ef4444" : "#111827"}
          />
          <StatMiniCard
            label="Bottleneck"
            value={flow.bottleneck ? "YES" : "NO"}
            valueColor={flow.bottleneck ? "#f59e0b" : "#22c55e"}
          />
          <StatMiniCard
            label="Exception"
            value={flow.exception ? "YES" : "NO"}
            valueColor={flow.exception ? "#ef4444" : "#22c55e"}
          />
          <StatMiniCard
            label="State"
            value={flow.state?.toUpperCase() ?? "HEALTHY"}
            valueColor={stateColor(flow.state)}
          />
          <StatMiniCard label="Type" value="FLOW" />
        </div>
      </div>

      <div>
        <SectionTitle>Flow Notes</SectionTitle>
        <EmptyCard>
          {flow.exception
            ? "This route is currently marked as an exception path."
            : flow.bottleneck
              ? "This route is currently the bottleneck in the chain."
              : (flow.blockedCount ?? 0) > 0
                ? "This route has blocked items that need clearing."
                : "Flow is currently operating normally."}
        </EmptyCard>
      </div>

      <RuntimeWorkflowCard departmentKey={flow.departmentKey} />
      <RuntimeEscalationCard departmentKey={flow.departmentKey} />
      <RuntimeToolsCard departmentKey={flow.departmentKey} />
      {flow.departmentKey === "marketing" ? <MarketingRuntimePanels /> : null}
    </>
  );
}

function AgentInspectorView({
  title,
  agent,
}: {
  title: string;
  agent: DepartmentFloorAgent;
}) {
  return (
    <>
      <div>
        <div style={{ fontSize: 12, color: "#6b7280" }}>{title}</div>
        <div style={{ fontSize: 22, fontWeight: 700, color: "#111827" }}>
          {agent.label}
        </div>
        <div style={{ fontSize: 13, color: "#4b5563", marginTop: 4 }}>
          {agent.displayTag ?? "AGENT"} · {agent.role} · {agent.state}
        </div>
      </div>

      <div>
        <SectionTitle>Agent Snapshot</SectionTitle>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 8,
          }}
        >
          <StatMiniCard
            label="State"
            value={agent.state.toUpperCase()}
            valueColor={stateColor(agent.state)}
          />
          <StatMiniCard label="Load" value={agent.workload} />
          <StatMiniCard label="Assigned" value={agent.assignedCount ?? "—"} />
          <StatMiniCard
            label="Conversion"
            value={typeof agent.conversionPct === "number" ? `${agent.conversionPct}%` : "—"}
          />
          <StatMiniCard label="Throughput" value={agent.throughput ?? "—"} />
          <StatMiniCard
            label="Revenue"
            value={typeof agent.revenue === "number" ? fmtMoney(agent.revenue) : "—"}
          />
        </div>
      </div>

      <div>
        <SectionTitle>Role</SectionTitle>
        <EmptyCard>{agent.role}</EmptyCard>
      </div>

      <RuntimeWorkflowCard departmentKey={agent.departmentKey} />
      <RuntimeEscalationCard departmentKey={agent.departmentKey} />
      <RuntimeToolsCard departmentKey={agent.departmentKey} />
      {agent.departmentKey === "marketing" ? <MarketingRuntimePanels /> : null}
    </>
  );
}

function OperationsStageInspectorView({
  stage,
  operationsFloor,
}: {
  stage: DepartmentFloorStage;
  operationsFloor?: OperationsFloorState;
}) {
  return (
    <StageInspectorView
      title="Operations Stage"
      stage={stage}
      stages={operationsFloor?.stages ?? []}
      flows={operationsFloor?.flows ?? []}
    />
  );
}

function OperationsAgentInspectorView({
  agent,
}: {
  agent: DepartmentFloorAgent;
}) {
  return <AgentInspectorView title="Operations Agent" agent={agent} />;
}

function SupportStageInspectorView({
  stage,
  supportFloor,
}: {
  stage: DepartmentFloorStage;
  supportFloor?: SupportFloorState;
}) {
  return (
    <StageInspectorView
      title="Support Stage"
      stage={stage}
      stages={supportFloor?.stages ?? []}
      flows={supportFloor?.flows ?? []}
    />
  );
}

function SupportAgentInspectorView({
  agent,
}: {
  agent: DepartmentFloorAgent;
}) {
  return <AgentInspectorView title="Support Agent" agent={agent} />;
}

function HRStageInspectorView({
  stage,
  hrFloor,
}: {
  stage: DepartmentFloorStage;
  hrFloor?: HRFloorState;
}) {
  return (
    <StageInspectorView
      title="HR Stage"
      stage={stage}
      stages={hrFloor?.stages ?? []}
      flows={hrFloor?.flows ?? []}
    />
  );
}

function HrAgentInspectorView({
  agent,
}: {
  agent: DepartmentFloorAgent;
}) {
  return <AgentInspectorView title="HR Agent" agent={agent} />;
}

function MarketingStageInspectorView({
  stage,
  marketingFloor,
}: {
  stage: DepartmentFloorStage;
  marketingFloor?: MarketingFloorState;
}) {
  return (
    <StageInspectorView
      title="Marketing Stage"
      stage={stage}
      stages={marketingFloor?.stages ?? []}
      flows={marketingFloor?.flows ?? []}
    />
  );
}

function MarketingAgentInspectorView({
  agent,
}: {
  agent: DepartmentFloorAgent;
}) {
  return <AgentInspectorView title="Marketing Agent" agent={agent} />;
}

export default function BoardroomInspector({
  seat,
  salesFloor,
  financeFloor,
  operationsFloor,
  supportFloor,
  hrFloor,
  marketingFloor,
  salesStage,
  salesAgent,
  financeStage,
  financeAgent,
  operationsStage,
  operationsAgent,
  supportStage,
  supportAgent,
  hrStage,
  hrAgent,
  marketingStage,
  marketingAgent,
  salesFlow,
  financeFlow,
  operationsFlow,
  supportFlow,
  hrFlow,
  marketingFlow,
}: {
  seat: Seat | null;
  salesFloor?: SalesFloorState;
  financeFloor?: FinanceFloorState;
  operationsFloor?: OperationsFloorState;
  supportFloor?: SupportFloorState;
  hrFloor?: HRFloorState;
  marketingFloor?: MarketingFloorState;
  salesStage?: DepartmentFloorStage | null;
  salesAgent?: DepartmentFloorAgent | null;
  financeStage?: DepartmentFloorStage | null;
  financeAgent?: DepartmentFloorAgent | null;
  operationsStage?: DepartmentFloorStage | null;
  operationsAgent?: DepartmentFloorAgent | null;
  supportStage?: DepartmentFloorStage | null;
  supportAgent?: DepartmentFloorAgent | null;
  hrStage?: DepartmentFloorStage | null;
  hrAgent?: DepartmentFloorAgent | null;
  marketingStage?: DepartmentFloorStage | null;
  marketingAgent?: DepartmentFloorAgent | null;
  salesFlow?: DepartmentFloorFlow | null;
  financeFlow?: DepartmentFloorFlow | null;
  operationsFlow?: DepartmentFloorFlow | null;
  supportFlow?: DepartmentFloorFlow | null;
  hrFlow?: DepartmentFloorFlow | null;
  marketingFlow?: DepartmentFloorFlow | null;
}) {
  if (salesStage) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <StageInspectorView
          title="Sales Stage"
          stage={salesStage}
          stages={salesFloor?.stages ?? []}
          flows={salesFloor?.flows ?? []}
        />
      </div>
    );
  }

  if (salesAgent) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <AgentInspectorView title="Sales Agent" agent={salesAgent} />
      </div>
    );
  }

  if (salesFlow) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <FlowInspectorView
          title="Sales Flow"
          flow={salesFlow}
          stages={salesFloor?.stages ?? []}
        />
      </div>
    );
  }

  if (financeStage) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <StageInspectorView
          title="Finance Stage"
          stage={financeStage}
          stages={financeFloor?.stages ?? []}
          flows={financeFloor?.flows ?? []}
        />
      </div>
    );
  }

  if (financeAgent) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <AgentInspectorView title="Finance Agent" agent={financeAgent} />
      </div>
    );
  }

  if (financeFlow) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <FlowInspectorView
          title="Finance Flow"
          flow={financeFlow}
          stages={financeFloor?.stages ?? []}
        />
      </div>
    );
  }

  if (operationsStage) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <OperationsStageInspectorView
          stage={operationsStage}
          operationsFloor={operationsFloor}
        />
      </div>
    );
  }

  if (operationsAgent) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <OperationsAgentInspectorView agent={operationsAgent} />
      </div>
    );
  }

  if (operationsFlow) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <FlowInspectorView
          title="Operations Flow"
          flow={operationsFlow}
          stages={operationsFloor?.stages ?? []}
        />
      </div>
    );
  }

  if (supportStage) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <SupportStageInspectorView stage={supportStage} supportFloor={supportFloor} />
      </div>
    );
  }

  if (supportAgent) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <SupportAgentInspectorView agent={supportAgent} />
      </div>
    );
  }

  if (supportFlow) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <FlowInspectorView
          title="Support Flow"
          flow={supportFlow}
          stages={supportFloor?.stages ?? []}
        />
      </div>
    );
  }

  if (hrStage) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <HRStageInspectorView stage={hrStage} hrFloor={hrFloor} />
      </div>
    );
  }

  if (hrAgent) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <HrAgentInspectorView agent={hrAgent} />
      </div>
    );
  }

  if (hrFlow) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <FlowInspectorView
          title="HR Flow"
          flow={hrFlow}
          stages={hrFloor?.stages ?? []}
        />
      </div>
    );
  }

  if (marketingStage) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <MarketingStageInspectorView
          stage={marketingStage}
          marketingFloor={marketingFloor}
        />
      </div>
    );
  }

  if (marketingAgent) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <MarketingAgentInspectorView agent={marketingAgent} />
      </div>
    );
  }

  if (marketingFlow) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <FlowInspectorView
          title="Marketing Flow"
          flow={marketingFlow}
          stages={marketingFloor?.stages ?? []}
        />
      </div>
    );
  }

  if (!seat) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid #e5e7eb",
          background: "#ffffff",
          padding: 16,
          color: "#6b7280",
          fontSize: 13,
        }}
      >
        Select a seat, stage, or agent to inspect goals, KPIs, tasks, and operating
        state.
      </div>
    );
  }

  return (
    <div
      style={{
        borderRadius: 16,
        border: "1px solid #e5e7eb",
        background: "#ffffff",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <SeatInspectorView
        seat={seat}
        salesFloor={salesFloor}
        financeFloor={financeFloor}
        operationsFloor={operationsFloor}
        supportFloor={supportFloor}
        hrFloor={hrFloor}
        marketingFloor={marketingFloor}
      />
    </div>
  );
}