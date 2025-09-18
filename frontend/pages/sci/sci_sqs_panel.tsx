import * as React from "react";

export default function SciSqsPanel(props: {
  wsUrl?: string;
  containerId?: string;
}) {
  return (
    <div className="p-4 text-zinc-200">
      <div className="text-lg font-semibold">SQS Panel</div>
      <div className="text-sm text-zinc-400">container: {props.containerId || "—"}</div>
      <div className="mt-3 text-sm">
        (Drop in your SQS grid here; this is just a placeholder)
      </div>
    </div>
  );
}