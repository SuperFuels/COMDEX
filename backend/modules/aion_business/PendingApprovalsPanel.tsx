"use client";

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

export default function PendingApprovalsPanel({
  approvals,
  loading,
  busy,
  onResolve,
}: {
  approvals: ApprovalItem[];
  loading: boolean;
  busy: boolean;
  onResolve: (approvalId: string, approve: boolean) => Promise<void>;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <div className="text-sm font-semibold text-slate-500">BO4</div>
        <h2 className="text-xl font-bold text-slate-900">Pending Approvals</h2>
      </div>

      {loading ? <div className="text-sm text-slate-500">Loading approvals…</div> : null}

      {!loading && approvals.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
          No pending approvals.
        </div>
      ) : null}

      <div className="space-y-4">
        {approvals.map((item) => {
          const payload = item.payload ?? {};
          const caption = String(payload["draft_caption"] ?? "—");
          const carousel = Array.isArray(payload["draft_carousel"])
            ? (payload["draft_carousel"] as unknown[]).map(String)
            : [];

          return (
            <div key={item.id} className="rounded-xl border border-slate-200 p-4">
              <div className="mb-2 flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-slate-900">{item.title}</div>
                  <div className="text-xs text-slate-500">{item.summary}</div>
                </div>
                <div className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
                  {item.status}
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg bg-slate-50 p-3">
                  <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Draft Caption
                  </div>
                  <div className="text-sm text-slate-800">{caption}</div>
                </div>

                <div className="rounded-lg bg-slate-50 p-3">
                  <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Carousel Structure
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {carousel.map((entry) => (
                      <span
                        key={entry}
                        className="rounded-full border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700"
                      >
                        {entry}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-4 flex gap-3">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onResolve(item.id, true)}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white"
                >
                  Approve
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onResolve(item.id, false)}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700"
                >
                  Reject
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}