import React, { useMemo, useState } from "react";
import {
  buildWorkflowArchitectReview,
  type WorkflowArchitectBuildReviewResponse,
} from "../../api/workflowArchitectClient";

type WorkflowArchitectReviewPanelProps = {
  defaultGoal?: string;
  businessContext?: Record<string, unknown>;
  connectedCredentials?: string[];
  missingCredentials?: string[];
  onValidReview?: (review: WorkflowArchitectBuildReviewResponse) => void;
};

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function getReviewSteps(payload: WorkflowArchitectBuildReviewResponse): Record<string, unknown>[] {
  const review = payload.review || {};
  const spec = (review["spec"] || review["workflow_spec"] || payload["spec"]) as Record<string, unknown> | undefined;
  const steps = spec?.["steps"] || review["steps"];
  return Array.isArray(steps) ? (steps as Record<string, unknown>[]) : [];
}

function getErrors(payload: WorkflowArchitectBuildReviewResponse | null): string[] {
  if (!payload) return [];
  return asArray(payload.errors).map(String);
}

function getWarnings(payload: WorkflowArchitectBuildReviewResponse | null): string[] {
  if (!payload) return [];
  return asArray(payload.warnings).map(String);
}

function reviewIsCanvasLoadable(payload: WorkflowArchitectBuildReviewResponse | null): boolean {
  if (!payload || payload.ok !== true) return false;

  const errors = getErrors(payload);
  if (errors.length > 0) return false;

  const review = payload.review || {};
  if (review["ok"] === false) return false;

  const combined = JSON.stringify(payload).toLowerCase();

  const forbidden = [
    "users.messages.send",
    "gmail_live_send",
    "send_message(",
    "live_execute",
  ];

  return !forbidden.some((token) => combined.includes(token));
}

export function WorkflowArchitectReviewPanel({
  defaultGoal = "",
  businessContext = {},
  connectedCredentials = [],
  missingCredentials = [],
  onValidReview,
}: WorkflowArchitectReviewPanelProps) {
  const [goal, setGoal] = useState(defaultGoal);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WorkflowArchitectBuildReviewResponse | null>(null);
  const [localError, setLocalError] = useState<string>("");

  const steps = useMemo(() => (result ? getReviewSteps(result) : []), [result]);
  const errors = useMemo(() => getErrors(result), [result]);
  const warnings = useMemo(() => getWarnings(result), [result]);
  const canLoadToCanvas = useMemo(() => reviewIsCanvasLoadable(result), [result]);

  async function handleBuildReview() {
    const trimmedGoal = goal.trim();
    setLocalError("");

    if (!trimmedGoal) {
      setLocalError("Please describe the workflow you want Aion to build.");
      return;
    }

    setLoading(true);
    try {
      const response = await buildWorkflowArchitectReview({
        workflow_goal: trimmedGoal,
        provider: "mock",
        business_context: businessContext,
        connected_credentials: connectedCredentials,
        missing_credentials: missingCredentials,
        must_not_do: [
          "Do not live-send Gmail messages.",
          "Do not bypass human approval before external writes.",
          "Do not invent unsupported Aion node types.",
        ],
      });

      setResult(response);
    } catch (error) {
      setResult({
        ok: false,
        errors: [`workflow_architect_client_error:${String(error)}`],
      });
    } finally {
      setLoading(false);
    }
  }

  function handleLoadToCanvas() {
    if (!canLoadToCanvas || !result) return;
    onValidReview?.(result);
  }

  return (
    <section
      data-testid="workflow-architect-review-panel"
      style={{
        display: "grid",
        gap: 12,
        padding: 14,
        border: "1px solid rgba(148, 163, 184, 0.35)",
        borderRadius: 14,
        background: "rgba(255,255,255,0.92)",
      }}
    >
      <header>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>
          Aion Workflow Architect
        </div>
        <div style={{ fontSize: 12, color: "#64748b" }}>
          Describe a workflow. Aion will generate a safe dry-run review first.
        </div>
      </header>

      <textarea
        data-testid="workflow-architect-goal-input"
        value={goal}
        onChange={(event) => setGoal(event.target.value)}
        placeholder="Example: Build a Gmail customer reply workflow that extracts lead details, creates a HubSpot contact, drafts a welcome email, and pauses for approval."
        rows={4}
        style={{
          width: "100%",
          resize: "vertical",
          border: "1px solid rgba(148, 163, 184, 0.45)",
          borderRadius: 10,
          padding: 10,
          fontSize: 13,
        }}
      />

      {localError ? (
        <div data-testid="workflow-architect-local-error" style={{ color: "#b91c1c", fontSize: 12 }}>
          {localError}
        </div>
      ) : null}

      <button
        data-testid="workflow-architect-build-review-button"
        type="button"
        onClick={handleBuildReview}
        disabled={loading}
        style={{
          border: "0",
          borderRadius: 10,
          padding: "10px 12px",
          fontWeight: 700,
          cursor: loading ? "wait" : "pointer",
        }}
      >
        {loading ? "Building review..." : "Build safe workflow review"}
      </button>

      {result ? (
        <div data-testid="workflow-architect-review-result" style={{ display: "grid", gap: 10 }}>
          <div style={{ fontSize: 12, fontWeight: 700 }}>
            Review status: {result.ok ? "Valid response" : "Needs attention"}
          </div>

          {steps.length > 0 ? (
            <div data-testid="workflow-architect-generated-steps">
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>
                Generated steps
              </div>
              <ol style={{ margin: 0, paddingLeft: 18 }}>
                {steps.map((step, index) => (
                  <li key={String(step.step_id || index)} style={{ fontSize: 12, marginBottom: 4 }}>
                    <strong>{String(step.label || step.step_id || `Step ${index + 1}`)}</strong>
                    {" "}
                    <span style={{ color: "#64748b" }}>
                      {String(step.node_type || "unknown_node")}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          ) : null}

          {warnings.length > 0 ? (
            <div data-testid="workflow-architect-warnings" style={{ fontSize: 12, color: "#92400e" }}>
              <strong>Warnings:</strong> {warnings.join(" | ")}
            </div>
          ) : null}

          {errors.length > 0 ? (
            <div data-testid="workflow-architect-errors" style={{ fontSize: 12, color: "#b91c1c" }}>
              <strong>Errors:</strong> {errors.join(" | ")}
            </div>
          ) : null}

          <button
            data-testid="workflow-architect-load-canvas-button"
            type="button"
            onClick={handleLoadToCanvas}
            disabled={!canLoadToCanvas}
            style={{
              border: "0",
              borderRadius: 10,
              padding: "10px 12px",
              fontWeight: 700,
              opacity: canLoadToCanvas ? 1 : 0.45,
              cursor: canLoadToCanvas ? "pointer" : "not-allowed",
            }}
          >
            Load valid review onto canvas
          </button>

          {!canLoadToCanvas ? (
            <div data-testid="workflow-architect-load-blocked" style={{ fontSize: 12, color: "#64748b" }}>
              Canvas loading is blocked until Aion returns a valid dry-run review with no safety errors.
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

export default WorkflowArchitectReviewPanel;
