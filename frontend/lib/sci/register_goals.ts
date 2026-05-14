// =====================================================
//  SCI Goals Panel Registration
// =====================================================
import { registerPanel } from "@/lib/sci/panel_registry";
import SciGoalPanel from "@/components/SQS/SciGoalPanel";

registerPanel({
  id: "goals",
  title: "Goals",
  component: SciGoalPanel,
  makeDefaultProps: () => ({
    wsUrl: process.env.NEXT_PUBLIC_QFC_WS || "ws://localhost:8080/ws/qfc",
    containerId: "sci:goals:init",
    authToken: process.env.NEXT_PUBLIC_AUTH_TOKEN || "",
  }),
});