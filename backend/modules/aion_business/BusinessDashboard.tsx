"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

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

type DepartmentCardSummary = {
  key: "marketing" | "sales" | "finance" | "operations" | "support" | "hr";
  label: string;
  seatLabel: string;
  status: string;
  primaryMetricLabel: string;
  primaryMetricValue: string;
  secondaryMetricLabel: string;
  secondaryMetricValue: string;
  tertiaryMetricLabel?: string;
  tertiaryMetricValue?: string;
  activeRuns: number;
  pendingApprovals: number;
  failedRuns: number;
  blockedItems: number;
  dueToday: number;
  openTasks: number;
  note?: string;
};

type OperatorCardSummary = {
  operatorId: string;
  departmentKey: string;
  label: string;
  status: string;
  activeRuns: number;
  waitingApproval: number;
  failedRuns: number;
  latestRunId?: string;
  latestUpdatedAt?: string | null;
  currentStep?: string;
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

type InspectorItem =
  | {
      kind: "department";
      department: DepartmentCardSummary;
    }
  | {
      kind: "operator";
      operator: OperatorCardSummary;
    }
  | {
      kind: "run";
      run: WorkflowRun;
    }
  | {
      kind: "approval";
      approval: ApprovalItem;
    }
  | null;

const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8080";

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

function extractLatestResult(run: WorkflowRun): string {
  const result = run.context?.result;
  if (result && typeof result === "object") {
    const status = (result as Record<string, unknown>).status;
    if (typeof status === "string") return status;
  }
  if (run.failure_reason) return run.failure_reason;
  return run.status;
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

function extractRunHeadline(run: WorkflowRun): string {
  const context = run.context ?? {};
  const result = context.result as Record<string, unknown> | undefined;
  const draft = context.draft as Record<string, unknown> | undefined;

  const options = [
    context.title,
    context.headline,
    context.brief,
    result?.title,
    result?.headline,
    draft?.title,
    draft?.headline,
    run.workflow_name,
  ];

  for (const value of options) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }

  return "Untitled run";
}

function getContextString(
  context: Record<string, unknown> | undefined,
  ...keys: string[]
): string | undefined {
  if (!context) return undefined;

  for (const key of keys) {
    const value = context[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number" && Number.isFinite(value)) return String(value);
  }

  return undefined;
}

function metricFromRun(
  run: WorkflowRun | undefined,
  label: string,
  fallback = "—",
): string {
  if (!run) return fallback;

  const context = run.context ?? {};
  const result =
    context.result && typeof context.result === "object"
      ? (context.result as Record<string, unknown>)
      : undefined;

  return getContextString(result, label) ?? getContextString(context, label) ?? fallback;
}

function extractRunPreview(run: WorkflowRun): string {
  const context = run.context ?? {};
  const result = context.result as Record<string, unknown> | undefined;
  const draft = context.draft as Record<string, unknown> | undefined;

  const options = [
    context.draft_caption,
    context.caption,
    result?.caption,
    result?.summary,
    draft?.caption,
    context.brief,
    run.failure_reason,
  ];

  for (const value of options) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }

  return "No preview available.";
}

function extractDraftCaption(run: WorkflowRun): string {
  const context = run.context ?? {};
  const result = context.result as Record<string, unknown> | undefined;
  const draft = context.draft as Record<string, unknown> | undefined;

  const options = [
    context.draft_caption,
    context.caption,
    result?.caption,
    result?.post_caption,
    draft?.caption,
    draft?.post_caption,
  ];

  for (const value of options) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }

  return "No draft caption found.";
}

function extractCarousel(run: WorkflowRun): string[] {
  const context = run.context ?? {};
  const result = context.result as Record<string, unknown> | undefined;
  const draft = context.draft as Record<string, unknown> | undefined;

  const rawValues = [
    context.draft_carousel,
    context.carousel,
    result?.carousel,
    result?.carousel_items,
    draft?.carousel,
    draft?.carousel_items,
  ];

  const out: string[] = [];

  rawValues.forEach((value) => {
    if (Array.isArray(value)) {
      value.forEach((item) => {
        if (typeof item === "string" && item.trim()) out.push(item.trim());
      });
    }
  });

  return Array.from(new Set(out));
}

function extractApprovalSummary(approval: ApprovalItem): string {
  if (approval.summary?.trim()) return approval.summary.trim();
  return approval.title;
}

