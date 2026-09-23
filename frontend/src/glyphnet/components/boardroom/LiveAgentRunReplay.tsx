"use client";

import { useMemo, useState } from "react";
import type { WorkflowRun } from "./boardroom.page.types";
import { formatTime, prettifyStatus } from "./boardroom.page.utils";

function toPrettyJson(value: unknown) {
  if (value == null) return "—";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

type Props = {
  run: WorkflowRun;
  compact?: boolean;
};

export default function LiveAgentRunReplay({ run, compact = false }: Props) {
  const [selectedStepIndex, setSelectedStepIndex] = useState(0);

  const steps = useMemo(() => run?.step_runs ?? [], [run]);
  const safeIndex = Math.min(selectedStepIndex, Math.max(steps.length - 1, 0));
  const selectedStep = steps[safeIndex];

  if (!run) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px solid rgba(226,232,240,1)",
          background: "#ffffff",
          padding: 14,
          color: "#64748b",
          fontSize: 12,
        }}
      >
        No run selected.
      </div>
    );
  }

  return (
    <div
      style={{
        borderRadius: 16,
        border: "1px solid rgba(226,232,240,1)",
        background: "#ffffff",
        padding: 14,
        display: "grid",
        gap: 12,
      }}
    >
      <div>
        <div style={{ fontSize: 13, fontWeight: 800, color: "#111827" }}>
          Run replay
        </div>
        <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
          {run.workflow_name} · {prettifyStatus(run.status)}
        </div>
      </div>

      {steps.length === 0 ? (
        <div style={{ fontSize: 12, color: "#64748b" }}>No step data yet.</div>
      ) : (
        <>
          <div
            style={{
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
            }}
          >
            {steps.map((step, index) => {
              const active = index === safeIndex;

              return (
                <button
                  key={step.id ?? `${step.step_id}-${index}`}
                  type="button"
                  onClick={() => setSelectedStepIndex(index)}
                  style={{
                    borderRadius: 999,
                    border: active
                      ? "1px solid rgba(26,138,255,0.55)"
                      : "1px solid rgba(191,206,224,0.9)",
                    background: active
                      ? "rgba(26,138,255,0.14)"
                      : "rgba(255,255,255,0.9)",
                    color: active ? "#0f4ea8" : "#1f2937",
                    padding: "7px 10px",
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  {index + 1}. {step.kind}
                </button>
              );
            })}
          </div>

          {selectedStep ? (
            <div style={{ display: "grid", gap: 10 }}>
              <div
                style={{
                  borderRadius: 12,
                  border: "1px solid rgba(226,232,240,1)",
                  background: "#f8fafc",
                  padding: "10px 12px",
                  display: "grid",
                  gap: 4,
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 700, color: "#111827" }}>
                  {selectedStep.kind}
                </div>
                <div style={{ fontSize: 12, color: "#64748b" }}>
                  Status: {prettifyStatus(selectedStep.status)}
                </div>
                <div style={{ fontSize: 12, color: "#64748b" }}>
                  Started: {formatTime(selectedStep.started_at)}
                </div>
                <div style={{ fontSize: 12, color: "#64748b" }}>
                  Completed: {formatTime(selectedStep.completed_at)}
                </div>
                {selectedStep.error ? (
                  <div style={{ fontSize: 12, color: "#b91c1c", fontWeight: 700 }}>
                    Error: {selectedStep.error}
                  </div>
                ) : null}
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 10,
                }}
              >
                <div
                  style={{
                    borderRadius: 12,
                    border: "1px solid rgba(226,232,240,1)",
                    background: "#ffffff",
                    padding: 12,
                    minHeight: 220,
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 800,
                      color: "#111827",
                      marginBottom: 8,
                    }}
                  >
                    Output payload
                  </div>
                  <pre
                    style={{
                      margin: 0,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      fontSize: 11,
                      lineHeight: 1.45,
                      color: "#334155",
                    }}
                  >
                    {toPrettyJson(selectedStep.output)}
                  </pre>
                </div>

                <div
                  style={{
                    borderRadius: 12,
                    border: "1px solid rgba(226,232,240,1)",
                    background: "#ffffff",
                    padding: 12,
                    minHeight: 220,
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 800,
                      color: "#111827",
                      marginBottom: 8,
                    }}
                  >
                    Run context
                  </div>
                  <pre
                    style={{
                      margin: 0,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      fontSize: 11,
                      lineHeight: 1.45,
                      color: "#334155",
                    }}
                  >
                    {toPrettyJson(run.context)}
                  </pre>
                </div>
              </div>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}