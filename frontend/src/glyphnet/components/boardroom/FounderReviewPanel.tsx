"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

type ReviewGroupPreview = {
  id: string;
  owned_by_role?: string;
  objective?: string;
  status?: string;
  escalation_reason?: string;
  escalation_target?: string;
  updated_at?: string;
};

type ReviewGroup = {
  count: number;
  task_ids: string[];
  preview: ReviewGroupPreview[];
};

type GroupCollection = {
  count?: number;
  groups?: Record<string, ReviewGroup>;
};

type EscalationSnapshot = {
  count?: number;
  task_ids?: string[];
  tasks_preview?: ReviewGroupPreview[];
};

type ReportHighlight = {
  key?: string;
  value?: unknown;
  count?: number;
  fields?: string[];
};

type ReportPayload = {
  report?: {
    summary?: string;
    highlights?: ReportHighlight[];
  };
};

type ReviewQueueSnapshot = {
  workflow_id?: string;
  workflow_run_id?: string;
  status?: string;
  escalation_snapshot?: EscalationSnapshot;
  target_groups?: GroupCollection;
  role_groups?: GroupCollection;
  produce_report?: ReportPayload;
  draft_content?: {
    title?: string;
    draft?: string;
  };
};

type WorkflowOutputs = {
  escalation_snapshot?: EscalationSnapshot;
  target_groups?: GroupCollection;
  role_groups?: GroupCollection;
  review_queue_snapshot?: ReviewQueueSnapshot;
  produce_report?: ReportPayload;
  draft_content?: {
    title?: string;
    draft?: string;
  };
};

type WorkflowResult = {
  id: string;
  workflow_id: string;
  status: string;
  completed_at?: string | null;
  updated_at?: string | null;
  outputs?: WorkflowOutputs;
};

type FounderReviewConfig = {
  workspace_id: string;
  role_id: string;
  enabled: boolean;
  cadence: string;
  days_back: number;
  include_draft: boolean;
  send_email?: boolean;
  send_to_emails?: string[];
  from_email?: string | null;
  last_run_at?: string | null;
  metadata?: Record<string, unknown>;
};

type FounderReviewRunResponse = {
  config: FounderReviewConfig;
  workflow_result: WorkflowResult;
};

type ReviewQueueRunResponse = WorkflowResult;

type AuditEvent = {
  id: string;
  created_at: string;
  summary: string;
  workflow_id?: string | null;
  payload?: Record<string, unknown>;
  tags?: string[];
};

type Props = {
  workspaceId?: string;
  roleId?: string;
  businessType?: string;
};

async function readJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const res = await fetch(input, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function readOptionalJson<T>(input: RequestInfo, init?: RequestInit): Promise<T | null> {
  const res = await fetch(input, init);
  if (res.status === 404) return null;
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

function prettyDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function formatValue(value: unknown): string {
  if (value == null) return "—";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function SectionCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div
      style={{
        borderRadius: 14,
        border: "1px solid rgba(226,232,240,1)",
        background: "rgba(255,255,255,0.92)",
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div>
        <div style={{ fontSize: 12, color: "#64748b", fontWeight: 700 }}>{title}</div>
        {subtitle ? (
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 2 }}>{subtitle}</div>
        ) : null}
      </div>
      {children}
    </div>
  );
}

function StatTile({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div
      style={{
        borderRadius: 10,
        background: "#f8fafc",
        padding: "10px 12px",
        border: "1px solid rgba(226,232,240,1)",
      }}
    >
      <div style={{ fontSize: 11, color: "#64748b" }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 800, color: "#111827", marginTop: 4 }}>
        {value}
      </div>
    </div>
  );
}

