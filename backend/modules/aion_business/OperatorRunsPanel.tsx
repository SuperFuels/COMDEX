"use client";

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

export default function OperatorRunsPanel({
  runs,
  loading,
}: {
  runs: WorkflowRun[];
  loading: boolean;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <div className="text-sm font-semibold text-slate-500">BO5</div>
        <h2 className="text-xl font-bold text-slate-900">Recent Operator Runs</h2>
      </div>

      {loading ? <div className="text-sm text-slate-500">Loading runs…</div> : null}

      {!loading && runs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
          No runs yet.
        </div>
      ) : null}

      <div className="space-y-3">
        {runs.map((run) => (
          <div key={run.id} className="rounded-xl border border-slate-200 p-4">
            <div className="mb-2 flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-semibold text-slate-900">{run.workflow_name}</div>
                <div className="text-xs text-slate-500">
                  {run.id} · {run.operator_id} · {run.trigger_kind}
                </div>
              </div>
              <StatusPill status={run.status} />
            </div>

            <div className="grid gap-2 text-sm text-slate-600">
              <div>Execution mode: {run.execution_mode}</div>
              <div>Current step index: {run.current_step_index}</div>
              <div>Created: {run.created_at}</div>
              {run.completed_at ? <div>Completed: {run.completed_at}</div> : null}
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {run.step_runs.map((step) => (
                <span
                  key={step.id}
                  className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700"
                >
                  {step.kind}: {step.status}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    queued: "bg-slate-100 text-slate-700",
    running: "bg-blue-100 text-blue-700",
    waiting_approval: "bg-amber-100 text-amber-700",
    failed: "bg-red-100 text-red-700",
    completed: "bg-emerald-100 text-emerald-700",
  };

  return (
    <div className={`rounded-full px-3 py-1 text-xs font-semibold ${styles[status] ?? "bg-slate-100 text-slate-700"}`}>
      {status}
    </div>
  );
}