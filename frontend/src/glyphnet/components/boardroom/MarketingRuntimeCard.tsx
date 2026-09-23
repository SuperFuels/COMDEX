"use client";

import { MARKETING_OPERATOR_ID } from "./boardroom.page.constants";
import { formatTime, getCurrentStepLabel, prettifyStatus } from "./boardroom.page.utils";
import type { ApprovalItem, WorkflowRun } from "./boardroom.page.types";
import type { DepartmentFloorAgent } from "./boardroom.domain";

type MarketingRuntimeCardProps = {
  selectedMarketingAgent: DepartmentFloorAgent | null;
  marketingStatusTone: {
    background: string;
    border: string;
    color: string;
  };
  marketingOperatorStatus?: string;
  runningCount: number;
  waitingApprovalCount: number;
  failedCount: number;
  completedCount: number;
  activeMarketingRun: WorkflowRun | null;
  selectedMarketingApproval: ApprovalItem | null;
  marketingRuntimeError: string | null;
  launchingMarketing: boolean;
  launchMarketingError: string | null;
  loadingMarketingRuntime: boolean;
  onLaunchMarketingWorkflow: () => void;
  onOpenMarketingStream: () => void;
  onOpenBrandFoundation: () => void;
};

export default function MarketingRuntimeCard({
  selectedMarketingAgent,
  marketingStatusTone,
  marketingOperatorStatus,
  runningCount,
  waitingApprovalCount,
  failedCount,
  completedCount,
  activeMarketingRun,
  selectedMarketingApproval,
  marketingRuntimeError,
  launchingMarketing,
  launchMarketingError,
  loadingMarketingRuntime,
  onLaunchMarketingWorkflow,
  onOpenMarketingStream,
  onOpenBrandFoundation,
}: MarketingRuntimeCardProps) {
  return (
    <div
      style={{
        borderRadius: 16,
        border: "1px solid rgba(26,138,255,0.16)",
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.95), rgba(248,250,252,0.95))",
        padding: 12,
        display: "grid",
        gap: 10,
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
          <div style={{ fontSize: 11, color: "#6b7280" }}>Live Marketing Operator</div>
          <div style={{ fontSize: 16, fontWeight: 800, color: "#111827", marginTop: 2 }}>
            {selectedMarketingAgent?.label ?? "Campaigns"}
          </div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
            {MARKETING_OPERATOR_ID}
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
            ...marketingStatusTone,
          }}
        >
          {prettifyStatus(marketingOperatorStatus)}
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
          ["Running", String(runningCount)],
          ["Awaiting approval", String(waitingApprovalCount)],
          ["Failed", String(failedCount)],
          ["Completed", String(completedCount)],
        ].map(([label, value]) => (
          <div
            key={label}
            style={{
              borderRadius: 12,
              border: "1px solid rgba(226,232,240,1)",
              background: "#ffffff",
              padding: "8px 10px",
            }}
          >
            <div style={{ fontSize: 10, color: "#6b7280", lineHeight: 1.1 }}>{label}</div>
            <div
              style={{
                fontSize: 15,
                fontWeight: 800,
                color: "#0f172a",
                marginTop: 4,
                lineHeight: 1.1,
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
          gap: 6,
        }}
      >
        <div style={{ fontSize: 11, fontWeight: 700, color: "#334155" }}>Selected run</div>
        <div style={{ fontSize: 13, fontWeight: 700, color: "#111827" }}>
          {activeMarketingRun?.workflow_name ?? "No active marketing run"}
        </div>
        <div style={{ fontSize: 12, color: "#64748b" }}>
          Step: {getCurrentStepLabel(activeMarketingRun)}
        </div>
        <div style={{ fontSize: 12, color: "#64748b" }}>
          Last update:{" "}
          {formatTime(activeMarketingRun?.updated_at ?? activeMarketingRun?.created_at)}
        </div>
        {selectedMarketingApproval ? (
          <div
            style={{
              marginTop: 2,
              fontSize: 12,
              color: "#b45309",
              fontWeight: 700,
            }}
          >
            Approval pending: {selectedMarketingApproval.title}
          </div>
        ) : null}
        {marketingRuntimeError ? (
          <div
            style={{
              marginTop: 2,
              fontSize: 12,
              color: "#b91c1c",
            }}
          >
            {marketingRuntimeError}
          </div>
        ) : null}
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={onLaunchMarketingWorkflow}
          disabled={launchingMarketing}
          style={{
            borderRadius: 12,
            border: "1px solid rgba(16,185,129,0.35)",
            background: launchingMarketing
              ? "rgba(226,232,240,0.9)"
              : "linear-gradient(180deg, #22c55e, #16a34a)",
            color: launchingMarketing ? "#475569" : "#ffffff",
            padding: "10px 12px",
            fontSize: 12,
            fontWeight: 800,
            cursor: launchingMarketing ? "not-allowed" : "pointer",
            boxShadow: launchingMarketing
              ? "none"
              : "0 8px 18px rgba(34,197,94,0.18)",
          }}
        >
          {launchingMarketing ? "Launching..." : "Launch workflow"}
        </button>

        <button
          type="button"
          onClick={onOpenMarketingStream}
          style={{
            borderRadius: 12,
            border: "1px solid rgba(26,138,255,0.4)",
            background: "linear-gradient(180deg, #3394ff, #1a8aff)",
            color: "#ffffff",
            padding: "10px 12px",
            fontSize: 12,
            fontWeight: 800,
            cursor: "pointer",
            boxShadow: "0 8px 18px rgba(26,138,255,0.18)",
          }}
        >
          Open marketing stream
        </button>

        <button
          type="button"
          onClick={onOpenBrandFoundation}
          style={{
            borderRadius: 12,
            border: "1px solid rgba(191,206,224,0.9)",
            background: "rgba(255,255,255,0.9)",
            color: "#1f2937",
            padding: "10px 12px",
            fontSize: 12,
            fontWeight: 700,
            cursor: "pointer",
          }}
        >
          Open brand foundation
        </button>
      </div>

      {launchMarketingError ? (
        <div
          style={{
            fontSize: 12,
            color: "#b91c1c",
          }}
        >
          {launchMarketingError}
        </div>
      ) : null}

      <div style={{ fontSize: 11, color: "#64748b" }}>
        {loadingMarketingRuntime
          ? "Loading execution-backed marketing runtime..."
          : "Marketing operator state is now tied to live workflow runtime."}
      </div>
    </div>
  );
}