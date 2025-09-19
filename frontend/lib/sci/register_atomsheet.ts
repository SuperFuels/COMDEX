import { registerPanel } from "./panel_registry";
import SCIAtomSheetPanel from "@/pages/sci/sci_atomsheet_panel";

registerPanel({
  id: "atomsheet",
  title: "AtomSheet",
  component: SCIAtomSheetPanel,
  makeDefaultProps: () => ({
    wsUrl: process.env.NEXT_PUBLIC_QFC_WS,
    containerId: "sci:atomsheet:init",
    defaultFile: "backend/data/sheets/example_sheet.atom",
  }),
});