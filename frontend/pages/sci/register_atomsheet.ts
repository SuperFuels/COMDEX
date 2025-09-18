import { registerPanel } from "./panel_registry";
// IMPORTANT: use your existing panel, not the stub I shared earlier
import SciAtomSheetPanel from "./sci_atomsheet_panel";

registerPanel({
  id: "atomsheet",
  title: "AtomSheet",
  component: SciAtomSheetPanel,
  makeDefaultProps: () => ({ /* seed anything the panel expects */ })
});