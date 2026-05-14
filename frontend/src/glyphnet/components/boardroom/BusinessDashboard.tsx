"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

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

type DashboardProps = {
  workspaceId?: string;
  departmentKey?: string;
  operatorId?: string;
  workflowId?: string;
  apiBase?: string;
  resolvedBy?: string;
  className?: string;
  activeZone?: string;
  onLaunchWorkflow?: () => void;
  onSelectMarketing?: () => void;
};

type ApiListResponse<T> = {
  ok?: boolean;
  items?: T[];
};

const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8080";

const DEPARTMENT_COPY: Record<
  string,
  {
    eyebrow: string;
    title: string;
    description: string;
    launchTitle: string;
    launchDescription: string;
    briefLabel: string;
    briefPlaceholder: string;
    operatorContractTitle: string;
    workflowSteps: string[];
    escalationRules: string[];
    connectedTools: string[];
    openFloorLabel?: string;
    briefDefault: string;
    approvalDraftTitle: string;
    outputDraftTitle: string;
  }
> = {
  marketing: {
    eyebrow: "Marketing Operations",
    title: "Marketing Agent Cockpit",
    description:
      "Launch draft workflows, review approvals, inspect outputs, and track the operator’s recent execution history from one surface.",
    launchTitle: "Create a new marketing draft",
    launchDescription: "This launches the operator in draft-and-approval mode.",
    briefLabel: "Content brief",
    briefPlaceholder: "Describe the marketing draft you want the operator to create.",
    operatorContractTitle: "Marketing Agent v1",
    workflowSteps: [
      "Create brief",
      "Draft caption",
      "Draft carousel",
      "Attach connector context",
      "Pause for approval",
      "Complete run",
    ],
    escalationRules: [
      "Public publish requires approval",
      "Connector misuse escalates to operator owner",
      "Failed run retried only under bounded policy",
      "Ambiguous output stays draft-only",
    ],
    connectedTools: [
      "meta_facebook",
      "approval queue",
      "workflow runtime",
      "operator_marketing_v1",
    ],
    openFloorLabel: "Open marketing floor",
    briefDefault: "Draft a Facebook post and simple carousel for spring telecom upgrade offer.",
    approvalDraftTitle: "Draft caption",
    outputDraftTitle: "Draft caption",
  },
  sales: {
    eyebrow: "Sales Operations",
    title: "Sales Execution Desk",
    description:
      "Track pipeline activity, review sales workflow runs, inspect outputs, and monitor execution state from one surface.",
    launchTitle: "Create a new sales workflow",
    launchDescription: "This launches the sales operator in controlled execution mode.",
    briefLabel: "Sales brief",
    briefPlaceholder: "Describe the sales workflow, lead follow-up, or pipeline task to run.",
    operatorContractTitle: "Sales Agent v1",
    workflowSteps: [
      "Load pipeline context",
      "Assess lead state",
      "Draft action output",
      "Attach CRM / connector context",
      "Pause for approval when required",
      "Complete run",
    ],
    escalationRules: [
      "High-risk outreach requires approval",
      "Connector misuse escalates to operator owner",
      "Repeated failure triggers review",
      "Low-confidence actions remain draft-only",
    ],
    connectedTools: [
      "sales_runtime",
      "crm_connector",
      "workflow runtime",
      "operator_sales_v1",
    ],
    briefDefault: "Review current pipeline, identify stale deals, and draft next-step actions for top opportunities.",
    approvalDraftTitle: "Draft action",
    outputDraftTitle: "Draft action",
  },
  finance: {
    eyebrow: "Finance Operations",
    title: "Finance Control Desk",
    description:
      "Review finance workflow runs, inspect cash and collections tasks, and monitor approvals and execution state.",
    launchTitle: "Create a new finance workflow",
    launchDescription: "This launches the finance operator in controlled execution mode.",
    briefLabel: "Finance brief",
    briefPlaceholder: "Describe the finance task, reconciliation, or cash-control workflow to run.",
    operatorContractTitle: "Finance Agent v1",
    workflowSteps: [
      "Load finance context",
      "Assess cash / debtor state",
      "Draft finance action",
      "Attach ledger / connector context",
      "Pause for approval when required",
      "Complete run",
    ],
    escalationRules: [
      "Sensitive financial actions require approval",
      "Connector misuse escalates to operator owner",
      "Repeated failure triggers review",
      "Low-confidence actions remain draft-only",
    ],
    connectedTools: [
      "finance_runtime",
      "ledger_connector",
      "workflow runtime",
      "operator_finance_v1",
    ],
    briefDefault: "Review cash position, debtor pressure, and draft the next finance control actions.",
    approvalDraftTitle: "Draft finance action",
    outputDraftTitle: "Draft finance action",
  },
  operations: {
    eyebrow: "Operations Management",
    title: "Operations Control Desk",
    description:
      "Track delivery workflows, inspect blocked jobs, and review execution and approval state from one surface.",
    launchTitle: "Create a new operations workflow",
    launchDescription: "This launches the operations operator in controlled execution mode.",
    briefLabel: "Operations brief",
    briefPlaceholder: "Describe the operational task, backlog item, or fulfilment workflow to run.",
    operatorContractTitle: "Operations Agent v1",
    workflowSteps: [
      "Load delivery context",
      "Assess backlog / blockers",
      "Draft operational action",
      "Attach runtime context",
      "Pause for approval when required",
      "Complete run",
    ],
    escalationRules: [
      "Risky execution paths require approval",
      "Connector misuse escalates to operator owner",
      "Repeated failure triggers review",
      "Blocked flows remain held for inspection",
    ],
    connectedTools: [
      "operations_runtime",
      "queue_connector",
      "workflow runtime",
      "operator_operations_v1",
    ],
    briefDefault: "Review backlog, blocked jobs, and propose the next operational actions to recover throughput.",
    approvalDraftTitle: "Draft operational action",
    outputDraftTitle: "Draft operational action",
  },
  support: {
    eyebrow: "Support Operations",
    title: "Support Resolution Desk",
    description:
      "Review support workflow runs, inspect ticket handling, and monitor execution and approval state from one surface.",
    launchTitle: "Create a new support workflow",
    launchDescription: "This launches the support operator in controlled execution mode.",
    briefLabel: "Support brief",
    briefPlaceholder: "Describe the support issue, queue task, or service workflow to run.",
    operatorContractTitle: "Support Agent v1",
    workflowSteps: [
      "Load ticket context",
      "Assess issue state",
      "Draft support action",
      "Attach support connector context",
      "Pause for approval when required",
      "Complete run",
    ],
    escalationRules: [
      "Sensitive customer actions require approval",
      "Connector misuse escalates to operator owner",
      "Repeated failure triggers review",
      "Unclear actions remain draft-only",
    ],
    connectedTools: [
      "support_runtime",
      "ticket_connector",
      "workflow runtime",
      "operator_support_v1",
    ],
    briefDefault: "Review open tickets and draft the highest-priority support actions for resolution.",
    approvalDraftTitle: "Draft support action",
    outputDraftTitle: "Draft support action",
  },
  hr: {
    eyebrow: "HR Operations",
    title: "HR Admin Desk",
    description:
      "Review people and admin workflow runs, inspect outputs, and monitor execution and approval state from one surface.",
    launchTitle: "Create a new HR workflow",
    launchDescription: "This launches the HR operator in controlled execution mode.",
    briefLabel: "HR brief",
    briefPlaceholder: "Describe the HR, admin, or compliance workflow to run.",
    operatorContractTitle: "HR Agent v1",
    workflowSteps: [
      "Load HR context",
      "Assess request / admin state",
      "Draft HR action",
      "Attach HR connector context",
      "Pause for approval when required",
      "Complete run",
    ],
    escalationRules: [
      "Sensitive people actions require approval",
      "Connector misuse escalates to operator owner",
      "Repeated failure triggers review",
      "Low-confidence actions remain draft-only",
    ],
    connectedTools: [
      "hr_runtime",
      "people_connector",
      "workflow runtime",
      "operator_hr_v1",
    ],
    briefDefault: "Review open HR and admin actions, then draft the next recommended actions.",
    approvalDraftTitle: "Draft HR action",
    outputDraftTitle: "Draft HR action",
  },
};

