export type WorkflowArchitectBuildReviewRequest = {
  workflow_goal: string;
  provider?: string;
  model?: string | null;
  user_steps?: Record<string, unknown>[];
  business_context?: Record<string, unknown>;
  connected_credentials?: string[];
  missing_credentials?: string[];
  must_not_do?: string[];
  inputs?: Record<string, unknown>;
};

export type WorkflowArchitectBuildReviewResponse = {
  ok: boolean;
  provider?: Record<string, unknown>;
  review?: Record<string, unknown>;
  build_pack?: Record<string, unknown>;
  errors?: string[];
  warnings?: string[];
};

function getApiBase(): string {
  const raw =
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "";

  return raw.replace(/\/+$/, "");
}

export async function buildWorkflowArchitectReview(
  payload: WorkflowArchitectBuildReviewRequest,
): Promise<WorkflowArchitectBuildReviewResponse> {
  const apiBase = getApiBase();

  const response = await fetch(`${apiBase}/api/workflow-architect/build-review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      provider: "mock",
      user_steps: [],
      business_context: {},
      connected_credentials: [],
      missing_credentials: [],
      must_not_do: [],
      inputs: {},
      ...payload,
    }),
  });

  const data = (await response.json()) as WorkflowArchitectBuildReviewResponse;

  if (!response.ok) {
    return {
      ok: false,
      errors: [
        `workflow_architect_http_error:${response.status}`,
        ...(Array.isArray(data.errors) ? data.errors : []),
      ],
      warnings: Array.isArray(data.warnings) ? data.warnings : [],
      provider: data.provider,
      review: data.review,
      build_pack: data.build_pack,
    };
  }

  return data;
}

export async function getWorkflowArchitectHealth(): Promise<Record<string, unknown>> {
  const apiBase = getApiBase();

  const response = await fetch(`${apiBase}/api/workflow-architect/health`, {
    method: "GET",
  });

  return (await response.json()) as Record<string, unknown>;
}