function groupOperatorRuns(runs: WorkflowRun[]) {
  const priority: Record<string, number> = {
    running: 6,
    waiting_approval: 5,
    failed: 4,
    queued: 3,
    completed: 2,
    cancelled: 1,
  };

  const map = new Map<
    string,
    {
      operatorId: string;
      runCount: number;
      latestRun?: WorkflowRun;
      status: string;
      running: number;
      waitingApproval: number;
      failed: number;
      completed: number;
      queued: number;
    }
  >();

  runs.forEach((run) => {
    const key = run.operator_id || "unknown_operator";
    const existing = map.get(key);

    if (!existing) {
      map.set(key, {
        operatorId: key,
        runCount: 1,
        latestRun: run,
        status: run.status,
        running: run.status === "running" ? 1 : 0,
        waitingApproval: run.status === "waiting_approval" ? 1 : 0,
        failed: run.status === "failed" ? 1 : 0,
        completed: run.status === "completed" ? 1 : 0,
        queued: run.status === "queued" ? 1 : 0,
      });
      return;
    }

    const latestExisting = new Date(existing.latestRun?.updated_at ?? 0).getTime();
    const nextTime = new Date(run.updated_at).getTime();

    existing.runCount += 1;
    existing.running += run.status === "running" ? 1 : 0;
    existing.waitingApproval += run.status === "waiting_approval" ? 1 : 0;
    existing.failed += run.status === "failed" ? 1 : 0;
    existing.completed += run.status === "completed" ? 1 : 0;
    existing.queued += run.status === "queued" ? 1 : 0;

    if (nextTime > latestExisting) {
      existing.latestRun = run;
    }

    if ((priority[run.status] ?? 0) > (priority[existing.status] ?? 0)) {
      existing.status = run.status;
    }
  });

  return Array.from(map.values()).sort((a, b) => {
    const aTime = new Date(a.latestRun?.updated_at ?? 0).getTime();
    const bTime = new Date(b.latestRun?.updated_at ?? 0).getTime();
    return bTime - aTime;
  });
}

