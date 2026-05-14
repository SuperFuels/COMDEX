"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type JsonRecord = Record<string, unknown>;

type ApprovalItem = {
  id: string;
  workspace_id: string;
  workflow_run_id: string;
  workflow_id: string;
  agent_id: string | null;
  department_key: string | null;
  title: string;
  summary: string | null;
  approval_class: string;
  status: string;
  requested_action: JsonRecord;
  context: JsonRecord;
  requested_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_note: string | null;
};

type StepRun = {
  step_id: string;
  step_name: string;
  step_kind: string;
  status: string;
  input_payload: JsonRecord;
  output_payload: JsonRecord;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
};

type WorkflowRun = {
  id: string;
  workspace_id: string;
  workflow_id: string;
  workflow_version: number;
  workflow_name: string | null;
  agent_id: string | null;
  department_key: string | null;
  trigger_id: string | null;
  trigger_event_type: string | null;
  status: string;
  current_step_id: string | null;
  approval_request_id: string | null;
  input_payload: JsonRecord;
  context: JsonRecord;
  result_payload: JsonRecord;
  error_message: string | null;
  step_runs: StepRun[];
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
};

type ApiListResponse<T> = {
  ok?: boolean;
  items?: T[];
};

type ApiItemResponse<T> = {
  ok?: boolean;
  item?: T;
};

type MarketingStreamPageProps = {
  workspaceId?: string;
  departmentKey?: string;
  operatorId?: string;
  workflowId?: string;
  apiBase?: string;
  resolvedBy?: string;
  onBackToBoardroom?: () => void;
  onBackToDashboard?: () => void;
  onOpenBrandFoundation?: () => void;
};

type NormalizedRunContent = {
  title?: string;
  channel?: string;
  format?: string;
  objective?: string;
  funnelGoal?: string;
  audience?: string;
  persona?: string;
  offer?: string;
  tone?: string;
  caption?: string;
  body?: string;
  hook?: string;
  problem?: string;
  solution?: string;
  proof?: string;
  cta?: string;
  headlines: string[];
  carousel: string[];
  hashtags: string[];
  keywords: string[];
  notes: string[];
  scheduledFor?: string;
  rawResult?: unknown;
  rawDraft?: unknown;
};

type NormalizedRun = {
  source: WorkflowRun;
  content: NormalizedRunContent;
  previewTitle: string;
  previewText: string;
  contentStatusLabel: string;
  stepLabel: string;
  latestError?: string | null;
  waitingApproval: boolean;
  failed: boolean;
  completed: boolean;
};

type CalendarDay = {
  key: string;
  label: string;
  runs: NormalizedRun[];
};

const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8080";

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

