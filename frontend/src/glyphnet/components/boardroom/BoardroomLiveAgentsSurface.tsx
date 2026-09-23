"use client";

import LiveAgentModal from "./LiveAgentModal";
import { formatTime, getMarketingStatusTone, getStepLabelFromRun, prettifyStatus } from "./boardroom.page.utils";
import type { AgentRuntimeCard } from "./boardroom.page.types";
import type { BusinessWorkspace } from "./boardroom.domain";

type BoardroomLiveAgentsSurfaceProps = {
  liveWorkspace: BusinessWorkspace;
  liveActiveAgents: AgentRuntimeCard[];
  selectedLiveAgent: AgentRuntimeCard | null;
  renderModeSwitch: () => JSX.Element;
  onOpenAgentModal: (agent: AgentRuntimeCard) => void;
  onCloseAgentModal: () => void;
  onOpenAgentInInspector: (agent: AgentRuntimeCard) => void;
};

export default function BoardroomLiveAgentsSurface({
  liveWorkspace,
  liveActiveAgents,
  selectedLiveAgent,
  renderModeSwitch,
  onOpenAgentModal,
  onCloseAgentModal,
  onOpenAgentInInspector,
}: BoardroomLiveAgentsSurfaceProps) {
  return (
    <div
      style={{
        width: "100%",
        borderRadius: 22,
        overflow: "hidden",
        minHeight: 760,
        background:
          "radial-gradient(1200px 600px at 20% 10%, rgba(26,138,255,0.08), transparent 55%)," +
          "radial-gradient(1000px 500px at 80% 20%, rgba(244,26,255,0.04), transparent 55%)," +
          "linear-gradient(180deg, #f7f9fc, #edf2f8)",
        border: "1px solid rgba(148,163,184,0.22)",
        boxShadow: "0 18px 50px rgba(15,23,42,0.06)",
        display: "flex",
        flexDirection: "column",
        minWidth: 0,
        position: "relative",
      }}
    >
      <div
        style={{
          padding: "18px 20px 12px",
          borderBottom: "1px solid rgba(148,163,184,0.16)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div style={{ fontSize: 11, color: "#6b7280" }}>Boardroom</div>
          <div
            style={{
              fontSize: 22,
              fontWeight: 800,
              color: "#111827",
              marginTop: 2,
              lineHeight: 1.1,
            }}
          >
            {liveWorkspace.name}
          </div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
            Live Active Agents
          </div>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 10,
            alignItems: "flex-end",
          }}
        >
          <div
            style={{
              padding: "6px 12px",
              borderRadius: 999,
              border: "1px solid rgba(26,138,255,0.35)",
              background: "rgba(255,255,255,0.78)",
              fontSize: 10,
              whiteSpace: "nowrap",
              color: "#0f4ea8",
              backdropFilter: "blur(6px)",
            }}
          >
            BUSINESS · LIVE AGENTS
          </div>
          {renderModeSwitch()}
        </div>
      </div>

      <div
        style={{
          padding: 20,
          overflowY: "auto",
          minHeight: 0,
          flex: "1 1 auto",
        }}
      >
        {liveActiveAgents.length === 0 ? (
          <div
            style={{
              borderRadius: 16,
              border: "1px solid rgba(226,232,240,1)",
              background: "#ffffff",
              padding: 16,
              color: "#64748b",
              fontSize: 13,
            }}
          >
            No active agents right now.
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: 14,
            }}
          >
            {liveActiveAgents.map((agent) => {
              const tone = getMarketingStatusTone(agent.runtimeStatus);

              return (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => onOpenAgentModal(agent)}
                  style={{
                    textAlign: "left",
                    borderRadius: 18,
                    border: "1px solid rgba(148,163,184,0.18)",
                    background: "rgba(255,255,255,0.94)",
                    padding: 14,
                    display: "grid",
                    gap: 10,
                    cursor: "pointer",
                    boxShadow: "0 10px 24px rgba(15,23,42,0.05)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      gap: 10,
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 800, color: "#111827" }}>
                        {agent.label}
                      </div>
                      <div style={{ fontSize: 12, color: "#64748b", marginTop: 3 }}>
                        {agent.role}
                      </div>
                      <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 3 }}>
                        {agent.departmentKey.toUpperCase()} · {agent.id}
                      </div>
                    </div>

                    <div
                      style={{
                        borderRadius: 999,
                        padding: "6px 10px",
                        fontSize: 11,
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: 0.3,
                        ...tone,
                      }}
                    >
                      {prettifyStatus(agent.runtimeStatus)}
                    </div>
                  </div>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(2, minmax(0,1fr))",
                      gap: 8,
                    }}
                  >
                    {[
                      ["Running", String(agent.runningCount)],
                      ["Waiting", String(agent.waitingApprovalCount)],
                      ["Queued", String(agent.queuedCount)],
                      ["Failed", String(agent.failedCount)],
                    ].map(([label, value]) => (
                      <div
                        key={label}
                        style={{
                          borderRadius: 12,
                          border: "1px solid rgba(226,232,240,1)",
                          background: "#f8fafc",
                          padding: "8px 10px",
                        }}
                      >
                        <div style={{ fontSize: 10, color: "#6b7280" }}>{label}</div>
                        <div
                          style={{
                            fontSize: 14,
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
                      borderRadius: 12,
                      border: "1px solid rgba(226,232,240,1)",
                      background: "#ffffff",
                      padding: "10px 12px",
                      display: "grid",
                      gap: 4,
                    }}
                  >
                    <div style={{ fontSize: 11, color: "#6b7280" }}>Current activity</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "#111827" }}>
                      {agent.latestRun?.workflow_name ?? "No recent workflow"}
                    </div>
                    <div style={{ fontSize: 12, color: "#64748b" }}>
                      Step: {getStepLabelFromRun(agent.latestRun)}
                    </div>
                    <div style={{ fontSize: 12, color: "#64748b" }}>
                      Updated:{" "}
                      {formatTime(agent.latestRun?.updated_at ?? agent.latestRun?.created_at)}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      <LiveAgentModal
        agent={selectedLiveAgent}
        onClose={onCloseAgentModal}
        onOpenInInspector={onOpenAgentInInspector}
      />
    </div>
  );
}