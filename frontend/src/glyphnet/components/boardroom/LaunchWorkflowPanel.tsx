"use client";

import { useState } from "react";

export default function LaunchWorkflowPanel({
  onLaunch,
  busy,
}: {
  onLaunch: (brief: string) => Promise<void>;
  busy: boolean;
}) {
  const [brief, setBrief] = useState(
    "Draft a Facebook post and simple carousel for spring telecom upgrade offer.",
  );

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <div className="text-sm font-semibold text-slate-500">BO9</div>
        <h2 className="text-xl font-bold text-slate-900">Launch Marketing Workflow</h2>
      </div>

      <div className="space-y-3">
        <label className="block text-sm font-medium text-slate-700">
          Content brief
          <textarea
            className="mt-2 min-h-[120px] w-full rounded-xl border border-slate-300 px-3 py-3 text-sm outline-none"
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
          />
        </label>

        <button
          type="button"
          disabled={busy || !brief.trim()}
          onClick={() => onLaunch(brief)}
          className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {busy ? "Launching…" : "Launch workflow"}
        </button>
      </div>
    </div>
  );
}