function isRecord(value: unknown): value is JsonRecord {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function asRecord(value: unknown): JsonRecord | undefined {
  return isRecord(value) ? value : undefined;
}

function firstString(...values: unknown[]): string | undefined {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return undefined;
}

function stringArray(...values: unknown[]): string[] {
  const out: string[] = [];

  values.forEach((value) => {
    if (Array.isArray(value)) {
      value.forEach((entry) => {
        if (typeof entry === "string" && entry.trim()) {
          out.push(entry.trim());
          return;
        }

        if (isRecord(entry)) {
          const text =
            firstString(
              entry.label,
              entry.title,
              entry.name,
              entry.text,
              entry.value,
              entry.caption,
            ) ?? "";
          if (text) out.push(text);
        }
      });
      return;
    }

    if (typeof value === "string" && value.trim()) {
      const split = value
        .split(/\n|,|•|·|\|/)
        .map((part) => part.trim())
        .filter(Boolean);
      out.push(...split);
    }
  });

  return Array.from(new Set(out));
}

function extractText(value: unknown, depth = 0): string | undefined {
  if (depth > 3) return undefined;

  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" || typeof value === "boolean") return String(value);

  if (Array.isArray(value)) {
    const joined = value
      .map((item) => extractText(item, depth + 1))
      .filter(Boolean)
      .join("\n")
      .trim();
    return joined || undefined;
  }

  if (isRecord(value)) {
    return firstString(
      value.caption,
      value.body,
      value.text,
      value.content,
      value.copy,
      value.message,
      value.summary,
      value.result,
      value.output,
    );
  }

  return undefined;
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

function formatDayLabel(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function formatCalendarHeader(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function prettifyStatus(value?: string | null) {
  if (!value) return "—";
  return value.replace(/_/g, " ");
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

function getCurrentStepLabel(run: WorkflowRun): string {
  if (!run.current_step_id) return "—";
  const step = run.step_runs.find((item) => item.step_id === run.current_step_id);
  if (!step) return run.current_step_id.replace(/_/g, " ");
  return (step.step_name || step.step_kind || step.step_id).replace(/_/g, " ");
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
  if (status === "queued") {
    return "bg-slate-100 text-slate-700 border-slate-200";
  }
  return "bg-slate-100 text-slate-700 border-slate-200";
}

function getChannelMeta(channel?: string) {
  const value = (channel ?? "").toLowerCase();

  if (value.includes("facebook")) {
    return {
      label: "Facebook",
      badge: "f",
      badgeClass: "bg-blue-600 text-white",
    };
  }

  if (value.includes("instagram")) {
    return {
      label: "Instagram",
      badge: "ig",
      badgeClass: "bg-pink-600 text-white",
    };
  }

  if (value.includes("linkedin")) {
    return {
      label: "LinkedIn",
      badge: "in",
      badgeClass: "bg-sky-700 text-white",
    };
  }

  if (value.includes("twitter") || value.includes("x")) {
    return {
      label: "X",
      badge: "x",
      badgeClass: "bg-slate-900 text-white",
    };
  }

  if (value.includes("tiktok")) {
    return {
      label: "TikTok",
      badge: "tt",
      badgeClass: "bg-black text-white",
    };
  }

  if (value.includes("youtube")) {
    return {
      label: "YouTube",
      badge: "yt",
      badgeClass: "bg-red-600 text-white",
    };
  }

  return {
    label: channel || "General",
    badge: "•",
    badgeClass: "bg-slate-700 text-white",
  };
}

function getFormatLabel(run: NormalizedRun) {
  return (
    run.content.format ??
    (run.content.carousel.length > 0 ? "Carousel" : undefined) ??
    (run.content.body ? "Long form" : undefined) ??
    "Post"
  );
}

function getVisualType(run: NormalizedRun) {
  const format = (run.content.format ?? "").toLowerCase();
  const text = `${run.previewTitle} ${run.previewText}`.toLowerCase();

  if (format.includes("video") || text.includes("video") || text.includes("ugc")) {
    return "video";
  }

  if (format.includes("image") || format.includes("visual")) {
    return "image";
  }

  if (format.includes("carousel") || run.content.carousel.length > 1) {
    return "carousel";
  }

  return "text";
}

function normalizeRun(run: WorkflowRun): NormalizedRun {
  const context = asRecord(run.context) ?? {};
  const inputPayload = asRecord(run.input_payload) ?? {};
  const resultPayload = asRecord(run.result_payload) ?? {};

  const resultPostPackage = asRecord(resultPayload.post_package) ?? {};
  const resultDraftCaption = asRecord(resultPayload.draft_caption) ?? {};
  const resultDraftCarousel = asRecord(resultPayload.draft_carousel) ?? {};
  const contextPostPackage = asRecord(context.post_package) ?? {};

  const marketingStrategy =
    asRecord(context.marketing_strategy) ??
    asRecord(inputPayload.marketing_strategy) ??
    {};

  const brandFoundation =
    asRecord(context.brand_foundation_snapshot) ??
    asRecord(inputPayload.brand_foundation_snapshot) ??
    {};

  const latestStep =
    Array.isArray(run.step_runs) && run.step_runs.length > 0
      ? run.step_runs[run.step_runs.length - 1]
      : undefined;

  const caption = firstString(
    resultDraftCaption.draft_caption,
    resultPostPackage.caption,
    context.draft_caption,
    contextPostPackage.caption,
    inputPayload.brief,
    run.workflow_name,
    run.workflow_id,
  );

  const carousel = stringArray(
    resultDraftCarousel.draft_carousel,
    resultPostPackage.carousel,
    context.draft_carousel,
    contextPostPackage.carousel,
  );

  const hashtags = stringArray(
    resultDraftCaption.hashtags,
    resultDraftCarousel.hashtags,
    resultPostPackage.hashtags,
    marketingStrategy.hashtags,
    brandFoundation.hashtags,
  );

  const keywords = stringArray(
    resultDraftCaption.keywords,
    resultDraftCarousel.keywords,
    resultPostPackage.keywords,
    marketingStrategy.keywords,
    brandFoundation.keywords,
  );

  const notes = stringArray(
    marketingStrategy.guidance_notes,
    marketingStrategy.campaign_notes,
    context.guidance_notes,
    context.campaign_notes,
  );

  const previewTitle =
    caption ||
    firstString(
      resultPostPackage.title,
      run.workflow_name,
      run.workflow_id,
    ) ||
    "Marketing output";

  const previewText =
    caption ||
    carousel[0] ||
    firstString(context.brief, inputPayload.brief) ||
    "No generated content available yet.";

  return {
    source: run,
    content: {
      title: previewTitle,
      channel: firstString(
        resultPostPackage.channel,
        stringArray(resultPostPackage.channels)[0],
        stringArray(marketingStrategy.channels)[0],
        stringArray(brandFoundation.channels)[0],
      ),
      format: carousel.length > 1 ? "Carousel" : "Post",
      objective: firstString(
        marketingStrategy.objective,
        brandFoundation.objective,
      ),
      funnelGoal: firstString(
        marketingStrategy.funnel_goal,
        brandFoundation.funnel_goal,
      ),
      audience: firstString(
        marketingStrategy.target_audience,
        brandFoundation.target_audience,
      ),
      persona: firstString(
        marketingStrategy.persona,
        brandFoundation.persona,
      ),
      offer: firstString(
        marketingStrategy.offer,
        brandFoundation.offer,
      ),
      tone: firstString(
        marketingStrategy.tone,
        brandFoundation.tone,
      ),
      caption,
      body: caption,
      hook: carousel[0],
      problem: carousel[1],
      solution: carousel[2],
      proof: carousel[3],
      cta: carousel[4],
      headlines: [],
      carousel,
      hashtags,
      keywords,
      notes,
      scheduledFor: firstString(
        resultPostPackage.scheduled_for,
        context.scheduled_for,
        run.created_at,
      ),
      rawResult: run.result_payload,
      rawDraft: context,
    },
    previewTitle,
    previewText,
    contentStatusLabel:
      run.status === "completed"
        ? "Final content"
        : run.status === "waiting_approval"
          ? "Awaiting approval"
          : run.status === "failed"
            ? "Needs attention"
            : run.status === "running"
              ? "Generating"
              : run.status === "queued"
                ? "Queued"
                : "Draft",
    stepLabel: getCurrentStepLabel(run),
    latestError:
      run.error_message ??
      latestStep?.error_message ??
      null,
    waitingApproval: run.status === "waiting_approval",
    failed: run.status === "failed",
    completed: run.status === "completed",
  };
}

function strategySummaryFromRun(run: WorkflowRun) {
  const context = asRecord(run.context) ?? {};
  const marketingStrategy = asRecord(context.marketing_strategy) ?? {};
  const foundation = asRecord(context.brand_foundation_snapshot) ?? {};

  return {
    brief: firstString(context.brief, marketingStrategy.brief),
    objective: firstString(marketingStrategy.objective, foundation.objective),
    funnelGoal: firstString(marketingStrategy.funnel_goal, foundation.funnel_goal),
    audience: firstString(
      marketingStrategy.target_audience,
      foundation.target_audience,
    ),
    persona: firstString(marketingStrategy.persona, foundation.persona),
    offer: firstString(marketingStrategy.offer, foundation.offer),
    channels: stringArray(marketingStrategy.channels, foundation.channels),
    hashtags: stringArray(marketingStrategy.hashtags, foundation.hashtags),
    keywords: stringArray(marketingStrategy.keywords, foundation.keywords),
    hardRules: stringArray(
      marketingStrategy.hard_rules,
      context.department_notes && isRecord(context.department_notes)
        ? context.department_notes.hard_rules
        : undefined,
    ),
    guidanceNotes: stringArray(
      marketingStrategy.guidance_notes,
      context.department_notes && isRecord(context.department_notes)
        ? context.department_notes.guidance_notes
        : undefined,
    ),
    campaignNotes: stringArray(
      marketingStrategy.campaign_notes,
      context.department_notes && isRecord(context.department_notes)
        ? context.department_notes.campaign_notes
        : undefined,
    ),
  };
}

function getApprovalForRun(
  runId: string | null,
  approvals: ApprovalItem[],
  resolved = false,
) {
  if (!runId) return undefined;

  const filtered = approvals.filter((item) => {
    const status = String(item.status || "").toLowerCase();
    return resolved ? status !== "pending" : status === "pending";
  });

  return filtered.find((item) => {
    const linkedRunId =
      (item as ApprovalItem & {
        run_id?: string;
        queue_item_id?: string;
        runtime_run_id?: string;
      }).workflow_run_id ||
      (item as ApprovalItem & { run_id?: string }).run_id ||
      (item as ApprovalItem & { queue_item_id?: string }).queue_item_id ||
      (item as ApprovalItem & { runtime_run_id?: string }).runtime_run_id ||
      null;

    return linkedRunId === runId;
  });
}

function getRunCalendarDate(run: NormalizedRun) {
  return run.content.scheduledFor || run.source.created_at;
}

function toDayKey(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export default function MarketingStreamPage({
  workspaceId = "costa-conexion",
  departmentKey = "marketing",
  operatorId = "agent_marketing_operator_v1",
  workflowId = "workflow_marketing_content_draft_v1",
  apiBase = DEFAULT_API_BASE,
  resolvedBy = "kevin",
  onBackToBoardroom,
  onBackToDashboard,
  onOpenBrandFoundation,
}: MarketingStreamPageProps) {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [runDetails, setRunDetails] = useState<Record<string, WorkflowRun>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingRunDetail, setLoadingRunDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedApprovalId, setSelectedApprovalId] = useState<string | null>(null);
  const [detailRunId, setDetailRunId] = useState<string | null>(null);
  const [showApprovalHistory, setShowApprovalHistory] = useState(false);
  const [showManualSuggestionModal, setShowManualSuggestionModal] = useState(false);
  const [calendarStartIndex, setCalendarStartIndex] = useState(0);
  const [terminalInput, setTerminalInput] = useState("");

  const [brief, setBrief] = useState(
    "Draft a Facebook post and simple carousel for spring telecom upgrade offer.",
  );
  const [objective, setObjective] = useState("Drive local enquiries");
  const [funnelGoal, setFunnelGoal] = useState("Lead capture");
  const [targetAudience, setTargetAudience] = useState(
    "Local homeowners and small business owners in core service towns.",
  );
  const [persona, setPersona] = useState("Local service buyer");
  const [offer, setOffer] = useState("Spring telecom upgrade offer");
  const [channels, setChannels] = useState("Facebook\nInstagram");
  const [hashtags, setHashtags] = useState(
    "#LocalBusiness\n#TrustedServices\n#LeadGeneration",
  );
  const [keywords, setKeywords] = useState(
    "local telecom upgrade\nsmall business connectivity\ntrusted local installer",
  );

  const [hardRules, setHardRules] = useState(
    [
      "Do not publish automatically.",
      "Do not exceed one main post per day.",
      "Avoid shouting sales language.",
    ].join("\n"),
  );

  const [guidanceNotes, setGuidanceNotes] = useState(
    [
      "Keep the tone clean, useful, and confident.",
      "Lean into trusted local-business language.",
      "Prefer simple visuals and clear calls to action.",
    ].join("\n"),
  );

  const [campaignNotes, setCampaignNotes] = useState(
    [
      "Current focus: spring telecom upgrade offer.",
      "Push reliability, clarity, and local service trust.",
      "Avoid weekend publishing for now.",
    ].join("\n"),
  );

  const refresh = useCallback(
    async (mode: "initial" | "refresh" = "refresh") => {
      if (mode === "initial") setLoading(true);
      else setRefreshing(true);

      setError(null);

      try {
        const [approvalsRes, runsRes] = await Promise.all([
          fetch(
            buildUrl(apiBase, "/api/local-node/approvals", {
              department_key: departmentKey,
              limit: 100,
            }),
            { cache: "no-store" },
          ),
          fetch(
            buildUrl(apiBase, "/api/local-node/runs", {
              department_key: departmentKey,
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

        const approvalsJson =
          (await approvalsRes.json()) as ApiListResponse<ApprovalItem>;
        const runsJson =
          (await runsRes.json()) as ApiListResponse<WorkflowRun>;

        const nextApprovals = Array.isArray(approvalsJson.items)
          ? approvalsJson.items
          : [];

        const nextRuns = Array.isArray(runsJson.items)
          ? runsJson.items
          : [];

        setApprovals(nextApprovals);
        setRuns(nextRuns);

        setRunDetails((prev) => {
          const merged = { ...prev };
          nextRuns.forEach((run) => {
            merged[run.id] = run;
          });
          return merged;
        });

        setSelectedRunId((prev) => {
          if (prev && nextRuns.some((run) => run.id === prev)) {
            return prev;
          }
          return nextRuns[0]?.id ?? null;
        });

        setSelectedApprovalId((prev) => {
          if (prev && nextApprovals.some((approval) => approval.id === prev)) {
            return prev;
          }
          return nextApprovals[0]?.id ?? null;
        });

        setDetailRunId((prev) => {
          if (!prev) return null;
          return nextRuns.some((run) => run.id === prev) ? prev : null;
        });
      } catch (e) {
        setError(
          e instanceof Error ? e.message : "Failed to load marketing stream",
        );
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

  useEffect(() => {
    if (!selectedRunId && runs[0]?.id) {
      setSelectedRunId(runs[0].id);
    }

    setRunDetails((prev) => {
      const merged = { ...prev };
      runs.forEach((run) => {
        merged[run.id] = run;
      });
      return merged;
    });
  }, [runs, selectedRunId]);

  const pendingApprovals = useMemo(
    () =>
      approvals.filter(
        (item) => String(item.status || "").toLowerCase() === "pending",
      ),
    [approvals],
  );

  const resolvedApprovals = useMemo(
    () =>
      approvals.filter(
        (item) => String(item.status || "").toLowerCase() !== "pending",
      ),
    [approvals],
  );

  const selectedRunRaw = useMemo(() => {
    if (!selectedRunId) return runs[0] ?? null;
    return (
      runDetails[selectedRunId] ??
      runs.find((run) => run.id === selectedRunId) ??
      null
    );
  }, [runDetails, runs, selectedRunId]);

  const detailRunRaw = useMemo(() => {
    if (!detailRunId) return null;
    return (
      runDetails[detailRunId] ??
      runs.find((run) => run.id === detailRunId) ??
      null
    );
  }, [detailRunId, runDetails, runs]);

  const selectedRun = useMemo(
    () => (selectedRunRaw ? normalizeRun(selectedRunRaw) : null),
    [selectedRunRaw],
  );

  const detailRun = useMemo(
    () => (detailRunRaw ? normalizeRun(detailRunRaw) : null),
    [detailRunRaw],
  );

  const normalizedRuns = useMemo(() => {
    const items = runs.map(normalizeRun);
    return [...items].sort((a, b) => {
      return (
        new Date(getRunCalendarDate(b)).getTime() -
        new Date(getRunCalendarDate(a)).getTime()
      );
    });
  }, [runs]);

  const selectedApproval = useMemo(() => {
    if (!approvals.length) return null;
    return approvals.find((item) => item.id === selectedApprovalId) ?? approvals[0];
  }, [approvals, selectedApprovalId]);

  const queueCount = useMemo(
    () => runs.filter((run) => run.status === "queued").length,
    [runs],
  );

  const runningCount = useMemo(
    () => runs.filter((run) => run.status === "running").length,
    [runs],
  );

  const waitingApprovalCount = useMemo(
    () => runs.filter((run) => run.status === "waiting_approval").length,
    [runs],
  );

  const failedCount = useMemo(
    () => runs.filter((run) => run.status === "failed").length,
    [runs],
  );

  const completedCount = useMemo(
    () => runs.filter((run) => run.status === "completed").length,
    [runs],
  );

  const strategySummary = useMemo(() => {
    if (!selectedRunRaw) {
      return {
        brief,
        objective,
        funnelGoal,
        audience: targetAudience,
        persona,
        offer,
        channels: stringArray(channels),
        hashtags: stringArray(hashtags),
        keywords: stringArray(keywords),
        hardRules: stringArray(hardRules),
        guidanceNotes: stringArray(guidanceNotes),
        campaignNotes: stringArray(campaignNotes),
      };
    }

    return strategySummaryFromRun(selectedRunRaw);
  }, [
    brief,
    campaignNotes,
    channels,
    funnelGoal,
    guidanceNotes,
    hardRules,
    hashtags,
    keywords,
    objective,
    offer,
    persona,
    selectedRunRaw,
    targetAudience,
  ]);

  const allCalendarDays = useMemo<CalendarDay[]>(() => {
    const groups = new Map<string, NormalizedRun[]>();

    normalizedRuns.forEach((run) => {
      const dayKey = toDayKey(getRunCalendarDate(run));
      const existing = groups.get(dayKey) ?? [];
      existing.push(run);
      groups.set(dayKey, existing);
    });

    const sortedKeys = [...groups.keys()].sort(
      (a, b) => new Date(a).getTime() - new Date(b).getTime(),
    );

    const limitedKeys = sortedKeys.slice(-14);

    return limitedKeys.map((key) => ({
      key,
      label: formatCalendarHeader(key),
      runs: (groups.get(key) ?? []).sort(
        (a, b) =>
          new Date(getRunCalendarDate(a)).getTime() -
          new Date(getRunCalendarDate(b)).getTime(),
      ),
    }));
  }, [normalizedRuns]);

  const visibleCalendarDays = useMemo(() => {
    return allCalendarDays.slice(calendarStartIndex, calendarStartIndex + 5);
  }, [allCalendarDays, calendarStartIndex]);

  const canPageBack = calendarStartIndex > 0;
  const canPageForward = calendarStartIndex + 5 < allCalendarDays.length;

  useEffect(() => {
    if (calendarStartIndex > Math.max(0, allCalendarDays.length - 5)) {
      setCalendarStartIndex(Math.max(0, allCalendarDays.length - 5));
    }
  }, [allCalendarDays.length, calendarStartIndex]);

  async function handleLaunch() {
    setBusy(true);
    setError(null);

    try {
      const res = await fetch(`${apiBase}/api/local-node/marketing/launch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brief,
          objective,
          funnel_goal: funnelGoal,
          target_audience: targetAudience,
          persona,
          offer,
          channels: stringArray(channels),
          hashtags: stringArray(hashtags),
          keywords: stringArray(keywords),
          hard_rules: stringArray(hardRules),
          guidance_notes: stringArray(guidanceNotes),
          campaign_notes: stringArray(campaignNotes),
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Launch failed");
      }

      const launchJson = (await res.json()) as
        | ApiItemResponse<WorkflowRun>
        | {
            ok?: boolean;
            item?: WorkflowRun;
          };

      const launchedRun = launchJson?.item;
      const launchedRunId = launchedRun?.id ?? null;
      const launchedApprovalId = launchedRun?.approval_request_id ?? null;

      await refresh();

      if (launchedRunId) {
        setSelectedRunId(launchedRunId);
        setDetailRunId(launchedRunId);
      }

      if (launchedApprovalId) {
        setSelectedApprovalId(launchedApprovalId);
      }

      setShowManualSuggestionModal(false);
      setTerminalInput("");
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
      const approval = approvals.find((item) => item.id === approvalId);

      const res = await fetch(
        `${apiBase}/api/local-node/approvals/${approvalId}/resolve`,
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

      const approvalJson = (await res.json()) as ApiItemResponse<WorkflowRun> & {
        run?: WorkflowRun;
        item?: {
          workflow_run_id?: string;
          run_id?: string;
        };
      };

      const resolvedRunId =
        approvalJson?.run?.id ||
        approval?.workflow_run_id ||
        approvalJson?.item?.workflow_run_id ||
        approvalJson?.item?.run_id ||
        null;

      await refresh();

      if (resolvedRunId) {
        setSelectedRunId(resolvedRunId);
        setDetailRunId(resolvedRunId);
      }

      setSelectedApprovalId(approvalId);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Approval resolution failed",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="h-full min-h-0 w-full overflow-hidden bg-slate-100 text-slate-900">
      <div className="flex h-full min-h-0 flex-col">
        <div className="border-b border-slate-200 bg-white px-6 py-4">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="min-w-0">
              <div className="text-sm font-semibold text-slate-500">
                Marketing Stream
              </div>
              <div className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
                Content calendar and creation
              </div>
              <div className="mt-2 text-sm text-slate-600">
                Brand-led content suggestions shown directly in calendar view.
                Open details only when needed.
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {onBackToBoardroom ? (
                <button
                  type="button"
                  onClick={onBackToBoardroom}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold shadow-sm transition hover:bg-slate-50"
                >
                  Back to boardroom
                </button>
              ) : null}

              {onBackToDashboard ? (
                <button
                  type="button"
                  onClick={onBackToDashboard}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold shadow-sm transition hover:bg-slate-50"
                >
                  Back to dashboard
                </button>
              ) : null}

              {onOpenBrandFoundation ? (
                <button
                  type="button"
                  onClick={onOpenBrandFoundation}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold shadow-sm transition hover:bg-slate-50"
                >
                  Brand foundation
                </button>
              ) : null}

              <button
                type="button"
                onClick={() => setShowApprovalHistory(true)}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold shadow-sm transition hover:bg-slate-50"
              >
                View history
              </button>

              <button
                type="button"
                onClick={() => setShowManualSuggestionModal(true)}
                className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
              >
                New manual suggestion
              </button>

              {refreshing ? (
                <div className="text-xs text-slate-500">Refreshing…</div>
              ) : null}

              <button
                type="button"
                onClick={() => void refresh()}
                disabled={busy || loading}
                className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>

        {error ? (
          <div className="mx-6 mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="min-h-0 flex-1 overflow-auto p-4">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <PillInfo label="Runs" value={String(runs.length)} />
            <PillInfo label="Awaiting approval" value={String(waitingApprovalCount)} />
            <PillInfo label="Queued" value={String(queueCount)} />
            <PillInfo label="Running" value={String(runningCount)} />
            <PillInfo label="Failed" value={String(failedCount)} />
            <PillInfo label="Completed" value={String(completedCount)} />
          </div>

          <div className="mb-4 rounded-[24px] border border-slate-200 bg-slate-950 px-4 py-3 text-sm text-emerald-300 shadow-sm">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
              <div className="shrink-0 font-mono text-xs text-emerald-400">
                &gt; Aion / marketing command
              </div>

              <input
                value={terminalInput}
                onChange={(e) => setTerminalInput(e.target.value)}
                placeholder="Ask for a content idea, platform mix, campaign angle, or scheduling suggestion..."
                className="min-w-0 flex-1 rounded-xl border border-emerald-700/40 bg-slate-900 px-4 py-2 text-sm text-emerald-200 outline-none placeholder:text-emerald-700"
              />

              <button
                type="button"
                onClick={() => {
                  const next = terminalInput.trim();
                  if (next) setBrief(next);
                  setShowManualSuggestionModal(true);
                }}
                className="rounded-xl border border-emerald-600/40 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-200 transition hover:bg-emerald-500/20"
              >
                Send
              </button>
            </div>
          </div>

          <div className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-5 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <div className="text-sm font-semibold text-slate-500">Calendar</div>
                <div className="text-2xl font-bold text-slate-900">
                  Suggested content plan
                </div>
                <div className="mt-1 text-sm text-slate-600">
                  Actual generated posts, shown by day and platform.
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCalendarStartIndex((prev) => Math.max(0, prev - 2))}
                  disabled={!canPageBack}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  ← Previous days
                </button>

                <button
                  type="button"
                  onClick={() =>
                    setCalendarStartIndex((prev) =>
                      Math.min(Math.max(0, allCalendarDays.length - 5), prev + 2),
                    )
                  }
                  disabled={!canPageForward}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next days →
                </button>
              </div>
            </div>

            {loading ? (
              <EmptyState>Loading content calendar…</EmptyState>
            ) : visibleCalendarDays.length === 0 ? (
              <EmptyState>No scheduled content yet.</EmptyState>
            ) : (
              <div className="overflow-x-auto">
                <div className="grid min-w-[1500px] grid-cols-5 gap-4">
                  {visibleCalendarDays.map((day) => (
                    <div
                      key={day.key}
                      className="rounded-[24px] border border-slate-200 bg-slate-50 p-3"
                    >
                      <div className="mb-3 flex items-center justify-between gap-2">
                        <div className="rounded-full bg-blue-600 px-3 py-1 text-xs font-semibold text-white">
                          {day.label}
                        </div>
                        <div className="text-xs text-slate-500">
                          {day.runs.length} item{day.runs.length === 1 ? "" : "s"}
                        </div>
                      </div>

                      <div className="space-y-4">
                        {day.runs.map((run) => {
                          const channelMeta = getChannelMeta(run.content.channel);
                          const approval = getApprovalForRun(run.source.id, approvals, false);
                          const visualType = getVisualType(run);

                          return (
                            <div
                              key={run.source.id}
                              className={`overflow-hidden rounded-[24px] border bg-white shadow-sm transition ${
                                selectedRunId === run.source.id
                                  ? "border-blue-300 ring-2 ring-blue-100"
                                  : "border-slate-200"
                              }`}
                            >
                              <div className="border-b border-slate-100 px-4 py-3">
                                <div className="flex items-start justify-between gap-3">
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span
                                        className={`inline-flex h-7 min-w-7 items-center justify-center rounded-full px-2 text-[11px] font-bold uppercase ${channelMeta.badgeClass}`}
                                      >
                                        {channelMeta.badge}
                                      </span>
                                      <div className="text-xs font-semibold text-slate-500">
                                        {channelMeta.label} · {getFormatLabel(run)}
                                      </div>
                                    </div>
                                    <div className="mt-2 text-sm font-semibold text-slate-900">
                                      {run.previewTitle}
                                    </div>
                                  </div>

                                  <StatusPill status={run.source.status} />
                                </div>
                              </div>

                              <div className="p-4">
                                <PostPreviewCard run={run} />

                                <div className="mt-4 flex flex-wrap gap-2">
                                  {run.content.hashtags.slice(0, 3).map((item) => (
                                    <Chip key={`${run.source.id}-${item}`}>{item}</Chip>
                                  ))}
                                </div>

                                <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-500">
                                  <span>{formatTime(getRunCalendarDate(run))}</span>
                                  <span>•</span>
                                  <span>{run.contentStatusLabel}</span>
                                  <span>•</span>
                                  <span>{visualType}</span>
                                </div>

                                {run.latestError ? (
                                  <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                                    {run.latestError}
                                  </div>
                                ) : null}

                                {approval ? (
                                  <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-3">
                                    <div className="text-sm font-semibold text-amber-800">
                                      Approval required
                                    </div>
                                    <div className="mt-1 text-xs text-amber-700">
                                      {approval.summary || approval.title}
                                    </div>
                                    <div className="mt-3 flex flex-wrap gap-2">
                                      <button
                                        type="button"
                                        disabled={busy}
                                        onClick={() => {
                                          setSelectedApprovalId(approval.id);
                                          setSelectedRunId(run.source.id);
                                          void handleResolveApproval(approval.id, true);
                                        }}
                                        className="rounded-xl bg-slate-950 px-3 py-2 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                                      >
                                        Approve
                                      </button>
                                      <button
                                        type="button"
                                        disabled={busy}
                                        onClick={() => {
                                          setSelectedApprovalId(approval.id);
                                          setSelectedRunId(run.source.id);
                                          void handleResolveApproval(approval.id, false);
                                        }}
                                        className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                                      >
                                        Reject
                                      </button>
                                    </div>
                                  </div>
                                ) : null}

                                <div className="mt-4 flex gap-2">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setSelectedRunId(run.source.id);
                                      setDetailRunId(run.source.id);
                                    }}
                                    className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
                                  >
                                    See details
                                  </button>
                                </div>
                              </div>
                            </div>
                          );
                        })}

                        {day.runs.length === 0 ? (
                          <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
                            No content planned.
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {detailRun && detailRunRaw ? (
        <RunDetailsModal
          run={detailRun}
          rawRun={detailRunRaw}
          approval={getApprovalForRun(detailRunRaw.id, approvals, false)}
          onClose={() => setDetailRunId(null)}
          onApprove={async (approvalId) => {
            setSelectedApprovalId(approvalId);
            await handleResolveApproval(approvalId, true);
          }}
          onReject={async (approvalId) => {
            setSelectedApprovalId(approvalId);
            await handleResolveApproval(approvalId, false);
          }}
          busy={busy}
        />
      ) : null}

      {showApprovalHistory ? (
        <ApprovalHistoryModal
          approvals={resolvedApprovals}
          selectedApproval={selectedApproval}
          onSelect={setSelectedApprovalId}
          onClose={() => setShowApprovalHistory(false)}
        />
      ) : null}

      {showManualSuggestionModal ? (
        <ManualSuggestionModal
          brief={brief}
          setBrief={setBrief}
          objective={objective}
          setObjective={setObjective}
          funnelGoal={funnelGoal}
          setFunnelGoal={setFunnelGoal}
          targetAudience={targetAudience}
          setTargetAudience={setTargetAudience}
          persona={persona}
          setPersona={setPersona}
          offer={offer}
          setOffer={setOffer}
          channels={channels}
          setChannels={setChannels}
          keywords={keywords}
          setKeywords={setKeywords}
          hashtags={hashtags}
          setHashtags={setHashtags}
          hardRules={hardRules}
          setHardRules={setHardRules}
          guidanceNotes={guidanceNotes}
          setGuidanceNotes={setGuidanceNotes}
          campaignNotes={campaignNotes}
          setCampaignNotes={setCampaignNotes}
          onClose={() => setShowManualSuggestionModal(false)}
          onSubmit={async () => {
            await handleLaunch();
            setShowManualSuggestionModal(false);
            setTerminalInput("");
          }}
          busy={busy}
          strategySummary={strategySummary}
        />
      ) : null}
    </div>
  );
}

function PostPreviewCard({ run }: { run: NormalizedRun }) {
  const channelMeta = getChannelMeta(run.content.channel);
  const visualType = getVisualType(run);

  if (visualType === "video") {
    return (
      <div className="overflow-hidden rounded-[22px] border border-slate-200 bg-slate-50">
        <div className="relative aspect-[4/5] bg-gradient-to-br from-slate-200 to-slate-300">
          <div className="absolute left-3 top-3 rounded-full bg-white/90 px-2 py-1 text-[11px] font-semibold text-slate-700">
            Video concept
          </div>
          <div className="absolute bottom-3 right-3 rounded-full bg-black/80 px-3 py-1 text-xs font-semibold text-white">
            0:30
          </div>
          <div className="absolute inset-x-4 bottom-6 rounded-2xl bg-white/92 p-3 shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {channelMeta.label}
            </div>
            <div className="mt-1 text-sm font-semibold text-slate-900">
              {run.previewTitle}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (visualType === "carousel") {
    return (
      <div className="space-y-2">
        <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Carousel preview
            </div>
            <span
              className={`inline-flex h-7 min-w-7 items-center justify-center rounded-full px-2 text-[11px] font-bold uppercase ${channelMeta.badgeClass}`}
            >
              {channelMeta.badge}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-2">
            {run.content.carousel.slice(0, 4).map((item, index) => (
              <div
                key={`${item}-${index}`}
                className="rounded-2xl border border-slate-200 bg-white p-3"
              >
                <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                  Card {index + 1}
                </div>
                <div className="mt-2 text-sm font-semibold text-slate-900">
                  {item}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[22px] border border-slate-200 bg-white p-4">
          <div className="text-sm text-slate-700">{run.previewText}</div>
        </div>
      </div>
    );
  }

  if (visualType === "image") {
    return (
      <div className="overflow-hidden rounded-[22px] border border-slate-200 bg-slate-50">
        <div className="relative aspect-square bg-gradient-to-br from-slate-200 via-slate-100 to-slate-300">
          <div className="absolute left-3 top-3 rounded-full bg-white/90 px-2 py-1 text-[11px] font-semibold text-slate-700">
            Image concept
          </div>
          <div className="absolute inset-x-4 bottom-4 rounded-2xl bg-white/92 p-3 shadow-sm">
            <div className="text-sm font-semibold text-slate-900">
              {run.previewTitle}
            </div>
            <div className="mt-1 line-clamp-3 text-xs text-slate-600">
              {run.previewText}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-[22px] border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Text preview
        </div>
        <span
          className={`inline-flex h-7 min-w-7 items-center justify-center rounded-full px-2 text-[11px] font-bold uppercase ${channelMeta.badgeClass}`}
        >
          {channelMeta.badge}
        </span>
      </div>
      <div className="text-sm font-semibold text-slate-900">{run.previewTitle}</div>
      <div className="mt-2 whitespace-pre-wrap text-sm text-slate-700">
        {run.previewText}
      </div>
    </div>
  );
}

function RunDetailsModal({
  run,
  rawRun,
  approval,
  onClose,
  onApprove,
  onReject,
  busy,
}: {
  run: NormalizedRun;
  rawRun: WorkflowRun;
  approval?: ApprovalItem;
  onClose: () => void;
  onApprove: (approvalId: string) => Promise<void>;
  onReject: (approvalId: string) => Promise<void>;
  busy: boolean;
}) {
  const strategy = strategySummaryFromRun(rawRun);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/45 p-4">
      <div className="flex h-[88vh] w-full max-w-6xl flex-col overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div className="min-w-0">
            <div className="text-sm font-semibold text-slate-500">Run details</div>
            <div className="mt-1 text-2xl font-bold text-slate-900">
              {run.previewTitle}
            </div>
            <div className="mt-1 text-sm text-slate-600">
              {rawRun.id} · {formatTimeLong(rawRun.updated_at)}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <StatusPill status={rawRun.status} />
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              Close
            </button>
          </div>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-0 xl:grid-cols-[minmax(0,1.2fr)_420px]">
          <div className="min-h-0 overflow-auto px-6 py-5">
            <div className="grid gap-4">
              <DetailCard title="Content preview">
                <PostPreviewCard run={run} />
              </DetailCard>

              {approval ? (
                <DetailCard title="Approval">
                  <div className="space-y-3">
                    <div className="text-sm text-slate-700">
                      {approval.summary || approval.title}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void onApprove(approval.id)}
                        className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void onReject(approval.id)}
                        className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                </DetailCard>
              ) : null}

              {run.content.caption || run.content.body ? (
                <DetailCard title="Generated copy">
                  {run.content.caption ? (
                    <>
                      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Caption
                      </div>
                      <pre className="mb-4 whitespace-pre-wrap text-sm text-slate-700">
                        {run.content.caption}
                      </pre>
                    </>
                  ) : null}

                  {run.content.body ? (
                    <>
                      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Body
                      </div>
                      <pre className="whitespace-pre-wrap text-sm text-slate-700">
                        {run.content.body}
                      </pre>
                    </>
                  ) : null}
                </DetailCard>
              ) : null}

              {run.content.carousel.length > 0 ? (
                <DetailCard title="Content blocks">
                  <div className="space-y-2">
                    {run.content.carousel.map((item, index) => (
                      <div
                        key={`${item}-${index}`}
                        className="rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-700"
                      >
                        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Card {index + 1}
                        </div>
                        {item}
                      </div>
                    ))}
                  </div>
                </DetailCard>
              ) : null}

              {run.content.headlines.length > 0 ? (
                <DetailCard title="Headlines">
                  <div className="flex flex-wrap gap-2">
                    {run.content.headlines.map((item) => (
                      <Chip key={item}>{item}</Chip>
                    ))}
                  </div>
                </DetailCard>
              ) : null}

              <DetailCard title="Step timeline">
                <div className="space-y-3">
                  {rawRun.step_runs.length === 0 ? (
                    <div className="text-sm text-slate-500">
                      No step data available.
                    </div>
                  ) : (
                    rawRun.step_runs.map((step, index) => (
                      <div
                        key={`${step.step_id}-${index}`}
                        className="rounded-2xl border border-slate-200 bg-white p-3"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="text-sm font-semibold text-slate-900">
                              {index + 1}. {prettifyStatus(step.step_name || step.step_kind || step.step_id)}
                            </div>
                            <div className="mt-1 text-xs text-slate-500">
                              {formatTime(step.started_at)} → {formatTime(step.completed_at)}
                            </div>
                          </div>
                          <StatusPill status={step.status} />
                        </div>

                        {step.error_message ? (
                          <div className="mt-3 rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                            {step.error_message}
                          </div>
                        ) : null}

                        {step.output_payload && Object.keys(step.output_payload).length > 0 ? (
                          <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs text-slate-700">
                            {stringifyValue(step.output_payload)}
                          </pre>
                        ) : null}
                      </div>
                    ))
                  )}
                </div>
              </DetailCard>
            </div>
          </div>

          <div className="min-h-0 overflow-auto border-l border-slate-200 bg-slate-50 px-5 py-5">
            <div className="grid gap-4">
              <div className="text-sm font-semibold text-slate-500">
                Strategy and metadata
              </div>

              <MiniStat label="Run ID" value={rawRun.id} />
              <MiniStat label="Status" value={prettifyStatus(rawRun.status)} />
              <MiniStat label="Current step" value={getCurrentStepLabel(rawRun)} />
              <MiniStat
                label="Scheduled / created"
                value={formatDayLabel(run.content.scheduledFor || rawRun.created_at)}
                helper={formatTimeLong(run.content.scheduledFor || rawRun.created_at)}
              />

              {run.content.objective ? (
                <MiniStat label="Objective" value={run.content.objective} />
              ) : null}
              {run.content.funnelGoal ? (
                <MiniStat label="Funnel goal" value={run.content.funnelGoal} />
              ) : null}
              {run.content.audience ? (
                <MiniStat label="Audience" value={run.content.audience} />
              ) : null}
              {run.content.persona ? (
                <MiniStat label="Persona" value={run.content.persona} />
              ) : null}
              {run.content.offer ? (
                <MiniStat label="Offer" value={run.content.offer} />
              ) : null}

              {strategy.channels.length > 0 ? (
                <DetailCard title="Channels">
                  <div className="flex flex-wrap gap-2">
                    {strategy.channels.map((item) => (
                      <Chip key={item}>{item}</Chip>
                    ))}
                  </div>
                </DetailCard>
              ) : null}

              {run.content.hashtags.length > 0 ? (
                <DetailCard title="Hashtags">
                  <div className="flex flex-wrap gap-2">
                    {run.content.hashtags.map((item) => (
                      <Chip key={item}>{item}</Chip>
                    ))}
                  </div>
                </DetailCard>
              ) : null}

              {run.content.keywords.length > 0 ? (
                <DetailCard title="Keywords">
                  <div className="flex flex-wrap gap-2">
                    {run.content.keywords.map((item) => (
                      <Chip key={item}>{item}</Chip>
                    ))}
                  </div>
                </DetailCard>
              ) : null}

              <DetailCard title="Raw context">
                <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-slate-700">
                  {stringifyValue(rawRun.context)}
                </pre>
              </DetailCard>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ApprovalHistoryModal({
  approvals,
  selectedApproval,
  onSelect,
  onClose,
}: {
  approvals: ApprovalItem[];
  selectedApproval: ApprovalItem | null;
  onSelect: (id: string | null) => void;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/45 p-4">
      <div className="flex h-[82vh] w-full max-w-4xl flex-col overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div>
            <div className="text-sm font-semibold text-slate-500">Approval history</div>
            <div className="mt-1 text-2xl font-bold text-slate-900">
              Review previous decisions
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Close
          </button>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-0 xl:grid-cols-[360px_minmax(0,1fr)]">
          <div className="min-h-0 overflow-auto border-r border-slate-200 bg-slate-50 p-5">
            <div className="space-y-3">
              {approvals.length === 0 ? (
                <EmptyState>No resolved approvals yet.</EmptyState>
              ) : (
                approvals.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onSelect(item.id)}
                    className={`w-full rounded-2xl border p-4 text-left transition ${
                      selectedApproval?.id === item.id
                        ? "border-blue-300 bg-blue-50"
                        : "border-slate-200 bg-white hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{item.title}</div>
                        <div className="mt-1 text-xs text-slate-500">
                          {item.resolved_at
                            ? `Resolved ${formatTimeLong(item.resolved_at)}`
                            : formatTimeLong(item.requested_at)}
                        </div>
                      </div>
                      <StatusPill status={item.status} />
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="min-h-0 overflow-auto p-5">
            {!selectedApproval ? (
              <EmptyState>Select an approval item.</EmptyState>
            ) : (
              <div className="space-y-4">
                <MiniStat label="Title" value={selectedApproval.title} />
                <MiniStat label="Status" value={prettifyStatus(selectedApproval.status)} />
                <MiniStat
                  label="Requested"
                  value={formatTimeLong(selectedApproval.requested_at)}
                />
                {selectedApproval.resolved_at ? (
                  <MiniStat
                    label="Resolved"
                    value={formatTimeLong(selectedApproval.resolved_at)}
                  />
                ) : null}
                {selectedApproval.summary ? (
                  <DetailCard title="Summary">
                    <div className="text-sm text-slate-700">{selectedApproval.summary}</div>
                  </DetailCard>
                ) : null}
                <DetailCard title="Payload">
                  <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-slate-700">
                    {stringifyValue({
                      requested_action: selectedApproval.requested_action,
                      context: selectedApproval.context,
                    })}
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

function PillInfo({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
      <span className="font-semibold text-slate-900">{value}</span> {label}
    </div>
  );
}

function ManualSuggestionModal({
  brief,
  setBrief,
  objective,
  setObjective,
  funnelGoal,
  setFunnelGoal,
  targetAudience,
  setTargetAudience,
  persona,
  setPersona,
  offer,
  setOffer,
  channels,
  setChannels,
  keywords,
  setKeywords,
  hashtags,
  setHashtags,
  hardRules,
  setHardRules,
  guidanceNotes,
  setGuidanceNotes,
  campaignNotes,
  setCampaignNotes,
  onClose,
  onSubmit,
  busy,
  strategySummary,
}: {
  brief: string;
  setBrief: (value: string) => void;
  objective: string;
  setObjective: (value: string) => void;
  funnelGoal: string;
  setFunnelGoal: (value: string) => void;
  targetAudience: string;
  setTargetAudience: (value: string) => void;
  persona: string;
  setPersona: (value: string) => void;
  offer: string;
  setOffer: (value: string) => void;
  channels: string;
  setChannels: (value: string) => void;
  keywords: string;
  setKeywords: (value: string) => void;
  hashtags: string;
  setHashtags: (value: string) => void;
  hardRules: string;
  setHardRules: (value: string) => void;
  guidanceNotes: string;
  setGuidanceNotes: (value: string) => void;
  campaignNotes: string;
  setCampaignNotes: (value: string) => void;
  onClose: () => void;
  onSubmit: () => Promise<void>;
  busy: boolean;
  strategySummary: {
    brief?: string;
    objective?: string;
    funnelGoal?: string;
    audience?: string;
    persona?: string;
    offer?: string;
  };
}) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/45 p-4">
      <div className="flex h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div>
            <div className="text-sm font-semibold text-slate-500">
              New manual suggestion
            </div>
            <div className="mt-1 text-2xl font-bold text-slate-900">
              Create content suggestions
            </div>
            <div className="mt-1 text-sm text-slate-600">
              Build the next content set from your brand strategy and campaign rules.
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Close
          </button>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-1 gap-0 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="min-h-0 overflow-auto px-6 py-5">
            <div className="grid gap-5">
              <Section title="Launch brief">
                <textarea
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  rows={4}
                  className="w-full rounded-3xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
                />
              </Section>

              <Section title="Strategy snapshot">
                <div className="grid gap-3 md:grid-cols-2">
                  <Input label="Objective" value={objective} onChange={setObjective} />
                  <Input label="Funnel goal" value={funnelGoal} onChange={setFunnelGoal} />
                  <Input
                    label="Target audience"
                    value={targetAudience}
                    onChange={setTargetAudience}
                  />
                  <Input label="Persona" value={persona} onChange={setPersona} />
                  <Input label="Offer" value={offer} onChange={setOffer} />
                </div>
              </Section>

              <Section title="Channels, keywords, hashtags">
                <div className="grid gap-4 md:grid-cols-3">
                  <LabelledTextarea
                    label="Channels"
                    value={channels}
                    onChange={setChannels}
                    rows={5}
                  />
                  <LabelledTextarea
                    label="Keywords"
                    value={keywords}
                    onChange={setKeywords}
                    rows={5}
                  />
                  <LabelledTextarea
                    label="Hashtags"
                    value={hashtags}
                    onChange={setHashtags}
                    rows={5}
                  />
                </div>
              </Section>

              <Section title="Hard rules">
                <textarea
                  value={hardRules}
                  onChange={(e) => setHardRules(e.target.value)}
                  rows={4}
                  className="w-full rounded-3xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
                />
              </Section>

              <Section title="Guidance notes">
                <textarea
                  value={guidanceNotes}
                  onChange={(e) => setGuidanceNotes(e.target.value)}
                  rows={4}
                  className="w-full rounded-3xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
                />
              </Section>

              <Section title="Campaign notes">
                <textarea
                  value={campaignNotes}
                  onChange={(e) => setCampaignNotes(e.target.value)}
                  rows={4}
                  className="w-full rounded-3xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
                />
              </Section>
            </div>
          </div>

          <div className="min-h-0 overflow-auto border-l border-slate-200 bg-slate-50 px-5 py-5">
            <div className="grid gap-4">
              <div className="text-sm font-semibold text-slate-500">
                Selected strategy
              </div>

              <MiniStat label="Objective" value={strategySummary.objective ?? "—"} />
              <MiniStat label="Funnel" value={strategySummary.funnelGoal ?? "—"} />
              <MiniStat label="Audience" value={strategySummary.audience ?? "—"} />
              <MiniStat label="Persona" value={strategySummary.persona ?? "—"} />
              <MiniStat label="Offer" value={strategySummary.offer ?? "—"} />

              <button
                type="button"
                onClick={() => void onSubmit()}
                disabled={busy || !brief.trim()}
                className="rounded-2xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {busy ? "Working..." : "Create content suggestions"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="mb-5">
      <div className="mb-3 text-sm font-semibold text-slate-700">{title}</div>
      {children}
    </div>
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
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-2 break-words text-sm font-bold text-slate-900">
        {value}
      </div>
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
    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </div>
      {children}
    </div>
  );
}

function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
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

function Input({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
      />
    </label>
  );
}

function LabelledTextarea({
  label,
  value,
  onChange,
  rows,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows: number;
}) {
  return (
    <label className="block">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        className="w-full rounded-3xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:bg-white"
      />
    </label>
  );
}