function buildUrl(
  base: string,
  path: string,
  params?: Record<string, string | number | undefined>,
) {
  const url = new URL(`${base}${path}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url.toString();
}

function formatTime(value?: string | null) {
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

function formatTimeLong(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function prettifyStatus(value?: string | null) {
  if (!value) return "—";
  return value.replace(/_/g, " ");
}

function extractLatestResult(run: WorkflowRun): string {
  const result = run.context?.result;
  if (result && typeof result === "object") {
    const status = (result as Record<string, unknown>).status;
    if (typeof status === "string") return status;
  }
  if (run.failure_reason) return run.failure_reason;
  return run.status;
}

function getCurrentStepLabel(run: WorkflowRun): string {
  const step = run.step_runs[run.current_step_index];
  if (!step) return "—";
  return step.kind.replace(/_/g, " ");
}

function getStatusTone(status?: string | null) {
  if (status === "completed" || status === "approved" || status === "ready") {
    return "bg-emerald-100 text-emerald-700 border-emerald-200";
  }
  if (status === "waiting_approval" || status === "pending") {
    return "bg-amber-100 text-amber-700 border-amber-200";
  }
  if (status === "failed" || status === "rejected" || status === "blocked") {
    return "bg-red-100 text-red-700 border-red-200";
  }
  if (status === "running" || status === "in_progress") {
    return "bg-blue-100 text-blue-700 border-blue-200";
  }
  return "bg-slate-100 text-slate-700 border-slate-200";
}

function stringifyValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function extractPrimaryDraftValue(run: WorkflowRun): unknown {
  const context = run.context ?? {};
  return (
    context.draft_caption ??
    context.draft_action ??
    context.draft_finance_action ??
    context.draft_operational_action ??
    context.draft_support_action ??
    context.draft_hr_action ??
    context.caption ??
    context.action ??
    context.result
  );
}

function extractCarouselItems(run: WorkflowRun): unknown[] {
  const context = run.context ?? {};
  const candidate =
    context.draft_carousel ??
    context.draft_actions ??
    context.action_items ??
    context.carousel ??
    context.result;

  if (Array.isArray(candidate)) return candidate;
  return [];
}

export default function BusinessDashboard({
  workspaceId = "costa-conexion",
  departmentKey = "marketing",
  operatorId = "operator_marketing_v1",
  workflowId = "workflow_marketing_content_draft_v1",
  apiBase = DEFAULT_API_BASE,
  resolvedBy = "kevin",
  className,
  activeZone,
  onLaunchWorkflow,
  onSelectMarketing,
}: DashboardProps) {
  const copy = DEPARTMENT_COPY[departmentKey] ?? DEPARTMENT_COPY.marketing;

  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [brief, setBrief] = useState(copy.briefDefault);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedApprovalId, setSelectedApprovalId] = useState<string | null>(null);

  useEffect(() => {
    setBrief(copy.briefDefault);
  }, [copy.briefDefault, departmentKey]);

  const refresh = useCallback(
    async (mode: "initial" | "refresh" = "refresh") => {
      if (mode === "initial") setLoading(true);
      else setRefreshing(true);

      setError(null);

      try {
        const [approvalsRes, runsRes] = await Promise.all([
          fetch(
            buildUrl(apiBase, "/api/business-runtime/approvals", {
              department_key: departmentKey,
            }),
            { cache: "no-store" },
          ),
          fetch(
            buildUrl(apiBase, "/api/business-runtime/runs", {
              department_key: departmentKey,
              limit: 20,
            }),
            { cache: "no-store" },
          ),
        ]);

        if (!approvalsRes.ok) {
          const text = await approvalsRes.text();
          throw new Error(text || "Failed to load approvals");
        }

        if (!runsRes.ok) {
          const text = await runsRes.text();
          throw new Error(text || "Failed to load runs");
        }

        const approvalsJson = (await approvalsRes.json()) as ApiListResponse<ApprovalItem>;
        const runsJson = (await runsRes.json()) as ApiListResponse<WorkflowRun>;

        const nextApprovals = approvalsJson.items ?? [];
        const nextRuns = runsJson.items ?? [];

        setApprovals(nextApprovals);
        setRuns(nextRuns);

        setSelectedRunId((prev) => {
          if (prev && nextRuns.some((run) => run.id === prev)) return prev;
          return nextRuns[0]?.id ?? null;
        });

        setSelectedApprovalId((prev) => {
          if (prev && nextApprovals.some((approval) => approval.id === prev)) return prev;
          return nextApprovals[0]?.id ?? null;
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load dashboard data");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [apiBase, departmentKey],
  );

  useEffect(() => {
    void refresh("initial");
  }, [refresh]);

  const laneCounts = useMemo(() => {
    const queued = runs.filter((r) => r.status === "queued").length;
    const running = runs.filter((r) => r.status === "running").length;
    const waitingApproval = runs.filter((r) => r.status === "waiting_approval").length;
    const failed = runs.filter((r) => r.status === "failed").length;
    const completed = runs.filter((r) => r.status === "completed").length;

    return { queued, running, waitingApproval, failed, completed };
  }, [runs]);

  const pendingApprovals = useMemo(
    () => approvals.filter((item) => item.status === "pending"),
    [approvals],
  );

  const approvalHistory = useMemo(
    () => approvals.filter((item) => item.status !== "pending"),
    [approvals],
  );

  const selectedRun = useMemo(() => {
    if (!runs.length) return null;
    return runs.find((run) => run.id === selectedRunId) ?? runs[0];
  }, [runs, selectedRunId]);

  const selectedApproval = useMemo(() => {
    if (!approvals.length) return null;
    return approvals.find((approval) => approval.id === selectedApprovalId) ?? approvals[0];
  }, [approvals, selectedApprovalId]);

  const latestRun = runs[0] ?? null;
  const latestApproval = approvals[0] ?? null;

  async function handleLaunch() {
    setBusy(true);
    setError(null);

    try {
      const res = await fetch(`${apiBase}/api/business-runtime/runs/launch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow_id: workflowId,
          trigger_kind: "manual",
          context: {
            workspace_id: workspaceId,
            brief,
            department_key: departmentKey,
          },
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Launch failed");
      }

      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Launch failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleResolveApproval(approvalId: string, approve: boolean) {
    setBusy(true);
    setError(null);

    try {
      const res = await fetch(
        `${apiBase}/api/business-runtime/approvals/${approvalId}/resolve`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            approve,
            resolved_by: resolvedBy,
          }),
        },
      );

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Approval resolution failed");
      }

      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approval resolution failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={className ?? "w-full text-slate-900"}>
      <div className="mx-auto w-full max-w-7xl">
        <div className="mb-6 rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm md:p-8">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0">
              <div className="text-sm font-semibold text-slate-500">{copy.eyebrow}</div>
              <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
                {copy.title}
              </h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600 md:text-base">
                {copy.description}
              </p>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Badge>{workspaceId}</Badge>
                <Badge>Department: {departmentKey}</Badge>
                <Badge>Operator: {operatorId}</Badge>
                {activeZone ? <Badge>Zone: {activeZone}</Badge> : null}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {onSelectMarketing && departmentKey === "marketing" ? (
                <button
                  type="button"
                  onClick={onSelectMarketing}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold shadow-sm transition hover:bg-slate-50"
                >
                  {copy.openFloorLabel ?? "Open floor"}
                </button>
              ) : null}

              {onLaunchWorkflow ? (
                <button
                  type="button"
                  onClick={onLaunchWorkflow}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold shadow-sm transition hover:bg-slate-50"
                >
                  Open boardroom inspector
                </button>
              ) : null}

              {refreshing ? (
                <div className="text-xs font-medium text-slate-500">Refreshing…</div>
              ) : null}

              <button
                type="button"
                onClick={() => void refresh()}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={busy || loading}
              >
                Refresh
              </button>
            </div>
          </div>
        </div>

        {error ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="mb-6 grid grid-cols-2 gap-4 xl:grid-cols-5">
          <LaneCard label="Queued" value={laneCounts.queued} />
          <LaneCard label="Running" value={laneCounts.running} />
          <LaneCard label="Waiting approval" value={laneCounts.waitingApproval} />
          <LaneCard label="Failed" value={laneCounts.failed} />
          <LaneCard label="Completed" value={laneCounts.completed} />
        </div>

        <div className="mb-6 grid gap-4 xl:grid-cols-3">
          <SummaryCard
            title="Workspace"
            value={workspaceId}
            subtitle={`Department: ${departmentKey}`}
          />
          <SummaryCard
            title="Latest run"
            value={latestRun?.id ?? "No runs yet"}
            subtitle={
              latestRun
                ? `${prettifyStatus(latestRun.status)} · ${formatTime(latestRun.updated_at)}`
                : "Launch a workflow to begin"
            }
          />
          <SummaryCard
            title="Latest approval"
            value={latestApproval?.id ?? "No approvals yet"}
            subtitle={
              latestApproval
                ? `${prettifyStatus(latestApproval.status)} · ${formatTime(
                    latestApproval.requested_at,
                  )}`
                : "No approval items recorded"
            }
          />
        </div>

        <div className="grid gap-6 2xl:grid-cols-[1.05fr_0.95fr]">
          <div className="space-y-6">
            <Panel>
              <PanelHeader
                eyebrow="Launch workflow"
                title={copy.launchTitle}
                subtitle={copy.launchDescription}
              />

              <div className="space-y-4">
                <div className="grid gap-4 lg:grid-cols-3">
                  <MiniStat label="Operator" value={operatorId} />
                  <MiniStat label="Workflow" value={workflowId} />
                  <MiniStat label="Mode" value="Draft + approval" />
                </div>

                <div>
                  <label
                    htmlFor="department-brief"
                    className="mb-2 block text-sm font-semibold text-slate-700"
                  >
                    {copy.briefLabel}
                  </label>
                  <textarea
                    id="department-brief"
                    value={brief}
                    onChange={(e) => setBrief(e.target.value)}
                    rows={5}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
                    placeholder={copy.briefPlaceholder}
                  />
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={() => void handleLaunch()}
                    disabled={busy || loading || !brief.trim()}
                    className="rounded-2xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {busy ? "Working..." : "Launch workflow"}
                  </button>
                  <div className="text-sm text-slate-500">
                    Launches a draft, attaches connector context, then pauses if approval is
                    required.
                  </div>
                </div>
              </div>
            </Panel>

            <Panel>
              <PanelHeader
                eyebrow="Pending approvals"
                title="Approvals needing a decision"
                subtitle="Only actionable approvals stay here. Once resolved they move into history."
              />

              {loading ? (
                <EmptyState>Loading approvals…</EmptyState>
              ) : pendingApprovals.length === 0 ? (
                <EmptyState>No pending approvals right now.</EmptyState>
              ) : (
                <div className="space-y-4">
                  {pendingApprovals.map((approval) => {
                    const draftPrimary =
                      approval.payload?.draft_caption ??
                      approval.payload?.draft_action ??
                      approval.payload?.draft_finance_action ??
                      approval.payload?.draft_operational_action ??
                      approval.payload?.draft_support_action ??
                      approval.payload?.draft_hr_action;

                    const draftList =
                      approval.payload?.draft_carousel ??
                      approval.payload?.draft_actions ??
                      approval.payload?.action_items;

                    return (
                      <div
                        key={approval.id}
                        className="rounded-3xl border border-slate-200 bg-slate-50 p-5"
                      >
                        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                          <div className="min-w-0">
                            <div className="text-xl font-bold text-slate-900">
                              {approval.title}
                            </div>
                            <div className="mt-1 text-sm text-slate-600">
                              {approval.summary}
                            </div>
                            <div className="mt-2 text-xs text-slate-500">
                              Requested {formatTimeLong(approval.requested_at)} ·{" "}
                              {approval.workflow_run_id}
                            </div>
                          </div>

                          <StatusPill status={approval.status} />
                        </div>

                        <div className="grid gap-4 xl:grid-cols-2">
                          <DetailCard title={copy.approvalDraftTitle}>
                            <div className="whitespace-pre-wrap text-sm text-slate-800">
                              {typeof draftPrimary === "string"
                                ? draftPrimary
                                : "No draft content found."}
                            </div>
                          </DetailCard>

                          <DetailCard title="Structured items">
                            {Array.isArray(draftList) && draftList.length > 0 ? (
                              <div className="flex flex-wrap gap-2">
                                {draftList.map((item, index) => (
                                  <Chip key={`${approval.id}-list-${index}`}>{String(item)}</Chip>
                                ))}
                              </div>
                            ) : (
                              <div className="text-sm text-slate-500">
                                No structured items found.
                              </div>
                            )}
                          </DetailCard>
                        </div>

                        <div className="mt-5 flex flex-wrap items-center gap-3">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => {
                              setSelectedApprovalId(approval.id);
                              void handleResolveApproval(approval.id, true);
                            }}
                            className="rounded-2xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Approve
                          </button>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => {
                              setSelectedApprovalId(approval.id);
                              void handleResolveApproval(approval.id, false);
                            }}
                            className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Reject
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </Panel>

            <Panel>
              <PanelHeader
                eyebrow="Approval history"
                title="Resolved approvals"
                subtitle="Completed approval records stay here as compact history items."
              />

              {loading ? (
                <EmptyState>Loading history…</EmptyState>
              ) : approvalHistory.length === 0 ? (
                <EmptyState>No resolved approvals yet.</EmptyState>
              ) : (
                <div className="space-y-3">
                  {approvalHistory.map((approval) => {
                    const active = selectedApproval?.id === approval.id;

                    return (
                      <button
                        key={approval.id}
                        type="button"
                        onClick={() => setSelectedApprovalId(approval.id)}
                        className={`w-full rounded-2xl border p-4 text-left transition ${
                          active
                            ? "border-blue-300 bg-blue-50"
                            : "border-slate-200 bg-white hover:bg-slate-50"
                        }`}
                      >
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                          <div className="min-w-0">
                            <div className="font-semibold text-slate-900">{approval.title}</div>
                            <div className="mt-1 text-sm text-slate-600">{approval.summary}</div>
                            <div className="mt-2 text-xs text-slate-500">
                              {approval.resolved_at
                                ? `Resolved ${formatTimeLong(approval.resolved_at)}`
                                : `Requested ${formatTimeLong(approval.requested_at)}`}
                            </div>
                          </div>

                          <StatusPill status={approval.status} />
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </Panel>
          </div>

          <div className="space-y-6">
            <Panel>
              <PanelHeader
                eyebrow="Operator contract"
                title={copy.operatorContractTitle}
                subtitle="Core workflow, approval policy, and connected tools."
              />

              <div className="mb-5 grid gap-3 md:grid-cols-2">
                <MiniStat label="Operator ID" value={operatorId} />
                <MiniStat label="Workflow ID" value={workflowId} />
                <MiniStat
                  label="Latest run"
                  value={latestRun?.id ?? "—"}
                  helper={
                    latestRun
                      ? `${prettifyStatus(latestRun.status)} · ${formatTime(latestRun.updated_at)}`
                      : undefined
                  }
                />
                <MiniStat
                  label="Latest approval"
                  value={latestApproval?.id ?? "—"}
                  helper={
                    latestApproval
                      ? `${prettifyStatus(latestApproval.status)} · ${formatTime(
                          latestApproval.requested_at,
                        )}`
                      : undefined
                  }
                />
              </div>

              <div className="grid gap-4 xl:grid-cols-3">
                <InfoBlock title="Workflow steps" lines={copy.workflowSteps} />
                <InfoBlock title="Escalation rules" lines={copy.escalationRules} />
                <InfoBlock title="Connected tools" lines={copy.connectedTools} />
              </div>
            </Panel>

            <Panel>
              <PanelHeader
                eyebrow="Recent runs"
                title="Run history"
                subtitle="Click any run to inspect the exact output it produced."
              />

              {loading ? (
                <EmptyState>Loading runs…</EmptyState>
              ) : runs.length === 0 ? (
                <EmptyState>No runs recorded yet.</EmptyState>
              ) : (
                <div className="space-y-3">
                  {runs.map((run) => {
                    const active = selectedRun?.id === run.id;

                    return (
                      <button
                        key={run.id}
                        type="button"
                        onClick={() => setSelectedRunId(run.id)}
                        className={`w-full rounded-2xl border p-4 text-left transition ${
                          active
                            ? "border-blue-300 bg-blue-50"
                            : "border-slate-200 bg-white hover:bg-slate-50"
                        }`}
                      >
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                          <div className="min-w-0">
                            <div className="font-semibold text-slate-900">{run.workflow_name}</div>
                            <div className="mt-1 text-sm text-slate-600">
                              {run.id} · {run.operator_id} · {prettifyStatus(run.trigger_kind)}
                            </div>
                            <div className="mt-2 text-sm text-slate-600">
                              Execution mode: {prettifyStatus(run.execution_mode)}
                            </div>
                            <div className="mt-1 text-sm text-slate-600">
                              Current step: {getCurrentStepLabel(run)}
                            </div>
                            <div className="mt-1 text-xs text-slate-500">
                              Created {formatTimeLong(run.created_at)}
                              {run.completed_at
                                ? ` · Completed ${formatTimeLong(run.completed_at)}`
                                : ""}
                            </div>
                            {run.failure_reason ? (
                              <div className="mt-2 text-sm font-medium text-red-600">
                                {run.failure_reason}
                              </div>
                            ) : null}
                          </div>

                          <StatusPill status={run.status} />
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </Panel>

            <Panel>
              <PanelHeader
                eyebrow="Selected run output"
                title={selectedRun?.workflow_name ?? "No run selected"}
                subtitle="Full draft payload, connector context, result status, and step history."
              />

              {!selectedRun ? (
                <EmptyState>Select a run to inspect its output.</EmptyState>
              ) : (
                <div className="space-y-5">
                  <div className="grid gap-3 md:grid-cols-2">
                    <MiniStat label="Run ID" value={selectedRun.id} />
                    <MiniStat
                      label="Status"
                      value={prettifyStatus(selectedRun.status)}
                      helper={formatTime(selectedRun.updated_at)}
                    />
                    <MiniStat label="Current step" value={getCurrentStepLabel(selectedRun)} />
                    <MiniStat
                      label="Approval request"
                      value={selectedRun.approval_request_id ?? "—"}
                    />
                  </div>

                  <div className="grid gap-4 xl:grid-cols-2">
                    <DetailCard title="Brief">
                      <div className="whitespace-pre-wrap text-sm text-slate-800">
                        {typeof selectedRun.context?.brief === "string"
                          ? selectedRun.context.brief
                          : "No brief found."}
                      </div>
                    </DetailCard>

                    <DetailCard title={copy.outputDraftTitle}>
                      <div className="whitespace-pre-wrap text-sm text-slate-800">
                        {(() => {
                          const value = extractPrimaryDraftValue(selectedRun);
                          return typeof value === "string" ? value : "No draft content found.";
                        })()}
                      </div>
                    </DetailCard>

                    <DetailCard title="Structured items">
                      {extractCarouselItems(selectedRun).length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {extractCarouselItems(selectedRun).map((item, index) => (
                            <Chip key={`${selectedRun.id}-carousel-${index}`}>{String(item)}</Chip>
                          ))}
                        </div>
                      ) : (
                        <div className="text-sm text-slate-500">No structured items found.</div>
                      )}
                    </DetailCard>

                    <DetailCard title="Connector context">
                      <pre className="overflow-x-auto whitespace-pre-wrap text-sm text-slate-800">
                        {stringifyValue(selectedRun.context?.connector_context)}
                      </pre>
                    </DetailCard>
                  </div>

                  <DetailCard title="Final result">
                    <pre className="overflow-x-auto whitespace-pre-wrap text-sm text-slate-800">
                      {stringifyValue(selectedRun.context?.result)}
                    </pre>
                  </DetailCard>

                  <DetailCard title="Failure / result">
                    <div className="whitespace-pre-wrap text-sm text-slate-700">
                      {selectedRun.failure_reason || extractLatestResult(selectedRun)}
                    </div>
                  </DetailCard>

                  <DetailCard title="Step history">
                    <div className="space-y-3">
                      {selectedRun.step_runs.map((step) => (
                        <div
                          key={step.id}
                          className="rounded-2xl border border-slate-200 bg-white p-4"
                        >
                          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                            <div className="min-w-0">
                              <div className="font-semibold text-slate-900">
                                {prettifyStatus(step.kind)}
                              </div>
                              <div className="mt-1 text-xs text-slate-500">
                                Started {formatTimeLong(step.started_at)} · Completed{" "}
                                {formatTimeLong(step.completed_at)}
                              </div>
                              {step.error ? (
                                <div className="mt-2 text-sm font-medium text-red-600">
                                  {step.error}
                                </div>
                              ) : null}
                            </div>
                            <StatusPill status={step.status} />
                          </div>

                          <div className="mt-3 rounded-xl bg-slate-50 p-3">
                            <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-slate-700">
                              {stringifyValue(step.output)}
                            </pre>
                          </div>
                        </div>
                      ))}
                    </div>
                  </DetailCard>
                </div>
              )}
            </Panel>

            <Panel>
              <PanelHeader
                eyebrow="Selected approval"
                title={selectedApproval?.title ?? "No approval selected"}
                subtitle="Resolved approval record and payload details."
              />

              {!selectedApproval ? (
                <EmptyState>Select an approval item to inspect it.</EmptyState>
              ) : (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <StatusPill status={selectedApproval.status} />
                    <div className="text-sm text-slate-500">
                      Requested {formatTimeLong(selectedApproval.requested_at)}
                    </div>
                    {selectedApproval.resolved_at ? (
                      <div className="text-sm text-slate-500">
                        Resolved {formatTimeLong(selectedApproval.resolved_at)}
                      </div>
                    ) : null}
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <MiniStat label="Approval ID" value={selectedApproval.id} />
                    <MiniStat label="Workflow run ID" value={selectedApproval.workflow_run_id} />
                    <MiniStat label="Resolved by" value={selectedApproval.resolved_by ?? "—"} />
                    <MiniStat
                      label="Resolution note"
                      value={selectedApproval.resolution_note ?? "—"}
                    />
                  </div>

                  <DetailCard title="Approval payload">
                    <pre className="overflow-x-auto whitespace-pre-wrap text-sm text-slate-800">
                      {stringifyValue(selectedApproval.payload)}
                    </pre>
                  </DetailCard>
                </div>
              )}
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
}

function Panel({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
      {children}
    </div>
  );
}

function PanelHeader({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-5">
      <div className="text-sm font-semibold text-slate-500">{eyebrow}</div>
      <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">{title}</h2>
      {subtitle ? <p className="mt-1 text-sm text-slate-600">{subtitle}</p> : null}
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
      {children}
    </span>
  );
}

function StatusPill({ status }: { status?: string | null }) {
  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${getStatusTone(
        status,
      )}`}
    >
      {prettifyStatus(status)}
    </span>
  );
}

function LaneCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 text-4xl font-bold text-slate-900">{value}</div>
    </div>
  );
}

function SummaryCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string;
  subtitle?: string;
}) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</div>
      <div className="mt-2 break-all text-xl font-bold text-slate-900">{value}</div>
      {subtitle ? <div className="mt-2 text-sm text-slate-600">{subtitle}</div> : null}
    </div>
  );
}

function MiniStat({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper?: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-2 break-all text-base font-bold text-slate-900">{value}</div>
      {helper ? <div className="mt-1 text-xs text-slate-600">{helper}</div> : null}
    </div>
  );
}

function DetailCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
      <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </div>
      {children}
    </div>
  );
}

function InfoBlock({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
      <div className="mb-3 text-sm font-semibold text-slate-700">{title}</div>
      <div className="space-y-2 text-sm text-slate-600">
        {lines.map((line) => (
          <div key={line}>{line}</div>
        ))}
      </div>
    </div>
  );
}

function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-8 text-sm text-slate-500">
      {children}
    </div>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
      {children}
    </span>
  );
}