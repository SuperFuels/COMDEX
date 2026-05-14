import React from "react";
import WorkflowArchitectReviewPanel from "./WorkflowArchitectReviewPanel";

type WorkflowArchitectSidebarMountProps = {
  connectedCredentials?: string[];
  missingCredentials?: string[];
};

export function WorkflowArchitectSidebarMount({
  connectedCredentials = ["gmail"],
  missingCredentials = ["hubspot", "calendly"],
}: WorkflowArchitectSidebarMountProps) {
  return (
    <div
      data-testid="workflow-architect-sidebar-mount"
      style={{
        marginTop: 14,
      }}
    >
      <WorkflowArchitectReviewPanel
        connectedCredentials={connectedCredentials}
        missingCredentials={missingCredentials}
        onValidReview={(review) => {
          console.log("[WorkflowArchitect] valid review ready for canvas load", review);
        }}
      />
    </div>
  );
}

export default WorkflowArchitectSidebarMount;
