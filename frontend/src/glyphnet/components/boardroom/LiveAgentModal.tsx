"use client";

import { formatTime, getMarketingStatusTone, getStepLabelFromRun, prettifyStatus } from "./boardroom.page.utils";
import type { AgentRuntimeCard } from "./boardroom.page.types";

type LiveAgentModalProps = {
  agent: AgentRuntimeCard | null;
  onClose: () => void;
  onOpenInInspector: (agent: AgentRuntimeCard) => void;
};

export default function LiveAgentModal({
  agent,
  onClose,
  onOpenInInspector,
}: LiveAgentModalProps) {
  if (!agent) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: "absolute",
        inset: 0,
        background: "rgba(15,23,42,0.42)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        zIndex: 20,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "min(920px, 100%)",
          maxHeight: "85vh",
          overflowY: "auto",
          borderRadius: 22,
          background: "#ffffff",
          border: "1px solid rgba(226,232,240,1)",
          boxShadow: "0 24px 70px rgba(15,23,42,0.24)",
          padding: 20,
          display: "grid",
          gap: 16,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: 12,
          }}
        >
          <div>
            <div style={{ fontSize: 12, color: "#6b7280" }}>Live Agent</div>
            <div style={{ fontSize: 24, fontWeight: 800, color: "#111827" }}>
              {agent.label}
            </div>
            <div style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>
              {agent.role} · {agent.departmentKey.toUpperCase()} · {agent.id}
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            style={{
              width: 36,
              height: 36,
              borderRadius: 999,
              border: "1px solid rgba(148,163,184,0.28)",
              background: "#ffffff",
              color: "#334155",
              cursor: "pointer",
              fontSize: 18,
              fontWeight: 700,
            }}
          >
            ×
          </button>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(5, minmax(0,1fr))",
            gap: 10,
          }}
        >
          {[
            ["Queued", String(agent.queuedCount)],
            ["Running", String(agent.runningCount)],
            ["Waiting", String(agent.waitingApprovalCount)],
            ["Failed", String(agent.failedCount)],
            ["Completed", String(agent.completedCount)],
          ].map(([label, value]) => (
            <div
              key={label}
              style={{
                borderRadius: 12,
                border: "1px solid rgba(226,232,240,1)",
                background: "#f8fafc",
                padding: "10px 12px",
              }}
            >
              <div style={{ fontSize: 11, color: "#6b7280" }}>{label}</div>
              <div
                style={{
                  fontSize: 16,
                  fontWeight: 800,
                  color: "#111827",
                  marginTop: 4,
                }}
              >
                {value}
              </div>
            </div>
          ))}
        </div>

        <div
          style={{
            borderRadius: 16,
            border: "1px solid rgba(226,232,240,1)",
            background: "#ffffff",
            padding: 14,
            display: "grid",
            gap: 10,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 800, color: "#111827" }}>
            Current work
          </div>

          {agent.latestRun ? (
            <>
              <div style={{ fontSize: 13, color: "#111827", fontWeight: 700 }}>
                {agent.latestRun.workflow_name}
              </div>
              <div style={{ fontSize: 12, color: "#64748b" }}>
                Status: {prettifyStatus(agent.latestRun.status)}
              </div>
              <div style={{ fontSize: 12, color: "#64748b" }}>
                Step: {getStepLabelFromRun(agent.latestRun)}
              </div>
              <div style={{ fontSize: 12, color: "#64748b" }}>
                Last update:{" "}
                {formatTime(agent.latestRun.updated_at ?? agent.latestRun.created_at)}
              </div>
              {agent.latestRun.failure_reason ? (
                <div style={{ fontSize: 12, color: "#b91c1c", fontWeight: 700 }}>
                  Failure: {agent.latestRun.failure_reason}
                </div>
              ) : null}
            </>
          ) : (
            <div style={{ fontSize: 12, color: "#64748b" }}>No current run.</div>
          )}
        </div>

        <div
          style={{
            borderRadius: 16,
            border: "1px solid rgba(226,232,240,1)",
            background: "#ffffff",
            padding: 14,
            display: "grid",
            gap: 10,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 800, color: "#111827" }}>
            Run history
          </div>

          {agent.runs.length === 0 ? (
            <div style={{ fontSize: 12, color: "#64748b" }}>No run history yet.</div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {agent.runs.slice(0, 12).map((run) => (
                <div
                  key={run.id}
                  style={{
                    borderRadius: 12,
                    border: "1px solid rgba(226,232,240,1)",
                    background: "#f8fafc",
                    padding: "10px 12px",
                    display: "grid",
                    gap: 4,
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
                    <div style={{ fontSize: 13, fontWeight: 700, color: "#111827" }}>
                      {run.workflow_name}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        fontWeight: 800,
                        textTransform: "uppercase",
                        ...getMarketingStatusTone(run.status),
                        borderRadius: 999,
                        padding: "4px 8px",
                      }}
                    >
                      {prettifyStatus(run.status)}
                    </div>
                  </div>

                  <div style={{ fontSize: 12, color: "#64748b" }}>
                    Step: {getStepLabelFromRun(run)}
                  </div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>
                    Created: {formatTime(run.created_at)} · Updated: {formatTime(run.updated_at)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() => onOpenInInspector(agent)}
            style={{
              borderRadius: 12,
              border: "1px solid rgba(26,138,255,0.4)",
              background: "linear-gradient(180deg, #3394ff, #1a8aff)",
              color: "#ffffff",
              padding: "10px 14px",
              fontSize: 12,
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            Open in boardroom inspector
          </button>

          <button
            type="button"
            onClick={onClose}
            style={{
              borderRadius: 12,
              border: "1px solid rgba(191,206,224,0.9)",
              background: "#ffffff",
              color: "#1f2937",
              padding: "10px 14px",
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}