export default function BusinessDashboard({
  workspaceId = "costa-conexion",
  departmentKey,
  operatorId = "operator_marketing_v1",
  workflowId = "workflow_marketing_content_draft_v1",
  apiBase = DEFAULT_API_BASE,
  resolvedBy = "kevin",
  className,
  activeZone,
  onLaunchWorkflow,
  onSelectMarketing,
}: DashboardProps) {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [brief, setBrief] = useState(
    "Draft a Facebook post and simple carousel for spring telecom upgrade offer.",
  );
  const [inspectorItem, setInspectorItem] = useState<InspectorItem>(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);

  const refresh = useCallback(
    async (mode: "initial" | "refresh" = "refresh") => {
      if (mode === "initial") setLoading(true);
      else setRefreshing(true);

      setError(null);

      try {
        const [approvalsRes, runsRes] = await Promise.all([
          fetch(
            buildUrl(apiBase, "/api/business-runtime/approvals", {
              department_key: departmentKey || undefined,
              limit: 100,
            }),
            { cache: "no-store" },
          ),
          fetch(
            buildUrl(apiBase, "/api/business-runtime/runs", {
              department_key: departmentKey || undefined,
              limit: 100,
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

        setApprovals(approvalsJson.items ?? []);
        setRuns(runsJson.items ?? []);
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

  const marketingRuns = useMemo(
    () => runs.filter((run) => run.department_key === "marketing"),
    [runs],
  );
  const salesRuns = useMemo(
    () => runs.filter((run) => run.department_key === "sales"),
    [runs],
  );
  const financeRuns = useMemo(
    () => runs.filter((run) => run.department_key === "finance"),
    [runs],
  );
  const operationsRuns = useMemo(
    () => runs.filter((run) => run.department_key === "operations"),
    [runs],
  );
  const supportRuns = useMemo(
    () => runs.filter((run) => run.department_key === "support"),
    [runs],
  );
  const hrRuns = useMemo(() => runs.filter((run) => run.department_key === "hr"), [runs]);

  const latestRun = runs[0] ?? null;
  const latestApproval = approvals[0] ?? null;

  const departmentCards = useMemo<DepartmentCardSummary[]>(() => {
    const makeCard = (
      key: DepartmentCardSummary["key"],
      label: string,
      departmentRuns: WorkflowRun[],
      config: {
        seatLabel: string;
        primaryMetricLabel: string;
        primaryMetricValue: string;
        secondaryMetricLabel: string;
        secondaryMetricValue: string;
        tertiaryMetricLabel?: string;
        tertiaryMetricValue?: string;
        blockedItems?: number;
        dueToday?: number;
        openTasks?: number;
        note?: string;
      },
    ): DepartmentCardSummary => {
      const pendingApprovalsForDept = approvals.filter(
        (item) => item.department_key === key && item.status === "pending",
      ).length;

      const failedRunsForDept = departmentRuns.filter((run) => run.status === "failed").length;
      const activeRunsForDept = departmentRuns.filter(
        (run) =>
          run.status === "running" ||
          run.status === "queued" ||
          run.status === "waiting_approval",
      ).length;

      const derivedStatus =
        failedRunsForDept > 0
          ? "warning"
          : pendingApprovalsForDept > 0
            ? "waiting_approval"
            : activeRunsForDept > 0
              ? "running"
              : "healthy";

      return {
        key,
        label,
        seatLabel: config.seatLabel,
        status: derivedStatus,
        primaryMetricLabel: config.primaryMetricLabel,
        primaryMetricValue: config.primaryMetricValue,
        secondaryMetricLabel: config.secondaryMetricLabel,
        secondaryMetricValue: config.secondaryMetricValue,
        tertiaryMetricLabel: config.tertiaryMetricLabel,
        tertiaryMetricValue: config.tertiaryMetricValue,
        activeRuns: activeRunsForDept,
        pendingApprovals: pendingApprovalsForDept,
        failedRuns: failedRunsForDept,
        blockedItems: config.blockedItems ?? 0,
        dueToday: config.dueToday ?? 0,
        openTasks: config.openTasks ?? 0,
        note: config.note,
      };
    };

    return [
      makeCard("marketing", "Marketing", marketingRuns, {
        seatLabel: "Growth Desk",
        primaryMetricLabel: "Latest run",
        primaryMetricValue: marketingRuns[0]?.workflow_name ?? "No runs",
        secondaryMetricLabel: "Current step",
        secondaryMetricValue: marketingRuns[0] ? getCurrentStepLabel(marketingRuns[0]) : "—",
        tertiaryMetricLabel: "Latest status",
        tertiaryMetricValue: marketingRuns[0] ? prettifyStatus(marketingRuns[0].status) : "—",
        note: "Content generation, approval flow, and campaign execution.",
      }),
      makeCard("sales", "Sales", salesRuns, {
        seatLabel: "Revenue Desk",
        primaryMetricLabel: "Pipeline",
        primaryMetricValue: metricFromRun(salesRuns[0], "pipeline", "£31.4k"),
        secondaryMetricLabel: "Close rate",
        secondaryMetricValue: metricFromRun(salesRuns[0], "close_rate", "28%"),
        tertiaryMetricLabel: "Stale deals",
        tertiaryMetricValue: metricFromRun(salesRuns[0], "stale_deals", "7"),
        blockedItems: salesRuns.filter((run) => run.status === "failed").length,
        dueToday: 2,
        openTasks: salesRuns.length,
        note: "Pipeline movement, close-rate pressure, and stale-deal recovery.",
      }),
      makeCard("finance", "Finance", financeRuns, {
        seatLabel: "Finance Desk",
        primaryMetricLabel: "Cash on hand",
        primaryMetricValue: metricFromRun(financeRuns[0], "cash_on_hand", "£2.3k"),
        secondaryMetricLabel: "Debtor days",
        secondaryMetricValue: metricFromRun(financeRuns[0], "debtor_days", "60d"),
        tertiaryMetricLabel: "Net cash 30d",
        tertiaryMetricValue: metricFromRun(financeRuns[0], "net_cash_30d", "£236"),
        blockedItems: financeRuns.filter((run) => run.status === "failed").length,
        dueToday: 1,
        openTasks: financeRuns.length,
        note: "Cash visibility, collections pressure, and payment timing.",
      }),
      makeCard("operations", "Operations", operationsRuns, {
        seatLabel: "Delivery Desk",
        primaryMetricLabel: "Backlog",
        primaryMetricValue: metricFromRun(operationsRuns[0], "backlog", "18"),
        secondaryMetricLabel: "Blocked jobs",
        secondaryMetricValue: metricFromRun(operationsRuns[0], "blocked_jobs", "3"),
        tertiaryMetricLabel: "Turnaround",
        tertiaryMetricValue: metricFromRun(operationsRuns[0], "turnaround", "2.4d"),
        blockedItems: operationsRuns.filter((run) => run.status === "failed").length + 3,
        dueToday: 4,
        openTasks: operationsRuns.length,
        note: "Delivery pressure, bottlenecks, and fulfilment recovery.",
      }),
      makeCard("support", "Support", supportRuns, {
        seatLabel: "Client Desk",
        primaryMetricLabel: "Open tickets",
        primaryMetricValue: metricFromRun(supportRuns[0], "open_tickets", "18"),
        secondaryMetricLabel: "SLA",
        secondaryMetricValue: metricFromRun(supportRuns[0], "sla", "96.4%"),
        tertiaryMetricLabel: "Escalations",
        tertiaryMetricValue: metricFromRun(supportRuns[0], "escalations", "2"),
        blockedItems: supportRuns.filter((run) => run.status === "failed").length,
        dueToday: 1,
        openTasks: supportRuns.length,
        note: "Ticket flow, escalations, and service level coverage.",
      }),
      makeCard("hr", "HR", hrRuns, {
        seatLabel: "People Desk",
        primaryMetricLabel: "Open actions",
        primaryMetricValue: metricFromRun(hrRuns[0], "open_actions", "12"),
        secondaryMetricLabel: "Avg response",
        secondaryMetricValue: metricFromRun(hrRuns[0], "avg_response", "1.4d"),
        tertiaryMetricLabel: "Compliance",
        tertiaryMetricValue: metricFromRun(hrRuns[0], "compliance", "98%"),
        blockedItems: hrRuns.filter((run) => run.status === "failed").length,
        dueToday: 1,
        openTasks: hrRuns.length,
        note: "Admin handling, people response, and compliance visibility.",
      }),
    ];
  }, [approvals, financeRuns, hrRuns, marketingRuns, operationsRuns, salesRuns, supportRuns]);

  const operatorCards = useMemo<OperatorCardSummary[]>(() => {
    const byOperator = new Map<string, WorkflowRun[]>();

    runs.forEach((run) => {
      const key = run.operator_id || "unknown_operator";
      const existing = byOperator.get(key) ?? [];
      existing.push(run);
      byOperator.set(key, existing);
    });

    return [...byOperator.entries()].map(([operatorKey, operatorRuns]) => {
      const sorted = [...operatorRuns].sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      );

      const latest = sorted[0];
      const activeRuns = operatorRuns.filter(
        (run) =>
          run.status === "running" ||
          run.status === "queued" ||
          run.status === "waiting_approval",
      ).length;

      const waitingApproval = operatorRuns.filter(
        (run) => run.status === "waiting_approval",
      ).length;

      const failedRuns = operatorRuns.filter((run) => run.status === "failed").length;

      return {
        operatorId: operatorKey,
        departmentKey: latest?.department_key ?? "unknown",
        label: operatorKey.replace(/_/g, " "),
        status:
          failedRuns > 0
            ? "failed"
            : waitingApproval > 0
              ? "waiting_approval"
              : activeRuns > 0
                ? "running"
                : latest?.status ?? "idle",
        activeRuns,
        waitingApproval,
        failedRuns,
        latestRunId: latest?.id,
        latestUpdatedAt: latest?.updated_at,
        currentStep: latest ? getCurrentStepLabel(latest) : "—",
      };
    });
  }, [runs]);

  const operatorSummaries = useMemo(() => groupOperatorRuns(runs), [runs]);

  const failedOrBlockedRuns = useMemo(() => {
    return runs.filter(
      (run) =>
        run.status === "failed" ||
        run.status === "waiting_approval" ||
        !!run.failure_reason,
    );
  }, [runs]);

  const marketingCardStats = useMemo(() => {
    return {
      totalRuns: marketingRuns.length,
      awaitingApproval: pendingApprovals.filter((a) => a.department_key === "marketing").length,
      failed: marketingRuns.filter((r) => r.status === "failed").length,
      running: marketingRuns.filter((r) => r.status === "running").length,
      latestHeadline: latestRun ? extractRunHeadline(latestRun) : "No runs yet",
    };
  }, [marketingRuns, pendingApprovals, latestRun]);

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
      setInspectorOpen(false);
      setInspectorItem(null);
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
              <div className="text-sm font-semibold text-slate-500">
                {departmentKey
                  ? `${departmentKey.charAt(0).toUpperCase()}${departmentKey.slice(1)} Operations`
                  : "Business Operations"}
              </div>
              <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
                {departmentKey
                  ? `${departmentKey.charAt(0).toUpperCase()}${departmentKey.slice(1)} Dashboard`
                  : "Business Operations Dashboard"}
              </h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600 md:text-base">
                Launch draft workflows, review approvals, inspect operators, and track failed
                or blocked work from one dashboard.
              </p>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Badge>{workspaceId}</Badge>
                <Badge>Department: {departmentKey ?? "All"}</Badge>
                <Badge>Operator: {operatorId}</Badge>
                {activeZone ? <Badge>Zone: {activeZone}</Badge> : null}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {onSelectMarketing ? (
                <button
                  type="button"
                  onClick={onSelectMarketing}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold shadow-sm transition hover:bg-slate-50"
                >
                  Open marketing floor
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

        <div className="mb-6">
          <div className="mb-3 text-sm font-semibold text-slate-500">Department status cards</div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {departmentCards.map((card) => (
              <button
                key={card.key}
                type="button"
                onClick={() => {
                  setInspectorItem({ kind: "department", department: card });
                  setInspectorOpen(true);
                }}
                className="rounded-[24px] border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:bg-slate-50"
              >
                <div className="mb-4 flex items-start justify-between gap-3">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {card.label}
                    </div>
                    <div className="mt-1 text-lg font-bold text-slate-900">{card.seatLabel}</div>
                  </div>
                  <StatusPill status={card.status} />
                </div>

                <div className="grid gap-3">
                  <MiniStat label={card.primaryMetricLabel} value={card.primaryMetricValue} />
                  <MiniStat label={card.secondaryMetricLabel} value={card.secondaryMetricValue} />
                  {card.tertiaryMetricLabel && card.tertiaryMetricValue ? (
                    <MiniStat
                      label={card.tertiaryMetricLabel}
                      value={card.tertiaryMetricValue}
                    />
                  ) : null}
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <Badge>{card.activeRuns} active runs</Badge>
                  <Badge>{card.pendingApprovals} approvals</Badge>
                  <Badge>{card.failedRuns} failed</Badge>
                  <Badge>{card.blockedItems} blocked/at risk</Badge>
                </div>

                {card.note ? <div className="mt-4 text-sm text-slate-600">{card.note}</div> : null}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-6 grid gap-6 xl:grid-cols-[1fr_1fr]">
          <Panel>
            <PanelHeader
              eyebrow="Operator status cards"
              title="Live operators"
              subtitle="Cross-department operator view using runtime activity."
            />

            {operatorCards.length === 0 ? (
              <EmptyState>No operator runtime data yet.</EmptyState>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {operatorCards.map((operator) => (
                  <button
                    key={operator.operatorId}
                    type="button"
                    onClick={() => {
                      setInspectorItem({ kind: "operator", operator });
                      setInspectorOpen(true);
                    }}
                    className="rounded-3xl border border-slate-200 bg-slate-50 p-5 text-left transition hover:bg-white"
                  >
                    <div className="mb-3 flex items-start justify-between gap-3">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {operator.departmentKey}
                        </div>
                        <div className="mt-1 text-base font-bold text-slate-900">
                          {operator.label}
                        </div>
                      </div>
                      <StatusPill status={operator.status} />
                    </div>

                    <div className="grid gap-3">
                      <MiniStat label="Active runs" value={String(operator.activeRuns)} />
                      <MiniStat
                        label="Waiting approval"
                        value={String(operator.waitingApproval)}
                      />
                      <MiniStat label="Failed runs" value={String(operator.failedRuns)} />
                    </div>

                    <div className="mt-3 text-xs text-slate-500">
                      Latest run: {operator.latestRunId ?? "—"} · {operator.currentStep ?? "—"}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Panel>

          <Panel>
            <PanelHeader
              eyebrow="Alerts"
              title="Failed or blocked runs"
              subtitle="Priority issues that need review or intervention."
            />

            {failedOrBlockedRuns.length === 0 ? (
              <EmptyState>No failed or blocked runs right now.</EmptyState>
            ) : (
              <div className="space-y-3">
                {failedOrBlockedRuns.map((run) => (
                  <button
                    key={run.id}
                    type="button"
                    onClick={() => {
                      setInspectorItem({ kind: "run", run });
                      setInspectorOpen(true);
                    }}
                    className="w-full rounded-2xl border border-slate-200 bg-slate-50 p-4 text-left transition hover:bg-white"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-semibold text-slate-900">{run.workflow_name}</div>
                        <div className="mt-1 text-sm text-slate-600">
                          {run.department_key} · {run.operator_id}
                        </div>
                        <div className="mt-1 text-xs text-slate-500">
                          {run.id} · {formatTimeLong(run.updated_at)}
                        </div>
                        <div className="mt-2 text-sm text-slate-700">
                          {run.failure_reason || extractLatestResult(run)}
                        </div>
                      </div>
                      <StatusPill status={run.status} />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Panel>
        </div>

        <div className="mb-6 grid gap-4 xl:grid-cols-3">
          <MarketingCard
            totalRuns={marketingCardStats.totalRuns}
            awaitingApproval={marketingCardStats.awaitingApproval}
            failed={marketingCardStats.failed}
            running={marketingCardStats.running}
            latestHeadline={marketingCardStats.latestHeadline}
            onOpenMarketing={onSelectMarketing}
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

        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-6">
            <Panel>
              <PanelHeader
                eyebrow="Launch workflow"
                title={
                  departmentKey
                    ? `Create a new ${departmentKey} workflow run`
                    : "Create a new workflow run"
                }
                subtitle="This launches the operator in draft-and-approval mode."
              />
              <div className="space-y-4">
                <div className="grid gap-4 lg:grid-cols-3">
                  <MiniStat label="Operator" value={operatorId} />
                  <MiniStat label="Workflow" value={workflowId} />
                  <MiniStat label="Mode" value="Draft + approval" />
                </div>

                <div>
                  <label
                    htmlFor="marketing-brief"
                    className="mb-2 block text-sm font-semibold text-slate-700"
                  >
                    Content brief
                  </label>
                  <textarea
                    id="marketing-brief"
                    value={brief}
                    onChange={(e) => setBrief(e.target.value)}
                    rows={5}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
                    placeholder="Describe the marketing draft you want the operator to create."
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
                eyebrow="Operator cards"
                title="Trained operators"
                subtitle="Status, load, and latest activity by operator."
              />

              {loading ? (
                <EmptyState>Loading operators…</EmptyState>
              ) : operatorSummaries.length === 0 ? (
                <EmptyState>No operators have run yet.</EmptyState>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {operatorSummaries.map((operator) => (
                    <button
                      key={operator.operatorId}
                      type="button"
                      onClick={() => {
                        if (operator.latestRun) {
                          setInspectorItem({ kind: "run", run: operator.latestRun });
                          setInspectorOpen(true);
                        }
                      }}
                      className="rounded-[24px] border border-slate-200 bg-slate-50 p-5 text-left transition hover:bg-slate-100"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-lg font-bold text-slate-900">
                            {operator.operatorId}
                          </div>
                          <div className="mt-1 text-sm text-slate-600">
                            Latest: {operator.latestRun?.workflow_name ?? "—"}
                          </div>
                        </div>
                        <StatusPill status={operator.status} />
                      </div>

                      <div className="mt-4 grid grid-cols-2 gap-3">
                        <MiniStat label="Runs" value={String(operator.runCount)} />
                        <MiniStat label="Running" value={String(operator.running)} />
                        <MiniStat label="Awaiting" value={String(operator.waitingApproval)} />
                        <MiniStat label="Failed" value={String(operator.failed)} />
                      </div>

                      <div className="mt-4 text-xs text-slate-500">
                        Last update {formatTimeLong(operator.latestRun?.updated_at)}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </Panel>

            <Panel>
              <PanelHeader
                eyebrow="Failed or blocked runs"
                title="Needs attention"
                subtitle="Failures and approval-blocked runs surfaced together."
              />

              {loading ? (
                <EmptyState>Loading run exceptions…</EmptyState>
              ) : failedOrBlockedRuns.length === 0 ? (
                <EmptyState>No failed or blocked runs right now.</EmptyState>
              ) : (
                <div className="space-y-3">
                  {failedOrBlockedRuns.map((run) => (
                    <button
                      key={run.id}
                      type="button"
                      onClick={() => {
                        setInspectorItem({ kind: "run", run });
                        setInspectorOpen(true);
                      }}
                      className="w-full rounded-2xl border border-slate-200 bg-slate-50 p-4 text-left transition hover:bg-slate-100"
                    >
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="min-w-0">
                          <div className="font-semibold text-slate-900">
                            {extractRunHeadline(run)}
                          </div>
                          <div className="mt-1 text-sm text-slate-600">
                            {run.workflow_name} · {run.operator_id}
                          </div>
                          <div className="mt-2 text-sm text-slate-600">
                            {extractRunPreview(run)}
                          </div>
                          <div className="mt-2 text-xs text-slate-500">
                            {getCurrentStepLabel(run)} · {formatTimeLong(run.updated_at)}
                          </div>
                        </div>

                        <StatusPill status={run.status} />
                      </div>
                    </button>
                  ))}
                </div>
              )}
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
                  {pendingApprovals.map((approval) => (
                    <div
                      key={approval.id}
                      className="rounded-3xl border border-slate-200 bg-slate-50 p-5"
                    >
                      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="min-w-0">
                          <div className="text-xl font-bold text-slate-900">{approval.title}</div>
                          <div className="mt-1 text-sm text-slate-600">{approval.summary}</div>
                          <div className="mt-2 text-xs text-slate-500">
                            Requested {formatTimeLong(approval.requested_at)} ·{" "}
                            {approval.workflow_run_id}
                          </div>
                        </div>

                        <StatusPill status={approval.status} />
                      </div>

                      <div className="mt-5 flex flex-wrap items-center gap-3">
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void handleResolveApproval(approval.id, true)}
                          className="rounded-2xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void handleResolveApproval(approval.id, false)}
                          className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          Reject
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setInspectorItem({ kind: "approval", approval });
                            setInspectorOpen(true);
                          }}
                          className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                        >
                          Inspect
                        </button>
                      </div>
                    </div>
                  ))}
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
                  {approvalHistory.map((approval) => (
                    <button
                      key={approval.id}
                      type="button"
                      onClick={() => {
                        setInspectorItem({ kind: "approval", approval });
                        setInspectorOpen(true);
                      }}
                      className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left transition hover:bg-slate-50"
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
                  ))}
                </div>
              )}
            </Panel>
          </div>

          <div className="space-y-6">
            <Panel>
              <PanelHeader
                eyebrow="Operator contract"
                title={departmentKey ? `${departmentKey} operator` : "Business operator"}
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
                <InfoBlock
                  title="Workflow steps"
                  lines={[
                    "Create brief",
                    "Draft caption",
                    "Draft carousel",
                    "Attach connector context",
                    "Pause for approval",
                    "Complete run",
                  ]}
                />
                <InfoBlock
                  title="Escalation rules"
                  lines={[
                    "Public publish requires approval",
                    "Connector misuse escalates to operator owner",
                    "Failed run retried only under bounded policy",
                    "Ambiguous output stays draft-only",
                  ]}
                />
                <InfoBlock
                  title="Connected tools"
                  lines={[
                    "meta_facebook",
                    "approval queue",
                    "workflow runtime",
                    "operator_marketing_v1",
                  ]}
                />
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
                  {runs.map((run) => (
                    <button
                      key={run.id}
                      type="button"
                      onClick={() => {
                        setInspectorItem({ kind: "run", run });
                        setInspectorOpen(true);
                      }}
                      className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left transition hover:bg-slate-50"
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
                  ))}
                </div>
              )}
            </Panel>
          </div>
        </div>
      </div>

      <SharedInspectorDrawer
        open={inspectorOpen}
        item={inspectorItem}
        onClose={() => {
          setInspectorOpen(false);
          setInspectorItem(null);
        }}
      />
    </div>
  );
}

function Panel({ children }: { children: ReactNode }) {
  return <div className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">{children}</div>;
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

function Badge({ children }: { children: ReactNode }) {
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
  children: ReactNode;
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

function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-8 text-sm text-slate-500">
      {children}
    </div>
  );
}

function Chip({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
      {children}
    </span>
  );
}

function MarketingCard({
  totalRuns,
  awaitingApproval,
  failed,
  running,
  latestHeadline,
  onOpenMarketing,
}: {
  totalRuns: number;
  awaitingApproval: number;
  failed: number;
  running: number;
  latestHeadline: string;
  onOpenMarketing?: () => void;
}) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Marketing card
          </div>
          <div className="mt-2 text-xl font-bold text-slate-900">Marketing</div>
          <div className="mt-1 text-sm text-slate-600 line-clamp-2">{latestHeadline}</div>
        </div>
        <div className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
          Active
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <MiniStat label="Runs" value={String(totalRuns)} />
        <MiniStat label="Running" value={String(running)} />
        <MiniStat label="Awaiting" value={String(awaitingApproval)} />
        <MiniStat label="Failed" value={String(failed)} />
      </div>

      {onOpenMarketing ? (
        <button
          type="button"
          onClick={onOpenMarketing}
          className="mt-4 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          Open marketing stream
        </button>
      ) : null}
    </div>
  );
}

function SharedInspectorDrawer({
  open,
  item,
  onClose,
}: {
  open: boolean;
  item: InspectorItem;
  onClose: () => void;
}) {
  if (!open) return null;

  const title =
    item?.kind === "department"
      ? item.department.label
      : item?.kind === "operator"
        ? item.operator.label
        : item?.kind === "run"
          ? extractRunHeadline(item.run)
          : item?.kind === "approval"
            ? item.approval.title
            : "Nothing selected";

  const subtitle =
    item?.kind === "department"
      ? item.department.seatLabel
      : item?.kind === "operator"
        ? `${item.operator.operatorId} · ${item.operator.departmentKey}`
        : item?.kind === "run"
          ? `${item.run.id} · ${prettifyStatus(item.run.status)} · ${formatTimeLong(item.run.updated_at)}`
          : item?.kind === "approval"
            ? `${item.approval.id} · ${prettifyStatus(item.approval.status)} · ${formatTimeLong(item.approval.requested_at)}`
            : undefined;

  return (
    <div className="fixed inset-0 z-[70] flex">
      <div className="flex-1 bg-slate-950/35" onClick={onClose} />
      <div className="h-full w-full max-w-2xl border-l border-slate-200 bg-white shadow-2xl">
        <div className="flex h-full flex-col">
          <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
            <div className="min-w-0">
              <div className="text-sm font-semibold text-slate-500">Shared inspector</div>
              <div className="mt-1 text-2xl font-bold text-slate-900">{title}</div>
              {subtitle ? <div className="mt-1 text-sm text-slate-600">{subtitle}</div> : null}
            </div>

            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              Close
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
            {!item ? (
              <EmptyState>Select a run or approval to inspect it.</EmptyState>
            ) : item.kind === "department" ? (
              <div className="space-y-4">
                <MiniStat label="Department" value={item.department.label} />
                <MiniStat label="Seat" value={item.department.seatLabel} />
                <MiniStat label="Status" value={prettifyStatus(item.department.status)} />
                <MiniStat
                  label={item.department.primaryMetricLabel}
                  value={item.department.primaryMetricValue}
                />
                <MiniStat
                  label={item.department.secondaryMetricLabel}
                  value={item.department.secondaryMetricValue}
                />
                {item.department.tertiaryMetricLabel && item.department.tertiaryMetricValue ? (
                  <MiniStat
                    label={item.department.tertiaryMetricLabel}
                    value={item.department.tertiaryMetricValue}
                  />
                ) : null}
                <DetailCard title="Operational state">
                  <div className="space-y-2 text-sm text-slate-700">
                    <div>Active runs: {item.department.activeRuns}</div>
                    <div>Pending approvals: {item.department.pendingApprovals}</div>
                    <div>Failed runs: {item.department.failedRuns}</div>
                    <div>Blocked / at-risk: {item.department.blockedItems}</div>
                    <div>Due today: {item.department.dueToday}</div>
                    <div>Open tasks: {item.department.openTasks}</div>
                  </div>
                </DetailCard>
                {item.department.note ? (
                  <DetailCard title="Summary">
                    <div className="text-sm text-slate-700">{item.department.note}</div>
                  </DetailCard>
                ) : null}
              </div>
            ) : item.kind === "operator" ? (
              <div className="space-y-4">
                <MiniStat label="Operator" value={item.operator.operatorId} />
                <MiniStat label="Department" value={item.operator.departmentKey} />
                <MiniStat label="Status" value={prettifyStatus(item.operator.status)} />
                <MiniStat label="Active runs" value={String(item.operator.activeRuns)} />
                <MiniStat label="Waiting approval" value={String(item.operator.waitingApproval)} />
                <MiniStat label="Failed runs" value={String(item.operator.failedRuns)} />
                <MiniStat label="Latest run" value={item.operator.latestRunId ?? "—"} />
                <MiniStat label="Current step" value={item.operator.currentStep ?? "—"} />
                <MiniStat label="Last update" value={formatTimeLong(item.operator.latestUpdatedAt)} />
              </div>
            ) : item.kind === "run" ? (
              <div className="space-y-5">
                <div className="grid gap-3 md:grid-cols-2">
                  <MiniStat label="Run ID" value={item.run.id} />
                  <MiniStat
                    label="Status"
                    value={prettifyStatus(item.run.status)}
                    helper={formatTime(item.run.updated_at)}
                  />
                  <MiniStat label="Department" value={item.run.department_key} />
                  <MiniStat label="Operator" value={item.run.operator_id} />
                  <MiniStat label="Current step" value={getCurrentStepLabel(item.run)} />
                  <MiniStat label="Approval request" value={item.run.approval_request_id ?? "—"} />
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <DetailCard title="Brief">
                    <div className="whitespace-pre-wrap text-sm text-slate-800">
                      {typeof item.run.context?.brief === "string"
                        ? item.run.context.brief
                        : "No brief found."}
                    </div>
                  </DetailCard>

                  <DetailCard title="Draft caption">
                    <div className="whitespace-pre-wrap text-sm text-slate-800">
                      {extractDraftCaption(item.run)}
                    </div>
                  </DetailCard>

                  <DetailCard title="Carousel">
                    {extractCarousel(item.run).length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {extractCarousel(item.run).map((carouselItem, index) => (
                          <Chip key={`${item.run.id}-carousel-${index}`}>{carouselItem}</Chip>
                        ))}
                      </div>
                    ) : (
                      <div className="text-sm text-slate-500">No carousel items found.</div>
                    )}
                  </DetailCard>

                  <DetailCard title="Connector context">
                    <pre className="overflow-x-auto whitespace-pre-wrap text-sm text-slate-800">
                      {stringifyValue(item.run.context?.connector_context)}
                    </pre>
                  </DetailCard>
                </div>

                <DetailCard title="Failure / result">
                  <div className="whitespace-pre-wrap text-sm text-slate-700">
                    {item.run.failure_reason || extractLatestResult(item.run)}
                  </div>
                </DetailCard>

                <DetailCard title="Final result">
                  <pre className="overflow-x-auto whitespace-pre-wrap text-sm text-slate-800">
                    {stringifyValue(item.run.context?.result)}
                  </pre>
                </DetailCard>

                <DetailCard title="Step history">
                  <div className="space-y-3">
                    {item.run.step_runs.map((step) => (
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
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusPill status={item.approval.status} />
                  <div className="text-sm text-slate-500">
                    Requested {formatTimeLong(item.approval.requested_at)}
                  </div>
                  {item.approval.resolved_at ? (
                    <div className="text-sm text-slate-500">
                      Resolved {formatTimeLong(item.approval.resolved_at)}
                    </div>
                  ) : null}
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <MiniStat label="Approval ID" value={item.approval.id} />
                  <MiniStat label="Workflow run ID" value={item.approval.workflow_run_id} />
                  <MiniStat label="Resolved by" value={item.approval.resolved_by ?? "—"} />
                  <MiniStat label="Resolution note" value={item.approval.resolution_note ?? "—"} />
                </div>

                <DetailCard title="Summary">
                  <div className="text-sm text-slate-800">
                    {extractApprovalSummary(item.approval)}
                  </div>
                </DetailCard>

                <DetailCard title="Approval payload">
                  <pre className="overflow-x-auto whitespace-pre-wrap text-sm text-slate-800">
                    {stringifyValue(item.approval.payload)}
                  </pre>
                </DetailCard>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}