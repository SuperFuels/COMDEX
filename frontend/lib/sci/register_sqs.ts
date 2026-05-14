// =====================================================
//  SCI SQS Panel Registration
// =====================================================
import { registerPanel } from "./panel_registry";
import SciSqsPanel from "@/pages/sci/sci_sqs_panel";

registerPanel({
  id: "sqs",
  title: "SQS",
  component: SciSqsPanel,
  makeDefaultProps: () => ({
    wsUrl: process.env.NEXT_PUBLIC_QFC_WS || "ws://localhost:8080/ws/qfc",
    authToken: process.env.NEXT_PUBLIC_AUTH_TOKEN || "",
    containerId: "sci:sqs:init",
    file: "backend/data/sheets/example_sheet.atom",
  }),
});