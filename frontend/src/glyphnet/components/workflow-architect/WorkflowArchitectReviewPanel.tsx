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
  const legacyPayload = payload as unknown as Record<string, unknown>;
  const spec = (review["spec"] || review["workflow_spec"] || legacyPayload["spec"]) as Record<string, unknown> | undefined;
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
    <section data-testid="workflow-architect-review-panel">
      <header>
        <strong>Aion Workflow Architect</strong>
        <p>Describe a workflow. Aion will generate a safe dry-run review first.</p>
      </header>

      <textarea
        data-testid="workflow-architect-goal-input"
        value={goal}
        onChange={(event) => setGoal(event.target.value)}
        placeholder="Example: Build a Gmail customer reply workflow."
        rows={4}
      />

      {localError ? (
        <div data-testid="workflow-architect-local-error">{localError}</div>
      ) : null}

      <button
        data-testid="workflow-architect-build-review-button"
        type="button"
        onClick={handleBuildReview}
        disabled={loading}
      >
        {loading ? "Building review..." : "Build safe workflow review"}
      </button>

      {result ? (
        <div data-testid="workflow-architect-review-result">
          <div>Review status: {result.ok ? "Valid response" : "Needs attention"}</div>

          {steps.length > 0 ? (
            <div data-testid="workflow-architect-generated-steps">
              <strong>Generated steps</strong>
              <ol>
                {steps.map((step, index) => (
                  <li key={String(step.step_id || index)}>
                    {String(step.label || step.step_id || `Step ${index + 1}`)}
                    {" "}
                    {String(step.node_type || "unknown_node")}
                  </li>
                ))}
              </ol>
            </div>
          ) : null}

          {warnings.length > 0 ? (
            <div data-testid="workflow-architect-warnings">
              Warnings: {warnings.join(" | ")}
            </div>
          ) : null}

          {errors.length > 0 ? (
            <div data-testid="workflow-architect-errors">
              Errors: {errors.join(" | ")}
            </div>
          ) : null}

          <button
            data-testid="workflow-architect-load-canvas-button"
            type="button"
            onClick={handleLoadToCanvas}
            disabled={!canLoadToCanvas}
          >
            Load valid review onto canvas
          </button>

          {!canLoadToCanvas ? (
            <div data-testid="workflow-architect-load-blocked">
              Canvas loading is blocked until Aion returns a valid dry-run review with no safety errors.
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

export default WorkflowArchitectReviewPanel;