export default function FounderReviewPanel({
  workspaceId = "test-workspace",
  roleId = "ceo-core",
  businessType = "service_business",
}: Props) {
  const [reviewQueueRun, setReviewQueueRun] = useState<ReviewQueueRunResponse | null>(null);
  const [founderReviewRun, setFounderReviewRun] = useState<FounderReviewRunResponse | null>(null);
  const [founderConfig, setFounderConfig] = useState<FounderReviewConfig | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningQueue, setRunningQueue] = useState(false);
  const [runningFounder, setRunningFounder] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAuditEvents = useCallback(async () => {
    const data = await readJson<AuditEvent[]>(
      `/api/aion/business/audit/${workspaceId}/events`,
    );
    setEvents(data);
  }, [workspaceId]);

  const loadFounderConfig = useCallback(async () => {
    const data = await readOptionalJson<FounderReviewConfig>(
      `/api/aion/business/founder-review/${workspaceId}/config`,
    );
    setFounderConfig(data);
  }, [workspaceId]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([
        loadAuditEvents(),
        loadFounderConfig(),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load founder review panel");
    } finally {
      setLoading(false);
    }
  }, [loadAuditEvents, loadFounderConfig]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const runReviewQueue = async () => {
    setRunningQueue(true);
    setError(null);
    try {
      const data = await readJson<ReviewQueueRunResponse>(
        `/api/aion/business/workflows/review-queue/run`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            workspace_id: workspaceId,
            role_id: roleId,
            role_type: "CEO",
            business_type: businessType,
            model_policy_ref: "openai_for_copy",
            days_back: 30,
            include_draft: false,
          }),
        },
      );
      setReviewQueueRun(data);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review queue run failed");
    } finally {
      setRunningQueue(false);
    }
  };

  const runFounderReview = async () => {
    setRunningFounder(true);
    setError(null);
    try {
      const data = await readJson<FounderReviewRunResponse>(
        `/api/aion/business/founder-review/run`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            workspace_id: workspaceId,
            role_id: roleId,
            days_back: 30,
            include_draft: false,
            persist_config: true,
          }),
        },
      );
      setFounderReviewRun(data);
      setFounderConfig(data.config);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Founder review run failed");
    } finally {
      setRunningFounder(false);
    }
  };

  const latestReviewQueueSnapshot = useMemo<ReviewQueueSnapshot | null>(() => {
    if (founderReviewRun?.workflow_result?.outputs?.review_queue_snapshot) {
      return founderReviewRun.workflow_result.outputs.review_queue_snapshot;
    }

    if (reviewQueueRun) {
      return {
        workflow_id: reviewQueueRun.workflow_id,
        workflow_run_id: reviewQueueRun.id,
        status: reviewQueueRun.status,
        escalation_snapshot: reviewQueueRun.outputs?.escalation_snapshot,
        target_groups: reviewQueueRun.outputs?.target_groups,
        role_groups: reviewQueueRun.outputs?.role_groups,
        produce_report: reviewQueueRun.outputs?.produce_report,
        draft_content: reviewQueueRun.outputs?.draft_content,
      };
    }

    return null;
  }, [founderReviewRun, reviewQueueRun]);

  const latestQueueGroups = useMemo<Record<string, ReviewGroup>>(() => {
    return latestReviewQueueSnapshot?.target_groups?.groups ?? {};
  }, [latestReviewQueueSnapshot]);

  const latestRoleGroups = useMemo<Record<string, ReviewGroup>>(() => {
    return latestReviewQueueSnapshot?.role_groups?.groups ?? {};
  }, [latestReviewQueueSnapshot]);

  const latestEscalationSnapshot = useMemo<EscalationSnapshot | null>(() => {
    return latestReviewQueueSnapshot?.escalation_snapshot ?? null;
  }, [latestReviewQueueSnapshot]);

  const founderSummary = useMemo(() => {
    return (
      founderReviewRun?.workflow_result?.outputs?.produce_report?.report?.summary ??
      "No founder review run yet."
    );
  }, [founderReviewRun]);

  const founderHighlights = useMemo<ReportHighlight[]>(() => {
    return founderReviewRun?.workflow_result?.outputs?.produce_report?.report?.highlights ?? [];
  }, [founderReviewRun]);

  const latestEmailEvent = useMemo(() => {
    return events.find((event) => event.tags?.includes("email_sent"));
  }, [events]);

  const latestEmailFailureEvent = useMemo(() => {
    return events.find((event) => event.tags?.includes("email_failed"));
  }, [events]);

  const latestTriggerEvent = useMemo(() => {
    return events.find((event) => event.tags?.includes("weekly_founder_review"));
  }, [events]);

  const reviewQueueTaskCount = latestEscalationSnapshot?.count ?? 0;
  const targetGroupCount = Object.keys(latestQueueGroups).length;
  const roleGroupCount = Object.keys(latestRoleGroups).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <SectionCard
        title="Founder Review"
        subtitle={`Workspace: ${workspaceId}`}
      >
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={runReviewQueue}
            disabled={runningQueue || runningFounder || loading}
            style={{
              borderRadius: 10,
              border: "1px solid rgba(148,163,184,0.28)",
              background: "#ffffff",
              color: "#0f172a",
              padding: "8px 10px",
              fontSize: 12,
              fontWeight: 700,
              cursor: runningQueue || runningFounder || loading ? "default" : "pointer",
              opacity: runningQueue || runningFounder || loading ? 0.6 : 1,
            }}
          >
            {runningQueue ? "Running queue..." : "Run Review Queue"}
          </button>

          <button
            type="button"
            onClick={runFounderReview}
            disabled={runningFounder || runningQueue || loading}
            style={{
              borderRadius: 10,
              border: "1px solid rgba(26,138,255,0.35)",
              background: "rgba(26,138,255,0.10)",
              color: "#0f4ea8",
              padding: "8px 10px",
              fontSize: 12,
              fontWeight: 700,
              cursor: runningFounder || runningQueue || loading ? "default" : "pointer",
              opacity: runningFounder || runningQueue || loading ? 0.6 : 1,
            }}
          >
            {runningFounder ? "Running founder review..." : "Run Founder Review"}
          </button>
        </div>

        {error ? (
          <div
            style={{
              borderRadius: 10,
              background: "rgba(254,242,242,1)",
              border: "1px solid rgba(254,202,202,1)",
              color: "#991b1b",
              padding: "10px 12px",
              fontSize: 12,
            }}
          >
            {error}
          </div>
        ) : null}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0,1fr))",
            gap: 8,
          }}
        >
          <StatTile
            label="Last founder run"
            value={prettyDate(founderReviewRun?.config.last_run_at ?? founderConfig?.last_run_at)}
          />
          <StatTile
            label="Cadence"
            value={founderReviewRun?.config.cadence ?? founderConfig?.cadence ?? "weekly"}
          />
          <StatTile
            label="Window"
            value={`${founderReviewRun?.config.days_back ?? founderConfig?.days_back ?? 30} days`}
          />
          <StatTile
            label="Email send"
            value={
              founderReviewRun?.config.send_email ?? founderConfig?.send_email
                ? "enabled"
                : "off"
            }
          />
        </div>

        <div
          style={{
            borderRadius: 10,
            background: "#f8fafc",
            padding: "10px 12px",
            border: "1px solid rgba(226,232,240,1)",
          }}
        >
          <div style={{ fontSize: 11, color: "#64748b" }}>Latest founder summary</div>
          <div style={{ fontSize: 12, color: "#0f172a", marginTop: 6, lineHeight: 1.5 }}>
            {founderSummary}
          </div>
        </div>

        {founderHighlights.length > 0 ? (
          <div
            style={{
              borderRadius: 10,
              background: "#f8fafc",
              padding: "10px 12px",
              border: "1px solid rgba(226,232,240,1)",
            }}
          >
            <div style={{ fontSize: 11, color: "#64748b" }}>Top highlights</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
              {founderHighlights.slice(0, 6).map((item, idx) => (
                <div key={`${item.key ?? "highlight"}-${idx}`} style={{ fontSize: 12, color: "#334155" }}>
                  <span style={{ fontWeight: 700 }}>{item.key ?? "item"}</span>
                  {item.value != null ? `: ${formatValue(item.value)}` : ""}
                  {item.count != null ? ` (${item.count})` : ""}
                  {item.fields?.length ? ` [${item.fields.join(", ")}]` : ""}
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard
        title="Review Queue Snapshot"
        subtitle={latestReviewQueueSnapshot?.workflow_run_id ?? "No queue run loaded"}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, minmax(0,1fr))",
            gap: 8,
          }}
        >
          <StatTile label="Escalated tasks" value={reviewQueueTaskCount} />
          <StatTile label="Target groups" value={targetGroupCount} />
          <StatTile label="Role groups" value={roleGroupCount} />
        </div>

        {latestEscalationSnapshot?.tasks_preview?.length ? (
          <div
            style={{
              borderRadius: 10,
              background: "#f8fafc",
              padding: "10px 12px",
              border: "1px solid rgba(226,232,240,1)",
            }}
          >
            <div style={{ fontSize: 11, color: "#64748b" }}>Escalation preview</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
              {latestEscalationSnapshot.tasks_preview.slice(0, 4).map((item) => (
                <div key={item.id} style={{ fontSize: 12, color: "#334155" }}>
                  <span style={{ fontWeight: 700 }}>{item.objective || item.id}</span>
                  {item.escalation_target ? ` → ${item.escalation_target}` : ""}
                  {item.escalation_reason ? ` — ${item.escalation_reason}` : ""}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ fontSize: 12, color: "#64748b" }}>No review queue loaded yet.</div>
        )}
      </SectionCard>

      <SectionCard
        title="Review Queue Targets"
        subtitle={`${targetGroupCount} target group(s)`}
      >
        {targetGroupCount === 0 ? (
          <div style={{ fontSize: 12, color: "#64748b" }}>No target grouping loaded yet.</div>
        ) : (
          Object.entries(latestQueueGroups).map(([groupName, group]) => (
            <div
              key={groupName}
              style={{
                borderRadius: 10,
                border: "1px solid rgba(226,232,240,1)",
                background: "#f8fafc",
                padding: 10,
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
                <div style={{ fontSize: 12, fontWeight: 800, color: "#111827" }}>{groupName}</div>
                <div style={{ fontSize: 11, color: "#64748b" }}>{group.count} task(s)</div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
                {group.preview.map((item) => (
                  <div key={item.id} style={{ fontSize: 12, color: "#334155" }}>
                    <span style={{ fontWeight: 700 }}>{item.objective || item.id}</span>
                    {item.escalation_reason ? ` — ${item.escalation_reason}` : ""}
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </SectionCard>

      <SectionCard
        title="Owning Roles"
        subtitle={`${roleGroupCount} role group(s)`}
      >
        {roleGroupCount === 0 ? (
          <div style={{ fontSize: 12, color: "#64748b" }}>No role grouping loaded yet.</div>
        ) : (
          Object.entries(latestRoleGroups).map(([groupName, group]) => (
            <div
              key={groupName}
              style={{
                borderRadius: 10,
                border: "1px solid rgba(226,232,240,1)",
                background: "#f8fafc",
                padding: 10,
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
                <div style={{ fontSize: 12, fontWeight: 800, color: "#111827" }}>{groupName}</div>
                <div style={{ fontSize: 11, color: "#64748b" }}>{group.count} task(s)</div>
              </div>
            </div>
          ))
        )}
      </SectionCard>

      <SectionCard
        title="Recent Audit Events"
        subtitle={`${events.length} event(s)`}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0,1fr))",
            gap: 8,
          }}
        >
          <StatTile
            label="Latest email status"
            value={
              latestEmailEvent
                ? "sent"
                : latestEmailFailureEvent
                  ? "failed"
                  : "none"
            }
          />
          <StatTile
            label="Latest trigger event"
            value={latestTriggerEvent ? prettyDate(latestTriggerEvent.created_at) : "—"}
          />
        </div>

        {events.length === 0 ? (
          <div style={{ fontSize: 12, color: "#64748b" }}>No workflow events yet.</div>
        ) : (
          events.slice(0, 8).map((event) => (
            <div
              key={event.id}
              style={{
                borderRadius: 10,
                border: "1px solid rgba(226,232,240,1)",
                background: "#f8fafc",
                padding: 10,
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 700, color: "#111827" }}>
                {event.summary}
              </div>
              <div style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>
                {event.workflow_id ?? "workflow"} · {prettyDate(event.created_at)}
              </div>
            </div>
          ))
        )}
      </SectionCard>
    </div>
  );
}