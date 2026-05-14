// =====================================================
//  SCI AtomSheet Panel Registration
// =====================================================

import SCIAtomSheetPanel, {
  SciAtomSheetProps,
} from "@/pages/sci/sci_atomsheet_panel";

export const ATOMSHEET_TOOL = {
  id: "atomsheet",
  title: "AtomSheet",
  component: SCIAtomSheetPanel,
  makeDefaultProps: (): SciAtomSheetProps => ({
    wsUrl: process.env.NEXT_PUBLIC_QFC_WS || "ws://localhost:8080/ws/qfc",
    containerId: "sci:atomsheet:init",
    defaultFile: "backend/data/sheets/example_sheet.atom",
  }),
};