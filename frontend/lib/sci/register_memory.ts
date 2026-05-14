// =====================================================
//  SCI Memory Panel Registration
// =====================================================
import { registerPanel } from "./panel_registry";
import SciMemoryPanel from "@/pages/sci/sci_memory_panel";

registerPanel({
  id: "memory",
  title: "Memory Scrolls",
  component: SciMemoryPanel,
  makeDefaultProps: () => ({
    wsUrl: process.env.NEXT_PUBLIC_QFC_WS || "ws://localhost:8080/ws/qfc",
    authToken: process.env.NEXT_PUBLIC_AUTH_TOKEN || "",
    containerId: "sci:memory:init",
  }),
});