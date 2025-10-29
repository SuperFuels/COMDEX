// =====================================================
//  SCI Editor Panel Registration
// =====================================================
import { registerPanel } from "./panel_registry";
import SciEditorPanel from "@/pages/sci/sci_editor_panel";

registerPanel({
  id: "editor",
  title: "Editor",
  component: SciEditorPanel,
  makeDefaultProps: () => ({
    wsUrl: process.env.NEXT_PUBLIC_QFC_WS,
    containerId: "sci:editor:init",
  }),
});