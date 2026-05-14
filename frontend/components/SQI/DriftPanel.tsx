// frontend/components/SQI/DriftPanel.tsx
"use client";
import React from "react";

export default function DriftPanel({
  data,
  loading,
  error,
}: {
  data?: any;
  loading?: boolean;
  error?: string;
}) {
  if (loading) return <div className="text-sm text-gray-500">Computing drift…</div>;
  if (error) return <div className="text-sm text-red-600">Error: {error}</div>;
  if (!data) return <div className="text-sm text-gray-500">No drift data.</div>;

  return (
    <div className="border rounded p-3 space-y-2">
      <div className="text-sm">
        <b>Container:</b> {data.container_id} &nbsp;|&nbsp; 
        <b>Status:</b> {data.status} &nbsp;|&nbsp; 
        <b>Total Drift:</b> {data.total_weight}
      </div>

      {data.gaps?.length ? (
        <div className="space-y-3">
          {data.gaps.map((g: any, i: number) => (
            <div key={i} className="bg-gray-50 border rounded p-2">
              <div className="font-semibold text-sm">{g.name}</div>
              <div className="text-xs text-gray-700">
                Reason: {g.reason} • Weight: {g.weight}
              </div>
              {g.missing?.length ? (
                <div className="text-xs mt-1">
                  <b>Missing:</b> {g.missing.join(", ")}
                </div>
              ) : null}
              {g.suggestions?.length ? (
                <div className="text-xs mt-2">
                  <b>Suggestions:</b>
                  <ul className="list-disc ml-5">
                    {g.suggestions.map((s: any, j: number) => (
                      <li key={j}>
                        <i>{s.missing}</i>:{" "}
                        {s.candidates.map((c: any) => `${c.name} (${c.score})`).join(", ")}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-sm text-green-700">No gaps — drift closed ✅</div>
      )}
    </div>
  );
}